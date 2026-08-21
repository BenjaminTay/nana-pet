# -*- coding: utf-8 -*-
"""那艺娜小狗桌宠 - 入口：托盘图标 + 多只宠物管理 + 每日问候 + 全局快捷键"""
import logging
import os
import random
import sys
from datetime import datetime

from qtcompat import (IS_MAC, QTimer, QPoint, QIcon, QAction, QGuiApplication,
                      QApplication, QMenu, QSystemTrayIcon, DIALOG_ACCEPTED)

import config
from nana.hotkeys import GlobalHotkeys
from nana.settings_dialog import SettingsDialog
from nana.size_dialog import SizeDialog
from nana.quote_library_dialog import QuoteLibraryDialog
from pet import (PetWindow, PetState, hourly_egg_for, screen_geometry_for,
                 APPEARANCE_NAMES, emotion_state)

ICON_FILE = 'icon.png' if IS_MAC else 'icon.ico'   # mac 不读 ico'
LOG_DIR = os.path.join(config.DATA_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, 'app.log'),
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
)   # 3.8 兼容：basicConfig 不支持 encoding，日志文件默认本地编码（中文 Windows 为 GBK）

class PetApp:
    def __init__(self, app):
        self.app = app
        app.setQuitOnLastWindowClosed(False)
        self.cfg = config.load()
        self.pets = {}
        self._exiting = False
        self._hotkey_status = '快捷键：初始化中'

        # 位置/大小等交互状态采用短暂防抖保存，避免连续滚轮缩放频繁写文件。
        self.save_debounce = QTimer()
        self.save_debounce.setSingleShot(True)
        self.save_debounce.setInterval(500)
        self.save_debounce.timeout.connect(self.save_state)

        # 全局快捷键
        self.hotkeys = GlobalHotkeys(self)
        app.installNativeEventFilter(self.hotkeys)
        self.act_hotkey_status = QAction(self._hotkey_status, self.app)
        self.act_hotkey_status.setEnabled(False)
        self.hotkeys.register_all(self.cfg.get('hotkeys', {}))

        # 托盘
        self.tray = QSystemTrayIcon(QIcon(os.path.join(config.BASE_DIR, 'assets', ICON_FILE)))
        self.tray.setToolTip('那艺娜小狗桌宠')
        self.tray.activated.connect(self._on_tray_activated)

        self.act_speech = QAction('💬 说话', checkable=True, checked=self.cfg['speech'])
        self.act_adult_quotes = QAction(
            '🔞 成人语录模式', checkable=True,
            checked=self.cfg.get('adult_quotes', True),
        )
        self.act_adult_quotes.setStatusTip(
            '开启：高强度语录 + 双模式共用；关闭：普通语录 + 双模式共用')
        self.act_quote_library = QAction('🗂️ 管理语录库', self.app)
        self.act_quote_library.setStatusTip(
            '用表格新增、修改、停用、删除语录，并调整显示模式')
        self.act_top = QAction('📌 置顶显示', checkable=True,
                               checked=self.cfg['always_on_top'])
        self.act_through = QAction('🖱 鼠标穿透（穿透后从托盘恢复）', checkable=True,
                                   checked=self.cfg['click_through'])
        self.act_autostart = QAction('🚀 开机自启', checkable=True,
                                     checked=config.get_autostart())
        self.act_hide = QAction('🙈 隐藏（点托盘恢复）', checkable=True, checked=False)
        self.act_speech.toggled.connect(self._on_speech)
        self.act_adult_quotes.toggled.connect(self._on_adult_quotes)
        self.act_quote_library.triggered.connect(self.open_quote_library)
        self.act_top.toggled.connect(self._on_always_on_top)
        self.act_through.toggled.connect(self._on_click_through)
        self.act_autostart.toggled.connect(self._on_autostart)
        self.act_hide.toggled.connect(self._on_hide)

        self.build_tray_menu()

        # 恢复上次的宠物
        if self.cfg['pets']:
            for p in self.cfg['pets']:
                self.add_pet(p)
        else:
            self.add_pet(None)

        # 每日问候（只让第一只说话，避免合唱）
        today = datetime.now().strftime('%Y-%m-%d')
        if self.cfg.get('last_greeting') != today and self.pets:
            first = next(iter(self.pets.values()))
            QTimer.singleShot(1500, first.greet)
            self.cfg['last_greeting'] = today

        # 自动保存（30秒+退出时）
        self.save_timer = QTimer()
        self.save_timer.timeout.connect(self.save_state)
        self.save_timer.start(30000)
        # 关键修复：aboutToQuit 只做存档，不做完整退出，避免递归
        app.aboutToQuit.connect(self.save_state)

        # 整点彩蛋：每小时一次应景语录（不打扰隐藏/睡眠中的宠物）
        self._last_egg_hour = datetime.now().hour
        self.egg_timer = QTimer()
        self.egg_timer.timeout.connect(self._hourly_egg)
        self.egg_timer.start(20000)

        logging.info(f'启动完成：{len(self.pets)} 只宠物')

    # ---------------- 宠物管理 ----------------
    def add_pet(self, saved):
        pet_id = saved['id'] if saved else self.cfg['next_id']
        if saved is None:
            self.cfg['next_id'] += 1
        last_fed = saved.get('last_fed') if saved else None
        appearance = (saved.get('appearance', self.cfg.get('appearance', 'classic'))
                      if saved else self.cfg.get('appearance', 'classic'))
        pet = PetWindow(pet_id, self.cfg, last_fed=last_fed,
                        on_remove=self.remove_pet, on_exit=self.on_exit,
                        on_state_changed=self.request_save,
                        appearance=appearance)
        if saved:
            pet.set_scale(config.scale_from_pet(saved), notify=False)
            # 多显示器：按存档坐标所在屏幕钳制，宠物留在原显示器
            screen = screen_geometry_for(
                QPoint(saved.get('x', 100) + pet.width() // 2,
                       saved.get('y', 100) + pet.height() // 2))
            x, y = pet.clamp_window_position(
                saved.get('x', 100), saved.get('y', 100), screen)
            pet.move(x, y)
            pet.ground_y = y
        else:
            screen = QApplication.primaryScreen().availableGeometry()
            x = random.randint(screen.left() + 50,
                               screen.left() + screen.width()
                               - pet.width() - 50)
            y = screen.top() + screen.height() - pet.height() - 30
            x, y = pet.clamp_window_position(x, y, screen)
            pet.move(x, y)
            pet.ground_y = pet.y()
        # 重启后恢复穿透设置（配置开启但进程重启后 window flag 会丢）
        if self.cfg.get('click_through'):
            pet.set_click_through(True)
        # 隐藏状态下新增的宠物保持隐藏，不突然冒出来
        if self.act_hide.isChecked():
            pet.set_hidden(True)
        self.pets[pet_id] = pet
        self._update_pet_menu_state()
        self.request_save()
        logging.info(f'添加宠物 #{pet_id}')
        return pet

    def remove_pet(self, pet_id):
        pet = self.pets.pop(pet_id, None)
        if pet:
            pet.close()
            pet.deleteLater()
            self.request_save()
            logging.info(f'移除宠物 #{pet_id}')
        if not self.pets:
            # 允许暂时没有宠物；程序继续驻留菜单栏，可通过“添加一只”恢复。
            logging.info('当前没有宠物，程序继续驻留菜单栏')
        self._update_pet_menu_state()

    def all_dance(self):
        for pet in self.pets.values():
            pet.play_action(PetState.DANCE, loops=2)

    def feed_all(self):
        for pet in self.pets.values():
            pet.feed()

    def reset_positions(self):
        """复位到各自所在屏幕右下角、任务栏上方（多只错开排列不重叠）"""
        groups = {}
        for pet in self.pets.values():
            sc = QGuiApplication.screenAt(QPoint(pet.x() + pet.width() // 2,
                                                 pet.y() + pet.height() // 2)) \
                or QGuiApplication.primaryScreen()
            groups.setdefault(sc, []).append(pet)
        for sc, group in groups.items():
            g = sc.availableGeometry()
            group.sort(key=lambda p: p.pet_id)
            for i, pet in enumerate(group):
                x = (g.left() + g.width() - pet.width() - 40
                     - i * (pet.width() + 10))
                y = g.top() + g.height() - pet.height() - 10
                x, y = pet.clamp_window_position(x, y, g)
                pet.move(x, y)
                pet.ground_y = y
        self.request_save()
        logging.info('复位位置')

    # ---------------- 托盘 ----------------
    def build_tray_menu(self):
        menu = QMenu()
        self.act_no_pets = QAction('ℹ️ 当前没有宠物（可添加一只）', menu)
        self.act_no_pets.setEnabled(False)
        menu.addAction(self.act_no_pets)
        self.act_show_all = menu.addAction('👀 显示/恢复全部宠物', self.show_all)
        self.act_add = menu.addAction('🐱 添加一只', self._add_new)
        self.act_all_dance = menu.addAction('💃 全部跳舞', self.all_dance)
        self.act_feed_all = menu.addAction('🍖 全部喂狗粮', self.feed_all)
        self.act_reset = menu.addAction('🏠 复位位置', self.reset_positions)
        menu.addSeparator()
        self.size_menu = menu.addMenu('大小（全部）')
        for key, name in [('small', '小'), ('medium', '中'), ('large', '大')]:
            act = QAction(name, self.size_menu)
            act.triggered.connect(lambda _=False, k=key: self._set_all_size(k))
            self.size_menu.addAction(act)
        self.size_menu.addAction('自定义大小…', self._set_all_custom_size)
        self.size_menu.addAction('恢复默认大小', lambda: self._set_all_scale(1.0))
        self.appearance_menu = menu.addMenu('形象（全部）')
        for key, name in APPEARANCE_NAMES.items():
            act = QAction(name, self.appearance_menu)
            act.triggered.connect(
                lambda _=False, k=key: self._set_all_appearance(k))
            self.appearance_menu.addAction(act)
        menu.addAction(self.act_speech)
        menu.addAction(self.act_adult_quotes)
        menu.addAction(self.act_quote_library)
        menu.addAction(self.act_top)
        menu.addAction(self.act_through)
        menu.addAction(self.act_hide)
        menu.addAction(self.act_autostart)
        menu.addSeparator()
        menu.addAction(self.act_hotkey_status)
        menu.addAction('⚙️ 设置（快捷键）', self.open_settings)
        menu.addSeparator()
        menu.addAction('🚪 退出', self.on_exit)
        self.tray.setContextMenu(menu)
        self.tray.show()
        self._update_pet_menu_state()

    def _update_pet_menu_state(self):
        """根据当前宠物数量更新托盘菜单，避免 0 只时出现无效操作。"""
        if not hasattr(self, 'act_no_pets'):
            return
        has_pets = bool(self.pets)
        self.act_no_pets.setVisible(not has_pets)
        self.act_show_all.setEnabled(has_pets)
        self.act_all_dance.setEnabled(has_pets)
        self.act_feed_all.setEnabled(has_pets)
        self.act_reset.setEnabled(has_pets)
        self.size_menu.setEnabled(has_pets)
        self.appearance_menu.setEnabled(has_pets)
        self.act_hide.setEnabled(has_pets)

    def _add_new(self):
        pet = self.add_pet(None)
        if not self.act_hide.isChecked():
            pet.show_and_front()

    def show_all(self):
        """清除隐藏状态，并将全部宠物恢复到当前可见浮动层。"""
        if not self.pets:
            logging.info('当前没有宠物，跳过显示/恢复')
            return
        if self.act_hide.isChecked():
            self.act_hide.setChecked(False)
        else:
            for pet in self.pets.values():
                pet.show_and_front()
        logging.info('显示/恢复全部宠物')

    def _set_all_size(self, key):
        for pet in self.pets.values():
            pet.set_size(key)

    def _set_all_scale(self, scale):
        for pet in self.pets.values():
            pet.set_scale(scale)
        self.request_save()

    def _set_all_appearance(self, appearance):
        self.cfg['appearance'] = appearance
        for pet in self.pets.values():
            pet.set_appearance(appearance)
        self.request_save()

    def _set_all_custom_size(self):
        original_scales = {pet_id: pet.scale
                           for pet_id, pet in self.pets.items()}
        current = next(iter(self.pets.values()), None)
        dialog = SizeDialog(
            current.scale if current else 1.0,
            on_preview=lambda scale: self._preview_all_scale(scale),
        )
        if current:
            dialog.place_beside(current)
        if dialog.exec() == DIALOG_ACCEPTED:
            self._set_all_scale(dialog.scale())
        else:
            for pet_id, scale in original_scales.items():
                pet = self.pets.get(pet_id)
                if pet:
                    pet.set_scale(scale, notify=False)

    def _preview_all_scale(self, scale):
        for pet in self.pets.values():
            pet.set_scale(scale, notify=False)

    def _on_speech(self, enabled):
        self.cfg['speech'] = enabled
        if not enabled:          # 关掉说话的瞬间把当前气泡也藏起来
            for pet in self.pets.values():
                pet.hide_bubble()
        self.request_save()

    def _on_adult_quotes(self, enabled):
        """切换高强度/普通模式；双模式共用语录在两种模式都保留。"""
        self.cfg['adult_quotes'] = enabled
        self.request_save()
        logging.info('成人语录: %s', enabled)

    def _on_always_on_top(self, enabled):
        self.cfg['always_on_top'] = enabled
        for pet in self.pets.values():
            pet.set_always_on_top(enabled, force_front=enabled)
        self.request_save()

    def _on_click_through(self, enabled):
        self.cfg['click_through'] = enabled
        for pet in self.pets.values():
            pet.set_click_through(enabled)
        if enabled:
            for pet in self.pets.values():
                pet.hide_bubble()
        self.request_save()

    def _on_autostart(self, enabled):
        config.set_autostart(enabled)
        self.request_save()

    def _on_hide(self, hidden):
        """隐藏全部宠物：窗口+气泡全藏，且禁言（不说话）"""
        for pet in self.pets.values():
            pet.set_hidden(hidden)
        if not hidden:
            for pet in self.pets.values():
                pet.show_and_front()
        self.request_save()
        logging.info('隐藏状态: %s', hidden)

    def on_hotkey_status(self, status):
        """将原生快捷键线程状态同步到菜单栏，避免用户误以为已注册。"""
        self._hotkey_status = f'⌨️ {status}'
        self.act_hotkey_status.setText(self._hotkey_status)
        logging.info('快捷键状态: %s', status)

    def open_settings(self):
        dlg = SettingsDialog(self.cfg)
        if dlg.exec() == DIALOG_ACCEPTED:
            self.cfg['hotkeys'] = dlg.values()
            config.save(self.cfg)
            self.hotkeys.register_all(self.cfg['hotkeys'])

    def open_quote_library(self):
        """打开语录库编辑器；保存后数据层会立即刷新所有抽取池。"""
        QuoteLibraryDialog().exec()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.cfg['click_through']:
                self.act_through.setChecked(False)
            if self.act_hide.isChecked():
                self.act_hide.setChecked(False)   # 触发 _on_hide 恢复显示

    # ---------------- 全局快捷键分发 ----------------
    def run_action(self, key):
        logging.info(f'快捷键触发: {key}')
        if key == 'dance':
            self.all_dance()
        elif key == 'feed':
            self.feed_all()
        elif key == 'reset':
            self.reset_positions()
        elif key == 'hide':
            self.act_hide.toggle()
        elif key == 'speech':
            self.act_speech.toggle()
        elif key == 'top':
            self.act_top.toggle()
        elif key == 'through':
            self.act_through.toggle()
        elif key == 'add':
            self._add_new()

    # ---------------- 整点彩蛋 ----------------
    def _hourly_egg(self):
        """小时变化时随机一只宠物说一句应景语录（原句逐字）"""
        now = datetime.now()
        if now.hour == self._last_egg_hour:
            return
        self._last_egg_hour = now.hour
        pets = [p for p in self.pets.values()
                if not p.suppressed and p.state != PetState.SLEEP]
        if not pets:
            return
        pet = random.choice(pets)
        text, emotion = hourly_egg_for(now.hour)
        pet.say(text, emotion=emotion_state(emotion))
        logging.info(f'整点彩蛋: {text}')

    # ---------------- 状态保存 ----------------
    def request_save(self):
        if not self._exiting:
            self.save_debounce.start()

    def save_state(self):
        self.cfg['pets'] = [
            {'id': pid, 'x': pet.x(), 'y': pet.y(), 'size': pet.size_key,
             'scale': pet.scale,
             'appearance': pet.appearance,
             'last_fed': pet.last_fed}
            for pid, pet in self.pets.items()
        ]
        config.save(self.cfg)

    def on_exit(self):
        """完整退出：守卫防重入（修复旧版递归退出导致段错误）"""
        if self._exiting:
            return
        self._exiting = True
        self.hotkeys.unregister_all()
        self.save_state()
        for pet in list(self.pets.values()):
            pet.close()
        self.tray.hide()
        logging.info('退出')
        self.app.quit()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('NANA DOG')
    app.setApplicationDisplayName('NANA DOG')
    app.setWindowIcon(QIcon(os.path.join(config.BASE_DIR, 'assets', ICON_FILE)))
    try:
        PetApp(app)
    except Exception:
        logging.exception('启动失败')
        raise
    sys.exit(app.exec())


if __name__ == '__main__':
    main()

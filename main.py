# -*- coding: utf-8 -*-
"""那艺娜小狗桌宠 - 入口：托盘图标 + 多只宠物管理 + 每日问候 + 全局快捷键"""
import logging
import os
import random
import sys
import time
from datetime import datetime

from qtcompat import (IS_WIN, IS_MAC, Qt, QTimer, QAbstractNativeEventFilter,
                      QPoint, QIcon, QAction, QKeySequence, QGuiApplication,
                      QApplication, QMenu, QSystemTrayIcon, QDialog,
                      QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                      QKeySequenceEdit, MODS, KEY, DIALOG_ACCEPTED)

import config
from mac_native import MacGlobalHotkeys
from pet import (PetWindow, PetState, hourly_egg_for, screen_geometry_for,
                 emotion_state)

ICON_FILE = 'icon.png' if IS_MAC else 'icon.ico'   # mac 不读 ico
if IS_WIN:
    import ctypes
    import ctypes.wintypes

LOG_DIR = os.path.join(config.DATA_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, 'app.log'),
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
)   # 3.8 兼容：basicConfig 不支持 encoding，日志文件默认本地编码（中文 Windows 为 GBK）

# 可绑快捷键的功能清单
ACTIONS = [
    ('dance', '💃 全部跳舞'),
    ('feed', '🍖 全部喂狗粮'),
    ('reset', '🏠 复位位置'),
    ('hide', '🙈 隐藏/显示'),
    ('speech', '💬 说话开关'),
    ('top', '📌 置顶开关'),
    ('through', '🖱 穿透开关'),
    ('add', '🐶 添加一只'),
]

MOD_CONTROL = 0x2
MOD_ALT = 0x1
MOD_SHIFT = 0x4
MOD_WIN = 0x8
WM_HOTKEY = 0x0312


def seq_to_vkmods(seq_str):
    """QKeySequence 字符串 → (Windows虚拟键码, 修饰键位掩码)；无法映射返回 (None, 0)"""
    if not seq_str:
        return None, 0
    ks = QKeySequence(seq_str)
    if ks.isEmpty():
        return None, 0
    combo = ks[0]
    kb = combo.keyboardModifiers()
    key = int(combo.key())
    mods = 0
    if kb & MODS.ControlModifier:
        mods |= MOD_CONTROL
    if kb & MODS.AltModifier:
        mods |= MOD_ALT
    if kb & MODS.ShiftModifier:
        mods |= MOD_SHIFT
    if kb & MODS.MetaModifier:
        mods |= MOD_WIN
    vk = None
    if KEY.Key_A.value <= key <= KEY.Key_Z.value:
        vk = ord('A') + (key - KEY.Key_A.value)
    elif KEY.Key_0.value <= key <= KEY.Key_9.value:
        vk = ord('0') + (key - KEY.Key_0.value)
    elif KEY.Key_F1.value <= key <= KEY.Key_F24.value:
        vk = 0x70 + (key - KEY.Key_F1.value)
    elif key == KEY.Key_Space.value:
        vk = 0x20
    return vk, mods


class GlobalHotkeys(QAbstractNativeEventFilter):
    """系统级全局快捷键。Windows: RegisterHotKey + WM_HOTKEY 原生事件过滤；
    macOS: Quartz CGEventTap（需要用户授予辅助功能/输入监控权限）。"""

    def __init__(self, app_owner):
        super().__init__()
        self.owner = app_owner
        self._ids = {}
        self._mac = MacGlobalHotkeys() if IS_MAC else None
        if IS_WIN:
            self._user32 = ctypes.windll.user32
            self._user32.RegisterHotKey.argtypes = [
                ctypes.c_void_p, ctypes.c_int, ctypes.c_uint, ctypes.c_uint]
            self._user32.RegisterHotKey.restype = ctypes.c_bool
            self._user32.UnregisterHotKey.argtypes = [ctypes.c_void_p, ctypes.c_int]
        if self._mac is not None and self._mac.available:
            self._mac.triggered.connect(self.owner.run_action)
            self._mac.status_changed.connect(self.owner.on_hotkey_status)

    def register_all(self, mapping):
        self.unregister_all()
        if IS_MAC:
            if not self._mac.available:
                self.owner.on_hotkey_status('原生快捷键模块不可用，请重新安装 macOS 依赖')
                return
            self._mac.register_all(mapping)
            return
        if not IS_WIN:
            return
        for i, (action, seq) in enumerate(mapping.items(), start=1):
            vk, mods = seq_to_vkmods(seq)
            if not vk or not mods:
                continue
            if self._user32.RegisterHotKey(None, i, mods, vk):
                self._ids[i] = action
        logging.info(f'全局快捷键注册: {list(self._ids.values())}')

    def unregister_all(self):
        if IS_MAC:
            self._mac.unregister_all()
            return
        if not IS_WIN:
            return
        for i in list(self._ids):
            self._user32.UnregisterHotKey(None, i)
        self._ids.clear()

    def nativeEventFilter(self, eventType, message):
        if IS_WIN and eventType == b'windows_generic_MSG':
            msg = ctypes.wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY and msg.wParam in self._ids:
                self.owner.run_action(self._ids[msg.wParam])
        return False, 0


class SettingsDialog(QDialog):
    """设置：所有功能自定义全局快捷键"""

    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.setWindowTitle('那艺娜小狗桌宠 - 设置')
        self.setWindowIcon(QIcon(os.path.join(config.BASE_DIR, 'assets', ICON_FILE)))
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)
        hint = ('macOS 全局快捷键需要在“系统设置 → 隐私与安全性 → 辅助功能/输入监控”中允许 NANA DOG。'
                if IS_MAC else
                '自定义全局快捷键（录制键位，Esc 可清空，保存后立即生效）')
        layout.addWidget(QLabel(hint))
        self.edits = {}
        hotkeys = cfg.get('hotkeys', {})
        for key, label in ACTIONS:
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            edit = QKeySequenceEdit()
            seq = hotkeys.get(key, '')
            edit.setKeySequence(QKeySequence(seq) if seq else QKeySequence())
            self.edits[key] = edit
            row.addWidget(edit, 1)
            layout.addLayout(row)
        btns = QHBoxLayout()
        btn_restore = QPushButton('恢复默认')
        btn_save = QPushButton('保存')
        btn_cancel = QPushButton('取消')
        btns.addWidget(btn_restore)
        btns.addStretch()
        btns.addWidget(btn_save)
        btns.addWidget(btn_cancel)
        layout.addLayout(btns)
        btn_restore.clicked.connect(self._restore)
        btn_save.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)

    def _restore(self):
        defaults = config.DEFAULT_CONFIG['hotkeys']
        for key, edit in self.edits.items():
            edit.setKeySequence(QKeySequence(defaults.get(key, '')))

    def values(self):
        return {key: edit.keySequence().toString() for key, edit in self.edits.items()}


class PetApp:
    def __init__(self, app):
        self.app = app
        app.setQuitOnLastWindowClosed(False)
        self.cfg = config.load()
        self.pets = {}
        self._exiting = False
        self._hotkey_status = '快捷键：初始化中'

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
        self.act_top = QAction('📌 置顶显示', checkable=True,
                               checked=self.cfg['always_on_top'])
        self.act_through = QAction('🖱 鼠标穿透（穿透后从托盘恢复）', checkable=True,
                                   checked=self.cfg['click_through'])
        self.act_autostart = QAction('🚀 开机自启', checkable=True,
                                     checked=config.get_autostart())
        self.act_hide = QAction('🙈 隐藏（点托盘恢复）', checkable=True, checked=False)
        self.act_speech.toggled.connect(self._on_speech)
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
        pet = PetWindow(pet_id, self.cfg, last_fed=last_fed,
                        on_remove=self.remove_pet, on_exit=self.on_exit)
        if saved:
            pet.size_key = saved.get('size', 'medium')
            pet.factor = config.SIZE_FACTOR[pet.size_key]
            pet.set_frame()
            # 多显示器：按存档坐标所在屏幕钳制，宠物留在原显示器
            screen = screen_geometry_for(
                QPoint(saved.get('x', 100) + pet.width() // 2,
                       saved.get('y', 100) + pet.height() // 2))
            x = max(screen.left(), min(saved.get('x', 100), screen.right() - pet.width()))
            y = max(screen.top(), min(saved.get('y', 100), screen.bottom() - pet.height()))
            pet.move(x, y)
            pet.ground_y = y
        else:
            screen = QApplication.primaryScreen().availableGeometry()
            pet.move(random.randint(screen.left() + 50,
                                    screen.right() - pet.width() - 50),
                     screen.bottom() - pet.height() - 30)
            pet.ground_y = pet.y()
        # 重启后恢复穿透设置（配置开启但进程重启后 window flag 会丢）
        if self.cfg.get('click_through'):
            pet.set_click_through(True)
        # 隐藏状态下新增的宠物保持隐藏，不突然冒出来
        if self.act_hide.isChecked():
            pet.set_hidden(True)
        self.pets[pet_id] = pet
        logging.info(f'添加宠物 #{pet_id}')
        return pet

    def remove_pet(self, pet_id):
        pet = self.pets.pop(pet_id, None)
        if pet:
            pet.close()
            pet.deleteLater()
            logging.info(f'移除宠物 #{pet_id}')
        if not self.pets:
            self.add_pet(None)

    def all_dance(self):
        for pet in self.pets.values():
            pet.wake_up()
            pet.set_state(PetState.DANCE, loops=2)

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
                x = g.right() - pet.width() - 40 - i * (pet.width() + 10)
                y = g.bottom() - pet.height() - 10
                pet.move(max(g.left() + 10, x), y)
                pet.ground_y = y
        logging.info('复位位置')

    # ---------------- 托盘 ----------------
    def build_tray_menu(self):
        menu = QMenu()
        menu.addAction('👀 显示/恢复全部宠物', self.show_all)
        menu.addAction('🐱 添加一只', self._add_new)
        menu.addAction('💃 全部跳舞', self.all_dance)
        menu.addAction('🍖 全部喂狗粮', self.feed_all)
        menu.addAction('🏠 复位位置', self.reset_positions)
        menu.addSeparator()
        size_menu = menu.addMenu('大小（全部）')
        for key, name in [('small', '小'), ('medium', '中'), ('large', '大')]:
            act = QAction(name, size_menu)
            act.triggered.connect(lambda _=False, k=key: self._set_all_size(k))
            size_menu.addAction(act)
        menu.addAction(self.act_speech)
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

    def _add_new(self):
        pet = self.add_pet(None)
        if not self.act_hide.isChecked():
            pet.show_and_front()

    def show_all(self):
        """清除隐藏状态，并将全部宠物恢复到当前可见浮动层。"""
        if self.act_hide.isChecked():
            self.act_hide.setChecked(False)
        else:
            for pet in self.pets.values():
                pet.show_and_front()
        logging.info('显示/恢复全部宠物')

    def _set_all_size(self, key):
        for pet in self.pets.values():
            pet.set_size(key)

    def _on_speech(self, enabled):
        self.cfg['speech'] = enabled
        if not enabled:          # 关掉说话的瞬间把当前气泡也藏起来
            for pet in self.pets.values():
                pet.hide_bubble()

    def _on_always_on_top(self, enabled):
        self.cfg['always_on_top'] = enabled
        for pet in self.pets.values():
            pet.set_always_on_top(enabled, force_front=enabled)

    def _on_click_through(self, enabled):
        self.cfg['click_through'] = enabled
        for pet in self.pets.values():
            pet.set_click_through(enabled)
        if enabled:
            for pet in self.pets.values():
                pet.hide_bubble()

    def _on_autostart(self, enabled):
        config.set_autostart(enabled)

    def _on_hide(self, hidden):
        """隐藏全部宠物：窗口+气泡全藏，且禁言（不说话）"""
        for pet in self.pets.values():
            pet.set_hidden(hidden)
        if not hidden:
            for pet in self.pets.values():
                pet.show_and_front()
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
    def save_state(self):
        self.cfg['pets'] = [
            {'id': pid, 'x': pet.x(), 'y': pet.y(), 'size': pet.size_key,
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

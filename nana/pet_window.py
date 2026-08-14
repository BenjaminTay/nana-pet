# -*- coding: utf-8 -*-
"""宠物窗口实现：动画、AI、交互、气泡同步和窗口层级。"""
import os
import random
import time
from datetime import datetime

from qtcompat import (IS_WIN, Qt, QTimer, QRectF, QPoint, QPixmap, QAction,
                      QTransform, QPainter, QPainterPath,
                      QColor, QPen, QFont, QFontMetrics, QWidget, QLabel,
                      QMenu, WT, WA, MOUSE_BTN, global_pos, RENDER_AA, PEN_NOPEN,
                      ALIGN_HC, ASPECT_KEEP, TRANS_SMOOTH, FONT_UI, MODS,
                      DIALOG_ACCEPTED)

import config
from mac_native import apply_window_level, show_and_front
from nana.bubble import Bubble
from nana.size_dialog import SizeDialog
from nana.pet_data import (
    ASSETS,
    CLICK_BAG,
    EMOTION_OF,
    FRAME_INTERVALS,
    GREET,
    HEAD,
    LINES,
    QUOTES,
    SIGNATURE,
    PetState,
    emotion_state,
    screen_geometry_for,
)
class PetWindow(QWidget):
    """一只娜娜小狗 = 一个透明窗口 + 独立AI + 情绪语录"""

    def __init__(self, pet_id, cfg, last_fed=None, on_remove=None,
                 on_exit=None, on_state_changed=None):
        super().__init__()
        self.pet_id = pet_id
        self.cfg = cfg
        self.on_remove = on_remove
        self.on_exit = on_exit
        self.on_state_changed = on_state_changed

        flags = (WT.FramelessWindowHint | WT.Tool)
        if self.cfg.get('always_on_top', True):
            flags |= WT.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(WA.WA_TranslucentBackground)
        # 显示时不抢占前台/不抢焦点，避免置顶切换瞬间弹到最前
        self.setAttribute(WA.WA_ShowWithoutActivating)
        self.setAcceptDrops(True)
        self.setWindowTitle(f'娜娜#{pet_id}')

        self.label = QLabel(self)
        self.label.setStyleSheet('background: transparent;')

        self.frames = {}
        self.load_frames()
        self._scaled_frame_cache = {}

        # 状态
        self.state = PetState.IDLE
        self.frame_idx = 0
        self.loops_left = 0
        self.facing = 1               # 1=朝右 -1=朝左
        self.size_key = 'medium'
        self.scale = 1.0              # 相对默认大小（中等大小）的比例
        self.factor = config.BASE_SIZE_FACTOR
        self.last_fed = last_fed if last_fed else time.time()

        # 物理
        self.speed = 0.0
        self.target_x = None
        self.vy = 0.0
        self.ground_y = 0
        self.vx = 0.0

        # 交互
        self.suppressed = False      # 隐藏状态：禁言+不弹气泡
        self._drag_offset = None
        self._pressed_pos = None
        self._picked = False
        self.last_interaction = time.time()
        self.click_times = []
        self._click_pending = False        # 单击延迟250ms，双击时取消（避免双击弹3条）
        self._click_timer = QTimer(self)
        self._click_timer.setSingleShot(True)
        self._click_timer.timeout.connect(self._handle_click)
        self._dbl_clicked = False          # 双击标记：双击后的 release 不再计点击
        self._long_petting = False         # 长按摸头中：持续冒爱心直到松手
        self._longpress_timer = QTimer(self)
        self._longpress_timer.setSingleShot(True)
        self._longpress_timer.timeout.connect(self._start_longpet)

        # 气泡
        self.bubble = Bubble(self.cfg.get('always_on_top', True))
        self._bubble_hide = QTimer(self)
        self._bubble_hide.setSingleShot(True)
        self._bubble_hide.timeout.connect(self.hide_bubble)
        self._bubble_sync = QTimer(self)          # 气泡持续跟随宠物
        self._bubble_sync.timeout.connect(self.update_bubble_pos)
        self._bubble_sync.start(100)

        # 定时器
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.next_frame)
        self.tick_timer = QTimer(self)
        self.tick_timer.timeout.connect(self.tick)
        self.ai_timer = QTimer(self)
        self.ai_timer.setSingleShot(True)
        self.ai_timer.timeout.connect(self.ai_decide)

        self.set_scale(self.scale, notify=False)
        self.set_state(PetState.IDLE)
        self.schedule_ai()
        self.tick_timer.start(16)
        self.show()
        # Qt 的 WindowStaysOnTopHint 在 macOS 上不足以跨应用/Space 保持层级，
        # 这里在原生窗口创建后同步到 NSWindow。
        apply_window_level(self, self.cfg.get('always_on_top', True))

    # ---------------- 资源 ----------------
    def load_frames(self):
        idle_frames = self._load_folder('idle')
        if not idle_frames:
            raise RuntimeError('assets/idle/ 下没有图片！请先运行 tools/gen_assets_nana.py')
        for s in PetState:
            frames = self._load_folder(s.value)
            self.frames[s.value] = frames if frames else idle_frames

    def _load_folder(self, name):
        folder = os.path.join(ASSETS, name)
        if not os.path.isdir(folder):
            return []
        files = sorted(f for f in os.listdir(folder)
                       if f.lower().startswith('frame_') and f.lower().endswith('.png'))
        return [QPixmap(os.path.join(folder, f)) for f in files]

    # ---------------- 渲染（含方向翻转） ----------------
    def set_frame(self):
        frames = self.frames[self.state.value]
        if not frames:
            return
        self.frame_idx %= len(frames)
        cache_key = (self.state.value, self.frame_idx, self.facing,
                     round(self.factor, 4))
        pm = self._scaled_frame_cache.get(cache_key)
        if pm is None:
            pm = frames[self.frame_idx]
            if self.facing < 0:
                pm = pm.transformed(QTransform().scale(-1, 1))
            pm = pm.scaled(int(pm.width() * self.factor),
                           int(pm.height() * self.factor),
                           ASPECT_KEEP, TRANS_SMOOTH)
            self._scaled_frame_cache[cache_key] = pm
        self.label.setPixmap(pm)
        self.label.resize(pm.size())
        self.resize(pm.size())

    def next_frame(self):
        frames = self.frames[self.state.value]
        self.frame_idx += 1
        if self.frame_idx >= len(frames):
            self.frame_idx = 0
            if self.loops_left > 0:
                self.loops_left -= 1
                if self.loops_left <= 0:
                    self.set_state(PetState.IDLE)
                    return
        self.set_frame()

    def set_state(self, state, loops=1):
        self.state = state
        self.frame_idx = 0
        self.loops_left = loops
        self.set_frame()
        if not self.suppressed:      # 隐藏时暂停动画（省CPU），恢复后继续
            self.anim_timer.start(FRAME_INTERVALS.get(state.value, 400))

    # ---------------- 说话（带情绪+跟随气泡） ----------------
    def say(self, text, emotion=None):
        if self.suppressed:        # 隐藏状态：不说话也不弹气泡
            return
        if emotion is not None and self.state != PetState.SLEEP:
            self.set_state(emotion, loops=2)
        if not self.cfg.get('speech', True):
            return
        self.bubble.set_text(text)
        self.bubble.show()
        self.update_bubble_pos()   # show 之后再定位，避免闪现旧位置
        apply_window_level(self.bubble, self.cfg.get('always_on_top', True))
        self._sync_bubble_z()      # 气泡Z序钉在宠物正上方，两层图层永远一致
        # 长句多留点时间看，最长8秒
        self._bubble_hide.start(min(8000, 3200 + len(text) * 25))

    def say_pool(self, key, emotion=None, chance=1.0):
        if random.random() < chance:
            self.say(QUOTES[key].next(), emotion)

    def hide_bubble(self):
        self.bubble.hide()
        self._bubble_hide.stop()

    def _sync_bubble_z(self):
        """原生 SetWindowPos 把气泡钉在宠物窗口正上方（Z序），
        关闭置顶时两者一起沉到前台窗口之下，不会气泡在最上、狗在后面。
        Windows 专属：macOS 没有 Z 带问题，跳过。"""
        if not IS_WIN:
            # macOS 通过 NSWindow level/collectionBehavior 保持气泡和宠物
            # 在同一浮动层；不调用 orderFront，避免说话时抢走用户焦点。
            apply_window_level(self, self.cfg.get('always_on_top', True))
            apply_window_level(self.bubble, self.cfg.get('always_on_top', True))
            return
        try:
            import ctypes
            ctypes.windll.user32.SetWindowPos(
                int(self.bubble.winId()), int(self.winId()),
                0, 0, 0, 0,
                0x0001 | 0x0002 | 0x0010)   # NOSIZE|NOMOVE|NOACTIVATE
        except Exception:
            pass

    def current_screen_geometry(self):
        """宠物中心所在的屏幕可用区域（多显示器支持）"""
        c = QPoint(self.x() + self.width() // 2, self.y() + self.height() // 2)
        return screen_geometry_for(c)

    def update_bubble_pos(self):
        """气泡始终锚定宠物头部上方，越界时翻到下方（朝向翻转时头部镜像）"""
        if not self.bubble.isVisible():
            return
        screen = self.current_screen_geometry()
        head_cx = int(self.width() * (HEAD[0] + HEAD[2]) / 2)
        if self.facing < 0:
            head_cx = self.width() - head_cx
        # 尾巴对准头中心：尾巴在气泡内的比例 = 头中心在宠物内的比例
        self.bubble.tail_frac = head_cx / max(self.width(), 1)
        bx = self.x() + head_cx - int(self.bubble.width() * self.bubble.tail_frac)
        by = self.y() - self.bubble.height() - 2
        self.bubble.tail_bottom = True
        if by < screen.top():
            by = self.y() + self.height() + 2
            self.bubble.tail_bottom = False
        bx = max(screen.left(), min(bx, screen.right() - self.bubble.width()))
        self.bubble.move(bx, by)
        self.bubble.update()

    # ---------------- AI ----------------
    def schedule_ai(self):
        if not self.suppressed:      # 隐藏时不调度AI
            self.ai_timer.start(random.randint(3000, 8000))

    def is_hungry(self):
        return time.time() - self.last_fed > self.cfg.get('hungry_hours', 3) * 3600

    def ai_decide(self):
        if self.suppressed or self._picked or self._drag_offset or self._long_petting:
            self.schedule_ai()
            return
        idle_sec = time.time() - self.last_interaction

        if idle_sec > 150 and self.state != PetState.SLEEP:
            self.set_state(PetState.SLEEP, loops=-1)
            self.say_pool('sleep', chance=0.5)
            self.schedule_ai()
            return
        if self.state == PetState.SLEEP:
            self.schedule_ai()
            return

        if self.is_hungry() and random.random() < 0.35:
            self.say_pool('hungry', emotion=PetState.ANGRY)
            self.schedule_ai()
            return

        if idle_sec < 60:
            choices = [PetState.WALK] * 4 + [PetState.RUN] * 2 + \
                      [PetState.JUMP] * 2 + [PetState.SIT] * 2 + \
                      [PetState.DANCE] * 1 + [PetState.SPIN] * 2 + \
                      [PetState.SING] * 2 + [PetState.IDLE] * 3
        else:
            choices = [PetState.IDLE] * 6 + [PetState.WALK] * 3 + \
                      [PetState.SIT] * 2 + [PetState.DANCE] * 1 + \
                      [PetState.SPIN] * 1 + [PetState.SING] * 1 + \
                      [PetState.SHY] * 1 + [PetState.SAD] * 1 + [PetState.CRY] * 1
        self.do_action(random.choice(choices))
        self.schedule_ai()

    def _walk_target_x(self):
        """散步/奔跑目标：65% 偏好屏幕左右边缘（像趴墙角），其余全屏随机"""
        screen = self.current_screen_geometry()
        margin = 8
        if random.random() < 0.65:
            return (screen.left() + margin if random.random() < 0.5
                    else screen.right() - self.width() - margin)
        return random.randint(screen.left() + 20, screen.right() - self.width() - 20)

    def do_action(self, action):
        screen = self.current_screen_geometry()
        if action == PetState.WALK:
            self.start_walk(self._walk_target_x(), speed=2.5)
            self.say_pool('walk', chance=0.3)
        elif action == PetState.RUN:
            self.start_walk(self._walk_target_x(), speed=6.0)
            self.say_pool('run', chance=0.35)
        elif action == PetState.JUMP:
            self.start_jump()
            self.say_pool('jump', chance=0.4)
        elif action == PetState.SIT:
            self.set_state(PetState.SIT, loops=random.randint(2, 5))
            self.say_pool('sit', chance=0.3)
        elif action == PetState.DANCE:
            self.set_state(PetState.DANCE, loops=2)
            self.say_pool('dance', chance=0.5)
        elif action == PetState.SPIN:
            self.set_state(PetState.SPIN, loops=random.randint(2, 4))
            self.say_pool('spin', chance=0.5)
        elif action == PetState.SING:
            self.set_state(PetState.SING, loops=random.randint(2, 3))
            self.say_pool('sing', chance=0.5)
        elif action == PetState.SHY:
            self.set_state(PetState.SHY, loops=random.randint(2, 3))
            self.say_pool('shy', chance=0.4)
        elif action == PetState.SAD:
            self.set_state(PetState.SAD, loops=random.randint(2, 3))
            self.say_pool('sad', chance=0.5)
        elif action == PetState.CRY:
            self.set_state(PetState.CRY, loops=random.randint(2, 3))
            self.say_pool('cry', chance=0.5)
        else:
            self.set_state(PetState.IDLE, loops=random.randint(2, 5))
            self.say_pool('idle', chance=0.25)

    # ---------------- 物理 ----------------
    def start_walk(self, target_x, speed):
        self.target_x = target_x
        self.speed = speed if target_x >= self.x() else -speed
        self.facing = 1 if self.speed > 0 else -1
        self.set_state(PetState.WALK if abs(speed) < 4 else PetState.RUN, loops=-1)

    def start_jump(self):
        self.ground_y = self.y()
        self.vy = -13.0
        self.vx = random.choice([-2.5, -1.0, 0, 1.0, 2.5])
        self.facing = 1 if self.vx >= 0 else -1
        self.set_state(PetState.JUMP, loops=-1)

    def tick(self):
        if self._picked:
            return
        s = self.state
        if s in (PetState.WALK, PetState.RUN):
            if self.target_x is not None:
                x = self.x() + self.speed
                if (self.speed > 0 and x >= self.target_x) or \
                   (self.speed < 0 and x <= self.target_x):
                    self.move(int(self.target_x), self.y())
                    self.target_x = None
                    self.set_state(PetState.IDLE, loops=random.randint(2, 5))
                else:
                    self.move(int(x), self.y())
        elif s == PetState.JUMP:
            self.vy += 0.9
            x = self.x() + self.vx
            y = self.y() + self.vy
            if y >= self.ground_y:
                y = self.ground_y
                self.vy = 0
                self.vx = 0
                self.set_state(PetState.IDLE, loops=random.randint(1, 3))
            screen = self.current_screen_geometry()
            x = max(screen.left(), min(x, screen.right() - self.width()))
            self.move(int(x), int(y))

    # ---------------- 鼠标交互 ----------------
    def is_head(self, pos):
        local = pos - self.pos()
        rx = local.x() / max(self.width(), 1)
        if self.facing < 0:        # 朝左时帧已镜像，头部坐标同步镜像
            rx = 1.0 - rx
        ry = local.y() / max(self.height(), 1)
        return HEAD[0] <= rx <= HEAD[2] and HEAD[1] <= ry <= HEAD[3]

    def mousePressEvent(self, e):
        self.last_interaction = time.time()
        self._pressed_pos = global_pos(e)
        self._dbl_clicked = False
        if e.button() == MOUSE_BTN.LeftButton:
            self._drag_offset = global_pos(e) - self.pos()
            if self.is_head(global_pos(e)):     # 按住头1秒 → 连续摸头冒爱心
                self._longpress_timer.start(1000)
        elif e.button() == MOUSE_BTN.RightButton:
            self.show_pet_menu(global_pos(e))

    def mouseMoveEvent(self, e):
        if self._drag_offset is not None:
            moved = (global_pos(e) - self._pressed_pos).manhattanLength()
            if moved > 8 and not self._picked:
                self._picked = True
                self._longpress_timer.stop()
                if self._long_petting:      # 长按摸头中途变拖拽：结束摸头
                    self._long_petting = False
                    self.set_state(PetState.IDLE, loops=2)
                self.hide_bubble()
                self.say_pool('pickup', chance=0.6)
            if self._picked:
                self.move(global_pos(e) - self._drag_offset)

    def mouseReleaseEvent(self, e):
        if e.button() != MOUSE_BTN.LeftButton:
            return
        was_picked = self._picked
        self._drag_offset = None
        self._picked = False
        self._longpress_timer.stop()
        if self._long_petting:              # 长按摸头结束：不算点击，恢复待机
            self._long_petting = False
            self.set_state(PetState.IDLE, loops=2)
            return
        if self._dbl_clicked:               # 双击后的 release 不再计一次点击
            self._dbl_clicked = False
            return
        if was_picked:
            screen = self.current_screen_geometry()
            x = max(screen.left(), min(self.x(), screen.right() - self.width()))
            y = max(screen.top(), min(self.y(), screen.bottom() - self.height()))
            self.move(x, y)
            self.ground_y = y
            self._state_changed()
            return
        # 连点时间戳立即记录（快速连点不能被延迟合并）；说话延迟250ms，
        # 若期间发生双击则取消，避免双击连弹3条
        self.click_times.append(time.time())
        self._click_pos = global_pos(e)
        self._click_pending = True
        self._click_timer.start(250)

    def _handle_click(self):
        if not self._click_pending:
            return
        self._click_pending = False
        self.wake_up()
        now = time.time()
        self.click_times = [t for t in self.click_times if now - t < 5]
        if len(self.click_times) >= 6:
            self.click_times.clear()
            self.say(QUOTES['angry'].next(), emotion=PetState.ANGRY)
            return
        if len(self.click_times) >= 3:
            self.say(QUOTES['happy'].next(), emotion=PetState.HAPPY)
            return
        if self.is_head(self._click_pos):
            self.set_state(PetState.HAPPY, loops=2)
            self.say_pool('pet', chance=0.7)
        else:
            # 身体点击：100句全量随机，表情随语录情绪走（喜怒哀乐悲都会出现）
            q = CLICK_BAG.next()
            self.say(q, emotion=emotion_state(EMOTION_OF[q]))

    def mouseDoubleClickEvent(self, e):
        self.last_interaction = time.time()
        self._click_pending = False     # 取消未处理的单击
        self._click_timer.stop()
        self._longpress_timer.stop()
        self.click_times.clear()        # 双击不计入连点，避免污染后续判定
        self._dbl_clicked = True        # 本次双击的 release 不再计一次点击
        self.wake_up()
        self.say(QUOTES['happy'].next(), emotion=PetState.HAPPY)

    def _start_longpet(self):
        """按住头部≥1秒：进入连续摸头（持续冒爱心直到松手）"""
        self._click_pending = False
        self._click_timer.stop()
        self.click_times.clear()
        self._long_petting = True
        self.wake_up()
        self.set_state(PetState.HAPPY, loops=-1)     # 循环爱心帧
        self.say(QUOTES['happy'].next())             # 不传emotion，避免覆盖loops=-1

    def wake_up(self):
        if self.state == PetState.SLEEP:
            self.set_state(PetState.DANCE, loops=2)
            if random.random() < 0.5:
                self.say(SIGNATURE)

    # ---------------- 喂食 ----------------
    def feed(self):
        self.last_interaction = time.time()
        self.last_fed = time.time()
        self.wake_up()
        self.set_state(PetState.EAT, loops=3)
        self.say_pool('eat', chance=0.7)

    # ---------------- 拖文件到身上（=把头像P到狗身上！） ----------------
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self.last_interaction = time.time()

    def dropEvent(self, e):
        if e.mimeData().hasUrls():
            self.last_interaction = time.time()
            self.wake_up()
            self.say(LINES[29], emotion=PetState.ANGRY)   # 第30句原句

    # ---------------- 右键菜单 ----------------
    def show_pet_menu(self, global_pos):
        menu = QMenu(self)
        menu.addAction('🍖 喂狗粮', self.feed)
        menu.addAction('💃 跳舞', lambda: (self.wake_up(),
                                          self.set_state(PetState.DANCE, loops=2)))
        menu.addAction('🐾 坐下', lambda: self.set_state(PetState.SIT, loops=3))
        menu.addAction('💤 睡觉', lambda: self.set_state(PetState.SLEEP, loops=-1))
        menu.addSeparator()
        size_menu = menu.addMenu('大小')
        for key, name in [('small', '小'), ('medium', '中'), ('large', '大')]:
            act = QAction(name, size_menu, checkable=True,
                          checked=config.is_preset_scale(self.scale, key))
            act.triggered.connect(lambda _=False, k=key: self.set_size(k))
            size_menu.addAction(act)
        size_menu.addSeparator()
        size_menu.addAction(f'当前大小：{round(self.scale * 100)}%',
                            lambda: None).setEnabled(False)
        size_menu.addAction('自定义大小…', self.open_size_dialog)
        menu.addSeparator()
        menu.addAction('❌ 移除这一只', lambda: self._safe(self.on_remove, self.pet_id))
        menu.addAction('🚪 退出程序', lambda: self._safe(self.on_exit))
        menu.exec(global_pos)

    @staticmethod
    def _safe(fn, *args):
        if fn:
            fn(*args)

    # ---------------- 隐藏（全部隐藏：窗口+气泡+禁言） ----------------
    def set_hidden(self, hidden):
        self.suppressed = hidden
        if hidden:
            self.hide_bubble()
            self.hide()
            # 暂停AI与动画：省CPU，恢复时位置/状态原样继续
            self.anim_timer.stop()
            self.tick_timer.stop()
            self.ai_timer.stop()
            self._bubble_sync.stop()
            self._longpress_timer.stop()
            self._long_petting = False
        else:
            self.show()
            apply_window_level(self, self.cfg.get('always_on_top', True))
            self.set_frame()
            self.anim_timer.start(FRAME_INTERVALS.get(self.state.value, 400))
            self.tick_timer.start(16)
            self._bubble_sync.start(100)
            self.schedule_ai()

    # ---------------- 大小 / 置顶 ----------------
    def set_size(self, key):
        self.set_scale(config.scale_for_size(key))

    def set_scale(self, scale, notify=True):
        """设置精确比例，保持宠物脚部锚点并同步气泡位置。"""
        scale = config.clamp_scale(scale)
        old_width = max(self.width(), 1)
        old_height = max(self.height(), 1)
        old_center_x = self.x() + old_width / 2
        old_bottom_y = self.y() + old_height
        old_ground_bottom = self.ground_y + old_height

        self.scale = scale
        self.factor = config.BASE_SIZE_FACTOR * scale
        self.size_key = config.size_key_for_scale(scale)
        self._scaled_frame_cache.clear()
        self.set_frame()

        x = round(old_center_x - self.width() / 2)
        y = round(old_bottom_y - self.height())
        screen = self.current_screen_geometry()
        x = max(screen.left(), min(x, screen.right() - self.width()))
        y = max(screen.top(), min(y, screen.bottom() - self.height()))
        self.move(x, y)
        self.ground_y = max(screen.top(), min(
            round(old_ground_bottom - self.height()),
            screen.bottom() - self.height()))
        self.update_bubble_pos()
        if notify:
            self._state_changed()

    def open_size_dialog(self):
        original_scale = self.scale
        dialog = SizeDialog(
            self.scale,
            on_preview=lambda scale: self.set_scale(scale, notify=False),
            parent=self,
        )
        dialog.place_beside(self)
        if dialog.exec() == DIALOG_ACCEPTED:
            self.set_scale(dialog.scale())
        else:
            self.set_scale(original_scale, notify=False)

    def wheelEvent(self, e):
        """Option/Alt + 滚轮缩放，避免普通滚轮误触。"""
        if e.modifiers() & MODS.AltModifier:
            delta = e.angleDelta().y()
            if delta:
                direction = 1 if delta > 0 else -1
                self.set_scale(self.scale + direction * config.SCALE_STEP)
                e.accept()
                return
        e.ignore()

    def _state_changed(self):
        if self.on_state_changed:
            self.on_state_changed()

    def set_always_on_top(self, enabled, force_front=False):
        self.setWindowFlag(WT.WindowStaysOnTopHint, enabled)
        if not self.suppressed:
            self.show()
            apply_window_level(self, enabled, force_front=force_front)
        if self.bubble is not None:
            bubble_was_visible = self.bubble.isVisible()
            self.bubble.setWindowFlag(WT.WindowStaysOnTopHint, enabled)
            if bubble_was_visible:
                self.bubble.show()
                apply_window_level(self.bubble, enabled, force_front=force_front)

    def set_click_through(self, enabled):
        """穿透状态同步到气泡：宠物可点透时气泡也必须可点透，图层行为一致"""
        self.setWindowFlag(WT.WindowTransparentForInput, enabled)
        if not self.suppressed:
            self.show()
            apply_window_level(self, self.cfg.get('always_on_top', True))
        if self.bubble is not None:
            self.bubble.setWindowFlag(WT.WindowTransparentForInput,
                                      enabled)
            if self.bubble.isVisible():
                self.bubble.show()   # setWindowFlag 会隐藏，重新show让flag生效
                apply_window_level(self.bubble, self.cfg.get('always_on_top', True))

    def show_and_front(self):
        """用户主动恢复宠物时清除隐藏状态并置于可见浮动层。"""
        if self.suppressed:
            self.set_hidden(False)
        else:
            self.show()
        show_and_front(self, self.cfg.get('always_on_top', True))
        if self.bubble.isVisible():
            show_and_front(self.bubble, self.cfg.get('always_on_top', True))

    # ---------------- 问候（时间感知，原句） ----------------
    def greet(self):
        h = datetime.now().hour
        if 5 <= h < 11:
            self.say(GREET['morning'])
        elif 11 <= h < 13:
            self.say(GREET['noon'])
        elif 13 <= h < 18:
            self.say(GREET['noon'])
        elif 18 <= h < 23:
            self.say(GREET['evening'])
        else:
            self.say(GREET['night'])
        if random.random() < 0.5:
            self.set_state(PetState.HAPPY, loops=2)

    # ---------------- 生命周期 ----------------
    def closeEvent(self, e):
        self.hide_bubble()
        super().closeEvent(e)

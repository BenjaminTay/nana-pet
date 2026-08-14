# -*- coding: utf-8 -*-
"""那艺娜小狗桌宠：语录情绪联动 + 摸头 + 喂狗粮饥饿系统 + 方向翻转 + 手绘气泡"""
import json
import os
import random
import re
import time
from datetime import datetime
from enum import Enum

from qtcompat import (IS_WIN, Qt, QTimer, QRectF, QPoint, QPixmap, QAction,
                      QGuiApplication, QTransform, QPainter, QPainterPath,
                      QColor, QPen, QFont, QFontMetrics, QWidget, QLabel,
                      QMenu, WT, WA, MOUSE_BTN, global_pos, RENDER_AA, PEN_NOPEN,
                      ALIGN_HC, ASPECT_KEEP, TRANS_SMOOTH, FONT_UI)

from config import SIZE_FACTOR, BASE_DIR
from mac_native import apply_window_level, show_and_front

ASSETS = os.path.join(BASE_DIR, 'assets')

# 头部区域（摸头判定），从 head.json 加载
HEAD = [0.45, 0.0, 1.0, 0.45]
try:
    with open(os.path.join(ASSETS, 'head.json'), encoding='utf-8') as f:
        HEAD = json.load(f)['head']
except Exception:
    pass


# ---------------- 语录：从用户提供的文件逐字加载 ----------------
def load_quotes():
    """解析 quotes.txt（'N. 内容' 格式），保持原句一字不差"""
    path = os.path.join(ASSETS, 'quotes.txt')
    lines = []
    try:
        with open(path, encoding='utf-8-sig') as f:
            for raw in f:
                raw = raw.strip()
                if not raw:
                    continue
                m = re.match(r'^\d+\.\s*(.+)$', raw)
                lines.append(m.group(1) if m else raw)
    except Exception:
        pass
    return lines


LINES = load_quotes()
if not LINES:
    raise RuntimeError('assets/quotes.txt 缺失或为空')


def L(*nums):
    """按行号取原句（1-based）"""
    return [LINES[n - 1] for n in nums]


class QuoteBag:
    """防重复语录袋：整袋顺序抽完再洗牌，且新一轮首句不与上一轮尾句重复"""

    def __init__(self, quotes):
        self.quotes = list(quotes)
        self._bag = []
        self._last = None

    def next(self):
        if not self.quotes:
            return ''
        if not self._bag:
            self._bag = self.quotes[:]
            random.shuffle(self._bag)
            if len(self._bag) > 1 and self._bag[0] == self._last:
                self._bag[0], self._bag[-1] = self._bag[-1], self._bag[0]
        self._last = self._bag.pop()
        return self._last


QUOTES = {
    # 喜怒哀乐悲五情（每句按语境配表情）
    'angry': QuoteBag(L(6, 7, 8, 10, 12, 14, 15, 17, 18, 19, 20, 21, 23, 24,
                       25, 26, 30, 38, 45, 46, 47, 51, 54, 57, 62, 63, 64, 72,
                       73, 78, 82, 86, 93, 98)),
    'cry': QuoteBag(L(11, 27, 29, 52, 59, 92)),
    'sad': QuoteBag(L(9, 22, 28, 31, 32, 33, 53, 55, 58, 65, 67, 69, 70, 71,
                      76, 77, 83, 91, 100)),
    'happy': QuoteBag(L(1, 2, 3, 36, 39, 40, 41, 42, 49, 66, 79, 80, 81, 94,
                        97)),
    'dance': QuoteBag(L(5, 13, 34, 37, 48, 50)),
    'sing': QuoteBag(L(43, 44)),
    'jump': QuoteBag(L(16)),
    'idle': QuoteBag(L(4, 35, 56, 60, 61, 68, 69, 74, 75, 84, 85, 87, 88, 89,
                       90, 95, 96, 99)),
    # 场景袋（AI动作/交互触发）
    'walk': QuoteBag(L(35, 60, 84, 87)),
    'run': QuoteBag(L(12, 57)),
    'sit': QuoteBag(L(33, 36, 41, 66)),
    'sleep': QuoteBag(L(41)),
    'eat': QuoteBag(L(36, 41, 68)),
    'hungry': QuoteBag(L(69, 70)),
    'pet': QuoteBag(L(39, 42, 80, 94)),
    'pickup': QuoteBag(L(23, 72)),
    'spin': QuoteBag(L(34, 37)),
    'shy': QuoteBag(L(32, 33)),
}
SIGNATURE = LINES[15]   # 第16句：我可不是娇滴滴的女王……
GREET = {'morning': LINES[0], 'noon': LINES[38], 'evening': LINES[40], 'night': LINES[40]}

# 语录→主情绪：怒/悲/哀优先注册（同一句在多个袋时取最强烈的情绪）
_EMOTION_PRIORITY = ['angry', 'cry', 'sad', 'happy', 'dance', 'sing', 'pet',
                     'hungry', 'walk', 'run', 'jump', 'sit', 'idle', 'eat',
                     'sleep', 'pickup', 'spin', 'shy']
EMOTION_OF = {}
for _key in _EMOTION_PRIORITY:
    for _q in QUOTES[_key].quotes:
        if _q not in EMOTION_OF:
            EMOTION_OF[_q] = _key

# 点击语录全局袋：61句全量随机（防重复），表情随语录情绪走
CLICK_BAG = QuoteBag(list(EMOTION_OF.keys()))

# 非PetState的情绪键 → 状态映射
_STATE_OF_EMOTION = {'hungry': 'ANGRY', 'pickup': 'ANGRY', 'sleep': 'SLEEP',
                     'pet': 'HAPPY', 'eat': 'EAT'}

# 整点彩蛋语录袋（每小时一次）：按时间段配语境，原句逐字
HOURLY_QUOTES = {
    'morning': QuoteBag(L(1, 60, 36)),
    'noon': QuoteBag(L(68, 69, 70)),
    'afternoon': QuoteBag(L(36, 56, 79)),
    'evening': QuoteBag(L(5, 39, 41)),
    'night': QuoteBag(L(41, 40, 33)),
}


def hourly_egg_for(hour):
    """整点彩蛋：按小时返回(原句, 情绪键)"""
    if 6 <= hour < 11:
        key = 'morning'
    elif 11 <= hour < 14:
        key = 'noon'
    elif 14 <= hour < 18:
        key = 'afternoon'
    elif 18 <= hour < 23:
        key = 'evening'
    else:
        key = 'night'
    q = HOURLY_QUOTES[key].next()
    return q, EMOTION_OF[q]


def emotion_state(key):
    """情绪键 → PetState"""
    if key in _STATE_OF_EMOTION:
        key = _STATE_OF_EMOTION[key]
    try:
        return PetState[key.upper()]
    except KeyError:
        return PetState.IDLE

FRAME_INTERVALS = {
    'idle': 420, 'walk': 110, 'run': 80, 'jump': 130, 'sit': 450,
    'sleep': 650, 'dance': 120, 'eat': 170, 'happy': 130, 'angry': 180,
    'sad': 380, 'cry': 340, 'spin': 80, 'sing': 160, 'shy': 320,
}


def screen_geometry_for(global_pos):
    """global_pos 所在屏幕的可用区域（多显示器）；不在任何屏幕上时回退主屏"""
    sc = QGuiApplication.screenAt(global_pos)
    if sc is None:
        sc = QGuiApplication.primaryScreen()
    return sc.availableGeometry()


class PetState(Enum):
    IDLE = 'idle'
    WALK = 'walk'
    RUN = 'run'
    JUMP = 'jump'
    SIT = 'sit'
    SLEEP = 'sleep'
    DANCE = 'dance'
    EAT = 'eat'
    HAPPY = 'happy'
    ANGRY = 'angry'
    SAD = 'sad'          # 哀
    CRY = 'cry'          # 悲
    SPIN = 'spin'        # 转圈
    SING = 'sing'        # 唱歌
    SHY = 'shy'          # 害羞


class Bubble(QWidget):
    """手绘对话气泡：圆角矩形+小尾巴+柔和阴影，尾巴指向宠物头部"""

    def __init__(self, always_on_top=True):
        flags = WT.Tool | WT.FramelessWindowHint
        if always_on_top:
            flags |= WT.WindowStaysOnTopHint
        super().__init__(None, flags)
        self.setAttribute(WA.WA_TranslucentBackground)
        # 显示时不抢占 Z 序最前/不抢焦点（SW_SHOWNA）：
        # 关闭置顶后气泡就不会浮到前台窗口上面，和宠物图层保持一致
        self.setAttribute(WA.WA_ShowWithoutActivating)
        self._lines = []
        self.tail_bottom = True      # True=尾巴朝下（气泡在宠物上方）
        self.tail_frac = 0.5         # 尾巴水平位置比例（对准宠物头中心）
        self._font = QFont(FONT_UI, 10)

    def set_text(self, text):
        fm = QFontMetrics(self._font)
        max_w = 280
        self._lines = []
        cur = ''
        for ch in text:
            if fm.horizontalAdvance(cur + ch) > max_w:
                self._lines.append(cur)
                cur = ch
            else:
                cur += ch
        self._lines.append(cur)
        line_h = fm.height() + 3
        w = max(fm.horizontalAdvance(l) for l in self._lines) + 38
        h = line_h * len(self._lines) + 22 + 10   # +10 尾巴
        self.resize(w, h)
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(RENDER_AA)
        w, h = self.width(), self.height()
        tail = 10
        if self.tail_bottom:
            body = QRectF(0, 0, w, h - tail)
        else:
            body = QRectF(0, tail, w, h - tail)
        # 阴影
        p.setPen(PEN_NOPEN)
        p.setBrush(QColor(0, 0, 0, 36))
        p.drawRoundedRect(body.translated(0, 2), 13, 13)
        # 主体+尾巴
        path = QPainterPath()
        path.addRoundedRect(body, 13, 13)
        cx = max(15.0, min(w - 15.0, w * self.tail_frac))
        if self.tail_bottom:
            path.moveTo(cx - 9, h - tail + 2)
            path.lineTo(cx, h)
            path.lineTo(cx + 9, h - tail + 2)
        else:
            path.moveTo(cx - 9, tail - 2)
            path.lineTo(cx, 0)
            path.lineTo(cx + 9, tail - 2)
        path.closeSubpath()
        p.setBrush(QColor(255, 251, 243, 249))
        p.setPen(QPen(QColor(238, 158, 108), 1.5))
        p.drawPath(path)
        # 文字
        p.setPen(QColor(107, 68, 35))
        p.setFont(self._font)
        fm = QFontMetrics(self._font)
        y0 = (tail if not self.tail_bottom else 0) + 8
        y = y0 + fm.ascent()
        for line in self._lines:
            p.drawText(QRectF(10, y - fm.ascent(), w - 20, fm.height() + 4),
                       ALIGN_HC, line)
            y += fm.height() + 3
        p.end()


class PetWindow(QWidget):
    """一只娜娜小狗 = 一个透明窗口 + 独立AI + 情绪语录"""

    def __init__(self, pet_id, cfg, last_fed=None, on_remove=None, on_exit=None):
        super().__init__()
        self.pet_id = pet_id
        self.cfg = cfg
        self.on_remove = on_remove
        self.on_exit = on_exit

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

        # 状态
        self.state = PetState.IDLE
        self.frame_idx = 0
        self.loops_left = 0
        self.facing = 1               # 1=朝右 -1=朝左
        self.size_key = 'medium'
        self.factor = SIZE_FACTOR['medium']
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

        self.set_size(self.size_key)
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
        pm = frames[self.frame_idx]
        if self.facing < 0:
            pm = pm.transformed(QTransform().scale(-1, 1))
        pm = pm.scaled(int(pm.width() * self.factor), int(pm.height() * self.factor),
                       ASPECT_KEEP,
                       TRANS_SMOOTH)
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
                          checked=(self.size_key == key))
            act.triggered.connect(lambda _=False, k=key: self.set_size(k))
            size_menu.addAction(act)
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
        self.size_key = key
        self.factor = SIZE_FACTOR[key]
        self.set_frame()
        # 变大后可能超出屏幕，钳制回所在屏幕可视区（多显示器）
        screen = self.current_screen_geometry()
        self.move(max(screen.left(), min(self.x(), screen.right() - self.width())),
                  max(screen.top(), min(self.y(), screen.bottom() - self.height())))

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

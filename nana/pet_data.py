# -*- coding: utf-8 -*-
"""宠物数据层：素材、语录、状态和屏幕几何辅助。"""
import json
import os
import random
import re
from enum import Enum

from qtcompat import QGuiApplication
from config import BASE_DIR
ASSETS = os.path.join(BASE_DIR, 'assets')
SKINS_DIR = os.path.join(ASSETS, 'skins')
APPEARANCE_NAMES = {
    'classic': '经典高清版',
    'q': 'Q版',
}
DEFAULT_APPEARANCE = 'classic'

# 头部区域（摸头判定），从 head.json 加载
HEAD = [0.45, 0.0, 1.0, 0.45]
try:
    with open(os.path.join(ASSETS, 'head.json'), encoding='utf-8') as f:
        HEAD = json.load(f)['head']
except Exception:
    pass


def normalize_appearance(value):
    """将配置中的形象名称限制在已支持的皮肤范围内。"""
    value = str(value or DEFAULT_APPEARANCE).lower().strip()
    return value if value in APPEARANCE_NAMES else DEFAULT_APPEARANCE


def assets_for_appearance(appearance):
    """返回形象素材根目录；缺少皮肤时回退到旧版 assets/。"""
    key = normalize_appearance(appearance)
    skin_root = os.path.join(SKINS_DIR, key)
    if os.path.isdir(os.path.join(skin_root, 'idle')):
        return skin_root
    return ASSETS


def head_for_appearance(appearance):
    """读取对应皮肤的摸头区域，旧素材或缺失文件时回退旧值。"""
    root = assets_for_appearance(appearance)
    try:
        with open(os.path.join(root, 'head.json'), encoding='utf-8') as f:
            return json.load(f)['head']
    except Exception:
        return list(HEAD)


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
    # 18/21/26/45 的素材已由补充语录中的更完整直播版本承接，不再重复抽取。
    'angry': QuoteBag(L(6, 7, 8, 10, 12, 14, 15, 17, 19, 20, 23, 24,
                       25, 30, 38, 46, 47, 51, 54, 57, 62, 63, 64, 72,
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

# 成人语录：保留直播录屏中的口音、错别字和破防表达，不改写原句。
# “成人”是内容开关，不是情绪；这里仍按情绪分组，让气泡出现时能同步表情。
ADULT_QUOTE_GROUPS = {
    'idle': L(101, 107, 110, 118),
    'happy': L(102, 103),
    'sing': L(104, 105),
    'angry': L(106, 108, 109, 111, 112, 113, 114, 115, 116, 117, 119),
}
ADULT_QUOTES = {
    key: QuoteBag(lines) for key, lines in ADULT_QUOTE_GROUPS.items()
}

# 成人模式下，动作语录仍按原来的场景选择，只是场景袋会并入成人语录。
QUOTES_WITH_ADULT = {
    key: QuoteBag(QUOTES[key].quotes + ADULT_QUOTE_GROUPS.get(key, []))
    for key in QUOTES
}


def quote_bag(key, adult=False):
    """按内容模式返回场景语录袋；成人模式保留普通语录并追加成人语录。"""
    return QUOTES_WITH_ADULT[key] if adult else QUOTES[key]


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

# 身体点击的全局随机池：成人模式下追加成人语录，并沿用对应情绪。
ADULT_EMOTION_OF = {}
for _key, _quotes in ADULT_QUOTE_GROUPS.items():
    for _q in _quotes:
        ADULT_EMOTION_OF[_q] = _key
EMOTION_OF_WITH_ADULT = dict(EMOTION_OF)
EMOTION_OF_WITH_ADULT.update(ADULT_EMOTION_OF)
CLICK_BAG_WITH_ADULT = QuoteBag(list(EMOTION_OF_WITH_ADULT.keys()))

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

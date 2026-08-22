# -*- coding: utf-8 -*-
"""宠物数据层：素材、语录、状态和屏幕几何辅助。"""
import json
import os
import random
import re
from enum import Enum

from qtcompat import QGuiApplication
import config
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
    """返回形象对应的正式运行时素材根目录。"""
    key = normalize_appearance(appearance)
    skin_root = os.path.join(SKINS_DIR, key)
    if not os.path.isdir(os.path.join(skin_root, 'idle')):
        relative_root = os.path.relpath(skin_root, BASE_DIR)
        raise RuntimeError(
            f'缺少 {relative_root}/idle/ 运行时素材，请先生成或恢复对应皮肤资源。')
    return skin_root


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

# ---------------- 语录内容分类 ----------------
# 三类不是互斥的“两个池子”：
# - adult-only：只在成人模式出现，保留高冲击、明显越界的内容；
# - normal-only：只在普通模式出现，保留纯日常、正向和安抚类内容；
# - common：两种模式都可以出现，包含身份介绍、音乐内容和轻度冲突表达。
#
# 分类结果由语录审阅表同步而来。后续用户可以在语录库编辑器中直接调整，
# 这里的编号只作为首次启动时的内置默认值。
NORMAL_ONLY_QUOTE_IDS = (
    1, 3, 5, 9, 11, 12, 13, 14, 15, 22, 28, 34, 35, 36, 39, 40, 41, 42,
    49, 50, 51, 56, 57, 58, 59, 60, 65, 66, 67, 68, 69, 70, 74, 75,
    76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91,
    92, 94, 95, 96, 97, 99, 102, 105, 118,
)
ADULT_ONLY_QUOTE_IDS = (
    18, 19, 20, 21, 27, 103, 104, 106, 108, 109, 110, 111, 112, 113,
    114, 115, 116, 117, 119,
)
_NORMAL_ONLY_QUOTE_ID_SET = set(NORMAL_ONLY_QUOTE_IDS)
_ADULT_ONLY_QUOTE_ID_SET = set(ADULT_ONLY_QUOTE_IDS)
_ALL_QUOTE_IDS = tuple(range(1, len(LINES) + 1))
COMMON_QUOTE_IDS = tuple(
    number for number in _ALL_QUOTE_IDS
    if number not in _NORMAL_ONLY_QUOTE_ID_SET
    and number not in _ADULT_ONLY_QUOTE_ID_SET
)

COMMON_QUOTE_LINES = set(L(*COMMON_QUOTE_IDS))
ADULT_ONLY_QUOTE_LINES = set(L(*ADULT_ONLY_QUOTE_IDS))
NORMAL_ONLY_QUOTE_LINES = set(L(*NORMAL_ONLY_QUOTE_IDS))
QUOTE_CATEGORY_OF = {
    quote: 'common' for quote in COMMON_QUOTE_LINES
}
QUOTE_CATEGORY_OF.update({
    quote: 'adult-only' for quote in ADULT_ONLY_QUOTE_LINES
})
QUOTE_CATEGORY_OF.update({
    quote: 'normal-only' for quote in NORMAL_ONLY_QUOTE_LINES
})
ADULT_MODE_QUOTE_LINES = COMMON_QUOTE_LINES | ADULT_ONLY_QUOTE_LINES
NORMAL_MODE_QUOTE_LINES = COMMON_QUOTE_LINES | NORMAL_ONLY_QUOTE_LINES

# 追加语录原始分组：分类与情绪/场景分开维护。
# 语录库编辑器会将 scene 作为可调整字段；这里保留旧分组作为内置默认值。
SUPPLEMENTAL_QUOTE_GROUPS = {
    'idle': L(101, 107, 110, 118),
    'happy': L(102, 103),
    'sing': L(104, 105),
    'angry': L(106, 108, 109, 111, 112, 113, 114, 115, 116, 117, 119),
}

# 成人专属语录：保留直播录屏中的口音、错别字和高冲击表达，不改写原句。
# “成人”是内容级别，不是情绪；这里仍按情绪分组，让气泡同步表情。
ADULT_QUOTE_GROUPS = {
    key: [quote for quote in lines if quote in ADULT_ONLY_QUOTE_LINES]
    for key, lines in SUPPLEMENTAL_QUOTE_GROUPS.items()
}
ADULT_QUOTE_GROUPS['cry'] = L(27)
ADULT_QUOTES = {
    key: QuoteBag(lines) for key, lines in ADULT_QUOTE_GROUPS.items()
}

# 用户语录库的内置场景映射。部分历史语录原本同时出现在多个场景中，
# 编辑器使用一个“主场景”保存；情绪优先级仍由 _EMOTION_PRIORITY 决定。
_BUILTIN_LINES = list(LINES)
_BUILTIN_ID_BY_TEXT = {quote: number for number, quote in
                        enumerate(_BUILTIN_LINES, 1)}
_BASE_SCENE_BY_ID = {}
for _scene_key, _bag in QUOTES.items():
    for _quote in _bag.quotes:
        _number = _BUILTIN_ID_BY_TEXT.get(_quote)
        if _number is not None:
            _BASE_SCENE_BY_ID.setdefault(_number, _scene_key)
for _scene_key, _quotes in SUPPLEMENTAL_QUOTE_GROUPS.items():
    for _quote in _quotes:
        _number = _BUILTIN_ID_BY_TEXT.get(_quote)
        if _number is not None:
            _BASE_SCENE_BY_ID.setdefault(_number, _scene_key)

# 审阅后的成人专属池包含基础语录和追加语录，统一按主场景建立兼容分组。
ADULT_QUOTE_GROUPS = {key: [] for key in QUOTES}
for _number in ADULT_ONLY_QUOTE_IDS:
    _scene_key = _BASE_SCENE_BY_ID.get(_number, 'idle')
    ADULT_QUOTE_GROUPS[_scene_key].append(_BUILTIN_LINES[_number - 1])
ADULT_QUOTES = {
    key: QuoteBag(lines) for key, lines in ADULT_QUOTE_GROUPS.items()
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

# 追加语录也需要进入情绪映射；没有明确场景的历史语录回退 idle。
for _key, _quotes in SUPPLEMENTAL_QUOTE_GROUPS.items():
    for _q in _quotes:
        if _q not in EMOTION_OF:
            EMOTION_OF[_q] = _key
for _q in NORMAL_MODE_QUOTE_LINES:
    EMOTION_OF.setdefault(_q, 'idle')

# 身体点击的全局随机池：成人模式包含成人专属语录和双模式共用语录。
ADULT_EMOTION_OF = {}
for _q in ADULT_ONLY_QUOTE_LINES:
    ADULT_EMOTION_OF[_q] = EMOTION_OF.get(_q, 'idle')
# 保留这个合并映射供旧代码/外部脚本兼容；它覆盖两种模式的全部可显示语录。
EMOTION_OF_WITH_ADULT = dict(EMOTION_OF)
for _q in ADULT_MODE_QUOTE_LINES:
    EMOTION_OF_WITH_ADULT.setdefault(_q, 'idle')

# 普通模式身体点击全局随机池，表情随语录情绪走。
CLICK_BAG = QuoteBag([
    quote for quote in LINES if quote in NORMAL_MODE_QUOTE_LINES
])


def _source_quotes_for_scene(key):
    """返回场景原始来源；运行时由语录库记录统一重建。"""
    return list(QUOTES[key].quotes)


def _build_mode_bags(allowed_lines):
    """为一个模式生成按场景分组的语录袋；空场景回退到该模式总池。"""
    all_lines = [quote for quote in LINES if quote in allowed_lines]
    bags = {}
    for key in QUOTES:
        scene_lines = [
            quote for quote in _source_quotes_for_scene(key)
            if quote in allowed_lines
        ]
        bags[key] = QuoteBag(scene_lines or all_lines)
    return bags


ADULT_MODE_QUOTES = _build_mode_bags(ADULT_MODE_QUOTE_LINES)
NORMAL_MODE_QUOTES = _build_mode_bags(NORMAL_MODE_QUOTE_LINES)
ADULT_CLICK_BAG = QuoteBag([
    quote for quote in LINES if quote in ADULT_MODE_QUOTE_LINES
])
ADULT_MODE_ALL_QUOTES = QuoteBag([
    quote for quote in LINES if quote in ADULT_MODE_QUOTE_LINES
])
NORMAL_MODE_ALL_QUOTES = QuoteBag([
    quote for quote in LINES if quote in NORMAL_MODE_QUOTE_LINES
])

# 旧导入名继续保留，但现在表示“成人模式候选池”，包含双模式共用语录。
QUOTES_WITH_ADULT = ADULT_MODE_QUOTES
CLICK_BAG_WITH_ADULT = ADULT_CLICK_BAG
ADULT_ALL_QUOTES = ADULT_MODE_ALL_QUOTES


def quote_bag(key, adult=False):
    """按内容模式返回场景语录袋：专属语录 + 双模式共用语录。"""
    return (ADULT_MODE_QUOTES if adult else NORMAL_MODE_QUOTES)[key]


def quote_allowed(quote, adult=False):
    """判断一条已登记语录能否在当前内容模式显示。"""
    allowed = ADULT_MODE_QUOTE_LINES if adult else NORMAL_MODE_QUOTE_LINES
    return quote in allowed


def quote_for_mode(key='idle', adult=True):
    """抽取当前模式语录及其情绪键。"""
    quote = quote_bag(key, adult=adult).next()
    if not quote:
        quote = (ADULT_MODE_ALL_QUOTES if adult else NORMAL_MODE_ALL_QUOTES).next()
    return quote, EMOTION_OF_WITH_ADULT.get(quote, 'idle')


def adult_quote_for(key='idle'):
    """兼容旧调用：抽取一条成人模式语录及其情绪键。"""
    return quote_for_mode(key, adult=True)

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
    return q, EMOTION_OF.get(q, 'idle')


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


# ---------------- 用户可编辑语录库 ----------------
# 语录内容放在用户数据目录，避免修改只读的 assets/quotes.txt。编号保持稳定：
# 停用内置语录时保留编号并让 LINES 对应位置为空，旧版场景引用不会错位。
QUOTE_CATEGORY_LABELS = {
    'normal-only': '普通专属',
    'common': '双模式共用',
    'adult-only': '成人专属',
}
QUOTE_CATEGORY_ALIASES = {
    **{key: key for key in QUOTE_CATEGORY_LABELS},
    **{label: key for key, label in QUOTE_CATEGORY_LABELS.items()},
    '普通模式': 'normal-only',
    '普通专属模式': 'normal-only',
    '双模式': 'common',
    '共用': 'common',
    '成人模式': 'adult-only',
    '成人专属模式': 'adult-only',
}
QUOTE_SCENE_LABELS = {
    'idle': '待机',
    'angry': '生气',
    'cry': '哭泣',
    'sad': '难过',
    'happy': '开心',
    'dance': '跳舞',
    'sing': '唱歌',
    'jump': '跳跃',
    'walk': '走路',
    'run': '奔跑',
    'sit': '坐下',
    'sleep': '睡觉',
    'eat': '进食',
    'hungry': '饥饿',
    'pet': '摸头',
    'pickup': '抱起',
    'spin': '转圈',
    'shy': '害羞',
}
_QUOTE_SCENES = tuple(QUOTE_SCENE_LABELS)


def _builtin_category(number):
    if number in _NORMAL_ONLY_QUOTE_ID_SET:
        return 'normal-only'
    if number in _ADULT_ONLY_QUOTE_ID_SET:
        return 'adult-only'
    return 'common'


_BUILTIN_QUOTE_RECORDS = [
    {
        'id': number,
        'text': quote,
        'category': _builtin_category(number),
        'scene': _BASE_SCENE_BY_ID.get(number, 'idle'),
        'enabled': True,
        'source': 'builtin',
    }
    for number, quote in enumerate(_BUILTIN_LINES, 1)
]
_QUOTE_RECORDS = []
_HOURLY_ID_GROUPS = {
    'morning': (1, 60, 36),
    'noon': (68, 69, 70),
    'afternoon': (36, 56, 79),
    'evening': (5, 39, 41),
    'night': (41, 40, 33),
}


def _copy_records(records):
    return [dict(record) for record in records]


def default_quote_records():
    """返回首次启动时的内置语录库副本。"""
    return _copy_records(_BUILTIN_QUOTE_RECORDS)


def _as_bool(value, default=True):
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {'false', '0', 'no', 'off', '否'}:
            return False
        if lowered in {'true', '1', 'yes', 'on', '是'}:
            return True
    return default if value is None else bool(value)


def normalize_quote_records(records):
    """清理用户编辑结果，保证编号、模式、场景和文本可安全进入运行时。"""
    if not isinstance(records, list):
        records = []
    normalized = []
    seen_ids = set()
    seen_texts = set()
    for raw in records:
        if not isinstance(raw, dict):
            continue
        try:
            number = int(raw.get('id'))
        except (TypeError, ValueError):
            continue
        text = str(raw.get('text') or '').strip()
        if number <= 0 or not text or number in seen_ids or text in seen_texts:
            continue
        category = QUOTE_CATEGORY_ALIASES.get(
            str(raw.get('category') or 'common').strip(), 'common')
        scene = str(raw.get('scene') or 'idle').strip()
        if scene not in _QUOTE_SCENES:
            scene = 'idle'
        source = str(raw.get('source') or '').strip()
        if source not in {'builtin', 'user'}:
            source = 'builtin' if number <= len(_BUILTIN_LINES) else 'user'
        normalized.append({
            'id': number,
            'text': text,
            'category': category,
            'scene': scene,
            'enabled': _as_bool(raw.get('enabled'), True),
            'source': source,
        })
        seen_ids.add(number)
        seen_texts.add(text)
    return sorted(normalized, key=lambda record: record['id'])


def get_quote_library():
    """返回当前语录库副本，供编辑器展示。"""
    return _copy_records(_QUOTE_RECORDS)


def _replace_bag(bag, quotes):
    unique = list(dict.fromkeys(quote for quote in quotes if quote))
    bag.quotes[:] = unique
    bag._bag = []
    bag._last = None


def _active_text_by_id(records, number):
    for record in records:
        if record['id'] == number and record['enabled']:
            return record['text']
    return ''


def rebuild_quote_runtime(records):
    """将编辑后的记录原地应用到所有语录池，运行中的宠物无需重启。"""
    records = normalize_quote_records(records)
    _QUOTE_RECORDS[:] = _copy_records(records)

    max_number = max([len(_BUILTIN_LINES)]
                     + [record['id'] for record in records])
    lines = [''] * max_number
    active_records = [record for record in records if record['enabled']]
    for record in active_records:
        lines[record['id'] - 1] = record['text']
    LINES[:] = lines

    _ALL_QUOTE_IDS = tuple(record['id'] for record in records)
    globals()['_ALL_QUOTE_IDS'] = _ALL_QUOTE_IDS
    normal_only = {record['text'] for record in active_records
                   if record['category'] == 'normal-only'}
    adult_only = {record['text'] for record in active_records
                  if record['category'] == 'adult-only'}
    common = {record['text'] for record in active_records
              if record['category'] == 'common'}
    COMMON_QUOTE_LINES.clear()
    COMMON_QUOTE_LINES.update(common)
    ADULT_ONLY_QUOTE_LINES.clear()
    ADULT_ONLY_QUOTE_LINES.update(adult_only)
    NORMAL_ONLY_QUOTE_LINES.clear()
    NORMAL_ONLY_QUOTE_LINES.update(normal_only)
    ADULT_MODE_QUOTE_LINES.clear()
    ADULT_MODE_QUOTE_LINES.update(common | adult_only)
    NORMAL_MODE_QUOTE_LINES.clear()
    NORMAL_MODE_QUOTE_LINES.update(common | normal_only)
    QUOTE_CATEGORY_OF.clear()
    for record in active_records:
        QUOTE_CATEGORY_OF[record['text']] = record['category']

    by_scene = {key: [] for key in QUOTE_SCENE_LABELS}
    for record in active_records:
        by_scene.setdefault(record['scene'], []).append(record['text'])
    for key in QUOTES:
        _replace_bag(QUOTES[key], by_scene.get(key, []))

    # 追加语录兼容分组只保留编号大于 100 的当前有效记录。
    for key in SUPPLEMENTAL_QUOTE_GROUPS:
        SUPPLEMENTAL_QUOTE_GROUPS[key][:] = [
            record['text'] for record in active_records
            if record['id'] > 100 and record['scene'] == key
        ]

    for key in ADULT_QUOTE_GROUPS:
        ADULT_QUOTE_GROUPS[key][:] = [
            record['text'] for record in active_records
            if record['category'] == 'adult-only' and record['scene'] == key
        ]
    for key in ADULT_QUOTE_GROUPS:
        if key not in ADULT_QUOTES:
            ADULT_QUOTES[key] = QuoteBag([])
        _replace_bag(ADULT_QUOTES[key], ADULT_QUOTE_GROUPS[key])
    for key in list(ADULT_QUOTES):
        if key not in ADULT_QUOTE_GROUPS:
            del ADULT_QUOTES[key]

    EMOTION_OF.clear()
    for key in _EMOTION_PRIORITY:
        for quote in QUOTES.get(key, QuoteBag([])).quotes:
            EMOTION_OF.setdefault(quote, key)
    for quote in NORMAL_MODE_QUOTE_LINES:
        EMOTION_OF.setdefault(quote, 'idle')
    ADULT_EMOTION_OF.clear()
    ADULT_EMOTION_OF.update({
        quote: EMOTION_OF.get(quote, 'idle') for quote in adult_only
    })
    EMOTION_OF_WITH_ADULT.clear()
    EMOTION_OF_WITH_ADULT.update(EMOTION_OF)
    for quote in ADULT_MODE_QUOTE_LINES:
        EMOTION_OF_WITH_ADULT.setdefault(quote, 'idle')

    all_active = [record['text'] for record in active_records]
    normal_active = [quote for quote in all_active
                     if quote in NORMAL_MODE_QUOTE_LINES]
    adult_active = [quote for quote in all_active
                    if quote in ADULT_MODE_QUOTE_LINES]
    for bags, allowed in (
        (NORMAL_MODE_QUOTES, NORMAL_MODE_QUOTE_LINES),
        (ADULT_MODE_QUOTES, ADULT_MODE_QUOTE_LINES),
    ):
        for key in QUOTES:
            scene_lines = [quote for quote in QUOTES[key].quotes
                           if quote in allowed]
            if key not in bags:
                bags[key] = QuoteBag(scene_lines or all_active)
            else:
                _replace_bag(bags[key], scene_lines or
                             (normal_active if allowed is NORMAL_MODE_QUOTE_LINES
                              else adult_active))
        for key in list(bags):
            if key not in QUOTES:
                del bags[key]
    _replace_bag(CLICK_BAG, normal_active)
    _replace_bag(ADULT_CLICK_BAG, adult_active)
    _replace_bag(NORMAL_MODE_ALL_QUOTES, normal_active)
    _replace_bag(ADULT_MODE_ALL_QUOTES, adult_active)

    # 这些公共对象会被 pet_window 直接引用，因此全部原地更新。
    fallback = all_active[0] if all_active else ''
    GREET.clear()
    GREET.update({
        'morning': _active_text_by_id(records, 1) or fallback,
        'noon': _active_text_by_id(records, 39) or fallback,
        'evening': _active_text_by_id(records, 41) or fallback,
        'night': _active_text_by_id(records, 41) or fallback,
    })
    globals()['SIGNATURE'] = (_active_text_by_id(records, 16) or fallback)
    for key, ids in _HOURLY_ID_GROUPS.items():
        values = [_active_text_by_id(records, number) for number in ids]
        _replace_bag(HOURLY_QUOTES[key], [value for value in values if value]
                     or normal_active or adult_active)
    return get_quote_library()


def save_quote_library(records):
    """保存并立即应用语录库。"""
    normalized = normalize_quote_records(records)
    os.makedirs(config.DATA_DIR, exist_ok=True)
    payload = {'version': 1, 'quotes': normalized}
    temp_path = config.QUOTE_LIBRARY_FILE + '.tmp'
    with open(temp_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(temp_path, config.QUOTE_LIBRARY_FILE)
    return rebuild_quote_runtime(normalized)


def load_quote_library():
    """读取用户语录库；文件不存在或损坏时使用内置审核结果。"""
    records = None
    try:
        with open(config.QUOTE_LIBRARY_FILE, 'r', encoding='utf-8') as f:
            payload = json.load(f)
        records = payload.get('quotes') if isinstance(payload, dict) else payload
    except (OSError, ValueError, TypeError):
        records = None
    if not isinstance(records, list):
        records = default_quote_records()
    normalized = normalize_quote_records(records)
    if not normalized:
        normalized = default_quote_records()
    return rebuild_quote_runtime(normalized)


def reset_quote_library():
    """恢复审核后的内置语录库，并覆盖用户自定义保存结果。"""
    return save_quote_library(default_quote_records())


def quote_text_by_id(number):
    """返回当前启用的指定编号语录。"""
    return _active_text_by_id(_QUOTE_RECORDS, number)


def signature_quote():
    """返回当前签名语录，供运行中的窗口动态读取。"""
    return quote_text_by_id(16) or next(
        (record['text'] for record in _QUOTE_RECORDS if record['enabled']), '')


# 模块加载完成后恢复用户上次保存的语录库；没有用户文件则直接使用审核后的默认值。
load_quote_library()

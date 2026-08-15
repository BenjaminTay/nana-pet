# -*- coding: utf-8 -*-
"""桌宠公共兼容入口。

新代码应按职责从 nana 包导入；保留本文件是为了兼容现有脚本、
测试和第三方扩展中的 from pet import ...。
"""
from nana.bubble import Bubble
from nana.pet_data import (
    ASSETS,
    ADULT_QUOTES,
    ADULT_QUOTE_GROUPS,
    APPEARANCE_NAMES,
    CLICK_BAG,
    CLICK_BAG_WITH_ADULT,
    EMOTION_OF,
    EMOTION_OF_WITH_ADULT,
    FRAME_INTERVALS,
    GREET,
    HEAD,
    HOURLY_QUOTES,
    LINES,
    L,
    QUOTES,
    QUOTES_WITH_ADULT,
    QuoteBag,
    SIGNATURE,
    PetState,
    emotion_state,
    hourly_egg_for,
    load_quotes,
    quote_bag,
    screen_geometry_for,
)
from nana.pet_window import PetWindow, random

__all__ = [
    'Bubble',
    'ASSETS',
    'ADULT_QUOTES',
    'ADULT_QUOTE_GROUPS',
    'APPEARANCE_NAMES',
    'CLICK_BAG',
    'CLICK_BAG_WITH_ADULT',
    'EMOTION_OF',
    'EMOTION_OF_WITH_ADULT',
    'FRAME_INTERVALS',
    'GREET',
    'HEAD',
    'HOURLY_QUOTES',
    'LINES',
    'L',
    'QUOTES',
    'QUOTES_WITH_ADULT',
    'QuoteBag',
    'SIGNATURE',
    'PetState',
    'PetWindow',
    'random',
    'emotion_state',
    'hourly_egg_for',
    'load_quotes',
    'quote_bag',
    'screen_geometry_for',
]

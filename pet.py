# -*- coding: utf-8 -*-
"""桌宠公共兼容入口。

新代码应按职责从 nana 包导入；保留本文件是为了兼容现有脚本、
测试和第三方扩展中的 from pet import ...。
"""
from nana.bubble import Bubble
from nana.pet_data import (
    ASSETS,
    CLICK_BAG,
    EMOTION_OF,
    FRAME_INTERVALS,
    GREET,
    HEAD,
    HOURLY_QUOTES,
    LINES,
    L,
    QUOTES,
    QuoteBag,
    SIGNATURE,
    PetState,
    emotion_state,
    hourly_egg_for,
    load_quotes,
    screen_geometry_for,
)
from nana.pet_window import PetWindow, random

__all__ = [
    'Bubble',
    'ASSETS',
    'CLICK_BAG',
    'EMOTION_OF',
    'FRAME_INTERVALS',
    'GREET',
    'HEAD',
    'HOURLY_QUOTES',
    'LINES',
    'L',
    'QUOTES',
    'QuoteBag',
    'SIGNATURE',
    'PetState',
    'PetWindow',
    'random',
    'emotion_state',
    'hourly_egg_for',
    'load_quotes',
    'screen_geometry_for',
]

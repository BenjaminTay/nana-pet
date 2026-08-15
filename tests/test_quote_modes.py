# -*- coding: utf-8 -*-
"""语录来源、成人池和情绪映射的纯数据验证。"""
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import config
from pet import (
    ADULT_QUOTE_GROUPS,
    EMOTION_OF_WITH_ADULT,
    LINES,
    QUOTES,
    QUOTES_WITH_ADULT,
    emotion_state,
)


adult_lines = [
    quote
    for group in ADULT_QUOTE_GROUPS.values()
    for quote in group
]
results = {}
results['all_appended_lines_loaded'] = len(LINES) == 119
results['adult_line_count'] = len(adult_lines) == 19
results['adult_lines_are_loaded'] = all(quote in LINES for quote in adult_lines)
results['adult_lines_have_emotion'] = all(
    quote in EMOTION_OF_WITH_ADULT and emotion_state(EMOTION_OF_WITH_ADULT[quote])
    for quote in adult_lines
)
results['adult_mode_default_on'] = config.DEFAULT_CONFIG['adult_quotes'] is True
results['adult_lines_enter_scene_pools'] = all(
    quote in QUOTES_WITH_ADULT[group].quotes
    for group, quotes in ADULT_QUOTE_GROUPS.items()
    for quote in quotes
)
results['normal_pools_unchanged'] = all(
    quote not in QUOTES[group].quotes
    for group, quotes in ADULT_QUOTE_GROUPS.items()
    for quote in quotes
)

ok = all(results.values())
for key in sorted(results):
    print(key, '=', 'PASS' if results[key] else 'FAIL')
print('ALL', 'PASS' if ok else 'FAIL')
sys.exit(0 if ok else 1)

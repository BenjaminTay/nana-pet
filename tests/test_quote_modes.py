# -*- coding: utf-8 -*-
"""语录来源、成人池和情绪映射的纯数据验证。"""
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import config
from pet import (
    ADULT_CLICK_BAG,
    ADULT_MODE_QUOTE_LINES,
    ADULT_ONLY_QUOTE_LINES,
    ADULT_QUOTE_GROUPS,
    CLICK_BAG,
    COMMON_QUOTE_LINES,
    EMOTION_OF_WITH_ADULT,
    LINES,
    NORMAL_MODE_QUOTE_LINES,
    NORMAL_ONLY_QUOTE_LINES,
    QUOTES,
    QUOTES_WITH_ADULT,
    QUOTE_CATEGORY_OF,
    quote_bag,
    emotion_state,
)


adult_lines = [
    quote
    for group in ADULT_QUOTE_GROUPS.values()
    for quote in group
]
all_lines = set(LINES)
results = {}
results['all_appended_lines_loaded'] = len(LINES) == 119
results['adult_line_count'] = len(adult_lines) == 19
results['adult_lines_are_loaded'] = all(quote in LINES for quote in adult_lines)
results['adult_groups_match_category'] = set(adult_lines) == ADULT_ONLY_QUOTE_LINES
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
results['adult_scene_pools_are_isolated'] = all(
    set(quote_bag(group, adult=True).quotes) <= ADULT_MODE_QUOTE_LINES
    for group in QUOTES
)
results['adult_click_pool_isolated'] = (
    set(ADULT_CLICK_BAG.quotes) == ADULT_MODE_QUOTE_LINES)
results['normal_click_pool_isolated'] = (
    set(CLICK_BAG.quotes) == NORMAL_MODE_QUOTE_LINES)
results['category_partition_covers_all_lines'] = (
    set(QUOTE_CATEGORY_OF) == all_lines)
results['category_partition_is_disjoint'] = (
    not (COMMON_QUOTE_LINES & ADULT_ONLY_QUOTE_LINES)
    and not (COMMON_QUOTE_LINES & NORMAL_ONLY_QUOTE_LINES)
    and not (ADULT_ONLY_QUOTE_LINES & NORMAL_ONLY_QUOTE_LINES))
results['category_counts'] = (
    len(ADULT_ONLY_QUOTE_LINES) == 19
    and len(COMMON_QUOTE_LINES) == 41
    and len(NORMAL_ONLY_QUOTE_LINES) == 59)
results['reviewed_category_ids'] = (
    {number for number in range(1, 120)
     if QUOTE_CATEGORY_OF[LINES[number - 1]] == 'normal-only'}
    == {1, 3, 5, 9, 11, 12, 13, 14, 15, 22, 28, 34, 35, 36, 39, 40,
        41, 42, 49, 50, 51, 56, 57, 58, 59, 60, 65, 66, 67, 68, 69,
        70, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87,
        88, 89, 90, 91, 92, 94, 95, 96, 97, 99, 102, 105, 118})
results['quote_102_is_normal_only'] = (
    QUOTE_CATEGORY_OF[LINES[101]] == 'normal-only'
    and LINES[101] in NORMAL_MODE_QUOTE_LINES
    and LINES[101] not in ADULT_MODE_QUOTE_LINES)
results['reviewed_common_appended_quotes'] = all(
    QUOTE_CATEGORY_OF[LINES[number - 1]] == 'common'
    for number in (101, 107)
)
results['reviewed_adult_quotes_are_adult_only'] = all(
    QUOTE_CATEGORY_OF[LINES[number - 1]] == 'adult-only'
    for number in (18, 19, 20, 21, 27, 103, 104, 106, 108, 109, 110,
                   111, 112, 113, 114, 115, 116, 117, 119)
)
results['adult_mode_includes_common'] = (
    COMMON_QUOTE_LINES <= ADULT_MODE_QUOTE_LINES
    and ADULT_ONLY_QUOTE_LINES <= ADULT_MODE_QUOTE_LINES
    and not (NORMAL_ONLY_QUOTE_LINES & ADULT_MODE_QUOTE_LINES))
results['normal_mode_includes_common'] = (
    COMMON_QUOTE_LINES <= NORMAL_MODE_QUOTE_LINES
    and NORMAL_ONLY_QUOTE_LINES <= NORMAL_MODE_QUOTE_LINES
    and not (ADULT_ONLY_QUOTE_LINES & NORMAL_MODE_QUOTE_LINES))
results['adult_only_excluded_from_normal_mode'] = all(
    quote not in NORMAL_MODE_QUOTE_LINES
    for quote in ADULT_ONLY_QUOTE_LINES
)

ok = all(results.values())
for key in sorted(results):
    print(key, '=', 'PASS' if results[key] else 'FAIL')
print('ALL', 'PASS' if ok else 'FAIL')
sys.exit(0 if ok else 1)

# -*- coding: utf-8 -*-
"""快捷键配置规则验证。"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from nana.settings_dialog import find_duplicate_hotkeys


results = {}
results['empty_keys_ignored'] = not find_duplicate_hotkeys({
    'dance': '', 'feed': ''})
duplicates = find_duplicate_hotkeys({
    'dance': 'Meta+Alt+D',
    'feed': 'Meta+Alt+D',
    'reset': 'Meta+Alt+R',
})
results['duplicate_keys_detected'] = len(duplicates) == 1
results['duplicate_labels_included'] = (
    duplicates and '全部跳舞' in duplicates[0] and '全部喂狗粮' in duplicates[0])
results['unique_keys_allowed'] = not find_duplicate_hotkeys({
    'dance': 'Meta+Alt+D',
    'feed': 'Meta+Alt+F',
})

ok = all(results.values())
for key in sorted(results):
    print(key, '=', 'PASS' if results[key] else 'FAIL')
print('ALL', 'PASS' if ok else 'FAIL')
sys.exit(0 if ok else 1)

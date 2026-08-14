# -*- coding: utf-8 -*-
"""macOS 适配层的无窗口单元验证。"""
import os
import sys

if sys.platform != 'darwin':
    print('SKIP: macOS-only Quartz hotkey mapping test')
    sys.exit(0)

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from mac_native import sequence_to_mac_hotkey


CASES = {
    'Meta+Alt+Shift+H': (4, 1703936),
    'Meta+Alt+Shift+N': (45, 1703936),
    'Meta+Alt+Shift+F1': (122, 1703936),
    'Ctrl+Alt+D': (2, 786432),
}

results = {}
for sequence, expected in CASES.items():
    results[sequence] = sequence_to_mac_hotkey(sequence) == expected
results['no_modifier_rejected'] = sequence_to_mac_hotkey('H') is None
results['unknown_key_rejected'] = sequence_to_mac_hotkey('Meta+Alt+Shift+Escape') is None

ok = all(results.values())
for key in sorted(results):
    print(key, '=', 'PASS' if results[key] else 'FAIL')
print('ALL', 'PASS' if ok else 'FAIL')
sys.exit(0 if ok else 1)

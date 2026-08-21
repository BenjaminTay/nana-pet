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

import mac_native
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


class _FakeNativeWindow:
    def __init__(self):
        self.has_shadow = None

    def setHasShadow_(self, value):
        self.has_shadow = bool(value)

    def setHidesOnDeactivate_(self, _value):
        pass

    def setLevel_(self, _value):
        pass

    def setCollectionBehavior_(self, _value):
        pass


# 透明宠物/气泡窗口不能使用 AppKit 默认阴影，否则会在运行时沿 alpha
# 轮廓生成素材中不存在的黑边。用无窗口 fake 保持该规则可在 CI 回归。
results['transparent_window_shadow_disabled'] = True
if mac_native.MAC_NATIVE_AVAILABLE:
    fake = _FakeNativeWindow()
    original_lookup = mac_native._nswindow_for
    mac_native._nswindow_for = lambda _widget: fake
    try:
        applied = mac_native.apply_window_level(object(), always_on_top=False)
    finally:
        mac_native._nswindow_for = original_lookup
    results['transparent_window_shadow_disabled'] = (
        applied and fake.has_shadow is False
    )

ok = all(results.values())
for key in sorted(results):
    print(key, '=', 'PASS' if results[key] else 'FAIL')
print('ALL', 'PASS' if ok else 'FAIL')
sys.exit(0 if ok else 1)

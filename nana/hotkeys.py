# -*- coding: utf-8 -*-
"""Windows/macOS 全局快捷键注册与映射。"""
import logging

from qtcompat import (IS_WIN, IS_MAC, QAbstractNativeEventFilter,
                      QKeySequence, MODS, KEY)
from mac_native import MacGlobalHotkeys

if IS_WIN:
    import ctypes
    import ctypes.wintypes

# 可绑快捷键的功能清单
ACTIONS = [
    ('dance', '💃 全部跳舞'),
    ('feed', '🍖 全部喂狗粮'),
    ('reset', '🏠 复位位置'),
    ('hide', '🙈 隐藏/显示'),
    ('speech', '💬 说话开关'),
    ('top', '📌 置顶开关'),
    ('through', '🖱 穿透开关'),
    ('add', '🐶 添加一只'),
]

MOD_CONTROL = 0x2
MOD_ALT = 0x1
MOD_SHIFT = 0x4
MOD_WIN = 0x8
WM_HOTKEY = 0x0312


def seq_to_vkmods(seq_str):
    """QKeySequence 字符串 → (Windows虚拟键码, 修饰键位掩码)；无法映射返回 (None, 0)"""
    if not seq_str:
        return None, 0
    ks = QKeySequence(seq_str)
    if ks.isEmpty():
        return None, 0
    combo = ks[0]
    kb = combo.keyboardModifiers()
    key = int(combo.key())
    mods = 0
    if kb & MODS.ControlModifier:
        mods |= MOD_CONTROL
    if kb & MODS.AltModifier:
        mods |= MOD_ALT
    if kb & MODS.ShiftModifier:
        mods |= MOD_SHIFT
    if kb & MODS.MetaModifier:
        mods |= MOD_WIN
    vk = None
    if KEY.Key_A.value <= key <= KEY.Key_Z.value:
        vk = ord('A') + (key - KEY.Key_A.value)
    elif KEY.Key_0.value <= key <= KEY.Key_9.value:
        vk = ord('0') + (key - KEY.Key_0.value)
    elif KEY.Key_F1.value <= key <= KEY.Key_F24.value:
        vk = 0x70 + (key - KEY.Key_F1.value)
    elif key == KEY.Key_Space.value:
        vk = 0x20
    return vk, mods


class GlobalHotkeys(QAbstractNativeEventFilter):
    """系统级全局快捷键。Windows: RegisterHotKey + WM_HOTKEY 原生事件过滤；
    macOS: Quartz CGEventTap（需要用户授予辅助功能/输入监控权限）。"""

    def __init__(self, app_owner):
        super().__init__()
        self.owner = app_owner
        self._ids = {}
        self._mac = MacGlobalHotkeys() if IS_MAC else None
        if IS_WIN:
            self._user32 = ctypes.windll.user32
            self._user32.RegisterHotKey.argtypes = [
                ctypes.c_void_p, ctypes.c_int, ctypes.c_uint, ctypes.c_uint]
            self._user32.RegisterHotKey.restype = ctypes.c_bool
            self._user32.UnregisterHotKey.argtypes = [ctypes.c_void_p, ctypes.c_int]
        if self._mac is not None and self._mac.available:
            self._mac.triggered.connect(self.owner.run_action)
            self._mac.status_changed.connect(self.owner.on_hotkey_status)

    def register_all(self, mapping):
        self.unregister_all()
        if IS_MAC:
            if not self._mac.available:
                self.owner.on_hotkey_status('原生快捷键模块不可用，请重新安装 macOS 依赖')
                return
            self._mac.register_all(mapping)
            return
        if not IS_WIN:
            return
        for i, (action, seq) in enumerate(mapping.items(), start=1):
            vk, mods = seq_to_vkmods(seq)
            if not vk or not mods:
                continue
            if self._user32.RegisterHotKey(None, i, mods, vk):
                self._ids[i] = action
        logging.info(f'全局快捷键注册: {list(self._ids.values())}')

    def unregister_all(self):
        if IS_MAC:
            self._mac.unregister_all()
            return
        if not IS_WIN:
            return
        for i in list(self._ids):
            self._user32.UnregisterHotKey(None, i)
        self._ids.clear()

    def nativeEventFilter(self, eventType, message):
        if IS_WIN and eventType == b'windows_generic_MSG':
            msg = ctypes.wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY and msg.wParam in self._ids:
                self.owner.run_action(self._ids[msg.wParam])
        return False, 0

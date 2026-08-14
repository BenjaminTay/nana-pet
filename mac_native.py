# -*- coding: utf-8 -*-
"""macOS 原生窗口层级与全局快捷键适配。

Qt 负责跨平台窗口和界面，macOS 的 NSWindow/Quartz 负责两件 Qt
本身无法稳定保证的事情：

* 桌宠在切换应用、Space、全屏应用后仍处于正确的浮动层级；
* 应用未激活时接收全局组合键。

本模块在非 macOS 上保持可导入、可调用的空实现，避免破坏 Windows 版本。
"""
import logging
import os
import sys
import threading
from typing import Dict, Optional, Tuple

from qtcompat import KEY, MODS, QKeySequence

IS_MAC = sys.platform == 'darwin'

if IS_MAC:
    try:
        import objc
        from AppKit import (
            NSFloatingWindowLevel,
            NSNormalWindowLevel,
            NSWindowCollectionBehaviorCanJoinAllApplications,
            NSWindowCollectionBehaviorCanJoinAllSpaces,
            NSWindowCollectionBehaviorDefault,
            NSWindowCollectionBehaviorStationary,
        )
        from Quartz import (
            CFMachPortCreateRunLoopSource,
            CFRunLoopAddSource,
            CFRunLoopGetCurrent,
            CFRunLoopRemoveSource,
            CFRunLoopRunInMode,
            CGEventGetFlags,
            CGEventGetIntegerValueField,
            CGEventTapCreate,
            CGEventTapEnable,
            CGEventMaskBit,
            CFRunLoopStop,
            kCGEventKeyDown,
            kCGEventTapDisabledByTimeout,
            kCGEventTapDisabledByUserInput,
            kCGEventTapOptionListenOnly,
            kCGHeadInsertEventTap,
            kCGHIDEventTap,
            kCGKeyboardEventKeycode,
            kCGEventFlagMaskAlternate,
            kCGEventFlagMaskCommand,
            kCGEventFlagMaskControl,
            kCGEventFlagMaskShift,
            kCFRunLoopCommonModes,
            kCFRunLoopDefaultMode,
        )
        from PySide6.QtCore import QObject, Signal
        MAC_NATIVE_AVAILABLE = True
    except ImportError as exc:  # 打包遗漏 PyObjC 时仍允许程序启动
        logging.warning('macOS 原生适配不可用: %s', exc)
        MAC_NATIVE_AVAILABLE = False
else:
    MAC_NATIVE_AVAILABLE = False


def _nswindow_for(widget):
    """通过 Qt 的 macOS 原生 view 指针取得 NSWindow。"""
    # Qt offscreen/minimal 平台没有真实 NSView，不能把虚拟 WId 交给 ObjC。
    if (not IS_MAC or not MAC_NATIVE_AVAILABLE or widget is None
            or os.environ.get('QT_QPA_PLATFORM') in ('offscreen', 'minimal')):
        return None
    try:
        # QWidget.winId() 在 macOS 上是 QNSView*，而不是 NSWindow*。
        view = objc.objc_object(c_void_p=int(widget.winId()))
        return view.window()
    except Exception:
        logging.exception('取得 macOS NSWindow 失败')
        return None


def apply_window_level(widget, always_on_top=True, force_front=False):
    """同步 Qt 窗口与 macOS NSWindow 的浮动层级。

    ``force_front`` 只用于用户明确点击“显示/恢复”时，避免定时调用
    orderFrontRegardless 抢走用户当前应用的焦点。
    """
    nswindow = _nswindow_for(widget)
    if nswindow is None:
        return False
    try:
        nswindow.setHidesOnDeactivate_(False)
        if always_on_top:
            nswindow.setLevel_(NSFloatingWindowLevel)
            behavior = (NSWindowCollectionBehaviorCanJoinAllSpaces
                        | NSWindowCollectionBehaviorStationary
                        | NSWindowCollectionBehaviorCanJoinAllApplications)
            nswindow.setCollectionBehavior_(behavior)
        else:
            nswindow.setLevel_(NSNormalWindowLevel)
            nswindow.setCollectionBehavior_(NSWindowCollectionBehaviorDefault)
        if force_front:
            nswindow.orderFrontRegardless()
        return True
    except Exception:
        logging.exception('设置 macOS NSWindow 层级失败')
        return False


def show_and_front(widget, always_on_top=True):
    """用于用户主动恢复窗口时的显示与置前。"""
    if widget is None:
        return False
    widget.show()
    return apply_window_level(widget, always_on_top, force_front=True)


def _mac_keycode_for_qt_key(key: int) -> Optional[int]:
    """Qt Key → macOS 虚拟键码（ANSI 键盘布局）。"""
    if KEY.Key_A.value <= key <= KEY.Key_Z.value:
        # macOS keycode 是物理键位，字母并非连续，见下表。
        return {
            'A': 0, 'S': 1, 'D': 2, 'F': 3, 'H': 4, 'G': 5,
            'Z': 6, 'X': 7, 'C': 8, 'V': 9, 'B': 11, 'Q': 12,
            'W': 13, 'E': 14, 'R': 15, 'Y': 16, 'T': 17, 'O': 31,
            'U': 32, 'I': 34, 'P': 35, 'L': 37, 'J': 38, 'K': 40,
            'N': 45, 'M': 46,
        }.get(chr(key))
    if KEY.Key_0.value <= key <= KEY.Key_9.value:
        return {
            0: 29, 1: 18, 2: 19, 3: 20, 4: 21, 5: 23,
            6: 22, 7: 26, 8: 28, 9: 25,
        }.get(key - KEY.Key_0.value)
    if KEY.Key_F1.value <= key <= KEY.Key_F20.value:
        return {
            1: 122, 2: 120, 3: 99, 4: 118, 5: 96, 6: 97,
            7: 98, 8: 100, 9: 101, 10: 109, 11: 103, 12: 111,
            13: 105, 14: 107, 15: 113, 16: 106, 17: 64, 18: 79,
            19: 80, 20: 90,
        }.get(key - KEY.Key_F1.value + 1)
    if key == KEY.Key_Space.value:
        return 49
    return None


def sequence_to_mac_hotkey(seq_str: str) -> Optional[Tuple[int, int]]:
    """QKeySequence 字符串 → (macOS keycode, CGEvent modifier mask)。"""
    if not seq_str:
        return None
    seq = QKeySequence(seq_str)
    if seq.isEmpty():
        return None
    combo = seq[0]
    keycode = _mac_keycode_for_qt_key(int(combo.key().value))
    if keycode is None:
        return None
    modifiers = combo.keyboardModifiers()
    flags = 0
    if modifiers & MODS.ControlModifier:
        flags |= kCGEventFlagMaskControl
    if modifiers & MODS.AltModifier:
        flags |= kCGEventFlagMaskAlternate
    if modifiers & MODS.ShiftModifier:
        flags |= kCGEventFlagMaskShift
    if modifiers & MODS.MetaModifier:
        flags |= kCGEventFlagMaskCommand
    # 全局快捷键必须有修饰键，避免拦截用户正常输入。
    return (keycode, flags) if flags else None


if IS_MAC and MAC_NATIVE_AVAILABLE:

    class MacGlobalHotkeys(QObject):
        """基于 Quartz CGEventTap 的 macOS 全局组合键监听器。"""

        triggered = Signal(str)
        status_changed = Signal(str)
        available = True

        def __init__(self):
            super().__init__()
            self._mapping: Dict[Tuple[int, int], str] = {}
            self._thread = None
            self._stop = None
            self._tap = None
            self._run_loop = None

        def register_all(self, mapping):
            self.unregister_all()
            parsed = {}
            for action, sequence in (mapping or {}).items():
                hotkey = sequence_to_mac_hotkey(sequence)
                if hotkey is None:
                    continue
                if hotkey in parsed:
                    self.status_changed.emit('快捷键冲突：部分快捷键未注册')
                    continue
                parsed[hotkey] = action
            self._mapping = parsed
            if not parsed:
                self.status_changed.emit('没有可用的 macOS 全局快捷键')
                return
            self._stop = threading.Event()
            self._thread = threading.Thread(target=self._run, name='NanaDogHotkeys',
                                             daemon=True)
            self._thread.start()

        def unregister_all(self):
            if self._stop is not None:
                self._stop.set()
            if self._run_loop is not None:
                try:
                    CFRunLoopStop(self._run_loop)
                except Exception:
                    pass
            if (self._thread is not None
                    and self._thread is not threading.current_thread()):
                self._thread.join(timeout=1.0)
            self._thread = None
            self._stop = None
            self._tap = None
            self._run_loop = None

        def _run(self):
            mask = CGEventMaskBit(kCGEventKeyDown)

            def callback(proxy, event_type, event, refcon):
                if event_type in (kCGEventTapDisabledByTimeout,
                                  kCGEventTapDisabledByUserInput):
                    if self._tap is not None:
                        CGEventTapEnable(self._tap, True)
                    return event
                if event_type == kCGEventKeyDown:
                    keycode = CGEventGetIntegerValueField(
                        event, kCGKeyboardEventKeycode)
                    flags = CGEventGetFlags(event)
                    action = self._mapping.get((keycode, flags & _MODIFIER_MASK))
                    if action:
                        self.triggered.emit(action)
                return event

            self._tap = CGEventTapCreate(
                kCGHIDEventTap,
                kCGHeadInsertEventTap,
                kCGEventTapOptionListenOnly,
                mask,
                callback,
                None,
            )
            if self._tap is None:
                self.status_changed.emit(
                    '快捷键权限不足：请在系统设置→隐私与安全性→辅助功能/输入监控中允许 NANA DOG')
                return

            self._run_loop = CFRunLoopGetCurrent()
            source = CFMachPortCreateRunLoopSource(None, self._tap, 0)
            CFRunLoopAddSource(self._run_loop, source, kCFRunLoopCommonModes)
            CGEventTapEnable(self._tap, True)
            self.status_changed.emit(f'已注册 {len(self._mapping)} 个 macOS 全局快捷键')
            try:
                while self._stop is not None and not self._stop.is_set():
                    CFRunLoopRunInMode(kCFRunLoopDefaultMode, 0.2, False)
            finally:
                try:
                    CFRunLoopRemoveSource(self._run_loop, source,
                                          kCFRunLoopCommonModes)
                except Exception:
                    pass


    _MODIFIER_MASK = (kCGEventFlagMaskAlternate
                      | kCGEventFlagMaskCommand
                      | kCGEventFlagMaskControl
                      | kCGEventFlagMaskShift)

else:

    class MacGlobalHotkeys:
        """非 macOS 或 PyObjC 缺失时的安全空实现。"""

        available = False

        def __init__(self):
            pass

        def register_all(self, mapping):
            return None

        def unregister_all(self):
            return None

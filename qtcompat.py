# -*- coding: utf-8 -*-
"""PySide6 / PySide2 兼容层 + 平台分支。

- 标准版（Win10/11）、macOS 版：PySide6
- 兼容版（Win7/8/8.1）：PySide2 5.15
- Windows 专用 API（Z序钉扎、注册表自启、全局热键）在 mac 上自动降级
用法：`from qtcompat import (Qt, QTimer, WT, WA, MODS, KEY, MOUSE_BTN, EV,
        global_pos, make_mouse_event, ...)`，不再直接 import PySide6/PySide2。
"""
import sys

IS_WIN = sys.platform == 'win32'
IS_MAC = sys.platform == 'darwin'

try:
    from PySide6.QtCore import (Qt, QTimer, QRectF, QPoint, QPointF, QEvent,
                                QAbstractNativeEventFilter)
    # Qt6 把 QAction 从 QtWidgets 挪到了 QtGui
    from PySide6.QtGui import (QPixmap, QAction, QGuiApplication, QTransform,
                               QPainter, QPainterPath, QColor, QPen, QFont,
                               QFontMetrics, QIcon, QKeySequence, QMouseEvent)
    from PySide6.QtWidgets import (QWidget, QLabel, QMenu, QApplication,
                                   QSystemTrayIcon, QDialog, QVBoxLayout,
                                   QHBoxLayout, QPushButton, QSlider,
                                   QKeySequenceEdit, QMessageBox)
    QT6 = True
except ImportError:                          # 兼容版：PySide2 5.15（Win7/8）
    from PySide2.QtCore import (Qt, QTimer, QRectF, QPoint, QPointF, QEvent,
                                QAbstractNativeEventFilter)
    from PySide2.QtGui import (QPixmap, QGuiApplication, QTransform,
                               QPainter, QPainterPath, QColor, QPen, QFont,
                               QFontMetrics, QIcon, QKeySequence, QMouseEvent)
    from PySide2.QtWidgets import (QAction, QWidget, QLabel, QMenu,
                                   QApplication, QSystemTrayIcon, QDialog,
                                   QVBoxLayout, QHBoxLayout, QPushButton,
                                   QSlider, QKeySequenceEdit, QMessageBox)
    QT6 = False

# ---- Qt5/Qt6 命名差异（Qt6 用作用域枚举，Qt5 直接挂在 Qt/QEvent/QDialog 上）----
WT = Qt.WindowType if QT6 else Qt                  # 窗口 flag
WA = Qt.WidgetAttribute if QT6 else Qt             # 窗口属性
MODS = Qt.KeyboardModifier if QT6 else Qt          # 键盘修饰键
KEY = Qt.Key if QT6 else Qt                        # 按键
MOUSE_BTN = Qt.MouseButton if QT6 else Qt          # 鼠标按键
EV = QEvent.Type if QT6 else QEvent                # 事件类型
DIALOG_ACCEPTED = (QDialog.DialogCode.Accepted
                   if QT6 else QDialog.Accepted)
RENDER_AA = (QPainter.RenderHint.Antialiasing
             if QT6 else QPainter.Antialiasing)    # 抗锯齿
PEN_NOPEN = Qt.PenStyle.NoPen if QT6 else Qt.NoPen
ALIGN_HC = (Qt.AlignmentFlag.AlignHCenter
            if QT6 else Qt.AlignHCenter)
ASPECT_KEEP = (Qt.AspectRatioMode.KeepAspectRatio
               if QT6 else Qt.KeepAspectRatio)
TRANS_SMOOTH = (Qt.TransformationMode.SmoothTransformation
                if QT6 else Qt.SmoothTransformation)
FONT_UI = 'PingFang SC' if IS_MAC else 'Microsoft YaHei'   # 跨平台中文字体
HORIZONTAL = (Qt.Orientation.Horizontal if QT6 else Qt.Horizontal)


def global_pos(e):
    """事件全局坐标（QPoint）：Qt6 globalPosition()，Qt5 globalPos()"""
    return e.globalPosition().toPoint() if QT6 else e.globalPos()


def make_mouse_event(etype, local_pos, global_pos_, button, buttons, mods):
    """构造鼠标事件：Qt6 七参 (type,local,scene,global,btn,btns,mods)，Qt5 六参"""
    if QT6:
        return QMouseEvent(etype, QPointF(local_pos), QPointF(local_pos),
                           QPointF(global_pos_), button, buttons, mods)
    return QMouseEvent(etype, QPoint(local_pos), QPoint(global_pos_),
                       button, buttons, mods)


def try_import_qtest():
    try:
        from PySide6.QtTest import QTest
    except ImportError:
        from PySide2.QtTest import QTest
    return QTest

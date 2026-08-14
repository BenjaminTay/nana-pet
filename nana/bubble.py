# -*- coding: utf-8 -*-
"""桌宠对话气泡窗口。"""
from qtcompat import (
    ALIGN_HC,
    FONT_UI,
    PEN_NOPEN,
    RENDER_AA,
    QFont,
    QFontMetrics,
    QPainter,
    QPainterPath,
    QRectF,
    QColor,
    QPen,
    WA,
    QWidget,
    WT,
)
class Bubble(QWidget):
    """手绘对话气泡：圆角矩形+小尾巴+柔和阴影，尾巴指向宠物头部"""

    def __init__(self, always_on_top=True):
        flags = WT.Tool | WT.FramelessWindowHint
        if always_on_top:
            flags |= WT.WindowStaysOnTopHint
        super().__init__(None, flags)
        self.setAttribute(WA.WA_TranslucentBackground)
        # 显示时不抢占 Z 序最前/不抢焦点（SW_SHOWNA）：
        # 关闭置顶后气泡就不会浮到前台窗口上面，和宠物图层保持一致
        self.setAttribute(WA.WA_ShowWithoutActivating)
        self._lines = []
        self.tail_bottom = True      # True=尾巴朝下（气泡在宠物上方）
        self.tail_frac = 0.5         # 尾巴水平位置比例（对准宠物头中心）
        self._font = QFont(FONT_UI, 10)

    def set_text(self, text):
        fm = QFontMetrics(self._font)
        max_w = 280
        self._lines = []
        cur = ''
        for ch in text:
            if fm.horizontalAdvance(cur + ch) > max_w:
                self._lines.append(cur)
                cur = ch
            else:
                cur += ch
        self._lines.append(cur)
        line_h = fm.height() + 3
        w = max(fm.horizontalAdvance(l) for l in self._lines) + 38
        h = line_h * len(self._lines) + 22 + 10   # +10 尾巴
        self.resize(w, h)
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(RENDER_AA)
        w, h = self.width(), self.height()
        tail = 10
        if self.tail_bottom:
            body = QRectF(0, 0, w, h - tail)
        else:
            body = QRectF(0, tail, w, h - tail)
        # 阴影
        p.setPen(PEN_NOPEN)
        p.setBrush(QColor(0, 0, 0, 36))
        p.drawRoundedRect(body.translated(0, 2), 13, 13)
        # 主体+尾巴
        path = QPainterPath()
        path.addRoundedRect(body, 13, 13)
        cx = max(15.0, min(w - 15.0, w * self.tail_frac))
        if self.tail_bottom:
            path.moveTo(cx - 9, h - tail + 2)
            path.lineTo(cx, h)
            path.lineTo(cx + 9, h - tail + 2)
        else:
            path.moveTo(cx - 9, tail - 2)
            path.lineTo(cx, 0)
            path.lineTo(cx + 9, tail - 2)
        path.closeSubpath()
        p.setBrush(QColor(255, 251, 243, 249))
        p.setPen(QPen(QColor(238, 158, 108), 1.5))
        p.drawPath(path)
        # 文字
        p.setPen(QColor(107, 68, 35))
        p.setFont(self._font)
        fm = QFontMetrics(self._font)
        y0 = (tail if not self.tail_bottom else 0) + 8
        y = y0 + fm.ascent()
        for line in self._lines:
            p.drawText(QRectF(10, y - fm.ascent(), w - 20, fm.height() + 4),
                       ALIGN_HC, line)
            y += fm.height() + 3
        p.end()

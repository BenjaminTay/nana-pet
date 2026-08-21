# -*- coding: utf-8 -*-
"""桌宠对话气泡窗口。"""
import time

from qtcompat import (
    ALIGN_HC,
    ALIGN_LEFT,
    ALIGN_VC,
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
    QTimer,
    WA,
    QWidget,
    WT,
)


# 颜色只负责表达情绪，不改变语录内容；成人模式不在气泡中做额外标注。
THEMES = {
    'normal': {
        'background': (255, 251, 243, 250),
        'border': (91, 65, 43, 255),
        'text': (83, 57, 38, 255),
    },
    'happy': {
        'background': (255, 232, 220, 252),
        'border': (216, 105, 76, 255),
        'text': (105, 55, 42, 255),
    },
    'sing': {
        'background': (241, 231, 250, 252),
        'border': (133, 95, 166, 255),
        'text': (76, 54, 93, 255),
    },
    'angry': {
        'background': (255, 224, 211, 252),
        'border': (187, 65, 47, 255),
        'text': (103, 43, 33, 255),
    },
    'sad': {
        'background': (226, 239, 249, 252),
        'border': (86, 126, 157, 255),
        'text': (48, 72, 91, 255),
    },
    'sleep': {
        'background': (229, 237, 249, 252),
        'border': (107, 126, 157, 255),
        'text': (54, 70, 91, 255),
    },
}

STATE_THEMES = {
    'happy': 'happy',
    'jump': 'happy',
    'eat': 'happy',
    'shy': 'happy',
    'sing': 'sing',
    'dance': 'sing',
    'spin': 'sing',
    'angry': 'angry',
    'sad': 'sad',
    'cry': 'sad',
    'sleep': 'sleep',
}


class Bubble(QWidget):
    """手绘贴纸气泡：圆角卡片、柔和阴影和圆润尾巴。"""

    MIN_WIDTH = 96
    MAX_TEXT_WIDTH = 300
    PAINT_MARGIN = 3
    H_PADDING = 14
    V_PADDING = 9
    TAIL_DEPTH = 12
    CORNER_RADIUS = 15
    SHADOW_OFFSET = 3
    ANIMATION_MS = 140

    def __init__(self, always_on_top=True):
        flags = WT.Tool | WT.FramelessWindowHint
        if always_on_top:
            flags |= WT.WindowStaysOnTopHint
        super().__init__(None, flags)
        self.setAttribute(WA.WA_TranslucentBackground)
        # 显示时不抢占 Z 序最前/不抢焦点（SW_SHOWNA）：
        # 关闭置顶后气泡就不会浮到前台窗口上面，和宠物图层保持一致。
        self.setAttribute(WA.WA_ShowWithoutActivating)

        self._lines = []
        self._text = ''
        self._emotion = 'normal'
        self._adult = False
        self.tail_bottom = True      # True=尾巴朝下（气泡在宠物上方）
        self.tail_frac = 0.5         # 尾巴水平位置比例（对准宠物头中心）
        self._font = QFont(FONT_UI, 11)

        # 使用绘制透明度做动画，不改变窗口属性，避免影响置顶和点击穿透。
        self._motion_progress = 0.0
        self._animation_mode = None
        self._animation_started = 0.0
        self._animation_start_progress = 0.0
        self._animation_timer = QTimer(self)
        self._animation_timer.setInterval(16)
        self._animation_timer.timeout.connect(self._animation_tick)

    @staticmethod
    def _normalize_emotion(emotion):
        if emotion is None:
            return 'normal'
        key = getattr(emotion, 'value', emotion)
        key = str(key).lower()
        return STATE_THEMES.get(key, key if key in THEMES else 'normal')

    @staticmethod
    def _color(rgba):
        return QColor(*rgba)

    def set_text(self, text, emotion='normal', adult=False):
        """设置原文并按当前情绪计算气泡尺寸。"""
        self._text = str(text or '')
        self._emotion = self._normalize_emotion(emotion)
        self._adult = bool(adult)

        fm = QFontMetrics(self._font)
        self._lines = self._wrap_text(self._text, fm, self.MAX_TEXT_WIDTH)
        longest = max(fm.horizontalAdvance(line) for line in self._lines)
        # MAX_TEXT_WIDTH 是“文字绘制区域”的宽度，不是整个窗口的宽度。
        # 窗口还要容纳左右内边距和绘制边距；如果直接用
        # MAX_TEXT_WIDTH + H_PADDING * 2，换行宽度会比实际 drawText 区域多
        # 2 * PAINT_MARGIN，最后一个字就可能被窗口右边界裁掉。
        content_width = (longest + self.H_PADDING * 2
                         + self.PAINT_MARGIN * 2)
        max_window_width = (self.MAX_TEXT_WIDTH + self.H_PADDING * 2
                            + self.PAINT_MARGIN * 2)
        width = min(max_window_width,
                    max(self.MIN_WIDTH, round(content_width)))
        line_height = fm.height() + 4
        height = (line_height * len(self._lines)
                  + self.V_PADDING * 2 + self.TAIL_DEPTH + 6)
        self.resize(width, height)
        self.update()

    @staticmethod
    def _wrap_text(text, fm, max_width):
        if not text:
            return ['']
        lines = []
        current = ''
        # 显式换行优先、再按字符拆分。这样中英文、网址和无空格长句
        # 都不会依赖 Qt 的单行裁切行为；空行也原样保留。
        for paragraph in text.replace('\r\n', '\n').replace('\r', '\n').split('\n'):
            if not paragraph:
                lines.append('')
                current = ''
                continue
            for ch in paragraph:
                if current and fm.horizontalAdvance(current + ch) > max_width:
                    lines.append(current)
                    current = ch
                else:
                    current += ch
            lines.append(current)
            current = ''
        return lines

    def _bubble_path(self, body, cx, tail_bottom):
        """绘制尾巴与卡片主体连续的路径，避免生硬三角形接缝。"""
        left, right = body.left(), body.right()
        top, bottom = body.top(), body.bottom()
        radius = min(self.CORNER_RADIUS, body.width() / 2,
                     body.height() / 2)
        tail_half = 10
        path = QPainterPath()

        def top_right():
            path.quadTo(right, top, right, top + radius)

        def bottom_right():
            path.quadTo(right, bottom, right - radius, bottom)

        def bottom_left():
            path.quadTo(left, bottom, left, bottom - radius)

        def top_left():
            path.quadTo(left, top, left + radius, top)

        if tail_bottom:
            path.moveTo(left + radius, top)
            path.lineTo(right - radius, top)
            top_right()
            path.lineTo(right, bottom - radius)
            bottom_right()
            path.lineTo(cx + tail_half, bottom)
            path.cubicTo(cx + 8, bottom + 4, cx + 4, bottom + 9,
                         cx, bottom + self.TAIL_DEPTH)
            path.cubicTo(cx - 4, bottom + 9, cx - 8, bottom + 4,
                         cx - tail_half, bottom)
            path.lineTo(left + radius, bottom)
            bottom_left()
            path.lineTo(left, top + radius)
            top_left()
        else:
            path.moveTo(left + radius, top)
            path.lineTo(cx - tail_half, top)
            path.cubicTo(cx - 8, top - 4, cx - 4, top - 9,
                         cx, top - self.TAIL_DEPTH)
            path.cubicTo(cx + 4, top - 9, cx + 8, top - 4,
                         cx + tail_half, top)
            path.lineTo(right - radius, top)
            top_right()
            path.lineTo(right, bottom - radius)
            bottom_right()
            path.lineTo(left + radius, bottom)
            bottom_left()
            path.lineTo(left, top + radius)
            top_left()
        path.closeSubpath()
        return path

    def _paint_geometry(self):
        margin = float(self.PAINT_MARGIN)
        if self.tail_bottom:
            body = QRectF(margin, margin, self.width() - margin * 2,
                          self.height() - self.TAIL_DEPTH - margin * 2)
        else:
            body = QRectF(margin, self.TAIL_DEPTH + margin,
                          self.width() - margin * 2,
                          self.height() - self.TAIL_DEPTH - margin * 2)
        cx = max(body.left() + 18,
                 min(body.right() - 18, self.width() * self.tail_frac))
        return body, cx

    def _text_width(self, body=None):
        """返回绘制文字的真实宽度，必须与换行计算使用同一口径。"""
        if body is None:
            body, _ = self._paint_geometry()
        return max(1.0, body.width() - self.H_PADDING * 2)

    def paintEvent(self, event):
        del event
        p = QPainter(self)
        p.setRenderHint(RENDER_AA)
        body, cx = self._paint_geometry()
        theme = THEMES[self._emotion]
        path = self._bubble_path(body, cx, self.tail_bottom)

        progress = max(0.0, min(1.0, self._motion_progress))
        offset_direction = 1 if self.tail_bottom else -1
        p.save()
        p.setOpacity(progress)
        p.translate(0, (1.0 - progress) * 6 * offset_direction)

        shadow = QPainterPath(path)
        shadow.translate(0, self.SHADOW_OFFSET)
        p.setPen(PEN_NOPEN)
        p.setBrush(QColor(47, 31, 22, 42))
        p.drawPath(shadow)

        p.setBrush(self._color(theme['background']))
        p.setPen(QPen(self._color(theme['border']), 1.45))
        p.drawPath(path)

        fm = QFontMetrics(self._font)
        text_x = body.left() + self.H_PADDING
        text_width = self._text_width(body)
        text_y = body.top() + self.V_PADDING
        line_height = fm.height() + 4
        p.setPen(self._color(theme['text']))
        p.setFont(self._font)
        alignment = ALIGN_LEFT | ALIGN_VC
        if len(self._lines) == 1 and len(self._text) <= 8 and not self._adult:
            alignment = ALIGN_HC | ALIGN_VC
            text_x = body.left() + self.H_PADDING
            text_width = body.width() - self.H_PADDING * 2
        for index, line in enumerate(self._lines):
            rect = QRectF(text_x, text_y + index * line_height,
                          text_width, line_height)
            p.drawText(rect, alignment, line)
        p.restore()
        p.end()

    def start_show_animation(self):
        """气泡首次出现时做一次轻量淡入/上移动画。"""
        self._animation_timer.stop()
        self._animation_mode = 'show'
        self._animation_started = time.monotonic()
        self._animation_start_progress = 0.0
        self._motion_progress = 0.0
        self.update()
        self._animation_timer.start()

    def show_static(self):
        """取消当前动画并保持完全显示，供连续替换语录使用。"""
        self._animation_timer.stop()
        self._animation_mode = None
        self._motion_progress = 1.0
        self.update()

    def start_hide_animation(self):
        """自然超时时淡出；显式关闭仍可调用 hide_immediately。"""
        if not self.isVisible() or self._animation_mode == 'hide':
            return
        self._animation_timer.stop()
        self._animation_mode = 'hide'
        self._animation_started = time.monotonic()
        self._animation_start_progress = self._motion_progress
        self._animation_timer.start()

    def hide_immediately(self):
        self._animation_timer.stop()
        self._animation_mode = None
        self._motion_progress = 0.0
        self.hide()

    def _animation_tick(self):
        elapsed = (time.monotonic() - self._animation_started) * 1000
        ratio = max(0.0, min(1.0, elapsed / self.ANIMATION_MS))
        eased = 1.0 - (1.0 - ratio) ** 3
        if self._animation_mode == 'show':
            self._motion_progress = eased
        elif self._animation_mode == 'hide':
            self._motion_progress = self._animation_start_progress * (1 - eased)
        else:
            self._animation_timer.stop()
            return
        self.update()
        if ratio >= 1.0:
            mode = self._animation_mode
            self._animation_timer.stop()
            self._animation_mode = None
            if mode == 'show':
                self._motion_progress = 1.0
            else:
                self._motion_progress = 0.0
                self.hide()

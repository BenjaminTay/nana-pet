# -*- coding: utf-8 -*-
"""宠物大小设置对话框。"""
from qtcompat import (HORIZONTAL, QDialog, QGuiApplication, QHBoxLayout,
                      QPoint,
                      QLabel, QPushButton, QSlider, QVBoxLayout)
import config


class SizeDialog(QDialog):
    """用滑块设置相对默认大小的精确比例。"""

    def __init__(self, scale=1.0, on_preview=None, parent=None):
        super().__init__(parent)
        self.on_preview = on_preview
        self.setWindowTitle('调整宠物大小')
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        self.value_label = QLabel()
        layout.addWidget(self.value_label)

        self.slider = QSlider(HORIZONTAL)
        self.slider.setRange(round(config.MIN_SCALE * 100),
                             round(config.MAX_SCALE * 100))
        self.slider.setSingleStep(round(config.SCALE_STEP * 100))
        self.slider.setPageStep(round(config.SCALE_STEP * 100))
        self.slider.setValue(round(config.clamp_scale(scale) * 100))
        self.slider.valueChanged.connect(self._update_label)
        layout.addWidget(self.slider)

        range_label = QHBoxLayout()
        range_label.addWidget(QLabel(f'{round(config.MIN_SCALE * 100)}%'))
        range_label.addStretch()
        range_label.addWidget(QLabel(f'{round(config.MAX_SCALE * 100)}%'))
        layout.addLayout(range_label)

        buttons = QHBoxLayout()
        reset = QPushButton('恢复默认')
        cancel = QPushButton('取消')
        save = QPushButton('应用')
        buttons.addWidget(reset)
        buttons.addStretch()
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)
        reset.clicked.connect(lambda: self.slider.setValue(100))
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self.accept)
        self._update_label(self.slider.value())

    def _update_label(self, value):
        self.value_label.setText(
            f'当前大小：{value}%（拖动滑块实时预览，默认大小为 100%）')
        if self.on_preview:
            self.on_preview(config.clamp_scale(value / 100.0))

    def scale(self):
        return config.clamp_scale(self.slider.value() / 100.0)

    def place_beside(self, anchor):
        """将对话框放到锚点窗口旁边，空间不足时自动换到另一侧。"""
        self.adjustSize()
        anchor_x = anchor.x()
        anchor_y = anchor.y()
        anchor_w = anchor.width()
        anchor_h = anchor.height()
        center = QPoint(anchor_x + anchor_w // 2,
                        anchor_y + anchor_h // 2)
        screen = (QGuiApplication.screenAt(center)
                  or QGuiApplication.primaryScreen())
        available = screen.availableGeometry()
        gap = 12

        right_x = anchor_x + anchor_w + gap
        left_x = anchor_x - self.width() - gap
        right_limit = available.right() - self.width() + 1
        if right_x <= right_limit:
            x = right_x
        elif left_x >= available.left():
            x = left_x
        else:
            x = max(available.left(), min(right_x, right_limit))

        y = anchor_y + (anchor_h - self.height()) // 2
        bottom_limit = available.bottom() - self.height() + 1
        y = max(available.top(), min(y, bottom_limit))
        self.move(x, y)

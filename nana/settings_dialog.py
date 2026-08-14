# -*- coding: utf-8 -*-
"""快捷键设置对话框。"""
import os

from qtcompat import (IS_MAC, QIcon, QKeySequence, QDialog,
                      QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                      QKeySequenceEdit, QMessageBox)
import config
from nana.hotkeys import ACTIONS

ICON_FILE = 'icon.png' if IS_MAC else 'icon.ico'


def find_duplicate_hotkeys(values):
    """返回重复快捷键描述，供界面提示和测试复用。"""
    labels = dict(ACTIONS)
    used = {}
    for key, sequence in values.items():
        if sequence:
            used.setdefault(sequence, []).append(labels.get(key, key))
    return [f'{sequence}：{", ".join(names)}'
            for sequence, names in used.items() if len(names) > 1]


class SettingsDialog(QDialog):
    """设置：所有功能自定义全局快捷键"""

    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.setWindowTitle('那艺娜小狗桌宠 - 设置')
        self.setWindowIcon(QIcon(os.path.join(config.BASE_DIR, 'assets', ICON_FILE)))
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)
        hint = ('macOS 全局快捷键需要在“系统设置 → 隐私与安全性 → 辅助功能/输入监控”中允许 NANA DOG。'
                if IS_MAC else
                '自定义全局快捷键（录制键位，Esc 可清空，保存后立即生效）')
        layout.addWidget(QLabel(hint))
        self.edits = {}
        hotkeys = cfg.get('hotkeys', {})
        for key, label in ACTIONS:
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            edit = QKeySequenceEdit()
            seq = hotkeys.get(key, '')
            edit.setKeySequence(QKeySequence(seq) if seq else QKeySequence())
            self.edits[key] = edit
            row.addWidget(edit, 1)
            layout.addLayout(row)
        btns = QHBoxLayout()
        btn_restore = QPushButton('恢复默认')
        btn_save = QPushButton('保存')
        btn_cancel = QPushButton('取消')
        btns.addWidget(btn_restore)
        btns.addStretch()
        btns.addWidget(btn_save)
        btns.addWidget(btn_cancel)
        layout.addLayout(btns)
        btn_restore.clicked.connect(self._restore)
        btn_save.clicked.connect(self._accept_if_valid)
        btn_cancel.clicked.connect(self.reject)

    def _restore(self):
        defaults = config.DEFAULT_CONFIG['hotkeys']
        for key, edit in self.edits.items():
            edit.setKeySequence(QKeySequence(defaults.get(key, '')))

    def _accept_if_valid(self):
        duplicates = find_duplicate_hotkeys(self.values())
        if duplicates:
            QMessageBox.warning(
                self,
                '快捷键冲突',
                '以下快捷键被多个功能使用，请修改后再保存：\n'
                + '\n'.join(duplicates),
            )
            return
        self.accept()

    def values(self):
        return {key: edit.keySequence().toString() for key, edit in self.edits.items()}

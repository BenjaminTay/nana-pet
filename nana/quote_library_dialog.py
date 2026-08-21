# -*- coding: utf-8 -*-
"""语录库表格编辑器。"""
from qtcompat import (
    QT6,
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)
from nana.pet_data import (
    QUOTE_CATEGORY_LABELS,
    QUOTE_SCENE_LABELS,
    default_quote_records,
    get_quote_library,
    save_quote_library,
)


def _enum_value(group, name):
    return getattr(group, name) if QT6 else getattr(QAbstractItemView, name)


class QuoteEditDialog(QDialog):
    """新增/编辑一条语录。"""

    def __init__(self, record=None, parent=None):
        super().__init__(parent)
        self.record = dict(record or {})
        self.setWindowTitle('编辑语录' if record else '新增语录')
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText('输入宠物要说的话')
        self.text_edit.setMinimumHeight(100)
        form.addRow('语录内容', self.text_edit)

        self.category = QComboBox()
        for key, label in QUOTE_CATEGORY_LABELS.items():
            self.category.addItem(label, key)
        form.addRow('显示模式', self.category)

        self.scene = QComboBox()
        for key, label in QUOTE_SCENE_LABELS.items():
            self.scene.addItem(label, key)
        form.addRow('情绪/场景', self.scene)

        self.enabled = QCheckBox('启用这条语录')
        self.enabled.setChecked(True)
        form.addRow('', self.enabled)
        layout.addLayout(form)
        layout.addWidget(QLabel(
            '普通专属：只在普通模式出现；成人专属：只在成人模式出现；\n'
            '双模式共用：两种模式都可能出现。停用比删除更容易恢复。'))

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton('取消')
        save = QPushButton('确定')
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self._accept_if_valid)

        if record:
            self.text_edit.setPlainText(record.get('text', ''))
            self._set_combo(self.category, record.get('category', 'common'))
            self._set_combo(self.scene, record.get('scene', 'idle'))
            self.enabled.setChecked(bool(record.get('enabled', True)))

    @staticmethod
    def _set_combo(combo, value):
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _accept_if_valid(self):
        if not self.text_edit.toPlainText().strip():
            QMessageBox.warning(self, '内容为空', '请先输入语录内容。')
            return
        self.accept()

    def values(self):
        return {
            'text': self.text_edit.toPlainText().strip(),
            'category': self.category.currentData(),
            'scene': self.scene.currentData(),
            'enabled': self.enabled.isChecked(),
        }


class QuoteLibraryDialog(QDialog):
    """以表格方式管理当前用户的语录库。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('那艺娜小狗 - 语录库管理')
        self.resize(900, 600)
        self.records = get_quote_library()

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            '双击一行即可编辑；可以新增、停用、删除或切换显示模式。\n'
            '保存后立即应用到当前运行中的宠物，用户自定义内容会保存在本机。'))

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ['编号', '语录内容', '显示模式', '情绪/场景', '状态', '来源'])
        self.table.setSelectionBehavior(_enum_value(
            QAbstractItemView.SelectionBehavior if QT6 else QAbstractItemView,
            'SelectRows'))
        self.table.setSelectionMode(_enum_value(
            QAbstractItemView.SelectionMode if QT6 else QAbstractItemView,
            'SingleSelection'))
        self.table.setEditTriggers(_enum_value(
            QAbstractItemView.EditTrigger if QT6 else QAbstractItemView,
            'NoEditTriggers'))
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.doubleClicked.connect(lambda *_: self._edit_selected())
        layout.addWidget(self.table, 1)

        actions = QHBoxLayout()
        add = QPushButton('新增')
        edit = QPushButton('编辑')
        toggle = QPushButton('停用/启用')
        remove = QPushButton('删除')
        restore = QPushButton('恢复内置审核结果')
        actions.addWidget(add)
        actions.addWidget(edit)
        actions.addWidget(toggle)
        actions.addWidget(remove)
        actions.addStretch()
        actions.addWidget(restore)
        layout.addLayout(actions)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton('取消')
        save = QPushButton('保存并应用')
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)

        add.clicked.connect(self._add)
        edit.clicked.connect(self._edit_selected)
        toggle.clicked.connect(self._toggle_selected)
        remove.clicked.connect(self._remove_selected)
        restore.clicked.connect(self._restore_defaults)
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self._save)
        self._refresh_table()

    def _refresh_table(self):
        self.table.setRowCount(len(self.records))
        for row, record in enumerate(self.records):
            values = [
                str(record['id']),
                record['text'],
                QUOTE_CATEGORY_LABELS.get(record['category'], record['category']),
                QUOTE_SCENE_LABELS.get(record['scene'], record['scene']),
                '启用' if record.get('enabled', True) else '已停用',
                '内置' if record.get('source') == 'builtin' else '自定义',
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if not record.get('enabled', True):
                    item.setToolTip('已停用：保存后不会进入任何模式的抽取池')
                self.table.setItem(row, column, item)
        self.table.resizeRowsToContents()

    def _selected_row(self):
        rows = self.table.selectionModel().selectedRows()
        return rows[0].row() if rows else -1

    def _add(self):
        dialog = QuoteEditDialog(parent=self)
        if dialog.exec() != (QDialog.DialogCode.Accepted if QT6 else QDialog.Accepted):
            return
        values = dialog.values()
        if any(record['text'] == values['text'] for record in self.records):
            QMessageBox.warning(self, '语录重复', '语录内容已经存在，请换一句。')
            return
        next_id = max([record['id'] for record in self.records] + [0]) + 1
        values.update({'id': next_id, 'source': 'user'})
        self.records.append(values)
        self.records.sort(key=lambda record: record['id'])
        self._refresh_table()

    def _edit_selected(self):
        row = self._selected_row()
        if row < 0:
            QMessageBox.information(self, '未选择语录', '请先选择一行语录。')
            return
        record = self.records[row]
        dialog = QuoteEditDialog(record, self)
        if dialog.exec() != (QDialog.DialogCode.Accepted if QT6 else QDialog.Accepted):
            return
        values = dialog.values()
        if any(index != row and item['text'] == values['text']
               for index, item in enumerate(self.records)):
            QMessageBox.warning(self, '语录重复', '语录内容已经存在，请换一句。')
            return
        record.update(values)
        self._refresh_table()
        self.table.selectRow(row)

    def _toggle_selected(self):
        row = self._selected_row()
        if row < 0:
            return
        self.records[row]['enabled'] = not self.records[row].get('enabled', True)
        self._refresh_table()
        self.table.selectRow(row)

    def _remove_selected(self):
        row = self._selected_row()
        if row < 0:
            return
        record = self.records[row]
        answer = QMessageBox.question(
            self,
            '确认删除',
            f'确定删除第 {record["id"]} 条语录吗？\n删除后可通过“恢复内置审核结果”找回内置语录。',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            if QT6 else QMessageBox.Yes | QMessageBox.No,
        )
        yes = QMessageBox.StandardButton.Yes if QT6 else QMessageBox.Yes
        if answer == yes:
            self.records.pop(row)
            self._refresh_table()

    def _restore_defaults(self):
        answer = QMessageBox.question(
            self,
            '恢复内置审核结果',
            '这会清除当前新增、修改、停用和删除结果，恢复为项目内置的审核分类。继续吗？',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            if QT6 else QMessageBox.Yes | QMessageBox.No,
        )
        yes = QMessageBox.StandardButton.Yes if QT6 else QMessageBox.Yes
        if answer == yes:
            self.records = default_quote_records()
            self._refresh_table()

    def _save(self):
        try:
            save_quote_library(self.records)
        except (OSError, ValueError, TypeError) as exc:
            QMessageBox.critical(self, '保存失败', f'语录库保存失败：{exc}')
            return
        self.accept()

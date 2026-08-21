# -*- coding: utf-8 -*-
"""用户语录库：读写、分类切换和运行时热更新验证。"""
import os
import sys
import tempfile

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import config
from pet import (
    ADULT_MODE_QUOTE_LINES,
    LINES,
    NORMAL_MODE_QUOTE_LINES,
    get_quote_library,
    quote_allowed,
    rebuild_quote_runtime,
    save_quote_library,
)


original_records = get_quote_library()
original_path = config.QUOTE_LIBRARY_FILE
results = {}

with tempfile.TemporaryDirectory() as temp_dir:
    config.QUOTE_LIBRARY_FILE = os.path.join(temp_dir, 'quotes_user.json')
    edited = get_quote_library()
    disabled_text = edited[0]['text']
    edited[0]['enabled'] = False
    edited[1]['category'] = 'adult-only'
    custom_text = '这是一条用户新增的测试语录。'
    edited.append({
        'id': 120,
        'text': custom_text,
        'category': 'common',
        'scene': 'idle',
        'enabled': True,
        'source': 'user',
    })
    saved = save_quote_library(edited)
    results['saved_file_created'] = os.path.isfile(config.QUOTE_LIBRARY_FILE)
    results['disabled_quote_removed_from_lines'] = disabled_text not in LINES
    results['disabled_quote_not_allowed'] = not quote_allowed(disabled_text)
    results['moved_quote_adult_only'] = (
        edited[1]['text'] in ADULT_MODE_QUOTE_LINES
        and edited[1]['text'] not in NORMAL_MODE_QUOTE_LINES)
    results['custom_common_quote_in_both_modes'] = (
        custom_text in ADULT_MODE_QUOTE_LINES
        and custom_text in NORMAL_MODE_QUOTE_LINES)
    results['custom_id_persisted'] = any(record['id'] == 120 for record in saved)
    results['saved_records_sorted'] = [record['id'] for record in saved] == sorted(
        record['id'] for record in saved)

    loaded = __import__('nana.pet_data', fromlist=['load_quote_library']).load_quote_library()
    results['reload_keeps_edit'] = any(
        record['id'] == 120 and record['text'] == custom_text
        for record in loaded)

config.QUOTE_LIBRARY_FILE = original_path
rebuild_quote_runtime(original_records)

from qtcompat import QApplication
from nana.quote_library_dialog import QuoteLibraryDialog

app = QApplication.instance() or QApplication([])
dialog = QuoteLibraryDialog()
results['editor_table_loaded'] = dialog.table.rowCount() == 119
results['editor_has_mode_column'] = dialog.table.item(0, 2).text() == '普通专属'
dialog.close()

ok = all(results.values())
for key in sorted(results):
    print(key, '=', 'PASS' if results[key] else 'FAIL')
print('ALL', 'PASS' if ok else 'FAIL')
sys.exit(0 if ok else 1)

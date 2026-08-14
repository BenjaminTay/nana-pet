# -*- coding: utf-8 -*-
"""真实窗口测试：置顶开关后，气泡与宠物层级是否一致（WS_EX_TOPMOST 位检查）"""
import ctypes
import os
import sys

if sys.platform != 'win32':
    print('SKIP: test_top.py 仅验证 Windows WS_EX_TOPMOST')
    sys.exit(0)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qtcompat import QApplication

import config
from pet import PetWindow

app = QApplication([])
cfg = config.load()
cfg['speech'] = True
cfg['always_on_top'] = True

pet = PetWindow(777, cfg)
pet.move(100, 100)
pet.say('置顶测试气泡')

GWL_EXSTYLE = -20
WS_EX_TOPMOST = 0x8
user32 = ctypes.windll.user32


def is_topmost(w):
    return bool(user32.GetWindowLongW(int(w.winId()), GWL_EXSTYLE) & WS_EX_TOPMOST)


results = {}
app.processEvents()
results['pet_top_before'] = is_topmost(pet)
results['bubble_top_before'] = is_topmost(pet.bubble)

pet.set_always_on_top(False)
app.processEvents()
pet.say('关了置顶之后的测试气泡')
app.processEvents()
results['pet_top_after_off'] = is_topmost(pet)
results['bubble_top_after_off'] = is_topmost(pet.bubble)

pet.set_always_on_top(True)
app.processEvents()
results['pet_top_back_on'] = is_topmost(pet)
results['bubble_top_back_on'] = is_topmost(pet.bubble)

pet.close()

for k in sorted(results):
    print(k, '=', results[k])
ok = results['pet_top_after_off'] == False and results['bubble_top_after_off'] == False \
    and results['pet_top_back_on'] and results['bubble_top_back_on']
print('CONSISTENT', '=' , ok)
sys.exit(0 if ok else 1)

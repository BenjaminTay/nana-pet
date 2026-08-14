# -*- coding: utf-8 -*-
"""真实窗口Z序测试：关闭置顶后，气泡不应浮到前台窗口上面（要和宠物保持一致）"""
import ctypes
import os
import sys

if sys.platform != 'win32':
    print('SKIP: test_zorder.py 仅验证 Windows 原生 Z 序')
    sys.exit(0)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from qtcompat import Qt, WT
from qtcompat import QApplication, QWidget

import config
from pet import PetWindow

app = QApplication([])
cfg = config.load()
cfg['speech'] = True
cfg['always_on_top'] = False          # 用户场景：置顶已关闭

pet = PetWindow(778, cfg)
pet.move(100, 100)

# 模拟"前台其他应用窗口"
other = QWidget(None, WT.Window)
other.setWindowTitle('OtherAppWindow')
other.setGeometry(300, 300, 400, 300)
other.show()
other.raise_()
other.activateWindow()
app.processEvents()

pet.say('新气泡测试')
app.processEvents()

user32 = ctypes.windll.user32
GW_HWNDNEXT = 2


def zorder_list():
    """从最顶往下遍历顶层窗口，返回 hwnd 列表"""
    result = []
    h = user32.GetTopWindow(None)
    while h:
        result.append(h)
        h = user32.GetWindow(h, GW_HWNDNEXT)
    return result


def idx(hwnd):
    for i, h in enumerate(zorder_list()):
        if h == hwnd:
            return i
    return -1


bubble_idx = idx(int(pet.bubble.winId()))
other_idx = idx(int(other.winId()))
pet_idx = idx(int(pet.winId()))

print('bubble_z =', bubble_idx, '(lower is closer to front)')
print('other_z  =', other_idx)
print('pet_z    =', pet_idx)
ok = bubble_idx > other_idx          # 气泡必须排在"其他应用"后面
print('BUBBLE_BEHIND_OTHER =', ok)

pet.close()
other.close()
sys.exit(0 if ok else 1)

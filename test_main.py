# -*- coding: utf-8 -*-
"""PetApp 级离屏验证：穿透配置重启恢复/隐藏态新增宠物/复位错开/说话开关藏气泡"""
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qtcompat import Qt, WT, QApplication

import config
import main as main_mod

app = QApplication([])
results = {}

# 1) 穿透配置：重启后 window flag 恢复（宠物+气泡都恢复）
cfg1 = config.load()
cfg1['click_through'] = True
config.save(cfg1)
owner = main_mod.PetApp(app)
pet = list(owner.pets.values())[0]
results['restore_click_through'] = bool(
    pet.windowFlags() & WT.WindowTransparentForInput)
results['restore_click_through_bubble'] = bool(
    pet.bubble.windowFlags() & WT.WindowTransparentForInput)
results['through_pet_visible'] = pet.isVisible()
owner.on_exit()

# 2) 隐藏状态下添加宠物 → 新宠物保持隐藏；取消隐藏全部恢复
cfg2 = config.load()
cfg2['click_through'] = False
cfg2['pets'] = []
config.save(cfg2)
owner2 = main_mod.PetApp(app)
owner2.act_hide.setChecked(True)          # 触发 _on_hide 隐藏现有宠物
owner2._add_new()
new_pet = list(owner2.pets.values())[-1]
results['new_pet_hidden'] = new_pet.suppressed and not new_pet.isVisible()
results['old_pet_hidden'] = all(p.suppressed for p in owner2.pets.values())
owner2.act_hide.setChecked(False)
results['unhide_all'] = all(p.isVisible() for p in owner2.pets.values())

# 3) 复位多宠物错开不重叠
owner2.reset_positions()
xs = sorted(p.x() for p in owner2.pets.values())
results['reset_no_overlap'] = len(set(xs)) == len(xs) and len(xs) == 2

# 4) 关闭说话开关 → 当前气泡立即隐藏
owner2.cfg['speech'] = True
pet0 = list(owner2.pets.values())[0]
pet0.say('测试气泡')
results['bubble_shown'] = pet0.bubble.isVisible()
owner2._on_speech(False)
results['speech_off_hides_bubble'] = not pet0.bubble.isVisible()
owner2._on_speech(True)

# 5) 穿透开关：宠物与气泡 flag 同步开/关（图层行为一致）
owner2._on_click_through(True)
results['through_on_pet'] = bool(
    pet0.windowFlags() & WT.WindowTransparentForInput)
results['through_on_bubble'] = bool(
    pet0.bubble.windowFlags() & WT.WindowTransparentForInput)
results['through_on_bubble_hidden'] = not pet0.bubble.isVisible()
owner2._on_click_through(False)
results['through_off_pet'] = not bool(
    pet0.windowFlags() & WT.WindowTransparentForInput)
results['through_off_bubble'] = not bool(
    pet0.bubble.windowFlags() & WT.WindowTransparentForInput)

owner2.on_exit()

# 清理测试痕迹（不影响真实启动）
cfg3 = config.load()
cfg3['pets'] = []
cfg3['click_through'] = False
config.save(cfg3)

ok = all(results.values())
for k in sorted(results):
    print(k, '=', 'PASS' if results[k] else 'FAIL')
print('ALL', 'PASS' if ok else 'FAIL')
sys.exit(0 if ok else 1)

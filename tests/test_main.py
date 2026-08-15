# -*- coding: utf-8 -*-
"""PetApp 级离屏验证：穿透/隐藏/复位/气泡/最后一只移除。"""
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

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

# 6) 最后一只宠物可移除，程序继续运行并可从托盘重新添加
cfg3 = config.load()
cfg3['pets'] = []
cfg3['click_through'] = False
config.save(cfg3)
owner3 = main_mod.PetApp(app)
first_pet_id = next(iter(owner3.pets))
owner3._add_new()
owner3.remove_pet(first_pet_id)
results['remove_one_of_many_keeps_other'] = len(owner3.pets) == 1
last_pet_id = next(iter(owner3.pets))
owner3.remove_pet(last_pet_id)
results['remove_last_pet_keeps_app'] = (
    not owner3.pets and not owner3._exiting)
results['empty_menu_state'] = (
    owner3.act_no_pets.isVisible()
    and not owner3.act_show_all.isEnabled()
    and not owner3.size_menu.isEnabled()
)
owner3._add_new()
results['add_after_empty'] = len(owner3.pets) == 1
owner3.remove_pet(next(iter(owner3.pets)))
owner3.on_exit()

# 7) 重启时没有宠物 → 按产品约定自动创建一只默认宠物
owner4 = main_mod.PetApp(app)
results['restart_empty_creates_default'] = len(owner4.pets) == 1
owner4.on_exit()

# 8) 形象切换写入存档，重启后仍保持 Q 版
cfg5 = config.load()
cfg5['pets'] = []
cfg5['appearance'] = 'classic'
config.save(cfg5)
owner5 = main_mod.PetApp(app)
owner5._set_all_appearance('q')
owner5.on_exit()
saved5 = config.load()
results['appearance_persisted'] = (
    saved5['pets'] and saved5['pets'][0].get('appearance') == 'q')
cfg5['pets'] = []
cfg5['appearance'] = 'classic'
config.save(cfg5)

# 清理测试痕迹（不影响真实启动）
cfg4 = config.load()
cfg4['pets'] = []
cfg4['click_through'] = False
cfg4['appearance'] = 'classic'
config.save(cfg4)

ok = all(results.values())
for k in sorted(results):
    print(k, '=', 'PASS' if results[k] else 'FAIL')
print('ALL', 'PASS' if ok else 'FAIL')
sys.exit(0 if ok else 1)

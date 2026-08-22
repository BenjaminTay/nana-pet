# -*- coding: utf-8 -*-
"""连续缩放、旧配置迁移和窗口锚点验证。"""
import os
import sys
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from qtcompat import QApplication, MODS, QPoint
import config
from nana.pet_data import assets_for_appearance, normalize_appearance
from nana.pet_window import PetWindow
from nana.size_dialog import SizeDialog


app = QApplication([])
results = {}

results['legacy_small_migrates'] = abs(
    config.scale_from_pet({'size': 'small'}) - config.SCALE_PRESETS['small']) < 1e-6
results['legacy_medium_migrates'] = abs(
    config.scale_from_pet({'size': 'medium'}) - 1.0) < 1e-6
results['explicit_scale_wins'] = config.scale_from_pet(
    {'size': 'small', 'scale': 1.5}) == 1.5
results['invalid_scale_falls_back'] = config.scale_from_pet(
    {'scale': 'invalid'}) == 1.0
results['scale_is_clamped'] = (
    config.clamp_scale(0.1) == config.MIN_SCALE
    and config.clamp_scale(99) == config.MAX_SCALE
)
results['appearance_names_normalize'] = (
    normalize_appearance('q') == 'q'
    and normalize_appearance('unknown') == 'classic'
)
expected_classic_assets = (Path(PROJECT_ROOT) / 'assets' / 'skins' / 'classic').resolve()
expected_q_assets = (Path(PROJECT_ROOT) / 'assets' / 'skins' / 'q').resolve()
results['appearance_assets_exist'] = (
    Path(assets_for_appearance('classic')).resolve() == expected_classic_assets
    and Path(assets_for_appearance('q')).resolve() == expected_q_assets
)
legacy_runtime_states = (
    'angry', 'cry', 'dance', 'eat', 'happy', 'idle', 'jump', 'run',
    'sad', 'shy', 'sing', 'sit', 'sleep', 'spin', 'walk',
)
results['legacy_runtime_assets_absent'] = not any(
    (Path(PROJECT_ROOT) / 'assets' / state).is_dir()
    for state in legacy_runtime_states
)

preview_values = []
dialog = SizeDialog(1.0, on_preview=preview_values.append)
dialog.slider.setValue(150)
results['slider_previews_live'] = (
    preview_values and abs(preview_values[-1] - 1.5) < 1e-6
)
dialog.close()

cfg = config.load()
cfg['speech'] = False
pet = PetWindow(1001, cfg)
pet.move(180, 180)
pet.ground_y = pet.y()
side_dialog = SizeDialog(pet.scale)
side_dialog.place_beside(pet)
results['dialog_is_beside_pet'] = (
    side_dialog.x() >= pet.x() + pet.width()
    or side_dialog.x() + side_dialog.width() <= pet.x()
)
side_dialog.close()
old_center = pet.x() + pet.width() / 2
old_bottom = pet.y() + pet.height()
pet.set_scale(1.5)
results['scale_applied'] = abs(pet.scale - 1.5) < 1e-6
results['factor_applied'] = abs(
    pet.factor - config.BASE_SIZE_FACTOR * 1.5) < 1e-6
results['center_preserved'] = abs(
    pet.x() + pet.width() / 2 - old_center) <= 1
results['bottom_preserved'] = abs(
    pet.y() + pet.height() - old_bottom) <= 1
pet.set_scale(0.1)
results['window_scale_min_clamped'] = pet.scale == config.MIN_SCALE
pet.set_scale(9)
results['window_scale_max_clamped'] = pet.scale == config.MAX_SCALE


class FakeWheelEvent:
    def __init__(self, delta, modifiers):
        self._delta = delta
        self._modifiers = modifiers
        self.accepted = False
        self.ignored = False

    def angleDelta(self):
        return QPoint(0, self._delta)

    def modifiers(self):
        return self._modifiers

    def accept(self):
        self.accepted = True

    def ignore(self):
        self.ignored = True


pet.set_scale(1.0)
before_wheel = pet.scale
wheel = FakeWheelEvent(120, MODS.AltModifier)
pet.wheelEvent(wheel)
results['alt_wheel_zoom_in'] = pet.scale > before_wheel and wheel.accepted
wheel = FakeWheelEvent(-120, MODS.NoModifier)
before_wheel = pet.scale
pet.wheelEvent(wheel)
results['plain_wheel_ignored'] = pet.scale == before_wheel and wheel.ignored
old_appearance = pet.appearance
old_center = pet.x() + pet.width() / 2
old_bottom = pet.y() + pet.height()
pet.set_appearance('q')
results['appearance_switches'] = pet.appearance == 'q'
results['appearance_preserves_anchor'] = (
    abs(pet.x() + pet.width() / 2 - old_center) <= 1
    and abs(pet.y() + pet.height() - old_bottom) <= 1
)
pet.set_appearance(old_appearance)
results['appearance_switches_back'] = pet.appearance == 'classic'
pet.close()

ok = all(results.values())
for key in sorted(results):
    print(key, '=', 'PASS' if results[key] else 'FAIL')
print('ALL', 'PASS' if ok else 'FAIL')
sys.exit(0 if ok else 1)

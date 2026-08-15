# -*- coding: utf-8 -*-
"""窗口贴边、跳跃和拖拽时不应把透明画布或角色裁出屏幕。"""
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from qtcompat import QApplication
from nana.pet_data import PetState
from nana.pet_window import PetWindow
import config


app = QApplication([])
cfg = config.load()
cfg.update({'speech': False, 'always_on_top': False})
results = {}

for skin in ('classic', 'q'):
    pet = PetWindow(f'edge-{skin}', cfg, appearance=skin)
    screen = pet.current_screen_geometry()
    left, top = screen.left(), screen.top()
    right = screen.left() + screen.width() - pet.width()
    bottom = screen.top() + screen.height() - pet.height()

    positions = [
        pet.clamp_window_position(-10000, -10000, screen),
        pet.clamp_window_position(10000, 10000, screen),
        pet.clamp_window_position(left, top, screen),
        pet.clamp_window_position(right, bottom, screen),
    ]
    results[f'{skin}_clamp_never_exits_screen'] = all(
        left <= x <= right and top <= y <= bottom
        for x, y in positions
    )

    pet.move(left, top)
    pet.start_jump()
    for _ in range(80):
        pet.tick()
    results[f'{skin}_jump_stays_in_screen'] = (
        left <= pet.x() <= right and top <= pet.y() <= bottom
    )
    results[f'{skin}_jump_state_valid'] = pet.state in {
        PetState.IDLE, PetState.JUMP
    }
    pet.close()

ok = all(results.values())
for key in sorted(results):
    print(key, '=', 'PASS' if results[key] else 'FAIL')
print('ALL', 'PASS' if ok else 'FAIL')
sys.exit(0 if ok else 1)

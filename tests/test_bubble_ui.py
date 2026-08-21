# -*- coding: utf-8 -*-
"""气泡 UI v2 的离屏验证：排版、主题、成人模式和淡入淡出。"""
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from qtcompat import QApplication, try_import_qtest
from nana.bubble import Bubble
from nana.pet_data import (
    ADULT_MODE_QUOTE_LINES,
    ADULT_QUOTE_GROUPS,
    COMMON_QUOTE_LINES,
    LINES,
    NORMAL_MODE_QUOTE_LINES,
    PetState,
)

import config
from nana.pet_window import (VISIBLE_ART_TOP_RATIO, PetWindow)


app = QApplication([])
QTest = try_import_qtest()
results = {}


# 1) 长句换行、情绪主题和成人模式状态
bubble = Bubble(False)
bubble.set_text(
    '这是一个很长很长很长的测试语录，用来验证气泡换行和成人版显示。',
    emotion=PetState.ANGRY,
    adult=True,
)
results['long_text_wraps'] = len(bubble._lines) >= 2
results['angry_theme'] = bubble._emotion == 'angry'
results['adult_state_kept_without_label'] = bubble._adult is True
results['font_is_larger'] = bubble._font.pointSize() == 11

# 2) 普通短句保持普通模式，且使用紧凑尺寸
short = Bubble(False)
short.set_text('吃饭了', emotion=PetState.HAPPY, adult=False)
results['short_text_theme'] = short._emotion == 'happy'
results['short_text_not_adult'] = short._adult is False
results['short_text_is_compact'] = short.width() < bubble.width()

# 3) 上下尾巴都能完成绘制，不抛出异常
bubble.show()
bubble.show_static()
bubble.grab()
bubble.tail_bottom = False
bubble.update()
bubble.grab()
results['both_tail_directions_render'] = True

# 4) 淡入和淡出最终状态正确
bubble.tail_bottom = True
bubble.start_show_animation()
QTest.qWait(220)
results['show_animation_finishes'] = (
    bubble.isVisible() and bubble._motion_progress == 1.0)
bubble.start_hide_animation()
QTest.qWait(220)
results['hide_animation_finishes'] = not bubble.isVisible()

# 5) PetWindow 会把现有情绪和成人语录状态传给气泡
cfg = config.load()
cfg['speech'] = True
cfg['adult_quotes'] = True
pet = PetWindow(998, cfg)
adult_quote = ADULT_QUOTE_GROUPS['angry'][0]
pet.say(adult_quote, emotion=PetState.ANGRY)
results['pet_passes_angry_theme'] = pet.bubble._emotion == 'angry'
results['pet_marks_adult_quote'] = pet.bubble._adult is True
if pet.bubble.tail_bottom:
    bubble_tip_y = pet.bubble.y() + pet.bubble.height() - 3
    visible_head_y = pet.y() + round(pet.height() * VISIBLE_ART_TOP_RATIO)
    results['bubble_attaches_to_visible_head'] = (
        0 <= visible_head_y - bubble_tip_y <= 12)
else:
    results['bubble_attaches_to_visible_head'] = False
pet.say('普通模式测试', emotion=PetState.HAPPY)
results['pet_keeps_normal_quote_unmarked'] = pet.bubble._adult is False
results['pet_passes_happy_theme'] = pet.bubble._emotion == 'happy'
# 成人模式下，历史硬编码普通语录也必须被最后一道内容隔离兜底替换。
pet.cfg['adult_quotes'] = True
pet.say(LINES[0])
results['adult_mode_replaces_normal_quote'] = (
    pet.bubble._text in ADULT_MODE_QUOTE_LINES
    and pet.bubble._text != LINES[0])
common_quote = next(iter(COMMON_QUOTE_LINES))
pet.say(common_quote)
results['common_quote_works_in_adult_mode'] = (
    pet.bubble._text == common_quote and pet.bubble._adult is False)
pet.cfg['adult_quotes'] = False
pet.say(LINES[0])
results['normal_mode_keeps_normal_quote'] = pet.bubble._text == LINES[0]
pet.say(ADULT_QUOTE_GROUPS['angry'][0])
results['normal_mode_replaces_adult_quote'] = (
    pet.bubble._text in NORMAL_MODE_QUOTE_LINES
    and pet.bubble._text not in ADULT_QUOTE_GROUPS['angry'])
pet.say(common_quote)
results['common_quote_works_in_normal_mode'] = (
    pet.bubble._text == common_quote and pet.bubble._adult is False)
# 长文本即使在宠物贴近屏幕顶部时，也不能让气泡窗口被屏幕底部裁掉。
edge_text = '这是一个需要完整显示的超长语录，' * 24
pet.move(pet.current_screen_geometry().left() + 20,
         pet.current_screen_geometry().top())
pet.say(edge_text, emotion=PetState.HAPPY)
screen = pet.current_screen_geometry()
results['edge_long_bubble_stays_on_screen'] = (
    pet.bubble.y() >= screen.top()
    and pet.bubble.y() + pet.bubble.height()
    <= screen.top() + screen.height())
pet.hide_bubble()
pet.close()

ok = all(results.values())
for key in sorted(results):
    print(key, '=', 'PASS' if results[key] else 'FAIL')
print('ALL', 'PASS' if ok else 'FAIL')
sys.exit(0 if ok else 1)

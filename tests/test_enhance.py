# -*- coding: utf-8 -*-
"""提升点离屏验证：长按摸头/双击不重复/隐藏暂停AI/气泡尾巴/边缘偏好/整点彩蛋"""
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from qtcompat import (Qt, QPoint, QPointF, EV, MODS, MOUSE_BTN,
                      QApplication, make_mouse_event)
QTest = __import__('qtcompat').try_import_qtest()

import config
import pet as pet_mod
from pet import (PetWindow, PetState, HEAD, LINES, hourly_egg_for,
                 screen_geometry_for)

app = QApplication([])
cfg = config.load()
cfg['speech'] = True

results = {}


def make_pet():
    pet = PetWindow(999, cfg)
    pet.said = []
    orig_say = pet.say

    def say(text, emotion=None):
        pet.said.append(text)
        orig_say(text, emotion)
    pet.say = say
    return pet


def send(pet, etype, local_pos, button=MOUSE_BTN.LeftButton):
    ev = make_mouse_event(etype, local_pos, pet.mapToGlobal(local_pos),
                          button, button, MODS.NoModifier)
    QApplication.sendEvent(pet, ev)


def head_pos(pet):
    return QPoint(int(pet.width() * (HEAD[0] + HEAD[2]) / 2),
                  int(pet.height() * (HEAD[1] + HEAD[3]) / 2))


# 1) 长按摸头：按住头1秒 → 持续爱心；松手 → 不算点击、恢复待机
pet = make_pet()
hp = head_pos(pet)
send(pet, EV.MouseButtonPress, hp)
QTest.qWait(1100)
results['longpress_active'] = pet._long_petting and pet.state == PetState.HAPPY
results['longpress_loops_forever'] = pet.loops_left == -1
results['longpress_said'] = len(pet.said)
send(pet, EV.MouseButtonRelease, hp)
QTest.qWait(300)
results['longpress_release_no_click'] = len(pet.click_times) == 0
results['longpress_release_idle'] = pet.state == PetState.IDLE
pet.close()

# 2) 双击喂食且不重复计数（喂食语句按原有概率出现）
pet = make_pet()
send(pet, EV.MouseButtonPress, QPoint(50, 50))
send(pet, EV.MouseButtonRelease, QPoint(50, 50))
send(pet, EV.MouseButtonDblClick, QPoint(50, 50))
send(pet, EV.MouseButtonRelease, QPoint(50, 50))
QTest.qWait(400)
results['dblclick_says_at_most_1'] = len(pet.said) <= 1
results['dblclick_no_leftover_clicks'] = len(pet.click_times) == 0
results['dblclick_feeds'] = pet.state == PetState.EAT
pet.set_state(PetState.SLEEP, loops=-1)
send(pet, EV.MouseButtonDblClick, QPoint(50, 50))
results['sleep_dblclick_feeds'] = pet.state == PetState.EAT
pet.close()

# 3) 明确动作应覆盖唤醒动作，不能被中间的舞蹈状态或情绪语句覆盖
pet = make_pet()
pet.set_state(PetState.SLEEP, loops=-1)
pet.play_action(PetState.DANCE, loops=2)
results['sleep_dance_final_state'] = pet.state == PetState.DANCE
pet.set_state(PetState.SLEEP, loops=-1)
pet.feed()
results['sleep_feed_final_state'] = pet.state == PetState.EAT
pet.close()

# 4) 6连点 → 1条怒（连点判定回归检查）
pet = make_pet()
for _ in range(6):
    send(pet, EV.MouseButtonPress, QPoint(50, 50))
    send(pet, EV.MouseButtonRelease, QPoint(50, 50))
QTest.qWait(400)
results['six_clicks_says_1'] = len(pet.said) == 1
results['six_clicks_angry'] = pet.state == PetState.ANGRY
pet.close()

# 4) 隐藏暂停AI：定时器全停、隐藏中不说话不出气泡
pet = make_pet()
pet.move(150, 150)
pet.set_hidden(True)
results['hide_all_timers_stopped'] = (not pet.tick_timer.isActive()
                                      and not pet.anim_timer.isActive()
                                      and not pet.ai_timer.isActive()
                                      and not pet._bubble_sync.isActive())
pet.set_state(PetState.DANCE, loops=2)
results['hide_set_state_no_anim'] = not pet.anim_timer.isActive()
pet.say('隐藏中不该说话')
results['hide_muted'] = not pet.bubble.isVisible()
pos_before = (pet.x(), pet.y())
QTest.qWait(300)
results['hide_pos_frozen'] = (pet.x(), pet.y()) == pos_before
pet.set_hidden(False)
results['show_timers_resumed'] = (pet.tick_timer.isActive()
                                  and pet.ai_timer.isActive()
                                  and pet._bubble_sync.isActive())
pet.close()

# 5) 气泡尾巴对准头中心（朝右/朝左都对齐）
pet = make_pet()
pet.move(200, 200)
pet.say('气泡尾巴测试')
head_cx = int(pet.width() * (HEAD[0] + HEAD[2]) / 2)
tail_x = pet.bubble.x() + int(pet.bubble.width() * pet.bubble.tail_frac)
results['tail_align_right'] = abs(tail_x - (pet.x() + head_cx)) <= 2
pet.facing = -1
pet.say('朝左也对齐')
head_cx2 = pet.width() - head_cx
tail_x2 = pet.bubble.x() + int(pet.bubble.width() * pet.bubble.tail_frac)
results['tail_align_left'] = abs(tail_x2 - (pet.x() + head_cx2)) <= 2
pet.close()

# 6) 散步目标：边缘偏好分支（固定随机数验证）
pet = make_pet()
orig = pet_mod.random.random
pet_mod.random.random = lambda: 0.0
x_edge = pet._walk_target_x()
pet_mod.random.random = lambda: 0.9
x_rand = pet._walk_target_x()
pet_mod.random.random = orig
screen = pet.current_screen_geometry()
results['edge_prefer_target'] = x_edge in (screen.left() + 8,
                                           screen.right() - pet.width() - 8)
results['rand_target_in_screen'] = screen.left() <= x_rand <= screen.right() - pet.width()
pet.close()

# 7) 整点彩蛋：各时段有语录、逐字原句、情绪键有效
eggs = [hourly_egg_for(h) for h in (3, 7, 12, 15, 19, 22)]
results['egg_every_hour_has_text'] = all(t for t, _ in eggs)
results['egg_verbatim'] = all(t in LINES for t, _ in eggs)
results['egg_emotion_valid'] = all(e for _, e in eggs)

# 8) 多显示器回退：越界点也能拿到屏幕几何
results['screen_fallback'] = screen_geometry_for(QPoint(99999, 99999)) is not None

ok = all(results.values())
for k in sorted(results):
    print(k, '=', 'PASS' if results[k] else 'FAIL')
print('ALL', 'PASS' if ok else 'FAIL')
sys.exit(0 if ok else 1)

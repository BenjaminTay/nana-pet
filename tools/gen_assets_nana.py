# -*- coding: utf-8 -*-
"""那艺娜小狗动画帧生成：以用户白底图.png为主素材，PIL变换生成15种状态。

情绪齐全：喜(happy) 怒(angry) 哀(sad) 悲(cry) 乐(dance)
特效（火焰/泪水/爱心/音符/腮红）全部锚定眼睛位置。
"""
import io
import json
import math
import os
import struct

from PIL import Image, ImageDraw, ImageFont

try:
    from .asset_cleanup import normalize_runtime_frame
except ImportError:
    from asset_cleanup import normalize_runtime_frame

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = PROJECT_ROOT
_WINDOWS_SRC = r'C:\Users\Administrator\Desktop\nana\白底图.png'
SRC = os.environ.get(
    'NANA_MASTER_IMAGE',
    _WINDOWS_SRC if os.path.exists(_WINDOWS_SRC)
    else os.path.join(BASE, 'assets_raw', 'nana_12.png'))
ASSETS = os.environ.get('NANA_ASSETS_DIR', os.path.join(BASE, 'assets'))
ACTION_STATES = {'eat', 'dance', 'sit', 'sleep', 'happy'}
PRESERVE_ACTIONS = os.environ.get('NANA_PRESERVE_ACTIONS', '1').lower() not in {
    '0', 'false', 'no', 'off'
}
os.makedirs(ASSETS, exist_ok=True)

PAD = 40          # 画布边距（给特效留空间）
TARGET_H = 340    # 主素材目标高度

FONT_B = None
for _font_path in (
        os.environ.get('NANA_FONT_PATH'),
        'C:/Windows/Fonts/arialbd.ttf',
        '/System/Library/Fonts/Supplemental/Arial Bold.ttf',
        '/Library/Fonts/Arial Bold.ttf'):
    if not _font_path:
        continue
    try:
        FONT_B = ImageFont.truetype(_font_path, 40)
        break
    except Exception:
        pass


def write_ico(path, frames):
    """frames: [(size, PIL.RGBA)] → 标准 ICO（PNG 编码帧，Vista+ 原生支持）。
    PIL 12 的 ico 插件 save(sizes=.../append_images=...) 实测都只写 1 帧，手写最可靠。"""
    blobs = [(s, _png_bytes(img)) for s, img in frames]
    header = struct.pack('<HHH', 0, 1, len(blobs))
    offset = 6 + 16 * len(blobs)
    entries = []
    for s, blob in blobs:
        entries.append(struct.pack('<BBBBHHII',
                                   0 if s >= 256 else s,   # 0 表示 256
                                   0 if s >= 256 else s,
                                   0, 0, 1, 32, len(blob), offset))
        offset += len(blob)
    with open(path, 'wb') as f:
        f.write(header + b''.join(entries) + b''.join(b for _, b in blobs))


def _png_bytes(img):
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


def build_icon_canvas(master, head, size=256):
    """256px 图标母版：渐变蓝圆角底 + 居中狗头。
    白狗在浅色桌面背景上会隐身，必须垫彩色底（托盘图标同理）。"""
    w, h = size, size
    margin = int(size * 0.03)
    radius = int(size * 0.22)
    top_c = (116, 185, 255)      # 天蓝
    bot_c = (29, 78, 216)        # 深蓝
    bg = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    tile = Image.new('RGBA', (w - margin * 2, h - margin * 2), (0, 0, 0, 0))
    px = tile.load()
    th = h - margin * 2
    for y in range(th):
        t = y / max(1, th - 1)
        r = int(top_c[0] + (bot_c[0] - top_c[0]) * t)
        g = int(top_c[1] + (bot_c[1] - top_c[1]) * t)
        b = int(top_c[2] + (bot_c[2] - top_c[2]) * t)
        for x in range(w - margin * 2):
            px[x, y] = (r, g, b, 255)
    mask = Image.new('L', tile.size, 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([0, 0, tile.width - 1, tile.height - 1],
                         radius=radius, fill=255)
    bg.paste(tile, (margin, margin), mask)

    # 狗头占画布 ~74% 高，底部留一点呼吸空间
    mw, mh = master.size
    hx0 = max(0, int(head[0] * mw) - 10)
    hx1 = min(mw, int(head[2] * mw) + 10)
    hy0 = max(0, int(head[1] * mh) - 30)
    hy1 = min(mh, int(head[3] * mh) + 20)
    head_img = master.crop((hx0, hy0, hx1, hy1))
    target_h = int(size * 0.74)
    head_img = head_img.resize(
        (int(target_h * head_img.width / head_img.height), target_h), Image.LANCZOS)
    bg.paste(head_img, ((w - head_img.width) // 2,
                        h - head_img.height - int(size * 0.07)),
             head_img)
    return bg


def load_master():
    img = Image.open(SRC).convert('RGBA')
    a = img.getchannel('A')
    w, h = img.size
    pts = [(x, y) for y in range(h) for x in range(w) if a.getpixel((x, y)) > 10]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    bbox = (min(xs), min(ys), max(xs) + 1, max(ys) + 1)
    img = img.crop(bbox)
    if img.height > TARGET_H:
        w2 = int(img.width * TARGET_H / img.height)
        img = img.resize((w2, TARGET_H), Image.LANCZOS)
    return img, bbox


def find_eyes(img):
    """眼睛暗像素聚类 → 左右眼坐标"""
    w, h = img.size
    px = img.load()
    dark = [(x, y) for y in range(int(h * 0.4)) for x in range(w)
            if px[x, y][3] > 100 and px[x, y][0] < 80 and px[x, y][1] < 80 and px[x, y][2] < 80]
    if len(dark) < 20:
        return (int(w * 0.55), int(h * 0.22)), (int(w * 0.78), int(h * 0.22))
    xs = sorted(p[0] for p in dark)
    mid = xs[len(xs) // 2]
    left = [p for p in dark if p[0] < mid]
    right = [p for p in dark if p[0] >= mid]

    def centroid(pts):
        return (int(sum(p[0] for p in pts) / len(pts)),
                int(sum(p[1] for p in pts) / len(pts)))
    return centroid(left), centroid(right)


def find_head(img):
    """头部区域（相对坐标），用于摸头判定"""
    w, h = img.size
    px = img.load()
    dark = [(x, y) for y in range(int(h * 0.45)) for x in range(w)
            if px[x, y][3] > 100 and px[x, y][0] < 70 and px[x, y][1] < 70 and px[x, y][2] < 70]
    if len(dark) < 20:
        return (0.45, 0.0, 1.0, 0.32)
    xs = [p[0] for p in dark]
    ys = [p[1] for p in dark]
    return (max(0, min(xs) / w - 0.10), max(0, min(ys) / h - 0.20),
            min(1.0, max(xs) / w + 0.10), min(1.0, max(ys) / h + 0.15))


def canvas(master):
    w, h = master.size
    return Image.new('RGBA', (w + PAD * 2, h + PAD), (0, 0, 0, 0))


def place(base, sprite, dx=0, dy=0):
    """居中、脚底对齐粘贴（不带 mask，避免半透明像素被二次衰减）。

    ``sprite`` 可能比母图更高或更宽。不能再固定粘到 ``PAD``，否则
    放大后的帧会在临时画布内部先被截掉；统一按底边对齐，利用画布
    预留的透明空间容纳放大的完整轮廓。
    """
    out = base.copy()
    x = (base.width - sprite.width) // 2 + dx
    y = base.height - sprite.height + dy
    out.paste(sprite, (x, y))
    return out


def squash_img(img, fy, align_bottom=True, fx=1.0):
    """缩放并返回完整 sprite，位置由 ``place`` 负责底边对齐。

    旧实现把放大后的图片粘回原尺寸 ``(w, h)``，当 ``fy > 1`` 时使用
    负 y 坐标，导致顶部内容在生成阶段永久丢失。返回实际放大后的
    图片，让外层透明画布承接超出的安全空间。
    """
    w, h = img.size
    w2 = max(10, int(w * fx))
    h2 = max(10, int(h * fy))
    return img.resize((w2, h2), Image.LANCZOS)


def tilt_img(img, deg):
    w, h = img.size
    return img.rotate(deg, resample=Image.BICUBIC, center=(w / 2, h - 1), expand=False)


def desat(img, factor):
    r, g, b, a = img.split()
    gray = Image.merge('RGB', (r, g, b)).convert('L')
    r = Image.blend(r, gray, 1 - factor)
    g = Image.blend(g, gray, 1 - factor)
    b = Image.blend(b, gray, 1 - factor)
    return Image.merge('RGBA', (r, g, b, a))


# ---------------- 特效（全部在master坐标系内绘制，锚定眼睛） ----------------
def draw_flames(img, eye_l, eye_r):
    """愤怒：眼睛上方两团火焰"""
    d = ImageDraw.Draw(img)
    for ex, ey in (eye_l, eye_r):
        fx, fy = ex, ey - 34
        # 外焰（橙红）
        d.ellipse([fx - 9, fy - 16, fx + 9, fy + 12], fill=(255, 120, 30, 255))
        d.polygon([(fx - 9, fy + 4), (fx, fy + 22), (fx + 9, fy + 4)],
                  fill=(255, 120, 30, 255))
        # 内焰（黄）
        d.ellipse([fx - 4, fy - 4, fx + 4, fy + 8], fill=(255, 220, 80, 255))
        d.polygon([(fx - 4, fy + 5), (fx, fy + 16), (fx + 4, fy + 5)],
                  fill=(255, 220, 80, 255))
    return img


def draw_tears(img, eye_l, eye_r, big=False, t=0):
    """哀/悲：眼泪。big=True 双眼瀑布泪（泪柱连成水帘+飞溅+雨云），t控制帧间抖动"""
    d = ImageDraw.Draw(img)
    for ex, ey in (eye_l, eye_r):
        if not big:
            # 哀：单颗泪珠
            ty = ey + 10 + (1 if t else 0)
            r = 3 + t
            d.ellipse([ex - r, ty - r, ex + r, ty + r], fill=(120, 180, 255, 235))
            d.polygon([(ex - r, ty), (ex + r, ty), (ex, ty + 13)],
                      fill=(120, 180, 255, 235))
        else:
            # 悲：瀑布泪——多层泪滴连成水柱垂到下巴
            n = 4
            for i in range(n):
                ty = ey + 6 + i * 10 + (i % 2) * (2 if t else -1)
                r = max(2, 5 - i * 0.8)
                d.ellipse([ex - r, ty - r, ex + r, ty + r], fill=(110, 175, 255, 240))
                d.polygon([(ex - r, ty), (ex + r, ty), (ex, ty + 14)],
                          fill=(110, 175, 255, 240))
            # 泪底飞溅水花
            for k in range(2):
                sx = ex + (-6 if k == 0 else 7)
                sy = ey + 6 + n * 10 + (4 if t else 2)
                d.ellipse([sx - 2, sy - 2, sx + 2, sy + 2], fill=(140, 200, 255, 210))
    if big:
        # 头顶雨云飘雨（emoji氛围）
        cx = (eye_l[0] + eye_r[0]) // 2
        cy = min(eye_l[1], eye_r[1]) - 48
        for dx, r in ((-15, 12), (0, 15), (15, 11)):
            d.ellipse([cx + dx - r, cy - r - 7, cx + dx + r, cy + r - 7],
                      fill=(155, 170, 205, 205))
        d.ellipse([cx - 24, cy - 12, cx + 24, cy + 8], fill=(155, 170, 205, 215))
        for i in range(5):
            x = cx - 27 + i * 13 + (t % 2) * 5
            y = cy + 16 + (i % 2) * 12
            d.line([(x, y), (x - 3, y + 13)], fill=(150, 190, 255, 195), width=3)
    return img


def draw_hearts(img, t, eye_l, eye_r):
    d = ImageDraw.Draw(img)
    hx = (eye_l[0] + eye_r[0]) // 2
    hy = min(eye_l[1], eye_r[1]) - 40 - t * 12
    for i, off in enumerate([(-26, 6), (22, 16)]):
        x = hx + off[0] + int(6 * math.sin(t * 2 + i))
        y = hy + off[1]
        r = 6 + i * 2
        d.ellipse([x - r, y - r, x, y], fill=(255, 90, 110, 255))
        d.ellipse([x, y - r, x + r, y], fill=(255, 90, 110, 255))
        d.polygon([(x - r + 1, y - r // 2), (x + r - 1, y - r // 2), (x, y + r)],
                  fill=(255, 90, 110, 255))
    return img


def draw_notes(img, t, eye_l, eye_r):
    d = ImageDraw.Draw(img)
    if not FONT_B:
        return img
    hx = (eye_l[0] + eye_r[0]) // 2
    hy = min(eye_l[1], eye_r[1]) - 36
    notes = ['♪', '♫', '♬']
    for i in range(3):
        k = (t + i) % 3
        x = hx + int(26 * math.sin(t * 1.3 + i * 2.1))
        y = hy - i * 26
        d.text((x, y), notes[k], font=FONT_B, fill=(210, 90, 150, 255))
    return img


def draw_blush(img, eye_l, eye_r):
    d = ImageDraw.Draw(img)
    for ex, ey in (eye_l, eye_r):
        d.ellipse([ex - 15, ey + 2, ex + 15, ey + 24], fill=(255, 130, 150, 150))
    return img


def draw_crumbs(img, t, eye_l, eye_r):
    d = ImageDraw.Draw(img)
    mx = (eye_l[0] + eye_r[0]) // 2
    my = max(eye_l[1], eye_r[1]) + 30
    for i in range(t + 1):
        d.ellipse([mx + i * 9, my + (i % 2) * 6, mx + i * 9 + 5, my + (i % 2) * 6 + 5],
                  fill=(140, 90, 50, 255))
    return img


def draw_bone(img, eye_l, eye_r):
    d = ImageDraw.Draw(img)
    bx = (eye_l[0] + eye_r[0]) // 2 + 4
    by = max(eye_l[1], eye_r[1]) + 28
    w_, h_ = 32, 11
    d.rounded_rectangle([bx - w_ // 2, by - h_ // 2, bx + w_ // 2, by + h_ // 2],
                        radius=4, fill=(250, 250, 245, 255))
    for dx in (-w_ // 2, w_ // 2):
        d.ellipse([bx + dx - 6, by - 9, bx + dx + 6, by + 1], fill=(250, 250, 245, 255))
        d.ellipse([bx + dx - 6, by - 1, bx + dx + 6, by + 9], fill=(250, 250, 245, 255))
    return img


def draw_zzz(img, t, eye_l, eye_r):
    d = ImageDraw.Draw(img)
    if not FONT_B:
        return img
    hx = (eye_l[0] + eye_r[0]) // 2 + 30
    hy = min(eye_l[1], eye_r[1]) - 40
    pos = [(hx, hy), (hx + 16, hy - 24), (hx + 34, hy - 48)]
    x, y = pos[t % 3]
    d.text((x, y), 'Z', font=FONT_B, fill=(120, 100, 180, 255))
    return img


def save_frames(state, frames):
    folder = os.path.join(ASSETS, state)
    os.makedirs(folder, exist_ok=True)
    existing = [f for f in os.listdir(folder)
                if f.lower().startswith('frame_') and f.lower().endswith('.png')]
    if state in ACTION_STATES and PRESERVE_ACTIONS and existing:
        print(f'{state}: 保留现有动作素材（如需覆盖请设置 NANA_PRESERVE_ACTIONS=0）')
        return
    for i, f in enumerate(frames):
        normalize_runtime_frame(f).save(
            os.path.join(folder, f'frame_{i + 1:03d}.png'))
    print(f'{state}: {len(frames)} 帧')


def gen_all():
    master, bbox = load_master()
    mw, mh = master.size
    eye_l, eye_r = find_eyes(master)
    head = find_head(master)
    print(f'主素材: {master.size}, 左眼{eye_l}, 右眼{eye_r}')
    print(f'头部区域: x {head[0]:.2f}-{head[2]:.2f}, y {head[1]:.2f}-{head[3]:.2f}')
    with open(os.path.join(ASSETS, 'head.json'), 'w') as f:
        json.dump({'head': list(head), 'eyes': [list(eye_l), list(eye_r)]}, f)

    base = canvas(master)

    # 待机：呼吸
    idle = []
    for fy in (1.0, 1.025, 1.0, 1.025):
        idle.append(place(base, squash_img(master, fy)))
    save_frames('idle', idle)

    # 走路：弹跳+摇摆+微拉宽
    walk = []
    for i in range(6):
        ph = i / 6 * 2 * math.pi
        bob = -int(5 * abs(math.cos(ph)))
        tilt = 3 * math.sin(ph)
        walk.append(place(base, tilt_img(squash_img(master, 1.0, fx=1.03), tilt), dy=bob))
    save_frames('walk', walk)

    # 奔跑：人物拉宽（速度感）+大幅弹跳
    run = []
    for i in range(6):
        ph = i / 6 * 2 * math.pi
        bob = -int(9 * abs(math.cos(ph)))
        tilt = 5 * math.sin(ph)
        fx = 1.0 + 0.09 * abs(math.cos(ph))
        run.append(place(base, tilt_img(squash_img(master, 1.0, fx=fx), tilt), dy=bob))
    save_frames('run', run)

    # 跳跃
    jump = [
        place(base, squash_img(master, 0.88)),
        place(base, squash_img(master, 1.08)),
        # 画布上方只留 40px 安全边距，不能再把整只角色推到画布外。
        place(base, master, dy=-30),
        place(base, squash_img(master, 0.9)),
    ]
    save_frames('jump', jump)

    # 坐下
    sit = [place(base, squash_img(master, 0.78)),
           place(base, squash_img(master, 0.8))]
    save_frames('sit', sit)

    # 睡觉：歪头+Zzz+微暗
    sleep = []
    for t in range(3):
        img = desat(tilt_img(master, -6 + t), 0.88)
        sleep.append(place(base, draw_zzz(img, t, eye_l, eye_r)))
    save_frames('sleep', sleep)

    # 跳舞（爱如火！）
    dance = []
    for i in range(8):
        ph = i / 8 * 2 * math.pi
        tilt = 9 * math.sin(ph)
        bob = -int(4 * abs(math.cos(ph)))
        dance.append(place(base, tilt_img(master, tilt), dy=bob))
    save_frames('dance', dance)

    # 吃狗粮
    eat = []
    for t in range(4):
        img = draw_bone(master, eye_l, eye_r)
        img = draw_crumbs(img, t, eye_l, eye_r)
        eat.append(place(base, img, dy=[0, -6, -3, -6][t]))
    save_frames('eat', eat)

    # 喜：被摸头/开心
    happy = []
    for t in range(4):
        bob = -int(6 * abs(math.cos(t / 4 * 2 * math.pi)))
        happy.append(place(base, draw_hearts(master, t, eye_l, eye_r), dy=bob))
    save_frames('happy', happy)

    # 怒：眼睛上方两团火焰
    angry = [
        place(base, draw_flames(tilt_img(master, 6), eye_l, eye_r)),
        place(base, draw_flames(tilt_img(master, -6), eye_l, eye_r)),
    ]
    save_frames('angry', angry)

    # 哀：垂头+一滴泪+略暗
    sad = [
        place(base, draw_tears(desat(tilt_img(master, -5), 0.94), eye_l, eye_r, t=0)),
        place(base, draw_tears(desat(tilt_img(master, -3), 0.94), eye_l, eye_r, t=1)),
    ]
    save_frames('sad', sad)

    # 悲：双眼瀑布泪+飞溅+雨云+更暗
    cry = [
        place(base, draw_tears(desat(tilt_img(master, -8), 0.9), eye_l, eye_r, big=True, t=0)),
        place(base, draw_tears(desat(tilt_img(master, -6), 0.9), eye_l, eye_r, big=True, t=1)),
    ]
    save_frames('cry', cry)

    # 转圈：整圈旋转（expand后适配画布）
    spin = []
    for i in range(8):
        rot = master.rotate(i * 45, resample=Image.BICUBIC, expand=True)
        rot.thumbnail((mw + PAD * 2 - 8, mh + PAD - 8), Image.LANCZOS)
        out = base.copy()
        out.paste(rot, (PAD + (mw - rot.width) // 2, PAD + mh - rot.height))
        spin.append(out)
    save_frames('spin', spin)

    # 唱歌：摇摆+音符
    sing = []
    for t in range(4):
        img = draw_notes(tilt_img(master, 6 * math.sin(t / 4 * 2 * math.pi)), t, eye_l, eye_r)
        sing.append(place(base, img, dy=-int(3 * abs(math.cos(t / 4 * 2 * math.pi)))))
    save_frames('sing', sing)

    # 害羞：低头+腮红
    shy = [
        place(base, draw_blush(tilt_img(master, -5), eye_l, eye_r)),
        place(base, draw_blush(tilt_img(master, -3), eye_l, eye_r)),
    ]
    save_frames('shy', shy)

    # 图标：256 母版（渐变圆角底+狗头）→ 7 档尺寸。PIL 12 的 ico 插件只写 1 帧，手写 ICO 容器
    canvas256 = build_icon_canvas(master, head, 256)
    write_ico(os.path.join(ASSETS, 'icon.ico'),
              [(s, canvas256.resize((s, s), Image.LANCZOS))
               for s in (16, 24, 32, 48, 64, 128, 256)])
    print('icon.ico: 完成')
    print('全部完成 ->', ASSETS)


if __name__ == '__main__':
    gen_all()

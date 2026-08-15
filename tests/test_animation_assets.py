# -*- coding: utf-8 -*-
"""动画资源尺寸与基线回归检查。"""
import os
import sys
from pathlib import Path
from statistics import median

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


SKINS = ('classic', 'q')
STATES = (
    'idle', 'walk', 'run', 'jump', 'sit', 'sleep', 'dance', 'eat',
    'happy', 'angry', 'sad', 'cry', 'spin', 'sing', 'shy',
)
EXPECTED_FRAME_COUNTS = {
    'idle': 4,
    'walk': 6,
    'run': 6,
    'jump': 4,
    'sit': 4,
    'sleep': 4,
    'dance': 8,
    'eat': 6,
    'happy': 4,
    'angry': 2,
    'sad': 2,
    'cry': 2,
    'spin': 8,
    'sing': 4,
    'shy': 4,
}
MIN_TOP_MARGIN = 48
MIN_SIDE_MARGIN = 16
MIN_BOTTOM_MARGIN = 16


def visible_size(path):
    with Image.open(path).convert('RGBA') as image:
        bbox = image.getchannel('A').getbbox()
    if bbox is None:
        return (0, 0, None, None)
    return (bbox[2] - bbox[0], bbox[3] - bbox[1], bbox[1], bbox[3])


def touches_forbidden_edge(path):
    with Image.open(path).convert('RGBA') as image:
        alpha = image.getchannel('A')
        width, height = image.size
        pixels = alpha.load()
        return {
            'top': any(pixels[x, 0] > 0 for x in range(width)),
            'left': any(pixels[0, y] > 0 for y in range(height)),
            'right': any(pixels[width - 1, y] > 0 for y in range(height)),
            'bottom': any(pixels[x, height - 1] > 0 for x in range(width)),
        }


def has_safe_margins(path):
    with Image.open(path).convert('RGBA') as image:
        bbox = image.getchannel('A').getbbox()
        if bbox is None:
            return False
        width, height = image.size
        left, top, right, bottom = bbox
        return (top >= MIN_TOP_MARGIN
                and left >= MIN_SIDE_MARGIN
                and width - right >= MIN_SIDE_MARGIN
                and height - bottom >= MIN_BOTTOM_MARGIN)


def background_edge_leakage(path):
    """统计明显的白底/黑底边缘残留，忽略正常的半透明抗锯齿像素。"""
    with Image.open(path).convert('RGBA') as image:
        alpha = image.getchannel('A')
        width, height = image.size
        pixels = image.load()
        count = 0
        for y in range(height):
            for x in range(width):
                r, g, b, a = pixels[x, y]
                # 极低 alpha 的生成器残留已经不可见，允许状态特效保留这些
                # 轻微抗锯齿像素；真正会形成桌面黑/白边的是较高 alpha 的底色。
                if a < 16:
                    continue
                adjacent_to_transparent = any(
                    0 <= nx < width and 0 <= ny < height
                    and pixels[nx, ny][3] == 0
                    for nx, ny in ((x - 1, y), (x + 1, y),
                                   (x, y - 1), (x, y + 1)))
                if not adjacent_to_transparent:
                    continue
                spread = max(r, g, b) - min(r, g, b)
                if (min(r, g, b) >= 220 and spread <= 100) or max(r, g, b) <= 40:
                    count += 1
        return count


results = {}
for skin in SKINS:
    skin_dir = PROJECT_ROOT / 'assets' / 'skins' / skin
    idle_frames = sorted((skin_dir / 'idle').glob('frame_*.png'))
    expected_canvas = Image.open(idle_frames[0]).size
    idle_width = median([visible_size(path)[0] for path in idle_frames])
    idle_heights = [visible_size(path)[1] for path in idle_frames]
    idle_height = median(idle_heights)
    idle_bottoms = [visible_size(path)[3] for path in idle_frames]
    idle_bottom = median(idle_bottoms)

    for state in STATES:
        frames = sorted((skin_dir / state).glob('frame_*.png'))
        results[f'{skin}_{state}_has_frames'] = bool(frames)
        results[f'{skin}_{state}_frame_count_matches_spec'] = (
            len(frames) == EXPECTED_FRAME_COUNTS[state]
        )
        results[f'{skin}_{state}_canvas_matches_idle'] = all(
            Image.open(path).size == expected_canvas for path in frames)
        results[f'{skin}_{state}_has_edge_safety_margin'] = all(
            not any(touches_forbidden_edge(path).values()) for path in frames)
        results[f'{skin}_{state}_has_minimum_margins'] = all(
            has_safe_margins(path) for path in frames)
        results[f'{skin}_{state}_no_background_edge_leakage'] = all(
            background_edge_leakage(path) <= 64 for path in frames)
        idle_signatures = {path.read_bytes() for path in idle_frames}
        results[f'{skin}_{state}_not_idle_fallback'] = (
            state == 'idle'
            or any(path.read_bytes() not in idle_signatures for path in frames)
        )

    happy_sizes = [visible_size(path) for path in
                   sorted((skin_dir / 'happy').glob('frame_*.png'))]
    happy_heights = [size[1] for size in happy_sizes]
    happy_bottoms = [size[3] for size in happy_sizes]
    results[f'{skin}_happy_matches_idle_scale'] = (
        min(happy_heights) >= idle_height * 0.85
        and max(happy_heights) <= idle_height * 1.30
        and max(size[0] for size in happy_sizes) <= idle_width * 1.20
    )
    results[f'{skin}_happy_frame_height_stable'] = (
        max(happy_heights) <= min(happy_heights) * 1.08
    )
    results[f'{skin}_happy_baseline_stable'] = (
        len(set(happy_bottoms)) == 1
        and happy_bottoms[0] == idle_bottom
    )

ok = all(results.values())
for key in sorted(results):
    print(key, '=', 'PASS' if results[key] else 'FAIL')
print('ALL', 'PASS' if ok else 'FAIL')
sys.exit(0 if ok else 1)

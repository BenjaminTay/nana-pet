# -*- coding: utf-8 -*-
"""一次性修复现有皮肤帧的透明边缘与画布安全边距。"""
import argparse
from pathlib import Path

from PIL import Image

try:
    from .asset_cleanup import (despill_alpha_edges, erode_alpha_boundary,
                                 repack_visible_frame)
except ImportError:
    from asset_cleanup import (despill_alpha_edges, erode_alpha_boundary,
                               repack_visible_frame)


STATES = (
    'idle', 'walk', 'run', 'jump', 'sit', 'sleep', 'dance', 'eat',
    'happy', 'angry', 'sad', 'cry', 'spin', 'sing', 'shy',
)


def normalize_skin(skin_dir, padding_x, top_margin, bottom_margin,
                   min_canvas_height):
    frame_paths = [
        path for state in STATES
        for path in sorted((skin_dir / state).glob('frame_*.png'))
    ]
    if not frame_paths:
        raise ValueError(f'没有找到动画帧: {skin_dir}')

    widths = []
    visible_heights = []
    for path in frame_paths:
        with Image.open(path).convert('RGBA') as image:
            bbox = image.getchannel('A').getbbox()
        if bbox:
            widths.append(image.width)
            visible_heights.append(bbox[3] - bbox[1])
    target_width = max(widths)
    target_height = max(
        min_canvas_height,
        max(visible_heights) + top_margin + bottom_margin)
    target_size = (target_width, target_height)
    changed = 0
    for path in frame_paths:
        with Image.open(path).convert('RGBA') as image:
            normalized = erode_alpha_boundary(
                despill_alpha_edges(image), passes=2)
            normalized = repack_visible_frame(
                normalized, target_size, top_margin=top_margin,
                bottom_margin=bottom_margin, side_margin=padding_x)
            normalized.save(path)
            changed += 1
    return {
        'skin': str(skin_dir),
        'frames': changed,
        'padding_added': True,
        'canvas': list(Image.open(frame_paths[0]).size),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--assets-dir', type=Path, default=Path('assets/skins'))
    parser.add_argument('--padding-x', type=int, default=16)
    parser.add_argument('--top-margin', type=int, default=48)
    parser.add_argument('--bottom-margin', type=int, default=16)
    parser.add_argument('--min-canvas-height', type=int, default=444)
    args = parser.parse_args()
    for skin in ('classic', 'q'):
        print(normalize_skin(
            args.assets_dir / skin, args.padding_x, args.top_margin,
            args.bottom_margin, args.min_canvas_height))


if __name__ == '__main__':
    main()

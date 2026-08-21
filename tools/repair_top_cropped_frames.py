# -*- coding: utf-8 -*-
"""修复两套皮肤中已被旧生成流程截掉顶部的待机/跳跃帧。

旧帧的顶部像素已经丢失，单纯重新加透明留白无法恢复，因此使用同一
动作中未裁切的完整参考帧重新生成安全的纵向变化，再固定回原画布。
"""
import argparse
from pathlib import Path

from PIL import Image

try:
    from .asset_cleanup import despill_alpha_edges
except ImportError:
    from asset_cleanup import despill_alpha_edges


DEFAULT_SKINS = ('classic', 'q')


def visible_sprite(path):
    with Image.open(path).convert('RGBA') as image:
        alpha = image.getchannel('A')
        bbox = alpha.getbbox()
        if bbox is None:
            raise ValueError(f'素材帧没有可见像素: {path}')
        return image.crop(bbox), image.size


def rebuild_frame(reference_path, target_path, vertical_scale,
                  top_margin=48, bottom_margin=16, side_margin=16):
    sprite, target_size = visible_sprite(reference_path)
    width, height = target_size
    scaled_size = (sprite.width,
                   max(1, round(sprite.height * vertical_scale)))
    sprite = sprite.resize(scaled_size, Image.Resampling.LANCZOS)

    max_width = width - side_margin * 2
    max_height = height - top_margin - bottom_margin
    fit = min(1.0, max_width / sprite.width, max_height / sprite.height)
    if fit < 1.0:
        sprite = sprite.resize(
            (max(1, round(sprite.width * fit)),
             max(1, round(sprite.height * fit))),
            Image.Resampling.LANCZOS,
        )

    canvas = Image.new('RGBA', target_size, (0, 0, 0, 0))
    x = (width - sprite.width) // 2
    y = height - bottom_margin - sprite.height
    if y < top_margin:
        raise ValueError(
            f'修复后仍无法满足顶部安全区: {target_path} y={y}')
    canvas.alpha_composite(sprite, (x, y))
    despill_alpha_edges(canvas).save(target_path)


def repair_skin(skin_dir):
    idle = skin_dir / 'idle'
    jump = skin_dir / 'jump'
    rebuild_frame(idle / 'frame_001.png', idle / 'frame_002.png', 1.025)
    rebuild_frame(idle / 'frame_001.png', idle / 'frame_004.png', 1.025)
    rebuild_frame(jump / 'frame_003.png', jump / 'frame_002.png', 1.08)
    return {
        'skin': str(skin_dir),
        'repaired': [
            str(idle / 'frame_002.png'),
            str(idle / 'frame_004.png'),
            str(jump / 'frame_002.png'),
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--assets-dir', type=Path, default=Path('assets/skins'))
    args = parser.parse_args()
    for skin in DEFAULT_SKINS:
        print(repair_skin(args.assets_dir / skin))


if __name__ == '__main__':
    main()

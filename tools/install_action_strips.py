# -*- coding: utf-8 -*-
"""将图像生成的横向动作条清理、拆帧并归一化为本项目的状态帧。

该脚本只负责确定性处理：去除边缘连通的浅色棋盘背景、拆分面板、
统一动作条的缩放与脚底基线。它不生成或绘制宠物图像。
"""
import argparse
from collections import deque
from pathlib import Path
from statistics import median

from PIL import Image

try:
    from .asset_cleanup import despill_alpha_edges, erode_alpha_boundary
except ImportError:
    from asset_cleanup import despill_alpha_edges, erode_alpha_boundary


SIDE_MARGIN = 16


def is_background_like(rgb):
    r, g, b = rgb
    return max(rgb) - min(rgb) <= 14 and (r + g + b) / 3 >= 218


def remove_border_background(image):
    """删除从边缘连通的浅色棋盘格，避免误删宠物上的白色道具。"""
    rgba = image.convert('RGBA')
    rgb = rgba.convert('RGB')
    width, height = rgba.size
    pixels = rgb.load()
    seen = bytearray(width * height)
    queue = deque()

    def enqueue(x, y):
        index = y * width + x
        if seen[index] or not is_background_like(pixels[x, y]):
            return
        seen[index] = 1
        queue.append((x, y))

    for x in range(width):
        enqueue(x, 0)
        enqueue(x, height - 1)
    for y in range(height):
        enqueue(0, y)
        enqueue(width - 1, y)

    while queue:
        x, y = queue.popleft()
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < width and 0 <= ny < height:
                enqueue(nx, ny)

    out = rgba.copy()
    alpha = out.getchannel('A')
    alpha_pixels = alpha.load()
    for index, marked in enumerate(seen):
        if marked:
            alpha_pixels[index % width, index // width] = 0
    out.putalpha(alpha)
    return out


def trim_alpha(image):
    bbox = image.getchannel('A').getbbox()
    return image.crop(bbox) if bbox else None


def connected_components(image):
    """返回透明背景之外的 8 连通组件。

    动作条中的每个姿势不一定严格落在自己的等宽 panel 内。先在整张
    动作条上找完整组件，再按组件与 panel 的重叠面积归属帧，才能避免
    在姿势已经越过分割线时先把它从中间切断。
    """
    alpha = image.getchannel('A')
    width, height = image.size
    values = alpha.load()
    seen = bytearray(width * height)
    components = []

    for y in range(height):
        for x in range(width):
            index = y * width + x
            if seen[index] or values[x, y] == 0:
                continue
            seen[index] = 1
            queue = deque([(x, y)])
            pixels = []
            min_x = max_x = x
            min_y = max_y = y
            while queue:
                cx, cy = queue.popleft()
                pixels.append((cx, cy))
                min_x = min(min_x, cx)
                max_x = max(max_x, cx)
                min_y = min(min_y, cy)
                max_y = max(max_y, cy)
                for nx in range(cx - 1, cx + 2):
                    for ny in range(cy - 1, cy + 2):
                        if not (0 <= nx < width and 0 <= ny < height):
                            continue
                        nindex = ny * width + nx
                        if seen[nindex] or values[nx, ny] == 0:
                            continue
                        seen[nindex] = 1
                        queue.append((nx, ny))
            components.append({
                'size': len(pixels),
                'bbox': (min_x, min_y, max_x, max_y),
                'pixels': pixels,
            })
    return components


def _panel_overlap(bbox, left, right):
    """计算组件 bbox 与半开区间 [left, right) 的水平重叠宽度。"""
    return max(0, min(bbox[2] + 1, right) - max(bbox[0], left))


def extract_frame_components(strip, frame_count, index, margin=48,
                             components=None):
    """从完整动作条中提取第 ``index`` 帧的完整主体组件。

    生成模型输出的动作条经常让姿势略微越过等宽分割线。直接 crop 会
    产生笔直的透明硬边；这里先完成连通组件分析，再把组件分配给重叠
    面积最大的 panel，最后只保留该帧的组件。
    """
    width, height = strip.size
    panel_left = round(index * width / frame_count)
    panel_right = round((index + 1) * width / frame_count)
    if components is None:
        components = connected_components(strip)
    if not components:
        return None

    assigned = []
    for component in components:
        bbox = component['bbox']
        overlaps = [
            _panel_overlap(
                bbox,
                round(frame * width / frame_count),
                round((frame + 1) * width / frame_count),
            )
            for frame in range(frame_count)
        ]
        owner = max(
            range(frame_count),
            key=lambda frame: (
                overlaps[frame],
                -abs((bbox[0] + bbox[2] + 1) / 2
                     - (round(frame * width / frame_count)
                        + round((frame + 1) * width / frame_count)) / 2),
                component['size'],
            ),
        )
        if owner == index:
            assigned.append(component)

    if not assigned:
        return None

    main = max(assigned, key=lambda component: component['size'])
    main_bbox = main['bbox']
    expanded = (
        main_bbox[0] - margin,
        main_bbox[1] - margin,
        main_bbox[2] + margin,
        main_bbox[3] + margin,
    )
    upper_limit = main_bbox[1] + (main_bbox[3] - main_bbox[1]) * 0.62

    keep = Image.new('L', (width, height), 0)
    keep_pixels = keep.load()
    for component in assigned:
        bbox = component['bbox']
        near_main = not (
            bbox[2] < expanded[0] or bbox[0] > expanded[2]
            or bbox[3] < expanded[1] or bbox[1] > expanded[3]
        )
        is_main = component is main
        if near_main and (is_main or bbox[1] <= upper_limit):
            for x, y in component['pixels']:
                keep_pixels[x, y] = 255

    out = strip.copy()
    out.putalpha(keep)
    return trim_alpha(out)


def infer_reference(reference_dir):
    """读取标准画布和可见角色高度，避免动作帧切换时缩放跳变。"""
    reference_dir = Path(reference_dir)
    frames = sorted(reference_dir.glob('frame_*.png'))
    if not frames:
        raise ValueError(f'参考目录没有 frame_*.png: {reference_dir}')
    heights = []
    bottom_margins = []
    with Image.open(frames[0]) as image:
        target_size = image.size
    for frame in frames:
        with Image.open(frame).convert('RGBA') as image:
            bbox = image.getchannel('A').getbbox()
        if bbox:
            heights.append(bbox[3] - bbox[1])
            bottom_margins.append(target_size[1] - bbox[3])
    if not heights:
        raise ValueError(f'参考目录没有可见角色: {reference_dir}')
    return target_size, round(median(heights)), round(median(bottom_margins))


def keep_main_components(image, margin=48):
    """移除相邻面板越界残片，同时保留嘴边道具和头边睡眠标记。"""
    width, height = image.size
    components = [
        (component['size'], component['bbox'], component['pixels'])
        for component in connected_components(image)
    ]

    if not components:
        return image
    components.sort(key=lambda item: item[0], reverse=True)
    main_bbox = components[0][1]
    expanded = (main_bbox[0] - margin, main_bbox[1] - margin,
                main_bbox[2] + margin, main_bbox[3] + margin)
    upper_limit = main_bbox[1] + (main_bbox[3] - main_bbox[1]) * 0.62
    keep = Image.new('L', (width, height), 0)
    keep_pixels = keep.load()
    for _, bbox, pixels in components:
        near_main = not (bbox[2] < expanded[0] or bbox[0] > expanded[2] or
                         bbox[3] < expanded[1] or bbox[1] > expanded[3])
        # 非主体组件只能位于头部/嘴部附近，避免把生成器误放在脚边的骨头、
        # 颗粒或相邻面板残片带入动作帧。主体组件本身不受此限制。
        is_main = bbox == main_bbox
        # 动作条相邻面板的残片通常会贴在当前 panel 的最左/最右边缘；
        # 道具不应跨越动作条分隔线，因此这类非主体组件直接丢弃。
        touches_panel_edge = bbox[0] <= 1 or bbox[2] >= width - 2
        if not is_main and touches_panel_edge:
            continue
        if near_main and (is_main or bbox[1] <= upper_limit):
            for x, y in pixels:
                keep_pixels[x, y] = 255
    out = image.copy()
    out.putalpha(keep)
    return out


def remove_edge_fringe(image, passes=3, brightness=195, spread=115):
    """去除白底抠图留下的浅色边缘光晕，不影响主体内部高光。

    只处理与透明区域相邻、且接近动作条背景色的像素，并重复几轮，
    让毛发边缘从外向内自然收紧。骨头等白色道具只会被削掉极薄外沿。
    """
    out = image.convert('RGBA')
    pixels = out.load()
    width, height = out.size
    for _ in range(passes):
        remove = []
        for y in range(height):
            for x in range(width):
                r, g, b, alpha = pixels[x, y]
                if alpha == 0:
                    continue
                adjacent_to_transparent = any(
                    0 <= nx < width and 0 <= ny < height
                    and pixels[nx, ny][3] == 0
                    for nx, ny in ((x - 1, y), (x + 1, y),
                                   (x, y - 1), (x, y + 1)))
                if not adjacent_to_transparent:
                    continue
                if ((r + g + b) / 3 >= brightness
                        and max(r, g, b) - min(r, g, b) <= spread):
                    remove.append((x, y))
        for x, y in remove:
            pixels[x, y] = (0, 0, 0, 0)
    return out


def install(strip_path, output_dir, frame_count, target_size,
            component_margin=48, reference_dir=None,
            target_visible_height=None, target_bottom_margin=None):
    if reference_dir is not None:
        (target_size, reference_visible_height,
         reference_bottom_margin) = infer_reference(reference_dir)
        if target_visible_height is None:
            target_visible_height = reference_visible_height
        if target_bottom_margin is None:
            target_bottom_margin = reference_bottom_margin
    strip = remove_border_background(Image.open(strip_path))
    width, height = strip.size
    strip_components = connected_components(strip)
    panels = []
    for index in range(frame_count):
        # 先按完整主体组件提取，再做边缘清理。不能先 crop，否则姿势
        # 越过等宽分割线的部分已经丢失，后续处理无法恢复。
        panel = extract_frame_components(
            strip, frame_count, index, margin=component_margin,
            components=strip_components)
        if panel is None:
            # 兼容空白背景或组件检测失败的异常素材，同时保留明确报错。
            x0 = round(index * width / frame_count)
            x1 = round((index + 1) * width / frame_count)
            panel = strip.crop((x0, 0, x1, height))
        panel = remove_edge_fringe(panel)
        panel = despill_alpha_edges(panel)
        panel = keep_main_components(panel, margin=component_margin)
        panel = erode_alpha_boundary(panel, passes=2)
        panel = trim_alpha(panel)
        if panel is None:
            raise ValueError(f'第 {index + 1} 帧为空')
        panels.append(panel)

    # 以动作条中最高的角色作为统一尺度，避免逐帧缩放造成大小跳动。
    max_width = max(panel.width for panel in panels)
    max_height = max(panel.height for panel in panels)
    target_width, target_height = target_size
    height_limit = (target_visible_height
                    if target_visible_height is not None else target_height - 4)
    scale = min(1.0, (target_width - SIDE_MARGIN * 2) / max_width,
                height_limit / max_height)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for index, panel in enumerate(panels, 1):
        size = (max(1, round(panel.width * scale)),
                max(1, round(panel.height * scale)))
        sprite = panel.resize(size, Image.Resampling.LANCZOS)
        canvas = Image.new('RGBA', target_size, (0, 0, 0, 0))
        x = (target_width - sprite.width) // 2
        y = target_height - (target_bottom_margin or 0) - sprite.height
        canvas.alpha_composite(sprite, (x, y))
        despill_alpha_edges(canvas).save(
            output_dir / f'frame_{index:03d}.png')

    return {
        'strip': str(strip_path),
        'frames': frame_count,
        'panel_widths': [round((i + 1) * width / frame_count) -
                         round(i * width / frame_count)
                         for i in range(frame_count)],
        'strip_height': height,
        'target_size': list(target_size),
        'target_visible_height': target_visible_height,
        'scale': scale,
        'max_source_width': max_width,
        'max_source_height': max_height,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--strip', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--frames', required=True, type=int)
    parser.add_argument('--target-width', type=int)
    parser.add_argument('--target-height', type=int)
    parser.add_argument(
        '--reference-dir', type=Path,
        help='从已有状态目录（通常是 idle）继承标准帧画布尺寸')
    parser.add_argument(
        '--target-visible-height', type=int,
        help='限制动作帧的可见角色高度；不提供时从 --reference-dir 推断')
    parser.add_argument(
        '--target-bottom-margin', type=int,
        help='保留参考帧脚底到画布底部的透明边距；不提供时从 --reference-dir 推断')
    parser.add_argument('--component-margin', type=int, default=48)
    args = parser.parse_args()
    if args.reference_dir is None and (
            args.target_width is None or args.target_height is None):
        parser.error('请同时提供 --target-width/--target-height，或提供 --reference-dir')
    target_size = ((args.target_width, args.target_height)
                   if args.reference_dir is None else None)
    result = install(args.strip, args.output_dir, args.frames,
                     target_size,
                     component_margin=args.component_margin,
                     reference_dir=args.reference_dir,
                     target_visible_height=args.target_visible_height,
                     target_bottom_margin=args.target_bottom_margin)
    print(result)


if __name__ == '__main__':
    main()

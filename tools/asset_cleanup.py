# -*- coding: utf-8 -*-
"""运行时透明 PNG 的边缘去杂色与安全画布处理。"""
from PIL import Image


def despill_alpha_edges(image, radius=4):
    """修复透明抗锯齿像素携带的黑/白底色，不改变 alpha 轮廓。

    生成器通常会先在白底或深色边缘上抗锯齿，再写入透明 PNG。若只清除
    alpha 而保留原 RGB，Qt 在桌面背景上合成时会出现黑边或白边。这里仅对
    接触透明区域的半透明像素，用最近的实心主体颜色重建 RGB；完全透明像素
    的 RGB 也归零，避免后续缩放或翻转重新采样出隐藏底色。
    """
    source = image.convert('RGBA')
    output = source.copy()
    src = source.load()
    dst = output.load()
    width, height = source.size

    for y in range(height):
        for x in range(width):
            red, green, blue, alpha = src[x, y]
            if alpha == 0:
                dst[x, y] = (0, 0, 0, 0)
                continue
            if alpha >= 255:
                continue
            touches_transparent = any(
                0 <= nx < width and 0 <= ny < height
                and src[nx, ny][3] == 0
                for nx, ny in ((x - 1, y), (x + 1, y),
                               (x, y - 1), (x, y + 1)))
            if not touches_transparent:
                continue

            replacement = None
            for distance in range(1, radius + 1):
                samples = []
                for nx in range(max(0, x - distance),
                                min(width, x + distance + 1)):
                    for ny in range(max(0, y - distance),
                                    min(height, y + distance + 1)):
                        if max(abs(nx - x), abs(ny - y)) != distance:
                            continue
                        red2, green2, blue2, alpha2 = src[nx, ny]
                        if alpha2 >= 245:
                            samples.append((red2, green2, blue2))
                if samples:
                    replacement = tuple(
                        round(sum(sample[channel] for sample in samples)
                              / len(samples))
                        for channel in range(3))
                    break
            if replacement is not None:
                dst[x, y] = (*replacement, alpha)
    return output


def erode_alpha_boundary(image, passes=2):
    """向内收紧透明边界，移除抠图时烘焙进去的浅色外轮廓。

    这一步只删除每轮中直接接触透明区的像素，不会改变主体内部颜色；
    对运行时小尺寸缩放而言，两个源像素约等于一个显示像素，能消除
    白底/灰底抠图常见的最后一圈可见光晕。
    """
    output = image.convert('RGBA')
    width, height = output.size
    for _ in range(max(0, passes)):
        source = output.copy()
        src = source.load()
        dst = output.load()
        remove = []
        for y in range(height):
            for x in range(width):
                if src[x, y][3] == 0:
                    continue
                if any(
                        0 <= nx < width and 0 <= ny < height
                        and src[nx, ny][3] == 0
                        for nx, ny in ((x - 1, y), (x + 1, y),
                                       (x, y - 1), (x, y + 1))):
                    remove.append((x, y))
        for x, y in remove:
            dst[x, y] = (0, 0, 0, 0)
    return output


def repack_visible_frame(image, canvas_size, top_margin=48,
                         bottom_margin=16, side_margin=16):
    """把可见主体重新放进统一透明画布，并固定脚底基线。

    先裁出可见区域再居中放置，避免旧画布中不一致的顶部偏移继续传递。
    ``top_margin`` 是所有动作帧都必须满足的最小顶部安全区；若素材本身
    太高，直接报错而不静默裁切。
    """
    source = image.convert('RGBA')
    bbox = source.getchannel('A').getbbox()
    if bbox is None:
        raise ValueError('素材帧没有可见像素')
    sprite = source.crop(bbox)
    width, height = canvas_size
    if sprite.width > width - side_margin * 2:
        raise ValueError(
            f'素材宽度 {sprite.width} 超过画布安全宽度 {width - side_margin * 2}')
    y = height - bottom_margin - sprite.height
    if y < top_margin:
        raise ValueError(
            f'素材高度 {sprite.height} 无法同时满足顶部 {top_margin}px '
            f'与底部 {bottom_margin}px 安全区（画布 {canvas_size}）')
    x = (width - sprite.width) // 2
    canvas = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    canvas.alpha_composite(sprite, (x, y))
    return canvas


def add_transparent_padding(image, padding_x=16, padding_y=16,
                            padding_top=None, padding_bottom=None):
    """增加透明安全区；可单独指定顶部和底部边距。"""
    image = image.convert('RGBA')
    if padding_top is None:
        padding_top = padding_y
    if padding_bottom is None:
        padding_bottom = padding_y
    width, height = image.size
    canvas = Image.new(
        'RGBA',
        (width + padding_x * 2, height + padding_top + padding_bottom),
        (0, 0, 0, 0),
    )
    canvas.alpha_composite(image, (padding_x, padding_top))
    return canvas


def normalize_runtime_frame(image, padding_x=16, padding_y=16,
                            top_margin=48, bottom_margin=16):
    """统一处理一帧新生成素材，并建立足够的顶部安全区。"""
    cleaned = erode_alpha_boundary(
        despill_alpha_edges(image), passes=2)
    source = cleaned.convert('RGBA')
    width, height = source.size
    canvas_size = (width + padding_x * 2,
                   height + top_margin + bottom_margin)
    return repack_visible_frame(
        cleaned, canvas_size, top_margin=top_margin,
        bottom_margin=bottom_margin, side_margin=padding_x)

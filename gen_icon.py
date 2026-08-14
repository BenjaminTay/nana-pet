# -*- coding: utf-8 -*-
"""单独重新生成 icon.ico（不动全套动画帧）：256px 渐变圆角底母版 → 7 档尺寸。
实现细节见 gen_assets_nana.build_icon_canvas / write_ico。"""
import json
import os
import shutil
import subprocess
import tempfile
import sys

from PIL import Image

from gen_assets_nana import build_icon_canvas, load_master, write_ico

BASE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(BASE, 'assets')
SIZES = (16, 24, 32, 48, 64, 128, 256)

master, _ = load_master()
head = json.load(open(os.path.join(ASSETS, 'head.json'), encoding='utf-8'))['head']
canvas = build_icon_canvas(master, head, 256)
write_ico(os.path.join(ASSETS, 'icon.ico'),
          [(s, canvas.resize((s, s), Image.LANCZOS)) for s in SIZES])
canvas.save(os.path.join(ASSETS, 'icon.png'))   # macOS 运行时/构建用 png

if sys.platform == 'darwin' and shutil.which('sips') and shutil.which('iconutil'):
    with tempfile.TemporaryDirectory(prefix='nanadog-icon-') as tmp:
        iconset = os.path.join(tmp, 'icon.iconset')
        os.makedirs(iconset)
        for size, retina_size in ((16, 32), (32, 64), (128, 256),
                                  (256, 512), (512, 1024)):
            subprocess.run([
                'sips', '-z', str(size), str(size), os.path.join(ASSETS, 'icon.png'),
                '--out', os.path.join(iconset, f'icon_{size}x{size}.png')],
                check=True, stdout=subprocess.DEVNULL)
            subprocess.run([
                'sips', '-z', str(retina_size), str(retina_size),
                os.path.join(ASSETS, 'icon.png'), '--out',
                os.path.join(iconset, f'icon_{size}x{size}@2x.png')],
                check=True, stdout=subprocess.DEVNULL)
        subprocess.run([
            'iconutil', '-c', 'icns', iconset, '-o',
            os.path.join(ASSETS, 'icon.icns')], check=True)

print('icon 重生成:', list(SIZES), '+ icon.png'
      + (' + icon.icns' if sys.platform == 'darwin' else ''))

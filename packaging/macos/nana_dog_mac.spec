# -*- mode: python ; coding: utf-8 -*-
"""NANA DOG macOS .app bundle.

Build on macOS with:
    python -m PyInstaller --clean --noconfirm packaging/macos/nana_dog_mac.spec
"""

import os

SPEC_DIR = os.path.abspath(SPECPATH)
PROJECT_ROOT = os.path.abspath(os.path.join(SPEC_DIR, '..', '..'))
with open(os.path.join(PROJECT_ROOT, 'VERSION'), encoding='utf-8') as version_file:
    APP_VERSION = version_file.read().strip()

a = Analysis(
    [os.path.join(PROJECT_ROOT, 'main.py')],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=[(os.path.join(PROJECT_ROOT, 'assets'), 'assets')],
    hiddenimports=['objc', 'AppKit', 'Foundation', 'Quartz'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='NANA DOG',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='NANA DOG',
)

app = BUNDLE(
    coll,
    name='NANA DOG.app',
    icon=os.path.join(PROJECT_ROOT, 'assets', 'icon.icns'),
    bundle_identifier='com.szsqq.nanadog',
    version=APP_VERSION,
    info_plist={
        'CFBundleDisplayName': 'NANA DOG',
        'NSPrincipalClass': 'NSApplication',
        # 桌宠是菜单栏常驻应用，不在 Dock 中显示重复入口。
        'LSUIElement': True,
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '13.0',
        'NSHumanReadableCopyright': 'Copyright © 2026 三青',
    },
)

#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

if [[ -n "${PYTHON:-}" ]]; then
  : # 使用调用方显式指定的解释器。
elif [[ -x ".venv-mac/bin/python" ]]; then
  PYTHON=".venv-mac/bin/python"
else
  PYTHON="python3.12"
fi

if [[ ! -f assets/icon.icns ]]; then
  echo "缺少 assets/icon.icns，先执行：$PYTHON tools/gen_icon.py"
  exit 1
fi

"$PYTHON" -m PyInstaller \
  --clean \
  --noconfirm \
  packaging/macos/nana_dog_mac.spec

echo "构建完成：dist/NANA DOG.app"
echo "启动命令：open 'dist/NANA DOG.app'"

# GitHub Release 不能直接上传目录，因此额外提供一个保留 .app 结构的 ZIP。
ditto -c -k --sequesterRsrc --keepParent \
  "dist/NANA DOG.app" \
  "dist/NANA DOG-macOS-arm64-App.zip"
echo "App ZIP 完成：dist/NANA DOG-macOS-arm64-App.zip"

# 生成可直接分享的 DMG：拖到 Applications 即可安装。
if command -v hdiutil >/dev/null 2>&1; then
  STAGE_DIR="$(mktemp -d)"
  cp -R "dist/NANA DOG.app" "$STAGE_DIR/NANA DOG.app"
  ln -s /Applications "$STAGE_DIR/Applications"
  hdiutil create \
    -volname "NANA DOG" \
    -srcfolder "$STAGE_DIR" \
    -ov \
    -format UDZO \
    "dist/NANA DOG.dmg" >/dev/null
  echo "DMG 完成：dist/NANA DOG.dmg"
fi

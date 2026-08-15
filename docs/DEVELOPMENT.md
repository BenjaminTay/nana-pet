# 开发指南

本文档面向需要从源码运行、测试、打包或维护素材的开发者。普通用户请先阅读项目根目录的 [README.md](../README.md)。

## 环境准备

运行项目需要 Python 3.10+，推荐 Python 3.12。运行时依赖安装方式：

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

打包或重新生成素材时，还需要安装构建依赖：

```bash
python -m pip install -r requirements-build.txt
```

## 测试

本地可以按功能运行测试：

```bash
python tests/test_enhance.py
python tests/test_main.py
python tests/test_mac.py
python tests/test_scale.py
python tests/test_hotkeys.py
python tests/test_animation_assets.py
python tests/test_window_edges.py
```

Windows 原生窗口层级测试需要在 Windows 上运行：

```bash
python tests/test_top.py
python tests/test_zorder.py
```

`test_animation_assets.py` 会检查 Classic/Q 版全部状态的帧数、画布尺寸、透明边缘、安全留白、背景泄漏、idle 回退和 `happy` 动画基线。

## Windows 打包

在 Windows 上可以双击 `packaging/windows/build_standard.bat`，也可以手动执行：

```bat
py -3.12 -m pip install -r requirements-build.txt
py -3.12 -m PyInstaller "packaging\windows\NANA DOG.spec" --noconfirm
py -3.12 -m PyInstaller "packaging\windows\NANA DOG Setup.spec" --noconfirm
```

安装程序输出到 `dist\NANA DOG Setup.exe`，安装后程序位于 `%LOCALAPPDATA%\Programs\NanaDog\`。

## macOS 打包

macOS 使用独立的 spec 和构建脚本，不要使用 Windows 的构建脚本：

```bash
python3.12 -m venv .venv-mac
.venv-mac/bin/python -m pip install -r requirements-build.txt
.venv-mac/bin/python tools/gen_icon.py
./packaging/macos/build_mac.sh
open "dist/NANA DOG.app"
```

构建脚本会生成：

- `dist/NANA DOG.app`
- `dist/NANA DOG.dmg`

如果脚本没有执行权限，先运行：

```bash
chmod +x packaging/macos/build_mac.sh
```

当前 macOS 构建使用 ad-hoc 签名，适合本机验证和技术分享。正式面向其他用户发布前，还需要使用 Developer ID Application 签名并完成 notarization。

## GitHub Actions 与发布

- `CI` 工作流在 Ubuntu、macOS 和 Windows 上运行跨平台测试；Windows 额外运行真实窗口层级测试。
- `Build packages` 工作流可以手动触发，也会在推送 `v*` 标签时运行。
- 推送版本标签后，工作流会构建 macOS arm64 DMG、Windows 安装程序、Windows 便携版 ZIP，并生成 `SHA256SUMS.txt`。
- Release 标题使用 `NANA DOG <tag>`，例如 `NANA DOG v0.2.0`。

发布前建议确认 `VERSION`、`CHANGELOG.md` 和 README 的下载说明保持一致，然后推送版本标签：

```bash
git tag v0.2.0
git push origin v0.2.0
```

## 素材生成与维护

素材生成器需要先安装 `requirements-build.txt`。

### 生成动画帧和图标

```bash
python tools/gen_assets_nana.py
python tools/gen_icon.py
```

生成器支持通过环境变量指定原始素材和输出目录，避免依赖固定路径：

```bash
NANA_MASTER_IMAGE=/absolute/path/to/source.png \
NANA_ASSETS_DIR=/absolute/path/to/nana-pet/assets/skins/classic \
python tools/gen_assets_nana.py
```

Q 版皮肤可以将 `NANA_ASSETS_DIR` 指向 `assets/skins/q`，并设置对应的 `NANA_MASTER_IMAGE`。

### 安装动作条和修复运行时帧

```bash
python tools/install_action_strips.py \
  --strip <动作条.png> \
  --output-dir <状态目录> \
  --frames <帧数> \
  --reference-dir <对应皮肤>/idle

python tools/normalize_runtime_assets.py \
  --assets-dir assets/skins \
  --padding-x 16 \
  --top-margin 48 \
  --bottom-margin 16 \
  --min-canvas-height 444
```

修改动作条后，应运行 `python tests/test_animation_assets.py`，再重新构建 macOS 或 Windows 安装包。

动作优化素材位于 `design/visual-concepts/round-1/action-repairs/`。如需明确回退到程序生成的旧版动作，设置 `NANA_PRESERVE_ACTIONS=0`。

## 项目结构

```text
nana-pet/
├── .github/workflows/       # CI 测试和跨平台构建
├── main.py                  # 入口：托盘、宠物管理和全局快捷键
├── pet.py                   # 兼容入口：导出宠物公共 API
├── nana/                    # 宠物数据、气泡、快捷键和设置模块
├── mac_native.py            # macOS 窗口层级与 Quartz 快捷键
├── config.py                # 配置读写和开机自启
├── assets/                  # 运行时素材、皮肤、图标和语录
├── assets_raw/              # 素材生成输入
├── design/                  # 视觉概念和验收素材
├── tests/                   # 交互、平台、缩放、快捷键和素材测试
├── tools/                   # 素材帧和图标生成工具
├── packaging/               # Windows/macOS 打包配置与脚本
├── VERSION                 # 当前发布版本
├── ASSET_LICENSE.md        # 素材与源码许可证边界
└── CHANGELOG.md            # 版本更新记录
```

运行数据不应提交到仓库。Windows 安装版和 macOS 版的日志、配置目录见根目录 [README.md](../README.md) 的“数据与设置”章节。

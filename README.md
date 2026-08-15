# NANA DOG 那艺娜小狗桌宠

一只住在你桌面右下角的小狗。AI 状态机驱动，15 种状态、100 条语录与情绪联动，
会发呆、会蹦跶、会害羞，饿了自己喊，整点说应景的话，支持多只共存。

## 功能特性

- 🐶 **15 种状态**：发呆 / 走路 / 跑步 / 跳跃 / 坐着 / 睡觉 / 跳舞 / 吃饭 / 开心 / 生气 / 难过 / 大哭 / 转圈 / 唱歌 / 害羞
- 💬 **情绪语录**：100 条原创语录（`assets/quotes.txt`），按情绪匹配，气泡手绘样式，与状态表情联动
- ⏰ **每日问候**：每天第一次启动时问好（只有第一只说，避免合唱）
- 🎁 **整点彩蛋**：每小时一条应景语录，不打扰隐藏/睡觉中的宠物
- 🍖 **喂食系统**：喂狗粮重置饥饿计时，太久没喂会喊饿
- ⌨️ **全局快捷键**：Windows 和 macOS 均支持跳舞 / 喂食 / 复位 / 隐藏 / 说话 / 置顶 / 穿透 / 添加，并可在设置里自定义
- 🖼 **多只共存**：任意添加多只，位置自动错开，各自记住自己的位置、大小、喂食时间
- 🔍 **连续缩放**：右键宠物使用滑块或预设大小；macOS 按住 `Option`、Windows 按住 `Alt` 滚轮缩放
- 🎨 **可切换形象**：经典高清版与 Q 版独立皮肤共存，可从宠物右键菜单或托盘菜单切换；每只宠物会记住自己的形象
- 📌 **置顶 / 鼠标穿透**：可开关，穿透后从托盘恢复；气泡与宠物 Z 序严格一致
- 🚀 **开机自启**：托盘菜单一键开关
- 💾 **状态持久化**：位置、精确大小、喂食时间会自动保存，重启恢复

## 环境要求

- Windows 10（1809 或更新）/ Windows 11，64 位
- macOS 13+（当前 PySide6 6.11 构建；源码运行和 `.app` 打包）
- Python 3.10+（推荐 3.12）
- PySide6 ≥ 6.5

运行桌宠安装 `requirements.txt`；打包或重新生成素材时安装
`requirements-build.txt`。

## 快速开始（源码运行）

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

Windows 也可以直接双击 `scripts/run.bat`。macOS 下不要运行这个 bat 脚本，使用上面的命令即可。

## 打包安装包

双击 `packaging/windows/build_standard.bat`（或手动执行）：

```bat
py -3.12 -m pip install -r requirements-build.txt
py -3.12 -m PyInstaller "packaging\windows\NANA DOG.spec" --noconfirm
py -3.12 -m PyInstaller "packaging\windows\NANA DOG Setup.spec" --noconfirm
```

安装程序输出到 `dist\NANA DOG Setup.exe`，脚本会自动复制到桌面。
安装后程序位于 `%LOCALAPPDATA%\Programs\NanaDog\`（免管理员权限，仅当前用户）。

## macOS 打包

在 macOS 上单独构建 `.app`，不要使用 Windows 的构建脚本或 spec：

```bash
python3.12 -m venv .venv-mac
.venv-mac/bin/python -m pip install -r requirements-build.txt
.venv-mac/bin/python tools/gen_icon.py
./packaging/macos/build_mac.sh
open "dist/NANA DOG.app"
```

构建产物为 `dist/NANA DOG.app`。如果系统提示缺少执行权限，先运行：

```bash
chmod +x packaging/macos/build_mac.sh
```

macOS 版使用 `packaging/macos/nana_dog_mac.spec`，运行数据保存在
`~/Library/Application Support/NanaDog/`。macOS 使用 Quartz 全局键盘监听；首次使用需要在“系统设置 → 隐私与安全性 → 辅助功能/输入监控”中允许 NANA DOG。

macOS 菜单栏中新增“显示/恢复全部宠物”，用于宠物被隐藏或窗口暂时不可见时主动恢复。置顶状态通过 macOS 原生 `NSWindow` 浮动层同步到宠物和气泡窗口，并支持跨 Space 显示。

宠物支持 `75%～200%` 连续缩放。右键宠物选择“大小 → 自定义大小…”后，设置窗口会优先显示在宠物侧边，拖动滑块即可实时预览；点击“应用”确认，点击“取消”恢复原大小。也可以在宠物上按住 `Option`（Windows 使用 `Alt`）滚动鼠标滚轮。缩放会保持宠物脚部位置，并自动调整气泡和屏幕边界。

运行期间可以移除全部宠物，程序会继续驻留菜单栏，此时可选择“添加一只”恢复。若在没有宠物时重启程序，应用会自动创建一只默认宠物。

`build_mac.sh` 会同时生成可分享的 `dist/NANA DOG.dmg`，打开后将应用拖入 Applications 即可。

当前 macOS 构建使用 ad-hoc 签名，适合本机验证和技术分享；未配置 Apple Developer
证书与 notarization。正式面向其他用户发布前，还需要使用 Developer ID Application
签名并完成公证，否则 Gatekeeper 可能提示“无法验证开发者”。

## GitHub Actions 自动构建

- `CI` 工作流在 Ubuntu、macOS 和 Windows 上运行跨平台测试；Windows 额外运行真实窗口层级测试。
- `Build packages` 工作流手动触发时只生成 Actions Artifacts；推送 `v*` 标签时会构建并自动创建 GitHub Release。
- Release 会上传 macOS arm64 DMG、Windows 安装程序、Windows 便携版 ZIP 和 `SHA256SUMS.txt`。
- 当前工作流不负责 Apple Developer 签名或公证；macOS 包仍可能触发 Gatekeeper 提示。

## 测试

测试包括离屏交互、连续缩放、macOS 快捷键映射、动画资源边缘与基线检查，以及
Windows 真实窗口层级测试：

```bash
python tests/test_enhance.py
python tests/test_main.py
python tests/test_mac.py
python tests/test_top.py
python tests/test_zorder.py
python tests/test_scale.py
python tests/test_hotkeys.py
python tests/test_animation_assets.py
```

其中 `test_animation_assets.py` 会检查 Classic/Q 版全部状态是否使用统一画布、
是否触碰画布边缘、是否存在明显白底/黑边残留，并额外检查 `happy` 动画的可见
高度与脚底基线。CI 会在 Ubuntu、macOS 和 Windows 上运行跨平台测试。

## 目录结构

```
nana-pet/
├── .github/workflows/    # CI 测试和跨平台构建
├── main.py              # 入口：托盘 + 多宠物管理 + 每日问候 + 全局快捷键
├── pet.py               # 兼容入口：导出 PetWindow 与宠物公共 API
├── nana/                 # 宠物数据、气泡、快捷键和设置模块
├── mac_native.py        # macOS NSWindow 层级与 Quartz 全局快捷键
├── config.py            # 配置读写、开机自启（Windows 注册表 / macOS LaunchAgent）
├── qtcompat.py          # Qt 版本兼容层（enum 命名差异、事件构造）
├── assets/              # 运行时素材：经典素材、皮肤目录、15 个状态帧目录 + head.json + quotes.txt + 图标
├── assets_raw/          # 原始素材图（生成 assets 的输入）
├── design/visual-concepts/ # 应用图标、高清版、Q版的视觉概念与验收素材
├── tests/               # 交互、平台、缩放、快捷键和素材 QA 测试
├── tools/               # 素材帧和图标生成工具
├── packaging/           # Windows / macOS 打包配置与脚本
├── VERSION              # 当前发布版本
├── requirements-build.txt # 打包和素材生成依赖
├── ASSET_LICENSE.md     # 素材与源码许可证边界
├── CHANGELOG.md         # 版本更新记录
└── scripts/             # 日常运行脚本
```

## 数据与配置

| 运行方式 | 配置位置 |
| --- | --- |
| Windows 源码运行 | 源码目录下 `config.json`（首次运行自动生成） |
| 打包安装版 | `%APPDATA%\NanaDog\config.json`，日志在 `%APPDATA%\NanaDog\logs\` |
| macOS 源码/打包版 | `~/Library/Application Support/NanaDog/config.json`，日志在同目录的 `logs/` |

配置内容：宠物列表（id/坐标/大小/精确缩放比例/形象/上次喂食时间）、新增宠物默认形象、穿透、置顶、说话、自启、饥饿小时数、8 组自定义快捷键。

## 素材再生成

素材生成器需要先安装 `requirements-build.txt`。

- 全套动画帧 + 图标：`python tools/gen_assets_nana.py`（读取 `assets_raw/` 与 `assets/head.json`）
- 仅图标：`python tools/gen_icon.py`（优先读取 `design/visual-concepts/round-1/app-icon-v1.png`，输出 `assets/icon.ico`、`assets/icon.png`；macOS 额外输出 `assets/icon.icns`）
- 动作条拆帧与清理：`python tools/install_action_strips.py --strip <动作条.png> --output-dir <状态目录> --frames <帧数> --reference-dir <对应皮肤>/idle`

素材生成器支持通过 `NANA_MASTER_IMAGE` 指定原始素材路径，避免依赖 Windows 固定路径：

```bash
NANA_MASTER_IMAGE=/absolute/path/to/source.png python tools/gen_assets_nana.py
```

如需指定其他图标标准图，可设置 `NANA_ICON_SOURCE=/absolute/path/to/icon.png`。

经典高清版和 Q 版皮肤使用同一个生成器、不同的输出目录。例如：

```bash
NANA_MASTER_IMAGE=/absolute/path/to/classic-master.png \
NANA_ASSETS_DIR=/absolute/path/to/nana-pet/assets/skins/classic \
python tools/gen_assets_nana.py

NANA_MASTER_IMAGE=/absolute/path/to/q-master.png \
NANA_ASSETS_DIR=/absolute/path/to/nana-pet/assets/skins/q \
python tools/gen_assets_nana.py
```

动作优化素材默认不会被全套生成器覆盖；如需明确回退到程序生成的旧版动作，设置 `NANA_PRESERVE_ACTIONS=0`。当前 Classic/Q 版的喂食、跳舞、坐下、睡觉、happy 动作由 `design/visual-concepts/round-1/action-repairs/` 的动作条确定性拆帧安装。安装动作条时应使用对应皮肤的 `idle` 目录作为 `--reference-dir`，让新动作继承同一套画布规格，避免切换时整体缩放。

动作安装器会移除动作条相邻面板残片和透明背景边缘光晕，再以对应皮肤的 idle
帧统一缩放、脚底对齐并写入透明画布。修改动作条后，应运行
`python tests/test_animation_assets.py`，再重新构建 macOS 或 Windows 安装包。

概念素材位于 `design/visual-concepts/round-1/`，当前两套皮肤已经生成并接入运行时；原来的
`assets/` 经典帧目录仍保留，便于回滚和兼容旧环境。

## 开源协议

[MIT License](LICENSE) © 2026 三青

素材与语录的发布边界见 [ASSET_LICENSE.md](ASSET_LICENSE.md)，版本变化见
[CHANGELOG.md](CHANGELOG.md)。

素材（`assets/`、`assets_raw/`）与语录（`assets/quotes.txt`）随仓库一同发布，
如不希望公开可自行替换为占位素材（替换后运行 `gen_assets_nana.py` 重新生成）。

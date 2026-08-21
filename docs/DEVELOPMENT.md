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

运行完整测试时安装测试依赖：

```bash
python -m pip install -r requirements-test.txt
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
python tests/test_quote_modes.py
python tests/test_quote_library.py
```

Windows 原生窗口层级测试需要在 Windows 上运行：

```bash
python tests/test_top.py
python tests/test_zorder.py
```

`test_animation_assets.py` 会检查 Classic/Q 版全部状态的帧数、画布尺寸、透明边缘、安全留白、背景泄漏、idle 回退和 `happy` 动画基线；同时检查待机/跳跃帧的顶部轮廓连续性，避免“画布有透明留白但角色轮廓已经被截断”的问题漏检。

## 语录维护

- 内置语录原文维护在 `assets/quotes.txt`，格式为 `N. 内容`；程序按文件顺序使用 1-based 行号映射，因此维护内置原文时新增语录应追加到文件末尾，不要在中间插入或删除行。普通用户应优先使用“管理语录库”，不要直接修改该只读资源文件。
- `nana/pet_data.py` 的 `QUOTES` 负责运行时场景分组；项目首次启动时使用审核后的默认分类：`adult-only` 19 条、`common` 41 条、`normal-only` 59 条，普通模式共 100 条，成人模式共 60 条。三类不是互斥的两个池子：共用语录会进入两种模式，专属语录只进入对应模式。
- 普通用户不需要编辑代码：从托盘/菜单栏打开“管理语录库”即可使用表格新增、修改、停用/启用和删除语录，也可以调整显示模式和情绪/场景。数据保存到 `config.QUOTE_LIBRARY_FILE` 指向的 `quotes_user.json`，保存后通过原地重建语录池立即生效。
- `assets/quotes.txt` 是只读的内置原文来源；用户编辑不会改写它。停用会保留编号并从抽取池移除，删除会移除记录；“恢复内置审核结果”会重新载入内置默认分类。成人语录不在气泡内额外标注，仍保留原句。
- 配置项 `adult_quotes` 默认开启，也可以从托盘菜单切换：开启时使用“高强度专属 + 双模式共用”，关闭时使用“普通专属 + 双模式共用”；任何历史硬编码语录在显示前也会经过当前模式隔离。旧键名保留用于兼容已有配置。
- 修改语录或分组后，至少运行 `python tests/test_quote_modes.py`、`python tests/test_quote_library.py` 和 `python tests/test_enhance.py`，确认审核分类、用户库读写、运行时热更新、情绪映射、气泡显示和互动触发没有回归。

## 气泡 UI 维护

- 气泡绘制和主题配置统一维护在 `nana/bubble.py`；`PetWindow.say()` 负责把当前宠物状态、成人语录状态和原文传入气泡。
- `Bubble` 保留透明窗口、点击穿透、置顶和尾巴定位接口。修改绘制时不要移除 `tail_bottom`、`tail_frac` 或 `hide_immediately()`，否则会影响窗口层级、边缘翻转和显式隐藏。
- `Bubble.MAX_TEXT_WIDTH` 表示文字绘制区域宽度，不是整个窗口宽度；换行、窗口宽度和 `paintEvent()` 必须共用 `_text_width()` 的边距口径，避免换行结果比实际绘制区域更宽而裁掉末字。
- 气泡位置使用 `nana/pet_window.py` 中的可见素材上下边界锚点，不要改回透明宠物窗口的外框边缘；Classic/Q 版画布的安全留白属于素材布局的一部分。
- 气泡主题按 `normal`、`happy`、`sing`、`angry`、`sad`、`sleep` 区分；成人语录不增加气泡标识、不修改或遮挡原文。
- 连续触发新语录时使用静态更新，只有首次出现和自然超时使用淡入/淡出动画，避免气泡闪烁。
- 修改气泡排版、主题或动画后，运行 `python tests/test_bubble_ui.py`；该测试包含长句换行、实际绘制区域、截图同款中文长句和屏幕边缘定位检查。并回归 `python tests/test_enhance.py`、`python tests/test_main.py`、`python tests/test_top.py` 和 `python tests/test_zorder.py`。

## Windows 打包

在 Windows 上可以双击 `packaging/windows/build_standard.bat`，也可以手动执行：

```bat
py -3.12 -m pip install -r requirements-build.txt
py -3.12 -m PyInstaller "packaging\windows\NANA DOG.spec" --noconfirm
py -3.12 -m PyInstaller "packaging\windows\NANA DOG Portable.spec" --noconfirm
py -3.12 -m PyInstaller "packaging\windows\NANA DOG Setup.spec" --noconfirm
```

构建会生成：

- `dist\NANA DOG\`：文件夹版程序本体，可压缩后便携运行；
- `dist\NANA DOG Portable.exe`：单文件便携版，启动时会先解压依赖；
- `dist\NANA DOG Setup.exe`：安装程序，安装后程序位于 `%LOCALAPPDATA%\NanaDog\`。

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
- `dist/NANA DOG-macOS-arm64-App.zip`：保留 `.app` 结构的直接运行分享包；
- `dist/NANA DOG.dmg`

如果脚本没有执行权限，先运行：

```bash
chmod +x packaging/macos/build_mac.sh
```

当前 macOS 构建使用 ad-hoc 签名，适合本机验证和技术分享。正式面向其他用户发布前，还需要使用 Developer ID Application 签名并完成 notarization。

## GitHub Actions 与发布

- `CI` 工作流在 Ubuntu、macOS 和 Windows 上运行跨平台测试；Windows 额外运行真实窗口层级测试。
- `Build packages` 工作流可以手动触发，也会在推送 `v*` 标签时运行。
- 推送版本标签后，工作流会构建 macOS arm64 DMG、macOS App ZIP、Windows 安装程序、Windows 单文件便携版 EXE、Windows 文件夹便携版 ZIP，并生成 `SHA256SUMS.txt`。
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

python tools/repair_top_cropped_frames.py --assets-dir assets/skins
```

macOS 的宠物和气泡使用透明无边框 `NSWindow`。`mac_native.apply_window_level()` 必须关闭 AppKit 默认的原生窗口阴影（`hasShadow=False`）：AppKit 会沿透明窗口的 alpha 轮廓生成阴影，运行时会在白底上形成素材中不存在的黑色描边；气泡的阴影由自身绘制逻辑负责。修改窗口层级或恢复显示逻辑时，要保留这项设置。

放大帧必须先保留完整 sprite，再由透明画布按脚底对齐；不要把超过母图尺寸的放大帧用负坐标粘回固定尺寸临时画布。旧帧若已经丢失顶部像素，重新增加透明留白无法恢复，应使用同动作的完整参考帧运行 `repair_top_cropped_frames.py` 后再验收。

修改动作条后，应运行 `python tests/test_animation_assets.py`，再重新构建 macOS 或 Windows 安装包。

动作优化素材位于 `design/visual-concepts/round-1/action-repairs/`。如需明确回退到程序生成的旧版动作，设置 `NANA_PRESERVE_ACTIONS=0`。

## 项目结构

```text
nana-pet/
├── .github/workflows/       # CI 测试和跨平台构建
├── main.py                  # 入口：托盘、宠物管理和全局快捷键
├── pet.py                   # 兼容入口：导出宠物公共 API
├── nana/                    # 宠物数据、气泡、语录库、快捷键和设置模块
│   └── quote_library_dialog.py  # 语录库表格编辑器
├── mac_native.py            # macOS 窗口层级与 Quartz 快捷键
├── config.py                # 配置读写和开机自启
├── assets/                  # 运行时素材、皮肤、图标和语录
├── assets_raw/              # 素材生成输入
├── design/                  # 视觉概念和验收素材
├── tests/                   # 交互、平台、缩放、语录、快捷键和素材测试
├── tools/                   # 素材帧和图标生成工具
├── packaging/               # Windows/macOS 打包配置与脚本
├── requirements-test.txt   # CI 和本地测试依赖
├── VERSION                 # 当前发布版本
├── ASSET_LICENSE.md        # 素材与源码许可证边界
└── CHANGELOG.md            # 版本更新记录
```

运行数据不应提交到仓库。Windows 安装版和 macOS 版的日志、配置目录见根目录 [README.md](../README.md) 的“数据与设置”章节。

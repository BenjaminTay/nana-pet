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
- 📌 **置顶 / 鼠标穿透**：可开关，穿透后从托盘恢复；气泡与宠物 Z 序严格一致
- 🚀 **开机自启**：托盘菜单一键开关
- 💾 **状态持久化**：位置、大小、喂食时间 30 秒自动保存，重启恢复

## 环境要求

- Windows 10（1809 或更新）/ Windows 11，64 位
- macOS 13+（当前 PySide6 6.11 构建；源码运行和 `.app` 打包）
- Python 3.10+（推荐 3.12）
- PySide6 ≥ 6.5

## 快速开始（源码运行）

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

Windows 也可以直接双击 `run.bat`。macOS 下不要运行 `run.bat`，使用上面的命令即可。

## 打包安装包

双击 `build_standard.bat`（或手动执行）：

```bat
py -3.12 -m PyInstaller "NANA DOG.spec" --noconfirm          :: ① 程序本体（onedir）
py -3.12 -m PyInstaller "NANA DOG Setup.spec" --noconfirm    :: ② 安装程序（onefile，内嵌本体）
```

安装程序输出到 `dist\NANA DOG Setup.exe`，脚本会自动复制到桌面。
安装后程序位于 `%LOCALAPPDATA%\Programs\NanaDog\`（免管理员权限，仅当前用户）。

## macOS 打包

在 macOS 上单独构建 `.app`，不要使用 Windows 的 `build_standard.bat` 或 `NANA DOG Setup.spec`：

```bash
python3.12 -m venv .venv-mac
.venv-mac/bin/python -m pip install -r requirements.txt
.venv-mac/bin/python gen_icon.py
./build_mac.sh
open "dist/NANA DOG.app"
```

构建产物为 `dist/NANA DOG.app`。如果系统提示缺少执行权限，先运行：

```bash
chmod +x build_mac.sh
```

macOS 版使用 `nana_dog_mac.spec`，运行数据保存在
`~/Library/Application Support/NanaDog/`。macOS 使用 Quartz 全局键盘监听；首次使用需要在“系统设置 → 隐私与安全性 → 辅助功能/输入监控”中允许 NANA DOG。

macOS 菜单栏中新增“显示/恢复全部宠物”，用于宠物被隐藏或窗口暂时不可见时主动恢复。置顶状态通过 macOS 原生 `NSWindow` 浮动层同步到宠物和气泡窗口，并支持跨 Space 显示。

`build_mac.sh` 会同时生成可分享的 `dist/NANA DOG.dmg`，打开后将应用拖入 Applications 即可。

## 测试

测试包括离屏交互、macOS 快捷键映射和 Windows 真实窗口层级测试：

```bash
python test_enhance.py
python test_main.py
python test_mac.py
python test_top.py
python test_zorder.py
```

## 目录结构

```
nana-pet/
├── main.py              # 入口：托盘 + 多宠物管理 + 每日问候 + 全局快捷键
├── pet.py               # 宠物窗口：状态机、气泡、拖拽、动画、物理
├── mac_native.py        # macOS NSWindow 层级与 Quartz 全局快捷键
├── config.py            # 配置读写、开机自启（Windows 注册表 / macOS LaunchAgent）
├── qtcompat.py          # Qt 版本兼容层（enum 命名差异、事件构造）
├── installer.py         # 安装程序逻辑（解包安装、进程检测、失败提示）
├── gen_assets_nana.py   # 素材生成器：原始图 → 全套动画帧 + 图标
├── gen_icon.py          # 单独重新生成 icon.ico / icon.png / macOS icon.icns
├── assets/              # 运行时素材：15 个状态帧目录 + head.json + quotes.txt + 图标
├── assets_raw/          # 原始素材图（生成 assets 的输入）
├── test_*.py            # 五套自动化测试
├── NANA DOG.spec        # PyInstaller 配置：程序本体
├── NANA DOG Setup.spec  # PyInstaller 配置：安装程序
├── nana_dog_mac.spec    # PyInstaller 配置：macOS .app
├── build_standard.bat   # 一键打包脚本
├── build_mac.sh         # macOS .app 打包脚本
└── run.bat              # 源码运行脚本
```

## 数据与配置

| 运行方式 | 配置位置 |
| --- | --- |
| Windows 源码运行 | 源码目录下 `config.json`（首次运行自动生成） |
| 打包安装版 | `%APPDATA%\NanaDog\config.json`，日志在 `%APPDATA%\NanaDog\logs\` |
| macOS 源码/打包版 | `~/Library/Application Support/NanaDog/config.json`，日志在同目录的 `logs/` |

配置内容：宠物列表（id/坐标/大小/上次喂食时间）、穿透、置顶、说话、自启、饥饿小时数、8 组自定义快捷键。

## 素材再生成

- 全套动画帧 + 图标：`python gen_assets_nana.py`（读取 `assets_raw/` 与 `head.json`）
- 仅图标：`python gen_icon.py`（输出 `icon.ico`、`icon.png`；macOS 额外输出 `icon.icns`）

素材生成器支持通过 `NANA_MASTER_IMAGE` 指定原始素材路径，避免依赖 Windows 固定路径：

```bash
NANA_MASTER_IMAGE=/absolute/path/to/source.png python gen_assets_nana.py
```

## 开源协议

[MIT License](LICENSE) © 2026 三青

素材（`assets/`、`assets_raw/`）与语录（`assets/quotes.txt`）随仓库一同发布，
如不希望公开可自行替换为占位素材（替换后运行 `gen_assets_nana.py` 重新生成）。

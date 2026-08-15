# NANA DOG

一只住在桌面上的动态小狗，陪你工作、发呆和摸鱼。

NANA DOG 是一个使用 Python + PySide6 编写的桌面宠物，支持 Windows 和 macOS。它会在桌面上自由活动、根据情绪展示动画和语录，也可以通过喂食、点击和快捷键与它互动。

[![CI](https://github.com/BenjaminTay/nana-pet/actions/workflows/ci.yml/badge.svg)](https://github.com/BenjaminTay/nana-pet/actions/workflows/ci.yml)
[![Build packages](https://github.com/BenjaminTay/nana-pet/actions/workflows/build.yml/badge.svg)](https://github.com/BenjaminTay/nana-pet/actions/workflows/build.yml)
[![Latest release](https://img.shields.io/github/v/release/BenjaminTay/nana-pet?display_name=tag&sort=semver)](https://github.com/BenjaminTay/nana-pet/releases)

<p>
  <img src="assets/icon.png" width="160" alt="NANA DOG 图标">
</p>

## 功能亮点

- 🐶 **15 种动态状态**：发呆、走路、跑步、跳跃、睡觉、跳舞、吃饭以及多种情绪动作。
- 🎨 **两套独立形象**：经典高清版与 Q 版，每只宠物可以记住自己的形象。
- 💬 **情绪语录与互动**：点击、长按、喂食和定时事件都会触发不同回应，并支持托盘中的“成人语录”模式。
- 🐾 **多只宠物共存**：可以添加多只宠物，分别记住位置、大小、形象和喂食时间。
- ⌨️ **全局快捷键**：支持跳舞、喂食、复位、隐藏、说话、置顶、穿透和添加宠物。
- 🖱️ **自由调整**：支持拖拽、连续缩放、置顶和鼠标穿透。
- 🚀 **后台常驻**：Windows 使用系统托盘，macOS 使用菜单栏，并支持开机自启。

## 下载

前往 [GitHub Releases](https://github.com/BenjaminTay/nana-pet/releases) 下载适合你系统的版本：

| 平台 | 安装包 | 说明 |
| --- | --- | --- |
| Windows 10/11（64 位） | `NANA DOG-Windows-Setup.exe` | 推荐，安装到当前用户目录，无需管理员权限 |
| Windows 10/11（64 位） | `NANA DOG-Windows-Portable.zip` | 解压后直接运行 |
| macOS 13+（Apple Silicon） | `NANA DOG-macOS-arm64.dmg` | 打开后将应用拖入 Applications |

版本标签推送后，GitHub Actions 会自动构建以上安装包，并生成 `SHA256SUMS.txt` 校验文件。

## 从源码运行

需要 Python 3.10 或更高版本，推荐 Python 3.12。

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

Windows 也可以直接运行：

```bat
scripts\run.bat
```

源码运行支持 Windows 和 macOS；Linux 目前仅用于 CI 测试，不是正式桌面运行目标。

## 基本操作

| 操作 | 方式 |
| --- | --- |
| 移动宠物 | 拖动宠物 |
| 打开操作菜单 | 右键宠物 |
| 喂食、说话或触发动作 | 使用右键菜单、托盘/菜单栏菜单或全局快捷键 |
| 调整大小 | 右键菜单中的“大小”，或按住 Windows `Alt` / macOS `Option` 滚动鼠标滚轮 |
| 添加宠物 | 从托盘/菜单栏菜单选择“添加一只” |
| 恢复隐藏的宠物 | 从托盘/菜单栏菜单选择“显示/恢复全部宠物” |

macOS 首次使用全局快捷键时，需要在“系统设置 → 隐私与安全性 → 辅助功能/输入监控”中允许 NANA DOG。当前 macOS 构建为 ad-hoc 签名，其他设备首次打开时可能出现 Gatekeeper 提示。

## 数据与设置

宠物的位置、大小、形象、喂食时间、鼠标穿透、置顶、成人语录、开机自启和快捷键会自动保存。

| 运行方式 | 配置位置 |
| --- | --- |
| Windows 源码运行 | 项目目录下的 `config.json` |
| Windows 安装版 | `%APPDATA%\\NanaDog\\config.json` |
| macOS 源码或安装版 | `~/Library/Application Support/NanaDog/config.json` |

## 开发与构建

开发环境、测试、Windows/macOS 打包、GitHub Actions、素材生成和动画资源验收说明见 [开发指南](docs/DEVELOPMENT.md)。

版本变化见 [CHANGELOG.md](CHANGELOG.md)。

## 许可证与素材

源码使用 [MIT License](LICENSE)。素材、皮肤和语录的发布边界见 [ASSET_LICENSE.md](ASSET_LICENSE.md)。

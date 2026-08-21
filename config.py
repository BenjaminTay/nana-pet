# -*- coding: utf-8 -*-
"""配置读写：宠物位置/大小/喂食时间、说话、穿透、自启（Win/mac 双平台）"""
import json
import math
import os
import plistlib
import sys

FROZEN = getattr(sys, 'frozen', False)
IS_MAC = sys.platform == 'darwin'

def _resource_base_dir():
    """定位源码和 PyInstaller macOS/Windows 包中的资源根目录。

    PyInstaller 在不同模式下可能让 ``__file__``、``sys._MEIPASS`` 和
    ``sys.executable`` 分别落在 Resources、临时解压目录或可执行文件目录。
    只依赖其中一个路径会让皮肤目录找不到，随后回退到旧版 ``assets/``，
    重新显示未经边缘清理的素材。优先选择实际包含运行时资源的候选目录。
    """
    module_dir = os.path.dirname(os.path.abspath(__file__))
    executable_dir = os.path.dirname(os.path.abspath(sys.executable))
    candidates = [
        module_dir,
        getattr(sys, '_MEIPASS', None),
        executable_dir,
        os.path.join(executable_dir, os.pardir, 'Resources'),
        os.path.join(executable_dir, os.pardir, '_internal'),
    ]
    seen = set()
    for candidate in candidates:
        if not candidate:
            continue
        candidate = os.path.abspath(candidate)
        if candidate in seen:
            continue
        seen.add(candidate)
        if os.path.isfile(os.path.join(candidate, 'assets', 'quotes.txt')):
            return candidate
    return module_dir


# 优先从真正包含 assets/quotes.txt 的目录定位 PyInstaller 只读资源。
BASE_DIR = _resource_base_dir()

if IS_MAC:
    # 应用包可能位于只读目录，用户数据不能写进 .app。
    DATA_DIR = os.path.join(os.path.expanduser('~'), 'Library',
                            'Application Support', 'NanaDog')
elif FROZEN:
    # Windows 打包版：用户数据放在 %APPDATA%\NanaDog。
    DATA_DIR = os.path.join(
        os.environ.get('APPDATA') or os.path.expanduser('~'), 'NanaDog')
else:
    # Windows 源码运行保持原有行为，便于开发时直接查看 config.json。
    DATA_DIR = BASE_DIR

os.makedirs(DATA_DIR, exist_ok=True)

CONFIG_FILE = os.path.join(DATA_DIR, 'config.json')

SIZE_FACTOR = {'small': 0.4, 'medium': 0.53, 'large': 0.66}   # 对标月薪喵实测尺寸
BASE_SIZE_FACTOR = SIZE_FACTOR['medium']
SCALE_PRESETS = {
    key: factor / BASE_SIZE_FACTOR for key, factor in SIZE_FACTOR.items()
}
MIN_SCALE = 0.75
MAX_SCALE = 2.0
SCALE_STEP = 0.05

WINDOWS_DEFAULT_HOTKEYS = {
    'dance': 'Ctrl+Alt+D',
    'feed': 'Ctrl+Alt+F',
    'reset': 'Ctrl+Alt+R',
    'hide': 'Ctrl+Alt+H',
    'speech': 'Ctrl+Alt+S',
    'top': 'Ctrl+Alt+T',
    'through': 'Ctrl+Alt+P',
    'add': 'Ctrl+Alt+N',
}

MAC_DEFAULT_HOTKEYS = {
    # 使用 Command + Option + Shift，降低与 macOS 系统快捷键冲突的概率。
    'dance': 'Meta+Alt+Shift+D',
    'feed': 'Meta+Alt+Shift+F',
    'reset': 'Meta+Alt+Shift+R',
    'hide': 'Meta+Alt+Shift+H',
    'speech': 'Meta+Alt+Shift+S',
    'top': 'Meta+Alt+Shift+T',
    'through': 'Meta+Alt+Shift+P',
    'add': 'Meta+Alt+Shift+N',
}

PLATFORM_DEFAULT_HOTKEYS = (MAC_DEFAULT_HOTKEYS
                             if IS_MAC else WINDOWS_DEFAULT_HOTKEYS)

DEFAULT_CONFIG = {
    'pets': [],              # [{'id':0,'x':100,'y':100,'size':'medium','last_fed':0}]
    'appearance': 'classic', # 新增宠物默认使用的形象：classic / q
    'click_through': False,
    'autostart': False,
    'speech': True,
    'adult_quotes': True,     # 成人语录池；保留直播破防/粗口，但可从托盘关闭
    'always_on_top': True,   # 置顶显示（关闭后会被窗口挡住）
    'next_id': 0,
    'hungry_hours': 3,       # 几小时没喂就喊饿
    'last_greeting': '',     # 每日问候日期，避免重复
    'hotkeys': PLATFORM_DEFAULT_HOTKEYS,
}


def load():
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
    except Exception:
        cfg = {}
    for k, v in DEFAULT_CONFIG.items():
        if k != 'hotkeys':
            cfg.setdefault(k, v)

    hotkeys = cfg.get('hotkeys')
    if not isinstance(hotkeys, dict):
        hotkeys = {}
    # 旧版 macOS 配置沿用了 Windows 默认键位。只在完整匹配旧默认值时
    # 自动迁移，避免覆盖用户已经自定义的快捷键。
    if IS_MAC and hotkeys == WINDOWS_DEFAULT_HOTKEYS:
        hotkeys = dict(MAC_DEFAULT_HOTKEYS)
    for key, value in PLATFORM_DEFAULT_HOTKEYS.items():
        hotkeys.setdefault(key, value)
    cfg['hotkeys'] = hotkeys
    pets = cfg.get('pets')
    if isinstance(pets, list):
        for pet in pets:
            if isinstance(pet, dict):
                pet.setdefault('scale', scale_from_pet(pet))
    return cfg


def clamp_scale(scale):
    """将用户输入的相对缩放比例限制在安全范围内。"""
    try:
        value = float(scale)
    except (TypeError, ValueError):
        value = 1.0
    if not math.isfinite(value):
        value = 1.0
    return max(MIN_SCALE, min(MAX_SCALE, value))


def scale_for_size(size_key):
    """旧版 small/medium/large 大小键转换为相对默认大小的比例。"""
    return clamp_scale(SCALE_PRESETS.get(size_key, SCALE_PRESETS['medium']))


def scale_from_pet(pet):
    """读取宠物大小；优先使用精确比例，兼容旧版 size 字段。"""
    if isinstance(pet, dict) and 'scale' in pet:
        return clamp_scale(pet.get('scale'))
    if isinstance(pet, dict):
        return scale_for_size(pet.get('size', 'medium'))
    return 1.0


def size_key_for_scale(scale):
    """为精确比例保留一个兼容用的最近预设名称。"""
    value = clamp_scale(scale)
    return min(SCALE_PRESETS,
               key=lambda key: abs(SCALE_PRESETS[key] - value))


def is_preset_scale(scale, size_key):
    """判断精确比例是否对应某个快捷预设。"""
    return math.isclose(clamp_scale(scale), scale_for_size(size_key),
                        rel_tol=0.0, abs_tol=SCALE_STEP / 2)


def save(cfg):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


MAC_LAUNCH_AGENT = os.path.join(os.path.expanduser('~'), 'Library',
                                'LaunchAgents', 'com.szsqq.nanadog.plist')


def get_autostart():
    """查询开机自启状态"""
    if IS_MAC:
        return os.path.exists(MAC_LAUNCH_AGENT)
    if sys.platform != 'win32':
        return False
    import winreg
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r'SOFTWARE\Microsoft\Windows\CurrentVersion\Run',
                             0, winreg.KEY_READ)
        winreg.QueryValueEx(key, 'NanaDog')
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def set_autostart(enabled):
    """设置/取消开机自启：Windows 注册表 Run 项，macOS LaunchAgent plist"""
    if IS_MAC:
        os.makedirs(os.path.dirname(MAC_LAUNCH_AGENT), exist_ok=True)
        if enabled:
            cmd = ([sys.executable]
                   if getattr(sys, 'frozen', False)
                   else [sys.executable, os.path.join(BASE_DIR, 'main.py')])
            plist = {
                'Label': 'com.szsqq.nanadog',
                'ProgramArguments': cmd,
                'RunAtLoad': True,
                'ProcessType': 'Interactive',
            }
            with open(MAC_LAUNCH_AGENT, 'wb') as f:
                plistlib.dump(plist, f, sort_keys=False)
        else:
            try:
                os.remove(MAC_LAUNCH_AGENT)
            except OSError:
                pass
        return
    if sys.platform != 'win32':
        return
    import winreg
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                         r'SOFTWARE\Microsoft\Windows\CurrentVersion\Run',
                         0, winreg.KEY_SET_VALUE)
    if enabled:
        if getattr(sys, 'frozen', False):
            cmd = f'"{sys.executable}"'
        else:
            pythonw = os.path.join(os.path.dirname(sys.executable), 'pythonw.exe')
            cmd = f'"{pythonw}" "{os.path.join(BASE_DIR, "main.py")}"'
        winreg.SetValueEx(key, 'NanaDog', 0, winreg.REG_SZ, cmd)
    else:
        try:
            winreg.DeleteValue(key, 'NanaDog')
        except Exception:
            pass
    winreg.CloseKey(key)

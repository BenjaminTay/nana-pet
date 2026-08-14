# -*- coding: utf-8 -*-
"""NANA DOG 桌宠 - 一键安装器：
解包到 %LOCALAPPDATA%\\NanaDog + 桌面/开始菜单快捷方式 + 卸载入口 + 安装完立即启动
无需管理员权限，所有 Windows 10/11 可用。"""
import base64
import ctypes
import ctypes.wintypes
import os
import shutil
import subprocess
import sys
import time

DISPLAY = 'NANA DOG'                  # 桌面/开始菜单名称
APP_EXE = 'NANA DOG.exe'              # 应用文件名
INSTALL_DIR = os.path.join(
    os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'NanaDog')
SILENT = os.environ.get('NANAPET_SILENT') == '1'   # 测试模式：不弹框

_k32 = ctypes.windll.kernel32 if sys.platform == 'win32' else None
TH32CS_SNAPPROCESS = 0x2
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ('dwSize', ctypes.wintypes.DWORD),
        ('cntUsage', ctypes.wintypes.DWORD),
        ('th32ProcessID', ctypes.wintypes.DWORD),
        ('th32DefaultHeapID', ctypes.c_void_p),
        ('th32ModuleID', ctypes.wintypes.DWORD),
        ('cntThreads', ctypes.wintypes.DWORD),
        ('th32ParentProcessID', ctypes.wintypes.DWORD),
        ('pcPriClassBase', ctypes.c_long),
        ('dwFlags', ctypes.wintypes.DWORD),
        ('szExeFile', ctypes.wintypes.WCHAR * 260),
    ]


def is_running(exe_name):
    """进程快照枚举判断 exe_name 是否在运行。
    不用 tasklist /FI：其过滤器对带空格的文件名解析有 bug（"NANA DOG.exe" 永远匹配不到）。"""
    snap = _k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap == INVALID_HANDLE_VALUE:
        return False
    entry = PROCESSENTRY32W()
    entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
    found = False
    if _k32.Process32FirstW(snap, ctypes.byref(entry)):
        while True:
            if entry.szExeFile == exe_name:
                found = True
                break
            if not _k32.Process32NextW(snap, ctypes.byref(entry)):
                break
    _k32.CloseHandle(snap)
    return found


def resource_dir():
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    return getattr(sys, '_MEIPASS', project_root)


def msg(title, text, icon=0x40):
    if not SILENT:
        ctypes.windll.user32.MessageBoxW(None, text, title, icon)


def powershell(script):
    subprocess.run(['powershell', '-NoProfile', '-NonInteractive',
                    '-Command', script], capture_output=True)


def make_shortcut(lnk_path, target, icon, workdir):
    ps = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{lnk}');"
          "$s.TargetPath='{tgt}';$s.WorkingDirectory='{wd}';"
          "$s.IconLocation='{icn}';$s.Save()").format(
        lnk=lnk_path.replace("'", "''"), tgt=target.replace("'", "''"),
        wd=workdir.replace("'", "''"), icn=icon.replace("'", "''"))
    powershell(ps)


def kill_pets(wait=True):
    """结束正在运行的宠物（新旧文件名都处理），并等进程真正退出"""
    subprocess.run(['taskkill', '/IM', APP_EXE, '/F'], capture_output=True)
    subprocess.run(['taskkill', '/IM', 'NanaPet.exe', '/F'], capture_output=True)
    if not wait:
        return
    for _ in range(50):
        if not is_running(APP_EXE):
            return
        time.sleep(0.1)


def copy_with_retry(s, d):
    """覆盖安装时旧进程可能还占着文件，重试几次"""
    for attempt in range(10):
        try:
            if os.path.isdir(s):
                shutil.rmtree(d, ignore_errors=True)
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)
            return
        except PermissionError:
            time.sleep(0.2)
    raise PermissionError(f'文件被占用：{d}')


def clean_legacy():
    """清理旧版本残留（那艺娜小狗桌宠 → NANA DOG 改名升级）"""
    powershell(
        "$d=[Environment]::GetFolderPath('Desktop');"
        "$p=[Environment]::GetFolderPath('Programs');"
        "Remove-Item -LiteralPath (Join-Path $d '那艺娜小狗桌宠.lnk')"
        " -Force -ErrorAction SilentlyContinue;"
        "Remove-Item -LiteralPath (Join-Path $p '那艺娜小狗桌宠.lnk')"
        " -Force -ErrorAction SilentlyContinue;"
        "Remove-Item -LiteralPath (Join-Path $p '卸载那艺娜小狗桌宠.lnk')"
        " -Force -ErrorAction SilentlyContinue;"
        "Remove-Item -LiteralPath (Join-Path $env:LOCALAPPDATA 'NanaPet')"
        " -Recurse -Force -ErrorAction SilentlyContinue;"
        "Remove-ItemProperty -Path 'HKCU:\\SOFTWARE\\Microsoft\\Windows"
        "\\CurrentVersion\\Run' -Name 'NanaDesktopPet'"
        " -ErrorAction SilentlyContinue")
    legacy_cfg = os.path.join(
        os.environ.get('APPDATA', ''), 'NanaPet', 'config.json')
    if os.path.exists(legacy_cfg):
        try:
            os.remove(legacy_cfg)
        except OSError:
            pass


def main():
    if sys.platform != 'win32':
        raise SystemExit('installer.py 仅支持 Windows；macOS 请构建并打开 NANA DOG.app')
    try:
        src = os.path.join(resource_dir(), 'NanaDog')
        exe = os.path.join(INSTALL_DIR, APP_EXE)

        # 1) 结束旧进程（等真正退出），清理旧版残留，解包安装文件
        kill_pets()
        clean_legacy()
        os.makedirs(INSTALL_DIR, exist_ok=True)
        for name in os.listdir(src):
            copy_with_retry(os.path.join(src, name),
                            os.path.join(INSTALL_DIR, name))

        # 2) 图标（PyInstaller 6.x 资源在 _internal 下）
        icon = os.path.join(INSTALL_DIR, '_internal', 'assets', 'icon.ico')
        if not os.path.exists(icon):
            icon = os.path.join(INSTALL_DIR, 'assets', 'icon.ico')

        # 3) 快捷方式：桌面 + 开始菜单 + 卸载入口
        desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
        if os.path.isdir(desktop):
            make_shortcut(os.path.join(desktop, DISPLAY + '.lnk'),
                          exe, icon, INSTALL_DIR)
        programs = os.path.join(os.environ['APPDATA'], 'Microsoft', 'Windows',
                                'Start Menu', 'Programs')
        make_shortcut(os.path.join(programs, DISPLAY + '.lnk'),
                      exe, icon, INSTALL_DIR)

        # 4) 卸载脚本：纯 ASCII 的 bat + base64(UTF-16LE) PowerShell，
        #    任何系统语言/编码下都可靠（避开中文乱码和 ExecutionPolicy 限制）
        ps_uninstall = (
            "Set-Location $env:TEMP\n"
            "taskkill /IM 'NANA DOG.exe' /F 2>$null | Out-Null\n"
            "Remove-Item -LiteralPath (Join-Path "
            "([Environment]::GetFolderPath('Desktop')) '" + DISPLAY + ".lnk')"
            " -Force -ErrorAction SilentlyContinue\n"
            "Remove-Item -LiteralPath (Join-Path "
            "([Environment]::GetFolderPath('Programs')) '" + DISPLAY + ".lnk')"
            " -Force -ErrorAction SilentlyContinue\n"
            "Remove-Item -LiteralPath (Join-Path "
            "([Environment]::GetFolderPath('Programs')) '卸载" + DISPLAY + ".lnk')"
            " -Force -ErrorAction SilentlyContinue\n"
            "Remove-ItemProperty -Path 'HKCU:\\SOFTWARE\\Microsoft\\Windows"
            "\\CurrentVersion\\Run' -Name 'NanaDog'"
            " -ErrorAction SilentlyContinue\n"
            "Remove-Item -LiteralPath (Join-Path $env:APPDATA 'NanaDog')"
            " -Recurse -Force -ErrorAction SilentlyContinue\n"
            "Write-Host 'NANA DOG 已卸载完成，本窗口 5 秒后自动关闭。'\n"
            "Start-Sleep -Seconds 5\n"
            "Remove-Item -LiteralPath (Join-Path $env:LOCALAPPDATA 'NanaDog')"
            " -Recurse -Force -ErrorAction SilentlyContinue\n")
        enc = base64.b64encode(ps_uninstall.encode('utf-16-le')).decode('ascii')
        uninstall = ('@echo off\r\n'
                     'taskkill /IM "NANA DOG.exe" /F >nul 2>&1\r\n'
                     'powershell -NoProfile -EncodedCommand ' + enc + '\r\n')
        with open(os.path.join(INSTALL_DIR, '卸载.bat'), 'w',
                  encoding='ascii') as f:
            f.write(uninstall)
        make_shortcut(os.path.join(programs, '卸载' + DISPLAY + '.lnk'),
                      os.path.join(INSTALL_DIR, '卸载.bat'), icon, INSTALL_DIR)

        # 5) 安装完立即启动，并确认进程真的活着（老系统/32位系统起不来时给明确提示）
        subprocess.Popen([exe], cwd=INSTALL_DIR)
        alive = False
        for _ in range(50):
            time.sleep(0.1)
            if is_running(APP_EXE):
                alive = True
                break
        if alive:
            msg('安装成功', f'{DISPLAY} 已安装并启动！\n\n'
                            f'桌面和开始菜单都有快捷方式，\n'
                            f'卸载入口在开始菜单。', 0x40)
        else:
            if SILENT:
                print('LAUNCH_FAILED')
            msg('启动失败',
                f'文件已安装，但程序未能启动。\n\n'
                f'{DISPLAY} 需要 64 位 Windows 10（1809 或更新）'
                f'/ Windows 11。\n'
                f'Windows 7 / 8 / 32 位系统暂不支持。', 0x10)
    except Exception as exc:
        msg('安装失败', f'发生错误：{exc}', 0x10)
        raise


if __name__ == '__main__':
    main()

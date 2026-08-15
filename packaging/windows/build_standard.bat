@echo off
chcp 65001 >nul
cd /d "%~dp0\..\.."
echo === [1/3] 打包程序本体 NANA DOG ===
py -3.12 -m PyInstaller "packaging\windows\NANA DOG.spec" --noconfirm
if errorlevel 1 goto :fail
echo === [2/3] 打包单文件便携版 NANA DOG Portable ===
py -3.12 -m PyInstaller "packaging\windows\NANA DOG Portable.spec" --noconfirm
if errorlevel 1 goto :fail
echo === [3/3] 打包安装程序 NANA DOG Setup ===
py -3.12 -m PyInstaller "packaging\windows\NANA DOG Setup.spec" --noconfirm
if errorlevel 1 goto :fail
copy /Y "dist\NANA DOG Setup.exe" "%USERPROFILE%\Desktop\" >nul
echo.
echo 完成：桌面已生成 NANA DOG Setup.exe
pause
exit /b 0
:fail
echo.
echo 打包失败，请检查上方错误信息
pause
exit /b 1

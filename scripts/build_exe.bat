@echo off
REM GuideLab 单 exe 打包（Windows）
cd /d %~dp0\..

if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

python scripts\build_exe.py
pause

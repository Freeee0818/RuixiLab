@echo off
REM 后端服务启动脚本 (Windows)

cd /d %~dp0\..

REM 检查虚拟环境
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

REM 启动计算服务（绘图 + PySR）
python -m analysis_module.main

pause


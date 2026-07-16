@echo off
REM AI 服务不需要 PySR / Julia，可使用独立虚拟环境。

cd /d %~dp0\..

if exist venv-ai\Scripts\activate.bat (
    call venv-ai\Scripts\activate.bat
)

python -m ai_module.main

pause

@echo off
REM Access 服务不需要 AI、RAG、PySR 或 Julia，可使用最小虚拟环境。

cd /d %~dp0\..

if exist venv-access\Scripts\activate.bat (
    call venv-access\Scripts\activate.bat
)

python -m access_service.main

pause

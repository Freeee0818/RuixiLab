#!/bin/bash
# 后端服务启动脚本 (Linux/macOS)

cd "$(dirname "$0")/.."

# 检查虚拟环境
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# 启动服务
python scripts/start_backend.py


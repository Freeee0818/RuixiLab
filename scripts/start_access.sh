#!/bin/bash
# Access 服务不需要 AI、RAG、PySR 或 Julia，可使用最小虚拟环境。

cd "$(dirname "$0")/.."

if [ -d "venv-access" ]; then
    source venv-access/bin/activate
fi

python -m access_service.main

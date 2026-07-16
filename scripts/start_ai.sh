#!/bin/bash
# AI 服务不需要 PySR / Julia，可使用独立虚拟环境。

cd "$(dirname "$0")/.."

if [ -d "venv-ai" ]; then
    source venv-ai/bin/activate
fi

python -m ai_module.main

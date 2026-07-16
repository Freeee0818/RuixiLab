#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Compatibility launcher for the compute backend.

AI now runs independently with ``python -m ai_module.main``.
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 加载环境变量
from dotenv import load_dotenv
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    print("警告: 未找到.env文件，使用默认配置或环境变量")

# 导入并启动绘图 + PySR 计算服务
from analysis_module.main import main

if __name__ == "__main__":
    print("提示：AI 服务请在另一个环境/进程运行 python -m ai_module.main")
    main()


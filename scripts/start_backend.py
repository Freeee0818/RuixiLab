#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
后端服务启动脚本
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

# 导入并启动服务
from pysr_module.main import main

if __name__ == "__main__":
    main()


#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
项目初始化脚本
用于设置开发环境
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(cmd, check=True):
    """运行命令"""
    print(f"执行: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"错误: {result.stderr}")
        sys.exit(1)
    return result

def main():
    """主函数"""
    project_root = Path(__file__).parent.parent
    
    print("=" * 60)
    print("睿析实验平台 - 项目初始化")
    print("=" * 60)
    
    # 1. 检查Python版本
    print("\n[1/6] 检查Python版本...")
    python_version = sys.version_info
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
        print("错误: 需要Python 3.8或更高版本")
        sys.exit(1)
    print(f"✓ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # 2. 创建虚拟环境
    print("\n[2/6] 创建虚拟环境...")
    venv_path = project_root / "venv"
    if not venv_path.exists():
        run_command(f"{sys.executable} -m venv venv")
        print("✓ 虚拟环境已创建")
    else:
        print("✓ 虚拟环境已存在")
    
    # 3. 激活虚拟环境并安装依赖
    print("\n[3/6] 安装Python依赖...")
    if sys.platform == "win32":
        pip_path = venv_path / "Scripts" / "pip.exe"
        python_path = venv_path / "Scripts" / "python.exe"
    else:
        pip_path = venv_path / "bin" / "pip"
        python_path = venv_path / "bin" / "python"
    
    # 安装主依赖
    if (project_root / "requirements.txt").exists():
        run_command(f'"{pip_path}" install -r requirements.txt')
    
    # 安装PySR模块依赖
    pysr_requirements = project_root / "pysr_module" / "requirements.txt"
    if pysr_requirements.exists():
        run_command(f'"{pip_path}" install -r "{pysr_requirements}"')
    
    # 安装服务器依赖
    server_requirements = project_root / "src" / "server" / "requirements.txt"
    if server_requirements.exists():
        run_command(f'"{pip_path}" install -r "{server_requirements}"')
    
    # 安装python-dotenv（用于加载.env文件）
    run_command(f'"{pip_path}" install python-dotenv')
    
    print("✓ Python依赖安装完成")
    
    # 4. 检查Node.js
    print("\n[4/6] 检查Node.js...")
    result = run_command("node --version", check=False)
    if result.returncode == 0:
        print(f"✓ {result.stdout.strip()}")
    else:
        print("⚠ 未检测到Node.js，前端依赖将无法安装")
    
    # 5. 安装前端依赖
    if result.returncode == 0:
        print("\n[5/6] 安装前端依赖...")
        run_command("npm install", check=False)
        print("✓ 前端依赖安装完成")
    else:
        print("\n[5/6] 跳过前端依赖安装")
    
    # 6. 创建.env文件
    print("\n[6/6] 配置环境变量...")
    env_file = project_root / ".env"
    env_example = project_root / "env.example"
    
    if not env_file.exists() and env_example.exists():
        import shutil
        shutil.copy(env_example, env_file)
        print("✓ 已创建.env文件（请编辑并填入实际配置）")
    elif env_file.exists():
        print("✓ .env文件已存在")
    else:
        print("⚠ 未找到env.example文件")
    
    print("\n" + "=" * 60)
    print("初始化完成！")
    print("=" * 60)
    print("\n下一步:")
    print("1. 编辑 .env 文件，填入API密钥等配置")
    print("2. 运行 scripts/start_backend.py 启动后端服务")
    print("3. 运行 npm run dev 启动前端服务")

if __name__ == "__main__":
    main()


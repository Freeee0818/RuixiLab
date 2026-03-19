#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
GuideLab 单 exe 打包脚本
1. 若缺少 dist/ 则提示先执行 npm run build
2. 调用 PyInstaller 使用 GuideLab.spec 打包
在项目根目录执行: python scripts/build_exe.py
"""

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = PROJECT_ROOT / "dist"
DIST_INDEX = DIST_DIR / "index.html"
SPEC_FILE = PROJECT_ROOT / "GuideLab.spec"


def main():
    os.chdir(PROJECT_ROOT)
    print(PROJECT_ROOT)

    if not DIST_INDEX.exists():
        print("未找到前端构建产物 dist/index.html。")
        print("请先执行: npm install && npm run build")
        try:
            r = input("是否现在执行 npm run build？[y/N]: ").strip().lower()
            if r == "y" or r == "yes":
                code = subprocess.call(["npm", "run", "build"], shell=(os.name == "nt"))
                if code != 0:
                    sys.exit(code)
                if not DIST_INDEX.exists():
                    print("构建后仍无 dist/index.html，退出。")
                    sys.exit(1)
            else:
                sys.exit(1)
        except EOFError:
            sys.exit(1)

    if not SPEC_FILE.exists():
        print(f"未找到 {SPEC_FILE}，退出。")
        sys.exit(1)

    try:
        import PyInstaller
    except ImportError:
        print("未安装 PyInstaller，请执行: pip install pyinstaller")
        sys.exit(1)

    print("正在使用 PyInstaller 打包（使用 GuideLab.spec）...")
    code = subprocess.call(
        [sys.executable, "-m", "PyInstaller", "--noconfirm", str(SPEC_FILE)],
        cwd=str(PROJECT_ROOT),
    )
    if code != 0:
        sys.exit(code)
    print("打包完成。可执行文件在: dist/GuideLab.exe（Windows）或 dist/GuideLab（Linux/macOS）")


if __name__ == "__main__":
    main()

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
迁移脚本：将旧的输出目录迁移到新的统一位置
"""

import os
import shutil
from pathlib import Path

def migrate_outputs():
    """迁移输出文件"""
    project_root = Path(__file__).parent.parent
    
    # 旧目录
    old_outputs = [
        project_root / "pysr_module" / "output",
        project_root / "pysr_module" / "outputs",
        project_root / "outputs",
    ]
    
    # 新目录
    new_output_dir = project_root / "data" / "outputs"
    new_plots_dir = new_output_dir / "plots"
    
    # 创建新目录
    new_output_dir.mkdir(parents=True, exist_ok=True)
    new_plots_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("迁移输出文件")
    print("=" * 60)
    
    migrated = False
    
    for old_dir in old_outputs:
        if old_dir.exists():
            print(f"\n发现旧目录: {old_dir}")
            
            # 迁移plots目录
            old_plots = old_dir / "plots"
            if old_plots.exists():
                print(f"  迁移 plots/ 目录...")
                for item in old_plots.iterdir():
                    if item.is_file():
                        dest = new_plots_dir / item.name
                        if not dest.exists():
                            shutil.copy2(item, dest)
                            print(f"    ✓ {item.name}")
                        else:
                            print(f"    - {item.name} (已存在，跳过)")
                migrated = True
            
            # 迁移其他文件
            for item in old_dir.iterdir():
                if item.is_file() and item.suffix in ['.csv', '.pkl', '.json']:
                    dest = new_output_dir / item.name
                    if not dest.exists():
                        shutil.copy2(item, dest)
                        print(f"  迁移文件: {item.name}")
                        migrated = True
            
            # 迁移子目录（如任务目录）
            for item in old_dir.iterdir():
                if item.is_dir() and item.name != "plots":
                    dest = new_output_dir / item.name
                    if not dest.exists():
                        shutil.copytree(item, dest)
                        print(f"  迁移目录: {item.name}")
                        migrated = True
    
    if migrated:
        print("\n✓ 迁移完成")
        print(f"\n新输出目录: {new_output_dir}")
        print("\n注意: 旧目录中的文件已复制到新位置，但未删除。")
        print("确认新位置的文件正常后，可以手动删除旧目录。")
    else:
        print("\n未发现需要迁移的文件")
    
    print("=" * 60)

if __name__ == "__main__":
    migrate_outputs()


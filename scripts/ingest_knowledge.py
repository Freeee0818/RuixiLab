#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
知识库导入脚本：将 knowledge_base/raw_docs 下的文档导入向量库。
支持 PDF、Word、Excel、TXT、PPT 等，首次运行会下载 Embedding 模型（约几百 MB）。
请在项目根目录执行：python scripts/ingest_knowledge.py
"""

import os
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

def main():
    raw_dir = project_root / "knowledge_base" / "raw_docs"
    if not raw_dir.exists():
        print(f"请先在项目下创建目录并放入文档：{raw_dir}")
        print("例如：knowledge_base/raw_docs/你的文档.pdf")
        sys.exit(1)

    print("正在初始化 RAG 服务（首次会下载 Embedding 模型，请稍候）...")
    from rag_module.ingestion import ingestor

    import argparse
    p = argparse.ArgumentParser(description="导入知识库文档")
    p.add_argument("--force", action="store_true", help="强制重新导入所有文件（忽略已导入未修改的）")
    args = p.parse_args()

    ingestor.ingest_all_formats(force_reimport=args.force)
    print("导入完成。可用 scripts/test_rag.py 测试检索效果。")
    if not (raw_dir / ".ingestion_index.json").exists() or len(ingestor.file_index) == 0:
        print("提示：当前未导入任何文档。请将 PDF、Word、TXT 等放入 knowledge_base/raw_docs 后重新运行本脚本。")

    # 显式关闭 Qdrant 客户端，避免退出时报 "Exception ignored in: QdrantClient.__del__"
    from rag_module.service import rag_service
    if getattr(rag_service, "client", None) is not None:
        try:
            rag_service.client.close()
        except Exception:
            pass

if __name__ == "__main__":
    main()

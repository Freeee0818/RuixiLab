#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RAG 检索测试脚本：不调用大模型，只测试「根据问题检索到的文档片段」是否合理。
用法（在项目根目录）：
  python scripts/test_rag.py
  python scripts/test_rag.py "单摆周期公式是什么"
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
    print("正在初始化 RAG 服务...")
    from rag_module.service import rag_service

    if not rag_service.initialized:
        rag_service.initialize()

    if not rag_service.initialized or rag_service.index is None:
        print("RAG 初始化失败，请先运行: python scripts/ingest_knowledge.py")
        sys.exit(1)

    questions = [
        "单摆周期公式是什么？",
        "如何用 Tracker 做视频分析？",
        "符号回归能做什么？",
    ]

    if len(sys.argv) > 1:
        questions = [" ".join(sys.argv[1:])]

    retriever = rag_service.index.as_retriever(similarity_top_k=3)

    for q in questions:
        print("\n" + "=" * 60)
        print(f"问题: {q}")
        print("=" * 60)
        try:
            nodes = retriever.retrieve(q)
            if not nodes:
                print("  (未检索到相关片段)")
                continue
            for i, node in enumerate(nodes, 1):
                src = node.metadata.get("file_name", "未知")
                score = getattr(node, "score", None)
                score_str = f" 相似度={score:.4f}" if score is not None else ""
                print(f"\n  [{i}] 来源: {src}{score_str}")
                print(f"  {node.text[:300].strip()}...")
        except Exception as e:
            print(f"  检索异常: {e}")

    print("\n若以上片段与问题相关，说明 RAG 训练/检索效果正常。")
    print("可在分析页使用 AI 助手提问，会先走 RAG 再生成回答。")

    # 显式关闭 Qdrant 客户端，避免退出时报 Exception ignored in: QdrantClient.__del__
    if getattr(rag_service, "client", None) is not None:
        try:
            rag_service.client.close()
        except Exception:
            pass

if __name__ == "__main__":
    main()

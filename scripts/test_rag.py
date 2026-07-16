#!/usr/bin/env python
"""Manual smoke test for dense, sparse, hybrid and reranked retrieval."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from dotenv import load_dotenv

load_dotenv(project_root / ".env")


DEFAULT_QUESTIONS = [
    "单摆周期公式是什么？",
    "如何用 Tracker 做视频分析？",
    "PySR 符号回归可以发现什么规律？",
]


def _print_results(question: str, mode: str, results: list[dict]) -> None:
    print("\n" + "=" * 72)
    print(f"问题: {question}")
    print(f"模式: {mode}")
    print("=" * 72)
    if not results:
        print("  (未检索到相关片段)")
        return
    for index, item in enumerate(results, 1):
        metadata = item.get("metadata") or {}
        location = metadata.get("page_label") or metadata.get("section_title") or ""
        score = item.get("score")
        dense_score = item.get("retrieval_score")
        rerank_score = item.get("rerank_score")
        print(
            f"\n[{index}] {item.get('title')} {location} "
            f"score={score:.4f} retrieval={dense_score:.4f} rerank={rerank_score}"
        )
        print(str(item.get("excerpt") or "")[:500].strip())


def main() -> None:
    parser = argparse.ArgumentParser(description="测试 GuideLab RAG v2 检索")
    parser.add_argument("query", nargs="*", help="可选的单个检索问题")
    parser.add_argument(
        "--mode",
        choices=("dense", "sparse", "hybrid", "hybrid_rerank"),
        default="hybrid_rerank",
    )
    parser.add_argument("--compare", action="store_true", help="依次比较四种检索模式")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    from rag_module.service import rag_service

    rag_service.initialize()
    count = rag_service.collection_count()
    print(f"RAG collection={rag_service.collection_name}, points={count}")
    if count == 0:
        raise SystemExit("向量库为空，请先运行 python scripts/ingest_knowledge.py")

    questions = [" ".join(args.query)] if args.query else DEFAULT_QUESTIONS
    modes = (
        ("dense", "sparse", "hybrid", "hybrid_rerank")
        if args.compare
        else (args.mode,)
    )
    try:
        for question in questions:
            for mode in modes:
                results = rag_service.retrieve(
                    question,
                    top_k=args.top_k,
                    mode=mode,
                    rerank=mode == "hybrid_rerank",
                )
                _print_results(question, mode, results)
    finally:
        rag_service.close()


if __name__ == "__main__":
    main()

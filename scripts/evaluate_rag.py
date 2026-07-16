#!/usr/bin/env python
"""Evaluate retrieval modes against a small, human-editable source benchmark."""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path


project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from dotenv import load_dotenv

load_dotenv(project_root / ".env")


def _load_dataset(path: Path) -> list[dict]:
    records = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        record = json.loads(line)
        if not record.get("query") or not record.get("expected_sources"):
            raise ValueError(f"评测集第 {line_number} 行缺少 query/expected_sources")
        records.append(record)
    if not records:
        raise ValueError("评测集为空")
    return records


def _matching_rank(results: list[dict], expected_sources: list[str]) -> int | None:
    expected = [item.casefold() for item in expected_sources]
    for rank, result in enumerate(results, 1):
        title = str(result.get("title") or "").casefold()
        if any(source in title for source in expected):
            return rank
    return None


def main() -> None:
    from config import settings

    parser = argparse.ArgumentParser(description="评测 GuideLab RAG v2")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path(settings.KNOWLEDGE_BASE_DIR) / "evaluation" / "rag_queries.jsonl",
    )
    parser.add_argument(
        "--modes",
        nargs="+",
        default=["dense", "sparse", "hybrid", "hybrid_rerank"],
        choices=["dense", "sparse", "hybrid", "hybrid_rerank"],
    )
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    from rag_module.service import rag_service

    dataset = _load_dataset(args.dataset)
    rag_service.initialize()
    if rag_service.collection_count() == 0:
        raise SystemExit("向量库为空，请先完成入库")

    report = {"dataset": str(args.dataset), "query_count": len(dataset), "modes": {}}
    try:
        for mode in args.modes:
            reciprocal_ranks = []
            latencies_ms = []
            misses = []
            for record in dataset:
                started = time.perf_counter()
                results = rag_service.retrieve(
                    record["query"],
                    top_k=args.top_k,
                    mode=mode,
                    rerank=mode == "hybrid_rerank",
                )
                latencies_ms.append((time.perf_counter() - started) * 1000)
                rank = _matching_rank(results, record["expected_sources"])
                reciprocal_ranks.append(0.0 if rank is None else 1.0 / rank)
                if rank is None:
                    misses.append(
                        {
                            "query": record["query"],
                            "returned_sources": [item.get("title") for item in results],
                        }
                    )

            hits = sum(value > 0 for value in reciprocal_ranks)
            ordered_latency = sorted(latencies_ms)
            p95_index = round(0.95 * (len(ordered_latency) - 1))
            summary = {
                f"recall@{args.top_k}": hits / len(dataset),
                f"mrr@{args.top_k}": sum(reciprocal_ranks) / len(dataset),
                "latency_p50_ms": statistics.median(latencies_ms),
                "latency_p95_ms": ordered_latency[p95_index],
                "latency_max_ms": max(latencies_ms),
                "misses": misses,
            }
            report["modes"][mode] = summary
            print(
                f"{mode:15s} recall@{args.top_k}={summary[f'recall@{args.top_k}']:.3f} "
                f"mrr@{args.top_k}={summary[f'mrr@{args.top_k}']:.3f} "
                f"p50={summary['latency_p50_ms']:.1f}ms "
                f"p95={summary['latency_p95_ms']:.1f}ms max={summary['latency_max_ms']:.1f}ms"
            )
    finally:
        rag_service.close()

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"报告已写入: {args.output}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python
"""Run a reproducible, side-effect-free GuideLab Tool-Agent experiment."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import platform
import random
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import httpx
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)
load_dotenv(PROJECT_ROOT / ".env")

STRATEGIES = ("schema_only", "skill_feedback", "guided_repair")


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        case = json.loads(line)
        missing = [key for key in ("id", "category", "question", "expected_tool") if key not in case]
        if missing:
            raise ValueError(f"评测集第 {line_number} 行缺少字段: {', '.join(missing)}")
        case_id = str(case["id"])
        if case_id in seen_ids:
            raise ValueError(f"评测集包含重复 id: {case_id}")
        seen_ids.add(case_id)
        cases.append(case)
    if not cases:
        raise ValueError("Agent Tool 评测集为空")
    return cases


def _prior_failure_messages(case: dict[str, Any], *, guided: bool) -> list[dict[str, Any]]:
    prior = case.get("prior_failure")
    if not isinstance(prior, dict):
        return []
    tool_name = str(prior.get("tool") or "unknown")
    call_id = f"eval_{case['id']}_failed"
    messages: list[dict[str, Any]] = [
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": call_id,
                "type": "function",
                "function": {
                    "name": tool_name,
                    "arguments": json.dumps(prior.get("arguments") or {}, ensure_ascii=False),
                },
            }],
        },
        {
            "role": "tool",
            "tool_call_id": call_id,
            "name": tool_name,
            "content": json.dumps({
                "ok": False,
                "result": None,
                "error": prior.get("error") or "工具调用失败",
            }, ensure_ascii=False),
        },
    ]
    if guided:
        messages.append({
            "role": "system",
            "content": (
                "上一轮工具调用失败。请检查 error 与 JSON Schema，修正参数或策略后再决定是否调用；"
                "不要重复完全相同的失败调用。若缺少必要信息或服务不可用，应停止调用并解释原因。"
            ),
        })
    return messages


def build_messages(case: dict[str, Any], skill, strategy: str) -> list[dict[str, Any]]:
    if strategy not in STRATEGIES:
        raise ValueError(f"未知评测策略: {strategy}")
    system = "你是睿析平台物理实验助手。根据问题决定是否调用工具；不需要外部执行时直接回答。"
    if strategy != "schema_only":
        system += f"\n\n【当前 Skill】{skill.name}\n{skill.instructions}"
    messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
    if strategy in {"skill_feedback", "guided_repair"}:
        messages.extend(_prior_failure_messages(case, guided=strategy == "guided_repair"))
    data_note = "当前对话已绑定实验数据。" if case.get("data_available") else "当前对话没有绑定实验数据。"
    messages.append({"role": "user", "content": f"{data_note}\n问题：{case['question']}"})
    return messages


_MISSING = object()


def _rule_matches(value: Any, rule: dict[str, Any]) -> bool:
    if rule.get("absent"):
        return value is _MISSING
    if value is _MISSING:
        return False
    if "equals" in rule and value != rule["equals"]:
        return False
    if "not_equals" in rule and value == rule["not_equals"]:
        return False
    if "minimum" in rule and (not isinstance(value, (int, float)) or value < rule["minimum"]):
        return False
    if "maximum" in rule and (not isinstance(value, (int, float)) or value > rule["maximum"]):
        return False
    if "one_of" in rule and value not in rule["one_of"]:
        return False
    return True


def arguments_match(case: dict[str, Any], arguments: dict[str, Any] | None) -> bool:
    if case.get("expected_tool") is None:
        return arguments is None
    if arguments is None:
        return False
    for key, expected in (case.get("expected_arguments") or {}).items():
        if arguments.get(key, _MISSING) != expected:
            return False
    for key, rule in (case.get("argument_rules") or {}).items():
        if not _rule_matches(arguments.get(key, _MISSING), rule):
            return False
    return True


def recovery_succeeds(case, actual_tool, arguments, schema_valid) -> bool:
    if not isinstance(case.get("prior_failure"), dict):
        return False
    expected_tool = case.get("expected_tool")
    if expected_tool is None:
        return actual_tool is None
    if actual_tool != expected_tool or schema_valid is not True or not arguments_match(case, arguments):
        return False
    prior = case["prior_failure"]
    return not (actual_tool == prior.get("tool") and arguments == (prior.get("arguments") or {}))


async def evaluate_case(
    client: httpx.AsyncClient,
    case: dict[str, Any],
    config: dict[str, Any],
    tools,
    skills,
    *,
    strategy: str,
    repetition: int,
    temperature: float,
    enable_thinking: bool,
) -> dict[str, Any]:
    skill = skills.get(case.get("skill") or "physics_experiment")
    payload = {
        "model": config["model"],
        "messages": build_messages(case, skill, strategy),
        "temperature": temperature,
        "max_tokens": min(int(config["max_tokens"]), 500),
        "stream": False,
        "tools": tools.schemas(skill.allowed_tools),
        "tool_choice": "auto",
    }
    if enable_thinking:
        payload["enable_thinking"] = True
    started = time.perf_counter()
    response = await client.post(
        f"{config['base_url'].rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {config['api_key']}", "Content-Type": "application/json"},
        json=payload,
    )
    latency_ms = (time.perf_counter() - started) * 1000
    response.raise_for_status()
    message = response.json()["choices"][0]["message"]
    tool_calls = message.get("tool_calls") or []
    function = ((tool_calls[0] if tool_calls else None) or {}).get("function") or {}
    actual_tool = function.get("name")
    raw_arguments = function.get("arguments") or "{}"
    schema_valid: bool | None = None
    arguments: dict[str, Any] | None = None
    schema_error = None
    if actual_tool:
        try:
            arguments = tools.validate_arguments(actual_tool, raw_arguments, allowed_tools=skill.allowed_tools)
            schema_valid = True
        except Exception as exc:
            schema_valid = False
            schema_error = str(exc)
    expected_tool = case.get("expected_tool")
    tool_correct = actual_tool == expected_tool
    argument_correct = tool_correct and arguments_match(case, arguments)
    recovery_case = isinstance(case.get("prior_failure"), dict)
    recovery_success = recovery_succeeds(case, actual_tool, arguments, schema_valid)
    end_to_end_success = tool_correct and argument_correct and (actual_tool is None or schema_valid is True)
    return {
        "id": case["id"], "category": case["category"], "strategy": strategy,
        "repetition": repetition, "skill": skill.name, "expected_tool": expected_tool,
        "actual_tool": actual_tool, "tool_call_count": len(tool_calls), "tool_correct": tool_correct,
        "schema_valid": schema_valid, "schema_error": schema_error, "arguments": arguments,
        "argument_correct": argument_correct, "recovery_case": recovery_case,
        "recovery_success": recovery_success, "end_to_end_success": end_to_end_success,
        "unnecessary_call": expected_tool is None and actual_tool is not None,
        "latency_ms": round(latency_ms, 2), "request_error": None,
    }


def _failed_result(case, strategy: str, repetition: int, exc: Exception) -> dict[str, Any]:
    return {
        "id": case["id"], "category": case["category"], "strategy": strategy,
        "repetition": repetition, "skill": case.get("skill") or "physics_experiment",
        "expected_tool": case.get("expected_tool"), "actual_tool": None, "tool_call_count": 0,
        "tool_correct": False, "schema_valid": None, "schema_error": None, "arguments": None,
        "argument_correct": False, "recovery_case": isinstance(case.get("prior_failure"), dict),
        "recovery_success": False, "end_to_end_success": False, "unnecessary_call": False,
        "latency_ms": None, "request_error": str(exc),
    }


def _mean(values: Iterable[bool | float]) -> float | None:
    values = list(values)
    return sum(float(value) for value in values) / len(values) if values else None


def _bootstrap_ci(values: list[bool | float], seed: int, samples: int = 2000) -> list[float] | None:
    if not values:
        return None
    rng = random.Random(seed)
    estimates = []
    for _ in range(samples):
        draw = [values[rng.randrange(len(values))] for _ in values]
        estimates.append(sum(float(value) for value in draw) / len(draw))
    estimates.sort()
    return [estimates[int(0.025 * (samples - 1))], estimates[int(0.975 * (samples - 1))]]


def summarize_strategy(results: list[dict[str, Any]], seed: int) -> dict[str, Any]:
    successful = [item for item in results if not item["request_error"]]
    called = [item for item in successful if item["actual_tool"] is not None]
    expected_calls = [item for item in successful if item["expected_tool"] is not None]
    recovery = [item for item in successful if item["recovery_case"]]
    no_call = [item for item in successful if item["expected_tool"] is None]
    values = {
        "end_to_end_success_rate": [item["end_to_end_success"] for item in successful],
        "tool_decision_accuracy": [item["tool_correct"] for item in successful],
        "schema_valid_rate": [item["schema_valid"] is True for item in called],
        "argument_correct_rate": [item["argument_correct"] for item in expected_calls],
        "recovery_success_rate": [item["recovery_success"] for item in recovery],
        "unnecessary_call_rate": [item["unnecessary_call"] for item in no_call],
    }
    metrics = {
        key: {"value": _mean(items), "ci95": _bootstrap_ci(items, seed + index), "n": len(items)}
        for index, (key, items) in enumerate(values.items())
    }
    latencies = [item["latency_ms"] for item in successful if item["latency_ms"] is not None]
    metrics["latency_mean_ms"] = {
        "value": statistics.mean(latencies) if latencies else None,
        "ci95": _bootstrap_ci(latencies, seed + 99) if latencies else None,
        "n": len(latencies),
    }
    return {"case_runs": len(results), "request_failures": len(results) - len(successful), "metrics": metrics}


def _git_metadata() -> dict[str, Any]:
    def run(*args: str) -> str:
        result = subprocess.run(["git", *args], cwd=PROJECT_ROOT, capture_output=True, text=True, check=False)
        return result.stdout.strip()
    return {"commit": run("rev-parse", "HEAD") or None, "branch": run("branch", "--show-current") or None,
            "dirty": bool(run("status", "--porcelain"))}


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


async def async_main(args) -> tuple[dict[str, Any], list[dict[str, Any]], Path]:
    from ai_module.agent import build_default_registries
    from config import settings
    settings.validate_ai_config()
    config = settings.get_ai_config()
    tools, skills = build_default_registries()
    cases = load_cases(args.dataset)
    if args.categories:
        selected_categories = set(args.categories)
        cases = [case for case in cases if case["category"] in selected_categories]
        if not cases:
            raise ValueError(f"筛选后没有案例: {sorted(selected_categories)}")
    if args.max_cases:
        cases = cases[:args.max_cases]
    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = args.output_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    strategies = tuple(args.strategies)
    semaphore = asyncio.Semaphore(args.concurrency)
    async with httpx.AsyncClient(timeout=config["timeout"], trust_env=False) as client:
        async def run_one(case, strategy, repetition):
            async with semaphore:
                try:
                    result = await evaluate_case(client, case, config, tools, skills, strategy=strategy,
                                                 repetition=repetition, temperature=args.temperature,
                                                 enable_thinking=args.enable_thinking)
                except Exception as exc:
                    result = _failed_result(case, strategy, repetition, exc)
                print(f"[{strategy:14s}] {case['id']:30s} expected={str(case.get('expected_tool')):31s} "
                      f"actual={str(result['actual_tool']):31s} success={result['end_to_end_success']}")
                return result
        jobs = [run_one(case, strategy, repetition) for repetition in range(1, args.repetitions + 1)
                for strategy in strategies for case in cases]
        results = await asyncio.gather(*jobs)
    summaries = {strategy: summarize_strategy([item for item in results if item["strategy"] == strategy],
                                               args.seed + index * 1000)
                 for index, strategy in enumerate(strategies)}
    summary = {
        "run_id": run_id, "created_at": datetime.now(timezone.utc).isoformat(),
        "research_question": "外部 Skill、执行错误反馈与显式修复提示能否提升物理 Tool-Agent 可靠性？",
        "hypothesis": "guided_repair 在恢复成功率和端到端成功率上优于 schema_only 与 skill_feedback。",
        "dataset": {"path": str(args.dataset), "sha256": _file_sha256(args.dataset),
                    "case_count": len(cases), "categories": sorted({case["category"] for case in cases})},
        "code": _git_metadata(),
        "environment": {"python": sys.version, "platform": platform.platform(), "model": config["model"],
                        "base_url": config["base_url"]},
        "config": {"strategies": list(strategies), "repetitions": args.repetitions,
                   "temperature": args.temperature, "enable_thinking": args.enable_thinking,
                   "concurrency": args.concurrency, "bootstrap_seed": args.seed,
                   "bootstrap_samples": 2000, "tools_executed": False,
                   "category_filter": args.categories},
        "summaries": summaries,
    }
    (run_dir / "raw_results.jsonl").write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in results), encoding="utf-8")
    (run_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary, results, run_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="运行 GuideLab 物理 Tool-Agent 消融实验")
    parser.add_argument("--dataset", type=Path,
                        default=PROJECT_ROOT / "knowledge_base" / "evaluation" / "agent_tool_cases.jsonl")
    parser.add_argument("--strategies", nargs="+", choices=STRATEGIES, default=list(STRATEGIES))
    parser.add_argument("--categories", nargs="+", help="只运行指定 category（例如 recovery）")
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--max-cases", type=int)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--enable-thinking", action="store_true")
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--seed", type=int, default=20260820)
    parser.add_argument("--run-id")
    parser.add_argument("--output-dir", type=Path,
                        default=PROJECT_ROOT / "experiments" / "agent_tools" / "runs")
    args = parser.parse_args()
    if args.repetitions < 1 or args.concurrency < 1:
        parser.error("--repetitions 和 --concurrency 必须大于 0")
    summary, _, run_dir = asyncio.run(async_main(args))
    print(json.dumps({key: value["metrics"] for key, value in summary["summaries"].items()},
                     ensure_ascii=False, indent=2))
    print(f"原始结果与汇总已写入: {run_dir}")


if __name__ == "__main__":
    main()

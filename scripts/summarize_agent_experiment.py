#!/usr/bin/env python
"""Create spreadsheet-ready tables, an SVG chart, and a research log."""

from __future__ import annotations

import argparse
import csv
import html
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


METRICS = (
    ("end_to_end_success_rate", "端到端成功率"),
    ("tool_decision_accuracy", "工具决策准确率"),
    ("recovery_success_rate", "纠错成功率"),
    ("schema_valid_rate", "Schema 通过率"),
    ("argument_correct_rate", "参数正确率"),
    ("unnecessary_call_rate", "不必要调用率"),
)


def load_run(run_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    raw = [
        json.loads(line)
        for line in (run_dir / "raw_results.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not raw:
        raise ValueError("raw_results.jsonl 为空")
    return summary, raw


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_tables(run_dir: Path, summary: dict[str, Any], raw: list[dict[str, Any]]) -> None:
    metric_rows = []
    for strategy, block in summary["summaries"].items():
        for metric, value in block["metrics"].items():
            ci = value.get("ci95")
            metric_rows.append({
                "strategy": strategy,
                "metric": metric,
                "value": value.get("value"),
                "ci95_low": ci[0] if ci else None,
                "ci95_high": ci[1] if ci else None,
                "n": value.get("n"),
            })
    _write_csv(
        run_dir / "metrics.csv",
        metric_rows,
        ["strategy", "metric", "value", "ci95_low", "ci95_high", "n"],
    )

    case_rows = []
    for item in raw:
        row = dict(item)
        row["arguments"] = json.dumps(item.get("arguments"), ensure_ascii=False)
        case_rows.append(row)
    _write_csv(
        run_dir / "case_results.csv",
        case_rows,
        [
            "id", "category", "strategy", "repetition", "skill", "expected_tool", "actual_tool",
            "tool_call_count", "tool_correct", "schema_valid", "arguments", "argument_correct",
            "recovery_case", "recovery_success", "end_to_end_success", "unnecessary_call",
            "latency_ms", "schema_error", "request_error",
        ],
    )

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in raw:
        if not item.get("request_error"):
            grouped[(item["strategy"], item["category"])].append(item)
    category_rows = []
    for (strategy, category), items in sorted(grouped.items()):
        category_rows.append({
            "strategy": strategy,
            "category": category,
            "n": len(items),
            "end_to_end_success_rate": sum(bool(item["end_to_end_success"]) for item in items) / len(items),
            "tool_decision_accuracy": sum(bool(item["tool_correct"]) for item in items) / len(items),
            "request_failures": 0,
        })
    _write_csv(
        run_dir / "category_metrics.csv",
        category_rows,
        ["strategy", "category", "n", "end_to_end_success_rate", "tool_decision_accuracy", "request_failures"],
    )


def write_svg(run_dir: Path, summary: dict[str, Any]) -> None:
    strategies = list(summary["summaries"])
    chart_metrics = [
        ("end_to_end_success_rate", "End-to-end"),
        ("tool_decision_accuracy", "Tool decision"),
        ("recovery_success_rate", "Recovery"),
    ]
    colors = {"schema_only": "#94a3b8", "skill_feedback": "#3b82f6", "guided_repair": "#16a34a"}
    width, height = 900, 520
    left, top, plot_w, plot_h = 85, 70, 760, 350
    group_w = plot_w / len(chart_metrics)
    bar_w = 48
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<style>text{font-family:Arial,"Microsoft YaHei",sans-serif;fill:#172033}.title{font-size:22px;font-weight:700}.axis{font-size:12px;fill:#64748b}.label{font-size:13px;font-weight:600}</style>',
        '<text x="450" y="34" text-anchor="middle" class="title">GuideLab Tool-Agent Ablation</text>',
    ]
    for tick in range(0, 101, 20):
        y = top + plot_h - plot_h * tick / 100
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" stroke="#e2e8f0"/>')
        parts.append(f'<text x="{left - 12}" y="{y + 4:.1f}" text-anchor="end" class="axis">{tick}%</text>')
    for metric_index, (metric, label) in enumerate(chart_metrics):
        group_x = left + metric_index * group_w
        total_bars_w = len(strategies) * bar_w + (len(strategies) - 1) * 12
        start_x = group_x + (group_w - total_bars_w) / 2
        for strategy_index, strategy in enumerate(strategies):
            value = summary["summaries"][strategy]["metrics"][metric]["value"]
            value = float(value or 0)
            x = start_x + strategy_index * (bar_w + 12)
            bar_h = value * plot_h
            y = top + plot_h - bar_h
            color = colors.get(strategy, "#7c3aed")
            parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w}" height="{bar_h:.1f}" rx="4" fill="{color}"/>')
            parts.append(f'<text x="{x + bar_w / 2:.1f}" y="{max(top + 12, y - 7):.1f}" text-anchor="middle" class="axis">{value * 100:.1f}</text>')
        parts.append(f'<text x="{group_x + group_w / 2:.1f}" y="{top + plot_h + 30}" text-anchor="middle" class="label">{html.escape(label)}</text>')
    legend_y = 480
    for index, strategy in enumerate(strategies):
        x = 180 + index * 210
        parts.append(f'<rect x="{x}" y="{legend_y - 12}" width="16" height="16" rx="3" fill="{colors.get(strategy, "#7c3aed")}"/>')
        parts.append(f'<text x="{x + 24}" y="{legend_y + 1}" class="axis">{html.escape(strategy)}</text>')
    parts.append('</svg>')
    (run_dir / "ablation_metrics.svg").write_text("".join(parts), encoding="utf-8")


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{value * 100:.1f}%"


def _pp(value: float | None) -> str:
    return "—" if value is None else f"{value * 100:+.1f} 个百分点"


def write_report(run_dir: Path, summary: dict[str, Any], raw: list[dict[str, Any]]) -> None:
    strategies = summary["summaries"]
    metric_lines = []
    for strategy, block in strategies.items():
        metrics = block["metrics"]
        metric_lines.append(
            f"| `{strategy}` | {_pct(metrics['end_to_end_success_rate']['value'])} | "
            f"{_pct(metrics['tool_decision_accuracy']['value'])} | "
            f"{_pct(metrics['recovery_success_rate']['value'])} | "
            f"{_pct(metrics['unnecessary_call_rate']['value'])} | {block['request_failures']} |"
        )
    failures = [item for item in raw if not item["end_to_end_success"]]
    by_strategy = {
        strategy: [item for item in failures if item["strategy"] == strategy]
        for strategy in strategies
    }
    schema = strategies.get("schema_only", {}).get("metrics", {})
    feedback = strategies.get("skill_feedback", {}).get("metrics", {})
    guided = strategies.get("guided_repair", {}).get("metrics", {})
    feedback_e2e = feedback.get("end_to_end_success_rate", {}).get("value")
    feedback_recovery = feedback.get("recovery_success_rate", {}).get("value")
    guided_e2e = guided.get("end_to_end_success_rate", {}).get("value")
    guided_recovery = guided.get("recovery_success_rate", {}).get("value")
    schema_e2e = schema.get("end_to_end_success_rate", {}).get("value")
    schema_recovery = schema.get("recovery_success_rate", {}).get("value")
    feedback_delta = None if feedback_e2e is None or schema_e2e is None else feedback_e2e - schema_e2e
    recovery_delta = (
        None
        if feedback_recovery is None or schema_recovery is None
        else feedback_recovery - schema_recovery
    )
    guided_delta = None if guided_e2e is None or feedback_e2e is None else guided_e2e - feedback_e2e
    guided_recovery_delta = (
        None
        if guided_recovery is None or feedback_recovery is None
        else guided_recovery - feedback_recovery
    )
    hypothesis_result = (
        "当前结果不支持原假设：`guided_repair` 未超过 `skill_feedback`。"
        if guided_delta is not None and guided_delta <= 0
        else "当前结果与原假设方向一致，但仍需重复实验和更多模型验证。"
    )
    repeat_next_step = (
        "- 已完成 3 次重复；下一步应按案例聚类估计区间，避免把同一案例的重复当作独立样本。"
        if summary["config"]["repetitions"] >= 3
        else "- 将重复次数提高到 3，以检验模型调用稳定性。"
    )

    report = f"""# GuideLab Tool-Agent 实验记录

## Goal

{summary['research_question']}

假设：{summary['hypothesis']}

## Setup

- Run ID：`{summary['run_id']}`
- 模型：`{summary['environment']['model']}`
- 数据集：{summary['dataset']['case_count']} 个案例，SHA-256 `{summary['dataset']['sha256']}`
- 策略：{', '.join(f'`{item}`' for item in summary['config']['strategies'])}
- 重复次数：{summary['config']['repetitions']}
- Temperature：{summary['config']['temperature']}
- Thinking：{summary['config']['enable_thinking']}
- 工具真实执行：否；只评测模型产生的 Tool call
- Git：`{summary['code']['commit']}`，dirty={summary['code']['dirty']}

## Run table

| Strategy | End-to-end | Tool decision | Recovery | Unnecessary call | Request failures |
|---|---:|---:|---:|---:|---:|
{chr(10).join(metric_lines)}

## Findings

- `skill_feedback` 相对 `schema_only`：端到端成功率 {_pp(feedback_delta)}，Recovery@1 {_pp(recovery_delta)}。
- `guided_repair` 相对 `skill_feedback`：端到端成功率 {_pp(guided_delta)}，Recovery@1 {_pp(guided_recovery_delta)}。
- {hypothesis_result}
- 因为 `skill_feedback` 同时加入了 Skill 说明和历史执行反馈，其相对基线的增益是组合效果，不能拆分归因。
- 若后一组差值为 0，只能说明显式 repair 提示在当前样本上未产生可测增益，不能宣称无效。
- 本报告来自一个模型和当前案例集，不把单次结果外推为普遍结论。
- 95% bootstrap 区间保存在 `metrics.csv` 与 `summary.json`。

## Failure notes

"""
    for strategy, items in by_strategy.items():
        report += f"\n### {strategy}：{len(items)} 个失败轨迹\n\n"
        for item in items[:8]:
            reason = item.get("request_error") or item.get("schema_error") or (
                f"expected={item.get('expected_tool')}, actual={item.get('actual_tool')}"
            )
            report += f"- `{item['id']}`：{reason}\n"
    report += """

## Next experiment

{repeat_next_step}
- 对失败最多的类别补充等价改写案例，避免结论只依赖措辞。
- 若用于正式论文，再加入其他模型和人工复核。
"""
    (run_dir / "REPORT.md").write_text(report, encoding="utf-8")

    resume = f"""# 简历表述候选

- 构建覆盖拟合、状态查询、任务取消、无需调用及失败修复的 {summary['dataset']['case_count']} 例物理实验 Tool-Agent 评测集。
- 设计 `schema_only`、`skill_feedback`、`guided_repair` 三组消融策略，并实现逐案例原始轨迹、Bootstrap 置信区间和自动化指标图表。
- 在 `{summary['environment']['model']}` 上，引入 Skill 与结构化执行反馈后，端到端成功率由 {_pct(schema_e2e)} 提升至 {_pct(feedback_e2e)}（{_pp(feedback_delta)}），Recovery@1 由 {_pct(schema_recovery)} 提升至 {_pct(feedback_recovery)}（{_pp(recovery_delta)}）。
- 显式 repair 提示相对 `skill_feedback` 未产生可测增益（端到端 {_pp(guided_delta)}）；该结果按“当前样本出现性能天花板”解释，不夸大为普遍结论。

注意：这些数字只对应 Run `{summary['run_id']}`，不可改写为大规模或跨模型结论。
"""
    (run_dir / "RESUME_CLAIMS.md").write_text(resume, encoding="utf-8")


def summarize(run_dir: Path) -> None:
    summary, raw = load_run(run_dir)
    write_tables(run_dir, summary, raw)
    write_svg(run_dir, summary)
    write_report(run_dir, summary, raw)


def main() -> None:
    parser = argparse.ArgumentParser(description="汇总 GuideLab Tool-Agent 实验")
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    summarize(args.run_dir)
    print(f"CSV、SVG、实验日志和简历表述已写入: {args.run_dir}")


if __name__ == "__main__":
    main()

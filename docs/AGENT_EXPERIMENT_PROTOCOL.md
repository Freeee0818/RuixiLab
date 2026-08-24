# GuideLab 物理 Tool-Agent 最小实验协议

## Goal

研究外部 Skill、结构化执行错误反馈和显式修复提示，是否能够提升物理实验 Tool-Agent
的工具决策、参数生成和失败恢复能力。

## Hypotheses

- H1：`skill_feedback` 的 Tool 决策准确率高于只提供 Tool Schema 的 `schema_only`。
- H2：`guided_repair` 的 Recovery@1 高于仅展示错误的 `skill_feedback`。
- H3：纠错收益不会以显著提高不必要工具调用率为代价。

## Dataset

`knowledge_base/evaluation/agent_tool_cases.jsonl` 包含 40 个物理实验场景：

- 拟合提交 8 例；
- 状态查询 6 例；
- 任务取消 4 例；
- 服务负载 4 例；
- 无需调用 8 例；
- 失败恢复 10 例。

每个案例包含唯一 ID、类别、Skill、是否绑定数据、期望 Tool，以及可选的参数约束或注入失败。
工具不会被真实执行，因此评测不会创建 PySR 任务或改变课堂队列。

## Ablations

| Strategy | Tool Schema | Skill 指令 | 既往执行错误 | 显式修复提示 |
|---|:---:|:---:|:---:|:---:|
| `schema_only` | ✓ |  |  |  |
| `skill_feedback` | ✓ | ✓ | ✓ |  |
| `guided_repair` | ✓ | ✓ | ✓ | ✓ |

## Metrics

- End-to-end success：Tool 名称、参数规则和 Schema 同时正确。
- Tool decision accuracy：调用正确 Tool，或在无需调用时不调用。
- Schema valid rate：实际生成的 Tool 参数通过生产环境同一套 Schema。
- Argument correct rate：满足案例的精确参数或取值范围。
- Recovery@1：注入一次失败后，下一次决策能修复或安全停止。
- Unnecessary call rate：无需调用的案例中仍发起 Tool 的比例。
- Latency：单次模型请求墙钟时间。

比例指标报告基于案例的 95% bootstrap 区间。今晚的最小实验使用一个模型、temperature 0
和一次重复；正式扩展时建议至少重复 3 次并增加其他模型。

## Commands

```bash
python scripts/evaluate_agent_tools.py \
  --run-id qwen-plus-r1 \
  --repetitions 1 \
  --concurrency 3

python scripts/summarize_agent_experiment.py \
  experiments/agent_tools/runs/qwen-plus-r1
```

## Outputs

- `raw_results.jsonl`：不可覆盖的逐案例原始结果。
- `summary.json`：模型、代码版本、数据哈希、配置、指标与置信区间。
- `metrics.csv`、`category_metrics.csv`：表格分析数据。
- `ablation_metrics.svg`：三种策略的对比图。
- `REPORT.md`：实验日志、失败案例和下一步。
- `RESUME_CLAIMS.md`：仅基于本次运行数字生成的简历表述候选。

## Interpretation boundary

该实验评测 Tool 决策与一次纠错，不评测最终自然语言答案的物理正确性，也不证明跨模型泛化。
任何简历数字都必须注明案例数和模型，不能写成面向全部学生或所有物理实验的普遍结论。

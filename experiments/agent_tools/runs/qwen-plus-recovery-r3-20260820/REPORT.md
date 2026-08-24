# GuideLab Tool-Agent 实验记录

## Goal

外部 Skill、执行错误反馈与显式修复提示能否提升物理 Tool-Agent 可靠性？

假设：guided_repair 在恢复成功率和端到端成功率上优于 schema_only 与 skill_feedback。

## Setup

- Run ID：`qwen-plus-recovery-r3-20260820`
- 模型：`qwen-plus`
- 数据集：10 个案例，SHA-256 `f56cde270f5472440023252a1ee1fcbde3474df0e6be91689ee6431d3d864761`
- 策略：`schema_only`, `skill_feedback`, `guided_repair`
- 重复次数：3
- Temperature：0.0
- Thinking：False
- 工具真实执行：否；只评测模型产生的 Tool call
- Git：`63de5894b7187ae1c88f20e962d4b8afa6e46ffe`，dirty=True

## Run table

| Strategy | End-to-end | Tool decision | Recovery | Unnecessary call | Request failures |
|---|---:|---:|---:|---:|---:|
| `schema_only` | 16.7% | 16.7% | 16.7% | 66.7% | 0 |
| `skill_feedback` | 96.7% | 96.7% | 96.7% | 0.0% | 0 |
| `guided_repair` | 96.7% | 96.7% | 96.7% | 0.0% | 0 |

## Findings

- `skill_feedback` 相对 `schema_only`：端到端成功率 +80.0 个百分点，Recovery@1 +80.0 个百分点。
- `guided_repair` 相对 `skill_feedback`：端到端成功率 +0.0 个百分点，Recovery@1 +0.0 个百分点。
- 当前结果不支持原假设：`guided_repair` 未超过 `skill_feedback`。
- 因为 `skill_feedback` 同时加入了 Skill 说明和历史执行反馈，其相对基线的增益是组合效果，不能拆分归因。
- 若后一组差值为 0，只能说明显式 repair 提示在当前样本上未产生可测增益，不能宣称无效。
- 本报告来自一个模型和当前案例集，不把单次结果外推为普遍结论。
- 95% bootstrap 区间保存在 `metrics.csv` 与 `summary.json`。

## Failure notes


### schema_only：25 个失败轨迹

- `repair_iterations_high`：expected=start_symbolic_regression, actual=get_analysis_service_status
- `repair_iterations_zero`：expected=start_symbolic_regression, actual=get_analysis_service_status
- `repair_population_low`：expected=start_symbolic_regression, actual=get_analysis_service_status
- `repair_population_high`：expected=start_symbolic_regression, actual=get_analysis_service_status
- `repair_maxsize_low`：expected=start_symbolic_regression, actual=get_analysis_service_status
- `repair_maxsize_high`：expected=start_symbolic_regression, actual=None
- `repair_unexpected_field`：expected=start_symbolic_regression, actual=None
- `repair_compute_offline_stop`：expected=None, actual=get_analysis_service_status

### skill_feedback：1 个失败轨迹

- `repair_maxsize_high`：expected=start_symbolic_regression, actual=None

### guided_repair：1 个失败轨迹

- `repair_maxsize_high`：expected=start_symbolic_regression, actual=None


## Next experiment

{repeat_next_step}
- 对失败最多的类别补充等价改写案例，避免结论只依赖措辞。
- 若用于正式论文，再加入其他模型和人工复核。

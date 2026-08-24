# GuideLab Tool-Agent 实验记录

## Goal

外部 Skill、执行错误反馈与显式修复提示能否提升物理 Tool-Agent 可靠性？

假设：guided_repair 在恢复成功率和端到端成功率上优于 schema_only 与 skill_feedback。

## Setup

- Run ID：`smoke-20260820`
- 模型：`qwen-plus`
- 数据集：3 个案例，SHA-256 `f56cde270f5472440023252a1ee1fcbde3474df0e6be91689ee6431d3d864761`
- 策略：`schema_only`, `skill_feedback`, `guided_repair`
- 重复次数：1
- Temperature：0.0
- Thinking：False
- 工具真实执行：否；只评测模型产生的 Tool call
- Git：`63de5894b7187ae1c88f20e962d4b8afa6e46ffe`，dirty=True

## Run table

| Strategy | End-to-end | Tool decision | Recovery | Unnecessary call | Request failures |
|---|---:|---:|---:|---:|---:|
| `schema_only` | 100.0% | 100.0% | — | — | 0 |
| `skill_feedback` | 100.0% | 100.0% | — | — | 0 |
| `guided_repair` | 100.0% | 100.0% | — | — | 0 |

## Findings

- `guided_repair` 相对 `schema_only` 的端到端差值：0.0%（百分点方向，负值表示下降）。
- 本报告来自一个模型和当前案例集，不把单次结果外推为普遍结论。
- 95% bootstrap 区间保存在 `metrics.csv` 与 `summary.json`。

## Failure notes


### schema_only：0 个失败轨迹


### skill_feedback：0 个失败轨迹


### guided_repair：0 个失败轨迹



## Next experiment

- 将重复次数提高到 3，以检验模型调用稳定性。
- 对失败最多的类别补充等价改写案例，避免结论只依赖措辞。
- 若用于正式论文，再加入其他模型和人工复核。

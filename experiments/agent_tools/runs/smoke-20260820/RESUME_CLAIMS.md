# 简历表述候选

- 构建覆盖拟合、状态查询、任务取消、无需调用及失败修复的 3 例物理实验 Tool-Agent 评测集。
- 设计 `schema_only`、`skill_feedback`、`guided_repair` 三组消融策略，并实现逐案例原始轨迹、Bootstrap 置信区间和自动化指标图表。
- 在 `qwen-plus` 上，`guided_repair` 的端到端成功率为 100.0%，相对 `schema_only` 差值为 0.0%；正式使用前应结合失败案例解释原因。

注意：这些数字只对应 Run `smoke-20260820`，不可改写为大规模或跨模型结论。

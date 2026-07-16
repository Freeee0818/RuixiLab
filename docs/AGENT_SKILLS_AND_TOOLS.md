# GuideLab Agent：Skill 与 Tool 扩展指南

GuideLab 的 AI 助手现在支持 OpenAI-compatible Chat Completions 工具调用。实现分为三层：

- **Skill**：描述一个专家工作模式，并声明允许使用的工具白名单。
- **Tool**：用 JSON Schema 声明参数，并绑定一个服务端 Python 函数。
- **Runner**：执行“模型选择工具 → 服务端调用 → 工具结果回传模型 → 最终回答”的循环。

默认最多执行 3 轮工具调用，可通过 `AGENT_MAX_TOOL_ROUNDS` 调整；`AGENT_ENABLE_TOOLS=false` 可整体关闭并回退到原有流式聊天。

## 当前能力

内置 Skill：

- `physics_experiment`：实验现象、数据趋势、误差和拟合结果解释。
- `symbolic_regression`：PySR 参数、任务状态、候选方程与可解释性。

内置 Tool：

- `search_physics_knowledge`：只检索本地知识库片段，不在工具内部再次调用 LLM。仅在
  `RAG_ENABLE_TOOL=true` 时注册，知识库未验证前保持关闭。检索链路为 BGE-M3
  dense+sparse → Qdrant RRF → BGE reranker，并返回文件名、页码或章节供回答引用。
- `start_symbolic_regression`：使用当前对话绑定的数据向 8000 计算服务提交 PySR 任务。
- `get_analysis_task_status`：读取队列位置、进度、耗时和候选方程摘要。
- `cancel_analysis_task`：取消等待中或运行中的 PySR 任务。
- `get_analysis_service_status`：读取并发槽位、队列长度、利用率与状态统计。

能力发现接口：

```http
GET /agent/capabilities
```

聊天接口仍为：

```http
POST /analyze_experiment
Content-Type: application/json

{
  "question": "用当前数据开始 PySR 拟合",
  "data_text": "0.1\t1.2\n0.2\t1.8",
  "data_filename": "experiment.txt",
  "data_mapping": "摆长→x0；Y 为周期",
  "skill": "symbolic_regression",
  "enable_tools": true,
  "conversation_id": "session-id"
}
```

`data_text` 会作为服务端 Tool 执行上下文绑定，不出现在模型生成的 Tool 参数中。模型只接收数据预览，PySR Tool 则把完整数据通过 `COMPUTE_SERVICE_URL` 转交计算服务。

## 新增 Tool

在 `ai_module/agent/capabilities.py` 中定义处理函数。处理函数应返回可 JSON 序列化的小对象，并避免返回大图、完整文件或密钥。需要访问计算任务时应通过 HTTP Tool 调用 `COMPUTE_SERVICE_URL`，不要导入 `pysr_module`。

```python
def _get_lab_device_status(device_id: str) -> dict:
    return {"device_id": device_id, "online": True}
```

然后注册 Schema：

```python
tools.register(
    ToolSpec(
        name="get_lab_device_status",
        description="查询实验设备在线状态。",
        parameters={
            "type": "object",
            "properties": {"device_id": {"type": "string"}},
            "required": ["device_id"],
            "additionalProperties": False,
        },
        handler=_get_lab_device_status,
    )
)
```

最后把工具名加入对应 Skill 的 `allowed_tools`。只注册 Tool 而不加入白名单时，Runner 会拒绝调用。

## 新增 Skill

```python
skills.register(
    AgentSkill(
        name="measurement_uncertainty",
        description="专注不确定度传播与误差分析。",
        instructions="先识别测量量、单位和仪器精度，再给出不确定度传播过程。",
        allowed_tools=("search_physics_knowledge",),
    )
)
```

客户端在请求中传入 `"skill": "measurement_uncertainty"` 即可选择。

## 安全边界

- 模型不能直接执行 Python 或 Shell，只能请求注册过的 Tool。
- 每个 Skill 都有 Tool 白名单；越权调用会作为失败结果返回模型。
- Tool 必填参数会在执行前校验，执行结果限制为 16,000 字符。
- 知识库、任务和服务对象均在服务端访问，不向模型暴露 API Key、进程对象或完整绘图数据。
- 达到最大轮数后，Runner 会停止调用工具并要求模型基于已有结果作答。
- 如果模型供应商不支持工具调用，聊天路由会自动回退到原有 SSE 流式回答。
- 浏览器使用后端签发的 HttpOnly 签名会话；`conversation_id` 只负责区分同一学生的对话，不能充当身份。
- AI 会把签名会话通过私网请求透传给计算服务，任务查询、取消和图表接口只接受任务所有者。
- 默认每个学生同时运行 1 个 PySR 任务、等待 2 个任务；AI 同一学生同时只生成 1 个回答。
- `start_symbolic_regression` 的 SSE Tool 轨迹包含结构化 `task_id`，前端据此轮询自己的任务卡片。

## 验证

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

Agent 测试使用假的模型响应，不消耗外部模型额度；调度测试也不启动 Julia。

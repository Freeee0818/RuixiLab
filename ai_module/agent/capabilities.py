"""Built-in GuideLab tools and skills.

RAG imports stay lazy, while compute-task tools cross the service boundary over
HTTP. Importing the AI service therefore never imports PySR or Julia code.
"""

from __future__ import annotations

import json
from typing import Any, Dict

import httpx

from config import settings

from .registry import AgentSkill, SkillRegistry, ToolRegistry, ToolSpec


def _compute_request(
    method: str,
    path: str,
    *,
    session_token: str = "",
    **kwargs: Any,
) -> Dict[str, Any]:
    base_url = settings.COMPUTE_SERVICE_URL.rstrip("/")
    try:
        headers = dict(kwargs.pop("headers", {}) or {})
        if session_token:
            headers[settings.CLASSROOM_SESSION_HEADER] = session_token
        with httpx.Client(timeout=min(settings.AI_TIMEOUT, 15.0), trust_env=False) as client:
            response = client.request(
                method,
                f"{base_url}{path}",
                headers=headers,
                **kwargs,
            )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("计算服务返回了非对象响应")
        return payload
    except Exception as exc:
        raise RuntimeError(f"计算服务不可用 ({base_url}): {exc}") from exc


def _session_token(context: Dict[str, Any] | None) -> str:
    return str((context or {}).get("session_token") or "")


def _compute_get(path: str, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
    return _compute_request("GET", path, session_token=_session_token(context))


def _analysis_task_status(
    task_id: str,
    _context: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    status = _compute_get(f"/tasks/{task_id}", _context)

    result = status.pop("result", None)
    if isinstance(result, dict):
        status["equations"] = [
            {
                "equation": item.get("equation"),
                "score": item.get("score"),
                "complexity": item.get("complexity"),
            }
            for item in (result.get("equations") or [])[:8]
        ]
    return status


def _analysis_service_status(
    _context: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    return _compute_get("/service-status", _context)


def _start_symbolic_regression(
    niterations: int = 100,
    population_size: int = 20,
    maxsize: int = 20,
    _context: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    context = _context or {}
    data_text = str(context.get("data_text") or "").strip()
    if not data_text:
        raise ValueError("当前对话没有接入数据，请先在分析页点击“使用为当前数据”")
    if context.get("submitted_task_id"):
        return {
            "task_id": context["submitted_task_id"],
            "status": "already_submitted",
            "message": "本轮对话已经提交过 PySR 任务，未重复创建。",
        }

    params: Dict[str, Any] = {
        "algorithm": "pysr",
        "niterations": niterations,
        "population_size": population_size,
        "maxsize": maxsize,
    }
    if isinstance(context.get("variable_mapping"), dict):
        params["variable_mapping"] = context["variable_mapping"]

    payload = _compute_request(
        "POST",
        "/tasks",
        session_token=_session_token(context),
        files={"file": ("agent_data.txt", data_text.encode("utf-8"), "text/plain")},
        data={"params": json.dumps(params, ensure_ascii=False)},
    )
    context["submitted_task_id"] = payload.get("task_id")
    return {
        "task_id": payload.get("task_id"),
        "status": "submitted",
        "message": "PySR 任务已提交；可使用任务 ID 查询进度。",
    }


def _cancel_analysis_task(
    task_id: str,
    _context: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    return _compute_request(
        "DELETE",
        f"/tasks/{task_id}",
        session_token=_session_token(_context),
    )


def _search_physics_knowledge(query: str, top_k: int = 5) -> Dict[str, Any]:
    from rag_module.service import rag_service

    sources = rag_service.retrieve(query, top_k=max(1, min(top_k, 6)))
    # Tool messages share a 16K safety budget with trace metadata. Parent
    # contexts remain larger in the service API, but Agent input is compact.
    for source in sources:
        source["excerpt"] = str(source.get("excerpt") or "")[:2000]
    return {"query": query, "sources": sources}


def build_default_registries() -> tuple[ToolRegistry, SkillRegistry]:
    tools = ToolRegistry()
    if settings.RAG_ENABLE_TOOL:
        tools.register(
            ToolSpec(
                name="search_physics_knowledge",
                description="检索本地物理实验知识库，返回答案摘要和来源片段。",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "具体的物理实验检索问题"},
                        "top_k": {"type": "integer", "minimum": 1, "maximum": 6, "default": 5},
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
                handler=_search_physics_knowledge,
            )
        )
    tools.register(
        ToolSpec(
            name="start_symbolic_regression",
            description="使用当前对话已接入的完整数据提交 PySR 符号回归任务，返回任务 ID。",
            parameters={
                "type": "object",
                "properties": {
                    "niterations": {"type": "integer", "minimum": 1, "maximum": 300, "default": 100},
                    "population_size": {"type": "integer", "minimum": 5, "maximum": 60, "default": 20},
                    "maxsize": {"type": "integer", "minimum": 5, "maximum": 40, "default": 20},
                },
                "additionalProperties": False,
            },
            handler=_start_symbolic_regression,
        )
    )
    tools.register(
        ToolSpec(
            name="get_analysis_task_status",
            description="查询一个符号回归任务的队列位置、进度、耗时和候选方程。",
            parameters={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "PySR 分析任务 ID"},
                },
                "required": ["task_id"],
                "additionalProperties": False,
            },
            handler=_analysis_task_status,
        )
    )
    tools.register(
        ToolSpec(
            name="cancel_analysis_task",
            description="取消一个等待中或运行中的 PySR 符号回归任务。",
            parameters={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "PySR 分析任务 ID"},
                },
                "required": ["task_id"],
                "additionalProperties": False,
            },
            handler=_cancel_analysis_task,
        )
    )
    tools.register(
        ToolSpec(
            name="get_analysis_service_status",
            description="查询分析服务的并发槽位、队列长度、利用率与任务状态统计。",
            parameters={"type": "object", "properties": {}, "additionalProperties": False},
            handler=_analysis_service_status,
        )
    )

    all_tools = (
        *(("search_physics_knowledge",) if settings.RAG_ENABLE_TOOL else ()),
        "start_symbolic_regression",
        "get_analysis_task_status",
        "cancel_analysis_task",
        "get_analysis_service_status",
    )
    skills = SkillRegistry()
    skills.register(
        AgentSkill(
            name="physics_experiment",
            description="解释物理实验、数据趋势、误差来源和拟合结果。",
            instructions=(
                "优先根据用户提供的数据、公式和图像作答。涉及教材结论或实验方法时可检索知识库；"
                "使用知识库结果时标明资料文件名和页码或章节；未检索到相关片段时明确说明，不要伪造来源；"
                "用户明确要求拟合且当前对话已接入数据时，调用符号回归工具提交任务；"
                "涉及任务进度时必须调用任务状态工具，不要猜测。工具结果要转述为学生易懂的结论。"
            ),
            allowed_tools=all_tools,
        )
    )
    skills.register(
        AgentSkill(
            name="symbolic_regression",
            description="专注 PySR 参数选择、队列状态、候选方程比较和物理可解释性。",
            instructions=(
                "围绕符号回归任务给出建议。任务状态和服务负载必须通过工具读取；"
                "用户要求开始拟合时直接调用符号回归工具；比较方程时同时考虑损失、复杂度和物理量纲，避免只选最高分。"
            ),
            allowed_tools=all_tools,
        )
    )
    return tools, skills

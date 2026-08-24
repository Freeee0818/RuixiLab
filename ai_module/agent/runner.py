"""OpenAI-compatible tool-calling loop used by the GuideLab assistant."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional
from uuid import uuid4

import httpx

from .registry import SkillRegistry, ToolExecution, ToolRegistry

CompletionCallable = Callable[[Dict[str, Any], Dict[str, Any]], Awaitable[Dict[str, Any]]]
AgentEventCallable = Callable[[Dict[str, Any]], Awaitable[None]]

_SENSITIVE_ARGUMENT = re.compile(r"(api.?key|token|secret|password|cookie)", re.IGNORECASE)
_CORRECTION_PROMPT = (
    "上一轮至少有一个工具调用失败。请检查工具返回的 error 与 JSON Schema；"
    "如果任务仍可完成，请修正参数或改用当前 Skill 授权的工具后重试。"
    "不要重复完全相同的失败调用；如果无法安全完成，请直接向用户说明阻断原因。"
)


def _safe_trace_arguments(arguments: Any) -> Dict[str, Any]:
    """Return a compact, redacted argument object suitable for browser audit."""
    try:
        parsed = json.loads(arguments) if isinstance(arguments, str) else arguments
    except (TypeError, json.JSONDecodeError):
        return {"_invalid_json": str(arguments)[:500]}
    if not isinstance(parsed, dict):
        return {"_invalid_arguments": str(parsed)[:500]}

    def redact(value: Any, *, key: str = "", depth: int = 0) -> Any:
        if key and _SENSITIVE_ARGUMENT.search(key):
            return "[REDACTED]"
        if depth >= 4:
            return "[TRUNCATED]"
        if isinstance(value, dict):
            return {
                str(item_key): redact(item_value, key=str(item_key), depth=depth + 1)
                for item_key, item_value in list(value.items())[:20]
            }
        if isinstance(value, list):
            return [redact(item, depth=depth + 1) for item in value[:20]]
        if isinstance(value, str):
            return value[:500]
        if isinstance(value, (int, float, bool)) or value is None:
            return value
        return str(value)[:500]

    return redact(parsed)


def _call_signature(name: str, arguments: Any) -> str:
    safe = _safe_trace_arguments(arguments)
    return f"{name}:{json.dumps(safe, ensure_ascii=False, sort_keys=True, default=str)}"


class AgentProviderError(RuntimeError):
    pass


@dataclass
class AgentResult:
    content: str
    reasoning: str = ""
    trace: List[Dict[str, Any]] = field(default_factory=list)
    rounds: int = 0
    run_id: str = ""
    model: str = ""
    skill: str = ""
    corrections: int = 0


class AgentRunner:
    def __init__(
        self,
        tools: ToolRegistry,
        skills: SkillRegistry,
        *,
        completion: Optional[CompletionCallable] = None,
    ) -> None:
        self.tools = tools
        self.skills = skills
        self._completion = completion

    async def _complete(self, payload: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        if self._completion:
            return await self._completion(payload, config)

        try:
            async with httpx.AsyncClient(timeout=config["timeout"]) as client:
                response = await client.post(
                    f"{config['base_url']}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {config['api_key']}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
                return response.json()
        except Exception as exc:
            raise AgentProviderError(f"Agent 模型请求失败: {exc}") from exc

    @staticmethod
    def _message_from_response(response: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return response["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AgentProviderError("Agent 模型返回格式不兼容") from exc

    async def run(
        self,
        *,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        skill_name: str,
        provider_config: Dict[str, Any],
        max_tool_rounds: int = 3,
        tool_context: Optional[Dict[str, Any]] = None,
        on_event: Optional[AgentEventCallable] = None,
    ) -> AgentResult:
        skill = self.skills.get(skill_name)
        run_id = f"agent_{uuid4().hex}"
        model_name = str(provider_config["model"])
        sequence = 0

        async def emit(event: Dict[str, Any]) -> None:
            nonlocal sequence
            if not on_event:
                return
            sequence += 1
            await on_event({
                "run_id": run_id,
                "sequence": sequence,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "model": model_name,
                "skill": skill.name,
                **event,
            })

        conversation = [
            {
                "role": "system",
                "content": f"{system_prompt}\n\n【当前 Skill】{skill.name}\n{skill.instructions}",
            },
            *messages,
        ]
        trace: List[Dict[str, Any]] = []
        reasoning_parts: List[str] = []
        tool_schemas = self.tools.schemas(skill.allowed_tools)
        rounds = max(1, min(int(max_tool_rounds), 6))
        failed_signatures: set[str] = set()
        corrections = 0

        await emit({"type": "agent", "phase": "started", "max_tool_rounds": rounds})

        for round_index in range(rounds):
            payload = {
                "model": provider_config["model"],
                "messages": conversation,
                "temperature": provider_config["temperature"],
                "max_tokens": provider_config["max_tokens"],
                "stream": False,
                "tools": tool_schemas,
                "tool_choice": "auto",
            }
            if provider_config.get("enable_thinking"):
                payload["enable_thinking"] = True

            response = await self._complete(payload, provider_config)
            assistant = self._message_from_response(response)
            reasoning = assistant.get("reasoning_content") or ""
            if reasoning:
                reasoning_parts.append(reasoning)
            tool_calls = assistant.get("tool_calls") or []
            if not tool_calls:
                result = AgentResult(
                    content=assistant.get("content") or "模型未返回有效回答。",
                    reasoning="".join(reasoning_parts),
                    trace=trace,
                    rounds=round_index + 1,
                    run_id=run_id,
                    model=model_name,
                    skill=skill.name,
                    corrections=corrections,
                )
                await emit({
                    "type": "agent",
                    "phase": "finished",
                    "rounds": result.rounds,
                    "corrections": corrections,
                    "tool_calls": len(trace),
                })
                return result

            conversation.append(
                {
                    "role": "assistant",
                    "content": assistant.get("content"),
                    "tool_calls": tool_calls,
                }
            )
            round_failed = False
            for call in tool_calls:
                function = call.get("function") or {}
                tool_name = function.get("name") or "unknown"
                arguments = function.get("arguments") or "{}"
                call_id = call.get("id") or f"call_{round_index}_{tool_name}"
                trace_arguments = _safe_trace_arguments(arguments)
                signature = _call_signature(tool_name, arguments)
                base_trace = {
                    "tool": tool_name,
                    "call_id": call_id,
                    "round": round_index + 1,
                    "arguments": trace_arguments,
                }
                await emit({"type": "tool", "phase": "started", **base_trace})

                if signature in failed_signatures:
                    execution = ToolExecution(
                        name=tool_name,
                        ok=False,
                        error="已阻止与上一轮完全相同的失败调用，请修改参数或策略",
                    )
                else:
                    execution = await self.tools.execute(
                        tool_name,
                        arguments,
                        allowed_tools=skill.allowed_tools,
                        context=tool_context,
                    )

                trace_item = {**execution.trace_dict(), **base_trace, "phase": "finished"}
                trace.append(trace_item)
                await emit({"type": "tool", **trace_item})
                if not execution.ok:
                    round_failed = True
                    failed_signatures.add(signature)
                conversation.append(
                    {
                        "role": "tool",
                        "tool_call_id": call_id,
                        "name": tool_name,
                        "content": execution.content(),
                    }
                )

            if round_failed:
                corrections += 1
                conversation.append({"role": "system", "content": _CORRECTION_PROMPT})
                await emit({
                    "type": "correction",
                    "phase": "requested",
                    "round": round_index + 1,
                    "message": _CORRECTION_PROMPT,
                })

        final_payload = {
            "model": provider_config["model"],
            "messages": conversation + [
                {"role": "system", "content": "请根据已获得的工具结果直接给出最终答复，不再调用工具。"}
            ],
            "temperature": provider_config["temperature"],
            "max_tokens": provider_config["max_tokens"],
            "stream": False,
        }
        final_response = await self._complete(final_payload, provider_config)
        final_message = self._message_from_response(final_response)
        result = AgentResult(
            content=final_message.get("content") or "模型未返回有效回答。",
            reasoning="".join(reasoning_parts) + (final_message.get("reasoning_content") or ""),
            trace=trace,
            rounds=rounds + 1,
            run_id=run_id,
            model=model_name,
            skill=skill.name,
            corrections=corrections,
        )
        await emit({
            "type": "agent",
            "phase": "finished",
            "rounds": result.rounds,
            "corrections": corrections,
            "tool_calls": len(trace),
        })
        return result

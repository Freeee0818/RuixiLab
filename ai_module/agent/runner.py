"""OpenAI-compatible tool-calling loop used by the GuideLab assistant."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

import httpx

from .registry import SkillRegistry, ToolRegistry

CompletionCallable = Callable[[Dict[str, Any], Dict[str, Any]], Awaitable[Dict[str, Any]]]


class AgentProviderError(RuntimeError):
    pass


@dataclass
class AgentResult:
    content: str
    reasoning: str = ""
    trace: List[Dict[str, Any]] = field(default_factory=list)
    rounds: int = 0


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
    ) -> AgentResult:
        skill = self.skills.get(skill_name)
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
                return AgentResult(
                    content=assistant.get("content") or "模型未返回有效回答。",
                    reasoning="".join(reasoning_parts),
                    trace=trace,
                    rounds=round_index + 1,
                )

            conversation.append(
                {
                    "role": "assistant",
                    "content": assistant.get("content"),
                    "tool_calls": tool_calls,
                }
            )
            for call in tool_calls:
                function = call.get("function") or {}
                tool_name = function.get("name") or "unknown"
                execution = await self.tools.execute(
                    tool_name,
                    function.get("arguments") or "{}",
                    allowed_tools=skill.allowed_tools,
                    context=tool_context,
                )
                trace.append(execution.trace_dict())
                conversation.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.get("id") or f"call_{round_index}_{tool_name}",
                        "name": tool_name,
                        "content": execution.content(),
                    }
                )

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
        return AgentResult(
            content=final_message.get("content") or "模型未返回有效回答。",
            reasoning="".join(reasoning_parts) + (final_message.get("reasoning_content") or ""),
            trace=trace,
            rounds=rounds + 1,
        )

"""Registries for declarative Agent skills and executable tools."""

from __future__ import annotations

import asyncio
import inspect
import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, Optional


def _validate_schema(value: Any, schema: Dict[str, Any], path: str = "参数") -> None:
    """Validate the JSON-Schema subset used by GuideLab Tool definitions."""
    expected = schema.get("type")
    type_checks = {
        "object": lambda item: isinstance(item, dict),
        "array": lambda item: isinstance(item, list),
        "string": lambda item: isinstance(item, str),
        "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
        "number": lambda item: isinstance(item, (int, float)) and not isinstance(item, bool),
        "boolean": lambda item: isinstance(item, bool),
        "null": lambda item: item is None,
    }
    if expected in type_checks and not type_checks[expected](value):
        raise ValueError(f"{path}必须是 {expected} 类型")

    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(f"{path}不在允许值范围内")

    if expected == "object":
        properties = schema.get("properties", {})
        missing = [name for name in schema.get("required", []) if name not in value]
        if missing:
            raise ValueError(f"{path}缺少必填字段: {', '.join(missing)}")
        if schema.get("additionalProperties") is False:
            unexpected = [name for name in value if name not in properties]
            if unexpected:
                raise ValueError(f"{path}包含未授权字段: {', '.join(unexpected)}")
        for name, item in value.items():
            if name in properties:
                _validate_schema(item, properties[name], f"{path}.{name}")
    elif expected == "array":
        if "minItems" in schema and len(value) < schema["minItems"]:
            raise ValueError(f"{path}项目数不能少于 {schema['minItems']}")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            raise ValueError(f"{path}项目数不能多于 {schema['maxItems']}")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                _validate_schema(item, item_schema, f"{path}[{index}]")
    elif expected == "string":
        if "minLength" in schema and len(value) < schema["minLength"]:
            raise ValueError(f"{path}长度不能小于 {schema['minLength']}")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            raise ValueError(f"{path}长度不能大于 {schema['maxLength']}")
    elif expected in {"integer", "number"}:
        if "minimum" in schema and value < schema["minimum"]:
            raise ValueError(f"{path}不能小于 {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            raise ValueError(f"{path}不能大于 {schema['maximum']}")


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable[..., Any] = field(repr=False)

    def openai_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


@dataclass(frozen=True)
class AgentSkill:
    name: str
    description: str
    instructions: str
    allowed_tools: tuple[str, ...] = ()

    def public_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "allowed_tools": list(self.allowed_tools),
        }


@dataclass
class ToolExecution:
    name: str
    ok: bool
    output: Any = None
    error: Optional[str] = None
    duration_ms: int = 0

    def content(self) -> str:
        payload = {
            "ok": self.ok,
            "result": self.output if self.ok else None,
            "error": self.error,
        }
        return json.dumps(payload, ensure_ascii=False, default=str)[:16_000]

    def trace_dict(self) -> Dict[str, Any]:
        trace = {
            "tool": self.name,
            "ok": self.ok,
            "duration_ms": self.duration_ms,
            "error": self.error,
        }
        # Only expose the small fields needed by the browser to follow an
        # Agent-created task.  Full tool output still stays inside the model
        # conversation and is not duplicated into the SSE trace.
        if self.ok and isinstance(self.output, dict):
            for key in ("task_id", "status", "message", "progress", "queue_position"):
                if key in self.output:
                    trace[key] = self.output[key]
        return trace


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        if spec.name in self._tools:
            raise ValueError(f"Tool already registered: {spec.name}")
        self._tools[spec.name] = spec

    def schemas(self, allowed_tools: Iterable[str]) -> list[Dict[str, Any]]:
        return [self._tools[name].openai_schema() for name in allowed_tools if name in self._tools]

    def public_tools(self) -> list[Dict[str, Any]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            }
            for tool in self._tools.values()
        ]

    async def execute(
        self,
        name: str,
        arguments: Any,
        *,
        allowed_tools: Iterable[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> ToolExecution:
        started = time.perf_counter()
        allowed = set(allowed_tools)
        if name not in allowed:
            return ToolExecution(
                name=name,
                ok=False,
                error="当前 Skill 未授权调用该工具",
                duration_ms=int((time.perf_counter() - started) * 1000),
            )

        spec = self._tools.get(name)
        if not spec:
            return ToolExecution(
                name=name,
                ok=False,
                error="工具不存在",
                duration_ms=int((time.perf_counter() - started) * 1000),
            )

        try:
            parsed = json.loads(arguments) if isinstance(arguments, str) else arguments
            parsed = parsed or {}
            if not isinstance(parsed, dict):
                raise ValueError("工具参数必须是 JSON 对象")
            try:
                _validate_schema(parsed, spec.parameters)
            except ValueError as exc:
                raise ValueError(f"工具参数不符合 Schema: {exc}") from exc

            if "_context" in inspect.signature(spec.handler).parameters:
                parsed["_context"] = context or {}

            if inspect.iscoroutinefunction(spec.handler):
                output = await spec.handler(**parsed)
            else:
                output = await asyncio.to_thread(spec.handler, **parsed)
            return ToolExecution(
                name=name,
                ok=True,
                output=output,
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
        except Exception as exc:
            return ToolExecution(
                name=name,
                ok=False,
                error=str(exc),
                duration_ms=int((time.perf_counter() - started) * 1000),
            )


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: Dict[str, AgentSkill] = {}

    def register(self, skill: AgentSkill) -> None:
        if skill.name in self._skills:
            raise ValueError(f"Skill already registered: {skill.name}")
        self._skills[skill.name] = skill

    def get(self, name: str) -> AgentSkill:
        try:
            return self._skills[name]
        except KeyError as exc:
            raise ValueError(f"未知 Skill: {name}") from exc

    def public_skills(self) -> list[Dict[str, Any]]:
        return [skill.public_dict() for skill in self._skills.values()]

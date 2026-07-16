"""In-process classroom limits for paid LLM requests.

The AI service intentionally runs as one Uvicorn worker because conversation
history and the limiter are process-local.  A future Redis deployment can keep
the same acquire/release interface.
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Dict


@dataclass(frozen=True)
class LimitDecision:
    allowed: bool
    message: str = ""


class ClassroomRequestLimiter:
    def __init__(
        self,
        *,
        max_global_active: int,
        max_session_active: int,
        max_session_per_minute: int,
    ) -> None:
        self.max_global_active = max(1, int(max_global_active))
        self.max_session_active = max(1, int(max_session_active))
        self.max_session_per_minute = max(1, int(max_session_per_minute))
        self._lock = asyncio.Lock()
        self._global_active = 0
        self._session_active: Dict[str, int] = defaultdict(int)
        self._recent: Dict[str, Deque[float]] = defaultdict(deque)

    async def acquire(self, session_id: str) -> LimitDecision:
        now = time.monotonic()
        async with self._lock:
            recent = self._recent[session_id]
            while recent and now - recent[0] >= 60:
                recent.popleft()

            if len(recent) >= self.max_session_per_minute:
                return LimitDecision(False, "提问过于频繁，请稍后再试")
            if self._session_active[session_id] >= self.max_session_active:
                return LimitDecision(False, "当前已有 AI 回答正在生成，请等待完成")
            if self._global_active >= self.max_global_active:
                return LimitDecision(False, "课堂 AI 当前较忙，请稍后再试")

            recent.append(now)
            self._session_active[session_id] += 1
            self._global_active += 1
            return LimitDecision(True)

    async def release(self, session_id: str) -> None:
        async with self._lock:
            if self._session_active.get(session_id, 0) > 0:
                self._session_active[session_id] -= 1
                self._global_active = max(0, self._global_active - 1)
            if self._session_active.get(session_id) == 0:
                self._session_active.pop(session_id, None)


__all__ = ["ClassroomRequestLimiter", "LimitDecision"]

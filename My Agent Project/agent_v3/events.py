"""Events: everything a frontend learns about a session arrives as one of these (plan §7).

Producers (session, model adapter, executor, approval gateway) build events with the common
fields left at their defaults; `Session` stamps `session_id`, `seq`, `ts` (and `turn_id` for
events that came from a turn) just before delivery.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import PurePath
from typing import Any, ClassVar

PROTOCOL_VERSION = 1


def jsonable(value: Any) -> Any:
    """Convert to plain JSON types (Enum → value, Path → str, tuples/sets → lists)."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, PurePath):
        return str(value)
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [jsonable(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if dataclasses.is_dataclass(value):
        return jsonable(dataclasses.asdict(value))
    return str(value)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


@dataclass(frozen=True, kw_only=True)
class Event:
    type: ClassVar[str] = "event"
    session_id: str = ""
    turn_id: str | None = None
    seq: int = 0
    ts: str = ""

    def to_dict(self) -> dict:
        data = {f.name: getattr(self, f.name) for f in dataclasses.fields(self)}
        return {"type": self.type, **jsonable(data)}


@dataclass(frozen=True, kw_only=True)
class SessionStarted(Event):
    type: ClassVar[str] = "session_started"
    protocol_version: int = PROTOCOL_VERSION
    config: dict = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class TurnStarted(Event):
    type: ClassVar[str] = "turn_started"
    user_message: str


@dataclass(frozen=True, kw_only=True)
class ModelRoundStarted(Event):
    type: ClassVar[str] = "model_round_started"
    round: int


@dataclass(frozen=True, kw_only=True)
class TextDelta(Event):
    type: ClassVar[str] = "text_delta"
    round: int
    text: str


@dataclass(frozen=True, kw_only=True)
class ModelRetry(Event):
    """The round's stream broke; frontends discard the partial text of this round."""
    type: ClassVar[str] = "model_retry"
    round: int
    attempt: int
    reason: str
    delay_s: float


@dataclass(frozen=True, kw_only=True)
class ModelRoundCompleted(Event):
    type: ClassVar[str] = "model_round_completed"
    round: int
    duration_s: float
    input_tokens: int
    cached_tokens: int
    output_tokens: int
    reasoning_tokens: int
    cost_usd: float | None
    function_calls: int


@dataclass(frozen=True, kw_only=True)
class WebAction(Event):
    type: ClassVar[str] = "web_action"
    kind: str                       # search | open_page | find_in_page
    detail: str


@dataclass(frozen=True, kw_only=True)
class ToolStarted(Event):
    type: ClassVar[str] = "tool_started"
    call_id: str
    name: str
    group: int
    target: str
    args: Any


@dataclass(frozen=True, kw_only=True)
class ToolCompleted(Event):
    type: ClassVar[str] = "tool_completed"
    call_id: str
    name: str
    group: int
    ok: bool
    summary: str
    error_code: str | None
    duration_s: float
    output: str
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class ApprovalRequested(Event):
    type: ClassVar[str] = "approval_requested"
    request: dict


@dataclass(frozen=True, kw_only=True)
class ApprovalResolved(Event):
    type: ClassVar[str] = "approval_resolved"
    request_id: str
    decision: str
    feedback: str | None = None
    by: str = "user"                # user | policy | cancel
    wait_s: float = 0.0


@dataclass(frozen=True, kw_only=True)
class Notice(Event):
    type: ClassVar[str] = "notice"
    level: str                      # info | warning
    code: str
    message: str


@dataclass(frozen=True, kw_only=True)
class TurnCompleted(Event):
    type: ClassVar[str] = "turn_completed"
    text: str
    sources: list = field(default_factory=list)       # cited [{title, url}]
    sources_all: list = field(default_factory=list)   # every source the web tool returned, for auditing
    stats: dict = field(default_factory=dict)
    stop_reason: str = "done"       # done | max_rounds | max_time | max_cost


@dataclass(frozen=True, kw_only=True)
class TurnCancelled(Event):
    type: ClassVar[str] = "turn_cancelled"
    stats: dict = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class TurnFailed(Event):
    type: ClassVar[str] = "turn_failed"
    error_code: str
    message: str
    stats: dict = field(default_factory=dict)


EVENT_TYPES: dict[str, type[Event]] = {cls.type: cls for cls in (
    SessionStarted, TurnStarted, ModelRoundStarted, TextDelta, ModelRetry, ModelRoundCompleted, WebAction,
    ToolStarted, ToolCompleted, ApprovalRequested, ApprovalResolved, Notice, TurnCompleted, TurnCancelled,
    TurnFailed)}


def event_from_dict(data: dict) -> Event:
    """Rebuild an Event from its `to_dict()` (e.g. a line of a saved log). Unknown keys are ignored.

    Raises ValueError for an unknown `type` and TypeError when a required field is missing.
    """
    cls = EVENT_TYPES.get(data.get("type"))
    if cls is None:
        raise ValueError(f"unknown event type {data.get('type')!r}")
    names = {f.name for f in dataclasses.fields(cls)}
    return cls(**{k: v for k, v in data.items() if k in names})

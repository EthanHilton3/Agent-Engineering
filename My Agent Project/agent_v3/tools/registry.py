from __future__ import annotations

import threading
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel

from ..approvals import ApprovalGateway, ApprovalRequest
from ..config import AgentConfig
from ..workspace import CancelToken, FileState, WorkspacePolicy


class ErrorCode(StrEnum):
    INVALID_ARGUMENTS = "invalid_arguments"
    UNKNOWN_TOOL = "unknown_tool"
    NOT_FOUND = "not_found"
    OUTSIDE_WORKSPACE = "outside_workspace"
    CONFLICT = "conflict"              # file changed since agent last saw it / unread overwrite
    NO_MATCH = "no_match"              # edit text not found
    AMBIGUOUS = "ambiguous"            # edit text found multiple times
    BINARY = "binary"
    TOO_LARGE = "too_large"
    REJECTED = "rejected"
    TIMEOUT = "timeout"
    NONZERO_EXIT = "nonzero_exit"
    CANCELLED = "cancelled"
    REPEATED_FAILURE = "repeated_failure"
    NOT_A_REPO = "not_a_repo"
    INTERNAL = "internal_error"


@dataclass
class ToolResult:
    ok: bool
    output: str                        # exactly what the model sees (already capped)
    summary: str                       # ≤ 80 chars for UI rows, e.g. "42 lines", "exit 0 · 3.2s"
    error_code: ErrorCode | None = None
    metadata: dict[str, Any] = field(default_factory=dict)  # JSON-serializable only

    @classmethod
    def success(cls, output: str, summary: str, **metadata: Any) -> "ToolResult":
        return cls(True, output, summary[:80], None, metadata)

    @classmethod
    def failure(cls, code: ErrorCode, message: str, summary: str | None = None,
                **metadata: Any) -> "ToolResult":
        return cls(False, f"Error ({code.value}): {message}",
                   (summary or code.value)[:80], code, metadata)


@dataclass
class ToolContext:
    config: AgentConfig
    workspace: WorkspacePolicy
    files: FileState                 # thread-safe path → sha of last content the agent saw/wrote
    approvals: ApprovalGateway
    cancel: CancelToken
    turn_id: str
    call_id: str
    seen_reads: dict                 # per-turn dedupe cache (§6.4); guarded by seen_lock
    seen_lock: threading.Lock = field(default_factory=threading.Lock)

    @property
    def output_dir(self) -> Path:
        return Path(self.config.output_dir) if self.config.output_dir \
            else self.workspace.root / ".agent_v3" / "outputs"


@dataclass(frozen=True)
class ToolSpec:
    name: str
    args_model: type[BaseModel]
    func: Callable[[Any, ToolContext], ToolResult]
    read_only: bool              # True → no approval, may run in parallel
    description: str             # what it does + when to use it + what it returns


class ToolRegistry:
    def __init__(self, specs: list[ToolSpec] | None = None):
        self._specs: dict[str, ToolSpec] = {}
        for spec in specs or []:
            self.register(spec)

    def register(self, spec: ToolSpec) -> None:
        if spec.name in self._specs:
            raise ValueError(f"duplicate tool name: {spec.name}")
        self._specs[spec.name] = spec

    def get(self, name: str) -> ToolSpec | None:
        return self._specs.get(name)

    def names(self) -> list[str]:
        return list(self._specs)

    def schemas(self) -> list[dict]:
        """Responses API function tools, in registration order (never reordered within a session)."""
        return [{"type": "function", "name": s.name, "description": s.description,
                 "parameters": strict_schema(s.args_model), "strict": True}
                for s in self._specs.values()]


def ask_approval(ctx: ToolContext, req: ApprovalRequest) -> ToolResult | None:
    """Ask the gateway. Returns None when allowed, or the REJECTED/CANCELLED result to hand back.

    A cancel can land while the user is approving; checking here means no tool acts after it."""
    res = ctx.approvals.request(req, turn_id=ctx.turn_id, cancel=ctx.cancel)
    if ctx.cancel.cancelled:
        return ToolResult.failure(ErrorCode.CANCELLED, "Cancelled by user before running.", summary="cancelled")
    if res.allowed:
        return None
    what = "command" if req.kind == "command" else "edit"
    msg = f"The user rejected this {what}."
    if res.feedback:
        msg += f"\nUser feedback: {res.feedback}"
    return ToolResult.failure(ErrorCode.REJECTED, msg, summary="rejected")


# ---------------------------------------------------------------------------------------------
# Strict JSON schema (OpenAI function-calling "strict" form)
# ---------------------------------------------------------------------------------------------

_KEPT_KEYS = ("type", "description", "enum", "minimum", "maximum")


def strict_schema(model: type[BaseModel]) -> dict:
    """Convert a Pydantic model's JSON schema to OpenAI strict form.

    Every property is required (optional ones are nullable via anyOf), every object has
    additionalProperties=false, $refs are inlined, and title/default and other keys are dropped.
    """
    raw = model.model_json_schema()
    defs = raw.get("$defs", {})

    def conv(node: dict) -> dict:
        if "$ref" in node:
            target = defs[node["$ref"].rsplit("/", 1)[-1]]
            return conv({**target, **{k: v for k, v in node.items() if k != "$ref"}})
        if "allOf" in node and len(node["allOf"]) == 1:     # older pydantic wraps refs in allOf
            return conv({**node["allOf"][0], **{k: v for k, v in node.items() if k != "allOf"}})
        out = {k: node[k] for k in _KEPT_KEYS if k in node}
        if "anyOf" in node:
            out["anyOf"] = [conv(n) for n in node["anyOf"]]
        if node.get("type") == "object" or "properties" in node:
            props = node.get("properties", {})
            out["type"] = "object"
            out["properties"] = {k: conv(v) for k, v in props.items()}
            out["required"] = list(props)
            out["additionalProperties"] = False
        if node.get("type") == "array" and "items" in node:
            out["items"] = conv(node["items"])
        return out

    return conv(raw)

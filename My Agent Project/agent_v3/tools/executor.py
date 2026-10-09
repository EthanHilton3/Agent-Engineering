from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from typing import Any, Callable, Iterable

from pydantic import ValidationError

from ..config import AgentConfig
from .registry import ErrorCode, ToolContext, ToolRegistry, ToolResult

# Failures that say nothing about whether an identical retry could succeed.
_NOT_REPEAT_GUARDED = {ErrorCode.REJECTED, ErrorCode.NONZERO_EXIT, ErrorCode.CANCELLED}

# emit(event_type, fields): Phase 2 turns these into Event dataclasses.
Emit = Callable[[str, dict], None]


@dataclass
class ToolCall:
    """Minimal view of a Responses API `function_call` item (any object with these attributes works)."""
    call_id: str
    name: str
    arguments: str


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _target(args: Any) -> str:
    if isinstance(args, dict):
        if isinstance(args.get("edits"), list):
            paths = [e.get("path", "") for e in args["edits"] if isinstance(e, dict)]
            return ", ".join(dict.fromkeys(paths))[:120]
        for key in ("path", "command", "pattern"):
            if isinstance(args.get(key), str):
                return args[key][:120]
    return ""


class ToolExecutor:
    def __init__(self, registry: ToolRegistry, config: AgentConfig, emit: Emit | None = None):
        self.registry = registry
        self.config = config
        self._emit = emit or (lambda *_: None)
        self._pool = ThreadPoolExecutor(max_workers=max(1, config.max_parallel_reads),
                                        thread_name_prefix="tool")
        self._failures: dict[str, dict[str, str]] = {}   # turn_id → call key → first line of the error
        self._lock = threading.Lock()

    def shutdown(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)

    def forget_turn(self, turn_id: str) -> None:
        with self._lock:
            self._failures.pop(turn_id, None)

    # -- batch ------------------------------------------------------------------------------

    def _plan(self, calls: list[Any]) -> list[list[int]]:
        """Group consecutive read-only calls; every other call is a barrier that runs alone."""
        groups: list[list[int]] = []
        prev_read_only = False
        for i, call in enumerate(calls):
            spec = self.registry.get(call.name)
            read_only = bool(spec and spec.read_only) and self.config.parallel_reads
            if read_only and prev_read_only:
                groups[-1].append(i)
            else:
                groups.append([i])
            prev_read_only = read_only
        return groups

    def run_batch(self, calls: Iterable[Any], ctx: ToolContext) -> list[tuple[Any, ToolResult, float]]:
        """Run the model's tool calls; results come back in call order."""
        calls = list(calls)
        results: list[tuple[Any, ToolResult, float] | None] = [None] * len(calls)
        for group, idxs in enumerate(self._plan(calls), start=1):
            if ctx.cancel.cancelled:
                for i in idxs:
                    results[i] = self._cancelled(calls[i], ctx, group)
            elif len(idxs) == 1:
                results[idxs[0]] = self._run_one(calls[idxs[0]], idxs[0], group, ctx)
            else:
                futures = [self._pool.submit(self._run_one, calls[i], i, group, ctx) for i in idxs]
                for i, fut in zip(idxs, futures):
                    results[i] = fut.result()
        return results  # type: ignore[return-value]

    def _cancelled(self, call: Any, ctx: ToolContext, group: int) -> tuple[Any, ToolResult, float]:
        result = ToolResult.failure(ErrorCode.CANCELLED, "Cancelled by user before running.", summary="cancelled")
        self._emit("tool_completed", self._completed_fields(call, ctx, group, result, 0.0))
        return call, result, 0.0

    def _completed_fields(self, call: Any, ctx: ToolContext, group: int, result: ToolResult, dur: float) -> dict:
        return {"turn_id": ctx.turn_id, "call_id": call.call_id, "name": call.name, "group": group,
                "ok": result.ok, "summary": result.summary,
                "error_code": result.error_code.value if result.error_code else None,
                "duration_s": round(dur, 3), "output": result.output, "metadata": result.metadata}

    def _run_one(self, call: Any, index: int, group: int, ctx: ToolContext) -> tuple[Any, ToolResult, float]:
        cctx = replace(ctx, call_id=call.call_id, call_index=index)
        try:
            args_json: Any = json.loads(call.arguments)
        except (json.JSONDecodeError, TypeError):
            args_json = call.arguments
        self._emit("tool_started", {"turn_id": ctx.turn_id, "call_id": call.call_id, "name": call.name,
                                    "group": group, "target": _target(args_json), "args": args_json})
        start = time.monotonic()
        try:
            result = self._execute(call, cctx)
        except Exception as e:      # _execute handles tool errors; this is the last line of defence
            result = ToolResult.failure(ErrorCode.INTERNAL, f"{type(e).__name__}: {e}")
        dur = time.monotonic() - start
        self._emit("tool_completed", self._completed_fields(call, ctx, group, result, dur))
        return call, result, dur

    # -- one call ---------------------------------------------------------------------------

    def _execute(self, call: Any, ctx: ToolContext) -> ToolResult:
        spec = self.registry.get(call.name)
        if spec is None:
            return ToolResult.failure(ErrorCode.UNKNOWN_TOOL, f"No tool named '{call.name}'. "
                                      f"Available: {', '.join(self.registry.names())}", summary="unknown tool")
        raw = call.arguments
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, TypeError) as e:
            return ToolResult.failure(ErrorCode.INVALID_ARGUMENTS,
                                      f"Arguments are not valid JSON ({e}). Raw arguments: {str(raw)[:200]}",
                                      summary="invalid JSON")
        try:
            args = spec.args_model.model_validate(parsed)
        except ValidationError as e:
            problems = "; ".join(f"{'.'.join(map(str, err['loc'])) or '(root)'}: {err['msg']}" for err in e.errors())
            return ToolResult.failure(ErrorCode.INVALID_ARGUMENTS, problems, summary="invalid arguments")

        key = f"{call.name}\0{canonical_json(parsed)}"
        with self._lock:
            previous = self._failures.get(ctx.turn_id, {}).get(key)
        if previous is not None:
            return ToolResult.failure(ErrorCode.REPEATED_FAILURE,
                                      f"This identical call already failed: {previous}. "
                                      "Change the arguments or approach.", summary="repeated failure")

        try:
            result = spec.func(args, ctx)
        except Exception as e:
            result = ToolResult.failure(ErrorCode.INTERNAL, f"{type(e).__name__}: {e}")

        with self._lock:
            if not result.ok and result.error_code not in _NOT_REPEAT_GUARDED:
                self._failures.setdefault(ctx.turn_id, {})[key] = result.output.split("\n", 1)[0]
            elif result.ok and not spec.read_only:
                # State changed, so earlier failures (e.g. "file not found") may no longer repeat.
                self._failures.pop(ctx.turn_id, None)
        return result

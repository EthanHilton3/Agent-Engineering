"""Session: the public API frontends drive (plan §8.1), the turn loop, budgets, pruning, cancel.

Threading model
- Each turn runs on a daemon worker thread; `on_event` is called from worker/tool threads.
- One re-entrant lock (`_lock`) guards session state, event delivery, and the approval gateway's
  pending slot, so events reach `on_event` in `seq` order and state changes are atomic with the
  events that announce them. `on_event` therefore runs under that lock: it must be quick and
  must not block on another thread (push into a queue, as the CLI does).
- `cancel()` commits the cancellation itself and bumps `_generation`. A worker whose generation is
  stale (or whose token is cancelled) never touches history, and its events are dropped because
  they carry a turn_id that is no longer active.
"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from collections import Counter
from dataclasses import dataclass, fields, replace
from typing import Callable

from .approvals import ApprovalGateway, ApprovalPolicy, Decision
from .config import AgentConfig
from .events import (ApprovalResolved, Event, ModelRoundCompleted, ModelRoundStarted, Notice, SessionStarted,
                     ToolCompleted, ToolStarted, TurnCancelled, TurnCompleted, TurnFailed, TurnStarted, WebAction,
                     now_iso)
from .model import Cancelled, ModelAdapter, ModelError, ModelResponse, web_tools
from .prompt import build_system_prompt, prompt_cache_key
from .tools import build_registry
from .tools.executor import ToolCall, ToolExecutor
from .tools.files import plural
from .tools.registry import ToolContext, ToolRegistry
from .workspace import CancelToken, FileState, WorkspacePolicy

logger = logging.getLogger(__name__)

TURN_RECORD_MAX_CHARS = 600
SUMMARY_INSTRUCTION = ("Budget reached ({reason}). Do not call tools. Summarize what was done, what was verified, "
                       "and what remains.")


class Busy(RuntimeError):
    """A turn is running; the command needs an idle session."""


@dataclass
class TurnStats:
    rounds: int = 0
    tool_calls: int = 0
    parallel_groups: int = 0
    web_searches: int = 0
    web_opens: int = 0
    web_finds: int = 0
    input_tokens: int = 0
    cached_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    model_cost_usd: float = 0.0
    web_cost_usd: float = 0.0
    elapsed_s: float = 0.0
    model_wait_s: float = 0.0
    tool_wait_s: float = 0.0
    approval_wait_s: float = 0.0

    def add(self, other: "TurnStats") -> None:
        for f in fields(self):
            setattr(self, f.name, getattr(self, f.name) + getattr(other, f.name))

    def to_dict(self) -> dict:
        out = {}
        for f in fields(self):
            v = getattr(self, f.name)
            out[f.name] = round(v, 6 if f.name.endswith("_usd") else 3) if isinstance(v, float) else v
        return out


def _clip(text: str, n: int) -> str:
    return text if len(text) <= n else text[: n - 1] + "…"


class _Turn:
    """Per-turn state. `observe` runs under the session lock for every delivered event of this turn."""

    def __init__(self, turn_id: str, generation: int, user_message: str, base_history: list, web_fee: float):
        self.id = turn_id
        self.generation = generation
        self.user_message = user_message
        self.base_history = base_history         # history snapshot taken at start_turn
        self.web_fee = web_fee
        self.cancel = CancelToken()
        self.started = time.monotonic()
        self.stats = TurnStats()
        self.sources: list[dict] = []
        self.sources_all: list[dict] = []
        self._started_calls: dict[str, ToolStarted] = {}
        self._group_sizes: Counter = Counter()
        self._reads: dict[str, None] = {}
        self._edits: dict[str, list[int]] = {}
        self._commands: list[str] = []
        self._rejected: list[str] = []

    def observe(self, ev: Event) -> None:
        s = self.stats
        if isinstance(ev, ModelRoundCompleted):
            s.rounds += 1
            s.input_tokens += ev.input_tokens
            s.cached_tokens += ev.cached_tokens
            s.output_tokens += ev.output_tokens
            s.reasoning_tokens += ev.reasoning_tokens
            s.model_cost_usd += ev.cost_usd or 0.0
            s.model_wait_s += ev.duration_s
        elif isinstance(ev, WebAction):
            if ev.kind == "search":
                s.web_searches += 1
                s.web_cost_usd = s.web_searches * self.web_fee
            elif ev.kind == "open_page":
                s.web_opens += 1
            elif ev.kind == "find_in_page":
                s.web_finds += 1
        elif isinstance(ev, ToolStarted):
            s.tool_calls += 1
            self._started_calls[ev.call_id] = ev
            self._group_sizes[ev.group] += 1
            s.parallel_groups = sum(1 for n in self._group_sizes.values() if n >= 2)
        elif isinstance(ev, ToolCompleted):
            self._record(ev)
        elif isinstance(ev, ApprovalResolved):
            s.approval_wait_s += ev.wait_s

    def _record(self, ev: ToolCompleted) -> None:
        started = self._started_calls.get(ev.call_id)
        args = started.args if started and isinstance(started.args, dict) else {}
        meta = ev.metadata or {}
        if ev.error_code == "rejected":
            what = args.get("command") or (started.target if started else "") or ev.name
            self._rejected.append(f"{ev.name} {_clip(str(what), 60)}")
        elif ev.name == "read_file" and ev.ok and meta.get("path"):
            self._reads[meta["path"]] = None
        elif ev.name in ("edit_files", "write_file") and ev.ok:
            for ch in meta.get("files_changed") or []:
                acc = self._edits.setdefault(ch["path"], [0, 0])
                acc[0] += ch.get("added", 0)
                acc[1] += ch.get("removed", 0)
        elif ev.name == "run_command" and args.get("command") and ev.error_code != "cancelled":
            outcome = f"exit {meta['exit_code']}" if ev.error_code in (None, "nonzero_exit") and "exit_code" in meta \
                else (ev.error_code or "ok")
            self._commands.append(f"`{_clip(args['command'], 80)}` ({outcome})")

    def activity(self) -> str:
        parts = []
        if self._reads:
            parts.append("read " + ", ".join(self._reads))
        if self._edits:
            parts.append("edited " + ", ".join(f"{p} (+{a} −{r})" for p, (a, r) in self._edits.items()))
        if self._commands:
            parts.append("ran " + ", ".join(self._commands))
        if self._rejected:
            parts.append("user rejected " + ", ".join(self._rejected))
        searches = self.stats.web_searches
        if searches:
            parts.append(f"{searches} web search{'es' if searches != 1 else ''}")
        if parts:
            return "; ".join(parts)
        n = self.stats.tool_calls
        return f"{plural(n, 'tool call')}, no files read or changed" if n else "no tool calls"

    def add_sources(self, response: ModelResponse) -> None:
        for src in response.sources:
            if src not in self.sources:
                self.sources.append(src)
        for src in response.sources_all:
            if src not in self.sources_all:
                self.sources_all.append(src)


class Session:
    def __init__(self, config: AgentConfig, on_event: Callable[[Event], None],
                 model: ModelAdapter | None = None, *, registry: ToolRegistry | None = None):
        self.config = config
        self.session_id = f"s_{uuid.uuid4().hex[:12]}"
        self._on_event = on_event
        self._lock = threading.RLock()
        self._seq = 0
        self._generation = 0
        self._turn_no = 0
        self._active: _Turn | None = None
        self._idle = threading.Event()
        self._idle.set()
        self._totals = TurnStats()

        self.registry = registry or build_registry()
        self.workspace = WorkspacePolicy(config.workspace)
        self.files = FileState()
        self.policy = ApprovalPolicy(config.approval)
        self.approvals = ApprovalGateway(policy=self.policy, emit=self._emit, lock=self._lock)
        self.executor = ToolExecutor(self.registry, config, emit=self._emit)
        self.model = model or ModelAdapter(config)
        self.tools = [*web_tools(config), *self.registry.schemas()]     # fixed for the session (cache-stable)
        self.system_prompt = build_system_prompt(config)
        self.cache_key = prompt_cache_key(config.workspace, self.system_prompt, self.tools)
        self.history: list = [{"role": "system", "content": self.system_prompt}]
        self._emit(SessionStarted(config={**config.summary(), "tools": self.registry.names()}))

    # -- commands ------------------------------------------------------------------------------

    def start_turn(self, user_message: str) -> str:
        with self._lock:
            if self._active is not None:
                raise Busy("A turn is already running.")
            self._generation += 1
            self._turn_no += 1
            turn = _Turn(f"t{self._turn_no}", self._generation, user_message, list(self.history),
                         self.config.web_search_fee_usd)
            self._active = turn
            self._idle.clear()
            self._emit(TurnStarted(turn_id=turn.id, user_message=user_message))
        threading.Thread(target=self._worker, args=(turn,), name=f"agent-{turn.id}", daemon=True).start()
        return turn.id

    def respond_approval(self, request_id: str, decision: Decision | str, feedback: str | None = None) -> bool:
        """Answer the pending approval. Returns False if that request is no longer pending."""
        return self.approvals.respond(request_id, decision, feedback)

    def cancel(self) -> None:
        with self._lock:
            turn = self._active
        if turn is None:
            return
        turn.cancel.cancel()               # kills running commands, closes the model stream (outside the lock)
        with self._lock:
            if self._active is not turn:   # finished on its own meanwhile
                return
            self.approvals.cancel_pending(turn.id)
            self.history += [{"role": "user", "content": turn.user_message},
                             {"role": "developer", "content": _clip(
                                 f"Turn cancelled by user after: {turn.activity()}.", TURN_RECORD_MAX_CHARS)}]
            self._generation += 1
            self._emit(TurnCancelled(turn_id=turn.id, stats=self._close_stats(turn)))
            self._end(turn)

    def new_conversation(self) -> None:
        with self._lock:
            if self._active is not None:
                raise Busy("A turn is running; cancel it first.")
            self.history = [{"role": "system", "content": self.system_prompt}]
            self.files = FileState()       # the model no longer remembers what it read
            self._emit(Notice(level="info", code="new_conversation", message="Conversation history cleared."))

    def close(self) -> None:
        self.cancel()
        self.executor.shutdown()

    # -- queries -------------------------------------------------------------------------------

    @property
    def busy(self) -> bool:
        return self._active is not None

    def wait(self, timeout: float | None = None) -> bool:
        return self._idle.wait(timeout)

    def usage_totals(self) -> dict:
        with self._lock:
            return self._totals.to_dict()

    # -- events --------------------------------------------------------------------------------

    def _emit(self, event: Event) -> bool:
        """Stamp and deliver. Events of a turn that is no longer active (a cancelled worker) are dropped."""
        with self._lock:
            turn = self._active
            if event.turn_id is not None and (turn is None or event.turn_id != turn.id):
                return False
            self._seq += 1
            event = replace(event, session_id=self.session_id, seq=self._seq, ts=now_iso())
            if turn is not None and event.turn_id == turn.id:
                turn.observe(event)
            try:
                self._on_event(event)
            except Exception:
                logger.exception("on_event raised for %s", event.type)
            return True

    def _turn_emitter(self, turn: _Turn) -> Callable[[Event], None]:
        def emit(event: Event) -> None:
            self._emit(event if event.turn_id is not None else replace(event, turn_id=turn.id))
        return emit

    # -- turn loop -----------------------------------------------------------------------------

    def _stale(self, turn: _Turn) -> bool:
        return turn.generation != self._generation or turn.cancel.cancelled

    def _worker(self, turn: _Turn) -> None:
        try:
            self._run_turn(turn)
        except Cancelled:
            pass                               # cancel() already committed the turn
        except ModelError as e:
            self._fail(turn, e.code, str(e))
        except Exception as e:
            if not self._stale(turn):
                logger.exception("turn %s crashed", turn.id)
            self._fail(turn, "internal_error", f"{type(e).__name__}: {e}")
        finally:
            self.executor.forget_turn(turn.id)

    def _run_turn(self, turn: _Turn) -> None:
        cfg = self.config
        emit = self._turn_emitter(turn)
        items: list = [{"role": "user", "content": turn.user_message}]
        ctx = ToolContext(config=cfg, workspace=self.workspace, files=self.files, approvals=self.approvals,
                          cancel=turn.cancel, turn_id=turn.id, call_id="", seen_reads={})
        for round_no in range(1, cfg.max_rounds + 1):
            if self._stale(turn):
                return
            if (stop := self._budget_exceeded(turn)):
                return self._finish_with_summary(turn, items, stop, round_no)
            if cfg.max_rounds >= 3 and round_no == cfg.max_rounds - 2:
                emit(Notice(level="warning", code="rounds_low", message="2 rounds left"))
            response = self._model_round(turn, items, round_no, "auto")
            items.extend(response.output)
            calls = response.function_calls
            if not calls:
                return self._commit(turn, items, response, "done")
            started, approval_before = time.monotonic(), turn.stats.approval_wait_s
            results = self.executor.run_batch(
                [ToolCall(c["call_id"], c["name"], c.get("arguments", "")) for c in calls], ctx)
            with self._lock:
                turn.stats.tool_wait_s += max(0.0, time.monotonic() - started
                                              - (turn.stats.approval_wait_s - approval_before))
            for call, result, _ in results:
                items.append({"type": "function_call_output", "call_id": call.call_id, "output": result.output})
        return self._finish_with_summary(turn, items, "max_rounds", cfg.max_rounds + 1)

    def _model_round(self, turn: _Turn, items: list, round_no: int, tool_choice: str) -> ModelResponse:
        emit = self._turn_emitter(turn)
        emit(ModelRoundStarted(round=round_no))
        response = self.model.respond(turn.base_history + items, tools=self.tools, round_no=round_no,
                                      cancel=turn.cancel, emit=emit, tool_choice=tool_choice,
                                      cache_key=self.cache_key)
        if self._stale(turn):
            raise Cancelled()
        u = response.usage
        emit(ModelRoundCompleted(round=round_no, duration_s=response.duration_s, input_tokens=u.input_tokens,
                                 cached_tokens=u.cached_tokens, output_tokens=u.output_tokens,
                                 reasoning_tokens=u.reasoning_tokens, cost_usd=response.cost_usd,
                                 function_calls=len(response.function_calls)))
        with self._lock:
            turn.add_sources(response)
        return response

    def _budget_exceeded(self, turn: _Turn) -> str | None:
        cfg, s = self.config, turn.stats
        if time.monotonic() - turn.started - s.approval_wait_s >= cfg.max_turn_seconds:
            return "max_time"
        if cfg.max_turn_cost_usd is not None and s.model_cost_usd + s.web_cost_usd >= cfg.max_turn_cost_usd:
            return "max_cost"
        return None

    def _finish_with_summary(self, turn: _Turn, items: list, reason: str, round_no: int) -> None:
        items.append({"role": "developer", "content": SUMMARY_INSTRUCTION.format(reason=reason)})
        response = self._model_round(turn, items, round_no, "none")
        # tool_choice="none" should prevent calls; drop any anyway so history never holds an unanswered call.
        response.output = [i for i in response.output if i.get("type") != "function_call"]
        items.extend(response.output)
        self._commit(turn, items, response, reason)

    # -- commit --------------------------------------------------------------------------------

    def _turn_record(self, turn: _Turn) -> str:
        return _clip(f"Turn record: {turn.activity()}.", TURN_RECORD_MAX_CHARS)

    def _commit(self, turn: _Turn, items: list, response: ModelResponse, stop_reason: str) -> None:
        with self._lock:
            if self._stale(turn):
                return
            if self.config.prune_history:
                # Only these three items survive the turn: no reasoning/function_call/output/web items,
                # so there are never orphaned call/output pairs, and the earlier prefix stays cached.
                self.history += [{"role": "user", "content": turn.user_message},
                                 {"role": "assistant", "content": response.text or "(no answer text)"},
                                 {"role": "developer", "content": self._turn_record(turn)}]
            else:
                self.history += items
            self._emit(TurnCompleted(turn_id=turn.id, text=response.text, sources=list(turn.sources),
                                     sources_all=list(turn.sources_all), stats=self._close_stats(turn),
                                     stop_reason=stop_reason))
            self._end(turn)

    def _fail(self, turn: _Turn, code: str, message: str) -> None:
        with self._lock:
            if self._stale(turn):
                return
            # Keep the user's message and what already happened (files may have been edited).
            self.history += [{"role": "user", "content": turn.user_message},
                             {"role": "developer", "content": _clip(
                                 f"Turn failed ({code}) after: {turn.activity()}.", TURN_RECORD_MAX_CHARS)}]
            self._emit(TurnFailed(turn_id=turn.id, error_code=code, message=message,
                                  stats=self._close_stats(turn)))
            self._end(turn)

    def _close_stats(self, turn: _Turn) -> dict:
        turn.stats.elapsed_s = time.monotonic() - turn.started
        self._totals.add(turn.stats)
        return turn.stats.to_dict()

    def _end(self, turn: _Turn) -> None:
        self._active = None
        self._idle.set()

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
- With a store, every recorder call also happens under `_lock` (sessions spec §5.4): an event is written
  before `on_event` sees it, and a turn's history line is written (and fsync'd) before its terminal event.
- `update_config` changes model, reasoning and approval in place, under `_lock` and only between turns (§5.6).
"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import replace
from typing import Callable

from .approvals import ApprovalGateway, ApprovalPolicy, Decision
from .config import AgentConfig
from .events import (ConfigChanged, Event, ModelRoundCompleted, ModelRoundStarted, Notice, SessionResumed,
                     SessionStarted, ToolCompleted, ToolStarted, TurnCancelled, TurnCompleted, TurnFailed, TurnStarted,
                     event_from_dict, now_iso)
from .model import Cancelled, ModelAdapter, ModelError, ModelResponse, web_tools
from .prompt import build_system_prompt, prompt_cache_key
from .sessions import InterruptedTurn, SavedSession, SessionRecorder, SessionStore
from .stats import StatsCounter, TurnStats
from .tools import build_registry
from .tools.executor import ToolCall, ToolExecutor
from .tools.files import plural
from .tools.registry import ToolContext, ToolRegistry
from .workspace import CancelToken, FileState, WorkspacePolicy

logger = logging.getLogger(__name__)

TURN_RECORD_MAX_CHARS = 600
RESUMED_TURNS_SHOWN = 20
CHANGEABLE_SETTINGS = ("model", "reasoning", "approval")    # update_config (§5.6); the rest need a new session
SUMMARY_INSTRUCTION = ("Budget reached ({reason}). Do not call tools. Summarize what was done, what was verified, "
                       "and what remains.")


class Busy(RuntimeError):
    """A turn is running; the command needs an idle session."""


def _clip(text: str, n: int) -> str:
    return text if len(text) <= n else text[: n - 1] + "…"


class _Turn(StatsCounter):
    """Per-turn state. `observe` runs under the session lock for every delivered event of this turn."""

    def __init__(self, turn_id: str, generation: int, user_message: str, base_history: list, web_fee: float):
        super().__init__(web_fee)
        self.id = turn_id
        self.generation = generation
        self.user_message = user_message
        self.base_history = base_history         # history snapshot taken at start_turn
        self.cancel = CancelToken()
        self.started = time.monotonic()
        self.sources: list[dict] = []
        self.sources_all: list[dict] = []
        self._started_calls: dict[str, ToolStarted] = {}
        self._reads: dict[str, None] = {}
        self._edits: dict[str, list[int]] = {}
        self._commands: list[str] = []
        self._rejected: list[str] = []

    def observe(self, ev: Event) -> None:
        super().observe(ev)                      # the stats
        if isinstance(ev, ToolStarted):
            self._started_calls[ev.call_id] = ev
        elif isinstance(ev, ToolCompleted):
            self._record(ev)

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
                 model: ModelAdapter | None = None, *, registry: ToolRegistry | None = None,
                 store: SessionStore | None = None, resume: str | None = None):
        """`store`: save the session there (None: nothing is saved). `resume`: a full session id in `store`
        to continue; SessionNotFound / SessionInUse are raised before anything is emitted."""
        self.config = config
        self._recorder: SessionRecorder | None = None
        self._save_failure_reported = False
        self._hold_save_failure = False          # while the resume events go out (§5.5: session_resumed comes next)
        saved: SavedSession | None = None
        if resume is not None:
            if store is None:
                raise ValueError("resume= needs a store")
            saved, self._recorder = store.open(resume, config)
            self.session_id = resume
        else:
            self.session_id = f"s_{uuid.uuid4().hex[:12]}"
            if store is not None:
                self._recorder = store.create(self.session_id, config)
        try:
            self._setup(config, on_event, model, registry)
            resumed = self._restore(saved) if saved is not None else None
        except BaseException:
            if self._recorder is not None:
                self._recorder.close()
            raise
        opening: list[Event] = [SessionStarted(config={**config.summary(), "tools": self.registry.names()})]
        if resumed is not None:
            opening.append(resumed)
            if resumed.interrupted_turn:
                opening.append(Notice(level="warning", code="turn_interrupted", message=(
                    f"Turn {resumed.interrupted_turn} was interrupted when the agent stopped. "
                    "Its partial work is noted in the history.")))
        for n, event in enumerate(opening, 1):
            self._hold_save_failure = n < len(opening)   # a failure at open or recovery is reported after these
            self._emit(event)

    def _setup(self, config: AgentConfig, on_event: Callable[[Event], None], model: ModelAdapter | None,
               registry: ToolRegistry | None) -> None:
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
        # history[1:] in its pruned form, kept in step at every commit: what a model change falls back to (§5.6)
        self._pruned_history: list = []

    # -- resume (sessions spec §5.2, §5.3) ------------------------------------------------------

    def _restore(self, saved: SavedSession) -> SessionResumed:
        """Load the saved turns into history and the counters, and recover an interrupted turn.

        The system prompt, cache key, FileState and approval allowances stay fresh (built by `_setup`).
        """
        cfg = self.config
        self._seq = saved.last_seq
        self._turn_no = saved.turn_no
        self._totals = TurnStats.from_dict(saved.totals)
        full = False
        turns = []
        for line in saved.turn_lines:
            items, record = line.get("items"), line.get("record")
            if not isinstance(items, list):
                continue
            # A full turn (record kept) goes back only to the model that made it, in a session that keeps full
            # turns; otherwise its pruned record does, which is valid for any model.
            if record is not None:
                if not cfg.prune_history and (line.get("model") or saved.info.model) == cfg.model:
                    full = True
                else:
                    items = record
            self.history += items
            self._pruned_history += items if record is None else record
            turns.append({k: line.get(k) for k in ("turn_id", "user_message", "outcome", "text", "ts")})
        interrupted = saved.interrupted
        if interrupted is not None:
            turns.append(self._recover_interrupted(interrupted))
        return SessionResumed(
            title=saved.info.title, created=saved.info.created,
            turns_total=saved.all_turn_lines + (interrupted is not None), turns=turns[-RESUMED_TURNS_SHOWN:],
            totals=self._totals.to_dict(), history="full" if full else "pruned",
            restored_items=len(self.history) - 1, interrupted_turn=interrupted.turn_id if interrupted else None,
            saved_config=dict(saved.saved_config))

    def _recover_interrupted(self, interrupted: InterruptedTurn) -> dict:
        """§5.3: replay the dead turn's logged events for its activity and billed costs, then commit it."""
        turn = _Turn(interrupted.turn_id, 0, interrupted.user_message, [], self.config.web_search_fee_usd)
        for d in interrupted.events:
            try:
                turn.observe(event_from_dict(d))
            except (TypeError, ValueError):
                continue                       # a line from another version; the rest still counts
        items = [{"role": "user", "content": turn.user_message},
                 {"role": "developer", "content": _clip(
                     f"Turn interrupted (the agent process stopped) after: {turn.activity()}. "
                     "Files may have changed since; re-read before editing.", TURN_RECORD_MAX_CHARS)}]
        self.history += items
        self._pruned_history += items
        self._totals.add(turn.stats)
        if self._recorder is not None:
            with self._lock:
                self._recorder.on_commit(turn_id=turn.id, outcome="interrupted", user_message=turn.user_message,
                                         text="", items=items, record=None, stats=turn.stats.to_dict())
        return {"turn_id": turn.id, "user_message": turn.user_message, "outcome": "interrupted", "text": "",
                "ts": now_iso()}

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
            items = [{"role": "user", "content": turn.user_message},
                     {"role": "developer", "content": _clip(
                         f"Turn cancelled by user after: {turn.activity()}.", TURN_RECORD_MAX_CHARS)}]
            self.history += items
            self._pruned_history += items
            self._generation += 1
            self._save_commit(turn, "cancelled", "", items, None)
            self._emit(TurnCancelled(turn_id=turn.id, stats=self._close_stats(turn)))
            self._end(turn)

    def new_conversation(self) -> None:
        with self._lock:
            if self._active is not None:
                raise Busy("A turn is running; cancel it first.")
            self.history = [{"role": "system", "content": self.system_prompt}]
            self._pruned_history = []
            self.files = FileState()       # the model no longer remembers what it read
            if self._recorder is not None:
                self._recorder.on_reset()
            self._emit(Notice(level="info", code="new_conversation", message="Conversation history cleared."))

    def update_config(self, *, model: str | None = None, reasoning: str | None = None,
                      approval: str | None = None) -> dict:
        """Change settings between turns, in place: same id, history, log and lock (sessions spec §5.6).

        Returns `{field: [old, new]}` for each field that changed. Emits `config_changed` even when nothing did.
        Raises Busy while a turn runs, ValueError for an invalid value (model names are not checked against a list).
        """
        with self._lock:
            if self._active is not None:
                raise Busy("A turn is running; settings can change between turns.")
            asked = {k: v for k, v in (("model", model), ("reasoning", reasoning), ("approval", approval))
                     if v is not None}
            if "model" in asked and (not isinstance(model, str) or not model.strip()):
                raise ValueError(f"model must be a non-empty string; got {model!r}")
            old = self.config
            new = replace(old, **asked)          # AgentConfig.__post_init__ rejects an unknown level or mode
            changes = {k: [getattr(old, k), getattr(new, k)] for k in CHANGEABLE_SETTINGS
                       if getattr(old, k) != getattr(new, k)}
            history = "unchanged"
            if changes:
                self.config = new
                self.model.set_config(new)
                if "approval" in changes:
                    # A new mode is a new trust decision: "allow for session" approvals start over. The prompt names
                    # the mode, so it and the cache key are rebuilt.
                    self.policy = self.approvals.policy = ApprovalPolicy(new.approval)
                    self.system_prompt = build_system_prompt(new)
                    self.cache_key = prompt_cache_key(new.workspace, self.system_prompt, self.tools)
                    self.history[0] = {"role": "system", "content": self.system_prompt}
                if "model" in changes and not new.prune_history and self.history[1:] != self._pruned_history:
                    # Full turns hold reasoning items encrypted for the old model: keep only their records (§5.2).
                    self.history = [self.history[0], *self._pruned_history]
                    history = "pruned"
            self._emit(ConfigChanged(changes={k: {"from": a, "to": b} for k, (a, b) in changes.items()},
                                     config={**self.config.summary(), "tools": self.registry.names()},
                                     history=history))
            return changes

    def close(self) -> None:
        self.cancel()
        self.executor.shutdown()
        with self._lock:
            if self._recorder is not None:
                self._recorder.close()     # after the last event (a cancelled worker's later events are dropped)

    # -- queries -------------------------------------------------------------------------------

    @property
    def busy(self) -> bool:
        return self._active is not None

    @property
    def saved(self) -> bool:
        """True while the session is being saved (a store was given and no write has failed)."""
        return self._recorder is not None and self._recorder.healthy

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
            if self._recorder is not None:
                self._recorder.on_event(event)     # on disk before the frontend sees it
            try:
                self._on_event(event)
            except Exception:
                logger.exception("on_event raised for %s", event.type)
            self._report_save_failure()
            return True

    def _report_save_failure(self) -> None:
        """Emit one `session_save_failed` notice the first time the recorder disables itself (§5.4).

        Called only by `_emit`, after it delivered an event, so the notice follows the event whose write failed.
        """
        r = self._recorder
        if r is not None and r.error is not None and not self._save_failure_reported and not self._hold_save_failure:
            self._save_failure_reported = True
            self._emit(Notice(level="warning", code="session_save_failed",
                              message=f"Saving stopped: {r.error}. The session continues unsaved."))

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
            # With pruning, only these three items survive the turn: no reasoning/function_call/output/web
            # items, so there are never orphaned call/output pairs, and the earlier prefix stays cached.
            record = [{"role": "user", "content": turn.user_message},
                      {"role": "assistant", "content": response.text or "(no answer text)"},
                      {"role": "developer", "content": self._turn_record(turn)}]
            new_items = record if self.config.prune_history else items
            self.history += new_items
            self._pruned_history += record
            self._save_commit(turn, "completed", response.text or "", new_items, record)
            self._emit(TurnCompleted(turn_id=turn.id, text=response.text, sources=list(turn.sources),
                                     sources_all=list(turn.sources_all), stats=self._close_stats(turn),
                                     stop_reason=stop_reason))
            self._end(turn)

    def _fail(self, turn: _Turn, code: str, message: str) -> None:
        with self._lock:
            if self._stale(turn):
                return
            # Keep the user's message and what already happened (files may have been edited).
            items = [{"role": "user", "content": turn.user_message},
                     {"role": "developer", "content": _clip(
                         f"Turn failed ({code}) after: {turn.activity()}.", TURN_RECORD_MAX_CHARS)}]
            self.history += items
            self._pruned_history += items
            self._save_commit(turn, "failed", "", items, None)
            self._emit(TurnFailed(turn_id=turn.id, error_code=code, message=message,
                                  stats=self._close_stats(turn)))
            self._end(turn)

    def _save_commit(self, turn: _Turn, outcome: str, text: str, items: list, record: list | None) -> None:
        """Write the turn's history line before its terminal event is emitted (§4.2 commit order)."""
        if self._recorder is not None:
            self._recorder.on_commit(turn_id=turn.id, outcome=outcome, user_message=turn.user_message, text=text,
                                     items=items, record=record)

    def _close_stats(self, turn: _Turn) -> dict:
        turn.stats.elapsed_s = time.monotonic() - turn.started
        self._totals.add(turn.stats)
        return turn.stats.to_dict()

    def _end(self, turn: _Turn) -> None:
        self._active = None
        self._idle.set()

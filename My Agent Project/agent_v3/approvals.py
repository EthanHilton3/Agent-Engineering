"""Approval policy and gateway (plan §8.6).

Tools build an ApprovalRequest and call `ApprovalGateway.request`. The policy either auto-allows
it (no events) or the gateway asks: it emits `approval_requested`, blocks the tool's thread until
`respond()` or `cancel_pending()`, and emits `approval_resolved`.

At most one approval is pending at a time: approvals only happen in non-read-only tool calls,
which the executor never runs concurrently, and a cancelled turn's token stops its worker from
opening a new request.
"""
from __future__ import annotations

import itertools
import re
import threading
import time
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any, Callable, Literal

from .config import APPROVAL_MODES
from .events import ApprovalRequested, ApprovalResolved, Event


class Decision(StrEnum):
    ALLOW = "allow"
    ALLOW_SESSION = "allow_session"
    REJECT = "reject"


@dataclass
class ApprovalRequest:
    kind: Literal["command", "edit"]
    title: str                     # "Run command" / "Edit 2 files" / "Create file"
    reason: str = ""               # why asking; set by the gateway from the policy
    request_id: str = ""           # assigned by the gateway when empty
    command: str | None = None
    cwd: str | None = None
    timeout: int | None = None
    paths: list[str] = field(default_factory=list)
    diff: str | None = None        # full unified diff; frontends decide how much to show
    outside_workspace: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)   # e.g. full_content for a "view all" UI

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ApprovalResult:
    decision: Decision
    feedback: str | None = None
    by: str = "policy"             # user | policy | cancel
    wait_s: float = 0.0

    @property
    def allowed(self) -> bool:
        return self.decision in (Decision.ALLOW, Decision.ALLOW_SESSION)


# A speed bump against mistakes, NOT a security boundary: trivially bypassed (aliases, scripts,
# `python -c`, variables). Never present it to users as protection.
ALWAYS_ASK_PATTERNS = [re.compile(p) for p in (
    r"\bgit\s+push\b",
    r"\bgit\s+(reset\s+--hard|clean\s+-[a-z]*f)",
    r"\brm\s+-[a-z]*r",
    r"\b(pip|pip3|uv|npm|pnpm|yarn|conda)\s+(install|uninstall|remove|add)\b",
    r"\bcurl\b.*\|\s*(ba)?sh",
)]


def always_ask_match(command: str) -> str | None:
    for pattern in ALWAYS_ASK_PATTERNS:
        if (m := pattern.search(command)):
            return m.group(0)
    return None


class ApprovalPolicy:
    """Decides whether a request needs the user. Session allowances never persist across sessions."""

    def __init__(self, mode: str = "ask"):
        if mode not in APPROVAL_MODES:
            raise ValueError(f"approval mode must be one of {', '.join(APPROVAL_MODES)}; got {mode!r}")
        self.mode = mode
        self.session_edits = False                # ALLOW_SESSION on an edit: workspace edits become auto
        self.session_commands: set[str] = set()   # ALLOW_SESSION on a command: that exact string becomes auto
        self._lock = threading.Lock()

    def check(self, req: ApprovalRequest) -> tuple[bool, str]:
        """(needs_user, reason). Outside-workspace and always-ask patterns win over every allowance."""
        with self._lock:
            if req.kind == "edit":
                if req.outside_workspace:
                    return True, "write outside workspace"
                if self.mode != "ask":
                    return False, f"edits are automatic in '{self.mode}' mode"
                if self.session_edits:
                    return False, "edits allowed for this session"
                return True, "edits need approval in 'ask' mode"
            command = req.command or ""
            if req.outside_workspace:
                return True, "cwd outside workspace"
            if (hit := always_ask_match(command)):
                return True, f"command matches an always-ask pattern ({hit.strip()})"
            if self.mode == "full-auto":
                return False, "commands are automatic in 'full-auto' mode"
            if command in self.session_commands:
                return False, "command allowed for this session"
            return True, f"commands need approval in '{self.mode}' mode"

    def allow_session(self, req: ApprovalRequest) -> None:
        with self._lock:
            if req.kind == "edit":
                self.session_edits = True
            elif req.command is not None:
                self.session_commands.add(req.command)


def reject_all(_: ApprovalRequest) -> ApprovalResult:
    return ApprovalResult(Decision.REJECT, by="policy")


class _Pending:
    def __init__(self, req: ApprovalRequest, turn_id: str | None):
        self.req = req
        self.turn_id = turn_id
        self.started = time.monotonic()
        self.done = threading.Event()
        self.result: ApprovalResult | None = None


class ApprovalGateway:
    """Applies the policy, then asks the user through events (or an injected `decide`).

    - `ApprovalGateway()` rejects everything that reaches it (fail closed; Phase 1 default).
    - `ApprovalGateway(decide)` calls `decide(req)` synchronously (tests, scripted frontends).
    - `ApprovalGateway(policy=..., emit=..., lock=...)` is the session flow: emit + wait.

    `lock` should be the session's event lock, so `approval_requested`/`approval_resolved`
    are ordered with every other event and the pending slot changes atomically with them.
    """

    def __init__(self, decide: Callable[[ApprovalRequest], ApprovalResult] | None = None, *,
                 policy: ApprovalPolicy | None = None, emit: Callable[[Event], None] | None = None,
                 lock: threading.RLock | None = None, poll_s: float = 0.1):
        self._decide = decide if decide is not None else (None if emit is not None else reject_all)
        self.policy = policy
        self._emit = emit
        self._lock = lock or threading.RLock()
        self._ids = itertools.count(1)
        self._pending: _Pending | None = None
        self._poll_s = poll_s

    @property
    def pending(self) -> ApprovalRequest | None:
        with self._lock:
            return self._pending.req if self._pending else None

    def request(self, req: ApprovalRequest, *, turn_id: str | None = None, cancel=None) -> ApprovalResult:
        with self._lock:
            if not req.request_id:
                req.request_id = f"ap_{next(self._ids)}"
        # Without a policy everything reaches `decide`; a fresh 'ask' policy (which always needs the
        # user) still supplies the reason text.
        needs_user, req.reason = (self.policy or ApprovalPolicy()).check(req)
        if not needs_user:
            return ApprovalResult(Decision.ALLOW, by="policy")
        if self._decide is not None:
            result = self._decide(req)
        else:
            result = self._ask(req, turn_id, cancel)
        if result.decision == Decision.ALLOW_SESSION and self.policy is not None:
            self.policy.allow_session(req)
        return result

    # -- event-based asking --------------------------------------------------------------------

    def _ask(self, req: ApprovalRequest, turn_id: str | None, cancel) -> ApprovalResult:
        with self._lock:
            if cancel is not None and cancel.cancelled:
                return ApprovalResult(Decision.REJECT, by="cancel")
            if self._pending is not None:
                raise RuntimeError(f"approval {self._pending.req.request_id} is still pending")
            slot = self._pending = _Pending(req, turn_id)
            self._emit(ApprovalRequested(turn_id=turn_id, request=req.to_dict()))
        # Cancel normally resolves us via cancel_pending(); polling the token is the backstop.
        while not slot.done.wait(self._poll_s):
            if cancel is not None and cancel.cancelled:
                with self._lock:
                    self._resolve(slot, ApprovalResult(Decision.REJECT, by="cancel"))
        return slot.result  # type: ignore[return-value]

    def _resolve(self, slot: _Pending, result: ApprovalResult) -> bool:
        """Caller holds the lock. Emits approval_resolved exactly once per request."""
        if slot.done.is_set():
            return False
        result.wait_s = round(time.monotonic() - slot.started, 3)
        slot.result = result
        if self._pending is slot:
            self._pending = None
        self._emit(ApprovalResolved(turn_id=slot.turn_id, request_id=slot.req.request_id,
                                    decision=result.decision.value, feedback=result.feedback,
                                    by=result.by, wait_s=result.wait_s))
        slot.done.set()
        return True

    def respond(self, request_id: str, decision: Decision | str, feedback: str | None = None) -> bool:
        """Answer the pending request. False if `request_id` is not pending (stale or already resolved)."""
        decision = Decision(decision)
        with self._lock:
            slot = self._pending
            if slot is None or slot.req.request_id != request_id:
                return False
            return self._resolve(slot, ApprovalResult(decision, feedback or None, by="user"))

    def cancel_pending(self, turn_id: str | None = None) -> bool:
        """Reject the pending request (by="cancel"); only that turn's when `turn_id` is given."""
        with self._lock:
            slot = self._pending
            if slot is None or (turn_id is not None and slot.turn_id != turn_id):
                return False
            return self._resolve(slot, ApprovalResult(Decision.REJECT, by="cancel"))

"""Approval gateway — Phase 1 STUB.

Tools build an ApprovalRequest and ask the gateway. The stub has no mode policy, no events and
no blocking; it delegates to an injectable `decide` callable and rejects everything by default
(fail closed). Phase 2 replaces this with the full ApprovalPolicy / event / wait flow (plan §8.6).
"""
from __future__ import annotations

import itertools
import threading
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any, Callable, Literal


class Decision(StrEnum):
    ALLOW = "allow"
    ALLOW_SESSION = "allow_session"
    REJECT = "reject"


@dataclass
class ApprovalRequest:
    kind: Literal["command", "edit"]
    title: str                     # "Run command" / "Edit 2 files" / "Create file"
    reason: str                    # why asking
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

    @property
    def allowed(self) -> bool:
        return self.decision in (Decision.ALLOW, Decision.ALLOW_SESSION)


def reject_all(_: ApprovalRequest) -> ApprovalResult:
    return ApprovalResult(Decision.REJECT, by="policy")


class ApprovalGateway:
    def __init__(self, decide: Callable[[ApprovalRequest], ApprovalResult] = reject_all):
        self._decide = decide
        self._ids = itertools.count(1)
        self._lock = threading.Lock()

    def request(self, req: ApprovalRequest) -> ApprovalResult:
        if not req.request_id:
            with self._lock:
                req.request_id = f"ap_{next(self._ids)}"
        return self._decide(req)

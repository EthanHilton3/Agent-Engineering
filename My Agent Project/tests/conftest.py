import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent_v3.approvals import ApprovalGateway, ApprovalRequest, ApprovalResult, Decision  # noqa: E402
from agent_v3.config import AgentConfig  # noqa: E402
from agent_v3.tools import build_registry  # noqa: E402
from agent_v3.tools.registry import ToolContext, ToolResult  # noqa: E402
from agent_v3.workspace import CancelToken, FileState, WorkspacePolicy  # noqa: E402


class Env:
    """A temp workspace plus everything needed to call tools the way the executor does."""

    def __init__(self, root: Path, **cfg):
        self.root = root.resolve()
        self.config = AgentConfig(workspace=self.root, **cfg)
        self.registry = build_registry()
        self.files = FileState()
        self.cancel = CancelToken()
        self.requests: list[ApprovalRequest] = []
        self.decision = ApprovalResult(Decision.ALLOW)
        self.approvals = ApprovalGateway(self._decide)
        self.seen_reads: dict = {}
        self.turn_id = "t1"
        self._calls = 0

    def _decide(self, req: ApprovalRequest) -> ApprovalResult:
        self.requests.append(req)
        return self.decision

    def reject(self, feedback=None):
        self.decision = ApprovalResult(Decision.REJECT, feedback)

    def ctx(self) -> ToolContext:
        self._calls += 1
        return ToolContext(config=self.config, workspace=WorkspacePolicy(self.root), files=self.files,
                           approvals=self.approvals, cancel=self.cancel, turn_id=self.turn_id,
                           call_id=f"c{self._calls}", seen_reads=self.seen_reads)

    def call(self, name: str, **args) -> ToolResult:
        spec = self.registry.get(name)
        return spec.func(spec.args_model.model_validate(args), self.ctx())

    def write(self, rel: str, content, newline=None) -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
        return p

    def read(self, rel: str) -> bytes:
        return (self.root / rel).read_bytes()


@pytest.fixture
def env(tmp_path):
    root = tmp_path / "ws"
    root.mkdir()
    return Env(root)


@pytest.fixture
def make_env(tmp_path):
    def make(**cfg):
        root = tmp_path / "ws"
        root.mkdir(exist_ok=True)
        return Env(root, **cfg)
    return make


def to_json(**kw) -> str:
    return json.dumps(kw)


# =============================================================================================
# Phase 2: FakeModelAdapter, event recorder, session fixture
# =============================================================================================

import itertools  # noqa: E402
import threading  # noqa: E402

_ids = itertools.count(1)


def fn_call(name: str, call_id: str | None = None, **args) -> dict:
    return fn_call_raw(name, json.dumps(args), call_id)


def fn_call_raw(name: str, arguments: str, call_id: str | None = None) -> dict:
    n = next(_ids)
    return {"type": "function_call", "id": f"fc_{n}", "call_id": call_id or f"call_{n}", "name": name,
            "arguments": arguments, "status": "completed"}


def msg(text: str, citations: list[tuple[str, str]] = ()) -> dict:
    anns = [{"type": "url_citation", "title": t, "url": u, "start_index": 0, "end_index": 1} for t, u in citations]
    return {"type": "message", "id": f"msg_{next(_ids)}", "role": "assistant", "status": "completed",
            "content": [{"type": "output_text", "text": text, "annotations": anns}]}


def web_call(query: str = "q", sources: list[str] = (), kind: str = "search") -> dict:
    action = {"type": kind, "query": query, "queries": [query], "sources": [{"type": "url", "url": u} for u in sources]}
    if kind == "open_page":
        action = {"type": "open_page", "url": query}
    return {"type": "web_search_call", "id": f"ws_{next(_ids)}", "status": "completed", "action": action}


def reasoning_item() -> dict:
    return {"type": "reasoning", "id": f"rs_{next(_ids)}", "summary": [], "encrypted_content": "gAAAA-opaque"}


from fakes import FakeModelAdapter, FakeStream, Round, usage  # noqa: E402,F401


class EventLog:
    """on_event sink that tests can wait on (stands in for a frontend's queue)."""

    def __init__(self):
        self.events: list = []
        self.cond = threading.Condition()

    def __call__(self, ev):
        with self.cond:
            self.events.append(ev)
            self.cond.notify_all()

    def of(self, type_: str) -> list:
        with self.cond:
            return [e for e in self.events if e.type == type_]

    def types(self) -> list[str]:
        with self.cond:
            return [e.type for e in self.events]

    def wait_for(self, type_: str, n: int = 1, timeout: float = 5.0):
        with self.cond:
            ok = self.cond.wait_for(lambda: sum(e.type == type_ for e in self.events) >= n, timeout)
        assert ok, f"timed out waiting for {n}x {type_}; got {self.types()}"
        return self.of(type_)[n - 1]


@pytest.fixture
def make_session(tmp_path):
    """make_session(rounds, **config) -> (session, fake, log). Default: approval ask, web search off."""
    from agent_v3.session import Session
    made = []

    def make(rounds, **cfg):
        root = tmp_path / "ws"
        root.mkdir(exist_ok=True)
        cfg.setdefault("web_search", False)
        config = AgentConfig(workspace=root, **cfg)
        fake = FakeModelAdapter(config, rounds)
        log = EventLog()
        session = Session(config, log, model=fake)
        made.append(session)
        return session, fake, log

    yield make
    for s in made:
        s.close()

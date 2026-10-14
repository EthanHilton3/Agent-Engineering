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
                           call_id=f"c{self._calls}", seen_reads=self.seen_reads, call_index=self._calls)

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

import copy  # noqa: E402
import itertools  # noqa: E402
import threading  # noqa: E402
from dataclasses import dataclass, field  # noqa: E402

import httpx  # noqa: E402

from agent_v3.model import ModelAdapter  # noqa: E402

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


def usage(inp: int = 100, cached: int = 0, out: int = 10, reasoning: int = 0) -> dict:
    return {"input_tokens": inp, "input_tokens_details": {"cached_tokens": cached},
            "output_tokens": out, "output_tokens_details": {"reasoning_tokens": reasoning},
            "total_tokens": inp + out}


@dataclass
class Round:
    """One scripted model round.

    fail_times: the stream breaks (httpx.RemoteProtocolError) after `fail_after` events this many
    times before the round succeeds. block: "cancel" waits until the adapter closes the stream
    (as a cancel does) and then raises like a closed socket; "release" ignores close() and waits
    for `release` (a network read that does not return promptly). error: raised when the stream is
    opened, `error_times` times.
    """
    output: list = field(default_factory=list)
    usage: dict = field(default_factory=usage)
    fail_times: int = 0
    fail_after: int = 1
    block: str | None = None
    release: threading.Event | None = None
    error: Exception | None = None
    error_times: int = 1
    status: str = "completed"
    incomplete_reason: str | None = None
    stream_error: dict | None = None


class FakeStream:
    def __init__(self, events: list, round_: Round, broken: bool):
        self.events, self.round, self.broken = events, round_, broken
        self.i = 0
        self.closed = threading.Event()
        self.blocked = threading.Event()        # set while blocked, so tests can sync with it

    def __iter__(self):
        return self

    def __next__(self):
        r = self.round
        if self.broken and self.i >= r.fail_after:
            raise httpx.RemoteProtocolError("peer closed connection without sending complete message body")
        if not self.broken and r.block and self.i == 1:
            self.blocked.set()
            if r.block == "cancel":
                self.closed.wait(10)
                raise httpx.ReadError("stream closed")
            r.release.wait(10)
        if self.closed.is_set() and r.block != "release":
            raise httpx.ReadError("stream closed")
        if self.i >= len(self.events):
            raise StopIteration
        self.i += 1
        return self.events[self.i - 1]

    def close(self):
        self.closed.set()


class FakeModelAdapter(ModelAdapter):
    """The real adapter with the network replaced by scripted rounds, so stream handling, retries,
    param fallback and cost math are all exercised. Records every request's params."""

    def __init__(self, config, rounds: list, **kw):
        super().__init__(config, client=object(), retry_delays=kw.pop("retry_delays", (0.0, 0.0)),
                         jitter=kw.pop("jitter", 0.0), **kw)
        self.rounds = [r if isinstance(r, Round) else Round(output=list(r)) for r in rounds]
        self.index = 0
        self.requests: list[dict] = []
        self.streams: list[FakeStream] = []

    def _open_stream(self, params):
        self.requests.append({**params, "input": copy.deepcopy(params["input"])})
        if self.index >= len(self.rounds):
            raise AssertionError("FakeModelAdapter ran out of scripted rounds")
        r = self.rounds[self.index]
        if r.error is not None and r.error_times > 0:
            r.error_times -= 1
            raise r.error
        broken = r.fail_times > 0
        if broken:
            r.fail_times -= 1
        else:
            self.index += 1
        stream = FakeStream(self._events(r), r, broken)
        self.streams.append(stream)
        return stream

    @staticmethod
    def _events(r: Round) -> list[dict]:
        events: list[dict] = [{"type": "response.created"}]
        for item in r.output:
            if item.get("type") == "message":
                for part in item["content"]:
                    words = part.get("text", "").split(" ")
                    for k, w in enumerate(words):
                        events.append({"type": "response.output_text.delta", "delta": w if k == 0 else " " + w})
            events.append({"type": "response.output_item.done", "item": copy.deepcopy(item)})
        if r.stream_error:
            events.append(r.stream_error)
        final = {"status": r.status, "output": copy.deepcopy(r.output), "usage": r.usage}
        if r.status == "incomplete":
            final["incomplete_details"] = {"reason": r.incomplete_reason or "max_output_tokens"}
        events.append({"type": "response.incomplete" if r.status == "incomplete" else "response.completed",
                       "response": final})
        return events


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

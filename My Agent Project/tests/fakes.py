"""Scripted stand-in for the model (no pytest import, so the stdio server's --fake-model-script can load it).

A script is a list of rounds. Each round is a list of Responses-API output items (see `fn_call`/`msg` in
conftest.py), or a `Round` (a dict of its fields in JSON). `usage` is the round's token usage.
"""
import copy
import threading
from dataclasses import dataclass, field

import httpx

from agent_v3.model import ModelAdapter


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


SCRIPT_ROUND_FIELDS = ("output", "usage", "fail_times", "fail_after", "block", "status", "incomplete_reason",
                       "stream_error")


def rounds_from_json(data) -> list:
    """The JSON form of a script (the stdio server's --fake-model-script): a list whose items are either a list of
    output items or an object with `Round` fields. `block` may only be "cancel" (the other modes need Python objects)."""
    if not isinstance(data, list):
        raise ValueError("a model script is a JSON list of rounds")
    rounds = []
    for i, item in enumerate(data):
        if isinstance(item, list):
            rounds.append(Round(output=item))
        elif isinstance(item, dict):
            unknown = set(item) - set(SCRIPT_ROUND_FIELDS)
            if unknown or item.get("block") not in (None, "cancel"):
                raise ValueError(f"round {i}: unsupported field(s) {sorted(unknown) or ['block']}")
            rounds.append(Round(**item))
        else:
            raise ValueError(f"round {i}: expected a list of output items or an object")
    return rounds

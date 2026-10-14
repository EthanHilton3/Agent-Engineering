"""The JSON-lines server, tested the way an app would use it: as a subprocess speaking over pipes.

The model is `--fake-model-script` (a JSON dump of the same rounds `FakeModelAdapter` takes in-process), so no
network is used. Every stdout line any test receives must be valid JSON (checked when the client is torn down).
"""
import io
import json
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest
from conftest import fn_call, msg

from agent_v3.config import AgentConfig
from agent_v3.frontends.stdio_server import StdioServer

ROOT = Path(__file__).resolve().parent.parent
TIMEOUT = 20.0

EDIT_THEN_ANSWER = [[fn_call("write_file", path="hello.txt", content="hi\n")], [msg("Created hello.txt.")]]
BLOCKED_ROUND = {"output": [msg("never delivered")], "block": "cancel"}      # waits until the turn is cancelled


class Client:
    """Spawns the server and records every line it writes to stdout."""

    def __init__(self, tmp_path: Path, script, *flags: str):
        self.workspace = tmp_path / "ws"
        self.workspace.mkdir(exist_ok=True)
        self.stderr_path = tmp_path / "server.stderr"
        script_path = tmp_path / "script.json"
        script_path.write_text(json.dumps(script), encoding="utf-8")
        self.received: list[dict] = []
        self.bad_lines: list[bytes] = []
        self._cond = threading.Condition()
        self._pos = 0
        self._stderr = self.stderr_path.open("wb")
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "agent_v3.frontends.stdio_server", "--workspace", str(self.workspace), "--no-web",
             "--fake-model-script", str(script_path), *flags],
            cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self._stderr)
        self._reader = threading.Thread(target=self._read, daemon=True)
        self._reader.start()

    def _read(self) -> None:
        for raw in self.proc.stdout:
            try:
                message = json.loads(raw)
            except ValueError:
                message = None
            with self._cond:
                if isinstance(message, dict) and raw.endswith(b"\n"):
                    self.received.append(message)
                else:
                    self.bad_lines.append(raw)
                self._cond.notify_all()

    # -- sending -------------------------------------------------------------------------------

    def send(self, **message) -> None:
        self.send_raw(json.dumps(message).encode() + b"\n")

    def send_raw(self, raw: bytes) -> None:
        self.proc.stdin.write(raw)
        self.proc.stdin.flush()

    # -- receiving -----------------------------------------------------------------------------

    def expect(self, type_: str, **fields) -> dict:
        """The next message (after the previous `expect`) with this type and these field values."""
        def match(m):
            return m.get("type") == type_ and all(m.get(k) == v for k, v in fields.items())
        with self._cond:
            def found():
                return any(match(m) for m in self.received[self._pos:])
            ok = self._cond.wait_for(found, TIMEOUT)
            assert ok, f"timed out waiting for {type_} {fields}; got {self.types()}"
            for i in range(self._pos, len(self.received)):
                if match(self.received[i]):
                    self._pos = i + 1
                    return self.received[i]

    def types(self) -> list[str]:
        return [m.get("type") for m in self.received]

    def barrier(self) -> list[dict]:
        """Everything the server has written so far: it answers get_usage only after handling earlier input."""
        self.send(type="get_usage")
        self.expect("usage")
        return list(self.received)

    def wait_exit(self) -> int:
        code = self.proc.wait(TIMEOUT)
        self._reader.join(TIMEOUT)
        return code

    def stderr(self) -> str:
        self._stderr.flush()
        return self.stderr_path.read_text(encoding="utf-8", errors="replace")

    def close(self) -> None:
        if self.proc.poll() is None:
            self.proc.kill()
        self.proc.wait(TIMEOUT)
        self._reader.join(TIMEOUT)
        self.proc.stdin.close()
        self.proc.stdout.close()
        self._stderr.close()


@pytest.fixture
def start(tmp_path):
    clients: list[Client] = []

    def make(script, *flags: str) -> Client:
        client = Client(tmp_path, script, *flags)
        clients.append(client)
        client.expect("session_started")
        return client

    yield make
    for c in clients:
        c.close()
    for c in clients:
        assert c.bad_lines == [], f"stdout carried non-protocol lines: {c.bad_lines}"


def tool_completed(client: Client) -> dict:
    return client.expect("tool_completed")


# -- the happy path ------------------------------------------------------------------------------


def test_session_started_is_first_line_and_announces_protocol(start):
    c = start([[msg("hi")]])
    first = c.received[0]
    assert first["type"] == "session_started" and first["protocol_version"] == 1
    assert first["seq"] == 1 and first["turn_id"] is None
    assert first["config"]["approval"] == "ask" and "write_file" in first["config"]["tools"]


def test_approval_round_trip_ends_in_turn_completed(start):
    c = start(EDIT_THEN_ANSWER)
    c.send(type="user_message", text="make hello.txt")
    request = c.expect("approval_requested")["request"]
    assert request["kind"] == "edit" and request["request_id"] == "ap_1"
    assert not (c.workspace / "hello.txt").exists()          # nothing is written before the answer
    c.send(type="approval_response", request_id="ap_1", decision="allow")
    done = c.expect("turn_completed")
    assert done["text"] == "Created hello.txt." and done["stop_reason"] == "done"
    assert (c.workspace / "hello.txt").read_text() == "hi\n"

    events = c.barrier()[:-1]                                  # drop the usage reply
    assert events[-1]["type"] == "turn_completed"
    types = [e["type"] for e in events]
    expected = ["session_started", "turn_started", "model_round_started", "model_round_completed", "tool_started", "approval_requested", "approval_resolved", "tool_completed", "model_round_started"]
    it = iter(types)
    assert all(t in it for t in expected), types               # an ordered subsequence
    seqs = [e["seq"] for e in events]
    assert seqs == sorted(seqs) and len(set(seqs)) == len(seqs)
    resolved = next(e for e in events if e["type"] == "approval_resolved")
    assert resolved["request_id"] == "ap_1" and resolved["decision"] == "allow" and resolved["by"] == "user"
    assert len({e["session_id"] for e in events}) == 1


def test_reject_with_feedback_reaches_the_model_and_writes_nothing(start):
    c = start(EDIT_THEN_ANSWER)
    c.send(type="user_message", text="make hello.txt")
    c.expect("approval_requested")
    c.send(type="approval_response", request_id="ap_1", decision="reject", feedback="not now")
    resolved = c.expect("approval_resolved")
    assert resolved["decision"] == "reject" and resolved["feedback"] == "not now"
    done = tool_completed(c)
    assert done["ok"] is False and done["error_code"] == "rejected"
    c.expect("turn_completed")
    assert not (c.workspace / "hello.txt").exists()


def test_text_deltas_stream_before_turn_completed(start):
    c = start([[msg("alpha beta gamma")]])
    c.send(type="user_message", text="hi")
    c.expect("turn_completed")
    deltas = [m["text"] for m in c.received if m["type"] == "text_delta"]
    assert "".join(deltas) == "alpha beta gamma"


def test_non_ascii_text_survives_the_pipe(start):
    c = start([[msg("héllo ✓ 日本")]])
    c.send(type="user_message", text="ünïcode ✓")
    assert c.expect("turn_started")["user_message"] == "ünïcode ✓"
    assert c.expect("turn_completed")["text"] == "héllo ✓ 日本"


# -- cancel --------------------------------------------------------------------------------------


def test_cancel_during_approval_then_the_session_is_usable(start):
    c = start([[fn_call("write_file", path="a.txt", content="x")], [msg("after the cancel")]])
    c.send(type="user_message", text="write a.txt")
    c.expect("approval_requested")
    c.send(type="cancel")
    assert c.expect("approval_resolved")["by"] == "cancel"
    c.expect("turn_cancelled")
    assert not (c.workspace / "a.txt").exists()
    c.send(type="user_message", text="try again")              # history survived; the next turn runs normally
    assert c.expect("turn_completed")["text"] == "after the cancel"


def test_cancel_during_model_wait(start):
    c = start([BLOCKED_ROUND])
    c.send(type="user_message", text="think")
    c.expect("model_round_started")
    c.send(type="cancel")
    cancelled = c.expect("turn_cancelled")
    assert cancelled["turn_id"] == "t1" and "stats" in cancelled
    c.barrier()
    assert "turn_completed" not in c.types()


def test_cancel_when_idle_is_a_no_op(start):
    c = start([[msg("hi")]])
    c.send(type="cancel")
    assert "turn_cancelled" not in [m["type"] for m in c.barrier()]


# -- busy ----------------------------------------------------------------------------------------


def test_commands_that_need_an_idle_session_get_busy(start):
    c = start([BLOCKED_ROUND])
    c.send(type="user_message", text="first")
    c.expect("turn_started")
    c.send(type="user_message", text="second")
    assert c.expect("error")["code"] == "busy"
    c.send(type="new_conversation")
    assert c.expect("error")["code"] == "busy"
    c.send(type="get_usage")                                   # read-only commands work mid-turn
    c.expect("usage")
    c.send(type="cancel")
    c.expect("turn_cancelled")
    c.send(type="new_conversation")                            # and once idle it is accepted
    assert c.expect("notice")["code"] == "new_conversation"


# -- get_usage -----------------------------------------------------------------------------------


def test_get_usage_reports_session_totals(start):
    c = start([[msg("one")], [msg("two")]])
    c.send(type="get_usage")
    assert c.expect("usage")["totals"]["rounds"] == 0
    for text in ("a", "b"):
        c.send(type="user_message", text=text)
        c.expect("turn_completed")
    c.send(type="get_usage")
    reply = c.expect("usage")
    assert reply["totals"]["rounds"] == 2
    assert reply["totals"]["input_tokens"] == 200 and reply["totals"]["output_tokens"] == 20


# -- bad_request ---------------------------------------------------------------------------------


BAD_LINES = {
    "not json": b"this is not json\n",
    "not an object": b"[1, 2]\n",
    "no type": b"{}\n",
    "unknown type": b'{"type": "nope"}\n',
    "type not a string": b'{"type": ["user_message"]}\n',
    "invalid utf-8": b"\xff\xfe\n",
    "missing text": b'{"type": "user_message"}\n',
    "blank text": b'{"type": "user_message", "text": "   "}\n',
    "text not a string": b'{"type": "user_message", "text": 5}\n',
    "missing request_id": b'{"type": "approval_response", "decision": "allow"}\n',
    "bad decision": b'{"type": "approval_response", "request_id": "ap_1", "decision": "maybe"}\n',
    "feedback not a string": b'{"type": "approval_response", "request_id": "ap_1", "decision": "reject", "feedback": 3}\n',
}


def test_bad_requests_get_an_error_and_the_server_keeps_going(start):
    c = start([[msg("still here")]])
    for name, raw in BAD_LINES.items():
        c.send_raw(raw)
        error = c.expect("error")
        assert error["code"] == "bad_request" and error["message"], name
    c.send_raw(b"\n\r\n")                                       # blank lines are ignored, not errors
    assert [m["type"] for m in c.barrier() if m["type"] == "error"] == ["error"] * len(BAD_LINES)
    c.send(type="user_message", text="hello", extra_field="ignored")
    assert c.expect("turn_completed")["text"] == "still here"


def test_a_stale_approval_response_is_ignored_and_logged_to_stderr(start):
    c = start([[msg("hi")]])
    c.send(type="approval_response", request_id="ap_99", decision="allow")
    messages = c.barrier()
    assert [m["type"] for m in messages] == ["session_started", "usage"]       # no reply, no error
    assert "ap_99" in c.stderr() and "ignored" in c.stderr()


# -- shutdown ------------------------------------------------------------------------------------


def test_shutdown_exits_cleanly(start):
    c = start([[msg("hi")]])
    c.send(type="shutdown")
    assert c.wait_exit() == 0
    assert c.types() == ["session_started"]


def test_shutdown_during_a_turn_cancels_it_first(start):
    c = start([BLOCKED_ROUND])
    c.send(type="user_message", text="long task")
    c.expect("model_round_started")
    c.send(type="shutdown")
    assert c.wait_exit() == 0
    assert c.types()[-1] == "turn_cancelled"


def test_closing_stdin_exits_cleanly(start):
    c = start([[msg("hi")]])
    c.proc.stdin.close()
    assert c.wait_exit() == 0


# -- startup, logs, and the write path ---------------------------------------------------------------


def test_unusable_model_script_exits_with_a_usage_error_and_empty_stdout(tmp_path):
    for body in ("not json", '{"a": 1}', '[{"output": [], "block": "release"}]', "[5]"):
        script = tmp_path / "bad.json"
        script.write_text(body, encoding="utf-8")
        run = subprocess.run([sys.executable, "-m", "agent_v3.frontends.stdio_server", "--workspace", str(tmp_path),
                              "--fake-model-script", str(script)], cwd=ROOT, capture_output=True, timeout=TIMEOUT)
        assert run.returncode == 2 and run.stdout == b"", body
        assert b"model script" in run.stderr
    missing = subprocess.run([sys.executable, "-m", "agent_v3.frontends.stdio_server", "--workspace", str(tmp_path),
                              "--fake-model-script", str(tmp_path / "nope.json")], cwd=ROOT, capture_output=True,
                             timeout=TIMEOUT)
    assert missing.returncode == 2 and missing.stdout == b""


def test_command_output_stays_in_the_tool_result_not_the_protocol(start):
    c = start([[fn_call("run_command", command="echo from-a-child")], [msg("done")]], "--approval", "full-auto")
    c.send(type="user_message", text="run it")
    c.expect("turn_completed")
    out = [m for m in c.received if m["type"] == "tool_completed"][0]
    assert "from-a-child" in out["output"]                      # captured by the tool; stdout stays pure JSON lines


def _in_process_server(tmp_path, stdout):
    return StdioServer(AgentConfig(workspace=tmp_path, web_search=False), _NoModel(), stdin=io.BytesIO(), stdout=stdout)


class _NoModel:
    """Never called: these tests only exercise the output side."""


class _SplitWrites(io.BytesIO):
    """Like a pipe that takes a line in pieces: without the write lock, other writers get in between."""

    def write(self, b):
        half = len(b) // 2
        super().write(b[:half])
        time.sleep(0.0005)
        super().write(b[half:])
        return len(b)


def test_concurrent_writers_never_interleave_lines(tmp_path):
    sink = _SplitWrites()
    server = _in_process_server(tmp_path, sink)
    big = "x" * 200

    def hammer(n):
        for i in range(50):
            server._write({"type": "usage", "n": n, "i": i, "pad": big})

    threads = [threading.Thread(target=hammer, args=(n,)) for n in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    server.session.close()
    lines = sink.getvalue().split(b"\n")
    assert lines[-1] == b""
    rows = [json.loads(l) for l in lines[:-1]]                  # session_started + 400 whole lines
    assert len(rows) == 1 + 8 * 50
    for n in range(8):
        assert [r["i"] for r in rows if r.get("n") == n] == list(range(50))      # per-writer order kept


class _ClosedPipe(io.RawIOBase):
    def writable(self):
        return True

    def write(self, b):
        raise BrokenPipeError("client went away")


def test_a_closed_stdout_stops_output_without_raising(tmp_path):
    server = _in_process_server(tmp_path, _ClosedPipe())        # session_started already failed to write
    assert server._broken
    server._write({"type": "usage"})                            # silently dropped
    assert server.serve() == 0                                  # empty stdin: returns at once

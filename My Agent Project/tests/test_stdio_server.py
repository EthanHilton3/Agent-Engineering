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


# -- saved sessions (sessions spec §7, phase S4) ---------------------------------------------------
#
# Two ways to drive the server: as a subprocess (`start_in`, several servers sharing one workspace), and in-process
# (`inproc`, with the FakeModelAdapter shared by every session, so `fake.requests` shows what the model was sent).

import shutil

from conftest import FakeModelAdapter, Round

from agent_v3.sessions import SessionStore

SHARED = "shared"


@pytest.fixture
def start_in(tmp_path):
    """Like `start`, but every client works in tmp_path/shared, so a second server can see the first one's sessions."""
    clients: list[Client] = []
    (tmp_path / SHARED).mkdir(exist_ok=True)

    def make(script, *flags: str) -> Client:
        home = tmp_path / f"home{len(clients)}"
        home.mkdir()
        client = Client(home, script, "--workspace", str(tmp_path / SHARED), *flags)     # the later flag wins
        client.workspace = tmp_path / SHARED
        clients.append(client)
        client.expect("session_started")
        return client

    yield make
    for c in clients:
        c.close()
    for c in clients:
        assert c.bad_lines == [], f"stdout carried non-protocol lines: {c.bad_lines}"


def _run_server(tmp_path, *args: str) -> subprocess.CompletedProcess:
    (tmp_path / SHARED).mkdir(exist_ok=True)
    script = tmp_path / "empty.json"
    script.write_text("[]", encoding="utf-8")
    return subprocess.run([sys.executable, "-m", "agent_v3.frontends.stdio_server", "--workspace",
                           str(tmp_path / SHARED), "--no-web", "--fake-model-script", str(script), *args],
                          cwd=ROOT, capture_output=True, timeout=TIMEOUT)


class InProc:
    """A StdioServer in this process, fed one line at a time. Its output is read back from a buffer."""

    def __init__(self, workspace: Path, rounds: list, *, saving: bool = True, resume: str | None = None):
        self.workspace = workspace
        self.out = io.BytesIO()
        config = AgentConfig(workspace=workspace, web_search=False)
        self.fake = FakeModelAdapter(config, rounds)
        self.store = SessionStore.for_workspace(workspace)
        self.server = StdioServer(config, self.fake, stdin=io.BytesIO(), stdout=self.out,
                                  store=self.store if saving else None, resume=resume)
        self._pos = 0

    @property
    def session_id(self) -> str:
        return self.server.session.session_id

    def take(self) -> list[dict]:
        """The messages written since the last `take`."""
        lines = self.out.getvalue().split(b"\n")[:-1]
        fresh, self._pos = lines[self._pos:], len(lines)
        return [json.loads(line) for line in fresh]

    def send(self, **message) -> list[dict]:
        self.server._handle_line(json.dumps(message).encode() + b"\n")
        return self.take()

    def turn(self, text: str) -> list[dict]:
        sent = self.send(type="user_message", text=text)
        assert self.server.session.wait(TIMEOUT)
        return sent + self.take()

    def blocked(self) -> None:
        """Wait until the (blocked) round is in flight."""
        deadline = time.monotonic() + TIMEOUT
        while not (self.fake.streams and self.fake.streams[-1].blocked.wait(0.05)):
            assert time.monotonic() < deadline, "the model round never started"


@pytest.fixture
def inproc(tmp_path):
    made: list[InProc] = []

    def make(rounds: list, **kw) -> InProc:
        workspace = kw.pop("workspace", tmp_path / "ws")
        workspace.mkdir(exist_ok=True)
        made.append(InProc(workspace, rounds, **kw))
        return made[-1]

    yield make
    for p in made:
        p.server.session.close()


def only(messages: list[dict], type_: str) -> dict:
    found = [m for m in messages if m.get("type") == type_]
    assert len(found) == 1, f"expected one {type_}, got {[m.get('type') for m in messages]}"
    return found[0]


def prompt_texts(request: dict) -> list:
    return [item.get("content") for item in request["input"]]


# -- list_sessions -------------------------------------------------------------------------------


def test_list_sessions_shows_the_open_session_as_current(start):
    c = start([[msg("hi")]])
    c.send(type="list_sessions")
    first = c.expect("sessions")
    assert first["sessions"] == [] and first["total"] == 0                  # nothing is saved before the first turn
    sid = c.received[0]["session_id"]
    assert first["current"] == sid

    c.send(type="user_message", text="Rename Store.remove please")
    c.expect("turn_completed")
    c.send(type="list_sessions")
    reply = c.expect("sessions")
    assert reply["current"] == sid and reply["total"] == 1 and "seq" not in reply
    (row,) = reply["sessions"]
    assert row["session_id"] == sid and row["status"] == "current" and row["turns"] == 1
    assert row["title"] == "Rename Store.remove please" and row["model"] and row["updated"] >= row["created"]


def test_list_sessions_without_a_limit_returns_every_session_with_total(inproc):
    p = inproc([[msg("a")], [msg("b")], [msg("c")]])
    ids = []
    for text in ("one", "two", "three"):
        p.turn(text)
        ids.append(p.session_id)
        if text != "three":
            p.send(type="new_session")
    reply = only(p.send(type="list_sessions"), "sessions")
    assert reply["total"] == 3 and {r["session_id"] for r in reply["sessions"]} == set(ids)
    assert reply["current"] == ids[-1]
    updated = [r["updated"] for r in reply["sessions"]]
    assert updated == sorted(updated, reverse=True)                         # newest first
    assert [r["status"] for r in reply["sessions"] if r["session_id"] == ids[-1]] == ["current"]

    limited = only(p.send(type="list_sessions", limit=2), "sessions")
    assert limited["total"] == 3 and [r["session_id"] for r in limited["sessions"]] == [r["session_id"] for r in reply["sessions"]][:2]
    for bad in (0, -1, "2", 1.5, True):
        assert only(p.send(type="list_sessions", limit=bad), "error")["code"] == "bad_request"


# -- starting with --resume / --continue -----------------------------------------------------------


def test_a_new_server_resumes_a_saved_session_with_the_flag(start_in):
    a = start_in([[msg("a1")]])
    sid = a.received[0]["session_id"]
    a.send(type="user_message", text="remember the number 7")
    a.expect("turn_completed")
    a.send(type="shutdown")
    assert a.wait_exit() == 0

    b = start_in([[msg("b1")]], "--resume", sid[2:8])
    resumed = b.expect("session_resumed")
    started = b.received[0]
    assert b.received[1] is resumed                                          # directly after session_started
    assert started["type"] == "session_started" and started["session_id"] == sid
    assert started["seq"] > 1 and started["protocol_version"] == 1
    assert resumed["type"] == "session_resumed" and resumed["session_id"] == sid and resumed["seq"] == started["seq"] + 1
    assert resumed["title"] == "remember the number 7" and resumed["turns_total"] == 1
    assert resumed["turns"][0]["text"] == "a1"
    b.send(type="user_message", text="again")
    assert b.expect("turn_started")["turn_id"] == "t2"                       # the turn counter continues
    b.expect("turn_completed")
    b.send(type="get_usage")
    assert b.expect("usage")["totals"]["rounds"] == 2                        # totals cover the earlier process too


def test_continue_resumes_the_latest_session_or_starts_a_new_one(start_in):
    first = start_in([[msg("x")]], "--continue")                             # nothing saved yet: a new session
    sid = first.received[0]["session_id"]
    assert first.received[0]["seq"] == 1 and not any(m["type"] == "session_resumed" for m in first.barrier())
    first.send(type="user_message", text="hello")
    first.expect("turn_completed")
    first.send(type="shutdown")
    first.wait_exit()
    second = start_in([[msg("y")]], "-c")
    second.expect("session_resumed")
    assert second.received[0]["session_id"] == sid and second.received[1]["type"] == "session_resumed"


def test_resume_startup_errors_exit_2_with_empty_stdout(tmp_path, start_in):
    a = start_in([[msg("a")]])
    sid = a.received[0]["session_id"]
    a.send(type="user_message", text="hello")
    a.expect("turn_completed")                                               # saved, and still open here

    in_use = _run_server(tmp_path, "--resume", sid)
    assert in_use.returncode == 2 and in_use.stdout == b"" and b"another agent_v3 process" in in_use.stderr
    cont = _run_server(tmp_path, "--continue")
    assert cont.returncode == 2 and cont.stdout == b"" and b"use --resume to pick another" in cont.stderr
    unknown = _run_server(tmp_path, "--resume", "s_ffffffffffff")
    assert unknown.returncode == 2 and unknown.stdout == b"" and b"No saved session" in unknown.stderr
    for flags in (["--resume"], ["--resume", "latest", "--continue"], ["--no-save", "--resume", "latest"],
                  ["--no-save", "--continue"]):
        run = _run_server(tmp_path, *flags)
        assert run.returncode == 2 and run.stdout == b"", flags


# -- resume_session, new_session -------------------------------------------------------------------


def test_resume_session_switches_to_the_saved_conversation(inproc):
    p = inproc([[msg("a1")], [msg("b1")], [msg("a2")], [msg("c1")]])
    p.turn("first question")
    first = p.session_id
    started = only(p.send(type="new_session"), "session_started")
    second = started["session_id"]
    assert second != first and started["seq"] == 1
    p.turn("second question")

    messages = p.send(type="resume_session", session_id=first[2:8])
    assert [m["type"] for m in messages] == ["session_started", "session_resumed"]
    assert messages[0]["session_id"] == first == p.session_id and messages[0]["seq"] > 1
    assert messages[1]["seq"] == messages[0]["seq"] + 1
    assert only(p.send(type="get_usage"), "usage")["totals"]["rounds"] == 1

    p.turn("third question")
    seen = prompt_texts(p.fake.requests[-1])
    assert "first question" in seen and "a1" in seen and "second question" not in seen
    p.send(type="new_session")                                               # unsaved until its first turn
    assert only(p.send(type="resume_session", latest=True), "session_started")["session_id"] == first


def test_resume_session_errors_leave_the_current_session_alone(inproc, tmp_path):
    p = inproc([Round(output=[msg("never")], block="cancel"), [msg("later")]])
    other = inproc([[msg("o")]])
    other.turn("held open elsewhere")
    held = other.session_id
    current = p.session_id

    p.send(type="user_message", text="start")
    p.blocked()
    assert only(p.send(type="resume_session", session_id=held), "error")["code"] == "busy"
    assert only(p.send(type="new_session"), "error")["code"] == "busy"
    p.send(type="cancel")
    assert p.server.session.wait(TIMEOUT)
    p.take()

    for message, code in (({"session_id": "ffff0000"}, "not_found"), ({"session_id": "ab"}, "not_found"),
                          ({"session_id": held}, "in_use"), ({"latest": True}, "bad_request"),    # latest is this one
                          ({"session_id": current}, "bad_request"), ({}, "bad_request"),
                          ({"session_id": held, "latest": True}, "bad_request"), ({"latest": "yes"}, "bad_request"),
                          ({"session_id": 5}, "bad_request")):
        reply = p.send(type="resume_session", **message)
        assert [m["type"] for m in reply] == ["error"] and reply[0]["code"] == code, (message, reply)
    assert p.session_id == current                                           # the failed resumes changed nothing
    p.turn("still works")
    assert p.fake.index == 2


def test_resume_session_with_an_ambiguous_prefix(inproc):
    p = inproc([[msg("a")]])
    p.turn("hello")
    twin = p.store.root / ("s_" + p.session_id[2:6] + "ffffffff")
    shutil.copytree(p.store.session_dir(p.session_id), twin)
    for name in ("meta.json", "lock"):
        (twin / name).unlink(missing_ok=True)
    reply = only(p.send(type="resume_session", session_id=p.session_id[2:6]), "error")
    assert reply["code"] == "ambiguous" and twin.name in reply["message"]


def test_new_session_is_a_new_id_while_new_conversation_keeps_its_meaning(inproc):
    p = inproc([[msg("a")], [msg("b")]])
    p.turn("hello")
    first = p.session_id
    reply = only(p.send(type="new_conversation"), "notice")
    assert reply["code"] == "new_conversation" and reply["session_id"] == first       # same id, history cleared
    assert p.session_id == first
    messages = p.send(type="new_session")
    assert [m["type"] for m in messages] == ["session_started"]
    assert messages[0]["session_id"] != first and messages[0]["seq"] == 1
    assert messages[0]["config"]["approval"] == "ask"
    p.turn("fresh start")
    assert "hello" not in prompt_texts(p.fake.requests[-1])


# -- export_session, delete_session ----------------------------------------------------------------


def test_export_session_returns_the_markdown(inproc):
    p = inproc([[msg("a")], [msg("b")]])
    empty = only(p.send(type="export_session"), "transcript")
    assert empty["session_id"] == p.session_id and empty["markdown"] == "" and "seq" not in empty
    p.turn("explain the cache")
    first = p.session_id
    current = only(p.send(type="export_session"), "transcript")
    assert current["session_id"] == first and "**USER:** explain the cache" in current["markdown"]
    p.send(type="new_session")
    p.turn("something else")
    old = only(p.send(type="export_session", session_id=first[2:8]), "transcript")      # another session, by prefix
    assert old["session_id"] == first and "explain the cache" in old["markdown"]
    assert "something else" not in old["markdown"]
    assert only(p.send(type="export_session", session_id="ffff0000"), "error")["code"] == "not_found"


def test_delete_session_removes_one_session(inproc):
    p = inproc([[msg("a")], [msg("b")]])
    held = inproc([[msg("h")]], workspace=p.workspace)
    held.turn("busy elsewhere")
    p.turn("old chat")
    old = p.session_id
    p.send(type="new_session")
    p.turn("current chat")
    current = p.session_id

    assert only(p.send(type="delete_session", session_id=current), "error")["code"] == "in_use"
    assert only(p.send(type="delete_session", session_id=held.session_id), "error")["code"] == "in_use"
    assert only(p.send(type="delete_session", session_id="ffff0000"), "error")["code"] == "not_found"
    assert only(p.send(type="delete_session"), "error")["code"] == "bad_request"
    assert only(p.send(type="delete_session", session_id=7), "error")["code"] == "bad_request"
    assert only(p.send(type="list_sessions"), "sessions")["total"] == 3

    deleted = only(p.send(type="delete_session", session_id=old[2:8]), "session_deleted")
    assert deleted == {"type": "session_deleted", "session_id": old}
    listed = only(p.send(type="list_sessions"), "sessions")
    assert {r["session_id"] for r in listed["sessions"]} == {current, held.session_id}
    assert not p.store.session_dir(old).exists()


# -- --no-save -----------------------------------------------------------------------------------------


def test_no_save_writes_nothing_but_still_lists_and_exports(start_in):
    a = start_in([[msg("saved")]])
    saved = a.received[0]["session_id"]
    a.send(type="user_message", text="keep this")
    a.expect("turn_completed")
    a.send(type="shutdown")
    a.wait_exit()
    sessions = a.workspace / ".agent_v3" / "sessions"
    before = sorted(p.name for p in sessions.iterdir())

    b = start_in([[msg("unsaved")], [msg("also unsaved")]], "--no-save")
    b.send(type="user_message", text="do not keep this")
    b.expect("turn_completed")
    b.send(type="list_sessions")
    listed = b.expect("sessions")
    assert [r["session_id"] for r in listed["sessions"]] == [saved] and listed["total"] == 1
    assert listed["sessions"][0]["status"] == "idle" and listed["current"] != saved

    b.send(type="resume_session", session_id=saved)
    assert b.expect("error")["code"] == "saving_disabled"
    b.send(type="resume_session", latest=True)
    assert b.expect("error")["code"] == "saving_disabled"
    b.send(type="export_session")
    assert b.expect("error")["code"] == "saving_disabled"
    b.send(type="export_session", session_id=b.received[0]["session_id"])
    assert b.expect("error")["code"] == "saving_disabled"
    b.send(type="export_session", session_id=saved)                          # a saved session can still be read
    assert "keep this" in b.expect("transcript")["markdown"]
    b.send(type="new_session")                                               # and a new (unsaved) one can start
    assert b.expect("session_started")["seq"] == 1
    b.barrier()
    assert sorted(p.name for p in sessions.iterdir()) == before


def test_no_save_creates_no_folder(start):
    c = start([[msg("hi")]], "--no-save")
    c.send(type="user_message", text="hello")
    c.expect("turn_completed")
    c.send(type="list_sessions")
    assert c.expect("sessions")["total"] == 0
    assert not (c.workspace / ".agent_v3").exists()


# -- set_config, get_session_events (sessions spec §5.6, §7.2, phase S5) -----------------------------


def test_set_config_changes_the_open_session_in_place(inproc):
    p = inproc([[msg("a")], [msg("b")], [msg("c")]])
    opening = only(p.take(), "session_started")
    first = p.turn("first")
    sid, last_seq = p.session_id, first[-1]["seq"]
    reply = p.send(type="set_config", model="gpt-5.6-sol", approval="auto-edit", reasoning=None)
    changed = only(reply, "config_changed")
    assert len(reply) == 1 and changed["session_id"] == sid and changed["seq"] == last_seq + 1
    assert changed["turn_id"] is None and changed["history"] == "unchanged"
    assert changed["changes"] == {"model": {"from": "gpt-6-luna", "to": "gpt-5.6-sol"},
                                  "approval": {"from": "ask", "to": "auto-edit"}}
    assert changed["config"]["model"] == "gpt-5.6-sol" and changed["config"]["approval"] == "auto-edit"
    assert changed["config"]["tools"] == opening["config"]["tools"]      # same shape as session_started.config
    p.turn("second")
    assert p.session_id == sid and p.fake.requests[-1]["model"] == "gpt-5.6-sol"
    assert "Approval mode: auto-edit" in p.fake.requests[-1]["input"][0]["content"]

    same = only(p.send(type="set_config", model="gpt-5.6-sol"), "config_changed")      # always answered
    assert same["changes"] == {} and same["config"]["model"] == "gpt-5.6-sol"

    started = only(p.send(type="new_session"), "session_started")    # new sessions start from the working config
    assert (started["config"]["model"], started["config"]["approval"]) == ("gpt-5.6-sol", "auto-edit")
    only(p.send(type="set_config", model="gpt-6-luna"), "config_changed")
    resumed = p.send(type="resume_session", session_id=sid)          # the changed model counts as typed
    assert resumed[1]["saved_config"]["model"] == "gpt-5.6-sol" and resumed[0]["config"]["model"] == "gpt-6-luna"
    assert resumed[0]["config"]["approval"] == "auto-edit"


def test_set_config_errors(inproc):
    p = inproc([Round(output=[msg("never")], block="cancel"), [msg("later")]])
    p.take()
    for message in ({}, {"model": None}, {"approval": "yolo"}, {"reasoning": "LOUD"}, {"model": 5}, {"model": ""},
                    {"reasoning": ["low"]}, {"model": "gpt-5.6-sol", "approval": "nope"}):
        reply = p.send(type="set_config", **message)
        assert [m["type"] for m in reply] == ["error"] and reply[0]["code"] == "bad_request", (message, reply)
    p.send(type="user_message", text="start")
    p.blocked()
    p.take()
    reply = p.send(type="set_config", reasoning="low")
    assert [m["type"] for m in reply] == ["error"] and reply[0]["code"] == "busy"
    p.send(type="cancel")
    assert p.server.session.wait(TIMEOUT)
    config = p.server.session.config
    assert (config.model, config.reasoning, config.approval) == ("gpt-6-luna", "medium", "ask")   # nothing applied
    started = only(p.send(type="new_session"), "session_started")
    assert started["config"]["model"] == "gpt-6-luna"                  # and nothing was remembered


def test_get_session_events_pages_through_a_saved_session(inproc):
    p = inproc([[msg("one two three")], [msg("four five")], [msg("six")]])
    empty = only(p.send(type="get_session_events"), "session_events")   # the open session, before its first turn
    assert empty == {"type": "session_events", "session_id": p.session_id, "events": [], "next_after_seq": 0,
                     "done": True}
    wire = p.turn("first") + p.send(type="set_config", reasoning="low") + p.turn("second")
    old = p.session_id
    expected = [m for m in [{"type": "session_started", "seq": 1}] + wire if m["type"] != "text_delta"]
    assert any(m["type"] == "text_delta" for m in wire)
    p.send(type="new_session")
    p.turn("third")

    events, after, pages = [], 0, 0
    while True:
        reply = only(p.send(type="get_session_events", session_id=old[2:8], after_seq=after, limit=4),
                     "session_events")
        assert reply["session_id"] == old and "seq" not in reply and len(reply["events"]) <= 4
        events += reply["events"]
        after, pages = reply["next_after_seq"], pages + 1
        if reply["done"]:
            break
        assert after == reply["events"][-1]["seq"]
    assert pages > 2 and [e["seq"] for e in events] == [m["seq"] for m in expected]
    assert events[1:] == expected[1:] and events[0]["type"] == "session_started"
    assert all(e["type"] != "text_delta" for e in events)
    tail = only(p.send(type="get_session_events", session_id=old, after_seq=after), "session_events")
    assert tail["events"] == [] and tail["done"] and tail["next_after_seq"] == after

    current = only(p.send(type="get_session_events"), "session_events")    # default: the open session
    assert current["session_id"] == p.session_id and current["done"]
    assert [e["type"] for e in current["events"]][:2] == ["session_started", "turn_started"]


def test_get_session_events_errors(inproc, tmp_path):
    saver = inproc([[msg("kept")]])
    saver.turn("a saved session")
    saved = saver.session_id
    saver.server.session.close()
    p = inproc([[msg("x")]], workspace=saver.workspace)
    assert only(p.send(type="get_session_events", session_id="ffff0000"), "error")["code"] == "not_found"
    for bad in ({"limit": 0}, {"limit": 2001}, {"limit": "5"}, {"after_seq": -1}, {"after_seq": 1.5},
                {"after_seq": True}, {"session_id": 7}):
        assert only(p.send(type="get_session_events", **bad), "error")["code"] == "bad_request", bad
    assert only(p.send(type="get_session_events", limit=2000), "session_events")["done"]

    unsaved = inproc([[msg("y")]], workspace=saver.workspace, saving=False)
    unsaved.turn("not kept")
    assert only(unsaved.send(type="get_session_events"), "error")["code"] == "saving_disabled"
    reply = unsaved.send(type="get_session_events", session_id=unsaved.session_id)
    assert only(reply, "error")["code"] == "saving_disabled"
    other = only(unsaved.send(type="get_session_events", session_id=saved), "session_events")   # still readable
    assert other["done"] and other["events"][0]["session_id"] == saved


# -- final review regressions --------------------------------------------------------------------


def test_set_config_strips_the_model_name_for_this_and_later_sessions(inproc):
    """#3: a padded model name is stored, announced, sent and carried over stripped."""
    p = inproc([[msg("a")], [msg("b")]])
    p.take()
    changed = only(p.send(type="set_config", model="gpt-5.6-sol "), "config_changed")
    assert changed["changes"]["model"]["to"] == "gpt-5.6-sol" and changed["config"]["model"] == "gpt-5.6-sol"
    p.turn("first")
    assert p.fake.requests[-1]["model"] == "gpt-5.6-sol"
    assert only(p.send(type="set_config", model=" \t"), "error")["code"] == "bad_request"
    started = only(p.send(type="new_session"), "session_started")
    assert started["config"]["model"] == "gpt-5.6-sol"


def test_null_optional_fields_mean_omitted(inproc):
    """#6: null is the default for every optional field, as set_config already treats it."""
    saver = inproc([[msg("kept")]])
    saver.turn("a saved session")
    saved = saver.session_id
    saver.server.session.close()
    p = inproc([[msg("x")]], workspace=saver.workspace)
    p.take()
    reply = only(p.send(type="get_session_events", session_id=saved, after_seq=None, limit=None), "session_events")
    assert reply["done"] and reply["events"][0]["seq"] == 1 and reply["next_after_seq"] == reply["events"][-1]["seq"]
    assert only(p.send(type="list_sessions", limit=None), "sessions")["total"] == 1
    assert only(p.send(type="export_session", session_id=None), "transcript")["session_id"] == p.session_id
    resumed = p.send(type="resume_session", session_id=saved[2:8], latest=None)
    assert [m["type"] for m in resumed][:2] == ["session_started", "session_resumed"] and p.session_id == saved

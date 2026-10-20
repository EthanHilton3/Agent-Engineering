"""Saved sessions in `Session` (sessions spec §5.2–§5.5, Phase S2): recorder hooks, resume, interrupted turns.

Each `Session` here gets its own FakeModelAdapter, so `fake.requests` shows exactly what a resumed session sends.
"""
import json
import os
import threading
import time

import pytest

from conftest import EventLog, FakeModelAdapter, Round, fn_call, msg, reasoning_item

from agent_v3 import events as ev
from agent_v3 import sessions as sessions_mod
from agent_v3.config import AgentConfig
from agent_v3.jsonl import read_jsonl
from agent_v3.session import Session
from agent_v3.sessions import SessionInUse, SessionNotFound, SessionStore


def run(session, text="go", timeout=10):
    tid = session.start_turn(text)
    assert session.wait(timeout), "turn did not finish"
    return tid


def kinds(items):
    return [i.get("type") or f"msg:{i['role']}" for i in items]


def outputs(request):
    return {i["call_id"]: i["output"] for i in request["input"] if i.get("type") == "function_call_output"}


def wait_blocked(fake, n=1, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if len(fake.streams) >= n and fake.streams[n - 1].blocked.is_set():
            return fake.streams[n - 1]
        time.sleep(0.01)
    raise AssertionError("fake stream never blocked")


def same_totals(a, b):
    """Totals restored from disk sum rounded per-turn stats, so their float fields can differ in the last digit."""
    assert a.keys() == b.keys()
    for k in a:
        assert a[k] == pytest.approx(b[k], abs=2e-3) if isinstance(a[k], float) else a[k] == b[k], k
    return True


def edit_call(path="a.py", old="x = 1", new="x = 2", call_id=None):
    return fn_call("edit_files", call_id=call_id, edits=[{"path": path, "old_text": old, "new_text": new}])


@pytest.fixture
def ws(tmp_path):
    root = tmp_path / "ws"
    root.mkdir()
    return root


@pytest.fixture
def store(ws):
    return SessionStore.for_workspace(ws)


@pytest.fixture
def open_session(ws, store):
    """open_session(rounds, resume=None, **config) -> (session, fake, log), saved in the workspace's store."""
    made = []

    def make(rounds, resume=None, **cfg):
        cfg.setdefault("web_search", False)
        config = AgentConfig(workspace=ws, **cfg)
        fake = FakeModelAdapter(config, rounds)
        log = EventLog()
        session = Session(config, log, model=fake, store=store, resume=resume)
        made.append(session)
        return session, fake, log

    yield make
    for s in made:
        s.close()


# -- no store ----------------------------------------------------------------------------------

def test_a_store_less_session_saves_nothing(make_session, ws):
    s, fake, log = make_session([[fn_call("run_command", command="echo hi")], [msg("ran it")]], approval="full-auto")
    run(s)
    s.close()
    assert log.of("turn_completed") and not s.saved
    assert not (s.workspace.root / ".agent_v3" / "sessions").exists()


def test_a_saved_session_without_turns_leaves_nothing_on_disk(open_session, ws):
    s, fake, log = open_session([])
    assert s.saved
    s.close()
    assert not s.saved and not (ws / ".agent_v3").exists()


# -- recording ---------------------------------------------------------------------------------

def test_events_and_the_history_line_reach_disk_before_the_frontend_sees_them(ws, store):
    seen, problems = [], []
    config = AgentConfig(workspace=ws, web_search=False, approval="full-auto")

    def sink(event):                                    # Session swallows sink errors, so collect them instead
        seen.append(event)
        path = store.events_path(event.session_id)
        if event.type in ("session_started", "text_delta"):  # session_started waits for the first turn
            return
        if list(read_jsonl(path))[-1]["seq"] != event.seq:
            problems.append(f"{event.type} not on disk yet")
        if event.type == "turn_completed":
            lines = list(read_jsonl(store.session_dir(event.session_id) / "history.jsonl"))
            if not lines or lines[-1]["turn_id"] != event.turn_id:
                problems.append("history line missing at turn_completed")

    s = Session(config, sink, model=FakeModelAdapter(config, [[fn_call("read_file", path="a.py")], [msg("x is 1")]]),
                store=store)
    (ws / "a.py").write_text("x = 1\n")
    run(s, "what is x?")
    s.close()
    assert problems == [] and len(seen) > 5
    on_disk = list(read_jsonl(store.events_path(s.session_id)))
    assert on_disk == [e.to_dict() for e in seen if e.type != "text_delta"]
    [line] = read_jsonl(store.session_dir(s.session_id) / "history.jsonl")
    assert (line["turn_id"], line["outcome"], line["text"], line["model"]) == ("t1", "completed", "x is 1", config.model)
    assert line["items"] == s.history[1:] and line["record"] is None


# -- resume ------------------------------------------------------------------------------------

def test_two_turns_close_and_resume(open_session):
    s1, fake1, log1 = open_session([[msg("a1")], [msg("a2")]])
    run(s1, "u1")
    run(s1, "u2")
    sid, totals, last_seq, before = s1.session_id, s1.usage_totals(), log1.events[-1].seq, list(s1.history)
    s1.close()

    s2, fake2, log2 = open_session([[msg("a3")]], resume=sid)
    assert s2.session_id == sid and s2.saved
    assert log2.types() == ["session_started", "session_resumed"]
    assert [e.seq for e in log2.events] == [last_seq + 1, last_seq + 2]
    assert {e.session_id for e in log2.events} == {sid}
    resumed = log2.of("session_resumed")[0]
    assert (resumed.title, resumed.turns_total, resumed.history, resumed.restored_items) == ("u1", 2, "pruned", 6)
    assert [(t["turn_id"], t["user_message"], t["outcome"], t["text"]) for t in resumed.turns] == [
        ("t1", "u1", "completed", "a1"), ("t2", "u2", "completed", "a2")]
    assert resumed.interrupted_turn is None and same_totals(resumed.totals, totals)
    assert resumed.saved_config == {"model": s1.config.model, "reasoning": "medium", "approval": "ask",
                                    "prune_history": True}
    assert same_totals(s2.usage_totals(), totals)

    assert run(s2, "u3") == "t3"
    [req] = fake2.requests
    assert req["input"] == [{"role": "system", "content": s2.system_prompt}, *before[1:],
                            {"role": "user", "content": "u3"}]
    assert kinds(req["input"]) == ["msg:system", *["msg:user", "msg:assistant", "msg:developer"] * 2, "msg:user"]
    assert s2.usage_totals()["rounds"] == 3
    seqs = [e.seq for e in log2.events]
    assert seqs == list(range(last_seq + 1, last_seq + 1 + len(seqs)))


def test_resume_with_another_approval_mode_rebuilds_the_prompt_and_cache_key(open_session, ws):
    s1, _, _ = open_session([[msg("a1")]])
    run(s1, "u1")
    s1.close()
    s2, fake2, log2 = open_session([[msg("a2")]], resume=s1.session_id, approval="auto-edit")
    assert "Approval mode: auto-edit" in s2.system_prompt and "Approval mode: ask" not in s2.system_prompt
    assert s2.cache_key != s1.cache_key
    fresh_cfg = AgentConfig(workspace=ws, web_search=False, approval="auto-edit")
    fresh = Session(fresh_cfg, EventLog(), model=FakeModelAdapter(fresh_cfg, []))
    fresh.close()
    assert s2.cache_key == fresh.cache_key
    assert log2.of("session_resumed")[0].saved_config["approval"] == "ask"
    run(s2, "u2")
    req = fake2.requests[0]
    assert req["input"][0]["content"] == s2.system_prompt and req["prompt_cache_key"] == s2.cache_key


def test_read_hashes_and_session_allowances_are_not_restored(open_session, ws):
    (ws / "a.py").write_text("x = 1\n")
    s1, _, log1 = open_session([[fn_call("read_file", path="a.py")], [fn_call("run_command", command="echo hi")],
                                [msg("read and ran")]])
    s1.start_turn("look")
    req = log1.wait_for("approval_requested").request
    s1.respond_approval(req["request_id"], "allow_session")
    assert s1.wait(10)
    s1.close()

    write = dict(path="a.py", content="x = 2\n", overwrite=True)
    s2, fake2, log2 = open_session([
        [fn_call("write_file", call_id="w1", **write)],
        [fn_call("read_file", path="a.py")],
        [fn_call("write_file", call_id="w2", **write)],
        [fn_call("run_command", command="echo hi")],
        [msg("done")],
    ], resume=s1.session_id, approval="auto-edit")
    s2.start_turn("overwrite it, then run echo hi")
    req = log2.wait_for("approval_requested").request                 # the allowance did not survive the resume
    assert req["kind"] == "command" and req["command"] == "echo hi"
    s2.respond_approval(req["request_id"], "allow")
    assert s2.wait(10)
    assert outputs(fake2.requests[1])["w1"] == "Error (conflict): Read the current file before overwriting it."
    assert outputs(fake2.requests[3])["w2"].startswith("Overwrote a.py")
    assert (ws / "a.py").read_text() == "x = 2\n"


def full_turn(answer):
    return [[reasoning_item(), fn_call("read_file", path="a.py")], [reasoning_item(), msg(answer)]]


def test_full_turns_come_back_only_to_the_model_that_made_them(open_session, ws):
    (ws / "a.py").write_text("x = 1\n")
    other = "gpt-5.6-luna"
    s1, _, _ = open_session(full_turn("one"), approval="full-auto", prune_history=False)
    run(s1, "u1")
    full1 = s1.history[1:]
    s1.close()
    assert kinds(full1) == ["msg:user", "reasoning", "function_call", "function_call_output", "reasoning", "message"]

    s2, fake2, log2 = open_session(full_turn("two"), resume=s1.session_id, approval="full-auto", prune_history=False)
    resumed = log2.of("session_resumed")[0]
    assert resumed.history == "full" and resumed.restored_items == 6 and s2.history[1:] == full1
    run(s2, "u2")
    assert fake2.requests[0]["input"][1:7] == full1                    # reasoning items go back to the same model
    s2.close()

    s3, fake3, log3 = open_session(full_turn("three"), resume=s1.session_id, model=other, approval="full-auto",
                                   prune_history=False)
    assert log3.of("session_resumed")[0].history == "pruned"
    assert kinds(s3.history) == ["msg:system", *["msg:user", "msg:assistant", "msg:developer"] * 2]
    assert s3.history[2]["content"] == "one" and s3.history[3]["content"] == "Turn record: read a.py."
    run(s3, "u3")                                                      # t3 is a full turn made by the other model
    s3.close()

    s4, _, log4 = open_session([], resume=s1.session_id, model=other, prune_history=False)
    assert log4.of("session_resumed")[0].history == "full"
    assert kinds(s4.history) == ["msg:system", *["msg:user", "msg:assistant", "msg:developer"] * 2,
                                 "msg:user", "reasoning", "function_call", "function_call_output", "reasoning",
                                 "message"]
    s4.close()

    s5, _, log5 = open_session([], resume=s1.session_id, model=other)  # pruning on: every turn pruned
    assert log5.of("session_resumed")[0].history == "pruned"
    assert kinds(s5.history) == ["msg:system", *["msg:user", "msg:assistant", "msg:developer"] * 3]
    assert log5.of("session_resumed")[0].saved_config["prune_history"] is False


def test_cancelled_and_failed_turns_come_back_with_their_notes(open_session):
    s1, fake1, log1 = open_session([
        Round(output=[msg("x")], stream_error={"type": "error", "code": "server_error", "message": "boom"}),
        Round(output=[msg("never")], block="cancel"),
    ])
    run(s1, "first")
    s1.start_turn("second")
    wait_blocked(fake1, n=2)
    s1.cancel()
    assert [e.type for e in log1.events if e.type.startswith("turn_")][-1] == "turn_cancelled"
    before = list(s1.history)
    s1.close()
    assert "Turn failed (server_error)" in before[2]["content"]
    assert before[4]["content"].startswith("Turn cancelled by user after:")

    s2, _, log2 = open_session([], resume=s1.session_id)
    assert s2.history[1:] == before[1:]
    assert [t["outcome"] for t in log2.of("session_resumed")[0].turns] == ["failed", "cancelled"]


def test_an_interrupted_turn_is_recovered_once(open_session, ws):
    (ws / "a.py").write_text("x = 1\n")
    release = threading.Event()
    s1, fake1, log1 = open_session([
        [msg("one")],
        [edit_call(), fn_call("run_command", command="echo hi")],
        Round(output=[msg("never")], block="release", release=release),
    ], approval="full-auto")
    try:
        run(s1, "first")
        s1.start_turn("Change x and run echo")
        wait_blocked(fake1, n=3)
        with s1._lock:                                   # the process "dies": its files and lock are let go
            s1._recorder.close()
        t2_cost = sum(e.cost_usd for e in log1.of("model_round_completed") if e.turn_id == "t2")
        t1_cost = s1.usage_totals()["model_cost_usd"]
        assert t2_cost > 0 and s1.usage_totals()["rounds"] == 1

        s2, fake2, log2 = open_session([[msg("three")]], resume=s1.session_id)
        assert log2.types() == ["session_started", "session_resumed", "notice"]
        notice = log2.of("notice")[0]
        assert (notice.level, notice.code) == ("warning", "turn_interrupted") and "Turn t2" in notice.message
        resumed = log2.of("session_resumed")[0]
        assert resumed.interrupted_turn == "t2" and resumed.turns_total == 2
        assert [(t["turn_id"], t["outcome"]) for t in resumed.turns] == [("t1", "completed"), ("t2", "interrupted")]
        note = s2.history[-1]["content"]
        assert s2.history[-2] == {"role": "user", "content": "Change x and run echo"}
        assert note.startswith("Turn interrupted (the agent process stopped) after: ")
        assert "edited a.py (+1 −1)" in note and "ran `echo hi` (exit 0)" in note and "re-read before editing" in note
        totals = s2.usage_totals()
        assert totals["rounds"] == 2 and totals["tool_calls"] == 2
        assert totals["model_cost_usd"] == pytest.approx(t1_cost + t2_cost, abs=1e-6)
        assert resumed.totals == totals
        assert run(s2, "now what?") == "t3"
        assert fake2.requests[0]["input"][-3:-1] == s2.history[-5:-3]  # the note went to the model
        after_t3 = s2.usage_totals()
        s2.close()

        s3, _, log3 = open_session([], resume=s1.session_id)
        assert log3.types() == ["session_started", "session_resumed"]
        resumed = log3.of("session_resumed")[0]
        assert resumed.interrupted_turn is None and resumed.turns_total == 3
        assert same_totals(s3.usage_totals(), after_t3)
        assert sum("Turn interrupted" in str(i.get("content")) for i in s3.history) == 1
        outcomes = [line["outcome"] for line in read_jsonl(sessions_mod.SessionStore.for_workspace(ws)
                                                           .session_dir(s1.session_id) / "history.jsonl")]
        assert outcomes == ["completed", "interrupted", "completed"]
    finally:
        release.set()
        s1.wait(5)


def test_a_resume_after_new_conversation_restores_only_later_turns(open_session):
    s1, _, _ = open_session([[msg("a1")], [msg("a2")]])
    run(s1, "u1")
    s1.new_conversation()
    run(s1, "u2")
    s1.close()
    s2, fake2, log2 = open_session([[msg("a3")]], resume=s1.session_id)
    resumed = log2.of("session_resumed")[0]
    assert resumed.turns_total == 2 and [t["turn_id"] for t in resumed.turns] == ["t2"]
    assert [i["content"] for i in s2.history[1:3]] == ["u2", "a2"] and resumed.restored_items == 3
    run(s2, "u3")
    assert [i["content"] for i in fake2.requests[0]["input"][1:]][::3] == ["u2", "u3"]


# -- failures ----------------------------------------------------------------------------------

def test_a_failing_disk_gives_one_notice_and_the_turns_still_complete(open_session, monkeypatch):
    s, fake, log = open_session([[fn_call("read_file", path="missing.py")], [msg("no file")], [msg("again")]])
    assert s.saved

    def broken(*args, **kwargs):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(sessions_mod, "append_line", broken)
    run(s, "first")
    run(s, "second")
    [notice] = [e for e in log.of("notice") if e.code == "session_save_failed"]
    assert notice.level == "warning" and s.session_id in notice.message and "No space left" in notice.message
    assert len(log.of("turn_completed")) == 2 and not s.saved
    assert [i["content"] for i in s.history if i["role"] == "assistant"] == ["no file", "again"]


def test_a_failing_fsync_is_reported_right_after_the_terminal_event(open_session, monkeypatch):
    s, fake, log = open_session([[msg("a1")], [msg("a2")]])
    run(s, "u1")

    def broken(fd):
        raise OSError(5, "Input/output error")

    monkeypatch.setattr(os, "fsync", broken)
    run(s, "u2")
    types = log.types()
    assert types[-2:] == ["turn_completed", "notice"] and log.events[-1].code == "session_save_failed"
    assert not s.saved and s.history[-2]["content"] == "a2"


def interrupt(open_session, ws):
    """A saved session whose t2 was running when its process "died". Returns (session id, release event)."""
    release = threading.Event()
    s1, fake1, _ = open_session([[msg("one")], Round(output=[msg("never")], block="release", release=release)])
    run(s1, "first")
    s1.start_turn("second")
    wait_blocked(fake1, n=2)
    with s1._lock:
        s1._recorder.close()
    return s1.session_id, release


def test_a_save_failure_on_resume_is_reported_after_the_resume_events(open_session, ws, monkeypatch):
    sid, release = interrupt(open_session, ws)
    try:
        def broken(fd):
            raise OSError(5, "Input/output error")

        monkeypatch.setattr(os, "fsync", broken)            # the recovered turn's history line fails
        s2, _, log2 = open_session([], resume=sid)
        assert log2.types() == ["session_started", "session_resumed", "notice", "notice"]
        assert [e.code for e in log2.of("notice")] == ["turn_interrupted", "session_save_failed"]
        assert not s2.saved
        s2.close()
        monkeypatch.undo()

        def unlockable(path, **kwargs):
            raise PermissionError(13, "Permission denied", str(path))

        s3, _, log3 = open_session([], resume=sid)           # recovers t2 for real this time
        s3.close()
        monkeypatch.setattr(sessions_mod, "_FileLock", unlockable)   # e.g. a read-only folder
        s4, _, log4 = open_session([], resume=sid)
        assert log4.types() == ["session_started", "session_resumed", "notice"]
        assert log4.events[-1].code == "session_save_failed" and not s4.saved
    finally:
        release.set()


def test_totals_rebuilt_from_the_logs_equal_the_live_ones(open_session, ws, store):
    from test_sessions_store import Driver

    config = AgentConfig(workspace=ws, web_search=False, web_search_fee_usd=0.05)
    rec = store.create("s_000000000001", config)
    d = Driver(rec, "s_000000000001", config)
    d.start()
    d.turn("t1", "one")
    d.begin("t2", "dies after a search and a parallel group")
    d.emit(ev.WebAction(turn_id="t2", kind="search", detail="query"))
    for call_id in ("p1", "p2"):
        d.emit(ev.ToolStarted(turn_id="t2", call_id=call_id, name="read_file", group=2, target="b.py", args={}))
    rec.close()

    s, _, _ = open_session([], resume="s_000000000001", web_search_fee_usd=0.05)   # recovers t2
    live = s.usage_totals()
    assert (live["parallel_groups"], live["web_searches"], live["web_cost_usd"]) == (1, 1, 0.05)
    s.close()
    meta_path = store.session_dir("s_000000000001") / "meta.json"
    recorded = store.load("s_000000000001")
    meta_path.unlink()
    rebuilt = store.load("s_000000000001")
    assert rebuilt.totals == recorded.totals and same_totals(rebuilt.totals, live)
    assert rebuilt.info.cost_usd == recorded.info.cost_usd == pytest.approx(0.001 + 0.001 + 0.05)


def test_resume_errors_are_raised_before_anything_is_emitted(open_session, ws, store, monkeypatch):
    s1, _, _ = open_session([[msg("a1")]])
    run(s1, "u1")                                        # s1 holds the lock
    config = AgentConfig(workspace=ws, web_search=False)
    log = EventLog()
    with pytest.raises(SessionInUse):
        Session(config, log, model=FakeModelAdapter(config, []), store=store, resume=s1.session_id)
    with pytest.raises(SessionNotFound):
        Session(config, log, model=FakeModelAdapter(config, []), store=store, resume="s_000000000000")
    with pytest.raises(ValueError):
        Session(config, log, model=FakeModelAdapter(config, []), resume=s1.session_id)
    assert log.events == []
    s1.close()

    import agent_v3.session as session_mod

    def boom(cfg):
        raise RuntimeError("prompt file missing")

    monkeypatch.setattr(session_mod, "build_system_prompt", boom)
    with pytest.raises(RuntimeError):
        Session(config, log, model=FakeModelAdapter(config, []), store=store, resume=s1.session_id)
    monkeypatch.undo()
    assert log.events == []
    s2, _, _ = open_session([], resume=s1.session_id)    # the failed attempt let go of the lock
    assert s2.saved


def test_session_resumed_is_json_safe_and_no_api_key_is_saved(open_session, ws, monkeypatch):
    secret = "sk-test-DO-NOT-SAVE-1234567890"
    monkeypatch.setenv("OPENAI_API_KEY", secret)
    s1, _, log1 = open_session([[msg("a1")]])
    run(s1, "u1")
    s1.close()
    s2, _, log2 = open_session([[msg("a2")]], resume=s1.session_id)
    run(s2, "u2")
    s2.close()
    resumed = log2.of("session_resumed")[0]
    d = json.loads(json.dumps(resumed.to_dict()))
    assert d["type"] == "session_resumed" and ev.event_from_dict(d) == resumed
    for e in log1.events + log2.events:
        json.dumps(e.to_dict())
    for started in log1.of("session_started") + log2.of("session_started"):
        assert all(secret not in str(v) for v in started.config.values())
    folder = SessionStore.for_workspace(ws).session_dir(s1.session_id)
    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
    assert all(secret not in json.dumps(v) for v in meta.values())
    for name in ("events.jsonl", "history.jsonl", "meta.json"):
        assert secret not in (folder / name).read_text(encoding="utf-8")

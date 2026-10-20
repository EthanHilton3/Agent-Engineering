"""Saved-session storage (sessions spec §4, Phase S1): store, recorder, locks, refs, crash safety.

The recorder is driven here the way `Session` will drive it in Phase S2: stamped events, and the history
line committed before the turn's terminal event.
"""
import json
import os
import subprocess
import sys
import threading
import time
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from agent_v3 import events as ev
from agent_v3 import sessions as sessions_mod
from agent_v3.config import AgentConfig
from agent_v3.frontends.eventlog import read_events
from agent_v3.jsonl import append_line, read_jsonl, repair_tail
from agent_v3.sessions import (AmbiguousSession, SessionInUse, SessionNotFound, SessionStore, config_for_resume,
                               session_title)

ROOT = Path(__file__).resolve().parent.parent
T0 = datetime(2026, 10, 16, 9, 0, tzinfo=timezone.utc)


class Driver:
    """Feeds a recorder like Session: seq and ts stamped, text_delta included, commit before the terminal event."""

    clock = 0                                    # shared, so later sessions have later timestamps

    def __init__(self, recorder, session_id, config, seq=0):
        self.rec, self.sid, self.config, self.seq = recorder, session_id, config, seq

    def emit(self, event):
        self.seq += 1
        Driver.clock += 1
        ts = (T0 + timedelta(seconds=Driver.clock)).isoformat(timespec="milliseconds")
        event = replace(event, session_id=self.sid, seq=self.seq, ts=ts)
        self.rec.on_event(event)
        return event

    def start(self):
        return self.emit(ev.SessionStarted(config={**self.config.summary(), "tools": ["read_file"]}))

    def begin(self, tid, message, cost=0.001):
        self.emit(ev.TurnStarted(turn_id=tid, user_message=message))
        self.emit(ev.ModelRoundStarted(turn_id=tid, round=1))
        self.emit(ev.TextDelta(turn_id=tid, round=1, text="partial"))
        self.emit(ev.ToolStarted(turn_id=tid, call_id=f"c_{tid}", name="read_file", group=1, target="a.py",
                                 args={"path": "a.py"}))
        self.emit(ev.ToolCompleted(turn_id=tid, call_id=f"c_{tid}", name="read_file", group=1, ok=True,
                                   summary="1 line", error_code=None, duration_s=0.01, output="x = 1",
                                   metadata={"path": "a.py"}))
        self.emit(ev.ModelRoundCompleted(turn_id=tid, round=1, duration_s=0.5, input_tokens=100, cached_tokens=20,
                                         output_tokens=10, reasoning_tokens=0, cost_usd=cost, function_calls=1))

    def turn(self, tid, message, answer="done", cost=0.001, record=None):
        self.begin(tid, message, cost)
        items = [{"role": "user", "content": message}, {"role": "assistant", "content": answer},
                 {"role": "developer", "content": "Turn record: read a.py."}]
        self.rec.on_commit(turn_id=tid, outcome="completed", user_message=message, text=answer, items=items,
                           record=items if record is None else record)
        stats = {"rounds": 1, "tool_calls": 1, "input_tokens": 100, "cached_tokens": 20, "output_tokens": 10,
                 "model_cost_usd": cost, "web_cost_usd": 0.0, "elapsed_s": 0.7}
        return self.emit(ev.TurnCompleted(turn_id=tid, text=answer, stats=stats))


@pytest.fixture
def ws(tmp_path):
    root = tmp_path / "ws"
    root.mkdir()
    return root


@pytest.fixture
def config(ws):
    return AgentConfig(workspace=ws, web_search=False)


@pytest.fixture
def store(ws):
    return SessionStore.for_workspace(ws)


def new_session(store, config, sid, turns=1, close=True):
    rec = store.create(sid, config)
    d = Driver(rec, sid, config)
    d.start()
    for n in range(1, turns + 1):
        d.turn(f"t{n}", f"question {n} for {sid}")
    if close:
        rec.close()
    return rec, d


def raw_lines(path):
    return [line for line in path.read_bytes().split(b"\n") if line]


# -- jsonl -------------------------------------------------------------------------------------

def test_read_jsonl_skips_a_torn_line_even_inside_a_multibyte_character(tmp_path):
    path = tmp_path / "x.jsonl"
    path.write_bytes(b'{"a": 1}\n' + '{"b": "—'.encode("utf-8")[:-1])
    assert list(read_jsonl(path)) == [{"a": 1}]
    assert list(read_events(path)) == [{"a": 1}]          # the old name still works


def test_repair_tail(tmp_path):
    path = tmp_path / "x.jsonl"
    repair_tail(path)                                       # missing: nothing happens
    assert not path.exists()
    path.write_bytes(b'{"a": 1}\n{"b": 2}\n')
    repair_tail(path)
    assert path.read_bytes() == b'{"a": 1}\n{"b": 2}\n'
    path.write_bytes(b'{"a": 1}\n{"b": ' + b"x" * 10_000)  # the fragment spans several read chunks
    repair_tail(path)
    assert path.read_bytes() == b'{"a": 1}\n'
    path.write_bytes(b'{"torn')
    repair_tail(path)
    assert path.read_bytes() == b""
    with path.open("ab") as f:
        append_line(f, {"c": "é"}, fsync=True)
    assert list(read_jsonl(path)) == [{"c": "é"}]


def test_event_from_dict_round_trips_and_ignores_unknown_keys():
    events = [ev.SessionStarted(config={"model": "m"}), ev.TurnStarted(turn_id="t1", user_message="hi"),
              ev.ToolCompleted(turn_id="t1", call_id="c", name="read_file", group=1, ok=True, summary="s",
                               error_code=None, duration_s=0.1, output="o", metadata={"path": "a.py"}),
              ev.ApprovalResolved(turn_id="t1", request_id="ap_1", decision="allow"),
              ev.TurnCompleted(turn_id="t1", text="done", stats={"rounds": 1}, sources=[{"title": "t", "url": "u"}])]
    for event in events:
        d = json.loads(json.dumps(event.to_dict()))
        assert ev.event_from_dict(d) == event
        assert ev.event_from_dict({**d, "added_in_a_later_version": 1}) == event
    with pytest.raises(ValueError):
        ev.event_from_dict({"type": "no_such_event"})


# -- creation and writing ----------------------------------------------------------------------

def test_nothing_is_written_before_the_first_turn_started(store, config, ws):
    rec = store.create("s_000000000001", config)
    Driver(rec, "s_000000000001", config).start()
    rec.close()
    assert not (ws / ".agent_v3").exists()
    assert store.list() == []


def test_first_turn_creates_the_folder_and_a_gitignore_that_is_never_overwritten(store, config, ws):
    rec = store.create("s_000000000001", config)
    d = Driver(rec, "s_000000000001", config)
    d.start()
    d.emit(ev.TurnStarted(turn_id="t1", user_message="hello"))
    folder = ws / ".agent_v3" / "sessions" / "s_000000000001"
    assert {p.name for p in folder.iterdir()} == {"events.jsonl", "history.jsonl", "meta.json", "lock"}
    assert (ws / ".agent_v3" / ".gitignore").read_text() == "*\n"
    assert [e["type"] for e in read_jsonl(folder / "events.jsonl")] == ["session_started", "turn_started"]
    rec.close()
    (ws / ".agent_v3" / ".gitignore").write_text("# mine\n*\n")
    new_session(store, config, "s_000000000002")
    assert (ws / ".agent_v3" / ".gitignore").read_text() == "# mine\n*\n"


def test_text_delta_is_not_saved_and_lines_are_readable_while_open(store, config):
    rec, d = new_session(store, config, "s_000000000001", close=False)
    saved = list(read_jsonl(store.events_path("s_000000000001")))        # the recorder still has it open
    assert [e["type"] for e in saved] == ["session_started", "turn_started", "model_round_started", "tool_started",
                                          "tool_completed", "model_round_completed", "turn_completed"]
    assert [e["seq"] for e in saved] == [1, 2, 3, 5, 6, 7, 8]          # seq 4 was the text_delta
    assert saved[4]["output"] == "x = 1"                                # tool output is kept in full
    rec.close()


def test_history_line_is_on_disk_before_the_terminal_event(store, config):
    rec = store.create("s_000000000001", config)
    d = Driver(rec, "s_000000000001", config)
    d.start()
    d.begin("t1", "hi")
    items = [{"role": "user", "content": "hi"}, {"type": "reasoning", "id": "rs_1", "encrypted_content": "gAAA"},
             {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "yo"}]}]
    record = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "yo"},
              {"role": "developer", "content": "Turn record: no tool calls."}]
    rec.on_commit(turn_id="t1", outcome="completed", user_message="hi", text="yo", items=items, record=record)
    history = store.session_dir("s_000000000001") / "history.jsonl"
    [line] = list(read_jsonl(history))                                  # before turn_completed is emitted
    assert line["v"] == 1 and line["kind"] == "turn" and line["turn_id"] == "t1" and line["outcome"] == "completed"
    assert line["items"] == items and line["record"] == record          # prune_history=False keeps both forms
    assert "turn_completed" not in [e["type"] for e in read_jsonl(store.events_path("s_000000000001"))]
    rec.on_commit(turn_id="t2", outcome="cancelled", user_message="x", text="", items=record[:1], record=record[:1])
    assert list(read_jsonl(history))[1]["record"] is None               # record equal to items is stored as null
    rec.close()


# -- loading, crash safety, meta ---------------------------------------------------------------

def test_load_restores_counters_and_turn_lines(store, config):
    new_session(store, config, "s_000000000001", turns=2)
    saved = store.load("s_000000000001")
    assert saved.turn_no == 2 and saved.last_seq == 15 and saved.all_turn_lines == 2
    assert [line["user_message"] for line in saved.turn_lines] == ["question 1 for s_000000000001",
                                                                   "question 2 for s_000000000001"]
    assert saved.totals["rounds"] == 2 and saved.totals["model_cost_usd"] == pytest.approx(0.002)
    assert saved.info.title == "question 1 for s_000000000001" and saved.info.turns == 2
    assert saved.info.cost_usd == pytest.approx(0.002) and saved.info.status == "idle"
    assert saved.info.model == config.model and saved.interrupted is None
    assert saved.saved_config == {"model": config.model, "reasoning": "medium", "approval": "ask",
                                  "prune_history": True}


def test_torn_last_lines_are_skipped_on_load_and_repaired_before_appending(store, config):
    new_session(store, config, "s_000000000001")
    folder = store.session_dir("s_000000000001")
    for name in ("events.jsonl", "history.jsonl"):
        with (folder / name).open("ab") as f:
            f.write(b'{"type": "tool_sta')
    saved = store.load("s_000000000001")
    assert saved.all_turn_lines == 1 and saved.last_seq == 8
    saved, rec = store.open("s_000000000001")
    d = Driver(rec, "s_000000000001", config, seq=saved.last_seq)
    d.start()
    d.turn("t2", "again")
    rec.close()
    for name in ("events.jsonl", "history.jsonl"):
        assert len(raw_lines(folder / name)) == len(list(read_jsonl(folder / name)))   # every line parses
    assert store.load("s_000000000001").all_turn_lines == 2


def test_missing_or_corrupt_meta_is_rebuilt_from_the_logs(store, config):
    rec, d = new_session(store, config, "s_000000000001", turns=2, close=False)
    d.begin("t3", "this one dies", cost=0.004)                    # interrupted, then recovered as in §5.3 ...
    rec.close()
    saved, rec = store.open("s_000000000001")
    from agent_v3.sessions import _logged_stats
    rec.on_commit(turn_id="t3", outcome="interrupted", user_message="this one dies", text="",
                  items=[{"role": "user", "content": "this one dies"}], record=None,
                  stats=_logged_stats(saved.interrupted.events, "t3", config.web_search_fee_usd))   # its billed round
    rec.close()
    meta_path = store.session_dir("s_000000000001") / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    expected_info, expected = store.list()[0], store.load("s_000000000001")
    assert meta["turns"] == 3 and meta["cost_usd"] == pytest.approx(0.006) and meta["active_turn"] is None
    for broken in (None, "{not json", '{"v": 1, "session_id": "s_000000000001", "turns": "x"}'):
        if broken is None:
            meta_path.unlink()
        else:
            meta_path.write_text(broken, encoding="utf-8")
        info, saved = store.list()[0], store.load("s_000000000001")
        assert info == expected_info
        assert (saved.info, saved.totals, saved.last_seq, saved.turn_no) == \
               (expected.info, expected.totals, expected.last_seq, expected.turn_no)
        assert saved.totals["model_cost_usd"] == pytest.approx(0.006) and saved.totals["rounds"] == 3


def test_a_meta_behind_the_logs_is_rebuilt(store, config):
    rec, d = new_session(store, config, "s_000000000001", close=False)
    meta_before = (store.session_dir("s_000000000001") / "meta.json").read_bytes()
    d.turn("t2", "second")
    rec.close()
    (store.session_dir("s_000000000001") / "meta.json").write_bytes(meta_before)   # crash before the meta write
    saved = store.load("s_000000000001")
    assert saved.info.turns == 2 and saved.totals["rounds"] == 2


def test_a_commit_without_its_terminal_event_keeps_its_costs_when_meta_is_rebuilt(store, config):
    rec, d = new_session(store, config, "s_000000000001", turns=2, close=False)
    d.begin("t3", "dies right after its commit", cost=0.004)
    items = [{"role": "user", "content": "dies right after its commit"}, {"role": "assistant", "content": "ok"}]
    rec.on_commit(turn_id="t3", outcome="completed", user_message="dies right after its commit", text="ok",
                  items=items, record=items)
    rec.close()                                             # no turn_completed, and meta.json still says 2 turns
    meta_path = store.session_dir("s_000000000001") / "meta.json"
    for missing in (False, True):
        if missing:
            meta_path.unlink()
        saved = store.load("s_000000000001")
        assert saved.interrupted is None and saved.info.turns == 3
        assert (saved.totals["rounds"], saved.totals["tool_calls"]) == (3, 3)
        assert saved.totals["model_cost_usd"] == pytest.approx(0.006) and saved.info.cost_usd == pytest.approx(0.006)
    assert store.list()[0].cost_usd == pytest.approx(0.006)


def test_a_rebuilt_meta_takes_prune_history_from_the_last_turn_line(store, config):
    full = replace(config, prune_history=False)
    rec = store.create("s_000000000001", full)
    d = Driver(rec, "s_000000000001", full)
    d.start()
    d.begin("t1", "fails")                                  # its line has record: null, like every non-completed turn
    items = [{"role": "user", "content": "fails"}, {"role": "developer", "content": "Turn failed (server_error)."}]
    rec.on_commit(turn_id="t1", outcome="failed", user_message="fails", text="", items=items, record=None)
    d.emit(ev.TurnFailed(turn_id="t1", error_code="server_error", message="boom", stats={"rounds": 1}))
    rec.close()
    meta_path = store.session_dir("s_000000000001") / "meta.json"
    meta_path.unlink()
    assert store.load("s_000000000001").saved_config["prune_history"] is False

    saved, rec = store.open("s_000000000001", config)        # resumed with pruning on: the last line decides
    d = Driver(rec, "s_000000000001", config, seq=saved.last_seq)
    d.start()
    d.turn("t2", "two")
    rec.close()
    meta_path.unlink()
    assert store.load("s_000000000001").saved_config["prune_history"] is True


def test_load_reports_an_interrupted_turn(store, config):
    rec, d = new_session(store, config, "s_000000000001", close=False)
    d.begin("t2", "Refactor report.py")
    rec.close()                                             # the process "died" mid-turn
    saved = store.load("s_000000000001")
    assert saved.interrupted.turn_id == "t2" and saved.interrupted.user_message == "Refactor report.py"
    assert [e["type"] for e in saved.interrupted.events] == ["turn_started", "model_round_started", "tool_started",
                                                             "tool_completed", "model_round_completed"]
    assert ev.event_from_dict(saved.interrupted.events[3]).metadata == {"path": "a.py"}
    assert saved.turn_no == 2 and saved.all_turn_lines == 1 and saved.info.status == "interrupted"
    assert saved.totals["rounds"] == 1                      # the recovery (S2) adds t2's round, not the store
    assert store.list()[0].status == "interrupted"


def test_open_records_the_owner_and_saves_new_settings_only_from_the_next_turn(store, config):
    new_session(store, config, "s_000000000001")
    meta_path = store.session_dir("s_000000000001") / "meta.json"
    json_meta = json.loads(meta_path.read_text(encoding="utf-8"))
    json_meta["owner_pid"] = 1
    meta_path.write_text(json.dumps(json_meta), encoding="utf-8")
    other = replace(config, model="gpt-5.6-sol", reasoning="high", approval="full-auto")
    saved, rec = store.open("s_000000000001", other)
    assert saved.saved_config["model"] == config.model
    assert json.loads(meta_path.read_text(encoding="utf-8"))["owner_pid"] == os.getpid()
    assert store.load("s_000000000001").info.model == config.model         # a bare open changes nothing
    d = Driver(rec, "s_000000000001", other, seq=saved.last_seq)
    d.start()
    d.turn("t2", "next")
    rec.close()
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert (meta["model"], meta["reasoning"], meta["approval"]) == ("gpt-5.6-sol", "high", "full-auto")


# -- listing and refs --------------------------------------------------------------------------

def test_listing_order_limit_and_statuses(store, config):
    new_session(store, config, "s_00000000000a")
    rec, d = new_session(store, config, "s_00000000000b", close=False)
    d.begin("t2", "dies")
    rec.close()
    held, _ = new_session(store, config, "s_00000000000c", close=False)
    rows = store.list()
    assert [(r.session_id, r.status) for r in rows] == [
        ("s_00000000000c", "in_use"), ("s_00000000000b", "interrupted"), ("s_00000000000a", "idle")]
    assert [r.session_id for r in store.list(limit=2)] == ["s_00000000000c", "s_00000000000b"]
    assert rows[1].turns == 1 and rows[0].title == "question 1 for s_00000000000c"
    held.close()
    assert store.list()[0].status == "idle"


def test_listing_and_loading_never_create_a_lock_file(store, config):
    new_session(store, config, "s_000000000001")
    lock = store.session_dir("s_000000000001") / "lock"
    lock.unlink()                                           # e.g. a copied or restored session folder
    assert store.list()[0].status == "idle" and store.load("s_000000000001").info.status == "idle"
    assert store.resolve("latest") == "s_000000000001"
    assert not lock.exists()
    _, rec = store.open("s_000000000001")                   # opening creates it
    assert lock.exists() and store.list()[0].status == "in_use"
    rec.close()


def test_listing_ignores_other_folders_and_an_empty_store(store, config, ws):
    assert store.list() == []
    new_session(store, config, "s_000000000001")
    (store.root / "not-a-session").mkdir()
    (store.root / "s_000000000002").mkdir()                  # no logs: skipped
    assert [r.session_id for r in store.list()] == ["s_000000000001"]


def test_resolve_refs(store, config):
    assert pytest.raises(SessionNotFound, store.resolve, "latest")
    for sid in ("s_aaaa11112222", "s_aaaa33334444", "s_bbbb00001111"):
        new_session(store, config, sid)
    assert store.resolve("s_bbbb00001111") == "s_bbbb00001111"
    assert store.resolve("bbbb") == store.resolve("s_bbbb") == store.resolve(" BBBB0 ") == "s_bbbb00001111"
    assert store.resolve("aaaa1") == "s_aaaa11112222"
    assert store.resolve("latest") == "s_bbbb00001111"
    with pytest.raises(AmbiguousSession) as amb:
        store.resolve("aaaa")
    assert amb.value.matches == ["s_aaaa11112222", "s_aaaa33334444"]
    assert "s_aaaa11112222" in str(amb.value)
    for ref in ("cccc", "bbb", "s_bb", ""):
        with pytest.raises(SessionNotFound):
            store.resolve(ref)
    with pytest.raises(SessionNotFound):
        store.load("s_cccc00000000")


def test_session_title():
    assert session_title("\n  \n  Fix   the\tfailing test\nsecond line") == "Fix the failing test"
    long = session_title("x" * 100)
    assert len(long) == 60 and long.endswith("…")
    assert session_title("   ") == ""


# -- locks and delete --------------------------------------------------------------------------

def test_a_second_open_in_the_same_process_is_in_use(store, config):
    new_session(store, config, "s_000000000001")
    saved, rec = store.open("s_000000000001")
    with pytest.raises(SessionInUse) as err:
        store.open("s_000000000001")
    assert err.value.owner_pid == os.getpid() and str(os.getpid()) in str(err.value)
    rec.close()
    rec.close()                                             # idempotent
    _, again = store.open("s_000000000001")
    again.close()


def test_open_waits_out_a_momentary_status_probe(store, config):
    new_session(store, config, "s_000000000001")
    probe = sessions_mod._FileLock(store.session_dir("s_000000000001") / "lock")   # another process's list()
    timer = threading.Timer(0.03, probe.close)
    timer.start()
    try:
        _, rec = store.open("s_000000000001")
    finally:
        timer.join()
    started = time.monotonic()
    with pytest.raises(SessionInUse):                       # a lock that stays held still fails, after ~100 ms
        store.open("s_000000000001")
    assert time.monotonic() - started >= 0.07
    rec.close()


def test_a_new_session_holds_its_lock_from_the_first_turn(store, config):
    rec, _ = new_session(store, config, "s_000000000001", close=False)
    with pytest.raises(SessionInUse):
        store.open("s_000000000001")
    rec.close()


CHILD = """
import sys, time
from agent_v3.sessions import SessionStore
saved, rec = SessionStore(sys.argv[1]).open(sys.argv[2])
print("locked", flush=True)
time.sleep(120)
"""


def test_a_lock_held_by_a_killed_process_is_released(store, config):
    new_session(store, config, "s_000000000001")
    child = subprocess.Popen([sys.executable, "-c", CHILD, str(store.root), "s_000000000001"], cwd=ROOT,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        assert child.stdout.readline().strip() == "locked", child.stderr.read()
        with pytest.raises(SessionInUse) as err:
            store.open("s_000000000001")
        assert err.value.owner_pid == child.pid
        assert store.list()[0].status == "in_use"
        with pytest.raises(SessionInUse):
            store.delete("s_000000000001")
    finally:
        child.kill()                                        # a hard kill: no cleanup code runs in the child
        child.wait(10)
        child.stdout.close()
        child.stderr.close()
    deadline = time.monotonic() + 5
    while True:
        try:
            _, rec = store.open("s_000000000001")
            break
        except SessionInUse:
            if time.monotonic() > deadline:
                raise
            time.sleep(0.05)
    rec.close()


def test_delete_refuses_an_open_session_and_removes_only_the_named_one(store, config):
    new_session(store, config, "s_000000000001")
    new_session(store, config, "s_000000000002")
    _, rec = store.open("s_000000000001")
    with pytest.raises(SessionInUse):
        store.delete("s_000000000001")
    store.delete("s_000000000002")
    assert [p.name for p in store.root.iterdir()] == ["s_000000000001"]
    assert [r.session_id for r in store.list()] == ["s_000000000001"]
    rec.close()
    store.delete("s_000000000001")
    assert list(store.root.iterdir()) == []
    with pytest.raises(SessionNotFound):
        store.delete("s_000000000001")


def test_delete_removes_the_logs_before_it_releases_the_lock(store, config, monkeypatch):
    new_session(store, config, "s_000000000001")
    folder = store.session_dir("s_000000000001")
    real_close, seen = sessions_mod._FileLock.close, []

    def close(lock):                                        # another process opens it the moment the lock is free
        real_close(lock)
        if not seen:
            seen.append("released")
            try:
                seen.append(store.open("s_000000000001")[1])
            except SessionNotFound as e:
                seen.append(e)

    monkeypatch.setattr(sessions_mod._FileLock, "close", close)
    try:
        store.delete("s_000000000001")
    finally:
        if len(seen) > 1 and not isinstance(seen[1], Exception):
            seen[1].close()
    assert isinstance(seen[1], SessionNotFound)             # nothing left to open
    assert not folder.exists() and store.list() == []


# -- resets and failures -----------------------------------------------------------------------

def test_reset_lines_follow_a_turn_and_load_returns_only_later_turns(store, config):
    rec = store.create("s_000000000001", config)
    d = Driver(rec, "s_000000000001", config)
    d.start()
    rec.on_reset()                                          # nothing to reset: no folder, no line
    assert not store.root.exists()
    d.turn("t1", "one")
    d.turn("t2", "two")
    rec.on_reset()
    rec.on_reset()                                          # no turn since the last reset: skipped
    d.turn("t3", "three")
    rec.close()
    lines = list(read_jsonl(store.session_dir("s_000000000001") / "history.jsonl"))
    assert [line["kind"] for line in lines] == ["turn", "turn", "reset", "turn"]
    saved = store.load("s_000000000001")
    assert [line["turn_id"] for line in saved.turn_lines] == ["t3"]
    assert saved.all_turn_lines == 3 and saved.info.turns == 3 and saved.turn_no == 3

    saved, rec = store.open("s_000000000001")               # turn lines after the reset: a reset is written
    rec.on_reset()
    rec.on_reset()
    rec.close()
    assert store.load("s_000000000001").turn_lines == []
    assert [line["kind"] for line in read_jsonl(store.session_dir("s_000000000001") / "history.jsonl")][-2:] == \
           ["turn", "reset"]


def test_an_unwritable_folder_disables_the_recorder_without_raising(tmp_path, config):
    blocker = tmp_path / "file"
    blocker.write_text("not a folder")
    store = SessionStore(blocker / "sessions")
    rec = store.create("s_000000000001", config)
    d = Driver(rec, "s_000000000001", config)
    d.start()
    assert rec.healthy
    d.turn("t1", "hello")                                   # every call after the failure is a no-op
    rec.on_reset()
    assert not rec.healthy and "s_000000000001" in rec.error and str(blocker) in rec.error
    rec.close()
    assert store.list() == []


@pytest.mark.skipif(os.name == "nt", reason="POSIX permissions")
def test_posix_files_are_private(store, config):
    new_session(store, config, "s_000000000001")
    folder = store.session_dir("s_000000000001")
    assert folder.stat().st_mode & 0o777 == 0o700
    for name in ("events.jsonl", "history.jsonl", "meta.json", "lock"):
        assert (folder / name).stat().st_mode & 0o777 == 0o600


# -- settings on resume ------------------------------------------------------------------------

def test_config_for_resume_restores_model_and_reasoning_but_never_approval(store, config):
    saved_cfg = replace(config, model="gpt-5.6-sol", reasoning="high", approval="full-auto")
    new_session(store, saved_cfg, "s_000000000001")
    info = store.load("s_000000000001").info
    launch = replace(config, approval="ask")
    out = config_for_resume(launch, info, set())
    assert (out.model, out.reasoning, out.approval) == ("gpt-5.6-sol", "high", "ask")
    out = config_for_resume(launch, info, {"model"})
    assert (out.model, out.reasoning) == (config.model, "high")
    out = config_for_resume(launch, info, {"model", "reasoning"})
    assert (out.model, out.reasoning) == (config.model, config.reasoning)
    assert out is not launch and launch.model == config.model
    bad = replace(info, reasoning="ludicrous", model="")
    out = config_for_resume(launch, bad, set())
    assert (out.model, out.reasoning) == (config.model, config.reasoning)

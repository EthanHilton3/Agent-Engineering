import json
import threading
import time

import httpx
import openai
import pytest

from conftest import EventLog, FakeModelAdapter, Round, fn_call, fn_call_raw, msg, reasoning_item, usage, web_call

from agent_v3.approvals import Decision
from agent_v3.config import AgentConfig
from agent_v3.pricing import PRICING
from agent_v3.session import Busy, Session


def run(session, text="go", timeout=10):
    tid = session.start_turn(text)
    assert session.wait(timeout), "turn did not finish"
    return tid


def kinds(items):
    return [i.get("type") or f"msg:{i['role']}" for i in items]


def outputs(request):
    return {i["call_id"]: i["output"] for i in request["input"] if i.get("type") == "function_call_output"}


def bad_request(message, param=None):
    req = httpx.Request("POST", "https://api.openai.com/v1/responses")
    return openai.BadRequestError(message, response=httpx.Response(400, request=req),
                                  body={"message": message, "param": param, "type": "invalid_request_error"})


def ws_file(session, rel, text):
    p = session.workspace.root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


# --- basic turns -----------------------------------------------------------------------------

def test_no_tool_answer(make_session):
    s, fake, log = make_session([[msg("Hello there, friend")]])
    tid = run(s, "hi")
    assert log.types() == ["session_started", "turn_started", "model_round_started", "text_delta", "text_delta",
                           "text_delta", "model_round_completed", "turn_completed"]
    done = log.of("turn_completed")[0]
    assert done.turn_id == tid and done.text == "Hello there, friend" and done.stop_reason == "done"
    assert "".join(e.text for e in log.of("text_delta")) == "Hello there, friend"
    assert [e.seq for e in log.events] == list(range(1, len(log.events) + 1))
    assert {e.session_id for e in log.events} == {s.session_id} and all(e.ts for e in log.events)
    started = log.of("session_started")[0]
    assert started.protocol_version == 1 and len(started.config["tools"]) == 9

    [req] = fake.requests
    assert req["tool_choice"] == "auto" and req["store"] is False and req["parallel_tool_calls"] is True
    assert req["include"] == ["reasoning.encrypted_content"]           # web search is off in this fixture
    assert req["prompt_cache_key"] == f"agent_v3:{s.session_id}"
    assert [t["type"] for t in req["tools"]] == ["function"] * 9
    assert kinds(req["input"]) == ["msg:system", "msg:user"] and req["input"][0]["content"] == s.system_prompt
    assert not s.busy


def test_multi_round_tool_use(make_session):
    s, fake, log = make_session([
        [fn_call("read_file", path="a.py")],
        [fn_call("search_text", pattern="x")],
        [msg("x is 1")],
    ])
    ws_file(s, "a.py", "x = 1\n")
    run(s)
    assert len(fake.requests) == 3
    second = fake.requests[1]["input"]
    assert kinds(second)[-2:] == ["function_call", "function_call_output"]
    assert "1| x = 1" in second[-1]["output"]
    third = fake.requests[2]["input"]
    assert kinds(third)[-4:] == ["function_call", "function_call_output", "function_call", "function_call_output"]
    stats = log.of("turn_completed")[0].stats
    assert stats["rounds"] == 3 and stats["tool_calls"] == 2
    assert s.history[-1]["content"].startswith("Turn record: read a.py")


def test_parallel_group_events_share_group(make_session):
    s, fake, log = make_session([
        [fn_call("read_file", path="a.py"), fn_call("read_file", path="b.py"), fn_call("glob_files", pattern="*.py"),
         fn_call("list_dir", path=".")],
        [msg("done")],
    ])
    ws_file(s, "a.py", "a\n")
    ws_file(s, "b.py", "b\n")
    run(s)
    groups = {e.call_id: e.group for e in log.of("tool_started")}
    assert len(groups) == 4 and len(set(groups.values())) == 1
    assert {e.group for e in log.of("tool_completed")} == set(groups.values())
    assert log.of("turn_completed")[0].stats["parallel_groups"] == 1
    # outputs come back in the model's call order
    ids = [i["call_id"] for i in fake.requests[1]["input"] if i.get("type") == "function_call_output"]
    assert ids == [i["call_id"] for i in fake.requests[1]["input"] if i.get("type") == "function_call"]


def test_invalid_arguments_round_trip(make_session):
    bad = fn_call_raw("read_file", '{"path": "a.py"', call_id="bad")
    missing = fn_call_raw("read_file", '{"start_line": 1}', call_id="missing")
    unknown = fn_call_raw("delete_everything", "{}", call_id="unknown")
    s, fake, log = make_session([[bad, missing, unknown], [msg("sorry")]])
    run(s)
    out = outputs(fake.requests[1])
    assert out["bad"].startswith("Error (invalid_arguments): Arguments are not valid JSON")
    assert out["missing"].startswith("Error (invalid_arguments): path: Field required")
    assert out["unknown"].startswith("Error (unknown_tool): No tool named 'delete_everything'")
    assert log.of("turn_completed")[0].text == "sorry"


def test_repeated_failure_guard(make_session):
    s, fake, log = make_session([
        [fn_call("read_file", call_id="c1", path="nope.py")],
        [fn_call("read_file", call_id="c2", path="nope.py")],
        [msg("giving up")],
    ])
    run(s)
    assert outputs(fake.requests[1])["c1"].startswith("Error (not_found)")
    assert outputs(fake.requests[2])["c2"].startswith("Error (repeated_failure): This identical call already failed")


def test_repeated_failure_memory_is_per_turn(make_session):
    s, fake, log = make_session([
        [fn_call("read_file", call_id="c1", path="nope.py")], [msg("missing")],
        [fn_call("read_file", call_id="c2", path="nope.py")], [msg("still missing")],
    ])
    run(s)
    run(s)
    assert outputs(fake.requests[3])["c2"].startswith("Error (not_found)")


def test_conflict_is_not_repeat_guarded_so_a_read_unblocks_the_same_write(make_session):
    write = dict(path="a.py", content="x = 2\n", overwrite=True)
    s, fake, log = make_session([
        [fn_call("write_file", call_id="w1", **write)],
        [fn_call("read_file", call_id="r1", path="a.py")],
        [fn_call("write_file", call_id="w2", **write)],
        [msg("done")],
    ], approval="full-auto")
    p = ws_file(s, "a.py", "x = 1\n")
    run(s)
    assert outputs(fake.requests[1])["w1"].startswith("Error (conflict): Read the current file")
    assert outputs(fake.requests[3])["w2"].startswith("Overwrote a.py")
    assert p.read_text() == "x = 2\n"


# --- approvals -------------------------------------------------------------------------------

def edit_call(path="a.py", old="x = 1", new="x = 2", call_id=None):
    return fn_call("edit_files", call_id=call_id, edits=[{"path": path, "old_text": old, "new_text": new}])


def test_approval_allow(make_session):
    s, fake, log = make_session([[edit_call()], [msg("edited")]])
    p = ws_file(s, "a.py", "x = 1\n")
    s.start_turn("change x")
    req = log.wait_for("approval_requested").request
    assert req["kind"] == "edit" and req["title"] == "Edit 1 file" and "-x = 1" in req["diff"]
    assert req["reason"] == "edits need approval in 'ask' mode"
    assert s.busy and s.approvals.pending.request_id == req["request_id"]
    time.sleep(0.3)
    assert s.respond_approval(req["request_id"], Decision.ALLOW) is True
    assert s.wait(5)
    resolved = log.of("approval_resolved")[0]
    assert (resolved.request_id, resolved.decision, resolved.by) == (req["request_id"], "allow", "user")
    assert p.read_text() == "x = 2\n"
    stats = log.of("turn_completed")[0].stats
    assert stats["approval_wait_s"] >= 0.3 and stats["tool_wait_s"] < 0.25
    assert s.respond_approval(req["request_id"], "allow") is False       # no longer pending


def test_approval_reject_with_feedback(make_session):
    s, fake, log = make_session([[edit_call(call_id="e1")], [msg("ok, leaving it")]])
    p = ws_file(s, "a.py", "x = 1\n")
    s.start_turn("change x")
    req = log.wait_for("approval_requested").request
    s.respond_approval(req["request_id"], "reject", "rename y instead")
    assert s.wait(5)
    assert p.read_text() == "x = 1\n"
    assert outputs(fake.requests[1])["e1"] == ("Error (rejected): The user rejected this edit.\n"
                                               "User feedback: rename y instead")
    assert log.of("approval_resolved")[0].feedback == "rename y instead"
    assert "user rejected edit_files a.py" in s.history[-1]["content"]


def test_approval_allow_session_for_edits(make_session):
    s, fake, log = make_session([
        [edit_call()], [edit_call(old="y = 1", new="y = 2", path="b.py")], [msg("both")],
        [edit_call(old="x = 2", new="x = 3")], [msg("again")],
    ])
    a, b = ws_file(s, "a.py", "x = 1\n"), ws_file(s, "b.py", "y = 1\n")
    s.start_turn("edit")
    req = log.wait_for("approval_requested").request
    s.respond_approval(req["request_id"], Decision.ALLOW_SESSION)
    assert s.wait(5)
    run(s, "edit again")                                    # later turns stay auto too
    assert len(log.of("approval_requested")) == 1
    assert (a.read_text(), b.read_text()) == ("x = 3\n", "y = 2\n")


def test_approval_allow_session_for_commands_is_exact_string(make_session):
    s, fake, log = make_session([
        [fn_call("run_command", command="echo hi")],
        [fn_call("run_command", command="echo hi")],
        [fn_call("run_command", command="echo bye", call_id="bye")],
        [msg("done")],
    ])
    s.start_turn("run")
    req = log.wait_for("approval_requested").request
    assert req["kind"] == "command" and req["command"] == "echo hi"
    s.respond_approval(req["request_id"], "allow_session")
    req2 = log.wait_for("approval_requested", n=2).request         # "echo bye" is a different command
    assert req2["command"] == "echo bye"
    s.respond_approval(req2["request_id"], "allow")
    assert s.wait(10)
    assert outputs(fake.requests[3])["bye"].startswith("Exit code 0")
    assert "ran `echo hi` (exit 0), `echo hi` (exit 0), `echo bye` (exit 0)" in s.history[-1]["content"]


def test_approvals_are_handed_off_one_at_a_time(make_session):
    s, fake, log = make_session([
        [edit_call(call_id="e1"), edit_call(path="b.py", old="y = 1", new="y = 2", call_id="e2")],
        [msg("done")],
    ])
    ws_file(s, "a.py", "x = 1\n")
    ws_file(s, "b.py", "y = 1\n")
    s.start_turn("two edits")
    first = log.wait_for("approval_requested").request
    time.sleep(0.2)
    assert len(log.of("approval_requested")) == 1                  # the second edit waits its turn
    s.respond_approval(first["request_id"], "allow")
    second = log.wait_for("approval_requested", n=2).request
    assert second["request_id"] != first["request_id"]
    assert s.respond_approval(first["request_id"], "allow") is False
    s.respond_approval(second["request_id"], "allow")
    assert s.wait(5)
    seq = [(e.type, getattr(e, "request_id", None) or e.request["request_id"]) for e in log.events
           if e.type.startswith("approval_")]
    assert seq == [("approval_requested", first["request_id"]), ("approval_resolved", first["request_id"]),
                   ("approval_requested", second["request_id"]), ("approval_resolved", second["request_id"])]


def test_auto_edit_mode_and_full_auto_always_ask(make_session):
    s, fake, log = make_session([
        [edit_call(), fn_call("run_command", command="git push origin main", call_id="push")],
        [msg("done")],
    ], approval="full-auto")
    p = ws_file(s, "a.py", "x = 1\n")
    s.start_turn("edit and push")
    req = log.wait_for("approval_requested").request
    assert req["kind"] == "command" and "always-ask pattern (git push)" in req["reason"]
    assert p.read_text() == "x = 2\n"                                   # the edit was auto-approved
    s.respond_approval(req["request_id"], "reject")
    assert s.wait(5)
    assert outputs(fake.requests[1])["push"] == "Error (rejected): The user rejected this command."


def test_approval_wait_is_excluded_from_max_turn_seconds(make_session):
    s, fake, log = make_session([[edit_call()], [msg("done")]], max_turn_seconds=1)
    ws_file(s, "a.py", "x = 1\n")
    s.start_turn("edit")
    req = log.wait_for("approval_requested").request
    time.sleep(1.2)
    s.respond_approval(req["request_id"], "allow")
    assert s.wait(5)
    assert log.of("turn_completed")[0].stop_reason == "done"


# --- cancellation ----------------------------------------------------------------------------

def wait_blocked(fake, n=1, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if len(fake.streams) >= n and fake.streams[n - 1].blocked.is_set():
            return fake.streams[n - 1]
        time.sleep(0.01)
    raise AssertionError("fake stream never blocked")


def test_cancel_during_model_wait_frees_frontend_and_discards_late_worker(make_session):
    release = threading.Event()
    s, fake, log = make_session([
        Round(output=[msg("late answer that must be discarded")], block="release", release=release),
        [msg("second turn answer")],
    ])
    t1 = s.start_turn("slow question")
    wait_blocked(fake)                       # the worker is stuck in a network read that ignores close()
    t0 = time.monotonic()
    s.cancel()
    assert time.monotonic() - t0 < 0.5
    assert not s.busy and s.wait(0)
    cancelled = log.of("turn_cancelled")[0]
    assert cancelled.turn_id == t1 and log.types()[-1] == "turn_cancelled"
    assert s.history[-2:] == [{"role": "user", "content": "slow question"},
                              {"role": "developer", "content": "Turn cancelled by user after: no tool calls."}]

    t2 = s.start_turn("next question")       # allowed while the abandoned worker is still blocked
    assert s.wait(5)
    release.set()                            # the late worker wakes up and must change nothing
    time.sleep(0.3)
    after_cancel = [e for e in log.events if e.seq > cancelled.seq]
    assert all(e.turn_id == t2 for e in after_cancel)
    assert log.of("turn_completed")[0].text == "second turn answer"
    assert not any("late answer" in str(m.get("content")) for m in s.history)
    assert kinds(fake.requests[1]["input"]) == ["msg:system", "msg:user", "msg:developer", "msg:user"]
    assert s.usage_totals()["rounds"] == 1


def test_cancel_closes_a_blocked_stream_without_retrying(make_session):
    s, fake, log = make_session([Round(output=[msg("never")], block="cancel")])
    s.start_turn("q")
    stream = wait_blocked(fake)
    s.cancel()
    assert stream.closed.is_set() and not s.busy
    time.sleep(0.3)
    assert len(fake.requests) == 1 and not log.of("model_retry") and not log.of("turn_failed")


def test_cancel_during_approval(make_session):
    s, fake, log = make_session([[edit_call()], [msg("unused")], [msg("fresh")]])
    p = ws_file(s, "a.py", "x = 1\n")
    s.start_turn("edit")
    req = log.wait_for("approval_requested").request
    s.cancel()
    assert not s.busy
    resolved = log.of("approval_resolved")[0]
    assert (resolved.decision, resolved.by) == ("reject", "cancel")
    assert log.types()[-2:] == ["approval_resolved", "turn_cancelled"]
    assert s.respond_approval(req["request_id"], "allow") is False
    time.sleep(0.2)
    assert p.read_text() == "x = 1\n" and s.approvals.pending is None
    assert len(fake.requests) == 1                                    # the stale worker made no new request
    fake.index = 2
    run(s, "something else")
    assert log.of("turn_completed")[0].text == "fresh"


def test_cancel_right_after_approval_writes_nothing(tmp_path):
    """A stdio/CLI client sends approval_response allow and then cancel straight away. When the cancel
    lands before the approved tool resumes, the tool must not write: cancel() has already committed
    a turn record without the edit, and the worker's ToolCompleted is dropped as stale."""
    cfg = AgentConfig(workspace=tmp_path, web_search=False)
    log, holder = EventLog(), {}

    def on_event(ev):
        log(ev)
        if ev.type == "approval_resolved" and ev.decision == "allow":
            holder["session"]._active.cancel.cancel()      # the cancel arrives before the worker wakes

    fake = FakeModelAdapter(cfg, [[edit_call()], [msg("unused")]])
    s = holder["session"] = Session(cfg, on_event, model=fake)
    p = ws_file(s, "a.py", "x = 1\n")
    tid = s.start_turn("edit")
    worker = next(t for t in threading.enumerate() if t.name == f"agent-{tid}")
    req = log.wait_for("approval_requested").request
    assert s.respond_approval(req["request_id"], "allow") is True
    s.cancel()
    worker.join(5)
    assert not worker.is_alive()
    assert p.read_text() == "x = 1\n"
    assert log.types()[-1] == "turn_cancelled" and not log.of("tool_completed")
    assert "edited" not in s.history[-1]["content"] and len(fake.requests) == 1
    s.close()


def test_cancel_during_command_kills_it(make_session):
    s, fake, log = make_session([[fn_call("run_command", command="sleep 30")], [msg("unused")]],
                                approval="full-auto")
    s.start_turn("sleep")
    log.wait_for("tool_started")
    time.sleep(0.3)
    t0 = time.monotonic()
    s.cancel()
    assert time.monotonic() - t0 < 3 and not s.busy
    assert "Turn cancelled by user after" in s.history[-1]["content"]


def test_truncated_outputs_in_different_rounds_keep_separate_logs(make_session):
    s, fake, log = make_session([
        [fn_call("run_command", command="seq 1 2000")],
        [fn_call("run_command", command="seq 5001 7000")],
        [msg("done")],
    ], approval="full-auto", tool_output_max_chars=1000)
    run(s)
    paths = [e.metadata["full_output_path"] for e in log.of("tool_completed")]
    assert len(set(paths)) == 2
    first, second = ((s.workspace.root / p).read_text(encoding="utf-8") for p in paths)
    assert first.startswith("1\n") and second.startswith("5001\n")


def test_cancel_when_idle_is_a_noop(make_session):
    s, fake, log = make_session([[msg("a")]])
    s.cancel()
    run(s)
    s.cancel()
    assert log.types().count("turn_cancelled") == 0


# --- budgets ---------------------------------------------------------------------------------

def test_max_rounds_ends_with_summary_request(make_session):
    s, fake, log = make_session([
        [fn_call("list_dir", path=".")], [fn_call("glob_files", pattern="*")], [fn_call("list_dir", path=".")],
        [msg("Summary: listed files; nothing verified.")],
    ], max_rounds=3)
    run(s)
    assert [r["tool_choice"] for r in fake.requests] == ["auto", "auto", "auto", "none"]
    last = fake.requests[3]["input"][-1]
    assert last["role"] == "developer" and last["content"].startswith("Budget reached (max_rounds). Do not call tools.")
    assert kinds(fake.requests[3]["input"])[-3:] == ["function_call", "function_call_output", "msg:developer"]
    done = log.of("turn_completed")[0]
    assert done.stop_reason == "max_rounds" and done.stats["rounds"] == 4
    assert done.text.startswith("Summary:")
    assert [n.code for n in log.of("notice")] == ["rounds_low"]


def test_max_cost_stops_before_next_round(make_session):
    s, fake, log = make_session([
        Round(output=[fn_call("list_dir", path=".")], usage=usage(inp=100_000, out=0)),   # $0.02 on luna
        [msg("Stopped for budget.")],
    ], max_turn_cost_usd=0.01)
    run(s)
    assert [r["tool_choice"] for r in fake.requests] == ["auto", "none"]
    done = log.of("turn_completed")[0]
    assert done.stop_reason == "max_cost" and done.stats["model_cost_usd"] >= 0.02


def test_max_time(make_session):
    s, fake, log = make_session([[msg("out of time")]], max_turn_seconds=0)
    run(s)
    assert fake.requests[0]["tool_choice"] == "none"
    assert log.of("turn_completed")[0].stop_reason == "max_time"


def test_summary_request_never_leaves_an_unanswered_call(make_session):
    s, fake, log = make_session([[fn_call("list_dir", path=".")], [msg("partial"), fn_call("list_dir", path=".")]],
                                max_rounds=1, prune_history=False)
    run(s)
    calls = [i for i in s.history if i.get("type") == "function_call"]
    outs = [i for i in s.history if i.get("type") == "function_call_output"]
    assert len(calls) == len(outs) == 1


# --- history pruning -------------------------------------------------------------------------

def tool_turn_rounds():
    return [
        [reasoning_item(), fn_call("read_file", path="a.py"), fn_call("run_command", command="echo ok")],
        [reasoning_item(), edit_call()],
        [reasoning_item(), msg("Changed x to 2.")],
    ]


def test_pruning_keeps_only_user_assistant_developer(make_session):
    s, fake, log = make_session([*tool_turn_rounds(), [msg("second answer")]], approval="full-auto")
    ws_file(s, "a.py", "x = 1\n")
    run(s, "change x")
    assert kinds(s.history) == ["msg:system", "msg:user", "msg:assistant", "msg:developer"]
    assert s.history[2]["content"] == "Changed x to 2."
    record = s.history[3]["content"]
    assert record == "Turn record: read a.py; edited a.py (+1 −1); ran `echo ok` (exit 0)."
    run(s, "and now?")
    nxt = fake.requests[-1]["input"]
    assert kinds(nxt) == ["msg:system", "msg:user", "msg:assistant", "msg:developer", "msg:user"]
    assert not any(i.get("type") in ("function_call", "function_call_output", "reasoning", "web_search_call")
                   for i in nxt)
    # the prefix through the previous turn is byte-identical (cache-stable)
    assert nxt[:1] == fake.requests[0]["input"][:1]


def test_reasoning_items_round_trip_within_a_turn(make_session):
    s, fake, log = make_session(tool_turn_rounds(), approval="full-auto")
    ws_file(s, "a.py", "x = 1\n")
    run(s)
    second = fake.requests[1]["input"]
    assert kinds(second)[2:5] == ["reasoning", "function_call", "function_call"]
    assert second[2]["encrypted_content"] == "gAAAA-opaque"


def test_prune_history_false_keeps_everything(make_session):
    s, fake, log = make_session(tool_turn_rounds(), approval="full-auto", prune_history=False)
    ws_file(s, "a.py", "x = 1\n")
    run(s)
    assert kinds(s.history) == ["msg:system", "msg:user", "reasoning", "function_call", "function_call",
                                "function_call_output", "function_call_output", "reasoning", "function_call",
                                "function_call_output", "reasoning", "message"]


def test_turn_record_is_capped(make_session):
    many = [fn_call("read_file", path=f"dir/file_with_a_long_name_{i:03}.py") for i in range(40)]
    s, fake, log = make_session([many, [msg("read them")]])
    for i in range(40):
        ws_file(s, f"dir/file_with_a_long_name_{i:03}.py", "x\n")
    run(s)
    record = s.history[-1]["content"]
    assert len(record) == 600 and record.endswith("…")


# --- model failures and retries --------------------------------------------------------------

def test_mid_stream_retry_emits_model_retry(make_session):
    s, fake, log = make_session([Round(output=[msg("recovered answer")], fail_times=1, fail_after=2)])
    run(s)
    [retry] = log.of("model_retry")
    assert retry.round == 1 and retry.attempt == 1 and "RemoteProtocolError" in retry.reason
    assert len(fake.requests) == 2
    done = log.of("turn_completed")[0]
    assert done.text == "recovered answer" and done.stats["rounds"] == 1
    types = log.types()
    assert types.index("model_retry") < types.index("model_round_completed")


def test_stream_keeps_breaking_fails_the_turn(make_session):
    s, fake, log = make_session([Round(output=[msg("x")], fail_times=3), [msg("next turn works")]])
    p = ws_file(s, "keep.txt", "k\n")
    run(s, "q1")
    assert len(log.of("model_retry")) == 2 and len(fake.requests) == 3
    failed = log.of("turn_failed")[0]
    assert failed.error_code == "stream_error" and "broke 3 times" in failed.message
    assert s.history[-2:] == [{"role": "user", "content": "q1"},
                              {"role": "developer", "content": "Turn failed (stream_error) after: no tool calls."}]
    fake.rounds[0].fail_times = 0
    fake.index = 1
    run(s, "q2")
    assert log.of("turn_completed")[0].text == "next turn works" and p.exists()


def test_api_error_fails_the_turn(make_session):
    s, fake, log = make_session([Round(error=bad_request("Unknown model 'gpt-nope'", param="model"))])
    run(s)
    failed = log.of("turn_failed")[0]
    assert failed.error_code == "bad_request" and "gpt-nope" in failed.message
    assert not s.busy


def test_stream_error_event_fails_the_turn(make_session):
    s, fake, log = make_session([Round(output=[msg("x")],
                                       stream_error={"type": "error", "code": "server_error", "message": "boom"})])
    run(s)
    failed = log.of("turn_failed")[0]
    assert failed.error_code == "server_error" and "boom" in failed.message


def test_rejected_include_is_dropped_with_a_notice(make_session):
    err = bad_request("Invalid value: 'reasoning.encrypted_content'. Supported values are: ...", param="include")
    s, fake, log = make_session([Round(output=[msg("fine")], error=err), [msg("still fine")]])
    run(s)
    run(s)
    assert "include" in fake.requests[0] and "include" not in fake.requests[1] and "include" not in fake.requests[2]
    [notice] = log.of("notice")
    assert notice.code == "include_rejected" and notice.level == "warning"
    assert log.of("turn_completed")[1].text == "still fine"


def test_unrelated_400_mentioning_include_keeps_include(make_session):
    err = bad_request("Invalid value: 'extreme'. Supported values include: 'low', 'medium', 'high'.",
                      param="reasoning.effort")
    s, fake, log = make_session([Round(output=[msg("fine")], error=err)])
    run(s)
    assert log.of("turn_failed")[0].error_code == "bad_request"
    assert not log.of("notice") and len(fake.requests) == 1
    run(s)
    assert fake.requests[1]["include"] == ["reasoning.encrypted_content"]


def test_rejected_prompt_cache_key_is_dropped(make_session):
    err = bad_request("Unknown parameter: 'prompt_cache_key'.", param="prompt_cache_key")
    s, fake, log = make_session([Round(output=[msg("ok")], error=err)])
    run(s)
    assert "prompt_cache_key" not in fake.requests[1] and fake.requests[1]["include"]
    assert [n.code for n in log.of("notice")] == ["prompt_cache_key_rejected"]


def test_incomplete_response_emits_notice_and_continues(make_session):
    s, fake, log = make_session([Round(output=[msg("partial ans")], status="incomplete")])
    run(s)
    assert [n.code for n in log.of("notice")] == ["response_incomplete"]
    assert "max_output_tokens" in log.of("notice")[0].message
    assert log.of("turn_completed")[0].text == "partial ans"


def test_on_event_exceptions_do_not_break_the_turn(tmp_path):
    def boom(ev):
        raise RuntimeError("frontend bug")
    cfg = AgentConfig(workspace=tmp_path, web_search=False)
    s = Session(cfg, boom, model=FakeModelAdapter(cfg, [[msg("ok")]]))
    run(s)
    assert s.history[-2]["content"] == "ok"


# --- usage and cost --------------------------------------------------------------------------

def test_usage_and_cost_math(make_session):
    u = usage(inp=12_000, cached=8_000, out=900, reasoning=300)
    s, fake, log = make_session([Round(output=[fn_call("list_dir", path=".")], usage=u),
                                 Round(output=[msg("a")], usage=u), Round(output=[msg("b")], usage=u)])
    rates = PRICING["gpt-5.6-luna"]
    expected = (4_000 * rates["input"] + 8_000 * rates["cached"] + 900 * rates["output"]) / 1_000_000
    run(s)
    r1 = log.of("model_round_completed")[0]
    assert (r1.input_tokens, r1.cached_tokens, r1.output_tokens, r1.reasoning_tokens) == (12_000, 8_000, 900, 300)
    assert r1.cost_usd == pytest.approx(expected) and r1.function_calls == 1
    stats = log.of("turn_completed")[0].stats
    assert stats["model_cost_usd"] == pytest.approx(2 * expected, abs=1e-6)
    assert stats["input_tokens"] == 24_000 and stats["reasoning_tokens"] == 600
    run(s)
    totals = s.usage_totals()
    assert totals["rounds"] == 3 and totals["model_cost_usd"] == pytest.approx(3 * expected, abs=1e-6)
    assert set(totals) == set(stats)


def test_unknown_model_cost_is_none_with_one_notice(make_session):
    s, fake, log = make_session([[msg("a")], [msg("b")]], model="some-new-model")
    run(s)
    run(s)
    assert [e.cost_usd for e in log.of("model_round_completed")] == [None, None]
    assert [n.code for n in log.of("notice")] == ["unknown_pricing"]
    assert s.usage_totals()["model_cost_usd"] == 0.0


def test_web_search_actions_sources_and_fees(make_session):
    s, fake, log = make_session([[
        web_call("python 3.14 release date", sources=["https://python.org/a", "https://peps.python.org/b"]),
        web_call("https://python.org/a", kind="open_page"),
        msg("It was released in October.", citations=[("Python", "https://python.org/a")]),
    ]], web_search=True, web_allowed_domains=["python.org"])
    run(s)
    req = fake.requests[0]
    assert req["tools"][0] == {"type": "web_search", "search_context_size": "medium",
                               "filters": {"allowed_domains": ["python.org"]}}
    assert req["include"] == ["reasoning.encrypted_content", "web_search_call.action.sources"]
    assert [(e.kind, e.detail) for e in log.of("web_action")] == [
        ("search", "'python 3.14 release date'"), ("open_page", "https://python.org/a")]
    done = log.of("turn_completed")[0]
    assert done.sources == [{"title": "Python", "url": "https://python.org/a"}]
    assert done.sources_all == [{"url": "https://python.org/a"}, {"url": "https://peps.python.org/b"}]
    assert (done.stats["web_searches"], done.stats["web_opens"], done.stats["web_cost_usd"]) == (1, 1, 0.01)
    assert "1 web search" in s.history[-1]["content"]
    assert "# Web search" in s.system_prompt


# --- session commands ------------------------------------------------------------------------

def test_busy_and_new_conversation(make_session):
    release = threading.Event()
    s, fake, log = make_session([Round(output=[msg("one")], block="release", release=release), [msg("two")]])
    s.start_turn("first")
    wait_blocked(fake)
    with pytest.raises(Busy):
        s.start_turn("again")
    with pytest.raises(Busy):
        s.new_conversation()
    release.set()
    assert s.wait(5)
    assert len(s.history) == 4
    s.new_conversation()
    assert kinds(s.history) == ["msg:system"] and log.of("notice")[-1].code == "new_conversation"
    run(s, "fresh")
    assert kinds(fake.requests[-1]["input"]) == ["msg:system", "msg:user"]


def test_new_conversation_forgets_file_state(make_session):
    s, fake, log = make_session([[fn_call("read_file", path="a.py")], [msg("read")],
                                 [fn_call("write_file", call_id="w", path="a.py", content="new\n", overwrite=True)],
                                 [msg("could not")]], approval="full-auto")
    ws_file(s, "a.py", "old\n")
    run(s)
    s.new_conversation()
    run(s)
    assert outputs(fake.requests[3])["w"] == "Error (conflict): Read the current file before overwriting it."


def test_all_events_are_json_serializable(make_session):
    s, fake, log = make_session([
        Round(output=[reasoning_item(), web_call("q", sources=["https://e.com"]), fn_call("read_file", path="a.py"),
                      fn_call("read_file", path="b.py"), edit_call()], fail_times=1, fail_after=3),
        [msg("done", citations=[("E", "https://e.com")])],
        Round(output=[msg("never")], block="cancel"),
    ], web_search=True)
    ws_file(s, "a.py", "x = 1\n")
    s.start_turn("everything")
    req = log.wait_for("approval_requested").request
    s.respond_approval(req["request_id"], "allow", "fine")
    assert s.wait(5)
    n = len(fake.streams) + 1
    s.start_turn("then cancel")
    wait_blocked(fake, n=n)
    s.cancel()
    seen = set()
    for e in log.events:
        d = json.loads(json.dumps(e.to_dict()))
        assert d["type"] == e.type and d["session_id"] == s.session_id and d["seq"] == e.seq and d["ts"]
        seen.add(e.type)
    assert seen >= {"session_started", "turn_started", "model_round_started", "text_delta", "model_retry",
                    "model_round_completed", "web_action", "tool_started", "tool_completed", "approval_requested",
                    "approval_resolved", "turn_completed", "turn_cancelled"}
    assert [e.seq for e in log.events] == list(range(1, len(log.events) + 1))


def test_event_log_thread_safety_under_parallel_tools(make_session):
    calls = [fn_call("read_file", path=f"f{i}.py") for i in range(16)]
    s, fake, log = make_session([calls, [msg("ok")]])
    for i in range(16):
        ws_file(s, f"f{i}.py", f"v = {i}\n")
    run(s)
    assert len(log.of("tool_started")) == len(log.of("tool_completed")) == 16
    assert [e.seq for e in log.events] == list(range(1, len(log.events) + 1))
    assert isinstance(log, EventLog)

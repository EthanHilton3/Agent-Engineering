"""Phase 3: transcript, event log and CLI, driven by events recorded from a real Session + FakeModelAdapter."""
import json
import queue

import pytest

from conftest import FakeModelAdapter, Round, fn_call, msg, usage, web_call

from agent_v3.config import AgentConfig
from agent_v3.frontends import cli as cli_mod
from agent_v3.frontends.cli import Cli, _Quit, diff_files
from agent_v3.frontends.eventlog import EventLogWriter, read_events
from agent_v3.frontends.formatting import completion_line, format_usage, round_summary
from agent_v3.frontends.transcript import TranscriptWriter
from agent_v3.session import Session


# --- recording ---------------------------------------------------------------------------------

def make_cli_session(tmp_path, rounds, **cfg):
    root = tmp_path / "ws"
    root.mkdir(exist_ok=True)
    cfg.setdefault("web_search", False)
    config = AgentConfig(workspace=root, **cfg)
    q: queue.Queue = queue.Queue()
    fake = FakeModelAdapter(config, rounds)
    return Session(config, q.put, model=fake), q, fake, root


def run_cli(session, q, inputs, sinks=(), **kw):
    """Run the CLI with scripted input; the script ends with EOF. Each item may be an exception to raise."""
    script = iter(inputs)

    def input_fn(prompt):
        try:
            item = next(script)
        except StopIteration:
            raise EOFError
        if isinstance(item, BaseException):
            raise item
        return item

    return Cli(session, q, input_fn=input_fn, sinks=tuple(sinks), **kw).run()


def edit_call(path="a.py", old="x = 1", new="x = 2", call_id=None):
    return fn_call("edit_files", call_id=call_id, edits=[{"path": path, "old_text": old, "new_text": new}])


@pytest.fixture
def recorded(tmp_path):
    """Events of a real two-turn session: parallel reads, a web search with a source, an approved edit,
    a retry-free second turn. Returns (list of Event objects, workspace path)."""
    root = tmp_path / "ws"
    root.mkdir()
    (root / "a.py").write_text("x = 1\n", encoding="utf-8")
    (root / "b.py").write_text("y = 1\n", encoding="utf-8")
    config = AgentConfig(workspace=root, web_search=True, approval="auto-edit")
    fake = FakeModelAdapter(config, [
        Round([fn_call("read_file", call_id="r1", path="a.py"), fn_call("read_file", call_id="r2", path="b.py"),
               web_call("pytest tips", ["https://example.com/p"])], usage=usage(1000, 0, 50, 10)),
        Round([edit_call(call_id="e1"), fn_call("read_file", call_id="r3", path="nope.py")],
              usage=usage(41200, 39000, 812, 240)),
        Round([msg("Changed x. Full details at example.", [("Example", "https://example.com/p")])],
              usage=usage(42000, 41000, 30, 0)),
        Round([msg("Second answer")]),
    ])
    events = []
    session = Session(config, events.append, model=fake)
    session.start_turn("change x to 2 please")
    assert session.wait(10)
    session.start_turn("thanks")
    assert session.wait(10)
    session.close()
    return events, root


# --- formatting --------------------------------------------------------------------------------

def test_round_summary_matches_spec_example():
    line = round_summary({"input_tokens": 41200, "cached_tokens": 39000, "output_tokens": 812,
                          "reasoning_tokens": 240, "duration_s": 4.1, "cost_usd": 0.0213})
    assert line == "41.2k in (39.0k cached) · 812 out (240 reasoning) · 4.1s · $0.0213"


def test_completion_line_and_pluralisation():
    stats = {"elapsed_s": 12.4, "rounds": 4, "tool_calls": 9, "parallel_groups": 2, "model_cost_usd": 0.03,
             "web_cost_usd": 0.001}
    assert completion_line(stats) == "Completed in 12.4s · 4 rounds · 9 tool calls (2 parallel groups) · $0.031"
    one = {"elapsed_s": 1.0, "rounds": 1, "tool_calls": 1, "parallel_groups": 1, "web_searches": 1}
    assert completion_line(one) == "Completed in 1.0s · 1 round · 1 tool call (1 parallel group) · 1 web search · $0.0000"
    assert completion_line({"elapsed_s": 0.5, "rounds": 1}) == "Completed in 0.5s · 1 round · $0.0000"


# --- transcript --------------------------------------------------------------------------------

def test_transcript_from_recorded_events(recorded, tmp_path):
    events, _ = recorded
    path = tmp_path / "out" / "t.md"
    t = TranscriptWriter(path)
    for ev in events:
        t(ev)
    t.close()
    text = path.read_text(encoding="utf-8")

    assert "# Transcript " in text and "model=gpt-6-luna" in text and "approval=auto-edit" in text
    assert text.index("**USER:** change x to 2 please") < text.index("**AGENT:** Changed x.")
    assert "**USER:** thanks" in text and "**AGENT:** Second answer" in text
    assert "> TOOL: `read_file(path='a.py')` -> 'lines 1" in text          # v2 style: repr of the result
    assert "> TOOL: `web_search('pytest tips')`" in text
    assert "FAILED (not_found)" in text                                  # the failed read
    # one ROUND line per round, in the v2-compatible shape
    assert "> ROUND 2 · 41.2k in (39.0k cached) · 812 out (240 reasoning) · " in text
    assert text.count("> ROUND ") == 4
    assert "**Sources:**\n1. [Example](https://example.com/p)" in text
    assert "seconds, 3 rounds, 4 tool calls (1 parallel group), 1 web search," in text
    # usage block at the end, summed over both turns
    assert text.rstrip().endswith("```") and "Total cost (USD): $" in text
    assert "Rounds: 4" in text and "Tool calls: 4" in text and "Web searches: 1" in text
    # close() writes the usage block only once
    t.close()
    assert path.read_text(encoding="utf-8") == text


def test_transcript_records_approvals_cancel_and_failure(tmp_path):
    t = TranscriptWriter(tmp_path / "t.md")
    base = {"session_id": "s", "seq": 1, "ts": "2026-10-13T10:00:00.000+00:00"}
    stats = {"rounds": 1, "elapsed_s": 2.0, "model_cost_usd": 0.01, "input_tokens": 10}
    for d in [
        {"type": "session_started", "config": {"model": "m", "reasoning": "none", "approval": "ask",
                                               "web_search": False, "workspace": "w"}, **base},
        {"type": "turn_started", "turn_id": "t1", "user_message": "run it", **base},
        {"type": "approval_requested", "request": {"request_id": "ap_1", "title": "Run command",
                                                   "command": "pytest -q", "paths": []}, **base},
        {"type": "approval_resolved", "request_id": "ap_1", "decision": "reject", "feedback": "not now",
         "by": "user", **base},
        {"type": "turn_cancelled", "turn_id": "t1", "stats": stats, **base},
        {"type": "turn_started", "turn_id": "t2", "user_message": "again", **base},
        {"type": "model_retry", "round": 1, "attempt": 1, "reason": "stream ended", "delay_s": 2.0, **base},
        {"type": "notice", "level": "warning", "code": "rounds_low", "message": "2 rounds left", **base},
        {"type": "turn_failed", "turn_id": "t2", "error_code": "api_error", "message": "boom", "stats": stats, **base},
    ]:
        t.write(d)                                                       # dicts work as well as Event objects
    t.close()
    text = (tmp_path / "t.md").read_text(encoding="utf-8")
    assert "> APPROVAL: Run command (pytest -q) -> reject (by user) — not now" in text
    assert "**CANCELLED** by the user." in text
    assert "> RETRY round 1 (attempt 1, in 2.0s): stream ended" in text
    assert "> NOTICE (warning, rounds_low): 2 rounds left" in text
    assert "**FAILED** (api_error): boom" in text
    assert "Rounds: 2" in text and "Input (tokens): 20" in text         # both stopped turns count


def test_transcript_without_session_started_writes_nothing_on_close(tmp_path):
    t = TranscriptWriter(tmp_path / "t.md")
    t.close()
    assert not (tmp_path / "t.md").exists()


# --- event log ---------------------------------------------------------------------------------

def test_eventlog_roundtrip_in_order(recorded, tmp_path):
    events, _ = recorded
    path = tmp_path / "logs" / "events.jsonl"
    log = EventLogWriter(path)
    for ev in events:
        log(ev)
    log.close()
    log.write(events[0])                                                # after close: ignored, no error

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == len(events)
    assert [json.loads(l) for l in lines] == [e.to_dict() for e in events]
    assert [d["seq"] for d in read_events(path)] == sorted(e.seq for e in events)
    types = [d["type"] for d in read_events(path)]
    assert types[0] == "session_started" and types.count("turn_completed") == 2


def test_eventlog_appends_and_replay_rebuilds_the_transcript(recorded, tmp_path):
    events, _ = recorded
    path = tmp_path / "events.jsonl"
    for chunk in (events[:5], events[5:]):                              # two runs append to the same file
        log = EventLogWriter(path)
        for ev in chunk:
            log(ev)
        log.close()
    direct, replayed = TranscriptWriter(tmp_path / "a.md"), TranscriptWriter(tmp_path / "b.md")
    for ev in events:
        direct(ev)
    for d in read_events(path):
        replayed(d)
    direct.close()
    replayed.close()
    assert (tmp_path / "a.md").read_text(encoding="utf-8") == (tmp_path / "b.md").read_text(encoding="utf-8")


def test_read_events_skips_torn_last_line(tmp_path):
    path = tmp_path / "e.jsonl"
    path.write_text('{"type": "notice"}\n{"type": "tur', encoding="utf-8")
    assert list(read_events(path)) == [{"type": "notice"}]


# --- CLI ---------------------------------------------------------------------------------------

def test_diff_files_counts_per_file():
    diff = "\n".join(["--- a/x.py", "+++ b/x.py", "@@ -1 +1,2 @@", "-old", "+new", "+more",
                      "--- a/sub/y.py", "+++ b/sub/y.py", "@@ -1 +1 @@", "-a", "+b"])
    assert diff_files(diff) == [["x.py", 2, 1], ["sub/y.py", 1, 1]]


def test_cli_plain_answer_and_usage(tmp_path, capsys):
    s, q, fake, _ = make_cli_session(tmp_path, [[msg("Hello there")]])
    assert run_cli(s, q, ["hi", "/usage", "/bogus"]) == 0
    out = capsys.readouterr().out
    assert "\x1b[" not in out                                           # non-TTY: no ANSI
    assert "Agent >\nHello there" in out
    assert "Completed in" in out and "1 round" in out
    assert "Unknown command /bogus" in out
    assert out.count("Total cost (USD)") == 2                           # /usage and the exit summary


def test_cli_tool_lines_parallel_header_and_failure(tmp_path, capsys):
    s, q, fake, root = make_cli_session(tmp_path, [
        [fn_call("read_file", path="a.py"), fn_call("read_file", path="b.py"), fn_call("read_file", path="no.py")],
        [msg("done")]])
    (root / "a.py").write_text("x\n", encoding="utf-8")
    (root / "b.py").write_text("y\n", encoding="utf-8")
    run_cli(s, q, ["read them"])
    out = capsys.readouterr().out
    assert "  parallel x3" in out
    assert "-> read_file  a.py  ok lines 1" in out
    assert "-> read_file  no.py  x not found" in out


def test_cli_approval_feedback_rejects_and_shows_diff(tmp_path, capsys):
    s, q, fake, root = make_cli_session(tmp_path, [[edit_call(call_id="e1")], [msg("ok, left alone")]])
    (root / "a.py").write_text("x = 1\n", encoding="utf-8")
    run_cli(s, q, ["change x", "d", "use y instead"])
    out = capsys.readouterr().out
    assert "Approval needed: Edit 1 file (edits need approval in 'ask' mode)" in out
    assert "a.py  +1 -1" in out and "-x = 1" in out and "+x = 2" in out
    assert "[y] allow  [a] allow for session  [n] reject  [d] show full diff" in out
    assert (root / "a.py").read_text() == "x = 1\n"
    tool_output = [i["output"] for i in fake.requests[1]["input"] if i.get("type") == "function_call_output"][0]
    assert tool_output.endswith("User feedback: use y instead")


def test_cli_approval_allow_and_allow_for_session(tmp_path):
    s, q, fake, root = make_cli_session(tmp_path, [
        [edit_call(call_id="e1")], [msg("one")], [edit_call(old="x = 2", new="x = 3", call_id="e2")], [msg("two")]])
    (root / "a.py").write_text("x = 1\n", encoding="utf-8")
    run_cli(s, q, ["first", "a", "second"])                             # "a" = allow for session: no 2nd prompt
    assert (root / "a.py").read_text() == "x = 3\n"


def test_cli_command_approval_has_no_diff_option(tmp_path, capsys):
    s, q, fake, root = make_cli_session(tmp_path, [[fn_call("run_command", command="echo hi", call_id="c1")],
                                                   [msg("ran")]])
    run_cli(s, q, ["run it", "y"])
    out = capsys.readouterr().out
    assert "Approval needed: Run command" in out and "  $ echo hi" in out and "[d] show" not in out
    assert "exit 0" in out


def test_cli_eof_at_approval_rejects(tmp_path):
    s, q, fake, root = make_cli_session(tmp_path, [[edit_call()], [msg("ok")]])
    (root / "a.py").write_text("x = 1\n", encoding="utf-8")
    run_cli(s, q, ["change x"])                                         # the approval prompt hits EOF
    assert (root / "a.py").read_text() == "x = 1\n"


def test_cli_ctrl_c_at_approval_cancels_turn_and_session_continues(tmp_path, capsys):
    s, q, fake, root = make_cli_session(tmp_path, [[edit_call()], [msg("Back again")]])
    (root / "a.py").write_text("x = 1\n", encoding="utf-8")
    run_cli(s, q, ["change x", KeyboardInterrupt(), "still there?"])
    out = capsys.readouterr().out
    assert "Cancelled." in out
    assert "Back again" in out                                          # the next prompt worked
    assert (root / "a.py").read_text() == "x = 1\n"
    assert any("Turn cancelled by user" in str(m.get("content")) for m in s.history)
    assert not s.busy


def test_cli_ctrl_c_at_prompt_exits_with_usage(tmp_path, capsys):
    s, q, fake, _ = make_cli_session(tmp_path, [[msg("hi")]])
    assert run_cli(s, q, ["hello", KeyboardInterrupt(), "never read"]) == 0
    out = capsys.readouterr().out
    assert "Hello" not in out and "Total cost (USD)" in out and "never read" not in out
    assert fake.index == 1


def test_cli_second_ctrl_c_within_two_seconds_quits(tmp_path):
    s, q, fake, _ = make_cli_session(tmp_path, [[msg("x")]])
    cli = Cli(s, q)
    cli._interrupt()                                                    # idle session: cancel is a no-op
    with pytest.raises(_Quit):
        cli._interrupt()
    cli._last_interrupt -= cli_mod.DOUBLE_INTERRUPT_S + 1               # long enough ago: just cancels again
    cli._interrupt()


def test_cli_cancel_race_does_not_prompt_for_a_dead_approval(tmp_path, capsys):
    """The approval_requested event is still queued when Ctrl+C cancels: the user must not be asked."""
    s, q, fake, root = make_cli_session(tmp_path, [[edit_call()], [msg("x")]])
    (root / "a.py").write_text("x = 1\n", encoding="utf-8")
    s.start_turn("change x")
    deadline = __import__("time").time() + 5
    while s.approvals.pending is None and __import__("time").time() < deadline:
        __import__("time").sleep(0.01)
    s.cancel()
    asked = []
    cli = Cli(s, q, input_fn=lambda p: asked.append(p) or "y")
    cli._pump()
    assert asked == []
    assert "Cancelled." in capsys.readouterr().out


def test_cli_writes_sinks_for_every_event(tmp_path):
    s, q, fake, _ = make_cli_session(tmp_path, [[msg("Hi")]])
    seen = []
    run_cli(s, q, ["hello"], sinks=[seen.append])
    assert [e.type for e in seen][0] == "session_started" and "turn_completed" in [e.type for e in seen]
    assert [e.seq for e in seen] == list(range(1, len(seen) + 1))


def test_cli_survives_a_failing_sink(tmp_path, capsys):
    s, q, fake, _ = make_cli_session(tmp_path, [[msg("Still works")]])

    def broken(ev):
        raise OSError("disk full")
    run_cli(s, q, ["hi"], sinks=[broken])
    out = capsys.readouterr().out
    assert out.count("could not write the event log") == 1 and "Still works" in out


def test_main_rejects_bad_workspace(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc:
        cli_mod.main(["--workspace", str(tmp_path / "missing")])
    assert exc.value.code == 2 and "workspace is not a folder" in capsys.readouterr().err


def test_config_from_args_maps_flags(tmp_path):
    args = cli_mod.build_parser().parse_args(
        ["--workspace", str(tmp_path), "--no-web", "--allow-domain", "a.com", "--allow-domain", "b.org",
         "--max-turn-cost", "0.5", "--no-prune-history", "--approval", "auto-edit", "--reasoning", "low"])
    c = cli_mod.config_from_args(args)
    assert (c.web_search, c.web_allowed_domains, c.max_turn_cost_usd) == (False, ["a.com", "b.org"], 0.5)
    assert (c.prune_history, c.parallel_reads, c.approval, c.reasoning) == (False, True, "auto-edit", "low")

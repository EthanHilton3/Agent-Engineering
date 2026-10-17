"""Phase S3: saved sessions in the terminal frontend (sessions spec §6, §11.2) and `export`/`sessions` subcommands.

The CLI is driven with scripted input and a FakeModelAdapter; `main()` is driven with a patched `ModelAdapter`
so each session it builds gets a fake whose config we can inspect.
"""
import queue
import re

import pytest

from conftest import FakeModelAdapter, msg

from agent_v3.config import AgentConfig
from agent_v3.frontends import cli as cli_mod
from agent_v3.frontends.args import explicit_settings
from agent_v3.frontends.cli import Cli
from agent_v3.frontends.commands import format_sessions
from agent_v3.frontends.eventlog import EventLogWriter
from agent_v3.frontends.transcript import TranscriptWriter
from agent_v3.session import Session
from agent_v3.sessions import SessionInfo, SessionStore, config_for_resume


# --- helpers -----------------------------------------------------------------------------------

def workspace(tmp_path):
    root = tmp_path / "ws"
    root.mkdir(parents=True, exist_ok=True)
    return root


def save_session(root, user="hello", answer="hi", **cfg):
    """A closed, saved one-turn session in `root`'s store; returns its id."""
    cfg.setdefault("web_search", False)
    config = AgentConfig(workspace=root, **cfg)
    s = Session(config, lambda e: None, model=FakeModelAdapter(config, [[msg(answer)]]),
                store=SessionStore.for_workspace(root))
    s.start_turn(user)
    assert s.wait(10)
    s.close()
    return s.session_id


def open_cli(root, rounds, saved=True, **cfg):
    """(session, queue, fake, store) with a Session that saves (or not) into `root`."""
    cfg.setdefault("web_search", False)
    config = AgentConfig(workspace=root, **cfg)
    store = SessionStore.for_workspace(root) if saved else None
    q: queue.Queue = queue.Queue()
    fake = FakeModelAdapter(config, rounds)
    return Session(config, q.put, model=fake, store=store), q, fake, store


def scripted(inputs):
    script = iter(inputs)

    def input_fn(prompt):
        try:
            return next(script)
        except StopIteration:
            raise EOFError
    return input_fn


def run_cli(session, q, inputs, **kw):
    return Cli(session, q, input_fn=scripted(inputs), **kw).run()


def type_input(monkeypatch, *lines):
    script = iter(lines)

    def fake_input(prompt=""):
        try:
            return next(script)
        except StopIteration:
            raise EOFError
    monkeypatch.setattr("builtins.input", fake_input)


@pytest.fixture
def configs(monkeypatch):
    """Patch the adapter `Session` builds when it is given none: every one is a fake that records its config."""
    seen: list[AgentConfig] = []

    def make(config):
        seen.append(config)
        return FakeModelAdapter(config, [[msg("pong")]] * 5)
    monkeypatch.setattr("agent_v3.session.ModelAdapter", make)
    return seen


# --- flags -------------------------------------------------------------------------------------

def test_transcript_flag_was_removed(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc:
        cli_mod.main(["--workspace", str(workspace(tmp_path)), "--transcript", "t.md"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "--transcript was removed" in err and "export latest -o FILE" in err


def test_no_save_cannot_be_combined_with_resume_or_continue(tmp_path, capsys):
    for flags in (["--resume", "latest"], ["--resume"], ["--continue"], ["-c"]):
        with pytest.raises(SystemExit) as exc:
            cli_mod.main(["--workspace", str(workspace(tmp_path)), "--no-save", *flags])
        assert exc.value.code == 2
    assert "--no-save cannot be combined" in capsys.readouterr().err


def test_explicit_settings_returns_only_typed_flags(tmp_path):
    parse = cli_mod.build_parser().parse_args
    assert explicit_settings(parse([])) == set()
    assert explicit_settings(parse(["--model", "m"])) == {"model"}
    assert explicit_settings(parse(["--reasoning", "high", "--model", "m", "--approval", "full-auto"])) == {"model", "reasoning"}
    # an omitted flag still builds the AgentConfig defaults
    c = cli_mod.config_from_args(parse(["--workspace", str(tmp_path)]))
    assert (c.model, c.reasoning) == (AgentConfig.model, AgentConfig.reasoning)


def test_config_for_resume_restores_unless_typed(tmp_path):
    root = workspace(tmp_path)
    sid = save_session(root, model="gpt-5.6-sol", reasoning="high", approval="full-auto")
    info = SessionStore.for_workspace(root).load(sid).info
    launch = AgentConfig(workspace=root)
    got = config_for_resume(launch, info, set())
    assert (got.model, got.reasoning, got.approval) == ("gpt-5.6-sol", "high", "ask")
    got = config_for_resume(launch, info, {"model"})
    assert (got.model, got.reasoning) == (launch.model, "high")
    got = config_for_resume(launch, info, {"model", "reasoning"})
    assert (got.model, got.reasoning) == (launch.model, launch.reasoning)


# --- option C through main() -------------------------------------------------------------------

def test_resume_restores_model_and_reasoning_but_never_approval(tmp_path, monkeypatch, capsys, configs):
    root = workspace(tmp_path)
    sid = save_session(root, "first question", "first answer", model="gpt-5.6-sol", reasoning="high", approval="full-auto")
    type_input(monkeypatch)
    assert cli_mod.main(["--workspace", str(root), "--resume", sid[2:8]]) == 0
    got = configs[-1]
    assert (got.model, got.reasoning, got.approval) == ("gpt-5.6-sol", "high", "ask")
    out = capsys.readouterr().out
    assert f"Resumed {sid}" in out and '"first question"' in out and "1 turn" in out
    assert "approval ask (saved with full-auto; approval is never restored)" in out
    assert "model gpt-5.6-sol (--model" not in out                    # nothing differs for model or reasoning
    assert "first question" in out and "first answer" in out           # the last exchange is shown again


def test_typed_flags_win_and_are_named_in_the_recap(tmp_path, monkeypatch, capsys, configs):
    root = workspace(tmp_path)
    sid = save_session(root, model="gpt-5.6-sol", reasoning="high", approval="full-auto")
    type_input(monkeypatch)
    cli_mod.main(["--workspace", str(root), "--resume", sid, "--model", "gpt-6-luna"])
    got = configs[-1]
    assert (got.model, got.reasoning) == ("gpt-6-luna", "high")       # model typed, reasoning restored
    assert "model gpt-6-luna (--model; saved with gpt-5.6-sol)" in capsys.readouterr().out

    type_input(monkeypatch)
    cli_mod.main(["--workspace", str(root), "--resume", sid, "--approval", "full-auto", "--reasoning", "low"])
    got = configs[-1]
    assert (got.model, got.reasoning, got.approval) == ("gpt-5.6-sol", "low", "full-auto")
    out = capsys.readouterr().out
    assert "reasoning low (--reasoning; saved with high)" in out and "approval" not in out.split("Resumed")[1].split("You")[0]


def test_new_after_a_resume_uses_the_launch_config(tmp_path, monkeypatch, capsys, configs):
    root = workspace(tmp_path)
    sid = save_session(root, model="gpt-5.6-sol", reasoning="high")
    type_input(monkeypatch, "/new")
    cli_mod.main(["--workspace", str(root), "--resume", sid])
    resumed, fresh = configs[-2], configs[-1]
    assert (resumed.model, resumed.reasoning) == ("gpt-5.6-sol", "high")
    assert (fresh.model, fresh.reasoning) == (AgentConfig.model, AgentConfig.reasoning)
    assert capsys.readouterr().out.count("agent_v3 - ") == 2           # two banners


def test_resume_without_ref_lists_and_asks(tmp_path, monkeypatch, capsys, configs):
    root = workspace(tmp_path)
    older = save_session(root, "older task")
    sid = save_session(root, "newer task")
    type_input(monkeypatch, "2")                                      # row 2 = the older session
    cli_mod.main(["--workspace", str(root), "--resume"])
    out = capsys.readouterr().out
    assert "Resume which? [1-2, Enter = new session]" not in out      # the prompt goes through input(), not stdout
    assert f"Resumed {older}" in out and sid[:12] in out


def test_continue_picks_the_latest_and_falls_back_to_a_new_session(tmp_path, monkeypatch, capsys, configs):
    root = workspace(tmp_path)
    type_input(monkeypatch)
    assert cli_mod.main(["--workspace", str(root), "--continue"]) == 0
    out = capsys.readouterr().out
    assert "No saved sessions in this workspace; starting a new one." in out and "Resumed" not in out
    save_session(root, "one")
    sid = save_session(root, "two")
    type_input(monkeypatch)
    cli_mod.main(["--workspace", str(root), "-c"])
    assert f"Resumed {sid}" in capsys.readouterr().out


def test_resume_errors_exit_2_without_a_session(tmp_path, capsys, configs):
    root = workspace(tmp_path)
    assert cli_mod.main(["--workspace", str(root), "--resume", "ffff0000"]) == 2
    assert "No saved session matches" in capsys.readouterr().err
    assert configs == []                                              # no Session (and no model) was built


def test_continue_reports_a_session_open_elsewhere(tmp_path, capsys):
    root = workspace(tmp_path)
    holder, q, fake, store = open_cli(root, [[msg("x")]])
    holder.start_turn("hold the lock")
    assert holder.wait(10)
    try:
        assert cli_mod.main(["--workspace", str(root), "--continue"]) == 2
    finally:
        holder.close()
    err = capsys.readouterr().err
    assert holder.session_id in err and "open in another agent_v3 process" in err and "use --resume to pick another" in err
    assert ".;" not in err and err.strip().endswith("use --resume to pick another.")


# --- slash commands ----------------------------------------------------------------------------

def test_new_with_text_goes_to_the_model_and_commands_do_not(tmp_path):
    root = workspace(tmp_path)
    s, q, fake, store = open_cli(root, [[msg("ok")]])
    run_cli(s, q, ["/new file please"], store=store)
    assert fake.index == 1 and any("/new file please" in str(i.get("content")) for i in fake.requests[0]["input"])

    root2 = workspace(tmp_path / "two")
    save_session(root2)
    s, q, fake, store = open_cli(root2, [])
    run_cli(s, q, ["/resume 2", "/export out.md", "/sessions"], store=store)
    assert fake.index == 0                                            # none of them reached the model


def test_clear_is_an_unknown_command_and_new_never_clears_in_place(tmp_path, capsys, monkeypatch):
    root = workspace(tmp_path)
    s, q, fake, store = open_cli(root, [[msg("a")]])
    monkeypatch.setattr(Session, "new_conversation", lambda self: pytest.fail("the CLI must not clear history in place"))
    first = s.session_id
    run_cli(s, q, ["first", "/clear", "/new"], store=store)
    out = capsys.readouterr().out
    assert "Unknown command /clear" in out and "/sessions" in out      # the hint lists the real commands
    assert out.count("agent_v3 - ") == 2                               # /new printed a new banner
    assert store.resolve(first) == first


def test_new_starts_a_new_saved_session_with_the_default_factory(tmp_path):
    root = workspace(tmp_path)
    s, q, fake, store = open_cli(root, [[msg("one")], [msg("two")]])
    cli = Cli(s, q, input_fn=scripted(["first", "/new", "second"]), store=store)
    cli.run()
    ids = {i.session_id for i in store.list()}
    assert len(ids) == 2 and s.session_id in ids and cli.session.session_id in ids and cli.session is not s
    assert fake.index == 2                                            # the default factory reuses the fake model
    users = [i["content"] for i in fake.requests[1]["input"] if i.get("role") == "user"]
    assert users == ["second"]                                        # the new session starts empty


def test_new_uses_a_given_open_session_factory(tmp_path):
    root = workspace(tmp_path)
    s, q, fake, store = open_cli(root, [])
    built = []

    def factory(resume_id):
        built.append(resume_id)
        return Session(s.config, q.put, model=FakeModelAdapter(s.config, [[msg("x")]]), store=store)
    run_cli(s, q, ["/new"], store=store, open_session=factory)
    assert built == [None]


def test_sessions_marks_the_current_one_and_resume_by_number(tmp_path, capsys):
    root = workspace(tmp_path)
    old = save_session(root, "old task", "old answer")
    s, q, fake, store = open_cli(root, [[msg("fresh answer")], [msg("follow-up answer")]])
    run_cli(s, q, ["fresh task", "/sessions", "/resume 2", "what next"], store=store)
    out = capsys.readouterr().out
    rows = [l for l in out.splitlines() if re.match(r"[ *] ?\d+  s_", l)]
    assert rows[0].startswith("* 1  " + s.session_id[:12]) and rows[1].startswith("  2  " + old[:12])
    assert f"Resumed {old}" in out and "old answer" in out
    # the resumed conversation carries the old exchange into the next request
    sent = [str(i.get("content")) for i in fake.requests[1]["input"]]
    assert any("old task" in c for c in sent) and any("old answer" in c for c in sent)
    assert not any("fresh task" in c for c in sent)


def test_resume_of_the_current_session_is_a_noop(tmp_path, capsys):
    root = workspace(tmp_path)
    s, q, fake, store = open_cli(root, [[msg("a")]])
    run_cli(s, q, ["task", "/resume 1"], store=store)
    assert f"Already in session {s.session_id}" in capsys.readouterr().out


def test_failed_resume_keeps_the_current_session(tmp_path, capsys):
    root = workspace(tmp_path)
    s, q, fake, store = open_cli(root, [[msg("a")], [msg("b")]])
    cli = Cli(s, q, input_fn=scripted(["task", "/resume ffff0000", "again"]), store=store)
    cli.run()
    assert cli.session is s and fake.index == 2
    assert "No saved session matches" in capsys.readouterr().out


def test_resume_without_argument_asks_and_enter_stays(tmp_path, capsys):
    root = workspace(tmp_path)
    save_session(root)
    s, q, fake, store = open_cli(root, [])
    asked = []

    def input_fn(prompt):
        asked.append(prompt)
        if len(asked) == 1:
            return "/resume"
        if len(asked) == 2:
            return ""                                                 # Enter
        raise EOFError
    Cli(s, q, input_fn=input_fn, store=store).run()
    assert asked[1] == "Resume which? [1-1, Enter = stay here] " and "Resumed" not in capsys.readouterr().out


def test_resume_shows_the_interrupted_notice(tmp_path, capsys):
    root = workspace(tmp_path)
    old = save_session(root, "long job")
    (SessionStore.for_workspace(root).session_dir(old) / "history.jsonl").write_text("", encoding="utf-8")
    s, q, fake, store = open_cli(root, [])
    run_cli(s, q, ["/resume 1"], store=store)
    out = capsys.readouterr().out
    assert "note: Turn t1 was interrupted when the agent stopped." in out and "long job" in out


def test_commands_without_saving_say_so(tmp_path, capsys):
    s, q, fake, _ = open_cli(workspace(tmp_path), [], saved=False)
    run_cli(s, q, ["/resume 1", "/export"])
    out = capsys.readouterr().out
    assert out.count("Sessions are not being saved") == 2 and "Saving this session" not in out


def test_sessions_still_lists_saved_sessions_without_saving(tmp_path, capsys):
    # --no-save only stops writing; listing reads the saved files (like the server's list_sessions).
    root = workspace(tmp_path)
    sid = save_session(root, "an older saved session")
    s, q, fake, _ = open_cli(root, [], saved=False)
    run_cli(s, q, ["/sessions"])
    out = capsys.readouterr().out
    assert sid[:12] in out and "an older saved session" in out and "not being saved" not in out
    assert [p.name for p in SessionStore.for_workspace(root).root.iterdir()] == [sid]   # nothing new written


def test_sessions_without_saving_and_nothing_saved(tmp_path, capsys):
    s, q, fake, _ = open_cli(workspace(tmp_path), [], saved=False)
    run_cli(s, q, ["/sessions"])
    out = capsys.readouterr().out
    assert "No saved sessions yet." in out and not (tmp_path / "ws" / ".agent_v3").exists()


def test_sessions_lists_ten_then_all(tmp_path, capsys):
    root = workspace(tmp_path)
    for n in range(14):
        save_session(root, f"task {n}")
    s, q, fake, store = open_cli(root, [])
    run_cli(s, q, ["/sessions"], store=store)
    out = capsys.readouterr().out
    assert len(re.findall(r"^[ *] ?\d+  s_", out, re.M)) == 10
    assert "... 4 more: /sessions all" in out and "\x1b[" not in out and "…" not in out

    s2, q2, _, store2 = open_cli(root, [])
    run_cli(s2, q2, ["/sessions all"], store=store2)
    out = capsys.readouterr().out
    assert len(re.findall(r"^[ *] ?\d+  s_", out, re.M)) == 14 and "more:" not in out


def test_listing_format_flags_and_ascii(tmp_path):
    root = workspace(tmp_path)
    sid = save_session(root, "x" * 100)
    rows = SessionStore.for_workspace(root).list()
    plain = format_sessions(rows, ascii_only=True)
    assert plain[0] == "  #  id            updated           turns     cost  title"
    assert plain[1].startswith(f"  1  {sid[:12]}  ") and plain[1].endswith("...") and "…" not in plain[1]
    assert format_sessions(rows, current=sid)[1].startswith(f"* 1  {sid[:12]}")


def test_listing_cost_uses_four_decimals_below_a_cent():
    base = dict(session_id="s_0123456789ab", title="t", created="2026-10-17T10:00:00+00:00",
                updated="2026-10-17T10:00:00+00:00", turns=1, model="m", reasoning="low", status="idle")
    small, big = SessionInfo(cost_usd=0.0002, **base), SessionInfo(cost_usd=0.031, **base)
    header, row_small = format_sessions([small])
    row_big = format_sessions([big])[1]
    assert "$0.0002" in row_small and "$0.000 " not in row_small and "$0.031" in row_big
    # the cost column lines up under its header
    assert row_small.index("$0.0002") + len("$0.0002") == header.index("cost") + len("cost")
    assert row_big.index("$0.031") + len("$0.031") == header.index("cost") + len("cost")


# --- /export -----------------------------------------------------------------------------------

def test_export_defaults_to_the_session_folder_and_matches_a_direct_replay(tmp_path, capsys):
    root = workspace(tmp_path)
    s, q, fake, store = open_cli(root, [[msg("first answer")], [msg("second answer")]])
    seen = []
    run_cli(s, q, ["task one", "task two", "/export"], store=store, sinks=[seen.append])
    default = store.session_dir(s.session_id) / "transcript.md"
    assert default.is_file() and f"Transcript written to {default}" in capsys.readouterr().out
    direct = TranscriptWriter(tmp_path / "direct.md")
    for ev in seen:
        direct(ev)
    direct.close()
    text = default.read_text(encoding="utf-8")
    assert text == (tmp_path / "direct.md").read_text(encoding="utf-8")
    assert "**USER:** task one" in text and "**AGENT:** second answer" in text
    assert not default.with_name("transcript.md.tmp").exists()


def test_export_to_a_given_path_rebuilds_from_scratch(tmp_path):
    root = workspace(tmp_path)
    s, q, fake, store = open_cli(root, [[msg("answer")]])
    target = tmp_path / "out" / "t.md"
    target.parent.mkdir()
    target.write_text("OLD CONTENT", encoding="utf-8")
    run_cli(s, q, ["task", f"/export {target}"], store=store)
    text = target.read_text(encoding="utf-8")
    assert "OLD CONTENT" not in text and text.count("# Transcript ") == 1


def test_export_before_the_first_turn_has_nothing_to_write(tmp_path, capsys):
    s, q, fake, store = open_cli(workspace(tmp_path), [])
    run_cli(s, q, ["/export"], store=store)
    assert "Nothing to export yet" in capsys.readouterr().out


def test_two_session_starts_give_one_header_and_a_resumed_line(tmp_path):
    base = {"session_id": "s_1", "turn_id": None, "ts": "2026-10-16T09:12:00.000+00:00"}
    cfg = {"model": "m", "reasoning": "low", "approval": "ask", "web_search": False, "workspace": "w"}
    t = TranscriptWriter(tmp_path / "t.md")
    for d in [{"type": "session_started", "seq": 1, "config": cfg, **base},
              {"type": "turn_started", "turn_id": "t1", "user_message": "hi", "seq": 2, **{k: v for k, v in base.items() if k != "turn_id"}},
              {"type": "session_started", "seq": 3, "config": {**cfg, "model": "m2", "approval": "full-auto"}, **base},
              {"type": "session_resumed", "seq": 4, "title": "t", "created": "c", "turns_total": 1, **base},
              {"type": "notice", "level": "warning", "code": "turn_interrupted", "message": "Turn t1 was interrupted", "seq": 5, **base}]:
        t(d)
    t.close()
    text = (tmp_path / "t.md").read_text(encoding="utf-8")
    assert text.count("# Transcript ") == 1 and text.count("> RESUMED ") == 1
    assert re.search(r"> RESUMED 2026-10-16 \d\d:\d\d \(model=m2, reasoning=low, approval=full-auto\)", text)
    assert "> NOTICE (warning, turn_interrupted): Turn t1 was interrupted" in text and "session_resumed" not in text
    assert "m2 cost (USD)" in text                                    # the usage block follows the latest model


# --- subcommands and the exit hint -------------------------------------------------------------

def test_export_subcommand_to_stdout_and_file(tmp_path, capsys):
    root = workspace(tmp_path)
    save_session(root, "older")
    sid = save_session(root, "the question", "the answer")
    assert cli_mod.main(["export", "latest", "--workspace", str(root)]) == 0
    out = capsys.readouterr().out
    assert "**USER:** the question" in out and "**AGENT:** the answer" in out and "older" not in out
    target = tmp_path / "e.md"
    assert cli_mod.main(["export", sid[2:8], "-o", str(target), "--workspace", str(root)]) == 0
    assert target.read_text(encoding="utf-8") == out and str(target) in capsys.readouterr().out
    assert cli_mod.main(["export", "ffff0000", "--workspace", str(root)]) == 2
    assert "No saved session matches" in capsys.readouterr().err


def test_sessions_subcommand_lists_all_and_honours_limit(tmp_path, capsys):
    root = workspace(tmp_path)
    assert cli_mod.main(["sessions", "--workspace", str(root)]) == 0
    assert "No saved sessions" in capsys.readouterr().out
    for n in range(12):
        save_session(root, f"task {n}")
    cli_mod.main(["sessions", "--workspace", str(root)])
    assert len(re.findall(r"^[ *] ?\d+  s_", capsys.readouterr().out, re.M)) == 12
    cli_mod.main(["sessions", "--workspace", str(root), "--limit", "3"])
    out = capsys.readouterr().out
    assert len(re.findall(r"^[ *] ?\d+  s_", out, re.M)) == 3 and "task 11" in out and "\x1b[" not in out


def test_sessions_delete_removes_only_the_named_sessions(tmp_path, capsys):
    root = workspace(tmp_path)
    a, b, c = (save_session(root, t) for t in "abc")
    store = SessionStore.for_workspace(root)
    assert cli_mod.main(["sessions", "delete", a, b[2:8], "--workspace", str(root)]) == 0
    out = capsys.readouterr().out
    assert f"Deleted {a}" in out and f"Deleted {b}" in out
    assert [i.session_id for i in store.list()] == [c]
    assert cli_mod.main(["sessions", "delete", "ffff0000", "--workspace", str(root)]) == 2
    with pytest.raises(SystemExit):
        cli_mod.main(["sessions", "delete", "--workspace", str(root)])


def test_sessions_delete_refuses_a_session_that_is_open(tmp_path, capsys):
    root = workspace(tmp_path)
    s, q, fake, store = open_cli(root, [[msg("x")]])
    s.start_turn("keep me")
    assert s.wait(10)
    try:
        assert cli_mod.main(["sessions", "delete", s.session_id, "--workspace", str(root)]) == 2
    finally:
        s.close()
    assert "open in another agent_v3 process" in capsys.readouterr().err
    assert store.list()


def test_exit_hint_only_for_a_saved_session_with_turns(tmp_path, capsys):
    root = workspace(tmp_path)
    s, q, fake, store = open_cli(root, [[msg("a")]])
    run_cli(s, q, ["task"], store=store)
    out = capsys.readouterr().out
    assert f"Session saved: {s.session_id} - resume with: python -m agent_v3" in out
    assert f"--resume {s.session_id[2:]}" in out
    assert out.index("Total cost (USD)") < out.index("Session saved:")

    s, q, fake, store = open_cli(root, [])                            # saved, but no turn: nothing on disk
    run_cli(s, q, [], store=store)
    assert "Session saved" not in capsys.readouterr().out

    s, q, fake, _ = open_cli(root, [[msg("a")]], saved=False)         # --no-save
    run_cli(s, q, ["task"])
    assert "Session saved" not in capsys.readouterr().out


def test_events_log_still_works_next_to_saving(tmp_path, monkeypatch, configs):
    root = workspace(tmp_path)
    type_input(monkeypatch, "ping")
    log = tmp_path / "events.jsonl"
    assert cli_mod.main(["--workspace", str(root), "--events-log", str(log)]) == 0
    assert '"type": "turn_completed"' in log.read_text(encoding="utf-8") and SessionStore.for_workspace(root).list()
    assert EventLogWriter  # the sink class is unchanged


def test_no_save_writes_nothing_to_the_workspace(tmp_path, monkeypatch, configs):
    root = workspace(tmp_path)
    type_input(monkeypatch, "ping")
    assert cli_mod.main(["--workspace", str(root), "--no-save"]) == 0
    assert not (root / ".agent_v3").exists()

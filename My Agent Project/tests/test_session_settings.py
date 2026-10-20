"""Changing settings mid-session (sessions spec §5.6, Phase S5): `Session.update_config`, `ModelAdapter.set_config`,
`config_changed` on disk, and `SessionStore.read_events` paging.
"""
import json
import time

import httpx
import openai
import pytest

from conftest import EventLog, FakeModelAdapter, Round, fn_call, msg, reasoning_item, usage

from agent_v3.config import AgentConfig
from agent_v3.model import ModelAdapter, request_timeout
from agent_v3.pricing import Usage, cost_usd
from agent_v3.session import Busy, Session
from agent_v3.sessions import SessionNotFound, SessionStore, config_for_resume


def run(session, text="go", timeout=10):
    tid = session.start_turn(text)
    assert session.wait(timeout), "turn did not finish"
    return tid


def kinds(items):
    return [i.get("type") or f"msg:{i['role']}" for i in items]


def bad_request(message, param=None):
    req = httpx.Request("POST", "https://api.openai.com/v1/responses")
    return openai.BadRequestError(message, response=httpx.Response(400, request=req),
                                  body={"message": message, "param": param, "type": "invalid_request_error"})


def wait_blocked(fake, timeout=5):
    deadline = time.monotonic() + timeout
    while not (fake.streams and fake.streams[-1].blocked.wait(0.01)):
        assert time.monotonic() < deadline, "the model round never started"


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
    """open_session(rounds, resume=None, saved=True, **config) -> (session, fake, log)."""
    made = []

    def make(rounds, resume=None, saved=True, **cfg):
        cfg.setdefault("web_search", False)
        config = AgentConfig(workspace=ws, **cfg)
        fake = FakeModelAdapter(config, rounds)
        log = EventLog()
        session = Session(config, log, model=fake, store=store if saved else None, resume=resume)
        made.append(session)
        return session, fake, log

    yield make
    for s in made:
        s.close()


# -- preconditions -----------------------------------------------------------------------------

def test_update_config_needs_an_idle_session_and_valid_values(open_session):
    s, fake, log = open_session([Round(output=[msg("never")], block="cancel")], saved=False)
    s.start_turn("hold")
    wait_blocked(fake)
    with pytest.raises(Busy):
        s.update_config(reasoning="low")
    s.cancel()
    assert s.wait(5)

    before = (s.config, s.system_prompt, s.cache_key, list(s.history))
    for bad in ({"reasoning": "extreme"}, {"approval": "yolo"}, {"model": ""}, {"model": "  "}, {"model": 5},
                {"reasoning": "low", "approval": "nope"}):           # all or nothing: low is not applied either
        with pytest.raises(ValueError):
            s.update_config(**bad)
    assert (s.config, s.system_prompt, s.cache_key, list(s.history)) == before
    assert log.of("config_changed") == []

    assert s.update_config(model=s.config.model, reasoning=s.config.reasoning, approval="ask") == {}
    assert s.update_config() == {}
    same = log.of("config_changed")
    assert len(same) == 2 and all(e.changes == {} and e.history == "unchanged" for e in same)
    assert same[0].config == {**s.config.summary(), "tools": s.registry.names()} and same[0].turn_id is None


# -- model -------------------------------------------------------------------------------------

def test_a_model_change_uses_the_new_model_and_its_rates(open_session):
    s, fake, log = open_session([Round(output=[msg("a1")], usage=usage(1000, 0, 100)),
                                 Round(output=[msg("a2")], usage=usage(1000, 0, 100))], saved=False)
    run(s, "first")
    history = list(s.history)
    assert s.update_config(model="gpt-5.6-sol") == {"model": ["gpt-6-luna", "gpt-5.6-sol"]}
    changed = log.of("config_changed")[-1]
    assert changed.changes == {"model": {"from": "gpt-6-luna", "to": "gpt-5.6-sol"}}
    assert changed.config["model"] == "gpt-5.6-sol" and changed.history == "unchanged"
    assert s.history == history                                       # pruned turns are valid for any model
    run(s, "second")
    assert [r["model"] for r in fake.requests] == ["gpt-6-luna", "gpt-5.6-sol"]
    first, second = (e.cost_usd for e in log.of("model_round_completed"))
    expected = cost_usd("gpt-5.6-sol", Usage(input_tokens=1000, output_tokens=100))
    assert second == pytest.approx(expected) and second > first * 10
    assert fake.requests[1]["input"][:len(history)] == history          # same prefix, the new model reads all of it


def test_a_model_change_with_full_turns_falls_back_to_their_records(open_session):
    s, fake, log = open_session([
        [reasoning_item(), fn_call("list_dir", path=".")], [reasoning_item(), msg("listed")], [msg("next")]],
        saved=False, prune_history=False, approval="full-auto")
    assert s.update_config(model="gpt-5.6-luna") and log.of("config_changed")[-1].history == "unchanged"   # no turns
    run(s, "list it")
    full = kinds(s.history[1:])
    assert "reasoning" in full and "function_call" in full
    s.update_config(model="gpt-6-luna")
    assert log.of("config_changed")[-1].history == "pruned"
    assert kinds(s.history[1:]) == ["msg:user", "msg:assistant", "msg:developer"]
    assert s.history[2]["content"] == "listed" and s.history[3]["content"].startswith("Turn record: ")
    run(s, "again")
    assert not {"reasoning", "function_call", "function_call_output"} & set(kinds(fake.requests[-1]["input"]))
    assert kinds(s.history[4:]) == ["msg:user", "message"]           # the new turn is kept in full again
    s.update_config(reasoning="low")                                 # not a model change: full turns stay
    assert log.of("config_changed")[-1].history == "unchanged"


def test_a_resumed_full_session_tracks_the_pruned_form_too(open_session, store):
    first, _, _ = open_session([[reasoning_item(), msg("one")], [msg("two")]], prune_history=False)
    run(first, "q1")
    sid = first.session_id
    first.close()
    s, fake, log = open_session([[msg("three")]], resume=sid, prune_history=False)
    assert log.of("session_resumed")[0].history == "full" and "reasoning" in kinds(s.history[1:])
    s.update_config(model="gpt-5.6-sol")
    assert log.of("config_changed")[-1].history == "pruned"
    assert s.history[1:] == store.load(sid).turn_lines[0]["record"]


def test_an_unknown_model_gets_its_own_pricing_notice(open_session):
    s, fake, log = open_session([[msg("a")], [msg("b")], [msg("c")]], saved=False, model="mystery-1")
    run(s)
    s.update_config(reasoning="low")
    run(s)
    assert len([n for n in log.of("notice") if n.code == "unknown_pricing"]) == 1     # once per model
    s.update_config(model="mystery-2")
    run(s)
    notices = [n.message for n in log.of("notice") if n.code == "unknown_pricing"]
    assert len(notices) == 2 and "mystery-2" in notices[1]


# -- approval ----------------------------------------------------------------------------------

def test_an_approval_change_rebuilds_the_prompt_and_forgets_allowances(open_session, ws):
    (ws / "a.py").write_text("x = 1\n", encoding="utf-8")
    s, fake, log = open_session([
        [fn_call("run_command", command="echo hi")], [msg("ran")],
        [fn_call("edit_files", edits=[{"path": "a.py", "old_text": "x = 1", "new_text": "x = 2"}])],
        [fn_call("run_command", command="echo hi")], [msg("done")]], saved=False)
    s.start_turn("run it")
    req = log.wait_for("approval_requested").request
    s.respond_approval(req["request_id"], "allow_session")
    assert s.wait(10)
    old_prompt, old_key = s.system_prompt, s.cache_key
    assert "Approval mode: ask" in old_prompt

    assert s.update_config(approval="auto-edit") == {"approval": ["ask", "auto-edit"]}
    assert "Approval mode: auto-edit" in s.system_prompt and s.cache_key != old_key
    assert s.history[0] == {"role": "system", "content": s.system_prompt} and len(s.history) == 4
    assert s.approvals.policy is s.policy and s.policy.mode == "auto-edit" and not s.policy.session_commands

    s.start_turn("edit, then run it again")
    req = log.wait_for("approval_requested", n=2).request              # the edit went through without asking
    assert req["kind"] == "command" and req["command"] == "echo hi"    # the session allowance is gone
    s.respond_approval(req["request_id"], "allow")
    assert s.wait(10)
    assert (ws / "a.py").read_text(encoding="utf-8") == "x = 2\n"
    later = fake.requests[2]
    assert later["input"][0]["content"] == s.system_prompt and later["prompt_cache_key"] == s.cache_key
    assert fake.requests[0]["prompt_cache_key"] == old_key


# -- reasoning ---------------------------------------------------------------------------------

def test_a_reasoning_change_keeps_the_prompt_and_cache_key(open_session):
    s, fake, log = open_session([[msg("a")], [msg("b")]], saved=False)
    client = fake._client
    run(s)
    prompt, key = s.system_prompt, s.cache_key
    assert s.update_config(reasoning="high") == {"reasoning": ["medium", "high"]}
    run(s)
    assert [r["reasoning"] for r in fake.requests] == [{"effort": "medium"}, {"effort": "high"}]
    assert s.system_prompt == prompt and s.cache_key == key
    assert fake.requests[1]["prompt_cache_key"] == key and fake.requests[1]["input"][0]["content"] == prompt
    assert fake._client is client                                     # an injected client is never rebuilt


def test_the_adapter_rebuilds_only_a_client_it_built(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-used")
    config = AgentConfig(workspace=tmp_path, reasoning="medium")
    adapter = ModelAdapter(config)
    adapter.dropped_params.add("prompt_cache_key")
    built = adapter.client
    adapter.set_config(AgentConfig(workspace=tmp_path, reasoning="low"))           # same timeout tier
    assert adapter.client is built
    adapter.set_config(AgentConfig(workspace=tmp_path, reasoning="high"))          # longer read timeout
    rebuilt = adapter.client
    assert rebuilt is not built and rebuilt.timeout == request_timeout("high")
    assert built.is_closed()                                                       # its connections are not left open
    assert adapter.config.reasoning == "high" and adapter.dropped_params == {"prompt_cache_key"}

    injected = object()
    adapter = ModelAdapter(config, client=injected)
    adapter.set_config(AgentConfig(workspace=tmp_path, reasoning="xhigh"))
    assert adapter.client is injected


# -- saving ------------------------------------------------------------------------------------

def test_a_change_is_saved_and_a_resume_restores_model_and_reasoning_but_not_approval(open_session, store, ws):
    s, fake, log = open_session([[msg("one")], [msg("two")]])
    run(s, "first")
    sid = s.session_id
    s.update_config(model="gpt-5.6-sol", reasoning="high", approval="full-auto")
    meta = json.loads((store.session_dir(sid) / "meta.json").read_text(encoding="utf-8"))
    assert (meta["model"], meta["reasoning"], meta["approval"]) == ("gpt-5.6-sol", "high", "full-auto")   # at once
    saved = [json.loads(line) for line in store.events_path(sid).read_text(encoding="utf-8").splitlines()]
    assert saved[-1]["type"] == "config_changed" and saved[-1]["changes"]["approval"]["to"] == "full-auto"
    run(s, "second")
    s.close()
    lines = store.load(sid).turn_lines
    assert [line["model"] for line in lines] == ["gpt-6-luna", "gpt-5.6-sol"]   # each turn tagged with its model

    launch = AgentConfig(workspace=ws, web_search=False)
    for meta_present in (True, False):
        if not meta_present:
            (store.session_dir(sid) / "meta.json").unlink()            # rebuilt from the logs: same answer
        info = store.load(sid).info
        resumed = config_for_resume(launch, info, set())
        assert (resumed.model, resumed.reasoning, resumed.approval) == ("gpt-5.6-sol", "high", "ask")
    assert store.list()[0].model == "gpt-5.6-sol"


def test_a_change_before_the_first_turn_is_saved_with_it(open_session, store):
    s, fake, log = open_session([[msg("one")]])
    s.update_config(model="gpt-5.6-sol")
    assert not store.root.exists()                                    # still nothing on disk before a turn
    run(s, "first")
    s.close()
    saved = [d["type"] for d in store.read_events(s.session_id)[0]]
    assert saved[:3] == ["session_started", "config_changed", "turn_started"]
    assert store.load(s.session_id).turn_lines[0]["model"] == "gpt-5.6-sol"
    assert store.load(s.session_id).info.model == "gpt-5.6-sol"


# -- read_events -------------------------------------------------------------------------------

def test_read_events_pages_in_order_without_text_deltas(open_session, store):
    s, fake, log = open_session([[msg("first answer has words")], [msg("second answer too")]])
    run(s, "one")
    s.update_config(reasoning="low")
    run(s, "two")
    s.close()
    sid = s.session_id
    wire = [e.to_dict() for e in log.events if e.type != "text_delta"]
    assert any(e.type == "text_delta" for e in log.events)

    events, done = store.read_events(sid)
    assert done and events == wire and all(d["type"] != "text_delta" for d in events)

    pages, after = [], 0
    while True:
        page, done = store.read_events(sid, after_seq=after, limit=3)
        pages.append(page)
        if done:
            break
        assert len(page) == 3
        after = page[-1]["seq"]
    assert [d for page in pages for d in page] == wire
    assert store.read_events(sid, after_seq=wire[-1]["seq"]) == ([], True)
    assert store.read_events(sid, after_seq=wire[-4]["seq"], limit=3) == (wire[-3:], True)   # exactly the rest
    assert store.read_events(sid, after_seq=wire[2]["seq"] - 1, limit=1) == ([wire[2]], False)

    with store.events_path(sid).open("ab") as f:
        f.write(b'{"type": "notice", "seq": 999, "lev')                 # a torn last line
    assert store.read_events(sid) == (wire, True)

    with pytest.raises(SessionNotFound):
        store.read_events("s_ffffffffffff")
    (store.root / "s_000000000000").mkdir()                              # a folder with no log
    with pytest.raises(SessionNotFound):
        store.read_events("s_000000000000")


# -- final review regressions --------------------------------------------------------------------

def test_a_model_change_retries_the_include_values_the_old_model_rejected(open_session):
    """#1: an include value one model rejected is tried again on the next model; a rejected cache key stays dropped."""
    include_err = bad_request("Invalid value: 'reasoning.encrypted_content'. Supported values are: ...", param="include")
    key_err = bad_request("Unknown parameter: 'prompt_cache_key'.", param="prompt_cache_key")
    s, fake, log = open_session([Round(output=[msg("a")], error=include_err), Round(output=[msg("b")], error=key_err),
                                 [msg("c")], Round(output=[msg("d")], error=include_err)], saved=False)
    run(s, "first")
    assert "include" in fake.requests[0] and "include" not in fake.requests[1]
    s.update_config(reasoning="low")                                   # not a model change: still dropped
    run(s, "second")
    assert "include" not in fake.requests[2] and "prompt_cache_key" not in fake.requests[3]
    s.update_config(model="gpt-5.6-sol")
    run(s, "third")
    assert fake.requests[4]["include"] == ["reasoning.encrypted_content"] and "prompt_cache_key" not in fake.requests[4]
    s.update_config(model="gpt-5.6-luna")
    run(s, "fourth")                                                   # rejected again: the fallback drops it again
    assert "include" in fake.requests[5] and "include" not in fake.requests[6]
    assert [n.code for n in log.of("notice")].count("include_rejected") == 2
    assert [e.type for e in log.events].count("turn_completed") == 4


def test_a_change_that_cannot_rebuild_the_prompt_changes_nothing(open_session, ws, tmp_path):
    """#2: the prompt file is read before anything is swapped in; on an error nothing is applied or emitted."""
    prompt = tmp_path / "prompt.md"
    prompt.write_text("You are a test agent.", encoding="utf-8")
    s, fake, log = open_session([[msg("a")], [msg("b")]], saved=False, prompt_path=prompt)
    before = (s.config, s.policy, s.approvals.policy, s.system_prompt, s.cache_key, list(s.history), fake.config)
    prompt.unlink()
    with pytest.raises(FileNotFoundError):
        s.update_config(model="gpt-5.6-sol", approval="auto-edit")
    assert (s.config, s.policy, s.approvals.policy, s.system_prompt, s.cache_key, list(s.history), fake.config) == before
    assert log.of("config_changed") == []
    run(s)
    assert fake.requests[0]["model"] == "gpt-6-luna" and "Approval mode: ask" in fake.requests[0]["input"][0]["content"]
    assert s.update_config(model="gpt-5.6-sol") == {"model": ["gpt-6-luna", "gpt-5.6-sol"]}   # needs no prompt
    run(s)
    assert fake.requests[1]["model"] == "gpt-5.6-sol"


def test_a_model_name_is_stripped(open_session):
    """#3: surrounding spaces never reach the config, the event or the request."""
    s, fake, log = open_session([[msg("a")]], saved=False)
    assert s.update_config(model="  gpt-5.6-sol\t") == {"model": ["gpt-6-luna", "gpt-5.6-sol"]}
    assert s.config.model == "gpt-5.6-sol" and log.of("config_changed")[-1].config["model"] == "gpt-5.6-sol"
    assert s.update_config(model=" gpt-5.6-sol ") == {}
    run(s)
    assert fake.requests[0]["model"] == "gpt-5.6-sol"


def test_read_events_decodes_each_line_once_and_follows_the_growing_log(open_session, store, ws, monkeypatch):
    """#4: pages seek through an index instead of decoding the log from the start; results are unchanged."""
    s, fake, log = open_session([[msg(f"answer {n}")] for n in range(7)])
    for n in range(6):
        run(s, f"question {n}")
    sid = s.session_id
    everything, done = store.read_events(sid)                          # builds the index
    assert done and len(everything) > 20

    decoded = []
    real_loads = json.loads
    monkeypatch.setattr(json, "loads", lambda text, *a, **kw: decoded.append(text) or real_loads(text, *a, **kw))
    page, done = store.read_events(sid, after_seq=everything[-5]["seq"], limit=2)
    assert page == everything[-4:-2] and not done
    assert len(decoded) == 2                                           # the page's two lines, nothing else

    run(s, "question 6")                                               # the log grows while the session is open
    s.close()
    decoded.clear()
    grown, done = store.read_events(sid, after_seq=everything[-1]["seq"])
    assert done and grown and grown[0]["type"] == "turn_started" and grown[-1]["type"] == "turn_completed"
    assert len(decoded) == 2 * len(grown)                              # each new line indexed once, then read once
    monkeypatch.undo()
    fresh = SessionStore.for_workspace(ws)                             # same answers as an index built from scratch
    assert store.read_events(sid) == fresh.read_events(sid) == (everything + grown, True)

    path = store.events_path(sid)
    line = json.dumps({"type": "notice", "seq": grown[-1]["seq"] + 1, "level": "info", "code": "x", "message": "m"})
    with path.open("ab") as f:
        f.write(line[:20].encode())                                    # torn: left out, and not indexed
    assert store.read_events(sid, after_seq=grown[-1]["seq"]) == ([], True)
    with path.open("ab") as f:
        f.write(line[20:].encode() + b"\n")                            # completed later: now it is there
    assert store.read_events(sid, after_seq=grown[-1]["seq"]) == ([json.loads(line)], True)


def test_models_used_covers_every_turn_including_restored_ones(open_session):
    """#7: the usage label's source. Restored turns count; a model set but never used does not."""
    s, fake, log = open_session([[msg("a")], [msg("b")]])
    assert s.models_used == []
    run(s)
    s.update_config(model="gpt-5.6-sol")
    assert s.models_used == ["gpt-6-luna"]
    run(s)
    s.update_config(model="gpt-5.6-terra")
    assert s.models_used == ["gpt-6-luna", "gpt-5.6-sol"]
    sid = s.session_id
    s.close()
    resumed, _, _ = open_session([], resume=sid, model="gpt-5.6-terra")
    assert resumed.models_used == ["gpt-6-luna", "gpt-5.6-sol"]

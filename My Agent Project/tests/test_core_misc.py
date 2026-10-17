"""Unit tests for events, pricing, prompt, config and the model adapter's helpers."""
import json
from datetime import date
from pathlib import Path

import pytest
from openai.types.responses import ResponseUsage

from conftest import FakeModelAdapter, msg, reasoning_item, web_call

from agent_v3 import events as ev
from agent_v3.config import AgentConfig
from agent_v3.model import ModelAdapter, as_dict, cited_sources, describe_web_action, output_text, request_timeout, web_tools
from agent_v3.pricing import PRICING, Usage, cost_usd, rates_for
from agent_v3.prompt import build_system_prompt, environment_block, prompt_cache_key


# --- events ----------------------------------------------------------------------------------

def test_event_types_cover_the_protocol():
    assert set(ev.EVENT_TYPES) == {
        "session_started", "turn_started", "model_round_started", "text_delta", "model_retry",
        "model_round_completed", "web_action", "tool_started", "tool_completed", "approval_requested",
        "approval_resolved", "notice", "turn_completed", "turn_cancelled", "turn_failed"}
    assert ev.PROTOCOL_VERSION == 1


def test_to_dict_is_json_safe_and_flat():
    e = ev.ToolCompleted(turn_id="t1", call_id="c", name="read_file", group=3, ok=True, summary="1 line",
                         error_code=None, duration_s=0.01, output="x", metadata={"path": Path("a.py"), "r": (1, 2)})
    d = e.to_dict()
    assert d["type"] == "tool_completed" and d["turn_id"] == "t1" and d["seq"] == 0
    assert d["metadata"] == {"path": "a.py", "r": [1, 2]}
    json.dumps(d)


def test_events_are_frozen():
    e = ev.Notice(level="info", code="x", message="m")
    with pytest.raises(Exception):
        e.code = "y"


# --- pricing ---------------------------------------------------------------------------------

def test_cost_formula():
    u = Usage(input_tokens=1_000_000, cached_tokens=250_000, output_tokens=100_000, reasoning_tokens=40_000)
    r = PRICING["gpt-5.6-sol"]
    assert cost_usd("gpt-5.6-sol", u) == pytest.approx(0.75 * r["input"] + 0.25 * r["cached"] + 0.1 * r["output"])


def test_rates_for_snapshots_and_unknown():
    assert rates_for("gpt-5-mini-2025-08-07") == PRICING["gpt-5-mini"]       # longest prefix, not "gpt-5"
    assert rates_for("gpt-5.6-luna") == PRICING["gpt-5.6-luna"]
    assert rates_for("mystery") is None and cost_usd("mystery", Usage()) is None


def test_usage_from_sdk_object_and_dict():
    sdk = ResponseUsage(input_tokens=10, input_tokens_details={"cached_tokens": 4, "cache_write_tokens": 0}, output_tokens=7,
                        output_tokens_details={"reasoning_tokens": 2}, total_tokens=17)
    assert Usage.from_api(sdk) == Usage(10, 4, 7, 2)
    assert Usage.from_api(as_dict(sdk)) == Usage(10, 4, 7, 2)
    assert Usage.from_api(None) == Usage() and Usage.from_api({"input_tokens": 3}) == Usage(3, 0, 0, 0)


# --- model helpers ---------------------------------------------------------------------------

def test_build_params(tmp_path):
    cfg = AgentConfig(workspace=tmp_path, reasoning="low")
    params = FakeModelAdapter(cfg, []).build_params([{"role": "user", "content": "x"}], [], "auto", "agent_v3:s")
    assert params["store"] is False and params["reasoning"] == {"effort": "low"}
    assert params["include"] == ["reasoning.encrypted_content", "web_search_call.action.sources"]
    assert params["prompt_cache_key"] == "agent_v3:s"
    stored = AgentConfig(workspace=tmp_path, store=True, web_search=False)
    p2 = FakeModelAdapter(stored, []).build_params([], [], "none", None)
    assert p2["store"] is True and "include" not in p2 and "prompt_cache_key" not in p2


def test_request_timeout_scales_with_reasoning(tmp_path):
    for effort in ("none", "minimal", "low", "medium"):
        assert request_timeout(effort).read == 120
    for effort in ("high", "xhigh"):
        assert request_timeout(effort).read == 300
    assert request_timeout("medium").connect == 15
    client = ModelAdapter(AgentConfig(workspace=tmp_path, reasoning="high", model="gpt-5.6-sol")).client
    assert client.timeout.read == 300


def test_web_tools(tmp_path):
    assert web_tools(AgentConfig(workspace=tmp_path, web_search=False)) == []
    assert web_tools(AgentConfig(workspace=tmp_path, search_context_size="high")) == [
        {"type": "web_search", "search_context_size": "high"}]


def test_describe_web_action():
    assert describe_web_action({"type": "search", "queries": ["a", "b"]}) == ("search", "'a', 'b'")
    assert describe_web_action({"type": "search", "query": "a"}) == ("search", "'a'")
    assert describe_web_action({"type": "open_page", "url": "https://x"}) == ("open_page", "https://x")
    assert describe_web_action({"type": "find_in_page", "pattern": "p", "url": "u"}) == ("find_in_page", "'p' in u")
    assert describe_web_action(None) == ("search", "")


def test_output_text_and_sources():
    items = [reasoning_item(), web_call("q"), msg("Hello ", [("A", "https://a")]), msg("world", [("A", "https://a")])]
    assert output_text(items) == "Hello world"
    assert cited_sources(items) == [{"title": "A", "url": "https://a"}]


# --- prompt ----------------------------------------------------------------------------------

def test_prompt_composition(tmp_path):
    (tmp_path / ".git").mkdir()
    cfg = AgentConfig(workspace=tmp_path, approval="auto-edit")
    text = build_system_prompt(cfg, today=date(2026, 10, 9))
    assert text.startswith("# Role") and "# Web search" in text
    env = text[text.index("## Environment"):]
    assert env.rstrip().splitlines() == [
        "## Environment", f"- Workspace: {tmp_path.resolve()}", env.splitlines()[2],
        "- Run Python tools via `python -m` (e.g. `python -m pytest`); bare `pytest` may not be on PATH",
        "- Date: 2026-10-09",
        "- Approval mode: auto-edit (workspace edits are automatic; commands need user approval)",
        "- Git repository: yes"]
    assert text.index("# Web search") < text.index("## Environment")
    assert build_system_prompt(cfg, today=date(2026, 10, 9)) == text        # stable within a session


def test_prompt_without_web_and_with_override(tmp_path):
    custom = tmp_path / "p.md"
    custom.write_text("# Custom\nBe brief.\n", encoding="utf-8")
    cfg = AgentConfig(workspace=tmp_path, web_search=False, prompt_path=custom)
    text = build_system_prompt(cfg)
    assert text.startswith("# Custom\nBe brief.") and "# Web search" not in text
    assert "- Git repository: no" in environment_block(cfg) or "- Git repository: yes" in environment_block(cfg)


def test_prompt_cache_key_is_stable_and_tracks_the_prefix(tmp_path):
    tools = [{"type": "function", "name": "read_file", "description": "Read.", "parameters": {}}]
    key = prompt_cache_key(tmp_path, "# Role", tools)
    assert key == prompt_cache_key(tmp_path, "# Role", [dict(t) for t in tools])         # same inputs, same key
    assert key.startswith("agent_v3:") and len(key) == len("agent_v3:") + 32
    assert key != prompt_cache_key(tmp_path / "other", "# Role", tools)                  # workspace
    assert key != prompt_cache_key(tmp_path, "# Role!", tools)                           # system prompt
    assert key != prompt_cache_key(tmp_path, "# Role", [{**tools[0], "description": "Read it."}])  # schemas
    assert key != prompt_cache_key(tmp_path, "# Role", tools + tools)                   # tool list


# --- config ----------------------------------------------------------------------------------

def test_config_validation(tmp_path):
    for kw in [{"approval": "auto"}, {"reasoning": "max"}, {"search_context_size": "huge"}, {"max_rounds": 0}]:
        with pytest.raises(ValueError):
            AgentConfig(workspace=tmp_path, **kw)


def test_config_summary(tmp_path):
    s = AgentConfig(workspace=str(tmp_path)).summary()
    assert s == {"model": "gpt-6-luna", "reasoning": "medium", "approval": "ask",
                 "workspace": str(tmp_path.resolve()), "web_search": True}

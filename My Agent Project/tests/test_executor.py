import threading
import time

from pydantic import BaseModel, Field

from agent_v3.config import AgentConfig
from agent_v3.tools.executor import ToolCall, ToolExecutor
from agent_v3.tools.registry import ErrorCode, ToolRegistry, ToolResult, ToolSpec


class Args(BaseModel):
    label: str = Field(description="Label.")
    delay: float | None = Field(default=None, description="Seconds to sleep. Default 0.")


class Recorder:
    """Fake tools that log start/finish times so tests can see what overlapped."""

    def __init__(self):
        self.events: list[tuple[str, str]] = []
        self.lock = threading.Lock()
        self.active = 0
        self.max_active = 0
        self.cancel_on: str | None = None
        self.cancel = None

    def tool(self, kind):
        def func(args, ctx):
            with self.lock:
                self.events.append(("start", args.label))
                self.active += 1
                self.max_active = max(self.max_active, self.active)
            time.sleep(args.delay or 0)
            if self.cancel_on == args.label:
                self.cancel.cancel()
            with self.lock:
                self.active -= 1
                self.events.append(("end", args.label))
            return ToolResult.success(f"{kind}:{args.label}", args.label)
        return func

    def registry(self):
        return ToolRegistry([
            ToolSpec("read", Args, self.tool("read"), True, "read"),
            ToolSpec("search", Args, self.tool("search"), True, "search"),
            ToolSpec("edit", Args, self.tool("edit"), False, "edit"),
        ])

    def started(self):
        return [label for kind, label in self.events if kind == "start"]


def call(i, name, label, delay=0.0):
    import json
    return ToolCall(f"call_{i}", name, json.dumps({"label": label, "delay": delay}))


def make(env, rec, **cfg):
    events = []
    ex = ToolExecutor(rec.registry(), AgentConfig(**cfg), emit=lambda t, d: events.append((t, d)))
    rec.cancel = env.cancel
    return ex, events


def test_read_read_search_edit_read_grouping_and_order(env):
    rec = Recorder()
    ex, events = make(env, rec)
    calls = [call(1, "read", "r1", 0.3), call(2, "read", "r2", 0.3), call(3, "search", "s", 0.3),
             call(4, "edit", "e", 0.05), call(5, "read", "r3", 0.05)]
    t0 = time.monotonic()
    results = ex.run_batch(calls, env.ctx())
    elapsed = time.monotonic() - t0

    assert [c.call_id for c, _, _ in results] == [f"call_{i}" for i in range(1, 6)]
    assert [r.output for _, r, _ in results] == ["read:r1", "read:r2", "search:s", "edit:e", "read:r3"]
    assert rec.max_active == 3                           # r1, r2, s overlapped; nothing else did
    assert elapsed < 0.3 * 3 * 0.8 + 0.4                 # ≈0.3 (parallel) + small, not 0.9 serial

    ends = {l: i for i, (k, l) in enumerate(rec.events) if k == "end"}
    starts = {l: i for i, (k, l) in enumerate(rec.events) if k == "start"}
    assert max(ends["r1"], ends["r2"], ends["s"]) < starts["e"]       # edit is a barrier
    assert ends["e"] < starts["r3"]

    groups = {d["call_id"]: d["group"] for t, d in events if t == "tool_started"}
    assert groups["call_1"] == groups["call_2"] == groups["call_3"]
    assert len({groups["call_3"], groups["call_4"], groups["call_5"]}) == 3
    assert [d["call_id"] for t, d in events if t == "tool_completed"].count("call_4") == 1


def test_results_in_call_order_when_completion_order_differs(env):
    rec = Recorder()
    ex, _ = make(env, rec)
    calls = [call(1, "read", "slow", 0.4), call(2, "read", "mid", 0.2), call(3, "read", "fast", 0.0)]
    results = ex.run_batch(calls, env.ctx())
    assert [r.output for _, r, _ in results] == ["read:slow", "read:mid", "read:fast"]
    finish_order = [l for k, l in rec.events if k == "end"]
    assert finish_order == ["fast", "mid", "slow"]               # really did complete out of order
    assert results[0][2] >= 0.35 and results[2][2] < 0.2         # durations are per call


def test_non_read_only_calls_never_overlap_and_keep_order(env):
    rec = Recorder()
    ex, _ = make(env, rec)
    ex.run_batch([call(1, "edit", "e1", 0.1), call(2, "edit", "e2", 0.1), call(3, "edit", "e3", 0.0)], env.ctx())
    assert rec.max_active == 1 and rec.started() == ["e1", "e2", "e3"]


def test_parallel_reads_can_be_disabled(env):
    rec = Recorder()
    ex, events = make(env, rec, parallel_reads=False)
    ex.run_batch([call(1, "read", "a", 0.05), call(2, "read", "b", 0.05)], env.ctx())
    assert rec.max_active == 1
    groups = [d["group"] for t, d in events if t == "tool_started"]
    assert len(set(groups)) == 2


def test_max_parallel_reads_bounds_the_pool(env):
    rec = Recorder()
    ex, _ = make(env, rec, max_parallel_reads=2)
    ex.run_batch([call(i, "read", f"r{i}", 0.1) for i in range(1, 6)], env.ctx())
    assert rec.max_active == 2


def test_events_started_and_completed_fields(env):
    rec = Recorder()
    ex, events = make(env, rec)
    ex.run_batch([call(1, "read", "a")], env.ctx())
    [started] = [d for t, d in events if t == "tool_started"]
    [done] = [d for t, d in events if t == "tool_completed"]
    assert started["name"] == "read" and started["args"] == {"label": "a", "delay": 0.0}
    assert done["ok"] is True and done["summary"] == "a" and done["output"] == "read:a" and done["error_code"] is None


def test_cancel_mid_batch_gives_cancelled_outputs_for_the_rest(env):
    rec = Recorder()
    rec.cancel_on = "e1"
    ex, events = make(env, rec)
    calls = [call(1, "read", "r1"), call(2, "edit", "e1"), call(3, "read", "r2"), call(4, "read", "r3"),
             call(5, "edit", "e2")]
    results = ex.run_batch(calls, env.ctx())
    assert [r.ok for _, r, _ in results] == [True, True, False, False, False]
    for _, r, _ in results[2:]:
        assert r.error_code == ErrorCode.CANCELLED
        assert r.output == "Error (cancelled): Cancelled by user before running."
    assert rec.started() == ["r1", "e1"]                         # nothing started after the cancel
    assert len(results) == len(calls)                            # every function_call still gets an output
    completed = [d["call_id"] for t, d in events if t == "tool_completed"]
    assert sorted(completed) == [f"call_{i}" for i in range(1, 6)]


def test_cancel_before_batch(env):
    rec = Recorder()
    ex, _ = make(env, rec)
    env.cancel.cancel()
    results = ex.run_batch([call(1, "read", "a"), call(2, "read", "b")], env.ctx())
    assert all(r.error_code == ErrorCode.CANCELLED for _, r, _ in results) and rec.events == []


def test_unknown_and_invalid_calls_inside_a_batch(env):
    rec = Recorder()
    ex, _ = make(env, rec)
    calls = [call(1, "read", "ok"), ToolCall("call_2", "bogus", "{}"), ToolCall("call_3", "read", "{bad"),
             call(4, "read", "ok2")]
    results = ex.run_batch(calls, env.ctx())
    assert [r.error_code for _, r, _ in results] == [None, ErrorCode.UNKNOWN_TOOL, ErrorCode.INVALID_ARGUMENTS, None]
    assert rec.started() == ["ok", "ok2"]


def test_empty_batch(env):
    ex, _ = make(env, Recorder())
    assert ex.run_batch([], env.ctx()) == []


def test_end_to_end_with_real_tools(env):
    """Real registry through the executor: read-only reads group, edit follows, result order is kept."""
    import json

    from agent_v3.tools import build_registry
    env.write("a.py", "x = 1\n")
    ex = ToolExecutor(build_registry(), env.config)
    calls = [ToolCall("c1", "read_file", json.dumps({"path": "a.py", "start_line": None, "end_line": None})),
             ToolCall("c2", "search_text", json.dumps({"pattern": "x", "path": None, "glob": None, "regex": None,
                                                       "ignore_case": None, "context_lines": None,
                                                       "max_results": None})),
             ToolCall("c3", "edit_files", json.dumps({"edits": [{"path": "a.py", "old_text": "x = 1",
                                                               "new_text": "x = 2", "replace_all": None}]})),
             ToolCall("c4", "read_file", json.dumps({"path": "a.py", "start_line": None, "end_line": None}))]
    results = ex.run_batch(calls, env.ctx())
    assert [r.ok for _, r, _ in results] == [True, True, True, True]
    assert "1| x = 2" in results[3][1].output and env.read("a.py") == b"x = 2\n"

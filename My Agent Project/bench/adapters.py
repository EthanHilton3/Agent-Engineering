"""Adapters that run one benchmark task with an agent and return RunStats (plan §11.3)."""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import threading
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from time import time

from tasks import CheckContext, Task, _test_count, snapshot

HOMEWORK = Path(__file__).resolve().parent.parent
WEB_SEARCH_COST_USD = 0.01      # per search action, same as agent_v2.py


@dataclass
class RunStats:
    task: str
    agent: str
    run: int
    success: bool
    rounds: int
    tool_calls: int
    web_actions: int
    input_tokens: int
    cached_tokens: int
    output_tokens: int
    reasoning_tokens: int
    cost_usd: float                     # model cost plus web-search fees
    wall_s: float
    model_wait_s: float | None          # v2 has no model/tool wait split
    tool_wait_s: float | None
    files_changed: list[str]
    model: str = ""
    reasoning: str = ""
    turns: list[dict] = field(default_factory=list)   # per-turn rounds/tokens/cost (T8 turn-2 input)
    error: str | None = None


TURN_TIMEOUT_S = 1500          # wall-clock backstop per prompt; the session's own limit is 1200 s


def run_v3(task: Task, workdir: Path, model: str, reasoning: str, flags: dict | None = None,
           run: int = 1) -> RunStats:
    """Run the task's prompts through an agent_v3 Session (full-auto, workspace=workdir).

    `flags` holds the AgentConfig ablation switches (parallel_reads, prune_history, dedupe_reads,
    lenient_edit_match) and optionally `events_log`, a path that receives every event as JSONL.
    """
    sys.path.insert(0, str(HOMEWORK))
    from agent_v3.config import AgentConfig
    from agent_v3.session import Session

    flags = dict(flags or {})
    events_log = flags.pop("events_log", None)
    before = snapshot(workdir)
    tests_before = _test_count(workdir)

    commands: list[str] = []
    answers: list[str] = []
    turns: list[dict] = []
    events: list[dict] = []
    totals = TurnTotals()
    web_actions = sources = 0
    error = None
    lock = threading.Lock()

    # Tool-output logs go outside the workdir, so they don't show up in files_changed.
    output_dir = Path(tempfile.mkdtemp(prefix="bench_v3_out_"))
    config = AgentConfig(model=model, reasoning=reasoning, workspace=workdir, approval="full-auto",
                         output_dir=output_dir, **flags)
    session = None

    def reject(request_id: str) -> None:
        session.respond_approval(request_id, "reject", "Not allowed in this benchmark run.")

    def on_event(event) -> None:                       # runs under the session lock: record, never wait
        nonlocal web_actions
        data = event.to_dict()
        with lock:
            events.append(data)
            if data["type"] == "tool_started" and data["name"] == "run_command" and isinstance(data["args"], dict):
                commands.append(str(data["args"].get("command", "")))
            elif data["type"] == "web_action":
                web_actions += 1
            elif data["type"] == "approval_requested":   # full-auto still asks for always-ask patterns
                threading.Thread(target=reject, args=(data["request"]["request_id"],), daemon=True).start()

    started = time()
    try:
        session = Session(config, on_event)
        for prompt in task.prompts:
            session.start_turn(prompt)
            if not session.wait(TURN_TIMEOUT_S):
                session.cancel()
                raise TimeoutError(f"turn exceeded {TURN_TIMEOUT_S} s")
            final = events[-1]
            if final["type"] == "turn_failed":
                raise RuntimeError(f"turn_failed ({final['error_code']}): {final['message']}")
            if final["type"] != "turn_completed":
                raise RuntimeError(f"turn ended with {final['type']}")
            stats = final["stats"]
            answers.append(final["text"])
            sources += len(final["sources"])
            turn_cost = stats["model_cost_usd"] + stats["web_cost_usd"]
            turns.append({"rounds": stats["rounds"], "input_tokens": stats["input_tokens"],
                          "cached_tokens": stats["cached_tokens"], "output_tokens": stats["output_tokens"],
                          "cost_usd": turn_cost, "stop_reason": final["stop_reason"]})
            totals.add(stats)
            if final["stop_reason"] != "done":
                raise RuntimeError(f"turn stopped early: {final['stop_reason']}")
    except Exception as exc:                            # record, don't kill the sweep
        error = f"{type(exc).__name__}: {exc}"
    finally:
        if session is not None:
            session.close()
        shutil.rmtree(output_dir, ignore_errors=True)
        if events_log:
            Path(events_log).parent.mkdir(parents=True, exist_ok=True)
            with open(events_log, "w", encoding="utf-8") as file:
                file.writelines(json.dumps(e) + "\n" for e in events)
    wall_s = time() - started

    after = snapshot(workdir)
    success = False
    if error is None:
        ctx = CheckContext(workdir, before, after, answers, web_actions, commands, sources, tests_before)
        success = bool(task.check(ctx))
    return RunStats(
        task=task.id, agent="v3", run=run, success=success, rounds=totals.rounds, tool_calls=totals.tool_calls,
        web_actions=web_actions, input_tokens=totals.input_tokens, cached_tokens=totals.cached_tokens,
        output_tokens=totals.output_tokens, reasoning_tokens=totals.reasoning_tokens,
        cost_usd=totals.cost_usd, wall_s=round(wall_s, 2),
        model_wait_s=round(totals.model_wait_s, 2), tool_wait_s=round(totals.tool_wait_s, 2),
        files_changed=sorted(p for p in set(before) | set(after) if before.get(p) != after.get(p)),
        model=model, reasoning=reasoning, turns=turns, error=error,
    )


@dataclass
class TurnTotals:
    rounds: int = 0
    tool_calls: int = 0
    input_tokens: int = 0
    cached_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    cost_usd: float = 0.0
    model_wait_s: float = 0.0
    tool_wait_s: float = 0.0

    def add(self, stats: dict) -> None:
        for name in ("rounds", "tool_calls", "input_tokens", "cached_tokens", "output_tokens",
                     "reasoning_tokens", "model_wait_s", "tool_wait_s"):
            setattr(self, name, getattr(self, name) + stats[name])
        self.cost_usd += stats["model_cost_usd"] + stats["web_cost_usd"]


def run_v2(task: Task, workdir: Path, model: str, reasoning: str, flags: dict | None = None,
           run: int = 1) -> RunStats:
    """Run the task's prompts through agent_v2's turn loop with auto-approval, in workdir."""
    sys.path.insert(0, str(HOMEWORK))
    import agent_toolbox_v2
    import agent_v2
    import usage
    from openai import OpenAI

    before = snapshot(workdir)
    tests_before = _test_count(workdir)
    commands: list[str] = []
    answers: list[str] = []
    turns: list[dict] = []
    totals = {"input": 0, "cached": 0, "output": 0, "reasoning": 0}
    model_cost = 0.0
    tool_calls = web_actions = web_searches = sources = rounds = 0

    previous_cwd, previous_auto = os.getcwd(), agent_toolbox_v2.AUTO_APPROVE
    toolbox = agent_toolbox_v2.toolbox
    real_call_tool = toolbox.call_tool

    def logging_call_tool(name, arguments):
        if name == "shell":
            commands.append(str(arguments.get("command", "")))
        return real_call_tool(name, arguments)

    error = None
    started = time()
    try:
        os.chdir(workdir)
        agent_toolbox_v2.AUTO_APPROVE = True
        toolbox.call_tool = logging_call_tool

        # Same system prompt construction as agent_v2.py's __main__.
        prompt = (HOMEWORK / "agent.md").read_text(encoding="utf-8")
        prompt += f"\n\n## Environment\n- Working folder: {Path.cwd()}\n- Today's date: {date.today()}\n"
        web_tool = {"type": "web_search", "search_context_size": "medium"}
        client = OpenAI()
        history = [{"role": "system", "content": prompt}]

        for user_message in task.prompts:
            history.append({"role": "user", "content": user_message})
            with contextlib.redirect_stdout(io.StringIO()):      # silence ui.py's per-tool printing
                text, turn_history, turn_usage, turn_tool_calls = agent_v2._run_agent_turn(
                    client, model, reasoning, history, None, web_tool)
            history += turn_history
            answers.append(text)

            search_items = [i for i in turn_history if getattr(i, "type", None) == "web_search_call"]
            turn_web = len(search_items)
            turn_searches = sum(getattr(getattr(i, "action", None), "type", None) == "search" for i in search_items)
            turn_totals = usage._aggregate_usage(turn_usage)
            turn_model_cost = usage._calculate_cost_usd(turn_totals)
            turn_in = sum(t["input"] for t in turn_totals.values())
            turn_cached = sum(t["cached"] for t in turn_totals.values())
            turn_out = sum(t["output"] for t in turn_totals.values())
            turn_reasoning = sum(t["reasoning"] for t in turn_totals.values())

            turns.append({"rounds": len(turn_usage), "input_tokens": turn_in, "cached_tokens": turn_cached,
                          "output_tokens": turn_out, "cost_usd": turn_model_cost + turn_searches * WEB_SEARCH_COST_USD})
            totals["input"] += turn_in
            totals["cached"] += turn_cached
            totals["output"] += turn_out
            totals["reasoning"] += turn_reasoning
            model_cost += turn_model_cost
            rounds += len(turn_usage)
            tool_calls += turn_tool_calls - turn_web       # v2 counts web actions as tool calls
            web_actions += turn_web
            web_searches += turn_searches
            sources += len(agent_v2._sources(turn_history))
    except Exception as exc:                                # API failure etc.: record, don't kill the sweep
        error = f"{type(exc).__name__}: {exc}"
    finally:
        toolbox.call_tool = real_call_tool
        agent_toolbox_v2.AUTO_APPROVE = previous_auto
        os.chdir(previous_cwd)
    wall_s = time() - started

    after = snapshot(workdir)
    success = False
    if error is None:
        ctx = CheckContext(workdir, before, after, answers, web_actions, commands, sources, tests_before)
        success = bool(task.check(ctx))
    return RunStats(
        task=task.id, agent="v2", run=run, success=success, rounds=rounds, tool_calls=tool_calls,
        web_actions=web_actions, input_tokens=totals["input"], cached_tokens=totals["cached"],
        output_tokens=totals["output"], reasoning_tokens=totals["reasoning"],
        cost_usd=model_cost + web_searches * WEB_SEARCH_COST_USD, wall_s=round(wall_s, 2),
        model_wait_s=None, tool_wait_s=None,
        files_changed=sorted(p for p in set(before) | set(after) if before.get(p) != after.get(p)),
        model=model, reasoning=reasoning, turns=turns, error=error,
    )

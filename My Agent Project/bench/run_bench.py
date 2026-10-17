"""Run benchmark tasks against an agent and write one JSON line of RunStats per run (plan §11.4)."""
import argparse
import json
import os
import shutil
import stat
import subprocess
import tempfile
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from adapters import RunStats, run_v2, run_v3
from tasks import TASKS, TASKS_BY_ID, Task

BENCH = Path(__file__).resolve().parent
FIXTURE = BENCH / "fixtures" / "inventory_app"
RESULTS = BENCH / "results"


def _git(workdir: Path, *args: str) -> None:
    subprocess.run(["git", "-c", "user.name=bench", "-c", "user.email=bench@example.com", *args],
                   cwd=workdir, check=True, capture_output=True)


WORK_ROOT = Path(tempfile.gettempdir()) / "agent_bench"


def prepare_workdir(task: Task) -> Path:
    """Copy the fixture to the task's fixed work dir, git init + commit, then apply the task's setup.

    The path is the same for every run of a task (it is cleaned first), as in real use where the workspace
    doesn't move between sessions, so the system prompt and v3's prompt_cache_key are stable across runs.
    """
    workdir = WORK_ROOT / task.id
    if workdir.exists():
        _rmtree(workdir)
    workdir.mkdir(parents=True)
    shutil.copytree(FIXTURE, workdir, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    _git(workdir, "init", "-q")
    _git(workdir, "add", "-A")
    _git(workdir, "commit", "-q", "-m", "fixture")
    task.setup(workdir)
    return workdir


def _rmtree(path: Path) -> None:
    def make_writable(func, p, _):      # git's object files are read-only on Windows
        os.chmod(p, stat.S_IWRITE)
        func(p)
    shutil.rmtree(path, onerror=make_writable)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run benchmark tasks and record per-run stats.")
    parser.add_argument("--agent", choices=("v2", "v3"), required=True)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--tasks", help="Comma-separated task ids, e.g. T2,T3. Default: T1-T8.")
    parser.add_argument("--model", default="gpt-6-luna")
    parser.add_argument("--reasoning", default="medium")
    parser.add_argument("--with-web", action="store_true", help="Also run the opt-in web task (T9).")
    parser.add_argument("--with-long", action="store_true", help="Also run the opt-in long-session task (T10).")
    parser.add_argument("--keep-workdirs", action="store_true",
                        help="Don't delete the work dirs after a run (each task's dir is reused by its next run).")
    parser.add_argument("--no-parallel-reads", action="store_true", help="v3 ablation: run tool calls one at a time.")
    parser.add_argument("--no-prune-history", action="store_true", help="v3 ablation: keep full tool output in history.")
    parser.add_argument("--no-dedupe-reads", action="store_true", help="v3 ablation: re-send unchanged file reads.")
    parser.add_argument("--no-lenient-edit", action="store_true", help="v3 ablation: exact-match edits only.")
    parser.add_argument("--label", default="", help="Suffix for the results file name, e.g. noprune.")
    args = parser.parse_args()

    ablations = {"parallel_reads": not args.no_parallel_reads, "prune_history": not args.no_prune_history,
                 "dedupe_reads": not args.no_dedupe_reads, "lenient_edit_match": not args.no_lenient_edit}
    if args.agent == "v2":
        if not all(ablations.values()):
            raise SystemExit("the --no-* ablation flags only apply to --agent v3.")
        runner = run_v2
    else:
        runner = run_v3

    if args.tasks:
        tasks = [TASKS_BY_ID[t.strip().upper()] for t in args.tasks.split(",")]
    else:
        tasks = [t for t in TASKS if (not t.web or args.with_web) and (not t.long or args.with_long)]

    RESULTS.mkdir(exist_ok=True)
    stamp = f"{datetime.now():%Y%m%d-%H%M%S}"
    out_path = RESULTS / f"{stamp}_{args.agent}{'_' + args.label if args.label else ''}.jsonl"
    off = [name for name, on in ablations.items() if not on]
    print(f"agent={args.agent} model={args.model} reasoning={args.reasoning} "
          f"tasks={','.join(t.id for t in tasks)} runs={args.runs}"
          f"{' ablated=' + ','.join(off) if off else ''}\nwriting {out_path}\n")

    total_cost = 0.0
    for task in tasks:
        for run in range(1, args.runs + 1):
            workdir = prepare_workdir(task)
            flags = {**ablations, "events_log": RESULTS / "events" / f"{out_path.stem}_{task.id}_r{run}.jsonl"} \
                if args.agent == "v3" else None
            try:
                stats: RunStats = runner(task, workdir, args.model, args.reasoning, flags, run)
            finally:
                if not args.keep_workdirs:
                    _rmtree(workdir)
            total_cost += stats.cost_usd
            with out_path.open("a", encoding="utf-8") as file:
                file.write(json.dumps(asdict(stats)) + "\n")
            verdict = "PASS" if stats.success else ("ERROR " + stats.error if stats.error else "FAIL")
            print(f"{task.id} run {run}: {verdict:<5} rounds={stats.rounds} tools={stats.tool_calls} "
                  f"web={stats.web_actions} ${stats.cost_usd:.4f} {stats.wall_s:.1f}s "
                  f"changed={stats.files_changed}", flush=True)
            if args.keep_workdirs:
                print(f"    workdir: {workdir}")
    print(f"\nTotal measured cost: ${total_cost:.4f}")


if __name__ == "__main__":
    main()

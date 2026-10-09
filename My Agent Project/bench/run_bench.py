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

from adapters import RunStats, run_v2
from tasks import TASKS, TASKS_BY_ID, Task

BENCH = Path(__file__).resolve().parent
FIXTURE = BENCH / "fixtures" / "inventory_app"
RESULTS = BENCH / "results"


def _git(workdir: Path, *args: str) -> None:
    subprocess.run(["git", "-c", "user.name=bench", "-c", "user.email=bench@example.com", *args],
                   cwd=workdir, check=True, capture_output=True)


def prepare_workdir(task: Task) -> Path:
    """Copy the fixture to a temp dir, git init + commit, then apply the task's setup."""
    workdir = Path(tempfile.mkdtemp(prefix=f"bench_{task.id}_"))
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
    parser.add_argument("--model", default="gpt-5.6-luna")
    parser.add_argument("--reasoning", default="none")
    parser.add_argument("--with-web", action="store_true", help="Also run the opt-in web task (T9).")
    parser.add_argument("--keep-workdirs", action="store_true", help="Don't delete the temp workspaces.")
    args = parser.parse_args()

    if args.agent == "v3":
        raise SystemExit("agent v3 does not exist yet (run_v3 arrives in Phase 3).")
    runner = run_v2

    if args.tasks:
        tasks = [TASKS_BY_ID[t.strip().upper()] for t in args.tasks.split(",")]
    else:
        tasks = [t for t in TASKS if not t.web or args.with_web]

    RESULTS.mkdir(exist_ok=True)
    out_path = RESULTS / f"{datetime.now():%Y%m%d-%H%M%S}_{args.agent}.jsonl"
    print(f"agent={args.agent} model={args.model} reasoning={args.reasoning} "
          f"tasks={','.join(t.id for t in tasks)} runs={args.runs}\nwriting {out_path}\n")

    total_cost = 0.0
    for task in tasks:
        for run in range(1, args.runs + 1):
            workdir = prepare_workdir(task)
            try:
                stats: RunStats = runner(task, workdir, args.model, args.reasoning, None, run)
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

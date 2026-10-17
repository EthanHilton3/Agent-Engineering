from __future__ import annotations

import functools
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

from pydantic import BaseModel, Field

from ..approvals import ApprovalRequest
from ..workspace import kill_process_tree, popen_in_tree, release_process_tree
from .registry import ErrorCode, ToolContext, ToolResult, ToolSpec, ask_approval

ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
POLL_SECONDS = 0.25


class ShellNotFound(RuntimeError):
    pass


@functools.lru_cache(maxsize=1)
def find_shell() -> str:
    """Locate bash: $AGENT_SHELL, then Git Bash on Windows (never WSL's System32 bash), or /bin/bash."""
    if (env := os.environ.get("AGENT_SHELL")):
        return env
    if os.name == "nt":
        git_bash = Path(r"C:\Program Files\Git\bin\bash.exe")
        if git_bash.exists():
            return str(git_bash)
        found = shutil.which("bash")
        if found and "system32" not in found.lower():
            return found
        raise ShellNotFound("Git Bash not found. Install Git for Windows or set AGENT_SHELL to a bash executable.")
    if Path("/bin/bash").exists():
        return "/bin/bash"
    raise ShellNotFound("/bin/bash not found. Set AGENT_SHELL to a bash executable.")


def cap_output(text: str, ctx: ToolContext) -> tuple[str, dict]:
    """Cap to tool_output_max_chars (first 40% + last 60%); save the full text when capped."""
    limit = ctx.config.tool_output_max_chars
    if len(text) <= limit:
        return text, {}
    head = int(limit * 0.4)
    capped = text[:head] + f"\n[… {len(text) - limit:,} chars omitted …]\n" + text[-(limit - head):]
    meta: dict = {"truncated": True}
    try:
        name = re.sub(r"[^\w.-]", "_", ctx.call_id) or "output"     # call ids are unique across rounds
        log = ctx.output_dir / f"{name}.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(text, encoding="utf-8")
        shown = ctx.workspace.display(log)
        meta["full_output_path"] = shown
        note = f"Full output saved to {shown} — use search_text on it for specifics."
    except OSError:
        note = "The full output could not be saved."
    return capped + f"\n[Output truncated: {len(text):,} chars total. {note}]", meta


class RunCommandArgs(BaseModel):
    command: str = Field(description="Bash command.")
    timeout: int | None = Field(default=None, ge=1, le=600, description="Timeout in seconds. Default 60.")
    cwd: str | None = Field(default=None, description="Working directory. Default: workspace root.")


def run_command(args: RunCommandArgs, ctx: ToolContext) -> ToolResult:
    cfg = ctx.config
    timeout = min(args.timeout or cfg.command_default_timeout, cfg.command_max_timeout)
    cwd = ctx.workspace.resolve(args.cwd) if args.cwd else ctx.workspace.root
    if not cwd.is_dir():
        return ToolResult.failure(ErrorCode.NOT_FOUND, f"cwd '{args.cwd}' is not an existing directory.")
    try:
        shell = find_shell()
    except ShellNotFound as e:
        return ToolResult.failure(ErrorCode.INTERNAL, str(e))

    outside = not ctx.workspace.is_inside(cwd)
    rejected = ask_approval(ctx, ApprovalRequest(
        kind="command", title="Run command", command=args.command, cwd=str(cwd), timeout=timeout,
        outside_workspace=outside))
    if rejected:
        return rejected

    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1", "GIT_PAGER": "cat",
           "PAGER": "cat", "NO_COLOR": "1", "TERM": "dumb"}
    started = time.monotonic()
    try:
        proc = popen_in_tree([shell, "-c", args.command], cwd=str(cwd), stdin=subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                             encoding="utf-8", errors="replace", env=env)
    except OSError as e:
        return ToolResult.failure(ErrorCode.INTERNAL, f"Could not start the command: {e}")

    ctx.cancel.register(proc)
    reason, out = None, ""
    try:
        deadline = started + timeout
        while True:
            try:
                out, _ = proc.communicate(timeout=POLL_SECONDS)
                break
            except subprocess.TimeoutExpired:
                if ctx.cancel.cancelled:
                    reason = "cancelled"
                elif time.monotonic() >= deadline:
                    reason = "timeout"
                else:
                    continue
                kill_process_tree(proc)
                try:
                    out, _ = proc.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    out = ""
                break
    finally:
        ctx.cancel.unregister(proc)
        release_process_tree(proc)
    duration = round(time.monotonic() - started, 2)
    if reason is None and ctx.cancel.cancelled and proc.returncode != 0:
        reason = "cancelled"        # killed by CancelToken.cancel() while we were waiting

    body, trunc_meta = cap_output(ANSI_RE.sub("", out or "").rstrip(), ctx)
    meta = {"duration_s": duration, "exit_code": proc.returncode, **trunc_meta}
    if outside:
        meta["outside_workspace"] = True

    def with_body(header: str) -> str:
        return f"{header}\n{body}" if body else header

    if reason == "timeout":
        return ToolResult(False, with_body(f"Error (timeout): Timed out after {timeout}s (process tree killed). "
                                           "Use a longer timeout (max 600) or a narrower command."),
                          f"timeout · {timeout}s", ErrorCode.TIMEOUT, meta)
    if reason == "cancelled":
        return ToolResult(False, with_body("Error (cancelled): Cancelled by user"),
                          "cancelled", ErrorCode.CANCELLED, meta)
    header = f"Exit code {proc.returncode} · {duration}s"
    summary = f"exit {proc.returncode} · {duration}s"
    if proc.returncode != 0:
        return ToolResult(False, with_body(f"Error (nonzero_exit): {header}"), summary, ErrorCode.NONZERO_EXIT, meta)
    return ToolResult(True, with_body(header), summary, None, meta)


SHELL_TOOLS = [
    ToolSpec("run_command", RunCommandArgs, run_command, False,
             "Run a bash command (Git Bash on Windows) for tests, builds, programs, and git operations "
             "beyond git_status/git_diff. Each call is a fresh shell; cwd does not persist."),
]

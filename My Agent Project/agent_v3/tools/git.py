from __future__ import annotations

import subprocess

from pydantic import BaseModel, Field

from .registry import ErrorCode, ToolContext, ToolResult, ToolSpec
from .shell import cap_output

GIT_TIMEOUT_SECONDS = 30


def _git(ctx: ToolContext, *argv: str) -> ToolResult | subprocess.CompletedProcess:
    """Run git directly (no shell) in the workspace root. Returns the process, or an error result."""
    try:
        proc = subprocess.run(["git", "--no-pager", "-c", "core.pager=cat", *argv], cwd=str(ctx.workspace.root),
                              stdin=subprocess.DEVNULL, capture_output=True, timeout=GIT_TIMEOUT_SECONDS)
    except FileNotFoundError:
        return ToolResult.failure(ErrorCode.INTERNAL, "git is not installed or not on PATH.")
    except subprocess.TimeoutExpired:
        return ToolResult.failure(ErrorCode.TIMEOUT, f"git did not finish within {GIT_TIMEOUT_SECONDS}s.")
    if proc.returncode != 0 and b"not a git repository" in proc.stderr.lower():   # git diff warns "Not a ..."
        return ToolResult.failure(ErrorCode.NOT_A_REPO, "The workspace is not a git repository.",
                                  summary="not a git repo")
    return proc


def _text(proc: subprocess.CompletedProcess) -> str:
    return (proc.stdout + (b"\n" + proc.stderr if proc.returncode != 0 else b"")).decode("utf-8", errors="replace")


class GitStatusArgs(BaseModel):
    pass


def git_status(args: GitStatusArgs, ctx: ToolContext) -> ToolResult:
    res = _git(ctx, "status", "--porcelain=v1", "--branch")
    if isinstance(res, ToolResult):
        return res
    if res.returncode != 0:
        return ToolResult.failure(ErrorCode.INTERNAL, f"git status failed: {_text(res).strip()}")
    out = _text(res).rstrip()
    changes = max(0, len(out.splitlines()) - 1)
    return ToolResult.success(out, f"{changes} changed" if changes else "clean", changes=changes)


class GitDiffArgs(BaseModel):
    path: str | None = Field(default=None, description="Limit the diff to this path. Default: whole repository.")
    staged: bool | None = Field(default=None, description="Show staged changes instead of unstaged. Default false.")
    stat_only: bool | None = Field(default=None, description="Show only the per-file change summary. Default false.")


def git_diff(args: GitDiffArgs, ctx: ToolContext) -> ToolResult:
    argv = ["diff", "--no-ext-diff", "--no-color"]
    if args.staged:
        argv.append("--cached")
    if args.stat_only:
        argv.append("--stat")
    if args.path:
        argv += ["--", args.path]
    res = _git(ctx, *argv)
    if isinstance(res, ToolResult):
        return res
    if res.returncode != 0:
        return ToolResult.failure(ErrorCode.INTERNAL, f"git diff failed: {_text(res).strip()}")
    text = _text(res).rstrip()
    if not text:
        return ToolResult.success("No differences.", "no differences")
    out, meta = cap_output(text, ctx)
    return ToolResult.success(out, f"{len(text.splitlines())} lines", **meta)


GIT_TOOLS = [
    ToolSpec("git_status", GitStatusArgs, git_status, True,
             "Show the current git branch and changed files (git status --porcelain). Read-only."),
    ToolSpec("git_diff", GitDiffArgs, git_diff, True,
             "Show uncommitted changes (git diff). Use stat_only for a per-file summary. Read-only; run it "
             "before finishing to confirm only intended changes were made."),
]

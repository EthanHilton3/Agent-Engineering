"""System prompt: prompt.md + (prompt_web.md if web search is on) + an Environment block (plan §9).

Built once per session, so the system message is byte-identical across every round (cache-stable).
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
from datetime import date
from pathlib import Path

from .config import AgentConfig

HERE = Path(__file__).resolve().parent

APPROVAL_TEXT = {
    "ask": "edits and commands need user approval",
    "auto-edit": "workspace edits are automatic; commands need user approval",
    "full-auto": "edits and commands run without approval, except risky commands and anything outside the workspace",
}


def is_git_repo(path: Path) -> bool:
    return any((p / ".git").exists() for p in (path, *path.parents))


def os_name() -> str:
    system, release = platform.system(), platform.release()
    return f"{system} {release}".strip() if system else "unknown"


def environment_block(config: AgentConfig, today: date | None = None) -> str:
    shell = "Git Bash" if os.name == "nt" else "bash"
    return "\n".join([
        "## Environment",
        f"- Workspace: {config.workspace}",
        f"- OS: {os_name()}; shell for run_command: {shell}",
        "- Run Python tools via `python -m` (e.g. `python -m pytest`); bare `pytest` may not be on PATH",
        f"- Date: {(today or date.today()).isoformat()}",
        f"- Approval mode: {config.approval} ({APPROVAL_TEXT[config.approval]})",
        f"- Git repository: {'yes' if is_git_repo(config.workspace) else 'no'}",
    ])


def build_system_prompt(config: AgentConfig, today: date | None = None) -> str:
    base = Path(config.prompt_path) if config.prompt_path else HERE / "prompt.md"
    parts = [base.read_text(encoding="utf-8").strip()]
    if config.web_search:
        parts.append((HERE / "prompt_web.md").read_text(encoding="utf-8").strip())
    parts.append(environment_block(config, today))
    return "\n\n".join(parts) + "\n"


def prompt_cache_key(workspace: Path, system_prompt: str, tools: list[dict]) -> str:
    """Stable across sessions that share a workspace and an identical fixed prefix (system prompt + tools).

    The server only reuses a cached prefix within one key, so a per-session key made every session's
    first round a cache miss. Any change to the prompt, tools, or workspace yields a new key.
    """
    prefix = json.dumps([str(workspace), system_prompt, tools], sort_keys=True, ensure_ascii=False)
    return "agent_v3:" + hashlib.sha256(prefix.encode("utf-8")).hexdigest()[:32]

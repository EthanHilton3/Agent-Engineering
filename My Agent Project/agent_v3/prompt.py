"""System prompt: prompt.md + (prompt_web.md if web search is on) + an Environment block (plan §9).

Built once per session, so the system message is byte-identical across every round (cache-stable).
"""
from __future__ import annotations

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

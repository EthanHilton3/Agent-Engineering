"""
PreToolUse hook: keep Claude inside this build folder, and keep the spec and harness read-only.

Claude Code sends the pending tool call as JSON on stdin. Exiting with code 2 blocks the call,
and the message on stderr goes back to Claude as the reason.
"""
import json
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2]).resolve()
TOOL_DIRS = (Path(tempfile.gettempdir()).resolve(), (Path.home() / ".claude").resolve())
READ_ONLY = ("spec.md", "CLAUDE.md", "HARNESS.md", ".claude")
OUTSIDE_IN_SHELL = re.compile(r"build-a-oneshot|build-b-harness|(^|[\s'\"=:(])\.\.([/\\]|\s|$)")


def main():
	call = json.load(sys.stdin)
	tool = call.get("tool_name", "")
	args = call.get("tool_input", {}) or {}
	cwd = Path(call.get("cwd") or ROOT)

	if tool == "Bash":
		command = args.get("command", "")
		if OUTSIDE_IN_SHELL.search(command):
			block("Shell commands must stay inside this build folder (no `..` paths or sibling builds).")
		return

	for key in ("file_path", "path", "notebook_path"):
		if args.get(key):
			check_path(tool, resolve(cwd, args[key]))
	if tool == "Glob" and ".." in args.get("pattern", ""):
		block("Glob patterns must stay inside this build folder (no `..`).")


def check_path(tool: str, path: Path):
	"""Block paths outside the build folder, and edits to read-only harness files."""
	if not path.is_relative_to(ROOT):
		if tool in ("Read", "Glob", "Grep") and any(path.is_relative_to(ok) for ok in TOOL_DIRS):
			return		# Claude Code's own temp output files and settings
		block(f"{path} is outside this build folder. Work only inside {ROOT}.")
	relative = path.relative_to(ROOT).as_posix()
	if tool in ("Edit", "Write", "NotebookEdit") and any(
		relative == name or relative.startswith(name + "/") for name in READ_ONLY
	):
		block(f"{relative} is part of the spec or harness and is read-only.")


def resolve(cwd: Path, raw: str) -> Path:
	"""Absolute, normalized path. Also accepts Git Bash style paths like /c/Users/..."""
	if os.name == "nt" and re.match(r"^/[a-zA-Z]/", raw):
		raw = f"{raw[1]}:/{raw[3:]}"
	path = Path(raw)
	return (path if path.is_absolute() else cwd / path).resolve()


def block(reason: str):
	print(f"Blocked by harness guard: {reason}", file=sys.stderr)
	sys.exit(2)


if __name__ == "__main__":
	main()

"""
Stop hook: don't let a session finish while the tests or the type check fail.

Exiting with code 2 makes Claude keep going, with the failure output (stderr) as its next instruction.
If Claude is already continuing because of this hook (stop_hook_active), let it stop, so it
can't loop forever.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
CHECKS = ("test", "typecheck")
TAIL_LINES = 40


def main():
	event = json.load(sys.stdin)
	if event.get("stop_hook_active"):
		return
	scripts = project_scripts()
	if scripts is None:
		return		# no app yet (still planning), nothing to check

	failures = [failure for name in CHECKS if name in scripts and (failure := run_check(name))]
	if failures:
		print("The session can't finish while checks fail:\n\n" + "\n\n".join(failures) +
		      "\n\nFix the failures, or, if you can't (for example you are the orchestrator or reviewer), "
		      "record them in the relevant handoff file and say so in your final message.", file=sys.stderr)
		sys.exit(2)


def project_scripts() -> dict | None:
	"""package.json scripts, or None if the app isn't set up and installed yet."""
	package = ROOT / "package.json"
	if not package.exists() or not (ROOT / "node_modules").exists():
		return None
	try:
		return json.loads(package.read_text(encoding="utf-8")).get("scripts", {})
	except json.JSONDecodeError:
		return {}


def run_check(name: str) -> str | None:
	"""Run `npm run <name>`. Returns a failure description, or None if it passed."""
	try:
		result = subprocess.run(f"npm run {name}", shell=True, cwd=ROOT, capture_output=True,
		                        text=True, encoding="utf-8", errors="replace", timeout=240)
	except subprocess.TimeoutExpired:
		return f"`npm run {name}` timed out after 240 seconds."
	if result.returncode == 0:
		return None
	tail = "\n".join((result.stdout + result.stderr).strip().splitlines()[-TAIL_LINES:])
	return f"`npm run {name}` failed (exit {result.returncode}):\n{tail}"


if __name__ == "__main__":
	main()

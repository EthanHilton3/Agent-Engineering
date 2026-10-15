"""
Workflow state for /build: decides the next step from the handoff files, and records steps.

	python .claude/skills/build/workflow.py next            # next step, subagent, and its exact prompt
	python .claude/skills/build/workflow.py record <step>   # log a finished step; says whether to pause
	python .claude/skills/build/workflow.py status          # milestones, verdicts, history

Steps: plan, review-plan, dev, review.
"""
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HANDOFF = ROOT / "handoff"
PLAN = HANDOFF / "plan.md"
PLAN_REVIEW = HANDOFF / "plan-review.md"
SESSIONS_LOG = HANDOFF / "sessions.log"
MAX_REVIEW_ROUNDS = 3
STEP_AGENTS = {"plan": "planner", "review-plan": "reviewer", "dev": "developer", "review": "reviewer"}
STOP_MESSAGES = {
	"done": "The latest code review approved the app. The build is finished.",
	"stuck": f"{MAX_REVIEW_ROUNDS} code reviews in a row asked for changes. The user must decide how to proceed.",
	"bad-plan": "handoff/plan.md has no milestones in the `- [ ] M1: ...` format. Ask the planner to fix the format.",
}


def main():
	command = sys.argv[1] if len(sys.argv) > 1 else "next"
	if command == "next":
		print_next()
	elif command == "record" and len(sys.argv) > 2 and sys.argv[2] in STEP_AGENTS:
		record(sys.argv[2])
	elif command == "status":
		print_status()
	else:
		sys.exit(__doc__)


def print_next():
	"""Print the next step, the subagent to run, and the exact prompt to give it."""
	step = next_step()
	if step in STOP_MESSAGES:
		print(f"Step: {step}\nSTOP: {STOP_MESSAGES[step]}")
		return
	print(f"Step: {step}\nSubagent: {STEP_AGENTS[step]}\nPrompt: {kickoff_message(step)}")


def record(step: str):
	"""Log a finished step, then say whether the user should review before continuing."""
	HANDOFF.mkdir(exist_ok=True)
	with SESSIONS_LOG.open("a", encoding="utf-8") as log:
		log.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {step}\n")
	print(f"Recorded {step}. Next step: {next_step()}")
	print(f"Pause: {pause_reason(step) or 'no, continue'}")


def pause_reason(finished: str) -> str | None:
	"""Human checkpoints: once the plan is final, and after every code review."""
	upcoming = next_step()
	if finished in ("plan", "review-plan") and upcoming == "dev":
		return "yes. The plan is final. The user should read handoff/plan.md before any code is written."
	if finished == "review":
		return f"yes. Code review finished ({verdict(code_reviews()[-1]) if code_reviews() else 'no review file'}). Report it to the user."
	if upcoming in STOP_MESSAGES:
		return f"yes. {STOP_MESSAGES[upcoming]}"
	return None


def kickoff_message(step: str) -> str:
	"""The prompt for the step's subagent."""
	if step == "plan":
		if PLAN.exists() and verdict(PLAN_REVIEW) == "CHANGES REQUIRED":
			return ("Revise handoff/plan.md to address every finding in handoff/plan-review.md, "
			        "and add a Revision notes section.")
		return "Read spec.md and write handoff/plan.md as your instructions describe."
	if step == "review-plan":
		return "Plan review mode. Review handoff/plan.md against spec.md and write handoff/plan-review.md."
	if step == "dev":
		review = review_to_fix()
		if review:
			return (f"Fix mode. Address every finding in handoff/{review.name}, verify, "
			        "and record what you did in handoff/progress.md.")
		return (f"Milestone mode. Complete {first_unchecked_milestone()} from handoff/plan.md, "
		        "verify it, and record it in handoff/progress.md.")
	n = len(code_reviews()) + 1
	return f"Code review mode. Review the app against spec.md and handoff/plan.md, and write handoff/review-{n}.md."


def next_step() -> str:
	"""Decide the next workflow step from the handoff files."""
	steps = sessions()
	if not PLAN.exists():
		return "plan"
	if not milestones():
		return "bad-plan"
	if "review-plan" not in steps:
		return "review-plan"
	if verdict(PLAN_REVIEW) == "CHANGES REQUIRED" and last_index(steps, "plan") < last_index(steps, "review-plan"):
		return "plan"
	if first_unchecked_milestone():
		return "dev"
	reviews = code_reviews()
	if not reviews or last_index(steps, "review") < last_index(steps, "dev"):
		return "review"
	if verdict(reviews[-1]) == "CHANGES REQUIRED":
		return "stuck" if len(reviews) >= MAX_REVIEW_ROUNDS else "dev"
	return "done"


def review_to_fix() -> Path | None:
	"""The latest code review, if it asked for changes and no developer session has run since."""
	reviews = code_reviews()
	if not reviews or verdict(reviews[-1]) != "CHANGES REQUIRED":
		return None
	steps = sessions()
	return reviews[-1] if last_index(steps, "dev") < last_index(steps, "review") else None


def print_status():
	"""Print milestones, verdicts, and step history."""
	found = milestones()
	print("Milestones:" if found else "Milestones: (none found in handoff/plan.md)")
	for done, title in found:
		print(f"  [{'x' if done else ' '}] {title}")
	print(f"Plan review: {verdict(PLAN_REVIEW) or '-'}")
	for review in code_reviews():
		print(f"{review.stem}: {verdict(review)}")
	print(f"Steps so far: {', '.join(sessions()) or '-'}")
	print(f"Next step: {next_step()}")


# ------------------------------------------------------------------ helpers

def sessions() -> list[str]:
	"""Every recorded step, oldest first."""
	if not SESSIONS_LOG.exists():
		return []
	return [line.split()[2] for line in read(SESSIONS_LOG).splitlines() if line.strip()]


def milestones() -> list[tuple[bool, str]]:
	"""(done, title) for every `- [ ] M#: ...` / `- [x] M#: ...` line in plan.md."""
	if not PLAN.exists():
		return []
	found = re.findall(r"^\s*- \[([ xX])\] (M\d+.*)$", read(PLAN), re.MULTILINE)
	return [(mark != " ", title.strip()) for mark, title in found]


def first_unchecked_milestone() -> str | None:
	"""The title of the first unticked milestone, e.g. 'M3: Board generation'."""
	return next((title for done, title in milestones() if not done), None)


def code_reviews() -> list[Path]:
	"""review-1.md, review-2.md, ... in order."""
	return sorted(HANDOFF.glob("review-*.md"), key=lambda p: int(re.sub(r"\D", "", p.stem) or 0))


def verdict(path: Path) -> str | None:
	"""APPROVED or CHANGES REQUIRED from a review file, or None if there's no verdict."""
	if not path.exists():
		return None
	match = re.search(r"Verdict:\s*(APPROVED|CHANGES REQUIRED)", read(path))
	return match.group(1) if match else None


def last_index(items: list[str], value: str) -> int:
	"""Position of the last occurrence of value, or -1."""
	return max((i for i, item in enumerate(items) if item == value), default=-1)


def read(path: Path) -> str:
	return path.read_text(encoding="utf-8")


if __name__ == "__main__":
	main()

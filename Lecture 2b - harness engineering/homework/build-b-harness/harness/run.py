"""
Harness driver: runs one role session of my v2 agent with the right prompt, and
records it. The workflow itself is described in harness/workflow.md.

Run from the build-b-harness folder:
	python harness/run.py next              # run whatever step the workflow says comes next
	python harness/run.py plan              # or run a specific step: plan, review-plan, dev, review
	python harness/run.py status            # milestones, verdicts, sessions, total cost

Options:
	--note "..."    add a note from you to the kickoff message
	--chat          talk to the session yourself instead of sending the kickoff automatically
	--dry-run       build the prompt and kickoff, print them, and stop
"""
import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HARNESS = ROOT / "harness"
HANDOFF = ROOT / "handoff"
TRANSCRIPTS = ROOT / "transcripts"
PLAN = HANDOFF / "plan.md"
PLAN_REVIEW = HANDOFF / "plan-review.md"
SESSIONS_LOG = HANDOFF / "sessions.log"
AGENT = Path(os.environ.get("HARNESS_AGENT", ROOT / "../../../My Agent Project/agent_v2.py")).resolve()
MAX_REVIEW_ROUNDS = 3


@dataclass(frozen=True)
class Role:
	model: str
	reasoning: str
	skills: tuple[str, ...]		# always loaded; optional skills are listed in operating-rules.md


ROLES = {
	"planner": Role("gpt-5.6-sol", "medium", ("code-style.md", "testing.md")),
	"developer": Role("gpt-5.6-terra", "medium", ("code-style.md", "bottom-up-code.md", "testing.md")),
	"reviewer": Role("gpt-5.6-sol", "medium", ("code-style.md", "testing.md")),
}
STEP_ROLES = {"plan": "planner", "review-plan": "reviewer", "dev": "developer", "review": "reviewer"}


def main():
	parser = argparse.ArgumentParser(description="Run one step of the planner/developer/reviewer workflow.")
	parser.add_argument("step", choices=["next", "status", *STEP_ROLES])
	parser.add_argument("--note", help="A note from you, added to the kickoff message.")
	parser.add_argument("--chat", action="store_true", help="Type to the session yourself.")
	parser.add_argument("--dry-run", action="store_true", help="Print the prompt and kickoff without running.")
	args = parser.parse_args()

	if args.step == "status":
		print_status()
		return

	step = next_step() if args.step == "next" else args.step
	if step == "done":
		print("The latest code review approved the app. The workflow is done; see workflow.md for the wrap-up.")
		return
	if step == "bad-plan":
		print("handoff/plan.md has no milestones in the `- [ ] M1: ...` format, so the harness can't track "
		      "progress. Fix the format by hand, or run `plan --note \"use the required milestone format\"`.")
		return
	if step == "stuck":
		print(f"{MAX_REVIEW_ROUNDS} code reviews still asked for changes. Read the latest review and decide "
		      "what to do (run `dev --note ...` or stop). See workflow.md.")
		return

	run_step(step, args.note, chat=args.chat, dry_run=args.dry_run)


def run_step(step: str, note: str | None, chat: bool, dry_run: bool):
	"""Compose the role prompt and kickoff, run the agent, and log the session."""
	role_name = STEP_ROLES[step]
	role = ROLES[role_name]
	kickoff = kickoff_message(step, note)
	number = len(sessions()) + 1
	prompt_file = TRANSCRIPTS / f"{number:02}-{step}.prompt.md"
	transcript = TRANSCRIPTS / f"{number:02}-{step}.md"

	prompt = compose_prompt(role_name, role)
	if dry_run:
		print(prompt)
		print(f"\n--- kickoff ---\n{kickoff}\n\n--- would run {role.model} ({role.reasoning}) ---")
		return

	if not AGENT.exists():
		sys.exit(f"Can't find the agent at {AGENT}. Set HARNESS_AGENT to the path of agent_v2.py.")
	HANDOFF.mkdir(exist_ok=True)
	TRANSCRIPTS.mkdir(exist_ok=True)
	prompt_file.write_text(prompt, encoding="utf-8")

	print(f"== Session {number}: {step} ({role_name}, {role.model}, reasoning {role.reasoning}) ==")
	print(f"Kickoff: {kickoff}\n")
	command = [sys.executable, str(AGENT), str(prompt_file), "--model", role.model,
	           "--reasoning", role.reasoning, "--auto", "--transcript", str(transcript)]
	if chat:
		print("Chat mode: paste the kickoff above as your first message. Send an empty line to end.\n")
		subprocess.run(command, cwd=ROOT)
	else:
		# v2 reads one line per message: the kickoff, then an empty line that ends the session.
		subprocess.run(command, cwd=ROOT, input=f"{kickoff}\n\n", text=True, encoding="utf-8")

	with SESSIONS_LOG.open("a", encoding="utf-8") as log:
		log.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {step} {transcript.name}\n")
	print(f"\nTranscript: {transcript.relative_to(ROOT)}")
	print(f"Next step: {next_step()}  (run `python harness/run.py next`, or `status` for an overview)")


def compose_prompt(role_name: str, role: Role) -> str:
	"""Operating rules + role instructions + the role's always-loaded skills, as one system prompt."""
	parts = [
		read(HARNESS / "shared" / "operating-rules.md"),
		read(HARNESS / "roles" / f"{role_name}.md"),
		"# Skills (always loaded for your role)",
		*(read(HARNESS / "skills" / skill) for skill in role.skills),
	]
	return "\n\n---\n\n".join(parts)


def kickoff_message(step: str, note: str | None) -> str:
	"""The first (and only) user message for a step. Must be one line: v2 reads one line per message."""
	if step == "plan":
		if PLAN.exists() and verdict(PLAN_REVIEW) == "CHANGES REQUIRED":
			message = ("You are the planner. Revise handoff/plan.md to address every finding in "
			           "handoff/plan-review.md, and add a Revision notes section.")
		else:
			message = "You are the planner. Read spec.md and write handoff/plan.md as your instructions describe."
	elif step == "review-plan":
		message = ("You are the reviewer, in plan review mode. Review handoff/plan.md against spec.md "
		           "and write handoff/plan-review.md.")
	elif step == "dev":
		review = review_to_fix()
		if review:
			message = (f"You are the developer, in fix mode. Address every finding in handoff/{review.name}, "
			           "verify, and record what you did in handoff/progress.md.")
		else:
			milestone = first_unchecked_milestone()
			if milestone is None:
				sys.exit("Every milestone is ticked and no review needs fixing. Run `review` or `next` instead.")
			message = (f"You are the developer, in milestone mode. Complete {milestone} from handoff/plan.md, "
			           "verify it, and record it in handoff/progress.md.")
	else:
		n = len(code_reviews()) + 1
		message = (f"You are the reviewer, in code review mode. Review the app against spec.md and "
		           f"handoff/plan.md, and write handoff/review-{n}.md.")

	if note:
		message += f" Note from the human: {note}"
	return " ".join(message.split())


def next_step() -> str:
	"""Decide the next workflow step from the handoff files (see the diagram in workflow.md)."""
	steps = [step for step, _ in sessions()]
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
	steps = [step for step, _ in sessions()]
	return reviews[-1] if last_index(steps, "dev") < last_index(steps, "review") else None


def print_status():
	"""Print milestones, verdicts, the session history, and total agent cost."""
	found = milestones()
	print("Milestones:" if found else "Milestones: (none found in handoff/plan.md)")
	for done, title in found:
		print(f"  [{'x' if done else ' '}] {title}")
	print(f"Plan review: {verdict(PLAN_REVIEW) or '-'}")
	for review in code_reviews():
		print(f"{review.stem}: {verdict(review)}")

	total = 0.0
	print("Sessions:")
	for step, transcript in sessions():
		cost = session_cost(TRANSCRIPTS / transcript)
		total += cost
		print(f"  {transcript:<28} ${cost:.4f}")
	print(f"Total agent cost: ${total:.4f}")
	print(f"Next step: {next_step()}")


# ------------------------------------------------------------------ helpers

def sessions() -> list[tuple[str, str]]:
	"""(step, transcript file name) for every session run so far, oldest first."""
	if not SESSIONS_LOG.exists():
		return []
	return [tuple(line.split()[2:4]) for line in read(SESSIONS_LOG).splitlines() if line.strip()]


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
	"""APPROVED or CHANGES REQUIRED from a review's first line, or None if there's no verdict."""
	if not path.exists():
		return None
	match = re.search(r"Verdict:\s*(APPROVED|CHANGES REQUIRED)", read(path))
	return match.group(1) if match else None


def session_cost(transcript: Path) -> float:
	"""The 'Total cost (USD)' that v2 writes at the end of its transcript."""
	if not transcript.exists():
		return 0.0
	costs = re.findall(r"Total cost \(USD\): \$([\d.]+)", read(transcript))
	return float(costs[-1]) if costs else 0.0


def last_index(items: list[str], value: str) -> int:
	"""Position of the last occurrence of value, or -1."""
	return max((i for i, item in enumerate(items) if item == value), default=-1)


def read(path: Path) -> str:
	return path.read_text(encoding="utf-8")


if __name__ == "__main__":
	main()

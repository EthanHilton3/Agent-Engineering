# Native Claude Code harness

This folder builds the app in `spec.md` with Claude Code. A main session acts as orchestrator and runs three subagents (planner, developer, reviewer) through a fixed workflow. Hooks enforce the rules that matter most. It's built entirely from Claude Code's own features: `CLAUDE.md`, subagents, skills, a slash command, permissions, and hooks.

## How to run it

1. **Open this folder as its own VS Code window** (File → Open Folder → `build-b-claude`). Claude Code finds `CLAUDE.md`, `.claude/agents`, `.claude/skills` and `.claude/settings.json` from the folder it starts in. If you start it from the repo root, none of this loads.
2. Start Claude Code with the **same model build A used** (`/model`), so the harness is the only difference between the two builds.
3. Type `/build`. It runs until a checkpoint:
   - when the plan is final: read `handoff/plan.md`
   - after each code review: read `handoff/review-N.md`
4. Type `/build` again to continue. Add a note when you want to steer, e.g. `/build keep the UI in separate files per panel`.
5. Check progress at any time with `python .claude/skills/build/workflow.py status`.

The first time, Claude Code may ask you to trust the folder and approve its hooks. That's expected.

## What each piece does

| File | Claude Code feature | When it takes effect |
|---|---|---|
| `CLAUDE.md` | Project memory | Loaded into **every** session automatically. Kept short: a map of the folder and the hard rules. |
| `.claude/skills/*/SKILL.md` | Skills | Only each skill's `description` is loaded up front. The full text loads when it's relevant, or when a subagent's `skills:` preloads it. This is **progressive disclosure**. |
| `.claude/skills/build/` | Skill as a slash command | `/build`. `disable-model-invocation: true` means only you can start it. |
| `.claude/skills/build/workflow.py` | A plain script | The orchestrator runs it to learn the next step and the exact subagent prompt. **Determinism over agent decisions.** |
| `.claude/agents/*.md` | Subagents | Each runs in a **fresh context window**, with its own system prompt and a restricted tool list. This is **context isolation**. |
| `.claude/settings.json` → `permissions` | Permission rules | `allow` skips approval prompts for safe commands (npm test, etc.). `deny` blocks reading sibling builds and editing the spec. |
| `.claude/hooks/guard.py` | PreToolUse hook | Runs **before every tool call**. Exit code 2 blocks the call and tells Claude why. Keeps Claude inside the folder and stops it editing the spec or harness. |
| `.claude/hooks/check.py` | Stop hook | Runs **whenever a session tries to finish**. If tests or the type check fail, Claude is sent back with the failure output (once, so it can't loop). |
| `handoff/` | Plain files | The only channel between subagents, which share no memory. |

## Prompt-level vs. mechanical rules

A prompt can only ask the agent to follow a rule. For the rules that matter, this harness makes breaking them impossible.

| Rule | Prompt only | This harness |
|---|---|---|
| Don't look at the other build | Asked | **Blocked** by `guard.py` and `deny` rules |
| Don't edit the spec or harness | Asked | **Blocked** |
| Planner writes no code | Asked | Planner has **no Bash tool**, and is told not to write code |
| Reviewer doesn't fix code | Asked | Reviewer has **no Edit tool**, and is told not to change code |
| Don't finish with failing tests | Asked | **Enforced** by the Stop hook |
| Steps in the right order | Asked | Decided by `workflow.py`, which the orchestrator calls |

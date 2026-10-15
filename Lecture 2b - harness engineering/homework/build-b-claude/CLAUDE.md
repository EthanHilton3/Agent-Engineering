# Catan Lite: team harness

This folder builds the app in `spec.md` with three subagents: **planner**, **developer**, and **reviewer** (`.claude/agents/`). The user starts and continues the build with `/build` (`.claude/skills/build/`). Subagents start with no memory of earlier sessions. Everything they know comes from files, and everything the next session needs must be written to a file.

## Folder map

| Path | What it is | Who writes it |
|---|---|---|
| `spec.md` | Product spec, the source of truth for behavior | Nobody. Never edit it. |
| `CLAUDE.md`, `HARNESS.md`, `.claude/` | The harness | Nobody. Never edit it. |
| `handoff/plan.md` | Architecture, test plan, milestone checklist | planner (developer only ticks boxes) |
| `handoff/plan-review.md`, `handoff/review-N.md` | Reviews | reviewer |
| `handoff/progress.md` | One entry per developer session | developer |
| `handoff/sessions.log` | Step history, kept by `workflow.py` | Nobody. Don't edit it. |
| everything else | The app | developer |

## Rules

- **Stay in this folder.** Never read, search, or run commands against anything outside it. Sibling folders contain other builds of the same app, and a hook blocks access to them.
- **Never start a process that doesn't exit by itself** (`npm run dev`, `vite`, watch mode). Verify with `npm test`, `npm run typecheck`, and `npm run build`.
- **Never claim a check passed** unless you ran it in this session and saw the result.
- **Write your handoff file as you go**, not only at the end.
- `spec.md` defines the Catan rules. Don't look rules up elsewhere.
- A Stop hook runs `npm test` and `npm run typecheck` (once they exist) whenever a session tries to finish, and sends failures back to you.

## Skills

The skills in `.claude/skills/` are `code-style`, `bottom-up-code`, `testing`, `project-setup`, `debugging`, and `ui-code`. Each one's description says when to use it.

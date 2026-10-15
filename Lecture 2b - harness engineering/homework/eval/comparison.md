# Build A vs. Build B: evaluation

- **Build A:** Claude Code, one prompt: "Build the app described in spec.md".
- **Build B:** Claude Code with the native harness in `build-b-claude/` (planner → plan review → 10 developer milestones → code review).

Both builds use the same `spec.md`. Both were evaluated on 2026-10-13 with the same independent checks:

- `eval/scenarios-build-a.ts`
- `eval/scenarios-build-b.ts`

These are one set of checks, ported to each build's API. They are separate from either build's own tests. The UI was not played in a browser. It was checked by reading the code (and by B's reviewer).

## Results

| | Build A (one-shot) | Build B (harness) |
|---|---|---|
| `npm run dev`, `typecheck`, `build` | All pass | All pass |
| Own test suite | 41 tests, 7 files, all pass | 98 tests, 10 files, all pass |
| **Independent 20 scenarios + extra edge cases** | **20/20** | **20/20** |
| UI requirements in spec | All present | All present |
| Known bugs | None found | 1 minor UI bug, found by its own reviewer but not fixed: clicking a building on a hex while moving the robber does nothing |
| Wall time | **13.2 min** | **63.7 min**: 55 min of agent time plus about 8 min waiting at the plan checkpoint |
| Model calls | 32 | 235 (orchestrator 47 + 14 subagents 188) |
| Output tokens | 81k | 201k |
| Cache reads / writes | 3.1M / 116k | 12.5M / 947k |
| **Cost (Opus 5.5 API rates)** | **$3.17** | **$11.42 (3.6×)** |
| Times I had to step in | 0 (by design) | 2 checkpoints (plan approval, review result) |

### Where build B's time and money went

| Phase | Time | Cost |
|---|---|---|
| Planning: plan, plan review, revision | 8.1 min | $1.60 |
| Development: 10 milestones | 42.3 min | $7.66 ($0.24–$1.30 each; the rules milestones M4–M7 cost the most) |
| Code review | 3.6 min | $1.05 |
| Orchestrator: main session running `workflow.py` and dispatching | (overlaps the above) | $1.10 |

How these numbers were measured:

- Source: Claude Code's session transcripts (`~/.claude/projects/…/*.jsonl`), counting each API response once. Build B counts the orchestrator plus all 14 subagent transcripts, up to the end of the build.
- Prices: claude-opus-5-5 at $4 per million input tokens, $20 output, $0.20 cache read, and $8 cache write (both sessions used 1-hour cache entries). These are API-equivalent costs; on a subscription plan this is usage, not a bill.

Most of the extra cost comes from **context isolation**. Every new subagent starts cold, re-reads `CLAUDE.md`, the skills, the plan and the code it needs, and writes all of that to cache again: about 900k tokens of cache writes, against 116k for the one-shot. Fresh, focused contexts are what keep each session sharp, and this is what they cost.

**Correctness was a tie.** The detailed spec, with its 20 acceptance scenarios, was enough for the one-shot build to get every rule right. In effect, the spec acted as a harness of its own.

## Code

| | Build A | Build B |
|---|---|---|
| Lines: engine / UI / CSS / tests | 949 / 564 / 142 / 892 | 1,182 / 1,019 / 541 / 1,890 |
| Source files | 9 | 22 |
| Largest file | `game.ts`, 557 lines (the whole rules engine is one class) | `boardView.ts`, 207 lines; every file is under 300 |
| Engine structure | One mutable `Game` class: setup, production, robber, building, trading, Longest Road, and victory all in methods of one class | 13 modules, one per rule area (`placement`, `production`, `turn`, `building`, `longestRoad`, `scoring`, ...) |
| State model | Methods mutate `this.state` | Pure reducer: `applyAction(state, action)` returns a new state, or an error that leaves the input untouched |
| Phase rules | Checked inside each method | One `ALLOWED_ACTIONS` table, checked before any handler runs |
| UI structure | `app.ts` (407 lines) renders the whole page from one template | 7 files, one per screen area (board, panels, action bar, log, debug, screens) |
| Board model | Shared corner/edge graph | Shared corner/edge graph (same idea) |
| Input validation | Out-of-range corner/edge IDs aren't checked | `isValidId` on every placement |
| Tests per scenario | 1 test each | 1–2 each, plus both sides of each rule (allowed and rejected) |
| Docs of decisions | README "Rule interpretations" (4 bullets) | `plan.md` Decisions (11 numbered), `progress.md` deviations per session |

Both are clean code. B is better organized: smaller units, a single source of truth for phases, and an immutable state model. A is smaller and quicker to read in one pass. The real difference would show up when changing the code, which is the next experiment.

## What the harness caught that a one-shot can't

- **Plan review, before any code existed:**
  - Scenarios 7 and 11 couldn't be tested at milestone M5, because cities only arrive in M6.
  - Test helpers were planned before the actions they depend on existed.
  - The spec is ambiguous about Longest Road when a holder is "tied but below 5."
- **Code review:** a real UI bug (finding 1). Because it was "minor", the verdict was still APPROVED and the bug was never fixed. This is a harness design flaw: minor findings get no follow-up step.

## Suggested next experiment: a change request

Give both builds the same request in fresh sessions, for example "Add ports: 9 harbors (4 generic 3:1, 5 resource-specific 2:1) on the coast; a settlement or city on a harbor's corners unlocks that rate."

Compare the following for each build:

- files touched
- lines changed
- whether anything broke
- time and cost
- whether the new code fits the existing structure

Ports depend on corner geometry and trade rules, so they exercise exactly the parts the two architectures handle differently.

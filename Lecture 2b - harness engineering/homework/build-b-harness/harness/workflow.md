# Workflow: plan → review plan → develop → review code

This harness builds the app in `spec.md` using my own agent (`My Agent Project/agent_v2.py`) in three roles. Each step is a **separate agent session** that starts with an empty context. Roles hand work to each other **only through files** in `handoff/`.

```
          ┌──────────┐   plan.md   ┌─────────────┐
 spec ──▶ │ planner  │ ──────────▶ │  reviewer   │──▶ plan-review.md
          └──────────┘ ◀────────── │ (plan mode) │
                ▲    revise once if CHANGES REQUIRED
                │                  └─────────────┘
       YOU: read & approve plan
                │
                ▼
          ┌──────────┐  one milestone per session, repeat until all [x]
          │developer │ ◀─────────┐
          └──────────┘           │ fix mode (max 3 rounds)
                │ progress.md    │
                ▼                │
          ┌─────────────┐  review-N.md: CHANGES REQUIRED
          │  reviewer   │ ───────┘
          │ (code mode) │ ──▶ APPROVED ──▶ done
          └─────────────┘
```

## Running it

From the `build-b-harness` folder:

```
python harness/run.py next      # runs whatever step comes next
python harness/run.py status    # where things stand, plus total cost so far
```

Repeat `next` until it says done. Run `status` and skim the files between steps; those are your checkpoints.

Other options:
- **Specific step:** `python harness/run.py plan | review-plan | dev | review`
- **Steer a step:** `--note "..."`, e.g. `python harness/run.py dev --note "the board test helper is duplicated; reuse it"`
- **Talk to the session yourself:** `--chat`
- **Preview the prompt and kickoff without spending anything:** `--dry-run`

## The steps

| Step | Role and model | Reads | Writes | How `run.py` decides it's next |
|---|---|---|---|---|
| `plan` | planner, gpt-5.6-sol | spec.md | `handoff/plan.md` | There's no plan yet, or the plan review asked for changes and no revision has run |
| `review-plan` | reviewer, gpt-5.6-sol | spec.md, plan.md | `handoff/plan-review.md` | There's a plan that hasn't been reviewed yet |
| `dev` | developer, gpt-5.6-terra | plan.md, progress.md, (review-N.md) | app code, `progress.md`, ticks a box in plan.md | Some milestone is still unticked, or the latest code review asked for changes |
| `review` | reviewer, gpt-5.6-sol | everything; runs the tests | `handoff/review-N.md` | All milestones are ticked, and no review has run since the last dev session |

The plan review runs once. If it asks for changes, the planner revises once and development starts. To get a second plan review, run `review-plan` by hand. Code review can loop up to 3 rounds. After that the harness stops and hands the decision back to you.

## Your checkpoints

1. **After `plan`** (and after `review-plan`), read `handoff/plan.md` before any code is written. This is the cheapest point to change direction. Check:
   - whether the data model makes the hard rules easy
   - whether every milestone is small
   - whether you agree with the decisions

   To change something, run `plan --note "..."` or edit plan.md yourself.
2. **After each `dev`**, skim the new entry in `handoff/progress.md`. If a session ended `partial` (it ran out of model calls), the next `dev` call continues the same milestone.
3. **After each `review`**, read the verdict. You can override it:
   - `dev --note "skip finding 4, it's out of scope"`
   - or stop.
4. **At the end**, play the game (`npm run dev`) and run the independent scenario check in `../eval/`.

## Files

```
build-b-harness/
├── spec.md                   identical copy of ../spec.md, never edited
├── harness/                  everything I wrote (the turn-in)
│   ├── workflow.md           this file
│   ├── run.py                driver: picks the step, builds the prompt, runs v2, logs it
│   ├── shared/operating-rules.md   loaded for every role
│   ├── roles/                planner.md, developer.md, reviewer.md
│   └── skills/               code-style, bottom-up-code, testing (always loaded per role)
│                             project-setup, debugging, ui-code (loaded on demand)
├── handoff/                  written by the agents: plan, reviews, progress, sessions.log
├── transcripts/              NN-step.md = transcript + cost; NN-step.prompt.md = the exact prompt
└── (the app: package.json, src/, tests/ ... written by the developer)
```

## Why it's built this way

| Choice | Reason (lecture concept) |
|---|---|
| **Three roles in separate sessions** | *Context isolation.* Each session sees only what its job needs, and v2 resends the whole history on every call, so short sessions also cost less. The reviewer never wrote the code, so it doesn't share the developer's blind spots. |
| **Handoff files instead of chat memory** | *Agent legibility.* If a decision isn't written down in the folder, the next session doesn't know it. It also makes every handoff something I can read and edit. |
| **One milestone per dev session** | v2 stops after 30 model calls per message. Small milestones fit within that, and progress is saved after each one. |
| **`run.py` picks the next step and writes the kickoff** | *Determinism over agent decisions.* The order of steps, which milestone is next, and which review to fix are decided by code, not left for the agent to work out. |
| **Some skills pasted in, others listed with "read it when"** | Skills every session of a role needs are always loaded, so they can't be skipped. Situational ones use *progressive disclosure*: only a one-line description sits in the prompt until it's needed. |
| **Verdict line and milestone checkboxes in fixed formats** | Code can read them to decide the next step, so the workflow doesn't depend on me interpreting prose. |
| **Different models per role** | Planning and reviewing need careful reasoning, so they use the strongest model. Development is many cheaper calls, so it uses a mid-tier model. This follows `rosters/dev/feature_flow`. |
| **Prompt saved with each transcript** | *Reviewing past conversations.* When a session goes wrong, I can see exactly what the agent was told and fix the harness, not just the code. |
| **No Catan-specific hints anywhere in the harness** | So the comparison with the one-shot build is fair. The harness adds process, not domain answers. |

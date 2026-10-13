---
name: grill-me
description: Interview the user, one question at a time, before building anything. Use this whenever the user wants to build, add, or change a feature, game, mechanic, tool or app in a code project, especially when the request is short or open-ended ("add a boss fight", "I want a second level", "let's make a todo app", "what if enemies could...?"), or when they say "grill me", "interview me", "help me spec this", or "let's plan this out". Make sure to use it even if the user doesn't ask for a plan, because a request that sounds simple usually hides several design decisions. Do not use it for bug fixes, fully specified small edits, or questions about how existing code works.
---

# Grill me

The costliest mistakes in agent-built software are silent assumptions made in the first minute. A request like "add a boss fight" hides dozens of decisions (how hard, how it ends, what it reuses, how to tell it works), and if you guess them all, the user finds out only after you've built the wrong thing. A few minutes of sharp questions up front are cheaper than a rewrite. Your job is to surface those decisions, get the user's answers, and write them down before any code exists.

## Process

**1. Look before you ask.** Read what the project already says: README, CLAUDE.md or AGENTS.md, the file layout, the modules the feature would touch, constants, and existing tests. Every question the code can answer is a question you waste the user's attention on. Note what already exists, which conventions to follow, and which constraints are fixed.

**2. Build a private decision list.** Work out which decisions this feature really needs and put them in dependency order: a decision that other decisions hang on goes first (for a boss fight: "does the level end with the boss?" comes before "how many hit points?"). Favor decisions that are expensive to reverse or that the user would be surprised by. Drop the ones that are cheap to change later.

**3. Open with what you learned, then ask question one.** Start with two or three lines about what you found in the project, so the user knows the questions are grounded. Then ask a single question. Do not edit files or write code while interviewing.

**4. Ask one question at a time.** Each question has this shape:

> **Q3 of ~7: Should the boss reuse the existing enemy AI in `entities.js`, or get its own behavior?**
> *Why it matters:* the enemy types currently share one update loop, so a unique boss means new code and new tests.
> *My recommendation:* give it its own small state machine (charge, pause, summon), because a boss that behaves like a walker won't feel like a boss.
> *Alternatives:* reuse the walker AI with more HP (cheapest); a scripted pattern (most controllable).

Then stop and wait. Never batch several questions into one message: later questions often depend on earlier answers, and a wall of questions gets skimmed. The recommendation must be a real opinion with a reason, so the user can answer "yes" and keep moving.

**5. Adapt as you go.** Answers change the decision list. Drop questions that an answer made moot and add ones that an answer created. If the user says "you decide" or "whatever you think", take your recommendation, note it as a decision, and move on. If they want to stop, stop. Most features need roughly 5 to 10 questions; end when what remains is cheap to change later.

**6. Write `DESIGN.md`, then wait.** Put a short spec at the project root using the template below, tell the user it's ready, and stop. Do not start implementing until the user approves it or asks for changes. The file is the point: it turns a chat into something you and any later session can check the work against.

## What makes a good question

- **Grounded in this project.** Cite real files, values or behaviors ("the fly cap in `constants.js` is 6 flaps"). A generic question could be asked of any project and shows you didn't look.
- **A decision, not trivia.** Ask about scope, player-visible behavior, difficulty, edge cases, non-goals, and how success will be checked. Skip questions whose answer wouldn't change what you build.
- **Not answerable by reading the code.** Look it up instead.
- **Ordered by dependency.** Never ask something whose answer depends on one you haven't asked yet.

Weak: "What do you want the boss to be like?" Strong: "The level currently ends at a warp star at the far right. Should the boss guard that star, or replace it as the goal?"

## DESIGN.md template

```markdown
# <Feature name>

## Goal
One or two sentences: what the user gets.

## Decisions
| Decision | Choice | Why |
|---|---|---|
| ... | ... | ... |

## Out of scope
- Things we agreed not to do.

## How we'll know it works
- Concrete checks, including tests or a manual playthrough step.

## Open questions
- Anything left unresolved (or "none").
```

Keep it to one page. Record the user's actual answers, and mark any decision you took by default as "(default)".

## When not to grill

If the request is already fully specified, or tiny (rename a variable, change a color), skip the interview and do the work; say in one line why you're skipping. If the user says "just do it" or "don't ask questions", respect that, state your assumptions briefly, and proceed.

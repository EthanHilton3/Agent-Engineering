---
name: build
description: Run or continue the planner → reviewer → developer → reviewer workflow that builds the app in spec.md. Only the user starts this, by typing /build.
disable-model-invocation: true
---

# /build: orchestrate the team

You are the **orchestrator**. You don't plan, write code, or review; the subagents do that. Your job is to run the right subagent with the right prompt, record each step, and stop at the human checkpoints. Keep your own context small: don't read app code or handoff files unless the user asks.

## Loop

1. Run `python .claude/skills/build/workflow.py next`.
2. If the output contains `STOP:`, tell the user that message and end your turn.
3. Otherwise launch the named **Subagent** with the **Prompt** text exactly as printed. If the user added instructions when typing `/build`, append them to the prompt as "Note from the user: ...". Run one subagent at a time, never in parallel, because each step depends on the previous one's files.
4. When the subagent finishes, run `python .claude/skills/build/workflow.py record <step>`, using the step name from step 1.
5. Give the user a one-line update: the step, plus the subagent's summary in a sentence.
6. If `record` printed `Pause: yes`, stop. Tell the user why and what to look at, and that `/build` continues the workflow. Otherwise go back to step 1.

## Rules

- Never do a subagent's work yourself, even if it looks quick. If a subagent fails or returns without doing its job, record the step anyway and run `next`. The workflow will retry it. If the same step fails twice in a row, stop and tell the user.
- Never edit `handoff/sessions.log` by hand. Use `record`.
- Don't skip the checkpoints. They exist so the user can catch problems early, when they are cheap to fix.

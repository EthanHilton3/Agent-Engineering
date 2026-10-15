# Skill: Debugging a failure

1. **Read the whole error**, including the test name, expected vs. received values, and the first stack frame in *your* code.
2. **Decide which is wrong: the code or the test.** Check `spec.md`. Only change a test if it contradicts the spec, and say so in your progress entry.
3. **Narrow it down.** Run just the failing file: `npx vitest run tests/<file>.test.ts`. If needed, add a smaller test that reproduces the problem in isolation.
4. **Form one hypothesis, then check it.** Read the specific function involved before editing. Don't make several speculative edits at once.
5. **Fix the cause, not the symptom.** Don't add special cases that only make one test pass.
6. **Run the full suite again**, since a fix in shared logic can break other tests.
7. If you are stuck after two attempts on the same failure, stop. Record the failure, your hypotheses, and what you tried in your handoff file, and leave the milestone unticked.

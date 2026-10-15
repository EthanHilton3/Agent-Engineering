---
name: testing
description: How to write and judge tests, including acceptance-scenario tests. Use whenever writing, changing, or reviewing tests, or planning a test strategy.
---

# Skill: Testing

- Test at the **outermost meaningful boundary**, meaning the game's public actions and queries, not private helpers. A test should still pass after a refactor that doesn't change behavior.
- Write a test for every acceptance scenario in `spec.md`. Name it `Scenario N: <short description>` so it's easy to find.
- Each scenario test asserts the **outcome the spec describes** (who received what, which spots are legal, who holds Longest Road), not merely that no error was thrown.
- Test both sides of a rule: one case where it allows something and one where it forbids it.
- Use seeds and debug hooks (forced dice rolls, given resources) to make tests deterministic. Never depend on `Math.random`.
- Small test helpers that build a game state are fine. Keep them in one helper file, and prefer helpers that set up state through public actions where that's practical.
- Don't mock internal modules. The rules engine is pure logic and needs no mocks.
- Run the whole suite with `npm test` (`vitest run`). Never use watch mode.

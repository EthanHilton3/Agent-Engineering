Verdict: CHANGES REQUIRED

## Findings

1. [major] Section 6, M5 (Scenarios 7 and 11) and Section 5 intro: Scenarios 7 and 11 can't be set up with public actions at M5. Scenario 7 needs a city, and that only arrives with `buildCity` in M6. Scenario 11 needs two players each owed 2 wheat on one roll, and one player owed 3 wheat. With settlements only, a hex holds at most 3 settlements (distance rule), and setup gives each player 2. So "each owed 2" needs cities, or a lucky seed with two wheat hexes sharing a number. "Owed 3" needs a city plus a settlement, or a third settlement that is built in normal play (M6). Section 5 says "A scenario test builds its state through `createGame` and `applyAction`", so the M5 developer would have to break that rule or leave the M5 "Done when" unmet. Required change: move Scenarios 7 and 11 (the `production.test.ts` cases that need cities or extra settlements) to M6, after `buildCity` and `buildSettlement` exist. Update the M5 and M6 `Scenarios:` lines and the M5 "Done when" to match. Scenarios 6 and 8 can stay in M5, because setup settlements are enough for them.

2. [minor] Section 2, Snake order / Piece limits walk-throughs: the plan never says that setup placements use up pieces from the supply. Scenario 18 ("placed all 5 settlements") counts the 2 setup settlements, and the 15-road limit counts the setup roads. Required change: state in the setup walk-through (or in the `setupPhase.ts` row) that `placeSetupSettlement` does `pieces.settlement--` and `placeSetupRoad` does `pieces.road--`, at no resource cost.

3. [minor] Section 3, `tests/helpers.ts` row, and M4 Files: M4 creates `tests/helpers.ts` with `giveCards`, `forceRoll`, and `toMainPhase`. Those depend on the debug actions and `roll`, which only arrive in M5. Required change: say that M4 adds `newGame`, `act`, and `runSetup`, and M5 adds `giveCards`, `forceRoll`, and `toMainPhase`.

4. [minor] Section 7, Decision 10, against spec "Longest Road": the spec says "If the holder is still tied for longest after a break, they keep the card", with no length condition. The plan's rule (`L[h] >= 5 && L[h] >= max(others)`) takes the card from a holder who is tied at 4 after a break. Applying the ≥5 threshold is defensible, since it matches the set-aside rule "nobody has at least 5". The decision should name this conflict explicitly, though. Required change: extend Decision 10 to cover the "tied but below 5" case, and add a matching test line in Section 5 (`longestRoad.test.ts`: holder tied with another player at 4 after a break, so the card is set aside).

5. [minor] Section 2 note under the types, and Section 3 `updateLongestRoad(state): GameState` / `checkWinner(state): GameState`: `applyAction` clones once and then hands the copy to the handlers. That suggests handlers mutate the clone, yet these helpers are typed to return a `GameState`. It isn't clear whether they mutate in place or return a new state, and mixing the two styles is a common source of bugs where an update gets lost. Required change: pick one convention and state it in one sentence. For example, "helpers called inside a handler mutate the cloned state in place and return `void`", with signatures to match.

6. [minor] Section 3, `placement.ts` `legal*` queries: the plan doesn't say whether `legalSettlementCorners`, `legalRoadEdges`, and `legalCityCorners` in the `main` phase take affordability and pieces left into account. If they don't, the UI highlights spots that the click will then reject. If they do, the UI needs a way to explain why nothing is highlighted. Required change: state that the `legal*` queries return `[]` when the current player can't pay for or has no pieces left of that build, and that the build-mode buttons show the matching engine error. The error comes from a pure read such as `buildError(state, kind): string | null` in `placement.ts`, so the UI never checks costs itself.

## Notes

- Walk-throughs I checked against the data model, all easy to compute with no special cases:
  - **Scenario 5:** `setupOrder(3) = [0,1,2,2,1,0]`, `turnIndex` 0..5, and at 6 the phase goes to `roll` with player 0. `turnIndex >= n` correctly marks the second settlement for Scenario 4.
  - **Scenario 11:** the per-resource `owed` sum compared with `bank[r]`, plus a count of owed players, gives exactly the spec's three outcomes.
  - **Scenario 16:** the edge-trail DFS on a degree-3 junction yields 3+3 = 6.
  - **Scenario 17:** `blockedByOpponent(y)` stops the walk at the mid-chain corner, giving 3/3. The holder rule then reassigns the card or sets it aside.
  - **Scenarios 9 and 10:** `discardAmount` and the candidate set (distinct owners on `hexCorners[robberHex]` minus the roller) are direct lookups.
- Scenario 15's claim that "exceeding takes, ties don't" follows from the holder rule. I checked the reasoning: each road placement can only raise the placer's length, and each settlement placement can only lower other players' lengths.
- Scenario 17's test should cover both outcomes the spec names: card reassigned to a unique leader of 5 or more, and card set aside.
- Scenario tests that give cards should work from `totalCards(hand)` and not assume empty hands, because setup's second settlement already hands out resources.
- `tests/smoke.test.ts` (M1) should be deleted once real tests exist. `tests/resources.test.ts` tests low-level helpers; keep it small and prefer behavior tests through `applyAction`, per the testing skill.
- M2 (4 small source files) and M9 (5 UI files) are a little above the "1–3 source files" guideline. Both are thin enough to fit in one session.
- `Player.color` in engine state is a UI concern, but it's harmless and keeps the setup simple.

Verdict: APPROVED

## Verification

Run in this review session from the project folder:

- `npm test` (vitest run): 10 files, 98 tests passed, exit 0.
- `npm run typecheck` (tsc --noEmit): clean, exit 0.
- `npm run build` (tsc --noEmit && vite build): succeeded. 25 modules; dist/index.html 0.39 kB, CSS 5.91 kB, JS 31.74 kB.
- `grep` for `any` types in `src/`: none found. Every file is under 300 lines; the largest are `src/ui/boardView.ts` at 207 and `src/engine/turn.ts` at 197.
- Tests import only from `src/engine/*` and `tests/helpers.ts`, as the plan requires.

### Spec conformance (section by section)

| Spec section | Where | Result |
|---|---|---|
| Board: 19 hexes, 3-4-5-4-3, terrain and number multisets, desert unnumbered, no adjacent 6/8, robber on desert, seeded | `topology.ts`, `board.ts`, `game.ts:29` | OK (reshuffle loop on the same RNG stream, `board.test.ts`, `setup.test.ts` creation test) |
| Seed shown and enterable | `app.ts:134`, `screens.ts` new-game form, `debugPanel.ts` | OK |
| Pieces 15/5/4, costs, city returns settlement, bank 19 each, spent/discarded cards to bank | `game.ts:28,169`, `resources.ts:7`, `building.ts` | OK |
| Distance rule (setup and play), settlement needs own road, road connects and not through an opponent's building, city replaces own settlement | `placement.ts:17-50,101-108` | OK |
| Setup: snake order, settlement then road touching it, 2nd settlement pays 1 per non-desert hex, P1 starts | `setupPhase.ts` | OK |
| Roll: production with robber exclusion, 1/2 per settlement/city, per-hex visits for shared corners | `production.ts:20-36` | OK |
| Bank shortage per resource, with the sole-claimant exception | `production.ts:42-54` | OK |
| 7: discard floor(n/2) above 7 in turn order, robber must move (desert allowed), steal from adjacent opponents only, none on 0 cards, no production | `turn.ts:126-171`, `placement.ts:71` | OK |
| Trade 4:1 if the bank has it; build in any order | `building.ts:52-76` | OK |
| End turn passes in order | `turn.ts:82` | OK |
| Phase enforcement | `game.ts:80-106` (`ALLOWED_ACTIONS` guard before any handler) | OK |
| Longest Road: trail DFS, edges used once, loops count, opponent buildings break, 5 to take, exceed to take, holder keeps on tie, reassign or set aside after a break, re-evaluated after each road/settlement | `longestRoad.ts` | OK (Decision 10 below-5 interpretation, see Notes) |
| Victory: 10 VP on own turn; other-turn win at the start of the next own turn; game stops | `scoring.ts`, `game.ts:48`, `game.ts:103` | OK |
| UI: terrain colors, 6/8 emphasized, robber, legal-only highlights, player panels (name/color, VP, cards, pieces, road length, current hand), phase/current player, dice, log, error messages, discard prompts in turn | `src/ui/*` | OK (one minor click issue, Finding 1) |
| Debug: seed + new game, force roll, give resource, show IDs | `debugPanel.ts`, `boardView.ts:169` | OK |
| Log covers rolls, production, builds, trades, discards, robber, steals, Longest Road changes, win | every `log.push` in `src/engine` | OK |

### Acceptance scenarios: each test checks the spec's outcome

| # | Test (file) | What it asserts |
|---|---|---|
| 1 | board.test.ts:9 (and setup.test.ts "uses the same board for the same seed" via `createGame`) | Boards deep-equal for 4 seeds |
| 2 | board.test.ts:15 | 100 seeds; no 6/8 has a 6/8 neighbour |
| 3 | setup.test.ts:79 | Neighbours are offered before placement and absent after; placing on one gives the distance error; a corner two edges away is still legal; exact legal count |
| 4 | setup.test.ts:103 | 0 cards after the first round; the 2nd settlement next to the desert pays exactly 2 matching cards; bank total conserved |
| 5 | setup.test.ts:126 | Observed placement order is [1,2,3,3,2,1] and the same player places the road |
| 6 | production.test.ts:81 | A three-hex corner earns exactly one card from each hex across the rolls, and the other player gets nothing |
| 7 | production.test.ts:188 | The same corner pays 1 as a settlement and 2 as a city; bank drops by 2 |
| 8 | production.test.ts:103 | The hex pays without the robber; after the robber moves there, the same roll changes no hand and no bank count |
| 9 | robber.test.ts:56 | Pending is exactly [{player 0, amount 4}]; 9 goes to 5, and the 7-card player is untouched |
| 10 | robber.test.ts:130 | Candidates [1,2] (roller 0 and non-adjacent 3 excluded); stealing from self or a non-candidate is rejected; the victim loses 1 card and the thief gains it |
| 11 | production.test.ts:207, :223 | Two cities owed 2 each, bank 2: nobody paid and bank stays 2. One player owed 3, bank 2: they get 2 and bank goes to 0 |
| 12 | building.test.ts:64, :83 | The road through an opponent's corner is not offered and is rejected; the same road is legal when the corner is empty |
| 13 | building.test.ts:94 | Road, settlement, city, and trade before rolling are rejected with "Roll the dice first"; no legal spots; the same actions succeed after rolling |
| 14 | longestRoad.test.ts:97 | At length 4: no holder and VP unchanged. At 5: holder and +2 VP, logged |
| 15 | longestRoad.test.ts:114 | Tie at 5/5 keeps holder 0; 6 takes it, with VP -2/+2 |
| 16 | longestRoad.test.ts:52 | Y of 3+3+1: length 6 with 7 roads built |
| 17 | longestRoad.test.ts:134, :145 | 6-chain split 3/3: reassigned to the unique 5, or set aside when nobody has 5 (VP -2, logged) |
| 18 | building.test.ts:120 | 5 placed: `No settlements left`, no legal spots, action rejected. After a city: allowed, then back to 0 |
| 19 | building.test.ts:234 | 4 wood gives -4 wood +1 ore with the bank adjusted; 3 wood is rejected |
| 20 | victory.test.ts:46 | 10 VP gives `gameOver` with winner 0 and a log line; all 11 action types are then rejected with "The game is over". The winner screen itself is UI (`screens.ts:renderWinnerScreen`, rendered by `app.ts:99`) |

Both sides of each rule are covered too: legal and illegal placements, shortage versus enough bank, keep versus take on ties, the piece limits, and the trade limits.

## Findings

1. [minor] src/ui/boardView.ts:22-25 and src/style.css (`.robber`, `.road`, `.building`): the robber, road, and building layers are drawn above the hexes and still receive pointer events. During `moveRobber`, a click that lands on a settlement, city, or road sitting on a highlighted hex hits that element. `closest('.target')` then finds nothing, so the click does nothing and shows no message, although the hex looks clickable there. Required change: add `pointer-events: none` to the `.robber`, `.roads`, and `.buildings` groups in `style.css`. Corner and edge targets are separate elements drawn on top, so they are unaffected.

## Notes

- **Decision 10** (the holder loses the card when a break drops them below 5, even if they are still tied or uniquely longest) is a reasoned reading of a spec gap. It was approved at plan review and is tested for the tied-at-4 case. The uniquely-longest-below-5 case follows from the same `nextHolder` branch but has no test. A one-line test would pin it down if the team wants that.
- **Redundant phase checks:** `mainPhaseError` in `building.ts:66`, the `phase.kind !== ...` checks at the top of `turn.ts` handlers, and the "Setup is over" checks in `setupPhase.ts` can't be reached through `applyAction`, because the dispatcher's phase guard runs first. They are harmless defensive checks. If kept, they are fine. If removed, the dispatcher stays the single source of phase rules.
- **Module-only exports:** `LONGEST_ROAD_MIN_LENGTH` (`longestRoad.ts:5`) and `WINNING_POINTS` (`scoring.ts:4`) are exported but used only inside their own modules. This is harmless.
- **Misleading guard message:** in `main`, a stray `discard`/`moveRobber`/`steal` action gets the guard message "You have already rolled this turn". The UI never sends these, so it doesn't matter in practice.
- **Recorded deviations in `progress.md`:** all acceptable.
  - `describeCounts`, `dom.ts`, the mixed dice seed, `lastRoll = null` on end turn, and the extra hex ID labels all stay within the plan's intent.
  - The new test helpers keep geometry derived from `TOPOLOGY` instead of hard-coded IDs.
  - The direct state edit for the empty-hand steal test is confined to one helper and documented. No public action can empty a hand at that point.
  - Leaving unaffordable build buttons clickable, with `aria-disabled`, so they can show the `buildError` reason matches the spec's "prevented with a short explanation".
- The UI was not exercised in a browser, because there is no DOM test environment and the dev server can't run here. A manual pass with `npm run dev` and the debug panel is still worthwhile for Scenarios 3, 9, 10, 13, 19, and 20.

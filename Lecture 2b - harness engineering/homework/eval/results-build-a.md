# Build A (one-shot) — evaluation results

Evaluated 2026-10-13. The game was not played in a browser. Rules were checked headlessly against the engine, and the UI was checked by reading the code.

## Automated checks

| Check | Result |
|---|---|
| `npm run dev` | Starts, no errors |
| `npm test` (build's own suite) | 41 / 41 pass, 7 files, every spec scenario tagged once |
| `npm run typecheck` | Clean |
| Independent scenario check (`eval/scenarios-build-a.ts`) | **20 / 20 pass** |

Run the independent check from `build-a-oneshot/` with `npx vite-node ../eval/scenarios-build-a.ts -v`.

The independent check goes beyond the spec wording in places:

- terrain and number counts
- 1000 boards with no adjacent 6/8, using hex adjacency computed separately from the build's own neighbour lists
- card conservation through setup
- 4-player snake order
- wrong discard amounts and discarding before the robber is resolved
- robber must move
- bank out of the requested resource
- a closed hex-ring road (length 6)
- a third player inheriting Longest Road when the holder's road is broken
- winning on another player's turn

## Spec scenarios

| # | Scenario | Result |
|---|---|---|
| 1 | Deterministic board | Pass |
| 2 | No adjacent 6/8 | Pass |
| 3 | Distance rule in setup | Pass |
| 4 | Setup resources from second settlement only | Pass |
| 5 | Snake order | Pass |
| 6 | Shared-corner production | Pass |
| 7 | City produces 2 | Pass |
| 8 | Robber blocks production | Pass |
| 9 | Discard on 7 | Pass |
| 10 | Steal targeting | Pass |
| 11 | Bank shortage | Pass |
| 12 | Road through opponent | Pass |
| 13 | Phase enforcement | Pass |
| 14 | Longest Road threshold | Pass |
| 15 | Longest Road tie | Pass |
| 16 | Longest Road branches (Y = 6) | Pass |
| 17 | Broken road | Pass |
| 18 | Piece limits | Pass |
| 19 | Bank trade | Pass |
| 20 | Win condition | Pass |

## UI requirements (checked by reading the code)

All present:

- legal-spot highlighting
- emphasized 6/8 tokens
- seed display and entry
- per-player panels (VP, card count, road length, pieces left; the current player's hand)
- dice display
- event log
- discard modal for each player
- robber hex selection and victim choice
- bank trade
- winner screen with final scores
- debug panel (seed, forced roll, give resources, show IDs)
- disabled actions show an explanation tooltip

## Code observations (for the comparison)

- **Size:** about 2,550 lines in total. Engine 950, UI 710, tests 890.
- **Board model:**
  - corners and edges are de-duplicated into one shared graph (54 corners, 72 edges) with adjacency lists
  - axial hex coordinates
  - topology computed once
- **Separation:**
  - the engine has no DOM dependency
  - every action returns `{ok}` or `{ok:false, error}`, and a failed action leaves state unchanged
  - the UI re-renders HTML strings from state
- **Weak spots to compare against B:**
  - `game.ts` is a single 557-line `Game` class that handles phases, setup, production, robber, building, trading and victory
  - the UI renders everything as one big template (`app.ts`, 407 lines)
- **Documented rule interpretations (README):**
  - Longest Road is set aside if the holder is tied but below 5
  - a win on another player's turn is checked when the winner's own turn starts
  - a robber with one eligible victim steals automatically

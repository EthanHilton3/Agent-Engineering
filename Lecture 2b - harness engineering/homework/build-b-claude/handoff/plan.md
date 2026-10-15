# Catan Lite: Implementation Plan

## 1. Overview

Catan Lite is a hot-seat browser game for 2–4 players, built with Vite + TypeScript, plus a Vitest suite. The core is a pure, DOM-free rules engine under `src/engine/`: one `GameState` value, and one `applyAction(state, action)` that returns either a new state or an error message. Board geometry (hexes, corners, edges, adjacency) is a static, seed-independent topology computed once, so every rule becomes an index lookup. Board contents (terrain, numbers) come from a seeded PRNG. The UI under `src/ui/` renders the state as SVG/DOM, asks the engine for legal spots and error messages, and never re-implements a rule.

## 2. Data model

```ts
// src/engine/types.ts
export type Resource = 'wood' | 'brick' | 'sheep' | 'wheat' | 'ore';
export type ResourceCounts = Record<Resource, number>;
export type Terrain = 'forest' | 'pasture' | 'fields' | 'hills' | 'mountains' | 'desert';
export type HexId = number;    // 0..18
export type CornerId = number; // 0..53
export type EdgeId = number;   // 0..71
export type PlayerId = number; // 0..N-1 (displayed as "Player 1".."Player N")

export interface Topology {            // static: identical for every game
  hexCoords: { q: number; r: number }[];     // axial, radius 2, rows 3-4-5-4-3
  hexCorners: CornerId[][];                  // 6 per hex
  hexNeighbors: HexId[][];                   // on-board neighbours only
  cornerHexes: HexId[][];                    // 1..3 per corner
  cornerNeighbors: CornerId[][];             // 2..3 per corner
  cornerEdges: EdgeId[][];                   // 2..3 per corner
  edgeCorners: [CornerId, CornerId][];       // endpoints
  cornerPositions: { x: number; y: number }[]; // unit hex size, for the UI
}

export interface Hex { id: HexId; terrain: Terrain; number: number | null }
export interface Board { seed: number; hexes: Hex[] }  // indexed by HexId

export interface Building { owner: PlayerId; kind: 'settlement' | 'city' }
export interface PiecesLeft { road: number; settlement: number; city: number }
export interface Player { id: PlayerId; name: string; color: string; hand: ResourceCounts; pieces: PiecesLeft }

export type Phase =
  | { kind: 'setup'; turnIndex: number; step: 'settlement' | 'road'; lastSettlement: CornerId | null }
  | { kind: 'roll' }
  | { kind: 'discard'; pending: { player: PlayerId; amount: number }[] }
  | { kind: 'moveRobber' }
  | { kind: 'steal'; candidates: PlayerId[] }
  | { kind: 'main' }                                   // trade and build
  | { kind: 'gameOver'; winner: PlayerId };

export interface GameState {
  board: Board;
  players: Player[];
  currentPlayer: PlayerId;
  phase: Phase;
  buildings: (Building | null)[];   // indexed by CornerId
  roads: (PlayerId | null)[];       // indexed by EdgeId
  bank: ResourceCounts;
  robberHex: HexId;
  longestRoadHolder: PlayerId | null;
  lastRoll: [number, number] | null;
  forcedRoll: number | null;        // debug: total for the next roll
  rngState: number;                 // dice and steals; advanced on use
  log: string[];
}

export type Action =
  | { type: 'placeSettlement'; corner: CornerId }   // setup and normal play
  | { type: 'placeRoad'; edge: EdgeId }              // setup and normal play
  | { type: 'placeCity'; corner: CornerId }
  | { type: 'roll' }
  | { type: 'discard'; cards: Partial<ResourceCounts> } // for phase.pending[0]
  | { type: 'moveRobber'; hex: HexId }
  | { type: 'steal'; victim: PlayerId }
  | { type: 'bankTrade'; give: Resource; get: Resource }
  | { type: 'endTurn' }
  | { type: 'debugForceRoll'; total: number }
  | { type: 'debugGiveResource'; player: PlayerId; resource: Resource; amount: number };

export type ActionResult = { ok: true; state: GameState } | { ok: false; error: string };
```

**Mutation convention (one rule, no exceptions):** `applyAction` never mutates its input. It `structuredClone`s the state once at the top and passes the copy (the *draft*) to the handler. Handlers and every helper called inside a handler (`updateLongestRoad`, `checkWinner`, debug actions) **mutate the draft in place and return `void`** (handlers return `string | null`: an error, or `null` for success). `applyAction` returns `{ ok: false, error }` and discards the draft on error, so a handler that fails after a partial change can never leak it; handlers should still validate before mutating, for clarity. Queries (`placement.ts`, `computeProduction`, `roadLength`, `victoryPoints`) are pure reads and never mutate.

### Rule walk-throughs

- **Distance rule (S3):** corner `c` is open for a settlement iff `buildings[c] === null` and `cornerNeighbors[c].every(n => buildings[n] === null)`. In normal play we also need `cornerEdges[c].some(e => roads[e] === player)`.
- **Road connection, including "not through an opponent" (S12):** edge `e` is legal iff `roads[e] === null` and some endpoint `x` of `edgeCorners[e]` satisfies one of two things: `buildings[x]?.owner === player`, or (`buildings[x]` is not an opponent's building and `cornerEdges[x].some(e2 => e2 !== e && roads[e2] === player)`). If `x` holds an opponent's building, that endpoint cannot provide the link. In setup, the road must instead satisfy `edgeCorners[e].includes(phase.lastSettlement)`.
- **Production with shared corners, cities, robber, and shortage (S6–S8, S11):** for roll `n`, look at each hex with `number === n` and `id !== robberHex`. For each `c` of `hexCorners[hex]` with a building, add 1 (settlement) or 2 (city) to `owed[owner][resourceOf(terrain)]`. A corner touching three such hexes is visited once per hex, so shared corners fall out naturally. Then, for each resource: if the sum owed ≤ `bank[r]`, pay everyone; else if exactly one player is owed, pay them `bank[r]`; else pay nobody.
- **Discard (S9):** `amount = handTotal > 7 ? Math.floor(handTotal / 2) : 0`. So 9 cards gives 4 and 7 cards gives 0. `pending` lists the players with `amount > 0`, in turn order starting with the roller.
- **Steal targets (S10):** `candidates` = the distinct owners of `buildings[c]` for `c` in `hexCorners[robberHex]`, excluding `currentPlayer`. If there are 0 candidates, nothing is stolen. If there is 1, the steal is automatic. If there are 2 or more, the phase becomes `steal` and the roller picks a victim.
- **Snake order (S5):** `setupOrder(n) = [0..n-1, n-1..0]`. During setup, `currentPlayer = setupOrder(n)[phase.turnIndex]`. After each road, `turnIndex++`. When it reaches `2n`, the phase becomes `{kind:'roll'}` with `currentPlayer = 0`. A settlement is the second one iff `turnIndex >= n`, and then the player gets 1 of each non-desert `cornerHexes[c]` resource from the bank (S4). Setup pieces come out of the supply at no resource cost: `placeSetupSettlement` does `pieces.settlement--` and `placeSetupRoad` does `pieces.road--`. So after setup every player has 3 settlements and 13 roads left, and Scenario 18's "all 5 settlements" counts the 2 setup ones.
- **Longest Road length (S16, S17):** use a DFS over the player's road edges. `walk(x, used)` = max over edges `e` in `cornerEdges[x]` with `roads[e] === p` and `e` not in `used`, of `1 + (blockedByOpponent(y) ? 0 : walk(y, used ∪ {e}))`, where `y` is the other end of `e`. The answer is the max of `walk(x, ∅)` over all corners touching p's roads. A Y of 3+3+1 has its best trail at 3+3 = 6, because a trail cannot use both branches and the stem without reusing an edge. An opponent's settlement in the middle of a chain stops `walk` there.
- **Longest Road award (S14, S15, S17):** recompute lengths `L` after every road or settlement placement. The holder `h` keeps the card iff `L[h] >= 5` and `L[h] >= max(L of others)` (see Decision 10 for the tied-below-5 case). Otherwise, if exactly one player has the maximum length and it is ≥ 5, that player becomes the holder; else `longestRoadHolder = null`. Because only one player's length grows per placement, "exceed to take, ties don't take" follows from this.
- **Piece limits (S18):** `buildError(state, 'settlement')` is non-null when `pieces.settlement === 0`, so `placeSettlement` fails. Every settlement placement, setup included, does `pieces.settlement--`; every road placement does `pieces.road--`. `placeCity` does `pieces.city--` and `pieces.settlement++`. Scenario 18: 2 setup + 3 built = 5 placed, the 6th is rejected; after one city upgrade it succeeds.
- **Victory (S20):** `victoryPoints(p)` = settlements + 2·cities + (holder === p ? 2 : 0). After every successful action, if `victoryPoints(currentPlayer) >= 10`, the phase becomes `gameOver`. `endTurn` runs the same check for the incoming player.

## 3. Modules

Import rules: `src/engine/*` imports only from `src/engine/*` and never touches `document` or `window`. `src/ui/*` imports from `src/engine/*` and `src/ui/*`. `src/main.ts` imports `src/ui/app.ts`. Tests import only from `src/engine/*` and `tests/helpers.ts`.

| Path | Responsibility | Public API |
|---|---|---|
| `src/engine/types.ts` | All shared types (above) | types only |
| `src/engine/rng.ts` | Seeded PRNG (mulberry32), pure | `randomInt(rngState: number, maxExclusive: number): { value: number; rngState: number }`; `shuffle<T>(items: T[], rngState: number): { items: T[]; rngState: number }` |
| `src/engine/resources.ts` | Resource-count math and costs | `RESOURCES: Resource[]`; `COSTS: Record<'road'\|'settlement'\|'city', ResourceCounts>`; `emptyCounts(): ResourceCounts`; `countsOf(partial): ResourceCounts`; `totalCards(c): number`; `hasAtLeast(have, need): boolean`; `addCounts(a, b)`; `subtractCounts(a, b)`; `terrainResource(t: Terrain): Resource \| null` |
| `src/engine/topology.ts` | Static board geometry: builds `Topology` once. Corners are deduplicated by rounded position; edges are keyed by sorted corner pair. | `TOPOLOGY: Topology`; `edgeBetween(a: CornerId, b: CornerId): EdgeId \| null` |
| `src/engine/board.ts` | Seeded board generation and the 6/8 check | `generateBoard(seed: number): Board`; `hasAdjacentRedNumbers(board: Board): boolean`; `desertHex(board: Board): HexId` |
| `src/engine/placement.ts` | Legality queries (pure reads of state) | `type BuildKind = 'road' \| 'settlement' \| 'city'`; `buildError(state, kind: BuildKind): string \| null` (current player, `main` phase: "Not enough resources" / "No settlements left" etc.; in setup always `null`, since setup is free); `settlementError(state, player, corner): string \| null`; `roadError(state, player, edge): string \| null`; `cityError(state, player, corner): string \| null` (the three `*Error` check location only); `legalSettlementCorners(state): CornerId[]`; `legalRoadEdges(state): EdgeId[]`; `legalCityCorners(state): CornerId[]`; `legalRobberHexes(state): HexId[]` (the last four are for the current player and phase; the three build queries return `[]` when `buildError` is non-null, i.e. the player can't pay or has no pieces of that kind left) |
| `src/engine/production.ts` | Dice production with robber and bank shortage | `computeProduction(state, total: number): ResourceCounts[]` (per player, already shortage-adjusted); `discardAmount(handTotal: number): number` |
| `src/engine/longestRoad.ts` | Road length and holder update | `roadLength(state, player): number`; `updateLongestRoad(draft: GameState): void` (mutates holder, logs changes) |
| `src/engine/scoring.ts` | Victory points and win check | `victoryPoints(state, player): number`; `checkWinner(draft: GameState, player: PlayerId): void` (sets `gameOver` if `player` has ≥ 10 VP) |
| `src/engine/setupPhase.ts` | Setup settlement/road handlers and snake order. Setup placements decrement `pieces.settlement` / `pieces.road` at no resource cost. | `setupOrder(playerCount: number): PlayerId[]`; `placeSetupSettlement(draft, corner): string \| null`; `placeSetupRoad(draft, edge): string \| null` |
| `src/engine/turn.ts` | Roll, discard, robber, steal, end turn | `roll(draft): string \| null`; `discard(draft, cards): string \| null`; `moveRobber(draft, hex): string \| null`; `steal(draft, victim): string \| null`; `endTurn(draft): string \| null` |
| `src/engine/building.ts` | Normal-play builds and bank trade. Each build calls `buildError` then the matching `*Error`. | `buildRoad(draft, edge)`, `buildSettlement(draft, corner)`, `buildCity(draft, corner)`, `bankTrade(draft, give, get)`, all returning `string \| null` |
| `src/engine/game.ts` | Game creation, the action dispatcher, phase guard, debug actions | `createGame(opts: { seed: number; playerNames: string[] }): GameState`; `applyAction(state, action): ActionResult`; `currentPhaseLabel(state): string` |
| `src/main.ts` | Entry point: mounts the app | none |
| `src/ui/app.ts` | Holds the current `GameState`, `dispatch(action)` (shows the error on failure), re-renders all views, and holds UI-only state (selected build mode, debug toggles) | `startApp(root: HTMLElement): void` |
| `src/ui/boardView.ts` | SVG board: hexes, numbers (6/8 emphasized), robber, buildings, roads, clickable legal corners/edges/hexes with `data-corner`/`data-edge`/`data-hex`, optional ID labels | `renderBoard(state, opts: BoardViewOptions): SVGSVGElement` |
| `src/ui/playerPanels.ts` | One panel per player: name/color, VP, card count, pieces left, road length; the current player's hand | `renderPlayerPanels(state): HTMLElement` |
| `src/ui/actionBar.ts` | Phase/current player, dice, roll/end-turn/build-mode buttons, bank-trade form, discard prompt, steal chooser, error message line. A build-mode button whose `buildError(state, kind)` is non-null shows that message (e.g. as its tooltip and in the error line when clicked); the UI never checks costs itself. | `renderActionBar(state, ui: ActionBarProps): HTMLElement` |
| `src/ui/logView.ts` | Event log | `renderLog(state): HTMLElement` |
| `src/ui/debugPanel.ts` | Seed + new game, force roll, give resource, show IDs toggle | `renderDebugPanel(props: DebugPanelProps): HTMLElement` |
| `src/ui/screens.ts` | New-game form (player count/names, seed) and winner screen with final scores | `renderNewGameForm(onStart)`, `renderWinnerScreen(state, onNewGame)` |
| `src/style.css` | Styling | none |
| `tests/helpers.ts` | Test helpers. M4 adds `newGame(players, seed)`, `act(state, action)` (throws on error), `runSetup(state, picks)`. M5 adds `giveCards`, `forceRoll`, `toMainPhase` (they need the debug actions and `roll`). | as listed |

`game.ts` dispatches by `action.type` and phase. Any action not allowed in the current phase returns an error such as `"Roll the dice first"` or `"Discard cards first"` (S13). Debug actions are allowed in every phase except `gameOver`. Every successful non-debug action is followed by `checkWinner(draft, draft.currentPlayer)`.

## 4. Spec coverage

| Spec section | Module(s) |
|---|---|
| Tech stack | M1 scaffold (`package.json`, `tsconfig.json`, `index.html`) |
| Scope | whole plan; out-of-scope items are not built |
| Board | `topology.ts`, `board.ts`, `rng.ts` |
| Pieces and costs | `resources.ts`, `building.ts`, `types.ts` (`PiecesLeft`), bank in `game.ts` |
| Placement rules | `placement.ts` |
| Setup phase | `setupPhase.ts`, `placement.ts` |
| Normal turn: Roll / production / shortage | `turn.ts`, `production.ts` |
| Normal turn: Roll of 7 | `turn.ts`, `production.ts` (`discardAmount`) |
| Trade and build | `building.ts` |
| End turn | `turn.ts` |
| Longest Road | `longestRoad.ts` (called from `building.ts`, `setupPhase.ts`) |
| Victory | `scoring.ts`, `game.ts`, `ui/screens.ts` |
| User interface | `ui/*` |
| Debug mode | `game.ts` debug actions, `ui/debugPanel.ts`, `ui/boardView.ts` (IDs) |
| Acceptance scenarios | see Test plan |

## 5. Test plan

All tests run under Node (no DOM). A scenario test builds its state through `createGame` and `applyAction`, using debug actions for dice and cards. To find corners and edges, tests use `TOPOLOGY` and `board.hexes`, never hard-coded terrain assumptions. Tests that give cards compare against `totalCards(hand)` before and after, never assume empty hands (the second setup settlement already pays out). Scenarios 7 and 11 live in `production.test.ts` but are written in M6, because they need `buildCity` / `buildSettlement` (e.g. Scenario 11: two players each upgrade a setup settlement on the same fields hex to a city, the bank's wheat is drained to 2 with `debugGiveResource`, then the number is forced).

| # | File | Test name |
|---|---|---|
| 1 | `tests/board.test.ts` | Scenario 1: same seed gives identical terrain and numbers |
| 2 | `tests/board.test.ts` | Scenario 2: no adjacent 6/8 across 100 seeds |
| 3 | `tests/setup.test.ts` | Scenario 3: corners next to a setup settlement are not legal |
| 4 | `tests/setup.test.ts` | Scenario 4: only the second setup settlement grants resources |
| 5 | `tests/setup.test.ts` | Scenario 5: 3-player snake order is 1,2,3,3,2,1 |
| 6 | `tests/production.test.ts` | Scenario 6: shared-corner settlement produces from all three hexes |
| 7 | `tests/production.test.ts` | Scenario 7: city produces 2 per roll |
| 8 | `tests/production.test.ts` | Scenario 8: robber hex produces nothing |
| 9 | `tests/robber.test.ts` | Scenario 9: 9 cards discards 4, 7 cards discards nothing |
| 10 | `tests/robber.test.ts` | Scenario 10: only adjacent opponents can be robbed, never the roller |
| 11 | `tests/production.test.ts` | Scenario 11: bank shortage pays nobody, or the single owed player what's left |
| 12 | `tests/building.test.ts` | Scenario 12: road cannot pass through an opponent's settlement |
| 13 | `tests/building.test.ts` | Scenario 13: building and trading before rolling are rejected |
| 14 | `tests/longestRoad.test.ts` | Scenario 14: 4 roads give no card, the 5th grants it (+2 VP) |
| 15 | `tests/longestRoad.test.ts` | Scenario 15: tying the holder does not take the card; exceeding does |
| 16 | `tests/longestRoad.test.ts` | Scenario 16: Y-shaped 3+3+1 network has length 6 |
| 17 | `tests/longestRoad.test.ts` | Scenario 17: opponent settlement splits a 6-chain; card reassigned or set aside |
| 18 | `tests/building.test.ts` | Scenario 18: 6th settlement rejected until a city upgrade frees one |
| 19 | `tests/building.test.ts` | Scenario 19: 4 wood trades for 1 chosen resource; 3 wood is rejected |
| 20 | `tests/victory.test.ts` | Scenario 20: reaching 10 VP on own turn ends the game; later actions rejected |

Other risky logic that needs its own tests:

- `tests/topology.test.ts`: 19 hexes, 54 corners, 72 edges. Every corner has 2–3 neighbours. Adjacency is symmetric. Every edge's endpoints are corner neighbours.
- `tests/board.test.ts`: terrain and number multiset counts are correct. The desert has no number. The robber starts on the desert. Different seeds usually give different boards.
- `tests/setup.test.ts`: a setup road must touch the just-placed settlement. Placing a road before a settlement is rejected. After setup, phase is `roll` and player 1 is current. After setup each player has 3 settlements and 13 roads left.
- `tests/production.test.ts` (M5, setup settlements only): shortage with two players each owed 1 and bank holding 1 pays neither; a single owed player with bank at 0 gets 0; other resources from the same roll are still paid.
- `tests/robber.test.ts`: a discard with the wrong total or with cards not held is rejected. Discard prompts run in order. The robber cannot stay on the same hex. A single candidate is robbed automatically. A victim with 0 cards loses nothing. Stolen cards are conserved. No production happens on a 7.
- `tests/building.test.ts`: cost is deducted and returned to the bank. A city returns a settlement piece. A normal settlement needs its own road. `buildError` and the `legal*` build queries: a player who can't pay gets a non-null `buildError` and `[]` from `legalRoadEdges`; after `debugGiveResource` both allow the build. Bank trade fails if the bank is out of the requested resource and fails when give equals get. 15-road and 4-city limits are enforced.
- `tests/longestRoad.test.ts`: a loop counts every edge once (a 6-edge ring has length 6). The holder keeps the card while still tied (at 5 or more) after a break. The card is set aside when the holder drops below 5 and nobody else has 5 or more. **Holder tied with another player at 4 after a break: the card is set aside** (Decision 10). Scenario 17's test covers both named outcomes: reassigned to a unique leader of 5+, and set aside.
- `tests/victory.test.ts`: a player who reaches 10 VP on another player's turn (via Longest Road reassignment) wins when their own turn starts.
- `tests/conservation.test.ts`: after a scripted sequence, for each resource the bank plus all hands equals 19.

## 6. Milestones

- [x] M1: Project scaffold
  - Goal: Vite + TypeScript + Vitest project per the `project-setup` skill, with a placeholder page.
  - Files: `package.json`, `tsconfig.json`, `index.html`, `.gitignore`, `src/main.ts`, `src/style.css`, `tests/smoke.test.ts`
  - Scenarios: none
  - Done when: `npm test` and `npm run typecheck` pass, and `npm run build` succeeds.
- [x] M2: Core types, RNG, resources, topology
  - Goal: the shared types, seeded PRNG, resource math, and static board geometry.
  - Files: `src/engine/types.ts`, `src/engine/rng.ts`, `src/engine/resources.ts`, `src/engine/topology.ts`, `tests/topology.test.ts`, `tests/resources.test.ts` (keep small); delete `tests/smoke.test.ts`
  - Scenarios: none
  - Done when: `npm test` and `npm run typecheck` pass, and the topology tests confirm 19/54/72 and symmetric adjacency.
- [x] M3: Board generation
  - Goal: deterministic seeded board with correct terrain/number counts and no adjacent 6/8.
  - Files: `src/engine/board.ts`, `tests/board.test.ts`
  - Scenarios: 1, 2
  - Done when: `npm test` and `npm run typecheck` pass, and Scenarios 1–2 pass.
- [x] M4: Game creation, placement rules, setup phase
  - Goal: `createGame`, the `applyAction` dispatcher with phase guard (clone-once, mutate-draft convention from Section 2), placement legality queries including `buildError`, and the full snake-order setup with second-settlement resources and piece decrements. Add the first test helpers: `newGame`, `act`, `runSetup`.
  - Files: `src/engine/game.ts`, `src/engine/placement.ts`, `src/engine/setupPhase.ts`, `tests/helpers.ts`, `tests/setup.test.ts`
  - Scenarios: 3, 4, 5
  - Done when: `npm test` and `npm run typecheck` pass, and after setup the phase is `roll` with player 1 current and each player has 3 settlements and 13 roads left.
- [x] M5: Rolling, production, robber
  - Goal: roll (with forced rolls), production with robber and bank shortage, discard, move robber, steal, end turn, plus the debug actions in `game.ts`. Add helpers `giveCards`, `forceRoll`, `toMainPhase`.
  - Files: `src/engine/production.ts`, `src/engine/turn.ts`, `src/engine/game.ts` (wire up), `tests/helpers.ts`, `tests/production.test.ts`, `tests/robber.test.ts`
  - Scenarios: 6, 8, 9, 10
  - Done when: `npm test` and `npm run typecheck` pass, Scenarios 6, 8, 9, 10 and the settlement-only shortage tests pass, and a 7 runs discard → move robber → steal → main correctly.
- [x] M6: Building, bank trade, victory
  - Goal: build road/settlement/city with costs and piece limits, 4:1 bank trade, victory points and win check (including at turn start). Add the production scenarios that need cities or extra settlements.
  - Files: `src/engine/building.ts`, `src/engine/scoring.ts`, `tests/building.test.ts`, `tests/production.test.ts` (Scenarios 7, 11), `tests/victory.test.ts`, `tests/conservation.test.ts`
  - Scenarios: 7, 11, 12, 13, 18, 19, 20
  - Done when: `npm test` and `npm run typecheck` pass, Scenarios 7, 11, 12, 13, 18, 19, 20 pass, and `gameOver` rejects every further action.
- [x] M7: Longest Road
  - Goal: trail-length DFS with opponent blocking, holder update rules, and VP integration. Call `updateLongestRoad` after every road/settlement placement, setup included.
  - Files: `src/engine/longestRoad.ts`, `src/engine/building.ts`, `src/engine/setupPhase.ts` (wire up), `tests/longestRoad.test.ts`, `tests/victory.test.ts` (other-turn win)
  - Scenarios: 14, 15, 16, 17
  - Done when: `npm test` and `npm run typecheck` pass, and all 20 scenario tests pass.
- [x] M8: UI shell and board
  - Goal: new-game form, app state/dispatch loop, SVG board with legal-spot highlighting and clicks for setup placements.
  - Files: `src/main.ts`, `src/ui/app.ts`, `src/ui/boardView.ts`, `src/ui/screens.ts` (new-game form), `src/style.css`
  - Scenarios: none (manual: 3, 5)
  - Done when: `npm test` and `npm run typecheck` pass, `npm run build` succeeds, and the UI never computes legality itself (only `legal*` queries).
- [x] M9: Turn UI: panels, action bar, log, prompts, winner screen
  - Goal: player panels, phase/dice display, roll/build/trade/end-turn controls, discard and steal prompts, robber placement, error messages, event log, winner screen.
  - Files: `src/ui/playerPanels.ts`, `src/ui/actionBar.ts`, `src/ui/logView.ts`, `src/ui/screens.ts` (winner), `src/ui/app.ts`
  - Scenarios: none (manual: 9, 10, 13, 19, 20)
  - Done when: `npm test` and `npm run typecheck` pass, `npm run build` succeeds, every engine error reaching `dispatch` is shown to the player, and unaffordable build buttons show the `buildError` message.
- [x] M10: Debug panel and final pass
  - Goal: debug toggle with seed/new game, force roll, give resource, and show IDs on the board. Audit that all log event types from the spec appear.
  - Files: `src/ui/debugPanel.ts`, `src/ui/boardView.ts` (ID labels), `src/ui/app.ts`
  - Scenarios: none (enables manual verification of all 20)
  - Done when: `npm test` and `npm run typecheck` pass, `npm run build` succeeds, and the debug panel exposes all four spec features.

## 7. Decisions

1. **Seed** is a non-negative integer (uint32). The UI shows it and accepts typed integers. With no input, the seed is `Date.now() % 2**32`.
2. **Board generation:** shuffle terrains over the 19 hexes, then shuffle numbers onto the non-desert hexes, and reshuffle the numbers (with the same RNG stream) until there is no adjacent 6/8. Same seed, same board.
3. **Topology is fixed**, so corner/edge IDs mean the same thing in every game. Corner IDs come from dedupe by rounded position, in hex order and then corner order.
4. **Dice and steals** use `rngState`, seeded from the board seed, so a whole game is reproducible.
5. **Forced roll** sets the total (2–12). It is shown as two dice: `die1 = min(6, total - 1)`, `die2 = total - die1`. It applies to the next roll only.
6. **Debug give resource** moves cards from the bank and fails if the bank has too few. This keeps the 19-per-resource invariant, and it is how tests create bank shortages.
7. **Discard order** is turn order, starting with the roller. A discard must total exactly the required amount and use only cards the player holds.
8. **Steal:** with exactly one candidate the steal is automatic. Candidates with 0 cards are still valid targets, and nothing is stolen from them. The stolen card is chosen uniformly from the victim's individual cards.
9. **Bank trade:** `give !== get`. The bank must hold at least 1 of `get`.
10. **Longest Road holder below 5:** if a break drops the holder below 5, they lose the card even if still longest, **including when they are tied for longest below 5** (e.g. holder and another player both at 4). It then goes to a unique ≥5 leader, or is set aside. This conflicts with the spec's literal "If the holder is still tied for longest after a break, they keep the card", which has no length condition. We resolve it in favour of the ≥5 threshold because the set-aside rule ("nobody has at least 5") and the take rule both require 5, and a card held at length 4 would be one nobody could have earned. Tested in `longestRoad.test.ts` (holder tied at 4 after a break: card set aside).
11. **Win on another player's turn:** checked when `endTurn` hands the turn to that player, before they roll. Victory is otherwise checked only for the current player, after each of their actions.
12. **Longest Road is re-evaluated during setup** too, as the spec says "every road or settlement placement". It cannot reach 5 there, so this has no visible effect.
13. **Setup road** must touch the settlement just placed, not just any of the player's settlements.
14. **Player names/colors:** defaults are "Player 1..N" with fixed colors (red, blue, white/orange, green). Names are editable on the new-game form.
15. **Errors** are plain short strings from the engine, shown verbatim by the UI. Log entries are plain strings generated by the engine.
16. **No production on a 7.** After a 7, the phase sequence is `discard` (if anyone must discard) → `moveRobber` → `steal` (only if 2+ candidates) → `main`.
17. **Build highlighting respects cost and supply.** In `main`, the `legal*` build queries return `[]` when the player can't pay or has no pieces of that kind left, so the UI never highlights a spot the click would reject. The reason comes from `buildError(state, kind)` and is shown on the build-mode button.
18. **Setup uses the supply.** Setup settlements and roads come from the player's 5/15 supply at no resource cost.

## 8. Revision notes

1. [major] Scenarios 7 and 11 moved from M5 to M6 (after `buildCity` / `buildSettlement`). M5 Scenarios are now 6, 8, 9, 10; M6 are 7, 11, 12, 13, 18, 19, 20; both "Done when" lines name their scenarios. M6 Files now include `tests/production.test.ts`. Section 5's intro says where Scenarios 7 and 11 are written and sketches the Scenario 11 setup. M5 still exercises the shortage rule with settlement-only tests (new bullet in Section 5).
2. [minor] Setup piece use is stated in the Snake order and Piece limits walk-throughs, in the `setupPhase.ts` row, in M4's goal and "Done when" (3 settlements / 13 roads left), as a `setup.test.ts` check, and as Decision 18.
3. [minor] `tests/helpers.ts` row split: M4 adds `newGame`, `act`, `runSetup`; M5 adds `giveCards`, `forceRoll`, `toMainPhase`. M4 and M5 Goal/Files lines updated.
4. [minor] Decision 10 now names the conflict with "If the holder is still tied ... they keep the card" and covers the tied-at-4 case (card set aside), with a matching `longestRoad.test.ts` line. The award walk-through points to Decision 10.
5. [minor] One convention stated under the types: handlers and in-handler helpers mutate the cloned draft in place; handlers return `string | null`, helpers return `void`; queries are pure. Signatures in `setupPhase.ts`, `turn.ts`, `building.ts`, `longestRoad.ts`, `scoring.ts` updated (`checkWinner(draft, player): void`).
6. [minor] Added `buildError(state, kind): string | null` to `placement.ts`. The build `legal*` queries return `[]` when it is non-null. The `actionBar.ts` row and M9 "Done when" say build buttons show that message. Added Decision 17 and a `building.test.ts` line.

Reviewer notes also applied: Scenario 17 test covers both outcomes; tests use `totalCards` deltas; M2 deletes `tests/smoke.test.ts` and keeps `resources.test.ts` small.

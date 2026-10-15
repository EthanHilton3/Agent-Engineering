# Catan Lite — Specification

A browser-based, hot-seat version of *Settlers of Catan* for 2–4 human players on one computer. "Lite" keeps the core board, building, robber, and longest-road rules, and cuts development cards, ports, and player-to-player trading.

## Tech stack

- TypeScript, runs in the browser, built with Vite.
- Any UI framework (or none) is acceptable.
- No backend, no network play, no persistence.
- `npm install && npm run dev` starts the game.
- `npm test` runs an automated test suite covering the game rules.

## Scope

| In scope | Out of scope |
|---|---|
| Standard 19-hex board, randomly generated from a seed | Ports / harbors |
| 2–4 human players, hot-seat | AI / bot players |
| Roads, settlements, cities | Development cards, Largest Army |
| Snake-order setup phase | Player-to-player trading |
| Dice production, bank supply limits | Expansions, variable board sizes |
| Rolling a 7: discard, robber, steal | Save / load, undo |
| 4:1 trading with the bank | Animations, sound |
| Longest Road | Online multiplayer |
| Win at 10 victory points | |

## Board

- 19 land hexes in the standard 3-4-5-4-3 layout.
- Terrain: 4 forest (wood), 4 pasture (sheep), 4 fields (wheat), 3 hills (brick), 3 mountains (ore), 1 desert.
- Number tokens: 2, 3, 3, 4, 4, 5, 5, 6, 6, 8, 8, 9, 9, 10, 10, 11, 11, 12 — one per non-desert hex. The desert has no number.
- A 6 or 8 must never be on a hex adjacent to another 6 or 8.
- The robber starts on the desert.
- The board is generated from a seed. The same seed always produces the same board. The seed is shown in the UI and can be entered to start a new game.

Settlements and cities sit on hex **corners** (intersections). Roads sit on hex **edges**. A corner is shared by up to 3 hexes and an edge by up to 2. A building on a shared corner belongs to all hexes touching that corner.

## Pieces and costs

Each player has a supply of 15 roads, 5 settlements, and 4 cities. A player cannot build a piece they have none left of.

| Build | Cost | Victory points |
|---|---|---|
| Road | 1 brick, 1 wood | 0 |
| Settlement | 1 brick, 1 wood, 1 wheat, 1 sheep | 1 |
| City (upgrades one of your settlements) | 3 ore, 2 wheat | 2 (replaces the settlement's 1) |

Upgrading to a city returns the settlement piece to the player's supply.

The bank holds 19 cards of each resource. Spent and discarded cards return to the bank.

## Placement rules

**Distance rule:** a settlement may never be placed on a corner that is adjacent (one edge away) to any corner holding a settlement or city, owned by anyone. This applies in setup and in normal play.

**Settlement (normal play):** must be on an empty corner, obey the distance rule, and touch at least one of the player's own roads.

**Road:** must be on an empty edge and connect to the player's own road, settlement, or city. A road cannot connect *through* a corner occupied by an opponent's settlement or city — i.e., if the only link between the new road and the player's network is a corner holding an opponent's building, the placement is illegal.

**City:** must replace one of the player's own settlements.

## Setup phase

1. Turn order is player 1 → N.
2. Round one, in order 1 → N: each player places one settlement and then one road touching that settlement.
3. Round two, in reverse order N → 1: each player places a second settlement and one road touching it.
4. Setup settlements obey the distance rule but need no road connection.
5. After placing their **second** settlement, a player receives one resource for each non-desert hex touching it. The first settlement gives nothing.
6. Player 1 then takes the first normal turn.

## Normal turn

A turn has three phases in this order. The UI must not allow actions out of phase (e.g., building before rolling).

### 1. Roll

Roll two six-sided dice.

**Roll of 2–6 or 8–12 — production:** each hex with that number produces resources, *except* the hex the robber is on. Each settlement touching it earns 1 of that hex's resource, each city earns 2.

**Bank shortage:** if the bank does not have enough of a resource to pay everyone owed it this roll, nobody receives that resource — unless only one player is owed it, in which case that player receives whatever the bank has left. Other resources from the same roll are still paid normally.

**Roll of 7 — robber:**

1. Every player (including the roller) holding more than 7 resource cards discards half, rounded down. Each player chooses which cards to discard.
2. The roller moves the robber to a different hex. The desert is allowed.
3. The roller steals one random resource card from an opponent who has a settlement or city touching the new robber hex. If more than one opponent qualifies, the roller chooses which. If the chosen opponent has no cards, nothing is stolen. If no opponent qualifies, nothing is stolen.
4. No production happens on a 7.

### 2. Trade and build

In any order and any number of times, as long as the player can pay:

- Trade 4 identical resources to the bank for 1 resource of their choice (if the bank has it).
- Build roads, settlements, and cities.

### 3. End turn

Play passes to the next player in order.

## Longest Road

- A player's road length is the longest continuous path of their roads that uses each road segment at most once. Branches do not add together — only the single longest path counts. A path may pass through the same corner more than once (loops count).
- An opponent's settlement or city on a corner breaks the path at that corner.
- The first player to reach a length of at least 5 takes the Longest Road card, worth 2 victory points.
- Another player takes the card only by **exceeding** the current holder's length. Ties do not take it.
- If the holder's road is broken (by an opponent's building) and they are no longer the longest:
  - if exactly one player is now the longest (with at least 5), that player takes the card;
  - if several players tie for longest, or nobody has at least 5, the card is set aside and no one holds it until someone uniquely has the longest road of at least 5.
- If the holder is still tied for longest after a break, they keep the card.
- Longest Road is re-evaluated after every road or settlement placement.

## Victory

- A player wins the moment they have 10 or more victory points **during their own turn**. If a player reaches 10 on someone else's turn, they win at the point in their next turn when they still have 10.
- Victory points: settlement 1, city 2, Longest Road 2.
- When a player wins, the game shows a winner screen with final scores and stops accepting actions.

## User interface

- The board is rendered with hexes showing terrain (by color or icon), number tokens (6 and 8 visually emphasized), and the robber.
- When placing a piece, only **legal** corners or edges are highlighted and clickable.
- A panel for each player shows: name and color, victory points, resource card count, pieces remaining, and Longest Road length. The current player's panel also shows their individual resource cards.
- The current phase and current player are always clearly displayed.
- Rolled dice values are shown.
- An event log shows rolls, production, builds, trades, discards, robber moves, steals, Longest Road changes, and the win.
- Illegal actions are prevented with a short explanation, not silently ignored.
- On a 7, each player who must discard is prompted in turn to choose their cards.

## Debug mode

A toggleable debug panel, so rules can be verified by hand:

- Set the seed and start a new game.
- Force the value of the next dice roll.
- Give any resource to any player.
- Show the coordinates or IDs of corners and edges on the board.

## Acceptance scenarios

Each of these must be verifiable in the running app (using debug mode where needed) and should be covered by automated tests.

1. **Deterministic board:** starting two games with the same seed produces identical terrain and number layouts.
2. **No adjacent red numbers:** across 100 generated boards, no 6 or 8 is adjacent to another 6 or 8.
3. **Distance rule in setup:** in setup, a corner one edge away from an existing settlement is not offered as legal.
4. **Setup resources:** only the second setup settlement grants resources, one per adjacent non-desert hex.
5. **Snake order:** with 3 players, setup placement order is 1, 2, 3, 3, 2, 1.
6. **Shared-corner production:** a settlement on a corner touching three hexes produces from each of them when their numbers are rolled.
7. **City production:** a city produces 2 resources per roll of an adjacent hex.
8. **Robber blocks production:** a hex with the robber on it produces nothing when its number is rolled.
9. **Discard on 7:** a player holding 9 cards discards 4; a player holding 7 cards discards nothing.
10. **Steal targeting:** after a 7, only opponents with a building touching the robber hex can be robbed; the roller cannot rob themselves.
11. **Bank shortage:** if the bank has 2 wheat left and two players are each owed 2 wheat, neither receives wheat. If only one player is owed 3 wheat, they receive 2.
12. **Road through opponent:** a road cannot extend through a corner occupied by an opponent's settlement.
13. **Phase enforcement:** building or trading before rolling is not possible.
14. **Longest Road threshold:** a player with 4 connected roads has no Longest Road; building the 5th grants it (+2 VP).
15. **Longest Road tie:** a second player reaching the same length as the holder does not take the card; exceeding it does.
16. **Longest Road branches:** a Y-shaped network of 3 + 3 + 1 roads has a length of 6, not 7.
17. **Broken road:** an opponent's settlement placed in the middle of a 6-road chain splits it, and Longest Road is reassigned or set aside per the rules.
18. **Piece limits:** a player who has placed all 5 settlements cannot build another until one is upgraded to a city.
19. **Bank trade:** trading 4 wood yields 1 chosen resource; trading 3 wood is not allowed.
20. **Win condition:** reaching 10 VP on your own turn ends the game with a winner screen.

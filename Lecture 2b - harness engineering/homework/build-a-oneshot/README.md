# Catan Lite

Hot-seat Settlers of Catan for 2–4 players in the browser. See [spec.md](spec.md) for the rules.

```sh
npm install
npm run dev     # start the game (Vite)
npm test        # rules test suite (Vitest)
npm run build   # typecheck + production build
```

## Layout

| Path | What |
|---|---|
| `src/game/geometry.ts` | Fixed board topology: 19 hexes, 54 corners, 72 edges and their adjacency |
| `src/game/board.ts` | Seeded board generation (terrain, numbers, no adjacent 6/8) |
| `src/game/longestRoad.ts` | Longest-trail search and Longest Road card assignment |
| `src/game/game.ts` | The rules engine: phases, setup, production, robber, building, trading, victory |
| `src/ui/` | Vanilla TypeScript + SVG UI that renders the engine state |
| `tests/` | One test file per rules area; every acceptance scenario is tagged `// Scenario N` |

The engine has no DOM dependency. Every action returns `{ ok: true }` or `{ ok: false, error }`, and a failed action leaves the state unchanged. The UI shows the error text to the player.

## Debug mode

Click **Show debug** in the header to:

- start a new game from a chosen seed (same players),
- force the next roll,
- give any player resources (taken from the bank, so you can also use it to drain the bank to test shortages),
- label every hex (`H#`), corner (`c#`) and edge (`e#`) on the board.

## Rule interpretations

- **Longest Road below 5:** if a break leaves the holder still tied for longest but under 5, the card is set aside. The spec says nobody holds the card without at least 5.
- **Win on another player's turn:** this is checked when your turn starts, before you roll.
- **Robber with one eligible victim:** the card is stolen automatically. When there are two or more, the roller picks one.
- **Dice and steals** use a PRNG seeded from the game seed, so a game replays the same way.

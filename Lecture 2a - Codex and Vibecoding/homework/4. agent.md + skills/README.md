# Kirby: Dream Meadows

A pixel-art Kirby platformer. All art and sound is made in code, with no build step and no dependencies.

## Play
Double-click `index.html` to open it in Chrome, Edge or Firefox.

| Key | Action |
|---|---|
| ← → or A D | Move |
| Space | Jump. Tap again in the air to fly (as often as you like). |
| Enter | Hold to inhale. Press again to spit what you swallowed as a star. |
| P / Esc | Pause |
| M | Mute |
| R | Restart from the beginning (asks first while playing) |

With a full mouth, Kirby can't fly, so spit first. Only spat stars hurt the boss: inhale its apples and spit them back.

## Tests
Requires Node 22 or newer.

```
node --test            # unit tests + automated playthrough
node tests/smoke.mjs   # headless Chrome smoke test (screenshots in .tmp/screenshots)
```

The smoke test finds Chrome or Edge automatically. Set `CHROME_PATH` if yours is somewhere unusual.

## Layout
- `js/logic/`: pure game logic (constants, physics, world, enemies, player, boss, game state). No DOM.
- `js/level.js`: level data. Add new levels here.
- `js/sprites.js`, `js/sprites-world.js`: pixel art drawn in code.
- `js/render.js`, `js/hud.js`: drawing. `js/audio.js`: Web Audio sound effects and music.
- `js/input.js`: keyboard. `js/main.js`: fixed 60 Hz loop.
- `tests/`: `node:test` suites, the playthrough bot (`bot.js`) and the smoke test.

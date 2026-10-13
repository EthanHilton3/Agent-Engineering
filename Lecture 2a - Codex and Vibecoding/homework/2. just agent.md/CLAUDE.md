# Kirby platformer

Browser pixel-art platformer.

## Constraints
- Must run by double-clicking index.html (file://). No build step, no npm dependencies, no external assets or libraries.
- Use classic `<script src>` tags, not ES modules (browsers block modules on file://).
- Fixed-timestep game loop (60 updates/sec), independent of render rate.
- Bind only the keys the request lists for movement, jump/fly and inhale/spit. Do not add alternative keys for those actions. Extra utility keys (pause, mute, restart) are fine.

## Structure
- Keep game logic separate from drawing and input. Logic files must not touch the DOM or canvas.
- Split into small files, each under ~400 lines: `js/logic/` (physics, collision, entities, inhale/spit, game state), `js/level.js`, `js/sprites.js`, `js/render.js`, `js/input.js`, `js/main.js`.
- Put tunable numbers (gravity, jump speed, fly limit, inhale range) in one named constants block. No magic numbers elsewhere.

## Testing (tests are part of the deliverable and stay in the project)
- Logic files end with `if (typeof module !== 'undefined') module.exports = { ... };` so Node can load them.
- Unit tests in `tests/` using `node:test`, run with `node --test`. Cover: collision (fast movement must not tunnel), jump and fly limits, which enemies fall inside the inhale cone, swallow and spit state changes, lives, score, win, game over and restart.
- One automated playthrough test: drive the game with simulated key events only (no teleporting, no setting state directly) and show that the level can be finished, including crossing every gap.
- Browser smoke test in `tests/smoke.mjs`: headless Chrome driven over the DevTools protocol with Node's built-in WebSocket (no dependencies). It fails on any console error. It uses a throwaway profile and saves screenshots in `.tmp/`, which is git-ignored.
- Always stop the headless Chrome process before finishing, so temp folders can be deleted on Windows.
- Run all tests before saying you are done. Fix failures instead of deleting tests.

## Definition of done
- Re-read the original request and check every requirement against the code. List anything unmet or approximated.
- Extras beyond the request are allowed only if cheap. List every extra you added in the final message.
- Say plainly what you could not verify (for example sound or how movement feels in real play).
- Final message: how to run it, how to run the tests, and known problems.

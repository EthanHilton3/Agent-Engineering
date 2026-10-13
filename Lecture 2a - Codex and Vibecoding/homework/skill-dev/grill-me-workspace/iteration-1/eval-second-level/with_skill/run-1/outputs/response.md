Before I build anything, I read how the game is put together, so my questions are about decisions and not things the code already tells me.

What I found:
- There is exactly one level. `js/level.js` stitches 11 hand-written sections into `DEFAULT_ROWS`, and `KB.Level.load()` always returns that level. `KB.Game.create()` takes it, and `win()` in `game.js` ends the whole game: the mode goes to `'won'` and the next confirm press calls `restart()`, which rebuilds level 1. Nothing in the code knows about "levels" yet.
- Everything that makes level 1 look and feel the way it does is global, not per level. That includes the sky, the cloud and hill background, the grass-and-flowers ground, the bushes and the tutorial signs. It is all drawn in `render.js` and `sprites.js`. A second level that "feels different" in look would need that to become per-level.
- Gameplay has four enemy types (walker, flyer, hopper, and the un-inhalable gordo), four tile types (ground, brick, star block, cloud) and the inhale/fly/spit moves. Level 1 uses them all, and it also teaches them with signs.
- `CLAUDE.md` adds rules that any second level must follow. The playthrough test has to finish the level using only simulated key presses, including crossing every gap. Tunable numbers go in `constants.js`. The game must still run from `file://` with no build step.

I have about 7 questions. I'll ask them one at a time, since later ones depend on your answers. No code or files will change until you approve a short `DESIGN.md`.

**Q1 of ~7: When you say "different from the first one", which kind of different do you mean?**
*Why it matters:* this decides how big the job is and which files change. A new look is mostly art and palette work in `render.js` and `sprites.js`. A new rule for the player is new logic in `physics.js`, `player.js` or `entities.js`, plus tests. A new shape of level is mostly level data and the camera. Every other question depends on this answer.
*My recommendation:* change the look and add one new gameplay twist. A reskin on its own would feel like the same level in different colors. Level 1 is a sunny, left-to-right meadow, so level 2 could be a dark cave or night level with one new thing to deal with, such as a new enemy or a new tile type. One twist is cheap, and it is enough to make someone say "this one plays differently".
*Alternatives:*
- Look and layout only: a new theme with a new route, but the same moves, enemies and tiles (cheapest, lowest risk).
- Structural change: for example a vertical climb or an auto-scrolling level (most different, but it touches the camera and the level format, and the playthrough bot would need work).
- Something else you have in mind. If there is a specific game moment you want the player to feel, tell me.

*(I'm stopping here for your answer. I'll start with the project's existing level and test conventions once the design is agreed.)*

FILES READ: SKILL.md (grill-me), CLAUDE.md, js/level.js, js/logic/constants.js, js/logic/game.js, js/render.js, js/logic/entities.js, js/main.js, tests/playthrough.test.js, tests/bot.js (first 60 lines)

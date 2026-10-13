Before I write any code, I want to pin down a few decisions. A boss fight is mostly design choices, and I'd rather ask now than build the wrong one. I'll ask one question at a time, then write the answers into a short `DESIGN.md` for you to approve.

What I found in the project:
- The level is 11 sections joined together in `js/level.js`. It ends with a staircase up to a single warp star (`E`). Touching it calls `win()` in `game.js`, which awards 1000 points plus 500 per life left.
- There are only four enemy types (walker, flyer, hopper, gordo). They share one update loop in `entities.js`, and every enemy dies in one hit: a star, a puff or a bump. Nothing in the game has hit points yet.
- `CLAUDE.md` requires every tunable number to live in `constants.js`. It also requires the playthrough test to finish the level using key events only, so that test will have to beat the boss too.

**Q1 of ~8: Should the boss replace the warp star as the goal of the level, or guard it?**
*Why it matters:* this decides how the level ends, and the other questions depend on it. Today the goal is just "touch the star" (`g.goal` overlap in `stepPlaying`). If beating the boss becomes the way to win, `win()`, the level layout after the stairs, the tutorial sign `6` ("TOUCH IT TO WIN") and the playthrough test all change.
*My recommendation:* add a boss arena after the stairs and have the warp star appear only when the boss is defeated. That makes the boss the real finale, and the existing win flow, score bonus and `E` goal can stay as they are. The star would be spawned or revealed on the boss's death instead of existing from the start.
*Alternatives:* (a) the boss guards the star but is optional, so you can run past it. This is the cheapest option but undercuts the fight. (b) The boss fight replaces the star entirely and a "boss defeated" event triggers `win()`. This is simpler code, but you lose the star as a visual payoff.

Which one do you want?

FILES READ: grill-me/SKILL.md, CLAUDE.md, js/logic/constants.js, js/logic/game.js, js/logic/entities.js, js/level.js, js/logic/inhale.js, tests/playthrough.test.js

I haven't changed any code yet. I read the game first, and a few design choices change what I'd build, so I'd like your answers before I start.

## What the code looks like now

- Swallowing sets `p.mode = 'full'` and `p.held = { kinds: [...] }` (`js/logic/inhale.js`).
- In `full` mode the Enter key can only spit a star (`player.js`, `handleAction`).
- The game already remembers which enemy kinds Kirby swallowed, and that data is never used. A copy ability can use it.
- There are three inhalable enemy kinds: `walker`, `flyer` and `hopper`. Gordo can't be inhaled. Star blocks can be inhaled, but they aren't enemies.
- `CLAUDE.md` says to bind only the keys the request lists and not to add alternative keys for those actions.

## Questions (each has my default)

1. **How does Kirby turn a mouthful into a power?** In the real games he presses Down to swallow, and Enter/spit gives you the star. Enter is already "spit", so we need a second action.
   - Default: add the **Down arrow** as "swallow", plus a key to drop the power. I'd treat it as a new action rather than an alternative key for an existing one, but that is a judgment call, so please confirm. If you'd rather not add keys, the fallback is: holding Enter spits, and a quick tap swallows.
   - How does he lose a power: a key, getting hurt (as in the real games), or both?
2. **Which enemy gives which power?** Three enemy kinds means three powers at most. My proposal:
   - Walker gives **Fire**: Enter breathes a short flame that defeats enemies and burns brick blocks.
   - Flyer gives **Cutter**: Enter throws a boomerang blade that returns to him.
   - Hopper gives **Spark**: Enter makes a short-range electric burst in all directions.
   - Do you want other powers, or new enemy types to go with them? New enemies mean new sprites and level edits. I'd keep to three powers for now.
3. **What does Enter do while Kirby has a power?** In the real games, the attack key uses the power and inhaling is unavailable until you drop it. I'd copy that. It has a side effect: with a power he can't inhale star blocks. Is that fine, or should star blocks be inhalable even with a power?
4. **Should abilities affect the level?** Right now they would only be a different way to kill enemies. If you want them to matter, I'd add a few things to the level, such as brick walls that only Fire clears or a gap that Cutter reaches across. Otherwise abilities are purely cosmetic, and the level and its tests stay as they are. Which do you want?
5. **What does the player see?** The default is a color-tinted Kirby sprite per power (red, grey, yellow) and the power's name in the HUD, which fits the existing `sprites.js` and `hud.js`. Do you want a hat or a hand-drawn sprite per power instead? That is more work.
6. **Does a power carry across death and checkpoints?** I'd say no: respawn clears it, and `killPlayer` already resets `held`. Say if you want it to persist.
7. **Multiple enemies in one mouthful?** `held.kinds` can hold several. I'd use the first enemy kind in the list. Enemy kinds that give no power would still be spat as a star.

## What I'd do first once you answer

1. Add the new numbers to `js/logic/constants.js` (flame range, cutter speed, spark radius and so on), because `CLAUDE.md` forbids magic numbers.
2. Add a `p.ability` field to the player, a `KB.Abilities` table that maps enemy kind to power, and swallow and drop functions in `js/logic/inhale.js`.
3. Put the power behavior in a new `js/logic/abilities.js` that stays under 400 lines and has no DOM or canvas access. It would create the power's projectile and hit-checking, reusing the existing projectile and collision code in `entities.js`.
4. Add the swallow key to `js/input.js`, tinted sprites to `js/sprites.js` and `js/render.js`, and the power name to `js/hud.js`.
5. Write new `node:test` tests in `tests/abilities.test.js`. They would cover which enemy gives which power, losing a power on hit or death, fire burning bricks, and a power not breaking the normal inhale and spit.
6. Extend the playthrough bot to take a power and use it. It would only press keys, with no teleporting or setting state directly. Then I'd run all tests, including the existing ones, and the browser smoke test.

## Risks

- I can't judge from tests whether the powers feel good, or whether the sounds and tints look right. You'd need to play it.
- The existing playthrough test has to keep passing without the bot using any power. That is why the power would be optional in the level, unless you pick the level-changes option in question 4.

If you just say "go with your defaults", I'll build exactly what's described above.

FILES READ: CLAUDE.md, js/logic/inhale.js, js/logic/player.js, js/logic/entities.js, js/logic/constants.js, js/logic/game.js, js/input.js, js/level.js, tests/bot.js, js/render.js (grep only), js/sprites.js (grep only), js/hud.js (grep only), js/main.js (grep only)

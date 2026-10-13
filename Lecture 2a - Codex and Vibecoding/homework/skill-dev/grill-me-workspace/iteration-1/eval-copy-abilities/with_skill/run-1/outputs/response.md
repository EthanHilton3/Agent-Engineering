Before I touch any code, I read the project so I only ask what the code can't answer. Here is what I found:

- **Inhale today:** Hold Enter to inhale. Anything swallowed puts Kirby in `'full'` mode (`inhale.js`), and the next Enter press spits it out as a star (`Inhale.spit`). The game never records what he swallowed in a way that matters: `p.held = { kinds, count }` stores the enemy kinds, but nothing reads them.
- **Enemies:** There are three inhalable kinds (walker, flyer, hopper). Gordo is flagged `inhalable: false`. All of them are plain data in `entities.js`, with no per-kind attacks.
- **Controls:** `input.js` binds only arrows/AD, Space and Enter, and `CLAUDE.md` says not to add keys for movement, jump/fly or inhale/spit beyond the ones requested. Enter is already overloaded: it inhales, spits when full, and exhales a puff when flying. A power needs to fit into that, or I need your permission for one new key.
- **Constraints:** Every number goes in `constants.js`. Logic stays free of the DOM. Tests are required (`inhale.test.js` and `player.test.js` cover swallow and spit today). The automated playthrough test uses simulated keys only.

I expect about 8 questions. Here is the first, since the others depend on it.

**Q1 of ~8: After Kirby swallows an enemy, how does he turn it into a power and use it, given that Enter is the only action key?**

*Why it matters:* This sets the control scheme, and every other decision builds on it. Today the mouthful state exists only to be spat back out as a star. Real Kirby gets his power by pressing Down to swallow. Down isn't bound here, and `CLAUDE.md` forbids adding keys for inhale/spit without your say-so.

*My recommendation:* Swallowing a power-giving enemy gives the power immediately, and the spit-a-star step is skipped for those enemies. Enter then uses the power. A second key (say, `S` or `ArrowDown`) drops it. This is the simplest option that fits one action key. It means giving up spit-a-star for those enemies, so keep it for any enemy that has no power.

*Alternatives:*
- **Keep the mouthful, add a swallow key.** This is closest to the real games, and you choose between spitting the star and swallowing it for the power. It needs one new key (Down). It is the most faithful and costs one new key plus a new state.
- **Hold-to-choose on the existing Enter key.** Pressing Enter again spits; holding it swallows. It adds no keys, but it is fiddly and easy to get wrong.

Which one do you want? Or if you'd rather I just pick, say "you decide" and I'll take my recommendation. Once we've settled Q1, the next questions are:

- which enemy gives which power (the four enemy types are walker, flyer, hopper and Gordo);
- how a power is dropped or lost when Kirby gets hurt;
- how a power is shown in the HUD and the sprites;
- how we'll check it works.

FILES READ: SKILL.md (grill-me), CLAUDE.md, js/logic/constants.js, js/logic/inhale.js, js/logic/entities.js, js/logic/player.js, js/input.js, js/logic/game.js, js/level.js

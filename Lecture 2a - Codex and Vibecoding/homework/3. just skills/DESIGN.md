# Kirby Pixel Platformer

## Goal
A polished, retro pixel-art Kirby platformer that runs by opening `index.html` directly from disk. One side-scrolling level built around running, flying, inhaling, spitting and a Fire copy ability, ending in a tree-boss fight and a warp star.

## Decisions
| Decision | Choice | Why |
|---|---|---|
| Flight | Unlimited flaps. Each flap gives weak lift, rise speed is capped, and Kirby sinks slowly between flaps. He can't inhale while flying; Enter exhales an air puff (weak attack) and ends the flight. | Faithful to Kirby. The challenge comes from flyers guarding gaps and low ceilings, not a stamina meter. |
| Damage and lives | 6 health pips per life. Enemy contact costs 1 pip with knockback and about 1.5 s of flashing invincibility. Pits cost a whole life. 3 lives to start. Food pickups heal. | Forgiving enough to get close and inhale; pits stay dangerous. |
| Enemies | **Walker** (patrols, turns at walls and ledges). **Flyer** (sine wave, occasional swoop). **Shooter** (stationary, lobs slow projectiles that Kirby can inhale). **Spiky** (Gordo-style, can't be inhaled or hurt). **Fire creature** (walks, pauses, puffs a short flame). | Each enemy has a distinct behavior and a distinct answer. |
| Copy ability | Only the fire creature gives an ability: **Fire**. Swallow it (Down) to get a flame crown. Hold Enter to breathe a flame stream that hurts enemies and the boss. Shift or taking damage drops the ability as a bouncing star that can be re-inhaled. The HUD shows the ability. | The enemy matches the power it gives. One ability keeps the scope sane. |
| Inhale | Holding Enter pulls in enemies, enemy projectiles, apples and star blocks in a cone in front of Kirby. Big objects (boulders 2× Kirby's size) pull slowly with a strain pose and screen shake. Spit = a star that flies straight, defeats regular enemies and breaks on walls. A big object fires a bigger, piercing star worth more points. Down swallows (small score bonus, or Fire if it was a fire creature). | The "surprisingly strong" moment is the boulder. Star blocks make inhaling useful for exploring. |
| Boss | A Whispy-style tree in a locked arena where the camera stops. 6 HP with a boss bar. Drops inhalable apples and blows air puffs that can't be inhaled. At half HP it gets faster and drops spiky enemies. Spit = 1 damage per hit; Fire = 1 damage per second of contact. Defeat spawns the warp star, and touching it wins. | A stationary boss suits the inhale-and-spit mechanic and is readable. |
| Level | About 200 tiles, about 3–4 minutes, in 4 sections: grassland (walkers, star blocks) → cliffs and gaps (flyers, pits, low ceiling) → hill (shooters, spiky, first boulder) → fire grove (fire creatures) → boss door → arena. | Each section introduces one idea. |
| Checkpoints | Start, midpoint flag, boss door. Losing a life respawns at the last checkpoint. Game over restarts the whole level and resets the score. | The boss shouldn't require replaying everything. |
| Sound | Synthesized Web Audio effects (jump, flap, inhale, swallow, spit, hit, pop, fire, boss hit, win and lose jingles). M mutes. Audio starts on the first keypress. No music. | Big polish win at low cost. |
| Presentation | 256×224 internal canvas scaled up by an integer factor, `image-rendering: pixelated`, a fixed palette of about 24 colors. Title screen, pause (P/Esc), controls strip always shown below the canvas. Game-over and win screens show the score, and Enter restarts. | Crisp SNES-style pixels. |
| Animations | Kirby: idle (blink), run, jump, fall, fly (puffed), inhale (open mouth), full (cheeks), strain, hurt, fire. Enemies: 2-frame cycles plus a pop effect on defeat. | Meets the spec. |
| Controls | ←/→ or A/D move · Space jump/flap · Enter inhale/spit/fire/puff · Down swallow · Shift drop ability · P/Esc pause · M mute | Spec, plus the keys the new mechanics need. |
| Scoring | Points for enemies defeated (more for multiple kills with one spit and for piercing stars), star blocks, swallows, food and boss defeat, plus a bonus for lives left at the win. (default) | Gives the score meaning. |
| File layout | `index.html` plus classic (non-module) scripts in `js/`; no external libraries, images or fetches. (default) | Works over `file://`; easier to read than one huge file. |

## Out of scope
- Background music and chiptune.
- Copy abilities other than Fire.
- Multiple levels, level select, saves, high-score persistence.
- Touch or gamepad controls.
- External assets or libraries of any kind.

## How we'll know it works
- Opening `index.html` by double-clicking (`file://`) shows the title screen with no console errors.
- Manual playthrough: run, jump, fly over a gap, inhale and spit a walker into a second walker, break a star block, inhale a boulder (strain and shake), fail to inhale a spiky enemy, swallow a fire creature, then use and drop Fire.
- Take hits until a life is lost and respawn at the checkpoint; lose all lives and see game over, then restart with Enter.
- Beat the boss with apples only, and separately with Fire only. The warp star appears and touching it shows the win screen with the score.
- Pixels stay crisp at several window sizes; the controls strip is visible; M mutes.
- The game feels right: a jump reaches about 3 tiles, flight is floaty but you can steer it, and the inhale pull is visibly strong.

## Open questions
- None.

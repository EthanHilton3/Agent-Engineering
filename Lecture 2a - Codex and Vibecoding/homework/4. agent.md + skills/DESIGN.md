# Kirby platformer

## Goal
A long, hard, polished pixel-art Kirby platformer that runs by double-clicking `index.html`. It is built around unlimited flight and an inhale/spit loop, ends in a boss fight, and is structured so more levels can be added later.

## Decisions
| Decision | Choice | Why |
|---|---|---|
| Flight | Unlimited flaps, like real Kirby. **Can't fly with a full mouth** (jump only). Fly limits = level ceiling + capped rise speed per flap + full-mouth lockout. | Faithful. Carrying something becomes a choice: spit now, or give up flight. |
| Damage | 3 lives × 6 health pips. A touch costs 1 pip, with knockback and an invincibility blink. A hit makes him drop what he's holding. A pit costs a whole life. Respawn at the last checkpoint with full health. | Forgiving Kirby feel; hits read clearly. |
| Extra lives | One hidden 1-up, plus an extra life at a score milestone (default). | Keeps "hard" from becoming hopeless. |
| Enemies | **Walker** (patrols, turns at edges and walls), **Flyer** (sine bob, drifts toward the player), **Hopper** (jumps toward the player), **Spiky** (bobbing hazard, **can't be inhaled**). Original sprites in a Kirby style. | Four distinct behaviors; the spiky stops inhale from always winning. |
| Objects | **Star blocks**: can be inhaled, then spat. Some wall off the path. Point stars, one health food before the boss. | Covers the "objects" in the request. |
| Spit | A swallowed thing comes out as a star projectile that flies straight and defeats the first enemy or star block it hits. | The request asks for spitting only. |
| Copy abilities | **None for now.** The mouth-full state records *what* was swallowed, so powers can be added later alongside new levels. | User chose this (Q8): not in the request, and Down isn't an allowed key. |
| Boss | A stationary tree in a closed arena. It drops apples (can be inhaled; your ammo) and blows air puffs (hurt, can't be inhaled). **Only spits damage it**, 6 HP, with an HP bar. When defeated, the arena opens and a **warp star** appears. Touching it wins. | The climax tests the core mechanic; predictable enough for the playthrough test. |
| Level | Long and hard: about 5–7 min, about 6 stretches before the arena (meadow, cliffs, star block fort, vertical climb, windy sky, gauntlet). A checkpoint roughly every stretch plus one at the arena door. | User asked for long and hard. |
| Level format | Level stored as data (tile rows + entity list) in `js/level.js`, loaded through one function (default). | Future levels drop in without engine changes. |
| Sound | Web Audio sound effects (jump, flap, inhale loop, gulp, spit, defeat, hurt, pickup, boss hit, win, game over) **plus a short looping chiptune melody**, with different loops for the level and the boss. M mutes. Audio unlocks on the first key. | Polish; no external assets allowed. |
| Restart | Game over → **Continue** from the last checkpoint with 3 lives; score resets to 0. R = full restart (asks for confirmation while playing). P/Esc = pause. Win screen shows score, time and best score (`localStorage`). | Fair on a long level; score still means something. |
| Keys | Move: ←/→ and A/D. Jump/fly and menu confirm: Space. Inhale (hold) / spit: Enter. Utility: M, P, Esc, R. No other gameplay keys. | Request + `CLAUDE.md`. |
| Look | 256×224 internal canvas, integer-scaled, smoothing off. Limited palette of about 16 colors. Animations: idle, run, jump, fly (puffed), inhale, full-mouth, hurt (default). | Crisp retro pixels. |
| Score | Enemy 200–300, star block 50, point star 100, boss 5000, plus a time bonus on win (default). | Cheap to retune later. |

## Out of scope
- Multiple levels (planned later; the format is ready for them).
- Copy abilities (decided in Q8; may come with later levels). Up/down keys.
- Touch or gamepad controls; a level editor.

## How we'll know it works
- Unit tests (`node --test`) for:
  - collision at high speed (no tunneling)
  - jump height, the flight ceiling, and the full-mouth no-fly rule
  - which enemies fall inside the inhale cone (the spiky is never pulled in)
  - swallow and spit state changes, and spit defeating enemies and star blocks
  - pips, lives, pits and respawn at the checkpoint
  - score, 1-up, the boss taking damage only from spits
  - win, game over, Continue, and full restart
- Playthrough test that uses only simulated key events: crosses every gap, breaks the star block wall, beats the boss with spat apples, touches the warp star, and reaches the win state.
- `tests/smoke.mjs`: headless Chrome over CDP, fails on any console error, saves screenshots of the title, gameplay, inhale, the boss and win to `.tmp/`, and always kills Chrome.
- A manual playthrough by the user for feel, difficulty and audio (I can't verify these).

## Open questions
- None.

## Changes made during the build
- Checkpoints activate when Kirby passes them at any height, not only on touch. Otherwise, flying over one silently skipped it.
- The boss's puffs are spaced 40 ticks apart, so "jump the low one, stand still for the high one" is a readable rhythm.
- The palette ended up with 18 colours, not about 16.

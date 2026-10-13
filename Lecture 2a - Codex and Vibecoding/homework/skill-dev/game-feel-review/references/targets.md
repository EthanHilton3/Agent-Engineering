# Starting targets for platformer feel

These are heuristics drawn from how well-regarded 2D platformers tend to play. Treat them as a starting range. If the user wants something floaty, heavy, or realistic, their goal replaces these numbers. Express everything in tiles (a tile is the game's grid size) and seconds.

## Jumping

| Metric | Tight platformer range | Why |
|---|---|---|
| Full-hold jump apex height | 3.5 to 5 tiles (small-character games: 2.5 to 4) | Must clear typical walls and steps with margin |
| Short-tap jump apex | 40 to 60 percent of full jump | Variable jump height gives control; if tap and hold are equal, jump-cut is missing |
| Time to apex | 0.30 to 0.45 s | Under 0.25 s feels twitchy, over 0.55 s feels floaty |
| Total airtime (flat ground) | 0.55 to 0.85 s | |
| Fall gravity vs. rise gravity | Fall 1.2x to 2x rise | Snappier landings read as "tight"; equal gravity feels floaty |
| Terminal fall speed | Capped (do not allow endless acceleration) | Keeps falls readable and collisions safe |
| Horizontal jump distance at top speed | 4 to 7 tiles | Should match the widest gap you want to require, plus 1 tile margin |

## Running

| Metric | Range | Why |
|---|---|---|
| Time to 90% of top speed | 0.08 to 0.25 s | Under 0.05 s feels binary, over 0.35 s feels slippery |
| Stopping distance from top speed | 0.3 to 1.2 tiles | Over 2 tiles feels like ice |
| Air control (fraction of ground acceleration) | 0.6 to 1.0 | Lower feels stiff in air |
| Top speed | 5 to 9 tiles/s for a small hero | Faster needs a wider view to stay readable |

## Forgiveness

| Metric | Range |
|---|---|
| Coyote time (jump allowed after leaving a ledge) | 4 to 8 ticks at 60 Hz (about 0.07 to 0.13 s) |
| Jump buffer (jump pressed before landing still fires) | 4 to 8 ticks |
| Hitbox vs. sprite | Player hitbox slightly smaller than the sprite (about 1 px per side) |

## Flying, gliding, double jump

- Define what the move is for, then measure it against the level. A fly or glide should cross the widest required gap with margin but should not trivialize vertical climbs unless the game wants that.
- Each flap or boost should gain a visible, consistent amount (0.7 to 1.5 tiles).
- A limited number of flaps or a fall-slow cap keeps it a tool and not a free pass. If it is unlimited, check that levels still have meaningful hazards.
- Maximum total height from flying and the maximum glide distance should each be above the level's largest requirement by 15 to 30 percent.

## Pull, grab or attack reach

| Metric | Range |
|---|---|
| Reach | 2 to 5 tiles; a longer range makes positioning meaningless |
| Time from press to effect | Under 0.2 s for a standard attack; pull or inhale effects can ramp up over 0.3 to 0.7 s |
| Shape | The area should be visible on screen or match the animation, so the player can tell why it hit |

## Level fit

- Biggest required gap <= horizontal jump distance minus 1 tile (or the fly distance minus 1 tile if flying is required).
- Tallest required step <= jump apex minus 0.5 tile.
- Platforms spaced more than 80 percent of the max jump distance require near-perfect play; flag them as hard.

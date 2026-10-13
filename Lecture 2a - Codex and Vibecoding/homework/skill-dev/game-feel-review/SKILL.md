---
name: game-feel-review
description: Measure and tune how a 2D game plays, instead of guessing from the code. Use this whenever the user says movement or controls feel floaty, heavy, slippery, stiff, laggy or "off", asks to tune, tighten or balance jumping, running, flying, dashing or attacks, asks whether the game is fun or playable, or has just added or changed a movement or action mechanic and wants it checked. Also use it when jump height, gap widths or ranges might not fit the level. Make sure to use it even when the user only says "make it feel better", because feel can be measured with a headless simulation and numeric targets. Do not use it for crashes, rendering glitches, sprite art, or adding new features.
---

# Game feel review

Whether a game "feels good" mostly comes down to a handful of numbers: how high and how long a jump is, how fast the player gets up to speed and stops, how forgiving the controls are, and how far special moves reach. Reading a constants file tells you what the numbers are called, not what they *do*. Gravity 950 and jump speed 335 mean nothing until you know the jump peaks 3.4 tiles high in 0.35 s. So the job is to run the game's own simulation, measure what the player actually experiences, compare it to sensible targets and to the level's demands, and change one knob at a time.

You cannot feel the game yourself. Say so in your report and tell the user exactly what to try by hand.

## Process

**1. Find the knobs and a way to step the game.**
Locate where the physics numbers live (a constants file, a config object, or magic numbers in an update function; if they are scattered, say so, because tuning scattered numbers is risky). Then find how to advance the game without a browser: a pure `update(state, input)` function you can call from Node is ideal (check the existing tests for how they do it). If the logic is welded to the DOM or canvas, drive the real page in headless Chrome instead, or tell the user the structure blocks measuring.

**2. Write a measurement script and keep it.**
Put it in the project (for example `tools/feel-report.js`), so later changes can be re-measured. It runs scripted input scenarios on a small flat test level and records the player's position and velocity every tick. Cover whatever the game actually has:

- standing jump: tap vs. full hold (apex height, time to apex, total airtime, horizontal distance at full speed)
- run: time to reach 90% of top speed, and the distance needed to stop
- air control: how much sideways speed can be added mid-air
- falling: time to fall a given height, terminal speed
- special moves (fly, double jump, dash, glide): per-use gain, total height or distance reachable, how long it lasts
- attacks or pull/grab ranges: reach in pixels and tiles, time from press to effect
- forgiveness: jump still works N ticks after leaving a ledge (coyote time), a jump pressed N ticks before landing still fires (buffer)

`scripts/trajectory_stats.js` computes the common numbers (apex, time to apex, airtime, distance, time to speed) from a list of samples, so you do not have to rewrite that math. Convert everything into **tiles and seconds** before comparing, because pixels per tick are impossible to judge.

**3. Compare against targets, then against the level.**
Read `references/targets.md` for starting ranges. They are heuristics for a tight, readable platformer, not laws; the user's taste and the game's genre override them. Then check the numbers against the level the player must actually cross: the tallest step to climb, the widest gap to jump or fly over, and the longest stretch the player must survive. A jump that is "feel-perfect" but cannot clear the level's biggest gap is a bug; a move that clears every gap trivially makes the level pointless. Read gap widths and heights from the level data and flag mismatches.

**4. Change one knob at a time.**
Pick the single number most responsible for the problem, change it, and re-run the measurement script. Keep a table of before and after. Small steps (10 to 20 percent) beat big jumps, and changing two knobs at once makes it impossible to tell which one helped. Run the project's tests after each change, since tuning often breaks level beatability tests. Do not edit level layouts to compensate for a bad number unless the user agrees.

**5. Report.**
Give the user a short table: metric, before, after, target. Then list what you changed and why in a line each. Finish with what you could not measure (sound, animation timing, hit-stop, camera, how it feels in hand) and **two or three specific things to try by hand** (for example: "tap jump rapidly across the first gap and see if flying feels floaty enough").

## Principles

- Measure first. Never conclude "this feels floaty" from reading constants.
- Prefer fixing the cause: if the jump feels heavy, check fall gravity vs. rise gravity before changing jump speed.
- Keep gameplay promises: if a tutorial sign, README or test says the player can do X, a tuning change must not quietly break X.
- Stay inside the request. If you spot art, bugs or design issues, mention them in one line at the end; do not fix them here.

## If there is nothing to tune

If the numbers already sit inside the targets and the level fits, say so plainly and show the measurements. Not changing anything is a valid result.

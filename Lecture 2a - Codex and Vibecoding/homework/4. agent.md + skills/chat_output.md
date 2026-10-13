/grill-me Work only inside the current directory. Do not read or modify any files outside it.

Build a pixel-art platformer game that runs in the browser by opening index.html.

Character: a small, round, pink character named Kirby who is surprisingly strong.
He can run, jump, and fly by pressing jump repeatedly while in the air. He can
also inhale: holding the action key pulls in nearby enemies and objects in front
of him. Once he has swallowed something, pressing the action key again spits it
out as a projectile that can defeat other enemies.

Game:
- One side-scrolling level with platforms, gaps, and a clear goal at the end.
- At least two kinds of enemies with different behavior (for example one that
  walks and one that flies).
- Lives, a score, a game-over screen, a win screen, and a way to restart.
- Controls: arrow keys or A/D to move, Space to jump and fly, Enter to inhale and spit.
  Show the controls on screen.

Look and feel:
- Retro pixel-art style with crisp pixels, a limited color palette, and simple
  animations (idle, run, jump, fly, inhale).
- Draw all sprites in code, with no external image files or libraries.
- Movement should feel tight and fun: sensible gravity, a floaty-but-controllable
  fly, and a satisfying inhale.

Make it polished and fun to play.
8:09 PM
I'll start by looking at what's already in the project directory.



Bash List project files and check Node version
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && ls -la && find . -type f -not -path "./.git/*" | head -50 && cat .gitignore 2>/dev/null; node --version

OUT
total 16
drwxr-xr-x 1 Ethan 197121    0 Oct  9 19:49 ./
drwxr-xr-x 1 Ethan 197121    0 Oct  9 19:35 ../
drwxr-xr-x 1 Ethan 197121    0 Oct  9 19:49 .claude/
-rw-r--r-- 1 Ethan 197121 2446 Oct  9 19:49 CLAUDE.md
-rw-r--r-- 1 Ethan 197121 1325 Oct  9 20:09 kirby_game_prompt.txt
./.claude/skills/grill-me/SKILL.md
./CLAUDE.md
./kirby_game_prompt.txt
v22.23.3
Bash Read the prompt file and check for a Chrome install
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && cat kirby_game_prompt.txt; ls "/c/Program Files/Google/Chrome/Application/chrome.exe" "/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" 2>&1

OUT
/grill-me

Work only inside the current directory. Do not read or modify any files outside it.

Build a pixel-art platformer game that runs in the browser by opening index.html.

Character: a small, round, pink character named Kirby who is surprisingly strong.
He can run, jump, and fly by pressing jump repeatedly while in the air. He can
also inhale: holding the action key pulls in nearby enemies and objects in front
of him. Once he has swallowed something, pressing the action key again spits it
out as a projectile that can defeat other enemies.

Game:
- One side-scrolling level with platforms, gaps, and a clear goal at the end.
- At least two kinds of enemies with different behavior (for example one that
  walks and one that flies).
- Lives, a score, a game-over screen, a win screen, and a way to restart.
- Controls: arrow keys or A/D to move, Space to jump and fly, Enter to inhale and spit.
  Show the controls on screen.

Look and feel:
- Retro pixel-art style with crisp pixels, a limited color palette, and simple
  animations (idle, run, jump, fly, inhale).
- Draw all sprites in code, with no external image files or libraries.
- Movement should feel tight and fun: sensible gravity, a floaty-but-controllable
  fly, and a satisfying inhale.

Make it polished and fun to play.
/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe*
/c/Program Files/Google/Chrome/Application/chrome.exe*
8:10 PM
The project is empty apart from CLAUDE.md and the prompt, so this starts from scratch. CLAUDE.md already settles a lot: classic <script> tags that work over file://, a fixed 60 Hz timestep, the file layout under js/logic/, one constants block, node:test unit tests, a playthrough driven only by key events, and a CDP smoke test. Node 22 and Chrome are both installed, so the smoke test can run. My questions cover only what those rules leave open.

Q1 of ~7: How limited should flying be?

Why it matters: this decides how the level gets designed. In real Kirby you can fly forever, which makes every gap trivial. CLAUDE.md also asks for a "fly limit" constant with tests, and the playthrough has to prove every gap can be crossed. The fly rules decide how wide gaps can be and whether they're a challenge at all.

My recommendation: give him a flap budget, around 6 flaps per airborne stretch, with flaps that are slow and floaty. The budget resets when he lands. Also, he can't fly while his mouth is full (as in the real games), so he can only jump. Gaps then come in two kinds: short ones you can jump, and wide ones you must fly over. Carrying an enemy becomes a real choice: spit it now, or hold it and give up flying.

Alternatives:

Unlimited flight, like real Kirby. Most faithful, but gaps stop being obstacles, so the challenge shifts to enemies.
A stamina meter that drains while flying. Smoother, but less readable than a flap count, and harder to tune.
A flap budget, but flying allowed with a full mouth. Simpler, but you lose the hold-or-spit choice.


CLAUDE.md
unlimited flight, like the real kirby, but he cant fly with his mouth full
8:11 PM
Got it: unlimited flight, but no flying with a full mouth. The "fly limit" that CLAUDE.md wants tested then becomes: a ceiling at the top of the level, a capped rise speed per flap, and the full-mouth lockout. Gaps will matter mainly when you're carrying something, or when flying enemies are in the way above them.

Q2 of ~7: What happens when Kirby gets hurt?

Why it matters: this sets the difficulty and how lives work. It also changes the HUD and the lives/game-over tests. With unlimited flight, falling into a pit is mostly a mistake made while your mouth is full.

My recommendation: a health bar inside each life, as in Kirby's Adventure. Kirby has 3 lives and 6 health pips per life. Touching an enemy costs 1 pip, gives a short blink of invincibility, and knocks him back. If he's holding something when hit, he drops it (it pops out and he can re-inhale it). Running out of pips, or falling into a pit, costs a life. Pits cost a life outright, whatever health is left. Each new life respawns at the last checkpoint with full health. Losing all lives leads to game over. Being forgiving fits Kirby, and the knockback and blinking make hits feel good.

Alternatives:

One hit = one life (Mario-style): simplest and much harsher. It suits a short level, but feels un-Kirby.
Health bar only, no separate lives: simpler, but the request explicitly asks for lives.


your recommendation is great
8:11 PM
Locked in: 3 lives, 6 health pips per life, knockback with a blink of invincibility, a hit makes him drop what he's holding, pits cost a life, and respawn is at the last checkpoint.

Q3 of ~7: What's the enemy and object lineup?

Why it matters: the request asks for two enemy types and says inhale pulls in "enemies and objects". This choice decides how many AI behaviors and inhale rules I build, which in turn sets the scope of the inhale-cone and spit tests.

My recommendation: original sprites, loosely Kirby-flavored:

Walker (Waddle Dee-like): patrols and turns at edges and walls. It can be inhaled.
Flyer (Bronto Burt-like): bobs on a sine wave and drifts toward the player. It can be inhaled, and it's the main threat over gaps.
Spiky (Gordo-like): a stationary or slowly bobbing hazard that can't be inhaled and can only be dodged. This teaches that inhale isn't the answer to everything, and costs little.
Star blocks: breakable blocks that can be inhaled and then spat. Some of them wall off the path, so you have to inhale something to get through. This covers the "objects" part of the request.
Alternatives:

Walker and flyer only: the minimum. Objects would come down to the star blocks alone.
Add a hopper (an enemy that jumps toward you): more variety, but one more AI to tune and test.
Drop the spiky: less to build, but the inhale becomes a button that always wins.


add all of the suggested ones, and a boss
8:12 PM
Roster locked in: walker, flyer, hopper, spiky (can't be inhaled), and star blocks. I'm reading "all of the suggested ones" as including the hopper too; tell me if you didn't mean that. Adding a boss raises the next decision.

Q4 of ~7: How does the boss fight work, and how does it relate to the goal?

Why it matters: the boss can only be hurt through the inhale/spit loop, so its design decides whether the core mechanic pays off at the end. It also changes what "finishing the level" means, and the automated playthrough test has to beat it using key presses only.

My recommendation: a tree boss in a closed arena at the end of the level (Whispy Woods-like, with original art):

It stands still on the right side of the arena.
It drops apples that roll toward you. Apples can be inhaled.
It blows air puffs, which hurt and can't be inhaled.
It can only be damaged by spit projectiles, at 6 HP. You get ammo by inhaling its apples and spitting them back.
When it's defeated, the arena opens and the goal (a warp star) appears. Touching the warp star wins the game.
Plus: a boss HP bar on the HUD, and a checkpoint at the arena door.
This is the cleanest test of inhale/spit. Its patterns are predictable, so the playthrough test can beat it reliably.

Alternatives:

A moving boss (Dedede-like: walks, jumps, hammer swings, and summons walkers you inhale as ammo): flashier, but much harder to tune and to beat deterministically in the test.
An optional boss guarding a bonus, with the warp star elsewhere: lower stakes, but the fight wouldn't feel like a climax.


go with your recommenation
8:13 PM
Boss locked in: a stationary tree boss in an arena, with apples to inhale for ammo, air puffs you can't inhale, damage only from spits, 6 HP, and a warp star after it falls.

Q5 of ~7: How long and how hard should the level be?

Why it matters: this sets how much level I hand-build, where checkpoints go, and how long the playthrough test runs. A level that's too short feels like a demo; one that's too long means lots of tuning I can't check by feel.

My recommendation: about 3 minutes for a first-time player, at gentle-to-medium difficulty, built as 4 themed stretches (roughly 220 tiles of 16px each):

Meadow (tutorial): flat ground, a couple of walkers, a short gap, and the controls hint on screen.
Cliffs: wider gaps, with flyers patrolling over them and a spiky placed where you'd naturally fly.
Star block fort: a wall of star blocks you must inhale-and-spit through, plus hoppers. A full mouth here means you can't fly over the gap that comes next, so you spit first.
Arena with the boss.
Checkpoints go at the start of stretch 2, the start of stretch 3, and the arena door. Collectibles: point stars along the way, and one food item that restores health before the boss.

Alternatives:

Short and tight (about 1 minute, 2 stretches before the boss): quicker to build and polish, but thinner.
Long (5 or more minutes, more stretches): more content, but more padding and more tuning risk.


long and hard
8:13 PM
Got it: long and hard. I'll aim for 5 to 7 minutes over about 6 stretches before the arena (for example meadow, cliffs, star block fort, a vertical climb, a windy sky section full of flyers, and a gauntlet), with denser enemy placement, tighter gaps under flyers, and spikies guarding the obvious flight lines. The 6-pip, 3-life model stays, but I'll keep extra lives rare: one hidden 1-up and an extra life at a score milestone (default). Checkpoints stay roughly every stretch so "hard" doesn't become "tedious".

Q6 of ~7: Do you want sound?

Why it matters: the request doesn't mention sound, but "polished and fun" and "a satisfying inhale" lean heavily on it: a whoosh while inhaling, a gulp, a spit pop, hit sounds. Sound has to be synthesized in code (no external assets allowed), and I can't verify how it sounds, only that it doesn't throw errors.

My recommendation: short chiptune sound effects made with Web Audio, for jump, flap, an inhale loop, gulp, spit, enemy defeat, hurt, star pickup, boss hit, win and game over. No music. Add an M key to mute, which CLAUDE.md allows. Sound starts on the first keypress, since browsers block audio until the player interacts. This is cheap and adds a lot of feel.

Alternatives:

Sound effects plus a simple looping chiptune melody: more atmosphere, but music I can't hear is risky to get right, and it gets grating over a long level.
No sound: zero risk, but the game feels noticeably flatter.


sounds effects with a simple looping melody
8:14 PM
Sound effects plus a looping chiptune melody, with M to mute and audio unlocked on the first keypress. I'll keep the melody short, quiet, and in a different key per area (main level vs. boss) so it's less likely to grate. I can't verify how it sounds, though.

Q7 of ~7: After game over, what does restarting do?

Why it matters: the level is long and hard, so a full restart after game over could mean replaying 5 or more minutes. This decides how restart works, what the game over and win screens offer, and what the restart test checks.

My recommendation:

The game over screen offers "Continue", which restarts from the last checkpoint with 3 lives and full health. Score resets to 0, since that's the cost of continuing.
The win screen shows the final score, time, and the best score saved in localStorage.
R restarts the whole run from the beginning at any time (with confirmation while playing).
P or Esc pauses.
A title screen shows the controls. The controls also stay visible in a small HUD strip during play, as the request asks.
The game over and title screens are started with Space, so Enter remains purely inhale/spit.

Alternatives:

Full restart only: classic and harsh, but painful on a long level.
Unlimited continues that keep your score: most forgiving, but score stops meaning much.


go with your recommendation, eventaully we'll addd more levels, but this is good for now
Write C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\DESIGN.md
44 lines
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
| Spit | A swallowed thing comes out as a star projectile that flies straight and defeats the first enemy or star block it hits. No copy abilities. | The request asks for spitting only. |
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
- Copy abilities, swallowing for powers, the down/up keys.
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
8:18 PM
The spec is written up in DESIGN.md. Nothing is built yet.

It records your seven answers. I filled in a few smaller points myself, marked "(default)" in the file:

Extra lives: a hidden 1-up, plus one at a score milestone, so "hard" doesn't turn hopeless.
Level format: the level is stored as data in js/level.js, so the extra levels you mentioned can be added without changing the engine.
Screen: a 256×224 canvas scaled up in whole steps, with about 16 colors.
Score values: placeholder numbers that are cheap to change later.
Hopper: I added it on top of the four enemies I recommended, reading "all of the suggested ones" as including it.

Keys: I won't add up or down arrow controls. The request only lists left/right for movement, and swallowing for powers is out of scope.

Read it over and tell me what to change, or say go and I'll start building.



in any of the quesitons, did yumention copy abilities?
8:18 PM
No, I never asked you about copy abilities. I decided on my own to leave them out, and I wrote that into DESIGN.md twice: in the Spit row and under Out of scope. I didn't mark either as "(default)" the way I did my other unasked choices. That was a mistake, because copy abilities change a lot about the game. Here's the question I should have asked.

Q8: Should Kirby get copy abilities?

Why it matters: in the real games you can swallow an enemy instead of spitting it, and gain its power. Your request only describes spitting. Adding powers means a swallow input, a power per enemy type, a way to drop the power, and more tests. It also changes the level design and the boss fight, which is currently built around spit-only damage.

Key constraint: swallowing in Kirby is done with the Down key. CLAUDE.md says to bind only the keys the request lists, and Down isn't one of them. Adding copy abilities would mean choosing to break that rule, or triggering swallow some other way (for example by holding Enter for a moment while your mouth is full).

My recommendation: leave them out for this first level, but structure the swallowed-thing state so powers can be added later alongside the extra levels. The request doesn't ask for them, and the long, hard level plus the boss is already a big build.

Alternatives:

One or two abilities now, for example a Spark from the hopper and a Beam from the walker, triggered by a long hold of Enter: more Kirby flavor, at a real cost in scope.
Full copy abilities with Down to swallow: most faithful, but it breaks the CLAUDE.md key rule.
Whatever you pick, I'll update DESIGN.md so it records your answer.



your rec
Edit C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\DESIGN.md
Added 1 line
Edit C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\DESIGN.md
Modified
8:19 PM
I've updated DESIGN.md: copy abilities now have their own row that records your choice, and the Out of scope line points back to it. The game will remember what Kirby swallowed, so powers can be added later with the new levels.

I also re-checked the spec for other decisions I made without asking. The rest are either marked "(default)" or follow directly from the request: the spit flies straight and knocks out the first thing it hits, and only Kirby's mouth-full state blocks flying.

Say go to start building, or tell me what else to change.



build to your herats content
8:30 PM
I'll start with the scaffolding and the logic layer (constants, physics, world), then the entities, then rendering, audio and tests.



Bash Create project folders and gitignore for .tmp
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && mkdir -p js/logic tests .tmp && printf '.tmp/\n' > .gitignore && git check-ignore -v .tmp/x; git status --short . | head

OUT
Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills/.gitignore:1:.tmp/	.tmp/x
?? ./
Write C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\js\logic\constants.js
140 lines
// Every tunable number in the game lives in this one block.
// Units: pixels for distance, ticks (1/60 s) for time, pixels per tick for speed.
var CONST = {
  // World and screen
  TILE: 16,
  VIEW_W: 256,
  VIEW_H: 224,
  TICKS_PER_SECOND: 60,
  MAX_SUBSTEP: 4,          // max px moved per collision sub-step (smaller than any body, so nothing tunnels)
  MAX_STEPS_PER_FRAME: 5,  // fixed-step catch-up cap so a slow frame cannot spiral

  // Player body and running
  PLAYER_W: 12,
  PLAYER_H: 12,
  RUN_MAX: 1.7,
  RUN_ACCEL: 0.16,
  RUN_DECEL: 0.22,
  RUN_TURN_BOOST: 0.12,
  AIR_ACCEL: 0.11,
  AIR_DECEL: 0.04,
  GRAVITY: 0.26,
  MAX_FALL: 4.8,
  JUMP_VY: -4.9,
  JUMP_CUT_VY: -1.8,       // releasing Space early clamps upward speed to this
  COYOTE_TICKS: 6,
  LAND_DUST_VY: 2.5,

  // Flying (unlimited flaps; the limits are the ceiling, the flap speed and the full-mouth lockout)
  FLAP_VY: -2.3,
  FLY_GRAVITY: 0.11,
  FLY_MAX_FALL: 1.1,
  FLY_MAX_SPEED: 1.25,
  FLY_ACCEL: 0.08,
  FLY_CEILING: 8,          // y in px that Kirby can never rise above
  FLAP_ANIM_TICKS: 10,

  // Mouth full
  FULL_MAX_SPEED: 1.2,
  FULL_JUMP_VY: -4.0,

  // Inhale
  INHALE_RANGE: 60,
  INHALE_HALF_HEIGHT: 10,  // cone half-height at the mouth
  INHALE_SPREAD: 0.35,     // extra half-height per px of distance
  INHALE_BEHIND: 4,        // how far behind the mouth still counts
  INHALE_HOLD_FACTOR: 1.3, // caught things stay caught out to range * this
  INHALE_PULL: 0.4,
  INHALE_MAX_PULL: 5,
  SWALLOW_RADIUS: 8,
  SWALLOW_LOCK_TICKS: 12,
  LOS_STEP: 6,             // px between line-of-sight samples

  // Spit star and exhaled air
  SPIT_SPEED: 4.5,
  SPIT_LIFE: 70,
  SPIT_SIZE: 12,
  BIG_SPIT_SIZE: 16,
  SPIT_RECOIL: 1.2,
  SPIT_ANIM_TICKS: 12,
  AIR_PUFF_SPEED: 3.2,
  AIR_PUFF_DRAG: 0.92,
  AIR_PUFF_LIFE: 18,
  AIR_PUFF_SIZE: 10,

  // Health and lives
  MAX_HEALTH: 6,
  START_LIVES: 3,
  INVULN_TICKS: 90,
  RESPAWN_INVULN_TICKS: 90,
  HURT_STUN_TICKS: 18,
  KNOCKBACK_VX: 2.2,
  KNOCKBACK_VY: -2.6,
  DEATH_TICKS: 120,
  PIT_MARGIN: 32,

  // Enemies
  ACTIVATION_RANGE: 300,
  STUN_TICKS: 30,
  WALKER_SPEED: 0.45,
  FLYER_SPEED: 0.55,
  FLYER_SENSE: 170,
  FLYER_AMP: 10,
  FLYER_FREQ: 0.05,
  FLYER_HOMING: 0.12,
  FLYER_LEASH: 48,
  FLYER_PATROL: 48,
  HOPPER_WAIT: 50,
  HOPPER_SENSE: 150,
  HOPPER_JUMP_VY: -4.2,
  HOPPER_HOP_VX: 1.3,
  SPIKY_AMP: 18,
  SPIKY_FREQ: 0.035,
  SPIKY_PATROL: 36,
  LOOSE_LIFE: 300,
  LOOSE_BOUNCE: -2.2,
  LOOSE_TOSS_VX: 1.5,
  LOOSE_FRICTION: 0.9,

  // Wind
  WIND_GUST_PERIOD: 150,
  WIND_GUST_MIN: 0.4,      // gusts vary between this fraction and 1.0 of full strength

  // Boss
  BOSS_HP: 6,
  BOSS_W: 40,
  BOSS_H: 56,
  BOSS_INTRO_TICKS: 90,
  BOSS_APPLE_WAIT: 130,
  BOSS_BLOW_WAIT: 110,
  BOSS_APPLES: 2,
  BOSS_RAGE_APPLES: 3,
  BOSS_PUFFS: 3,
  BOSS_PUFF_GAP: 26,
  BOSS_PUFF_SPEED: 1.5,
  BOSS_PUFF_LOW: 14,       // puff centre height above the floor (must jump)
  BOSS_PUFF_HIGH: 40,      // puff centre height above the floor (walk under)
  BOSS_PUFF_SIZE: 12,
  BOSS_HIT_INVULN: 45,
  BOSS_DEATH_TICKS: 150,
  BOSS_RAGE_HP: 3,
  BOSS_RAGE_SPEEDUP: 0.7,
  BOSS_APPLE_MARGIN: 32,   // apples never drop closer than this to the arena gate or the trunk
  APPLE_SIZE: 12,
  APPLE_ROLL_SPEED: 0.8,
  APPLE_LIFE: 420,
  ARENA_LOCK_OFFSET: 40,   // px past the gate before it slams shut

  // Score
  SCORE: { walker: 200, flyer: 300, hopper: 300, apple: 50, block: 50, star: 100, food: 500, boss: 5000 },
  TIME_BONUS_MAX: 10000,
  TIME_BONUS_PER_SECOND: 20,
  EXTRA_LIFE_SCORE: 15000,

  // Screens
  SCREEN_INPUT_DELAY: 45,  // ticks before title/game-over/win screens accept input
  BANNER_TICKS: 150
};

if (typeof module !== 'undefined') module.exports = { CONST };
Write C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\js\logic\physics.js
137 lines
// Tile collision and movement. Pure logic: no DOM, no canvas.
var Physics = (function () {
  'use strict';
  var C = typeof CONST !== 'undefined' ? CONST : require('./constants.js').CONST;
  var T = C.TILE;
  var EPS = 0.001;

  var TILES = { EMPTY: 0, GROUND: 1, STONE: 2, PLATFORM: 3, STAR: 4, SPIKES: 5 };

  function isSolid(t) {
    return t === TILES.GROUND || t === TILES.STONE || t === TILES.STAR || t === TILES.SPIKES;
  }

  // Outside the level sideways is a wall; above and below is open air.
  function tileAt(world, tx, ty) {
    if (tx < 0 || tx >= world.w) return TILES.STONE;
    if (ty < 0 || ty >= world.h) return TILES.EMPTY;
    return world.tiles[ty * world.w + tx];
  }

  function setTile(world, tx, ty, t) {
    if (tx < 0 || tx >= world.w || ty < 0 || ty >= world.h) return;
    world.tiles[ty * world.w + tx] = t;
  }

  function solidAtPoint(world, x, y) {
    return isSolid(tileAt(world, Math.floor(x / T), Math.floor(y / T)));
  }

  function overlaps(a, b) {
    return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
  }

  function stepX(world, body, dx) {
    var nx = body.x + dx;
    var top = Math.floor(body.y / T);
    var bottom = Math.floor((body.y + body.h - EPS) / T);
    var col = dx > 0 ? Math.floor((nx + body.w - EPS) / T) : Math.floor(nx / T);
    for (var r = top; r <= bottom; r++) {
      if (isSolid(tileAt(world, col, r))) {
        body.x = dx > 0 ? col * T - body.w : (col + 1) * T;
        body.vx = 0;
        body.hitWall = dx > 0 ? 1 : -1;
        return false;
      }
    }
    body.x = nx;
    return true;
  }

  function stepY(world, body, dy) {
    var ny = body.y + dy;
    var left = Math.floor(body.x / T);
    var right = Math.floor((body.x + body.w - EPS) / T);
    if (dy > 0) {
      var row = Math.floor((ny + body.h - EPS) / T);
      var rowTop = row * T;
      var wasAbove = body.y + body.h <= rowTop + EPS;
      for (var c = left; c <= right; c++) {
        var t = tileAt(world, c, row);
        if (isSolid(t) || (t === TILES.PLATFORM && wasAbove)) {
          body.y = rowTop - body.h;
          body.vy = 0;
          body.onGround = true;
          return false;
        }
      }
    } else {
      var rowUp = Math.floor(ny / T);
      for (var c2 = left; c2 <= right; c2++) {
        if (isSolid(tileAt(world, c2, rowUp))) {
          body.y = (rowUp + 1) * T;
          body.vy = 0;
          body.hitCeiling = true;
          return false;
        }
      }
    }
    body.y = ny;
    return true;
  }

  // Moves a body by its velocity (plus any pushX, such as wind) in small sub-steps,
  // resolving x then y each sub-step. Sets onGround, hitWall and hitCeiling.
  function moveBody(world, body) {
    body.onGround = false;
    body.hitWall = 0;
    body.hitCeiling = false;
    var dx = body.vx + (body.pushX || 0);
    var dy = body.vy;
    var steps = Math.max(1, Math.ceil(Math.max(Math.abs(dx), Math.abs(dy)) / C.MAX_SUBSTEP));
    var sx = dx / steps, sy = dy / steps;
    for (var i = 0; i < steps; i++) {
      if (sx !== 0 && !stepX(world, body, sx)) sx = 0;
      if (sy !== 0 && !stepY(world, body, sy)) sy = 0;
    }
  }

  // True when the body stands on a spike tile.
  function onSpikes(world, body) {
    if (!body.onGround) return false;
    var row = Math.round((body.y + body.h) / T);
    var left = Math.floor(body.x / T);
    var right = Math.floor((body.x + body.w - EPS) / T);
    for (var c = left; c <= right; c++) {
      if (tileAt(world, c, row) === TILES.SPIKES) return true;
    }
    return false;
  }

  // Samples points along a segment; true when no solid tile (other than star blocks) is in the way.
  function clearLine(world, x0, y0, x1, y1, ignoreStar) {
    var len = Math.hypot(x1 - x0, y1 - y0);
    var n = Math.max(1, Math.ceil(len / C.LOS_STEP));
    for (var i = 1; i < n; i++) {
      var x = x0 + (x1 - x0) * i / n, y = y0 + (y1 - y0) * i / n;
      var t = tileAt(world, Math.floor(x / T), Math.floor(y / T));
      if (isSolid(t) && !(ignoreStar && t === TILES.STAR)) return false;
    }
    return true;
  }

  return {
    TILES: TILES,
    isSolid: isSolid,
    tileAt: tileAt,
    setTile: setTile,
    solidAtPoint: solidAtPoint,
    overlaps: overlaps,
    moveBody: moveBody,
    onSpikes: onSpikes,
    clearLine: clearLine
  };
})();

if (typeof module !== 'undefined') module.exports = { Physics };
Write C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\js\logic\world.js
130 lines
// Turns level data (sections of tile placements) into a playable world. Pure logic.
var World = (function () {
  'use strict';
  var C = typeof CONST !== 'undefined' ? CONST : require('./constants.js').CONST;
  var P = typeof Physics !== 'undefined' ? Physics : require('./physics.js').Physics;
  var T = C.TILE, TL = P.TILES;

  var CHAR_TILES = { '#': TL.GROUND, '=': TL.STONE, '-': TL.PLATFORM, 'S': TL.STAR, '^': TL.SPIKES, ' ': TL.EMPTY };
  var ENEMY_CHARS = { w: 'walker', f: 'flyer', h: 'hopper', g: 'spiky', q: 'spiky' };
  var ITEM_CHARS = { o: 'star', T: 'food', '1': 'oneup' };

  function build(level) {
    var h = level.height;
    var w = level.sections.reduce(function (s, sec) { return s + sec.width; }, 0);
    var world = {
      w: w, h: h, tiles: new Uint8Array(w * h), groundRow: level.groundRow,
      spawns: [], items: [], checkpoints: [], signs: [], gaps: [], winds: [], caves: [], sections: [],
      start: null, bossSpawn: null, warp: null, gateCol: -1
    };
    var x0 = 0;

    level.sections.forEach(function (sec) {
      function place(ch, col, row) {
        if (col < 0 || col >= sec.width || row < 0 || row >= h) {
          throw new Error('Section "' + sec.name + '": placement out of bounds at ' + col + ',' + row);
        }
        var ax = x0 + col;
        if (CHAR_TILES[ch] !== undefined) { world.tiles[row * w + ax] = CHAR_TILES[ch]; return; }
        var px = ax * T, py = row * T;
        if (ENEMY_CHARS[ch]) {
          world.spawns.push({ type: ENEMY_CHARS[ch], col: ax, row: row, patrol: ch === 'q' });
        } else if (ITEM_CHARS[ch]) {
          world.items.push({ id: world.items.length, kind: ITEM_CHARS[ch], x: px + 3, y: py + 3, w: 10, h: 10 });
        } else if (ch === 'C') {
          world.checkpoints.push({ x: px + 4, y: py + T - 24, w: 8, h: 24 });
        } else if (ch === 'P') {
          world.start = { x: px + 2, y: py + T - C.PLAYER_H };
        } else if (ch === 'B') {
          world.bossSpawn = { x: px, y: py + T - C.BOSS_H };
        } else if (ch === 'W') {
          world.warp = { x: px - 4, y: py - 4, w: 24, h: 24 };
        } else if (ch === 'A') {
          world.gateCol = ax;
        } else {
          throw new Error('Section "' + sec.name + '": unknown level character "' + ch + '"');
        }
      }

      world.sections.push({ name: sec.name, x0: x0 * T, x1: (x0 + sec.width) * T });

      for (var c = 0; c < sec.width; c++) {
        var inGap = (sec.gaps || []).some(function (g) { return c >= g[0] && c < g[1]; });
        if (inGap) continue;
        for (var r = level.groundRow; r < h; r++) world.tiles[r * w + x0 + c] = TL.GROUND;
      }
      (sec.ceiling || []).forEach(function (cl) {
        for (var cc = cl[0]; cc < cl[1]; cc++) for (var rr = 0; rr <= cl[2]; rr++) place('=', cc, rr);
        world.caves.push({ x0: (x0 + cl[0]) * T, x1: (x0 + cl[1]) * T, top: (cl[2] + 1) * T });
      });
      (sec.fill || []).forEach(function (f) {
        for (var i = 0; i < f[2]; i++) for (var j = 0; j < f[3]; j++) place(f[4], f[0] + i, f[1] + j);
      });
      (sec.put || []).forEach(function (pt) {
        for (var i = 0; i < pt[2].length; i++) if (pt[2][i] !== '.') place(pt[2][i], pt[0] + i, pt[1]);
      });
      (sec.signs || []).forEach(function (s) {
        world.signs.push({ x: (x0 + s[0]) * T + T / 2, text: s[1] });
      });
      if (sec.wind) world.winds.push({ x0: x0 * T, x1: (x0 + sec.width) * T, strength: sec.wind });
      x0 += sec.width;
    });

    if (!world.start) throw new Error('Level has no player start (P)');
    world.checkpoints.sort(function (a, b) { return a.x - b.x; });
    world.checkpoints.forEach(function (cp, i) { cp.index = i; });

    // Gaps are runs of columns with no floor in the bottom row: falling there is a pit.
    var run = -1;
    for (var col = 0; col <= w; col++) {
      var open = col < w && !P.isSolid(world.tiles[(h - 1) * w + col]);
      if (open && run < 0) run = col;
      if (!open && run >= 0) { world.gaps.push({ x0: run * T, x1: col * T }); run = -1; }
    }
    world.original = world.tiles.slice();
    return world;
  }

  function resetTiles(world) {
    world.tiles.set(world.original);
  }

  // Signed horizontal wind push (px/tick) at a position and time.
  function windAt(world, x, time) {
    for (var i = 0; i < world.winds.length; i++) {
      var wd = world.winds[i];
      if (x >= wd.x0 && x < wd.x1) {
        var gust = C.WIND_GUST_MIN + (1 - C.WIND_GUST_MIN) * (0.5 + 0.5 * Math.sin(time * 2 * Math.PI / C.WIND_GUST_PERIOD));
        return wd.strength * gust;
      }
    }
    return 0;
  }

  function sectionIndexAt(world, x) {
    for (var i = 0; i < world.sections.length; i++) {
      if (x < world.sections[i].x1) return i;
    }
    return world.sections.length - 1;
  }

  // Small deterministic RNG (mulberry32) so runs and tests are reproducible.
  function rand(state) {
    state.rngState = (state.rngState + 0x6D2B79F5) | 0;
    var t = state.rngState;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }

  return {
    build: build,
    resetTiles: resetTiles,
    windAt: windAt,
    sectionIndexAt: sectionIndexAt,
    rand: rand
  };
})();

if (typeof module !== 'undefined') module.exports = { World };
Edit C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\js\logic\world.js
Added 19 lines
8:32 PM
Now the entity modules. First I'll give clearLine a skip box so a target's own tile doesn't block its line of sight.



Edit C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\js\logic\physics.js
Added 1 line
Write C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\js\logic\enemies.js
204 lines
// Enemy and object behaviour: walker, flyer, hopper, spiky, loose objects, apples, boss puffs. Pure logic.
var Enemies = (function () {
  'use strict';
  var C = typeof CONST !== 'undefined' ? CONST : require('./constants.js').CONST;
  var P = typeof Physics !== 'undefined' ? Physics : require('./physics.js').Physics;
  var W = typeof World !== 'undefined' ? World : require('./world.js').World;
  var T = C.TILE;

  var INHALABLE = { walker: true, flyer: true, hopper: true, apple: true, loose: true };
  var HARMFUL = { walker: true, flyer: true, hopper: true, spiky: true, apple: true, bosspuff: true };
  var DEFEATABLE = { walker: true, flyer: true, hopper: true, apple: true };
  var nextId = 1;

  function base(type, x, y, w, h) {
    return {
      id: nextId++, type: type, x: x, y: y, w: w, h: h, vx: 0, vy: 0, facing: -1,
      onGround: false, hitWall: 0, active: false, caught: false, pull: 0, stun: 0, t: 0, timer: 0,
      dead: false, inhalable: !!INHALABLE[type], harmful: !!HARMFUL[type]
    };
  }

  function fromSpawn(sp) {
    var x = sp.col * T, y = sp.row * T, e;
    if (sp.type === 'walker' || sp.type === 'hopper') return base(sp.type, x + 2, y + T - 12, 12, 12);
    if (sp.type === 'flyer') {
      e = base('flyer', x + 2, y + 3, 12, 10);
      e.baseY = e.y; e.spawnX = e.x; e.spawnY = e.y;
      return e;
    }
    e = base('spiky', x + 1, y + 1, 14, 14);
    e.baseX = e.x; e.baseY = e.y; e.patrol = !!sp.patrol;
    return e;
  }

  function spawnAll(world) {
    return world.spawns.map(fromSpawn);
  }

  function makeLoose(kind, x, y, vx, score) {
    var e = base('loose', x, y, 12, 12);
    e.kind = kind; e.vx = vx; e.vy = C.LOOSE_BOUNCE; e.life = C.LOOSE_LIFE;
    e.score = score || 0; e.active = true; e.bounce = C.LOOSE_BOUNCE;
    return e;
  }

  function makeApple(x, y) {
    var e = base('apple', x, y, C.APPLE_SIZE, C.APPLE_SIZE);
    e.life = C.APPLE_LIFE; e.active = true; e.rolling = false;
    return e;
  }

  function makePuff(x, y, vx) {
    var e = base('bosspuff', x, y, C.BOSS_PUFF_SIZE, C.BOSS_PUFF_SIZE);
    e.vx = vx; e.baseY = y; e.active = true;
    return e;
  }

  function fall(world, e) {
    e.vy = Math.min(e.vy + C.GRAVITY, C.MAX_FALL);
    P.moveBody(world, e);
  }

  function updateWalker(state, e) {
    var world = state.world;
    if (e.onGround) {
      var fx = e.facing > 0 ? e.x + e.w + 1 : e.x - 1;
      var below = P.tileAt(world, Math.floor(fx / T), Math.floor((e.y + e.h + 1) / T));
      if (!P.isSolid(below) && below !== P.TILES.PLATFORM) e.facing = -e.facing;
    }
    e.vx = e.facing * C.WALKER_SPEED;
    fall(world, e);
    if (e.hitWall) e.facing = -e.facing;
  }

  function updateHopper(state, e) {
    var p = state.player;
    if (e.onGround) {
      e.vx = 0;
      e.timer++;
      var dx = (p.x + p.w / 2) - (e.x + e.w / 2);
      if (e.timer >= C.HOPPER_WAIT && Math.abs(dx) < C.HOPPER_SENSE) {
        e.facing = dx < 0 ? -1 : 1;
        e.vy = C.HOPPER_JUMP_VY;
        e.vx = e.facing * C.HOPPER_HOP_VX;
        e.timer = 0;
      }
    }
    fall(state.world, e);
  }

  function updateFlyer(state, e) {
    var p = state.player;
    var dx = p.x - e.x, dy = p.y - e.baseY;
    if (Math.abs(dx) < C.FLYER_SENSE && Math.abs(dy) < C.FLYER_SENSE) {
      e.facing = dx < 0 ? -1 : 1;
      e.baseY += Math.max(-C.FLYER_HOMING, Math.min(C.FLYER_HOMING, dy));
      e.baseY = Math.max(e.spawnY - C.FLYER_LEASH, Math.min(e.spawnY + C.FLYER_LEASH, e.baseY));
      e.x += e.facing * C.FLYER_SPEED;
    } else {
      if (Math.abs(e.x - e.spawnX) > C.FLYER_PATROL) e.facing = e.x < e.spawnX ? 1 : -1;
      e.x += e.facing * C.FLYER_SPEED * 0.5;
    }
    e.y = e.baseY + C.FLYER_AMP * Math.sin(e.t * C.FLYER_FREQ);
  }

  function updateSpiky(state, e) {
    var s = Math.sin(e.t * C.SPIKY_FREQ);
    if (e.patrol) e.x = e.baseX + C.SPIKY_PATROL * s;
    else e.y = e.baseY + C.SPIKY_AMP * s;
  }

  function updateLoose(state, e) {
    fall(state.world, e);
    if (e.onGround) {
      e.vx *= C.LOOSE_FRICTION;
      e.bounce *= 0.6;
      if (e.bounce < -0.8) e.vy = e.bounce;
    }
    if (--e.life <= 0) e.dead = true;
  }

  function updateApple(state, e) {
    var p = state.player;
    if (e.rolling) e.vx = e.facing * C.APPLE_ROLL_SPEED;
    fall(state.world, e);
    if (e.onGround && !e.rolling) {
      e.rolling = true;
      e.facing = p.x + p.w / 2 < e.x + e.w / 2 ? -1 : 1;
      W.emit(state, 'appleLand', e.x + e.w / 2, e.y + e.h);
    }
    if (e.hitWall) e.facing = -e.facing;
    if (--e.life <= 0) e.dead = true;
  }

  function updatePuff(state, e) {
    e.x += e.vx;
    e.y = e.baseY + 2 * Math.sin(e.t * 0.25);
    if (P.solidAtPoint(state.world, e.x + e.w / 2, e.y + e.h / 2)) {
      e.dead = true;
      W.emit(state, 'puffPop', e.x + e.w / 2, e.y + e.h / 2);
    }
  }

  var UPDATERS = {
    walker: updateWalker, hopper: updateHopper, flyer: updateFlyer, spiky: updateSpiky,
    loose: updateLoose, apple: updateApple, bosspuff: updatePuff
  };
  var GROUNDED = { walker: true, hopper: true, loose: true, apple: true };

  function update(state) {
    var p = state.player, world = state.world;
    for (var i = 0; i < state.enemies.length; i++) {
      var e = state.enemies[i];
      if (e.dead || e.caught) continue;
      if (!e.active) {
        if (Math.abs(e.x - p.x) < C.ACTIVATION_RANGE) e.active = true;
        else continue;
      }
      e.t++;
      if (e.stun > 0) {
        e.stun--;
        e.vx = 0;
        if (GROUNDED[e.type]) fall(world, e);
        continue;
      }
      UPDATERS[e.type](state, e);
      if (e.y > world.h * T + C.PIT_MARGIN) e.dead = true;
    }
  }

  // Called when the inhale lets go of something it was pulling.
  function release(e) {
    e.caught = false;
    e.pull = 0;
    e.stun = C.STUN_TICKS;
    if (e.type === 'flyer') { e.baseY = e.y; e.t = 0; }
  }

  function defeat(state, e) {
    e.dead = true;
    W.addScore(state, C.SCORE[e.type] || 0);
    W.emit(state, 'defeat', e.x + e.w / 2, e.y + e.h / 2, { kind: e.type });
  }

  function removeDead(state) {
    state.enemies = state.enemies.filter(function (e) { return !e.dead; });
  }

  return {
    DEFEATABLE: DEFEATABLE,
    fromSpawn: fromSpawn,
    spawnAll: spawnAll,
    makeLoose: makeLoose,
    makeApple: makeApple,
    makePuff: makePuff,
    update: update,
    release: release,
    defeat: defeat,
    removeDead: removeDead
  };
})();

if (typeof module !== 'undefined') module.exports = { Enemies };
8:32 PM
I'll move the few remaining hard-coded numbers in enemies.js into the constants block now, so I don't forget.



Bash Move enemy magic numbers into constants and scan for leftovers
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills/js/logic" && python - <<'EOF'
import re
p='constants.js'; s=open(p,encoding='utf8').read()
s=s.replace("""  LOOSE_FRICTION: 0.9,
""","""  LOOSE_FRICTION: 0.9,
  LOOSE_BOUNCE_DECAY: 0.6,
  LOOSE_MIN_BOUNCE: -0.8,
  ENEMY_SIZE: 12,          // walker, hopper, flyer width; loose objects
  FLYER_H: 10,
  SPIKY_SIZE: 14,
""")
s=s.replace("""  BOSS_PUFF_SIZE: 12,
""","""  BOSS_PUFF_SIZE: 12,
  BOSS_PUFF_WOBBLE: 2,
  BOSS_PUFF_WOBBLE_FREQ: 0.25,
""")
open(p,'w',encoding='utf8').write(s)
p='enemies.js'; s=open(p,encoding='utf8').read()
s=s.replace("""    var x = sp.col * T, y = sp.row * T, e;
    if (sp.type === 'walker' || sp.type === 'hopper') return base(sp.type, x + 2, y + T - 12, 12, 12);
    if (sp.type === 'flyer') {
      e = base('flyer', x + 2, y + 3, 12, 10);""","""    var S = C.ENEMY_SIZE, x = sp.col * T, y = sp.row * T, e;
    if (sp.type === 'walker' || sp.type === 'hopper') return base(sp.type, x + (T - S) / 2, y + T - S, S, S);
    if (sp.type === 'flyer') {
      e = base('flyer', x + (T - S) / 2, y + (T - C.FLYER_H) / 2, S, C.FLYER_H);""")
s=s.replace("""    e = base('spiky', x + 1, y + 1, 14, 14);""","""    e = base('spiky', x + (T - C.SPIKY_SIZE) / 2, y + (T - C.SPIKY_SIZE) / 2, C.SPIKY_SIZE, C.SPIKY_SIZE);""")
s=s.replace("""    var e = base('loose', x, y, 12, 12);""","""    var e = base('loose', x, y, C.ENEMY_SIZE, C.ENEMY_SIZE);""")
s=s.replace("""      e.bounce *= 0.6;
      if (e.bounce < -0.8) e.vy = e.bounce;""","""      e.bounce *= C.LOOSE_BOUNCE_DECAY;
      if (e.bounce < C.LOOSE_MIN_BOUNCE) e.vy = e.bounce;""")
s=s.replace("""    e.y = e.baseY + 2 * Math.sin(e.t * 0.25);""","""    e.y = e.baseY + C.BOSS_PUFF_WOBBLE * Math.sin(e.t * C.BOSS_PUFF_WOBBLE_FREQ);""")
open(p,'w',encoding='utf8').write(s)
EOF
grep -n "[^A-Z_.a-z0-9][0-9]\+\.[0-9]\|[ (,][2-9][0-9]*[ ,;)]" enemies.js | head -20

OUT
24:    if (sp.type === 'walker' || sp.type === 'hopper') return base(sp.type, x + (T - S) / 2, y + T - S, S, S);
26:      e = base('flyer', x + (T - S) / 2, y + (T - C.FLYER_H) / 2, S, C.FLYER_H);
30:    e = base('spiky', x + (T - C.SPIKY_SIZE) / 2, y + (T - C.SPIKY_SIZE) / 2, C.SPIKY_SIZE, C.SPIKY_SIZE);
80:      var dx = (p.x + p.w / 2) - (e.x + e.w / 2);
101:      e.x += e.facing * C.FLYER_SPEED * 0.5;
128:      e.facing = p.x + p.w / 2 < e.x + e.w / 2 ? -1 : 1;
129:      W.emit(state, 'appleLand', e.x + e.w / 2, e.y + e.h);
138:    if (P.solidAtPoint(state.world, e.x + e.w / 2, e.y + e.h / 2)) {
140:      W.emit(state, 'puffPop', e.x + e.w / 2, e.y + e.h / 2);
182:    W.emit(state, 'defeat', e.x + e.w / 2, e.y + e.h / 2, { kind: e.type });
Bash Replace flyer patrol speed factor with a constant
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && sed -i 's/e.x += e.facing \* C.FLYER_SPEED \* 0.5;/e.x += e.facing * C.FLYER_PATROL_SPEED;/' js/logic/enemies.js && sed -i 's/^  FLYER_PATROL: 48,$/  FLYER_PATROL: 48,\n  FLYER_PATROL_SPEED: 0.3,/' js/logic/constants.js && grep -n "PATROL_SPEED" js/logic/*.js

OUT
js/logic/constants.js:87:  FLYER_PATROL_SPEED: 0.3,
js/logic/enemies.js:101:      e.x += e.facing * C.FLYER_PATROL_SPEED;
8:32 PM
Next, the player module (movement, flying, inhale, spit, damage).



Write C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\js\logic\player.js
283 lines
// Kirby: running, jumping, unlimited flight, inhale, swallow, spit and taking damage. Pure logic.
var Player = (function () {
  'use strict';
  var C = typeof CONST !== 'undefined' ? CONST : require('./constants.js').CONST;
  var P = typeof Physics !== 'undefined' ? Physics : require('./physics.js').Physics;
  var W = typeof World !== 'undefined' ? World : require('./world.js').World;
  var E = typeof Enemies !== 'undefined' ? Enemies : require('./enemies.js').Enemies;
  var T = C.TILE;

  function create(x, y) {
    return {
      x: x, y: y, w: C.PLAYER_W, h: C.PLAYER_H, vx: 0, vy: 0, pushX: 0, facing: 1,
      onGround: false, hitWall: 0, hitCeiling: false,
      health: C.MAX_HEALTH, flying: false, inhaling: false, jumping: false, mouth: null,
      coyote: 0, invuln: 0, hurtTimer: 0, spitAnim: 0, flapAnim: 0, swallowLock: 0,
      actionNeedsRelease: false, inhaleTicks: 0, animT: 0
    };
  }

  function approach(v, target, step) {
    return v < target ? Math.min(v + step, target) : Math.max(v - step, target);
  }

  function mouthPoint(p) {
    return { x: p.facing > 0 ? p.x + p.w : p.x, y: p.y + p.h / 2 };
  }

  // Is the centre of box inside the cone in front of Kirby's mouth?
  function inInhaleCone(p, box) {
    var m = mouthPoint(p);
    var dx = (box.x + box.w / 2 - m.x) * p.facing;
    var dy = Math.abs(box.y + box.h / 2 - m.y);
    return dx >= -C.INHALE_BEHIND && dx <= C.INHALE_RANGE &&
      dy <= C.INHALE_HALF_HEIGHT + Math.max(0, dx) * C.INHALE_SPREAD;
  }

  function update(state, input) {
    var p = state.player, world = state.world;
    p.animT++;
    if (p.invuln > 0) p.invuln--;
    if (p.spitAnim > 0) p.spitAnim--;
    if (p.flapAnim > 0) p.flapAnim--;
    if (p.swallowLock > 0) p.swallowLock--;
    var stunned = p.hurtTimer > 0;
    if (stunned) p.hurtTimer--;
    if (!input.action) p.actionNeedsRelease = false;

    if (stunned) setInhaling(state, false);
    else handleAction(state, input);

    var dir = (stunned || p.inhaling) ? 0 : (input.right ? 1 : 0) - (input.left ? 1 : 0);
    if (dir !== 0) p.facing = dir;

    // Horizontal movement
    var maxSpeed = p.flying ? C.FLY_MAX_SPEED : (p.mouth ? C.FULL_MAX_SPEED : C.RUN_MAX);
    var accel = p.flying ? C.FLY_ACCEL : (p.onGround ? C.RUN_ACCEL : C.AIR_ACCEL);
    var decel = p.onGround ? C.RUN_DECEL : C.AIR_DECEL;
    if (dir !== 0) {
      if (p.vx * dir < 0 && p.onGround) accel += C.RUN_TURN_BOOST;
      if (p.vx * dir < maxSpeed) p.vx = Math.min(p.vx * dir + accel, maxSpeed) * dir;
      else p.vx = approach(p.vx, dir * maxSpeed, decel);
    } else {
      p.vx = approach(p.vx, 0, decel);
    }

    // Jump, or flap when already airborne
    if (p.onGround) p.coyote = C.COYOTE_TICKS;
    else if (p.coyote > 0) p.coyote--;
    if (input.jumpPressed && !stunned && !p.inhaling) {
      if (p.coyote > 0 && !p.flying) {
        p.vy = p.mouth ? C.FULL_JUMP_VY : C.JUMP_VY;
        p.jumping = true;
        p.coyote = 0;
        W.emit(state, 'jump', p.x + p.w / 2, p.y + p.h);
      } else if (!p.mouth) {
        p.flying = true;
        p.jumping = false;
        p.vy = C.FLAP_VY;
        p.flapAnim = C.FLAP_ANIM_TICKS;
        W.emit(state, 'flap', p.x + p.w / 2, p.y + p.h);
      } else {
        W.emit(state, 'noFly', p.x + p.w / 2, p.y);
      }
    }
    if (p.jumping && !input.jump && p.vy < C.JUMP_CUT_VY) p.vy = C.JUMP_CUT_VY;
    if (p.vy >= 0) p.jumping = false;

    // Gravity, wind and collision
    var g = p.flying ? C.FLY_GRAVITY : C.GRAVITY;
    var maxFall = p.flying ? C.FLY_MAX_FALL : C.MAX_FALL;
    p.vy = Math.min(p.vy + g, maxFall);
    p.pushX = W.windAt(world, p.x, state.time);
    var wasOnGround = p.onGround, fallSpeed = p.vy;
    P.moveBody(world, p);
    if (p.y < C.FLY_CEILING) {
      p.y = C.FLY_CEILING;
      if (p.vy < 0) p.vy = 0;
    }
    if (p.onGround) {
      p.jumping = false;
      if (p.flying) {
        p.flying = false;
        W.emit(state, 'deflate', p.x + p.w / 2, p.y + p.h / 2, { facing: p.facing });
      } else if (!wasOnGround && fallSpeed > C.LAND_DUST_VY) {
        W.emit(state, 'land', p.x + p.w / 2, p.y + p.h);
      }
    }
  }

  function setInhaling(state, on) {
    var p = state.player;
    if (on && !p.inhaling) W.emit(state, 'inhaleStart', p.x, p.y);
    if (!on && p.inhaling) W.emit(state, 'inhaleStop', p.x, p.y);
    p.inhaling = on;
    p.inhaleTicks = on ? p.inhaleTicks + 1 : 0;
  }

  function handleAction(state, input) {
    var p = state.player;
    if (p.flying) {
      setInhaling(state, false);
      if (input.actionPressed) {
        p.flying = false;
        p.actionNeedsRelease = true;
        var m = mouthPoint(p), s = C.AIR_PUFF_SIZE;
        state.projectiles.push({
          kind: 'air', x: p.facing > 0 ? m.x : m.x - s, y: m.y - s / 2, w: s, h: s,
          vx: p.facing * C.AIR_PUFF_SPEED, life: C.AIR_PUFF_LIFE, pierce: false, power: 1
        });
        W.emit(state, 'exhale', m.x, m.y, { facing: p.facing });
      }
      return;
    }
    if (p.mouth) {
      setInhaling(state, false);
      if (input.actionPressed && p.swallowLock === 0) spit(state);
      return;
    }
    setInhaling(state, !!input.action && !p.actionNeedsRelease);
  }

  function spit(state) {
    var p = state.player;
    var big = p.mouth.count >= 2;
    var size = big ? C.BIG_SPIT_SIZE : C.SPIT_SIZE;
    var m = mouthPoint(p);
    state.projectiles.push({
      kind: 'star', big: big, x: p.facing > 0 ? m.x - 2 : m.x - size + 2, y: m.y - size / 2,
      w: size, h: size, vx: p.facing * C.SPIT_SPEED, life: C.SPIT_LIFE,
      pierce: big, power: big ? 2 : 1
    });
    p.mouth = null;
    p.spitAnim = C.SPIT_ANIM_TICKS;
    p.vx -= p.facing * C.SPIT_RECOIL;
    p.actionNeedsRelease = true;
    W.emit(state, 'spit', m.x, m.y, { facing: p.facing, big: big });
  }

  // Pull a single star-block tile out of the wall once it is inside the cone.
  function grabStarBlock(state, m) {
    var p = state.player, world = state.world;
    if (state.enemies.some(function (e) { return e.caught && e.kind === 'block'; })) return;
    var half = C.INHALE_HALF_HEIGHT + C.INHALE_RANGE * C.INHALE_SPREAD;
    var x0 = Math.min(m.x, m.x + p.facing * C.INHALE_RANGE), x1 = Math.max(m.x, m.x + p.facing * C.INHALE_RANGE);
    var best = null, bestD = Infinity;
    for (var c = Math.floor(x0 / T); c <= Math.floor(x1 / T); c++) {
      for (var r = Math.floor((m.y - half) / T); r <= Math.floor((m.y + half) / T); r++) {
        if (P.tileAt(world, c, r) !== P.TILES.STAR) continue;
        var box = { x: c * T, y: r * T, w: T, h: T };
        if (!inInhaleCone(p, box)) continue;
        if (!P.clearLine(world, m.x, m.y, box.x + T / 2, box.y + T / 2, box)) continue;
        var d = Math.hypot(box.x + T / 2 - m.x, box.y + T / 2 - m.y);
        if (d < bestD) { bestD = d; best = { c: c, r: r }; }
      }
    }
    if (!best) return;
    P.setTile(world, best.c, best.r, P.TILES.EMPTY);
    var S = C.ENEMY_SIZE;
    var blk = E.makeLoose('block', best.c * T + (T - S) / 2, best.r * T + (T - S) / 2, 0, C.SCORE.block);
    blk.vy = 0;
    blk.caught = true;
    state.enemies.push(blk);
    W.emit(state, 'blockGrab', best.c * T + T / 2, best.r * T + T / 2);
  }

  // Runs after movement: pulls inhalable things in the cone toward the mouth and swallows them.
  function applyInhale(state) {
    var p = state.player, world = state.world;
    var i, e;
    if (!p.inhaling) {
      for (i = 0; i < state.enemies.length; i++) if (state.enemies[i].caught) E.release(state.enemies[i]);
      return;
    }
    var m = mouthPoint(p);
    grabStarBlock(state, m);
    var swallowed = [];
    for (i = 0; i < state.enemies.length; i++) {
      e = state.enemies[i];
      if (e.dead || !e.inhalable) continue;
      var cx = e.x + e.w / 2, cy = e.y + e.h / 2;
      if (!e.caught) {
        if (!inInhaleCone(p, e) || !P.clearLine(world, m.x, m.y, cx, cy, e)) continue;
        e.caught = true;
        e.active = true;
        e.pull = 0;
      } else if (Math.hypot(cx - m.x, cy - m.y) > C.INHALE_RANGE * C.INHALE_HOLD_FACTOR) {
        E.release(e);
        continue;
      }
      e.pull = Math.min(e.pull + C.INHALE_PULL, C.INHALE_MAX_PULL);
      var dx = m.x - cx, dy = m.y - cy, d = Math.hypot(dx, dy);
      if (d <= C.SWALLOW_RADIUS + e.pull) swallowed.push(e);
      else { e.x += dx / d * e.pull; e.y += dy / d * e.pull; }
    }
    if (swallowed.length) swallow(state, swallowed);
  }

  function swallow(state, list) {
    var p = state.player;
    var count = p.mouth ? p.mouth.count : 0;
    var kind = p.mouth ? p.mouth.kind : (list[0].kind || list[0].type);
    list.forEach(function (e) {
      e.dead = true;
      e.caught = false;
      count++;
      var pts = e.type === 'loose' ? e.score : (C.SCORE[e.type] || 0);
      if (pts) W.addScore(state, pts);
    });
    p.mouth = { kind: kind, count: count };
    setInhaling(state, false);
    p.swallowLock = C.SWALLOW_LOCK_TICKS;
    p.actionNeedsRelease = true;
    state.enemies.forEach(function (e) { if (e.caught) E.release(e); });
    var m = mouthPoint(p);
    W.emit(state, 'swallow', m.x, m.y, { kind: kind, count: count });
  }

  function hurt(state, srcX) {
    var p = state.player;
    if (p.invuln > 0 || state.mode !== 'playing') return false;
    p.health -= 1;
    p.invuln = C.INVULN_TICKS;
    p.hurtTimer = C.HURT_STUN_TICKS;
    var away = (p.x + p.w / 2) < srcX ? -1 : 1;
    p.vx = away * C.KNOCKBACK_VX;
    p.vy = C.KNOCKBACK_VY;
    p.flying = false;
    p.jumping = false;
    setInhaling(state, false);
    if (p.mouth) {
      state.enemies.push(E.makeLoose(p.mouth.kind, p.x, p.y - C.ENEMY_SIZE / 2, -away * C.LOOSE_TOSS_VX, 0));
      p.mouth = null;
      W.emit(state, 'drop', p.x + p.w / 2, p.y);
    }
    W.emit(state, 'hurt', p.x + p.w / 2, p.y + p.h / 2);
    if (p.health <= 0) kill(state);
    return true;
  }

  function kill(state) {
    var p = state.player;
    p.health = 0;
    p.flying = false;
    p.mouth = null;
    setInhaling(state, false);
    state.mode = 'dying';
    state.deathTimer = C.DEATH_TICKS;
    W.emit(state, 'death', p.x + p.w / 2, p.y + p.h / 2);
  }

  return {
    create: create,
    update: update,
    applyInhale: applyInhale,
    inInhaleCone: inInhaleCone,
    mouthPoint: mouthPoint,
    hurt: hurt,
    kill: kill
  };
})();

if (typeof module !== 'undefined') module.exports = { Player };
8:33 PM
Now the boss.



Write C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\js\logic\boss.js
120 lines
// Old Gnarlwood, the tree boss: drops apples (inhalable ammo) and blows air puffs.
// Only spat stars hurt it. Pure logic.
var Boss = (function () {
  'use strict';
  var C = typeof CONST !== 'undefined' ? CONST : require('./constants.js').CONST;
  var W = typeof World !== 'undefined' ? World : require('./world.js').World;
  var E = typeof Enemies !== 'undefined' ? Enemies : require('./enemies.js').Enemies;
  var T = C.TILE;

  function create(world) {
    if (!world.bossSpawn) return null;
    return {
      x: world.bossSpawn.x, y: world.bossSpawn.y, w: C.BOSS_W, h: C.BOSS_H,
      hp: C.BOSS_HP, state: 'dormant', timer: 0, invuln: 0, t: 0, cycle: 0, mouthOpen: 0
    };
  }

  function alive(b) {
    return !!b && b.state !== 'dormant' && b.state !== 'dying' && b.state !== 'dead';
  }

  function enraged(b) {
    return b.hp <= C.BOSS_RAGE_HP;
  }

  function wait(b, ticks) {
    return Math.round(enraged(b) ? ticks * C.BOSS_RAGE_SPEEDUP : ticks);
  }

  function floorY(state) {
    return state.world.groundRow * T;
  }

  function wake(state) {
    var b = state.boss;
    if (!b || b.state !== 'dormant') return;
    b.state = 'intro';
    b.timer = 0;
    W.emit(state, 'bossWake', b.x + b.w / 2, b.y);
  }

  function dropApples(state, b) {
    var n = enraged(b) ? C.BOSS_RAPID_APPLES || C.BOSS_RAGE_APPLES : C.BOSS_APPLES;
    var left = state.world.gateCol * T + C.BOSS_APPLE_MARGIN;
    var right = b.x - C.BOSS_APPLE_MARGIN;
    var top = state.world.arenaTop;
    for (var i = 0; i < n; i++) {
      // Spread apples across the arena in equal lanes, jittered inside each lane.
      var lane = (right - left) / n;
      var x = left + lane * i + W.rand(state) * (lane - C.APPLE_SIZE);
      state.enemies.push(E.makeApple(Math.round(x), top));
    }
    W.emit(state, 'appleDrop', b.x, b.y);
  }

  function blowPuff(state, b, k) {
    var low = (k + b.cycle) % 2 === 0;
    var cy = floorY(state) - (low ? C.BOSS_PUFF_LOW : C.BOSS_PUFF_HIGH);
    state.enemies.push(E.makePuff(b.x - C.BOSS_PUFF_SIZE, cy - C.BOSS_PUFF_SIZE / 2, -C.BOSS_PUFF_SPEED));
    b.mouthOpen = C.BOSS_PUFF_GAP;
    W.emit(state, 'bossBlow', b.x, cy);
  }

  function update(state) {
    var b = state.boss;
    if (!b || b.state === 'dormant' || b.state === 'dead') return;
    b.t++;
    if (b.invuln > 0) b.invuln--;
    if (b.mouthOpen > 0) b.mouthOpen--;
    b.timer++;
    if (b.state === 'intro') {
      if (b.timer >= C.BOSS_INTRO_TICKS) { b.state = 'apples'; b.timer = 0; }
    } else if (b.state === 'apples') {
      if (b.timer === 1) dropApples(state, b);
      if (b.timer >= wait(b, C.BOSS_APPLE_WAIT)) { b.state = 'blow'; b.timer = 0; }
    } else if (b.state === 'blow') {
      var gap = wait(b, C.BOSS_PUFF_GAP);
      if (b.timer % gap === 0 && b.timer / gap <= C.BOSS_PUFFS) blowPuff(state, b, b.timer / gap);
      if (b.timer >= wait(b, C.BOSS_BLOW_WAIT)) { b.state = 'apples'; b.timer = 0; b.cycle++; }
    } else if (b.state === 'dying') {
      if (b.timer % C.BOSS_BOOM_EVERY === 0) {
        W.emit(state, 'bossBoom', b.x + W.rand(state) * b.w, b.y + W.rand(state) * b.h);
      }
      if (b.timer >= C.BOSS_DEATH_TICKS) {
        b.state = 'dead';
        state.warp.active = true;
        W.addScore(state, C.SCORE.boss);
        W.emit(state, 'bossDefeated', b.x + b.w / 2, b.y + b.h / 2);
      }
    }
  }

  // A spat star hit the boss. Returns true if it took damage.
  function hit(state, power) {
    var b = state.boss;
    if (!alive(b) || b.invuln > 0) return false;
    b.hp = Math.max(0, b.hp - power);
    b.invuln = C.BOSS_HIT_INVULN;
    W.emit(state, 'bossHit', b.x + b.w / 2, b.y + b.h / 3, { hp: b.hp });
    if (b.hp === 0) {
      b.state = 'dying';
      b.timer = 0;
      state.enemies.forEach(function (e) {
        if (e.type === 'apple' || e.type === 'bosspuff') e.dead = true;
      });
    }
    return true;
  }

  return {
    create: create,
    alive: alive,
    wake: wake,
    update: update,
    hit: hit
  };
})();

if (typeof module !== 'undefined') module.exports = { Boss };
Bash Fix boss constants and add arena top to world
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && python - <<'EOF'
p='js/logic/boss.js'; s=open(p,encoding='utf8').read()
s=s.replace("C.BOSS_RAPID_APPLES || C.BOSS_RAGE_APPLES","C.BOSS_RAGE_APPLES")
open(p,'w',encoding='utf8').write(s)
p='js/logic/constants.js'; s=open(p,encoding='utf8').read()
s=s.replace("  BOSS_DEATH_TICKS: 150,\n","  BOSS_DEATH_TICKS: 150,\n  BOSS_BOOM_EVERY: 12,\n")
open(p,'w',encoding='utf8').write(s)
p='js/logic/world.js'; s=open(p,encoding='utf8').read()
s=s.replace("""    world.original = world.tiles.slice();""","""    // The arena's open area starts below its ceiling; apples drop from there.
    world.arenaTop = 0;
    if (world.gateCol >= 0) {
      var r0 = 0;
      while (r0 < h && P.isSolid(world.tiles[r0 * w + world.gateCol + 1])) r0++;
      world.arenaTop = r0 * T;
    }
    world.original = world.tiles.slice();""")
open(p,'w',encoding='utf8').write(s)
EOF
grep -n "arenaTop\|BOOM" js/logic/*.js

OUT
js/logic/boss.js:46:    var top = state.world.arenaTop;
js/logic/boss.js:81:      if (b.timer % C.BOSS_BOOM_EVERY === 0) {
js/logic/constants.js:128:  BOSS_BOOM_EVERY: 12,
js/logic/world.js:85:    world.arenaTop = 0;
js/logic/world.js:89:      world.arenaTop = r0 * T;
8:34 PM
Now the game state machine that ties it together.



Write C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\js\logic\game.js
262 lines
// Game state machine: title, playing, paused, confirm-restart, dying, game over, win.
// Owns projectiles and every player-vs-world interaction. Pure logic.
var Game = (function () {
  'use strict';
  var C = typeof CONST !== 'undefined' ? CONST : require('./constants.js').CONST;
  var P = typeof Physics !== 'undefined' ? Physics : require('./physics.js').Physics;
  var W = typeof World !== 'undefined' ? World : require('./world.js').World;
  var E = typeof Enemies !== 'undefined' ? Enemies : require('./enemies.js').Enemies;
  var PL = typeof Player !== 'undefined' ? Player : require('./player.js').Player;
  var B = typeof Boss !== 'undefined' ? Boss : require('./boss.js').Boss;
  var T = C.TILE;
  var DEFAULT_SEED = 20261009;

  function create(level, opts) {
    opts = opts || {};
    var state = {
      level: level, world: W.build(level), mode: 'title', events: [], frame: 0, time: 0,
      score: 0, lives: C.START_LIVES, best: opts.best || 0, seed: opts.seed || DEFAULT_SEED,
      collected: {}, checkpoint: -1, extraLifeAwarded: false, screenTimer: C.SCREEN_INPUT_DELAY,
      deathTimer: 0, maxSection: 0, arenaLocked: false, winBonus: 0, continues: 0, deaths: 0
    };
    state.rngState = state.seed;
    placeAtCheckpoint(state);
    return state;
  }

  function spawnPoint(state) {
    var world = state.world;
    if (state.checkpoint < 0) return world.start;
    var cp = world.checkpoints[state.checkpoint];
    return { x: cp.x + cp.w / 2 - C.PLAYER_W / 2, y: cp.y + cp.h - C.PLAYER_H };
  }

  // Rebuilds everything that resets on a lost life: tiles, enemies, boss, gate.
  // Collected items, score and checkpoint progress survive.
  function placeAtCheckpoint(state) {
    var world = state.world;
    W.resetTiles(world);
    var sp = spawnPoint(state);
    state.player = PL.create(sp.x, sp.y);
    state.enemies = E.spawnAll(world);
    state.projectiles = [];
    state.boss = B.create(world);
    state.warp = world.warp ? { x: world.warp.x, y: world.warp.y, w: world.warp.w, h: world.warp.h, active: false } : null;
    state.arenaLocked = false;
    state.rngState = state.seed;
  }

  function newRun(state) {
    state.score = 0;
    state.lives = C.START_LIVES;
    state.time = 0;
    state.collected = {};
    state.checkpoint = -1;
    state.extraLifeAwarded = false;
    state.maxSection = 0;
    state.continues = 0;
    state.deaths = 0;
    state.winBonus = 0;
    placeAtCheckpoint(state);
    state.mode = 'playing';
    W.emit(state, 'start', state.player.x, state.player.y);
    W.emit(state, 'section', 0, 0, { name: state.world.sections[0].name });
  }

  function respawn(state) {
    placeAtCheckpoint(state);
    state.player.invuln = C.RESPAWN_INVULN_TICKS;
    state.mode = 'playing';
    W.emit(state, 'respawn', state.player.x, state.player.y);
  }

  function continueRun(state) {
    state.lives = C.START_LIVES;
    state.score = 0;
    state.extraLifeAwarded = false;
    state.continues++;
    respawn(state);
  }

  function update(state, input) {
    state.events.length = 0;
    state.frame++;
    if (state.screenTimer > 0) state.screenTimer--;
    var ready = state.screenTimer === 0;
    switch (state.mode) {
      case 'title':
        if (ready && input.jumpPressed) newRun(state);
        break;
      case 'playing':
        if (input.pausePressed) { state.mode = 'paused'; W.emit(state, 'pause'); }
        else if (input.restartPressed) { state.mode = 'confirm'; W.emit(state, 'pause'); }
        else step(state, input);
        break;
      case 'paused':
        if (input.pausePressed) { state.mode = 'playing'; W.emit(state, 'resume'); }
        else if (input.restartPressed) state.mode = 'confirm';
        break;
      case 'confirm':
        if (input.restartPressed) newRun(state);
        else if (input.pausePressed) { state.mode = 'playing'; W.emit(state, 'resume'); }
        break;
      case 'dying':
        if (--state.deathTimer <= 0) loseLife(state);
        break;
      case 'gameover':
        if (ready && input.jumpPressed) continueRun(state);
        else if (ready && input.restartPressed) newRun(state);
        break;
      case 'win':
        if (ready && (input.jumpPressed || input.restartPressed)) newRun(state);
        break;
    }
  }

  function loseLife(state) {
    state.lives -= 1;
    state.deaths += 1;
    if (state.lives <= 0) {
      state.mode = 'gameover';
      state.best = Math.max(state.best, state.score);
      state.screenTimer = C.SCREEN_INPUT_DELAY;
      W.emit(state, 'gameOver');
    } else {
      respawn(state);
    }
  }

  function step(state, input) {
    state.time++;
    PL.update(state, input);
    PL.applyInhale(state);
    E.update(state);
    B.update(state);
    updateProjectiles(state);
    interact(state);
    E.removeDead(state);
  }

  function starHitsTiles(state, pr) {
    var world = state.world;
    var c0 = Math.floor(pr.x / T), c1 = Math.floor((pr.x + pr.w - 1) / T);
    var r0 = Math.floor(pr.y / T), r1 = Math.floor((pr.y + pr.h - 1) / T);
    for (var c = c0; c <= c1; c++) {
      for (var r = r0; r <= r1; r++) {
        var t = P.tileAt(world, c, r);
        if (t === P.TILES.STAR) {
          P.setTile(world, c, r, P.TILES.EMPTY);
          W.addScore(state, C.SCORE.block);
          W.emit(state, 'blockBreak', c * T + T / 2, r * T + T / 2);
          if (!pr.pierce) pr.dead = true;
        } else if (P.isSolid(t)) {
          pr.dead = true;
        }
      }
    }
    if (pr.dead) W.emit(state, 'starPoof', pr.x + pr.w / 2, pr.y + pr.h / 2);
  }

  function projectileHitsEnemies(state, pr) {
    for (var i = 0; i < state.enemies.length && !pr.dead; i++) {
      var e = state.enemies[i];
      if (e.dead || e.caught || !P.overlaps(pr, e)) continue;
      if (e.type === 'spiky') {
        pr.dead = true;
        W.emit(state, 'clink', pr.x + pr.w / 2, pr.y + pr.h / 2);
      } else if (E.DEFEATABLE[e.type]) {
        E.defeat(state, e);
        if (!pr.pierce) pr.dead = true;
      }
    }
    var b = state.boss;
    if (!pr.dead && b && B.alive(b) && P.overlaps(pr, b)) {
      if (pr.kind === 'star') B.hit(state, pr.power);
      pr.dead = true;
      W.emit(state, 'starPoof', pr.x + pr.w / 2, pr.y + pr.h / 2);
    }
  }

  function updateProjectiles(state) {
    state.projectiles.forEach(function (pr) {
      pr.x += pr.vx;
      if (pr.kind === 'air') pr.vx *= C.AIR_PUFF_DRAG;
      if (pr.kind === 'star') starHitsTiles(state, pr);
      else if (P.solidAtPoint(state.world, pr.x + pr.w / 2, pr.y + pr.h / 2)) pr.dead = true;
      if (!pr.dead) projectileHitsEnemies(state, pr);
      if (--pr.life <= 0 && !pr.dead) {
        pr.dead = true;
        if (pr.kind === 'star') W.emit(state, 'starPoof', pr.x + pr.w / 2, pr.y + pr.h / 2);
      }
    });
    state.projectiles = state.projectiles.filter(function (pr) { return !pr.dead; });
  }

  function collect(state, it) {
    var p = state.player;
    state.collected[it.id] = true;
    if (it.kind === 'star') W.addScore(state, C.SCORE.star);
    if (it.kind === 'food') { p.health = C.MAX_HEALTH; W.addScore(state, C.SCORE.food); }
    if (it.kind === 'oneup') state.lives += 1;
    W.emit(state, 'pickup', it.x + it.w / 2, it.y + it.h / 2, { kind: it.kind });
  }

  function lockArena(state) {
    var world = state.world;
    state.arenaLocked = true;
    for (var r = 0; r < world.groundRow; r++) P.setTile(world, world.gateCol, r, P.TILES.STONE);
    B.wake(state);
    W.emit(state, 'arenaLock', world.gateCol * T, 0);
  }

  function win(state) {
    var seconds = Math.floor(state.time / C.TICKS_PER_SECOND);
    state.winBonus = Math.max(0, C.TIME_BONUS_MAX - seconds * C.TIME_BONUS_PER_SECOND);
    W.addScore(state, state.winBonus);
    state.best = Math.max(state.best, state.score);
    state.mode = 'win';
    state.screenTimer = C.SCREEN_INPUT_DELAY;
    W.emit(state, 'win', state.warp.x, state.warp.y);
  }

  function interact(state) {
    var p = state.player, world = state.world, i;
    if (p.y > world.h * T + C.PIT_MARGIN) { PL.kill(state); return; }
    if (P.onSpikes(world, p)) PL.hurt(state, p.x + p.w / 2 + p.facing);

    for (i = 0; i < state.enemies.length && state.mode === 'playing'; i++) {
      var e = state.enemies[i];
      if (!e.dead && e.harmful && !e.caught && P.overlaps(p, e)) PL.hurt(state, e.x + e.w / 2);
    }
    var b = state.boss;
    if (b && B.alive(b) && state.mode === 'playing' && P.overlaps(p, b)) PL.hurt(state, b.x + b.w / 2);
    if (state.mode !== 'playing') return;

    world.items.forEach(function (it) {
      if (!state.collected[it.id] && P.overlaps(p, it)) collect(state, it);
    });
    world.checkpoints.forEach(function (cp) {
      if (cp.index > state.checkpoint && P.overlaps(p, cp)) {
        state.checkpoint = cp.index;
        W.emit(state, 'checkpoint', cp.x + cp.w / 2, cp.y);
      }
    });
    if (!state.arenaLocked && world.gateCol >= 0 && p.x > world.gateCol * T + C.ARENA_LOCK_OFFSET) lockArena(state);
    if (state.warp && state.warp.active && P.overlaps(p, state.warp)) { win(state); return; }

    var si = W.sectionIndexAt(world, p.x + p.w / 2);
    if (si > state.maxSection) {
      state.maxSection = si;
      W.emit(state, 'section', 0, 0, { name: world.sections[si].name });
    }
  }

  return {
    create: create,
    update: update,
    newRun: newRun
  };
})();

if (typeof module !== 'undefined') module.exports = { Game };
8:36 PM
Next, the level data.



Write C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\js\level.js
93 lines
// Level data. A level is a list of sections laid side by side.
// Every section has solid ground at groundRow except in its gaps; then:
//   ceiling: [fromCol, toCol(excl), bottomRow]  stone from the top of the level down to bottomRow (a cave)
//   fill:    [col, row, width, height, char]   rectangle of one character
//   put:     [col, row, string]                 characters left to right; '.' leaves the cell alone
//   signs:   [col, text]                        a sign post standing on the ground
//   wind:    px/tick push (negative = headwind)
// Tiles:    # ground   = stone   - one-way platform   S star block (inhale or spit to break)   ^ spikes
// Things:   P start    C checkpoint   w walker   f flyer   h hopper   g spiky (bobs)   q spiky (patrols)
//           o point star   T tomato (full health)   1 extra life   A arena gate   B boss   W warp star
// Columns and rows are local to the section. Rows run 0 (top) to height-1.
var LEVEL_1 = {
  name: 'Dream Meadows',
  height: 22,
  groundRow: 18,
  sections: [
    {
      name: 'MEADOW', width: 64, gaps: [[28, 31], [60, 64]],
      fill: [[56, 15, 1, 3, 'S']],
      put: [
        [3, 17, 'P'], [9, 17, '###'], [10, 16, '#'], [15, 17, 'w'],
        [18, 14, '-----'], [18, 13, 'o.o.o'], [36, 17, 'w'], [40, 14, '---'], [40, 13, 'ooo'],
        [44, 17, 'w'], [46, 12, 'f'], [51, 17, 'h'], [61, 13, 'oo']
      ],
      signs: [[5, 'SPACE: JUMP'], [25, 'TAP SPACE IN AIR: FLY'], [33, 'HOLD ENTER: INHALE'],
        [47, 'ENTER: SPIT'], [54, 'INHALE BLOCKS!']]
    },
    {
      name: 'CLIFFS', width: 72, gaps: [[4, 10], [18, 26], [36, 42], [52, 62]],
      fill: [[12, 15, 4, 3, '#'], [28, 14, 5, 4, '#'], [44, 16, 4, 2, '#']],
      put: [
        [1, 17, 'C'], [13, 14, 'h'], [30, 13, 'w'], [46, 15, 'w'], [66, 17, 'w'], [69, 17, 'h'],
        [7, 12, 'f'], [21, 11, 'f'], [24, 14, 'f'], [39, 12, 'f'], [55, 11, 'f'], [59, 14, 'f'],
        [22, 13, 'g'], [57, 12, 'g'],
        [5, 13, 'o.o.o'], [19, 10, 'o.o.o.o'], [37, 11, 'o.o.o'], [53, 9, 'o.o.o.o.o'], [40, 2, '1']
      ],
      signs: [[2, 'FLY OVER THE GAPS']]
    },
    {
      name: 'STAR BLOCK FORT', width: 64, gaps: [[44, 47]],
      ceiling: [[8, 61, 10]],
      fill: [[20, 11, 1, 7, 'S'], [36, 11, 2, 7, 'S'], [56, 11, 1, 7, 'S']],
      put: [
        [2, 17, 'C'], [14, 17, 'w'], [17, 17, 'h'], [26, 17, 'h'], [30, 17, 'w'], [32, 18, '^^^'],
        [23, 16, 'ooo'], [40, 13, 'ooo'], [50, 13, 'f'], [52, 15, 'q'], [58, 17, 'h']
      ],
      signs: [[5, 'SPIT STARS AT WALLS'], [42, 'MOUTH FULL? NO FLYING']]
    },
    {
      name: 'THE CLIMB', width: 48,
      ceiling: [[4, 14, 11]],
      fill: [[22, 7, 26, 11, '#']],
      put: [
        [1, 17, 'C'], [7, 17, 'w'], [11, 17, 'h'],
        [19, 16, '---'], [14, 14, '---'], [19, 12, '---'], [14, 10, '---'], [19, 8, '---'],
        [17, 11, 'q'], [17, 3, 'f'],
        [24, 6, 'ooo'], [28, 6, 'w'], [32, 7, '^^'], [38, 6, 'h'], [44, 6, 'C']
      ]
    },
    {
      name: 'WINDY SKY', width: 72, gaps: [[0, 72]], wind: -0.45,
      fill: [[10, 9, 4, 2, '#'], [28, 7, 4, 2, '#'], [46, 10, 4, 2, '#'], [62, 8, 10, 2, '#']],
      put: [
        [4, 8, '---'], [19, 11, '---'], [22, 6, '---'], [37, 9, '---'], [40, 4, '---'], [55, 7, '---'],
        [8, 5, 'f'], [16, 8, 'f'], [22, 3, 'f'], [26, 11, 'f'], [34, 5, 'f'], [43, 8, 'f'], [51, 4, 'f'], [58, 11, 'f'],
        [18, 6, 'g'], [33, 10, 'g'], [38, 1, 'g'], [50, 7, 'g'], [60, 4, 'g'],
        [11, 8, 'h'], [64, 7, 'w'], [68, 7, 'h'], [25, 5, 'ooo'], [45, 3, 'ooo']
      ]
    },
    {
      name: 'GAUNTLET', width: 64, gaps: [[6, 9], [22, 25], [40, 44]],
      ceiling: [[26, 36, 12]],
      fill: [[30, 13, 1, 5, 'S'], [46, 15, 2, 3, '=']],
      put: [
        [2, 17, 'C'], [11, 17, 'h'], [10, 12, 'f'], [12, 13, 'ooooo'], [16, 16, 'q'], [18, 18, '^^'],
        [23, 13, 'f'], [28, 17, 'w'], [33, 17, 'w'], [37, 17, 'h'], [42, 14, 'g'], [42, 11, 'f'],
        [50, 17, 'h'], [52, 13, 'g'], [54, 17, 'w'], [57, 16, 'T'], [61, 17, 'C']
      ],
      signs: [[59, 'BOSS AHEAD!']]
    },
    {
      name: 'GNARLWOOD ARENA', width: 18,
      ceiling: [[0, 18, 4]],
      fill: [[16, 5, 2, 13, '=']],
      put: [[0, 17, 'A'], [4, 13, '---'], [8, 13, '---'], [12, 17, 'B'], [7, 11, 'W']]
    }
  ]
};

var LEVELS = [LEVEL_1];

if (typeof module !== 'undefined') module.exports = { LEVEL_1, LEVELS };
8:36 PM
Let me dump the parsed level as ASCII to check the layout.



Bash Print ASCII map of the first two sections
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && cat > .tmp/dump.js <<'EOF'
const { World } = require('../js/logic/world.js');
const { LEVEL_1 } = require('../js/level.js');
const w = World.build(LEVEL_1);
const ch = ['.', '#', '=', '-', 'S', '^'];
const grid = [];
for (let r = 0; r < w.h; r++) { let s = ''; for (let c = 0; c < w.w; c++) s += ch[w.tiles[r * w.w + c]]; grid.push(s.split('')); }
const L = { walker: 'w', flyer: 'f', hopper: 'h', spiky: 'g' };
w.spawns.forEach(s => grid[s.row][s.col] = s.patrol ? 'q' : L[s.type]);
w.items.forEach(it => grid[Math.floor(it.y / 16)][Math.floor(it.x / 16)] = it.kind[0]);
w.checkpoints.forEach(cp => grid[Math.floor((cp.y + 23) / 16)][Math.floor(cp.x / 16)] = 'C');
const [from, to] = process.argv.slice(2).map(Number);
console.log('size', w.w, w.h, 'gaps', w.gaps.map(g => [g.x0 / 16, g.x1 / 16].join('-')).join(' '), 'arenaTop', w.arenaTop, 'gate', w.gateCol);
console.log('sections', w.sections.map(s => s.name + '@' + s.x0 / 16).join(', '));
const ruler = Array.from({ length: to - from }, (_, i) => ((from + i) % 10)).join('');
console.log('   ' + ruler);
grid.forEach((row, r) => console.log(String(r).padStart(2) + ' ' + row.slice(from, to).join('')));
EOF
node .tmp/dump.js 0 136

OUT
size 402 22 gaps 28-31 60-64 68-74 82-90 100-106 116-126 180-183 248-320 326-329 342-345 360-364 arenaTop 80 gate 384
sections MEADOW@0, CLIFFS@64, STAR BLOCK FORT@136, THE CLIMB@200, WINDY SKY@248, GAUNTLET@320, GNARLWOOD ARENA@384
   0123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345
 0 ........................................................................................................................................
 1 ........................................................................................................................................
 2 ........................................................................................................o...............................
 3 ........................................................................................................................................
 4 ........................................................................................................................................
 5 ........................................................................................................................................
 6 ........................................................................................................................................
 7 ........................................................................................................................................
 8 ........................................................................................................................................
 9 .....................................................................................................................s.s.s.s.s..........
10 ...................................................................................s.s.s.s..............................................
11 .....................................................................................f...............s.s.s.............f................
12 ..............................................f........................f...............................f.................g..............
13 ..................s.s.s.................sss..................ss......s.s.s............g.......w.........................................
14 ..................-----.................---..................................h..........f...#####..........................f............
15 ........................................................S...................####............#####.............w.........................
16 ..........#.............................................S...................####............#####...........####........................
17 .........###...w....................w.......w......h....S........C..........####............#####...........####..................w..h..
18 ############################...#############################....####......########........##########......##########..........##########
19 ############################...#############################....####......########........##########......##########..........##########
20 ############################...#############################....####......########........##########......##########..........##########
21 ############################...#############################....####......########........##########......##########..........##########
Bash Print ASCII map of the remaining sections
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && node .tmp/dump.js 136 270 | tail -23; node .tmp/dump.js 270 402 | tail -23

OUT
   67890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789
 0 ........=====================================================.......==========........................................................
 1 ........=====================================================.......==========........................................................
 2 ........=====================================================.......==========........................................................
 3 ........=====================================================.......==========...f....................................................
 4 ........=====================================================.......==========........................................................
 5 ........=====================================================.......==========..........................................f.............
 6 ........=====================================================.......==========..........sss.w.........h.....C.....................g...
 7 ........=====================================================.......==========........##########^^##############......................
 8 ........=====================================================.......==========.....---##########################....---....h....f.....
 9 ........=====================================================.......==========........##########################..........####........
10 ........=====================================================.......==========---.....##########################..........####........
11 ....................S...............SS..................S...........==========...q....##########################...................---
12 ....................S...............SS..................S..........................---##########################......................
13 ....................S...............SS..sss.......f.....S.............................##########################......................
14 ....................S...............SS..................S.....................---.....##########################......................
15 ....................S...............SS..............q...S.............................##########################......................
16 ....................S..sss..........SS..................S..........................---##########################......................
17 ..C...........w..h..S.....h...w.....SS..................S.h......C.....w...h..........##########################......................
18 ################################^^^#########...#################################################################......................
19 ############################################...#################################################################......................
20 ############################################...#################################################################......................
21 ############################################...#################################################################......................
   012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901
 0 ............................................................................==========............................==================
 1 ................g...........................................................==========............................==================
 2 ............................................................................==========............................==================
 3 f......................sss..................................................==========............................==================
 4 ..................---........f........g.....................................==========............................==================
 5 ...sss......f...............................................................==========............................................==
 6 ---.........................................................................==========............................................==
 7 ......####..................g....---......w...h.............................==========............................................==
 8 ......####...........f..................##########..........................==========............................................==
 9 ...............---......................##########..........................==========............................................==
10 ...........g............####................................................==========............................................==
11 ....f...................####........f.......................................==========......f.....................................==
12 ............................................................f...............==========............................................==
13 ..............................................................sssss......f......S.....................g...............---.---.....==
14 ................................................................................S...........g.....................................==
15 ................................................................................S...............==................................==
16 ..................................................................q.............S...............==.........f......................==
17 ....................................................C........h................w.S..w...h........==..h...w......C..................==
18 ..................................................######...#########^^##...###############....######################################
19 ..................................................######...#############...###############....######################################
20 ..................................................######...#############...###############....######################################
21 ..................................................######...#############...###############....######################################
8:36 PM
The layout looks right. Before building the renderer, a quick sanity simulation of the logic:



Bash Run a quick headless logic simulation
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && cat > .tmp/sim.js <<'EOF'
const { Game } = require('../js/logic/game.js');
const { LEVEL_1 } = require('../js/level.js');
const s = Game.create(LEVEL_1, {});
const I = (o) => Object.assign({ left: false, right: false, jump: false, action: false, jumpPressed: false, actionPressed: false, pausePressed: false, restartPressed: false }, o);
for (let i = 0; i < 50; i++) Game.update(s, I({}));
Game.update(s, I({ jumpPressed: true, jump: true }));
console.log('mode', s.mode, 'player', s.player.x, s.player.y);
let maxH = 0, y0 = s.player.y;
for (let i = 0; i < 20; i++) Game.update(s, I({}));
// run right
for (let i = 0; i < 120; i++) { Game.update(s, I({ right: true })); }
console.log('after run', s.player.x.toFixed(1), s.player.y, 'vx', s.player.vx, 'onGround', s.player.onGround);
// jump measure
y0 = s.player.y; let minY = y0, t = 0;
Game.update(s, I({ right: false, jump: true, jumpPressed: true }));
while (!s.player.onGround && t < 200) { Game.update(s, I({ jump: true })); minY = Math.min(minY, s.player.y); t++; }
console.log('jump height', y0 - minY, 'airtime', t);
// inhale walker
for (let i = 0; i < 200 && !s.player.mouth; i++) Game.update(s, I({ action: true, actionPressed: i === 0 }));
console.log('mouth', s.player.mouth, 'score', s.score, 'events');
Game.update(s, I({}));
Game.update(s, I({ action: true, actionPressed: true }));
console.log('projectiles', s.projectiles.length, 'mouth', s.player.mouth);
EOF
node .tmp/sim.js

OUT
mode playing player 50 276
after run 132.0 276 vx 0 onGround true
jump height 43.74000000000001 airtime 36
mouth null score 0 events
projectiles 0 mouth null
8:36 PM
Physics behaves as expected (the run stopped at the hill, and the jump height is about 44px). Next, input:



Write C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\js\input.js
73 lines
// Keyboard input. Tracks held keys and presses between fixed-step polls,
// so a tap shorter than one tick is never lost. The tracker itself has no DOM
// dependency (tests feed it key events); attach() wires it to the page.
var KirbyInput = (function () {
  'use strict';

  // Only the keys the game asks for. Utility keys: P/Esc pause, M mute, R restart.
  var BINDINGS = {
    ArrowLeft: 'left', KeyA: 'left',
    ArrowRight: 'right', KeyD: 'right',
    Space: 'jump',
    Enter: 'action',
    KeyP: 'pause', Escape: 'pause',
    KeyM: 'mute',
    KeyR: 'restart'
  };
  var ACTIONS = ['left', 'right', 'jump', 'action', 'pause', 'mute', 'restart'];

  function create() {
    var down = {};
    var pressed = {};

    function held(action) {
      for (var code in down) if (down[code] && BINDINGS[code] === action) return true;
      return false;
    }

    return {
      keyDown: function (code) {
        var action = BINDINGS[code];
        if (!action) return false;
        if (!down[code]) pressed[action] = true;
        down[code] = true;
        return true;
      },
      keyUp: function (code) {
        if (!BINDINGS[code]) return false;
        down[code] = false;
        return true;
      },
      releaseAll: function () {
        down = {};
      },
      // One snapshot per fixed update. Presses are consumed by the poll.
      poll: function () {
        var snap = {};
        ACTIONS.forEach(function (a) {
          snap[a] = held(a) || !!pressed[a];
          snap[a + 'Pressed'] = !!pressed[a];
        });
        pressed = {};
        return snap;
      }
    };
  }

  function attach(input, target, onAnyKey) {
    target.addEventListener('keydown', function (e) {
      if (onAnyKey) onAnyKey();
      if (e.repeat && BINDINGS[e.code]) { e.preventDefault(); return; }
      if (input.keyDown(e.code)) e.preventDefault();
    });
    target.addEventListener('keyup', function (e) {
      if (input.keyUp(e.code)) e.preventDefault();
    });
    target.addEventListener('blur', function () { input.releaseAll(); });
  }

  return { BINDINGS: BINDINGS, create: create, attach: attach };
})();

if (typeof module !== 'undefined') module.exports = { KirbyInput };
8:38 PM
Now the sprites, all drawn in code. This first file holds the palette, a small pixel-buffer helper, and Kirby's animation frames.



Write C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\js\sprites.js
216 lines
// Pixel-art sprites drawn in code: a limited palette, a tiny pixel buffer, and Kirby's frames.
// Every sprite is rasterised once at start-up into an offscreen canvas (plus a mirrored copy).
var Sprites = (function () {
  'use strict';

  // The whole game uses only these colours.
  var PAL = {
    K: '#1d1130', // outline / ink
    p: '#f7a3c6', // Kirby pink
    l: '#ffd6e9', // light pink
    d: '#d65c95', // dark pink
    r: '#e3294f', // red
    w: '#fff7ec', // white
    y: '#ffd83d', // yellow
    o: '#f28330', // orange
    t: '#f4c891', // tan
    b: '#9c5b33', // brown
    B: '#5a321e', // dark brown
    g: '#5cc452', // green
    G: '#2c7a40', // dark green
    s: '#86ccff', // sky
    S: '#cdeeff', // pale sky
    v: '#6d43a6', // purple
    n: '#8a87a8', // stone
    N: '#46435f'  // dark stone
  };

  function Pix(w, h) {
    this.w = w;
    this.h = h;
    this.d = new Array(w * h).fill(null);
  }
  Pix.prototype.set = function (x, y, c) {
    x = Math.floor(x); y = Math.floor(y);
    if (x >= 0 && y >= 0 && x < this.w && y < this.h) this.d[y * this.w + x] = c;
  };
  Pix.prototype.get = function (x, y) {
    if (x < 0 || y < 0 || x >= this.w || y >= this.h) return null;
    return this.d[y * this.w + x];
  };
  Pix.prototype.rect = function (x, y, w, h, c) {
    for (var j = 0; j < h; j++) for (var i = 0; i < w; i++) this.set(x + i, y + j, c);
  };
  // Filled ellipse with optional lower-right shade and upper-left highlight.
  Pix.prototype.ellipse = function (cx, cy, rx, ry, c, shade, light) {
    for (var y = Math.floor(cy - ry); y <= Math.ceil(cy + ry); y++) {
      for (var x = Math.floor(cx - rx); x <= Math.ceil(cx + rx); x++) {
        var nx = (x + 0.5 - cx) / rx, ny = (y + 0.5 - cy) / ry, d = nx * nx + ny * ny;
        if (d > 1) continue;
        var col = c;
        if (shade && nx * 0.45 + ny * 0.9 > 0.6) col = shade;
        if (light && nx * 0.6 + ny * 0.8 < -0.5 && d < 0.7 && d > 0.25) col = light;
        this.set(x, y, col);
      }
    }
  };
  // Filled polygon (even-odd rule), sampled at pixel centres.
  Pix.prototype.poly = function (pts, c) {
    for (var y = 0; y < this.h; y++) {
      for (var x = 0; x < this.w; x++) {
        var px = x + 0.5, py = y + 0.5, inside = false;
        for (var i = 0, j = pts.length - 1; i < pts.length; j = i++) {
          var xi = pts[i][0], yi = pts[i][1], xj = pts[j][0], yj = pts[j][1];
          if ((yi > py) !== (yj > py) && px < (xj - xi) * (py - yi) / (yj - yi) + xi) inside = !inside;
        }
        if (inside) this.set(x, y, c);
      }
    }
  };
  // Draws pixel rows like ['.KK.', 'KyyK'] at (x, y); '.' is transparent.
  Pix.prototype.rows = function (x, y, rows) {
    for (var j = 0; j < rows.length; j++) {
      for (var i = 0; i < rows[j].length; i++) if (rows[j][i] !== '.') this.set(x + i, y + j, rows[j][i]);
    }
  };
  // Adds a 1px outline around everything drawn so far.
  Pix.prototype.outline = function (c) {
    var src = this.d.slice(), w = this.w;
    for (var y = 0; y < this.h; y++) {
      for (var x = 0; x < w; x++) {
        if (src[y * w + x] !== null) continue;
        var n = (x > 0 && src[y * w + x - 1]) || (x < w - 1 && src[y * w + x + 1]) ||
          (y > 0 && src[(y - 1) * w + x]) || (y < this.h - 1 && src[(y + 1) * w + x]);
        if (n) this.d[y * w + x] = c;
      }
    }
  };
  Pix.prototype.toCanvas = function (flip) {
    var cv = document.createElement('canvas');
    cv.width = this.w; cv.height = this.h;
    var ctx = cv.getContext('2d');
    for (var y = 0; y < this.h; y++) {
      for (var x = 0; x < this.w; x++) {
        var c = this.d[y * this.w + x];
        if (!c) continue;
        ctx.fillStyle = PAL[c] || c;
        ctx.fillRect(flip ? this.w - 1 - x : x, y, 1, 1);
      }
    }
    return cv;
  };

  // Five-pointed star outline points.
  function starPoints(cx, cy, outer, inner, rot) {
    var pts = [];
    for (var i = 0; i < 10; i++) {
      var a = rot - Math.PI / 2 + i * Math.PI / 5, r = i % 2 ? inner : outer;
      pts.push([cx + Math.cos(a) * r, cy + Math.sin(a) * r]);
    }
    return pts;
  }

  var cache = {};
  function add(name, pix) {
    cache[name] = { r: pix.toCanvas(false), l: pix.toCanvas(true), w: pix.w, h: pix.h };
  }
  function get(name) {
    var s = cache[name];
    if (!s) throw new Error('Missing sprite ' + name);
    return s;
  }
  function has(name) {
    return !!cache[name];
  }

  // ---- Kirby (24x24 frames, facing right, feet on the bottom row) ----
  var KS = 24;

  function face(P, cx, cy, rx, o) {
    var ex = Math.round(cx + 1 + (rx - 7) * 0.5), ey = Math.round(cy - 3 - (o.eyeUp || 0));
    var e2 = ex + 3;
    if (o.eyes === 'open') {
      [ex, e2].forEach(function (x) { P.set(x, ey, 'w'); P.set(x, ey + 1, 'K'); P.set(x, ey + 2, 'K'); P.set(x, ey + 3, 'K'); });
    } else if (o.eyes === 'closed') {
      [ex, e2].forEach(function (x) { P.set(x - 1, ey + 2, 'K'); P.set(x, ey + 3, 'K'); P.set(x + 1, ey + 2, 'K'); });
    } else if (o.eyes === 'squint') {
      P.rows(ex - 1, ey + 1, ['K..', '.K.', 'K..']);
      P.rows(e2 - 1, ey + 1, ['..K', '.K.', '..K']);
    } else if (o.eyes === 'x') {
      P.rows(ex - 1, ey, ['K.K', '.K.', 'K.K']);
      P.rows(e2 - 1, ey, ['K.K', '.K.', 'K.K']);
    }
    var by = ey + 4;
    if (o.blush !== false) {
      P.set(ex - 2, by, 'r'); P.set(ex - 3, by, 'r');
      P.set(e2 + 2, by, 'r');
    }
    var mx = ex + 1, my = by;
    if (o.mouth === 'smile') { P.set(mx, my, 'K'); P.set(mx + 1, my, 'K'); }
    else if (o.mouth === 'o') P.rows(mx, my - 1, ['KK', 'rr', 'KK']);
    else if (o.mouth === 'wail') P.rows(mx, my, ['KK', 'rK']);
    else if (o.mouth === 'full') P.rows(mx - 1, my, ['K.K', '.K.']);
    else if (o.mouth === 'puff') P.set(mx + 1, my, 'K');
  }

  function kirby(o) {
    var P = new Pix(KS, KS);
    var rx = o.rx || 7, ry = o.ry || 7, lift = o.lift || 0;
    var cx = 12 + (o.dx || 0), cy = 22.5 - lift - ry - (o.feetGap || 0);
    (o.feet || [[-4, 0], [3, 0]]).forEach(function (f) { P.ellipse(cx + f[0], 21.6 + f[1], o.footR || 3.2, 1.7, 'r'); });
    var arms = o.arms || [[-rx + 0.5, 1.5], [rx - 0.5, 1.5]];
    P.ellipse(cx + arms[0][0], cy + arms[0][1], 2.2, 1.8, 'p', 'd');
    P.ellipse(cx, cy, rx, ry, 'p', 'd', 'l');
    if (o.cheeks) P.ellipse(cx + rx - 2.5, cy + 1.5, 3, 2.6, 'p', 'd');
    P.ellipse(cx + arms[1][0], cy + arms[1][1], 2.2, 1.8, 'p', 'd');
    if (o.bigMouth) {
      var m = o.bigMouth;
      P.ellipse(cx + m[0], cy + m[1], m[2], m[3], 'K');
      P.ellipse(cx + m[0], cy + m[1] + m[3] * 0.5, m[2] * 0.6, m[3] * 0.4, 'r');
    }
    P.outline('K');
    face(P, cx, cy, rx, o);
    return P;
  }

  var KIRBY_FRAMES = {
    idle0: { eyes: 'open', mouth: 'smile' },
    idle1: { rx: 7.5, ry: 6.6, eyes: 'open', mouth: 'smile' },
    blink: { eyes: 'closed', mouth: 'smile' },
    run0: { lift: 1, feet: [[-6, 0], [4, -1]], arms: [[-7, 0], [6, 2]], eyes: 'open', mouth: 'smile' },
    run1: { feet: [[-3, 0], [2, 0]], eyes: 'open', mouth: 'smile' },
    run2: { lift: 1, feet: [[-5, -1], [5, 0]], arms: [[-6, 2], [7, 0]], eyes: 'open', mouth: 'smile' },
    run3: { feet: [[-2, 0], [1, 0]], eyes: 'open', mouth: 'smile' },
    jump: { rx: 6.5, ry: 7.4, feetGap: 1, feet: [[-3, 0], [2, 0]], arms: [[-6, -3], [6, -3]], eyes: 'open', mouth: 'o' },
    fall: { rx: 7.4, ry: 6.8, feetGap: 1, feet: [[-4, 0], [3, 0]], arms: [[-7, -4], [7, -4]], eyes: 'open', mouth: 'smile' },
    fly0: { rx: 9.4, ry: 9, feetGap: 1, footR: 2.6, feet: [[-4, 0], [3, 0]], arms: [[-9.5, -3], [9.5, -3]], eyes: 'open', mouth: 'puff', eyeUp: 1 },
    fly1: { rx: 9.4, ry: 8.6, feetGap: 1, footR: 2.6, feet: [[-4, 0], [3, 0]], arms: [[-9.5, 2.5], [9.5, 2.5]], eyes: 'open', mouth: 'puff', eyeUp: 1 },
    inhale0: { rx: 7.6, ry: 6.8, dx: -1, eyes: 'squint', blush: false, mouth: 'none', bigMouth: [4.5, 1.5, 2.6, 3.2], arms: [[-7, 1], [5, 3]] },
    inhale1: { rx: 7.8, ry: 6.6, dx: -1, eyes: 'squint', blush: false, mouth: 'none', bigMouth: [4.5, 1.5, 3, 3.8], arms: [[-7, 1], [5, 3]] },
    full0: { rx: 9, ry: 7.6, cheeks: true, eyes: 'open', mouth: 'full' },
    full1: { rx: 9.2, ry: 7.3, cheeks: true, lift: 1, feet: [[-5, 0], [4, -1]], eyes: 'open', mouth: 'full' },
    full2: { rx: 9.2, ry: 7.3, cheeks: true, lift: 1, feet: [[-3, -1], [5, 0]], eyes: 'open', mouth: 'full' },
    spit: { rx: 6.6, ry: 7.2, dx: -1, eyes: 'squint', mouth: 'o', arms: [[-6, 0], [6, -1]] },
    hurt: { rx: 7.6, ry: 6.6, eyes: 'x', mouth: 'wail', arms: [[-8, -3], [8, -3]], feet: [[-5, 0], [4, 0]] }
  };

  function buildKirby() {
    for (var name in KIRBY_FRAMES) add('kirby_' + name, kirby(KIRBY_FRAMES[name]));
    // Small head icon for the lives counter.
    var P = new Pix(10, 9);
    P.ellipse(5, 4.5, 4.5, 4, 'p', 'd', 'l');
    P.outline('K');
    P.set(5, 2, 'K'); P.set(5, 3, 'K'); P.set(7, 2, 'K'); P.set(7, 3, 'K'); P.set(3, 5, 'r'); P.set(8, 5, 'r');
    add('icon_life', P);
  }

  var builders = [buildKirby];
  function register(fn) { builders.push(fn); }
  function init() { builders.forEach(function (fn) { fn(); }); }

  return {
    PAL: PAL, Pix: Pix, starPoints: starPoints, add: add, get: get, has: has,
    register: register, init: init, KIRBY_SIZE: KS
  };
})();
8:39 PM
Next, the sprites for enemies, items, tiles, the boss and the background:



Write C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\js\sprites-world.js
318 lines
// World sprites drawn in code: tiles, enemies, items, the boss and background pieces.
(function () {
  'use strict';
  var Pix = Sprites.Pix, add = Sprites.add, starPoints = Sprites.starPoints;

  // Deterministic per-pixel noise so textures look hand-placed but never change.
  function hash(x, y) {
    var h = (x * 374761393 + y * 668265263) | 0;
    h = Math.imul(h ^ (h >>> 13), 1274126177);
    return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
  }

  function dirt(P, y0) {
    for (var y = y0; y < 16; y++) {
      for (var x = 0; x < 16; x++) {
        var n = hash(x, y);
        P.set(x, y, n < 0.08 ? 'B' : n > 0.95 ? 't' : 'b');
      }
    }
  }

  function tiles() {
    var P = new Pix(16, 16);
    dirt(P, 0);
    add('tile_dirt', P);

    P = new Pix(16, 16);
    dirt(P, 0);
    P.rect(0, 0, 16, 1, 'G');
    P.rect(0, 1, 16, 3, 'g');
    for (var x = 0; x < 16; x++) {
      P.set(x, 4, 'G');
      if (hash(x, 4) > 0.55) P.set(x, 5, 'G');
      if (hash(x, 1) > 0.8) P.set(x, 1, 'G');
    }
    add('tile_grass', P);

    P = new Pix(16, 16);
    P.rect(0, 0, 16, 16, 'n');
    P.rect(0, 7, 16, 1, 'N'); P.rect(0, 15, 16, 1, 'N');
    P.rect(7, 0, 1, 7, 'N'); P.rect(15, 8, 1, 7, 'N');
    P.rect(0, 0, 7, 1, 'S'); P.rect(8, 8, 7, 1, 'S');
    add('tile_stone', P);

    P = new Pix(16, 16);
    P.ellipse(4, 3.5, 4.5, 3, 'w', 'S');
    P.ellipse(11, 3, 5.5, 3.2, 'w', 'S');
    P.ellipse(8, 5, 7.5, 2.2, 'w', 'S');
    P.outline('n');
    add('tile_platform', P);

    P = new Pix(16, 16);
    P.rect(0, 0, 16, 16, 'o');
    P.rect(1, 1, 14, 1, 'y'); P.rect(1, 1, 1, 14, 'y');
    P.rect(1, 14, 14, 1, 'b'); P.rect(14, 1, 1, 14, 'b');
    P.poly(starPoints(8, 8.3, 6, 2.6, 0), 'y');
    P.set(7, 6, 'w'); P.set(8, 6, 'w');
    for (var i = 0; i < 16; i++) { P.set(i, 0, 'B'); P.set(i, 15, 'B'); P.set(0, i, 'B'); P.set(15, i, 'B'); }
    add('tile_star', P);

    P = new Pix(16, 16);
    dirt(P, 9);
    P.rect(0, 9, 16, 1, 'G');
    for (var s = 0; s < 3; s++) {
      var bx = s * 5 + 0.5;
      P.poly([[bx, 9], [bx + 2.5, 1], [bx + 5, 9]], 'w');
      P.poly([[bx + 2.5, 2], [bx + 5, 9], [bx + 2.5, 9]], 'n');
    }
    add('tile_spikes', P);
  }

  function walker() {
    [0, 1].forEach(function (f) {
      var P = new Pix(16, 16);
      P.ellipse(f ? 5.5 : 4, 14.5, 2.8, 1.6, 'B');
      P.ellipse(f ? 10.5 : 12, 14.5, 2.8, 1.6, 'B');
      P.ellipse(8, 8.5 + (f ? 0.5 : 0), 6.6, 6, 'o', 'b');
      P.ellipse(9.8, 9.2 + (f ? 0.5 : 0), 4.3, 3.6, 't');
      P.rows(7, 0 + f, ['.g.', 'gGg', '.G.']);
      P.outline('K');
      var ey = 7 + f;
      P.set(8, ey, 'K'); P.set(8, ey + 1, 'K'); P.set(11, ey, 'K'); P.set(11, ey + 1, 'K');
      P.set(13, ey + 3, 'r');
      add('walker' + f, P);
    });
  }

  function flyer() {
    [0, 1].forEach(function (f) {
      var P = new Pix(20, 16);
      if (f === 0) { P.ellipse(5, 4.5, 4.2, 2.6, 'w', 'S'); P.ellipse(4, 6.5, 3, 1.6, 'w', 'S'); }
      else { P.ellipse(5, 11.5, 4.2, 2.6, 'w', 'S'); P.ellipse(4, 9.5, 3, 1.6, 'w', 'S'); }
      P.ellipse(11, 8.5, 5.8, 5.2, 'v', 'N');
      P.ellipse(9, 14, 1.6, 1, 'y'); P.ellipse(13, 14, 1.6, 1, 'y');
      P.outline('K');
      P.rows(11, 6, ['ww.ww', 'Kw.Kw']);
      P.rows(10, 5, ['K....K']);
      P.set(13, 10, 'r'); P.set(14, 10, 'r');
      add('flyer' + f, P);
    });
  }

  function hopper() {
    var P = new Pix(16, 18);
    P.ellipse(8, 13, 7.2, 4.8, 'g', 'G');
    P.outline('K');
    P.rows(8, 10, ['ww.ww', 'wK.wK']);
    P.rows(9, 14, ['KKK']);
    add('hopper0', P);
    P = new Pix(16, 18);
    P.ellipse(8, 9.5, 5.2, 7.8, 'g', 'G');
    P.outline('K');
    P.rows(8, 5, ['ww.ww', 'wK.wK', 'wK.wK']);
    P.rows(9, 10, ['.K.', 'KrK']);
    add('hopper1', P);
  }

  function spiky() {
    [0, 1].forEach(function (f) {
      var P = new Pix(20, 20), cx = 10, cy = 10;
      for (var k = 0; k < 8; k++) {
        var a = k * Math.PI / 4 + f * Math.PI / 8;
        P.poly([
          [cx + Math.cos(a) * 9.8, cy + Math.sin(a) * 9.8],
          [cx + Math.cos(a + 0.42) * 5.5, cy + Math.sin(a + 0.42) * 5.5],
          [cx + Math.cos(a - 0.42) * 5.5, cy + Math.sin(a - 0.42) * 5.5]
        ], 'w');
      }
      P.ellipse(cx, cy, 6.2, 6.2, 'N', 'K');
      P.outline('K');
      P.rows(8, 7, ['w.w', 'w.w']);
      P.rows(11, 7, ['w', 'w']);
      P.set(12, 7, 'w'); P.set(12, 8, 'w');
      add('spiky' + f, P);
    });
  }

  function objects() {
    var P = new Pix(12, 12);
    P.ellipse(6, 7, 5.2, 4.7, 'r', 'd', 'l');
    P.rect(6, 0, 1, 3, 'B');
    P.rows(7, 0, ['gg', '.g']);
    P.outline('K');
    add('apple', P);

    P = new Pix(14, 12);
    P.ellipse(5, 6.5, 4.5, 4, 'w', 'S');
    P.ellipse(9.5, 5.5, 4, 4.2, 'w', 'S');
    P.outline('n');
    add('bosspuff', P);

    P = new Pix(10, 10);
    P.ellipse(4, 5, 3.6, 3.2, 'w', 'S');
    P.ellipse(6.5, 4.5, 3, 3, 'w', 'S');
    P.outline('S');
    add('airpuff', P);

    [12, 16].forEach(function (size) {
      for (var f = 0; f < 4; f++) {
        var Q = new Pix(size, size), c = size / 2, rot = f * Math.PI / 10;
        Q.poly(starPoints(c, c + 0.4, c - 0.5, c * 0.45, rot), 'o');
        Q.poly(starPoints(c, c + 0.4, c - 2, c * 0.32, rot), 'y');
        Q.set(c - 1, c - 1, 'w'); Q.set(c, c - 1, 'w');
        Q.outline('K');
        add('spit' + size + '_' + f, Q);
      }
    });

    [1, 0.6, 0.2, 0.6].forEach(function (sx, f) {
      var Q = new Pix(10, 10);
      var pts = starPoints(5, 5.4, 4.6, 2, 0).map(function (p) { return [5 + (p[0] - 5) * sx, p[1]]; });
      Q.poly(pts, 'y');
      if (sx > 0.5) Q.set(4, 4, 'w');
      Q.outline('o');
      add('pointstar' + f, Q);
    });

    P = new Pix(12, 12);
    P.ellipse(6, 7, 5.4, 4.8, 'r', 'd');
    P.rows(3, 1, ['g.g.g', '.ggg.']);
    P.set(3, 5, 'w'); P.set(3, 6, 'w'); P.set(4, 5, 'w');
    P.outline('K');
    add('food', P);

    P = new Pix(12, 12);
    P.ellipse(6, 6.5, 5, 4.6, 'p', 'd', 'l');
    P.outline('K');
    P.rows(5, 4, ['K.K', 'K.K']);
    P.set(3, 7, 'r'); P.set(9, 7, 'r');
    P.rows(0, 0, ['y']); P.rows(11, 1, ['y']);
    add('oneup', P);

    P = new Pix(16, 16);
    P.rect(7, 8, 2, 8, 'B');
    P.rect(1, 1, 14, 8, 'b');
    P.rect(2, 2, 12, 1, 't');
    P.rect(3, 4, 7, 1, 'B'); P.rect(3, 6, 9, 1, 'B');
    P.outline('K');
    add('sign', P);
  }

  function markers() {
    ['off', 'on0', 'on1'].forEach(function (name, f) {
      var P = new Pix(14, 26);
      P.rect(2, 2, 2, 24, 'N');
      P.rect(2, 2, 1, 24, 'n');
      var col = f === 0 ? 'n' : 'y', shade = f === 0 ? 'N' : 'o';
      var wave = f === 2 ? 1 : 0;
      P.poly([[4, 3], [13, 5 + wave], [13, 10 + wave], [4, 11]], col);
      P.rect(4, 10, 9, 1, shade);
      if (f > 0) P.poly(starPoints(8.5, 7.3 + wave * 0.5, 2.6, 1.1, 0), 'w');
      P.ellipse(3, 2, 2, 2, 'y', 'o');
      P.outline('K');
      add('checkpoint_' + name, P);
    });

    [0, 1].forEach(function (f) {
      var P = new Pix(28, 28);
      P.poly(starPoints(14, 15, 13 - f * 0.5, 6, f * 0.06), 'o');
      P.poly(starPoints(14, 15, 11 - f * 0.5, 5, f * 0.06), 'y');
      P.ellipse(10, 11, 2, 1.5, 'w');
      P.outline('K');
      P.rows(12, 13, ['K..K', 'K..K']);
      P.rows(13, 16, ['rr']);
      add('warp' + f, P);
    });
  }

  function boss() {
    ['idle', 'blow', 'hurt', 'dead'].forEach(function (mode) {
      var P = new Pix(80, 120);
      // Canopy
      P.ellipse(40, 34, 38, 26, 'g', 'G');
      P.ellipse(16, 46, 15, 12, 'g', 'G');
      P.ellipse(64, 46, 15, 12, 'g', 'G');
      P.ellipse(40, 12, 22, 11, 'g', 'G');
      for (var i = 0; i < 40; i++) {
        var lx = Math.floor(hash(i, 7) * 76) + 2, ly = Math.floor(hash(i, 9) * 56) + 4;
        if (P.get(lx, ly) === 'g') P.set(lx, ly, 'G');
      }
      // Trunk with flared roots
      P.rect(21, 52, 38, 68, 'b');
      P.poly([[21, 104], [8, 120], [24, 120]], 'b');
      P.poly([[59, 104], [72, 120], [56, 120]], 'b');
      for (var b = 0; b < 9; b++) {
        var bx = 23 + Math.floor(hash(b, 3) * 34), by = 56 + Math.floor(hash(b, 5) * 50), len = 4 + Math.floor(hash(b, 11) * 8);
        P.rect(bx, by, 1, len, 'B');
      }
      P.rect(21, 52, 2, 68, 'B');
      P.rect(57, 52, 2, 68, 'd');
      P.outline('K');
      // Face
      if (mode === 'dead') {
        P.rows(30, 74, ['K...K', '.K.K.', '..K..', '.K.K.', 'K...K']);
        P.rows(45, 74, ['K...K', '.K.K.', '..K..', '.K.K.', 'K...K']);
      } else if (mode === 'hurt') {
        P.rows(29, 76, ['KKK...', '...KKK']);
        P.rows(45, 76, ['...KKK', 'KKK...']);
      } else {
        P.rows(28, 70, ['KKKK....', '....KKKK']);
        P.rows(44, 70, ['....KKKK', 'KKKK....']);
        P.ellipse(32, 79, 2.6, 4, 'K'); P.ellipse(48, 79, 2.6, 4, 'K');
        P.set(31, 77, 'w'); P.set(47, 77, 'w');
      }
      if (mode === 'blow') { P.ellipse(40, 97, 5, 6, 'K'); P.ellipse(40, 99, 3, 3, 'B'); }
      else if (mode === 'hurt' || mode === 'dead') P.rows(33, 95, ['K.K.K.K.K.K.K.', '.K.K.K.K.K.K.K']);
      else P.rows(33, 96, ['.KKKKKKKKKKKK.', 'K............K']);
      // Apples hanging in the canopy
      [[14, 40], [62, 38], [30, 18], [52, 22]].forEach(function (a) {
        P.ellipse(a[0], a[1], 3, 3, 'r', 'd');
        P.set(a[0] - 1, a[1] - 1, 'l');
      });
      add('boss_' + mode, P);
    });
  }

  function background() {
    var P = new Pix(256, 72);
    for (var x = 0; x < 256; x++) {
      var hgt = 40 + Math.sin(x / 256 * Math.PI * 4) * 14 + Math.sin(x / 256 * Math.PI * 10) * 6;
      for (var y = Math.floor(72 - hgt); y < 72; y++) P.set(x, y, 'S');
    }
    add('bg_far', P);

    P = new Pix(256, 56);
    for (var x2 = 0; x2 < 256; x2++) {
      var h2 = 30 + Math.sin(x2 / 256 * Math.PI * 6 + 1) * 12 + Math.sin(x2 / 256 * Math.PI * 2) * 6;
      for (var y2 = Math.floor(56 - h2); y2 < 56; y2++) P.set(x2, y2, y2 < 56 - h2 + 2 ? 'G' : 'g');
    }
    for (var t = 0; t < 7; t++) {
      var tx = 18 + t * 37, base = 56 - (30 + Math.sin(tx / 256 * Math.PI * 6 + 1) * 12 + Math.sin(tx / 256 * Math.PI * 2) * 6);
      P.rect(tx, base - 6, 2, 8, 'B');
      P.ellipse(tx + 1, base - 9, 5, 5, 'G');
    }
    add('bg_hills', P);

    P = new Pix(48, 20);
    P.ellipse(14, 12, 12, 7, 'w', 'S');
    P.ellipse(28, 9, 13, 9, 'w', 'S');
    P.ellipse(38, 13, 9, 6, 'w', 'S');
    add('bg_cloud', P);

    P = new Pix(12, 3);
    P.rect(0, 1, 12, 1, 'w'); P.rect(3, 0, 5, 1, 'S'); P.rect(6, 2, 4, 1, 'S');
    add('wind_streak', P);
  }

  Sprites.register(tiles);
  Sprites.register(walker);
  Sprites.register(flyer);
  Sprites.register(hopper);
  Sprites.register(spiky);
  Sprites.register(objects);
  Sprites.register(markers);
  Sprites.register(boss);
  Sprites.register(background);
})();
8:41 PM
Now the HUD (with a hand-made 3×5 pixel font) and the screens:



Write C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\js\hud.js
217 lines
// Pixel font, HUD, controls bar and the full-screen overlays (title, pause, game over, win).
var Font = (function () {
  'use strict';
  var G = {
    'A': '.#./#.#/###/#.#/#.#', 'B': '##./#.#/##./#.#/##.', 'C': '.##/#../#../#../.##', 'D': '##./#.#/#.#/#.#/##.',
    'E': '###/#../##./#../###', 'F': '###/#../##./#../#..', 'G': '.##/#../#.#/#.#/.##', 'H': '#.#/#.#/###/#.#/#.#',
    'I': '###/.#./.#./.#./###', 'J': '..#/..#/..#/#.#/.#.', 'K': '#.#/#.#/##./#.#/#.#', 'L': '#../#../#../#../###',
    'M': '#.#/###/###/#.#/#.#', 'N': '##./#.#/#.#/#.#/#.#', 'O': '.#./#.#/#.#/#.#/.#.', 'P': '##./#.#/##./#../#..',
    'Q': '.#./#.#/#.#/##./.##', 'R': '##./#.#/##./#.#/#.#', 'S': '.##/#../.#./..#/##.', 'T': '###/.#./.#./.#./.#.',
    'U': '#.#/#.#/#.#/#.#/###', 'V': '#.#/#.#/#.#/#.#/.#.', 'W': '#.#/#.#/###/###/#.#', 'X': '#.#/#.#/.#./#.#/#.#',
    'Y': '#.#/#.#/.#./.#./.#.', 'Z': '###/..#/.#./#../###',
    '0': '###/#.#/#.#/#.#/###', '1': '.#./##./.#./.#./###', '2': '##./..#/.#./#../###', '3': '##./..#/.#./..#/##.',
    '4': '#.#/#.#/###/..#/..#', '5': '###/#../##./..#/##.', '6': '.##/#../###/#.#/###', '7': '###/..#/.#./.#./.#.',
    '8': '###/#.#/###/#.#/###', '9': '###/#.#/###/..#/##.',
    '.': './././././#', ',': '../../../.#/#.', '!': '#/#/#/./#', '?': '##./..#/.#./.../.#.', ':': './#/./#/.',
    '-': '.../.../###/.../...', '+': '.../.#./###/.#./...', '/': '..#/..#/.#./#../#..', "'": '#/#/././.',
    '(': '.#/#./#./#./.#', ')': '#./.#/.#/.#/#.', '<': '..#/.#./#../.#./..#', '>': '#../.#./..#/.#./#..',
    '=': '.../###/.../###/...', '*': '.../#.#/.#./#.#/...', '%': '#.#/..#/.#./#../#.#', '"': '#.#/#.#/.../.../...',
    '←': '..#../.##../#####/.##../..#..', '→': '..#../..##./#####/..##./..#..',
    '♥': '.#.#./#####/#####/.###./..#..',
    ' ': '../../../../..'
  };
  var glyphs = {};
  for (var ch in G) glyphs[ch] = G[ch].split('/');
  var cache = {};

  function glyph(ch, color) {
    var key = ch + color;
    if (cache[key]) return cache[key];
    var rows = glyphs[ch] || glyphs['?'];
    var cv = document.createElement('canvas');
    cv.width = rows[0].length; cv.height = 5;
    var g = cv.getContext('2d');
    g.fillStyle = Sprites.PAL[color] || color;
    rows.forEach(function (r, y) { for (var x = 0; x < r.length; x++) if (r[x] === '#') g.fillRect(x, y, 1, 1); });
    cache[key] = cv;
    return cv;
  }

  function measure(text, scale) {
    var w = 0;
    for (var i = 0; i < text.length; i++) w += ((glyphs[text[i]] || glyphs['?'])[0].length + 1) * (scale || 1);
    return Math.max(0, w - (scale || 1));
  }

  // align: 'left' | 'center' | 'right'. shadow: optional colour drawn 1px down-right.
  function draw(ctx, text, x, y, color, opts) {
    opts = opts || {};
    var s = opts.scale || 1;
    text = String(text).toUpperCase();
    var w = measure(text, s);
    var x0 = Math.round(opts.align === 'center' ? x - w / 2 : opts.align === 'right' ? x - w : x);
    y = Math.round(y);
    if (opts.shadow) draw(ctx, text, x0 + s, y + s, opts.shadow, { scale: s });
    for (var i = 0; i < text.length; i++) {
      var g = glyph(text[i], color);
      ctx.drawImage(g, x0, y, g.width * s, g.height * s);
      x0 += (g.width + 1) * s;
    }
    return w;
  }

  // Draws [text, colour] runs one after another.
  function runs(ctx, parts, x, y, align) {
    var total = parts.reduce(function (s, p) { return s + measure(p[0].toUpperCase()) + 1; }, -1);
    var cx = align === 'center' ? Math.round(x - total / 2) : x;
    parts.forEach(function (p) { cx += draw(ctx, p[0], cx, y, p[1]) + 1; });
  }

  return { draw: draw, measure: measure, runs: runs };
})();

var Hud = (function () {
  'use strict';
  var C = CONST, PAL = Sprites.PAL, VW = C.VIEW_W, VH = C.VIEW_H;

  function pad(n, len) {
    var s = String(Math.max(0, Math.floor(n)));
    while (s.length < len) s = '0' + s;
    return s;
  }

  function clock(ticks) {
    var sec = Math.floor(ticks / C.TICKS_PER_SECOND);
    return Math.floor(sec / 60) + ':' + pad(sec % 60, 2);
  }

  function panel(ctx, x, y, w, h, alpha) {
    ctx.globalAlpha = alpha === undefined ? 0.8 : alpha;
    ctx.fillStyle = PAL.K;
    ctx.fillRect(x, y, w, h);
    ctx.globalAlpha = 1;
  }

  function topBar(ctx, state, opts) {
    var p = state.player;
    panel(ctx, 0, 0, VW, 11, 0.6);
    for (var i = 0; i < C.MAX_HEALTH; i++) {
      var x = 3 + i * 7, full = i < p.health;
      ctx.fillStyle = PAL.K; ctx.fillRect(x, 2, 6, 7);
      ctx.fillStyle = full ? PAL.p : PAL.N; ctx.fillRect(x + 1, 3, 4, 5);
      if (full) { ctx.fillStyle = PAL.l; ctx.fillRect(x + 1, 3, 2, 1); }
    }
    ctx.drawImage(Sprites.get('icon_life').r, 50, 1);
    Font.draw(ctx, '*' + state.lives, 61, 3, 'w');
    if (p.mouth) Font.runs(ctx, [['MOUTH FULL', 'y']], 78, 3);
    Font.runs(ctx, [['SCORE ', 'S'], [pad(state.score, 6), 'w']], 162, 3);
    if (opts.muted) Font.draw(ctx, 'MUTED', 252, 13, 'n', { align: 'right' });
    var b = state.boss;
    if (b && b.state !== 'dormant' && b.state !== 'dead') {
      panel(ctx, 128, 11, 128, 9, 0.6);
      Font.draw(ctx, 'GNARLWOOD', 132, 13, 'g');
      for (var k = 0; k < C.BOSS_HP; k++) {
        ctx.fillStyle = PAL.K; ctx.fillRect(172 + k * 13, 13, 12, 5);
        ctx.fillStyle = k < b.hp ? PAL.r : PAL.N; ctx.fillRect(173 + k * 13, 14, 10, 3);
      }
    }
  }

  function controlsBar(ctx) {
    panel(ctx, 0, VH - 9, VW, 9, 0.6);
    Font.runs(ctx, [
      ['←→/AD', 'y'], ['MOVE ', 'w'], ['SPACE', 'y'], ['JUMP/FLY ', 'w'],
      ['ENTER', 'y'], ['INHALE/SPIT ', 'w'], ['P', 'y'], ['PAUSE ', 'w'], ['M', 'y'], ['MUTE', 'w']
    ], VW / 2, VH - 7, 'center');
  }

  function banner(ctx, text, timer) {
    var a = Math.min(1, timer / 20, (C.BANNER_TICKS - timer) / 15);
    if (a <= 0) return;
    ctx.globalAlpha = a;
    var w = Font.measure(text, 2) + 16;
    panel(ctx, VW / 2 - w / 2, 34, w, 18, 0.75);
    ctx.globalAlpha = a;
    Font.draw(ctx, text, VW / 2, 38, 'y', { scale: 2, align: 'center', shadow: 'K' });
    ctx.globalAlpha = 1;
  }

  function dim(ctx, alpha) {
    panel(ctx, 0, 0, VW, VH, alpha);
  }

  function blink(state) {
    return Math.floor(state.frame / 30) % 2 === 0;
  }

  function title(ctx, state) {
    dim(ctx, 0.45);
    Font.draw(ctx, 'KIRBY', VW / 2, 22, 'p', { scale: 5, align: 'center', shadow: 'K' });
    Font.draw(ctx, 'DREAM MEADOWS', VW / 2, 52, 'y', { scale: 2, align: 'center', shadow: 'K' });
    var frame = Math.floor(state.frame / 32) % 2 ? 'kirby_idle1' : 'kirby_idle0';
    if (state.frame % 200 < 8) frame = 'kirby_blink';
    ctx.drawImage(Sprites.get(frame).r, VW / 2 - 24, 66, 48, 48);
    panel(ctx, 20, 118, VW - 40, 64, 0.75);
    var rows = [
      [['← →  OR  A D', 'y'], [' MOVE', 'w']],
      [['SPACE', 'y'], [' JUMP - TAP AGAIN IN THE AIR TO FLY', 'w']],
      [['ENTER', 'y'], [' HOLD TO INHALE, PRESS TO SPIT', 'w']],
      [['P/ESC', 'y'], [' PAUSE  ', 'w'], ['M', 'y'], [' MUTE  ', 'w'], ['R', 'y'], [' RESTART', 'w']]
    ];
    rows.forEach(function (r, i) { Font.runs(ctx, r, VW / 2, 124 + i * 9, 'center'); });
    Font.draw(ctx, 'MOUTH FULL? YOU CAN\'T FLY - SPIT FIRST!', VW / 2, 166, 'S', { align: 'center' });
    if (blink(state)) Font.draw(ctx, 'PRESS SPACE TO START', VW / 2, 190, 'w', { scale: 1, align: 'center', shadow: 'K' });
    if (state.best) Font.draw(ctx, 'BEST ' + pad(state.best, 6), VW / 2, 202, 'y', { align: 'center', shadow: 'K' });
  }

  function centerBox(ctx, lines, y) {
    var h = lines.length * 10 + 8;
    panel(ctx, 24, y, VW - 48, h, 0.8);
    lines.forEach(function (l, i) {
      Font.draw(ctx, l[0], VW / 2, y + 6 + i * 10, l[1] || 'w', { align: 'center' });
    });
  }

  function overlays(ctx, state) {
    var m = state.mode;
    if (m === 'title') title(ctx, state);
    else if (m === 'paused') {
      dim(ctx, 0.5);
      Font.draw(ctx, 'PAUSED', VW / 2, 70, 'w', { scale: 3, align: 'center', shadow: 'K' });
      centerBox(ctx, [['P / ESC: RESUME'], ['R: RESTART'], ['M: MUTE']], 100);
    } else if (m === 'confirm') {
      dim(ctx, 0.6);
      centerBox(ctx, [['RESTART FROM THE BEGINNING?', 'y'], [''], ['R: YES      P / ESC: NO']], 90);
    } else if (m === 'gameover') {
      dim(ctx, 0.7);
      Font.draw(ctx, 'GAME OVER', VW / 2, 56, 'r', { scale: 3, align: 'center', shadow: 'K' });
      Font.draw(ctx, 'SCORE ' + pad(state.score, 6), VW / 2, 84, 'w', { align: 'center' });
      if (state.screenTimer === 0) {
        centerBox(ctx, [['SPACE: CONTINUE FROM CHECKPOINT', 'y'], ['(SCORE RESETS TO 0)', 'n'], [''],
          ['R: RESTART FROM THE BEGINNING']], 104);
      }
    } else if (m === 'win') {
      dim(ctx, 0.55);
      Font.draw(ctx, 'YOU WIN!', VW / 2, 40, 'y', { scale: 3, align: 'center', shadow: 'K' });
      var lines = [
        ['TIME        ' + clock(state.time)], ['TIME BONUS  ' + pad(state.winBonus, 6)],
        ['SCORE       ' + pad(state.score, 6), 'y'], ['BEST        ' + pad(state.best, 6), 'p']
      ];
      if (state.continues) lines.push(['CONTINUES   ' + state.continues, 'n']);
      centerBox(ctx, lines, 72);
      if (state.screenTimer === 0 && blink(state)) {
        Font.draw(ctx, 'PRESS SPACE TO PLAY AGAIN', VW / 2, 150, 'w', { align: 'center', shadow: 'K' });
      }
    }
  }

  function draw(ctx, state, opts) {
    if (state.mode !== 'title') topBar(ctx, state, opts);
    controlsBar(ctx);
    if (opts.banner) banner(ctx, opts.banner.text, opts.banner.timer);
    overlays(ctx, state);
  }

  return { draw: draw, pad: pad, clock: clock };
})();
8:41 PM
Now the renderer:



Write C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\js\render.js
340 lines
// Draws the game state. Owns only visual state: camera, particles, floating text, shake, banners.
var Renderer = (function () {
  'use strict';
  var C = CONST, T = C.TILE, VW = C.VIEW_W, VH = C.VIEW_H;
  var TL = Physics.TILES, PAL = Sprites.PAL;

  // Visual-only tuning (camera feel and effects); gameplay numbers live in CONST.
  var FX = {
    CAM_LERP: 0.12, CAM_LEAD: 28, CAM_LEAD_SPEED: 0.8, CAM_Y_OFFSET: 130,
    SHAKE_DECAY: 0.85, FLOATER_TICKS: 50, NOFLY_COOLDOWN: 60, WIND_STREAKS: 14
  };

  var ctx = null;
  var cam = { x: 0, y: 0, lead: FX.CAM_LEAD, shake: 0 };
  var particles = [], floaters = [], banner = null, flash = 0, noFlyCooldown = 0;
  var windStreaks = [];

  function init(context) {
    ctx = context;
    for (var i = 0; i < FX.WIND_STREAKS; i++) windStreaks.push({ x: Math.random() * VW, y: Math.random() * VH, s: 2 + Math.random() * 3 });
  }

  function camTarget(state) {
    var p = state.player, world = state.world;
    var minX = state.arenaLocked ? world.gateCol * T : 0;
    var tx = Math.max(minX, Math.min(world.w * T - VW, p.x + p.w / 2 - VW / 2 + cam.lead));
    var ty = Math.max(0, Math.min(world.h * T - VH, p.y + p.h / 2 - FX.CAM_Y_OFFSET));
    return { x: tx, y: ty };
  }

  function snapCamera(state) {
    cam.lead = state.player.facing * FX.CAM_LEAD;
    var t = camTarget(state);
    cam.x = t.x; cam.y = t.y;
  }

  function spawn(x, y, n, opts) {
    for (var i = 0; i < n; i++) {
      var a = (opts.angle !== undefined ? opts.angle : Math.random() * Math.PI * 2) + (Math.random() - 0.5) * (opts.spread || 0);
      var sp = (opts.speed || 1) * (0.5 + Math.random() * 0.8);
      particles.push({
        x: x, y: y, vx: Math.cos(a) * sp, vy: Math.sin(a) * sp, g: opts.g || 0, life: opts.life || 20,
        max: opts.life || 20, color: opts.color || 'w', size: opts.size || 2, sprite: opts.sprite
      });
    }
  }

  function floater(x, y, text, color) {
    floaters.push({ x: x, y: y, text: text, color: color || 'w', life: FX.FLOATER_TICKS });
  }

  function onEvent(ev, state) {
    var x = ev.x, y = ev.y;
    switch (ev.type) {
      case 'start': case 'respawn': snapCamera(state); particles = []; break;
      case 'jump': case 'land': case 'appleLand': spawn(x, y, 4, { angle: -Math.PI / 2, spread: 2.6, speed: 0.8, color: 'S', life: 14 }); break;
      case 'flap': spawn(x, y, 2, { angle: Math.PI / 2, spread: 1.2, speed: 0.7, color: 'w', life: 12 }); break;
      case 'deflate': spawn(x + ev.facing * 8, y, 5, { angle: ev.facing > 0 ? 0 : Math.PI, spread: 1, speed: 1.4, color: 'w', size: 3, life: 14 }); break;
      case 'defeat':
        spawn(x, y, 8, { speed: 1.8, sprite: 'pointstar0', life: 22 });
        floater(x, y - 8, '+' + (C.SCORE[ev.kind] || 0), 'y');
        cam.shake = Math.max(cam.shake, 2);
        break;
      case 'swallow':
        spawn(x, y, 6, { speed: 1.2, color: 'p', life: 12 });
        floater(x, y - 14, ev.count > 1 ? 'BIG STAR!' : 'GULP!', 'p');
        break;
      case 'spit': spawn(x, y, 5, { angle: ev.facing > 0 ? 0 : Math.PI, spread: 1.4, speed: 1.6, color: 'y', life: 12 }); break;
      case 'exhale': break;
      case 'blockGrab': spawn(x, y, 4, { speed: 0.8, color: 'o', life: 12 }); break;
      case 'blockBreak':
        spawn(x, y, 8, { speed: 2, g: 0.15, color: 'o', size: 3, life: 26 });
        spawn(x, y, 4, { speed: 1.5, g: 0.15, color: 'y', size: 2, life: 22 });
        break;
      case 'starPoof': spawn(x, y, 6, { speed: 1.2, color: 'y', life: 12 }); break;
      case 'clink': spawn(x, y, 6, { speed: 1.6, color: 'w', size: 1, life: 10 }); floater(x, y - 10, 'CLINK!', 'n'); break;
      case 'puffPop': spawn(x, y, 5, { speed: 0.9, color: 'w', size: 3, life: 12 }); break;
      case 'hurt': cam.shake = Math.max(cam.shake, 4); flash = 4; spawn(x, y, 8, { speed: 1.8, color: 'r', life: 16 }); break;
      case 'drop': floater(x, y - 12, 'DROPPED IT!', 'n'); break;
      case 'death': cam.shake = 6; break;
      case 'pickup':
        spawn(x, y, 6, { speed: 1.3, color: 'y', life: 16 });
        floater(x, y - 8, ev.kind === 'star' ? '+' + C.SCORE.star : ev.kind === 'food' ? 'HEALTH UP!' : '1UP!', ev.kind === 'star' ? 'y' : 'p');
        break;
      case 'oneUp': floater(x, y - 20, '1UP!', 'p'); break;
      case 'checkpoint': spawn(x, y, 10, { speed: 1.6, sprite: 'pointstar0', life: 24 }); floater(x, y - 8, 'CHECKPOINT!', 'y'); break;
      case 'noFly':
        if (noFlyCooldown === 0) { floater(x, y - 10, 'SPIT FIRST!', 'r'); noFlyCooldown = FX.NOFLY_COOLDOWN; }
        break;
      case 'section': banner = { text: ev.name, timer: C.BANNER_TICKS }; break;
      case 'arenaLock': cam.shake = 6; banner = { text: 'OLD GNARLWOOD', timer: C.BANNER_TICKS }; break;
      case 'bossHit': cam.shake = 6; flash = 3; spawn(x, y, 10, { speed: 2.2, sprite: 'pointstar0', life: 20 }); break;
      case 'bossBoom': spawn(x, y, 6, { speed: 1.5, color: 'w', size: 4, life: 18 }); spawn(x, y, 4, { speed: 1, color: 'y', size: 3, life: 14 }); cam.shake = 3; break;
      case 'bossDefeated': flash = 10; cam.shake = 10; floater(x, y - 30, '+' + C.SCORE.boss, 'y'); break;
      case 'win': spawn(x + 12, y + 12, 24, { speed: 2.5, sprite: 'pointstar0', life: 40 }); break;
    }
  }

  // Called once per fixed update.
  function tick(state) {
    if (state.mode === 'playing' || state.mode === 'dying' || state.mode === 'title' || state.mode === 'win') {
      if (state.mode === 'playing') cam.lead += Math.max(-FX.CAM_LEAD_SPEED, Math.min(FX.CAM_LEAD_SPEED, state.player.facing * FX.CAM_LEAD - cam.lead));
      var t = camTarget(state);
      if (state.mode !== 'dying') {
        cam.x += (t.x - cam.x) * FX.CAM_LERP;
        cam.y += (t.y - cam.y) * FX.CAM_LERP;
      }
    }
    if (state.mode === 'paused' || state.mode === 'confirm') return;
    cam.shake *= FX.SHAKE_DECAY;
    if (cam.shake < 0.3) cam.shake = 0;
    if (flash > 0) flash--;
    if (noFlyCooldown > 0) noFlyCooldown--;
    if (banner && --banner.timer <= 0) banner = null;
    particles.forEach(function (p) { p.x += p.vx; p.y += p.vy; p.vy += p.g; p.life--; });
    particles = particles.filter(function (p) { return p.life > 0; });
    floaters.forEach(function (f) { f.y -= 0.4; f.life--; });
    floaters = floaters.filter(function (f) { return f.life > 0; });
  }

  // Integer camera position for this frame, including shake.
  function view() {
    var sx = cam.shake ? Math.round((Math.random() - 0.5) * cam.shake) : 0;
    var sy = cam.shake ? Math.round((Math.random() - 0.5) * cam.shake) : 0;
    return { x: Math.round(cam.x) + sx, y: Math.round(cam.y) + sy };
  }

  function sprite(name, x, y, flip) {
    var s = Sprites.get(name);
    ctx.drawImage(flip ? s.l : s.r, Math.round(x), Math.round(y));
  }

  // Draw a sprite centred on a body horizontally and standing on its bottom edge.
  function onBody(name, b, v, flip, dy) {
    var s = Sprites.get(name);
    sprite(name, b.x + b.w / 2 - s.w / 2 - v.x, b.y + b.h - s.h - v.y + (dy || 0), flip);
  }

  function drawBackground(state, v) {
    var inArena = state.arenaLocked || (state.world.gateCol >= 0 && v.x > state.world.gateCol * T - VW / 2);
    ctx.fillStyle = inArena ? PAL.v : PAL.s;
    ctx.fillRect(0, 0, VW, VH);
    var horizon = VH - 40 - (v.y - (state.world.h * T - VH)) * 0.3;
    var far = Sprites.get('bg_far'), hills = Sprites.get('bg_hills'), cloud = Sprites.get('bg_cloud');
    var fx = -Math.round(v.x * 0.15) % far.w;
    for (var x = fx - far.w; x < VW + far.w; x += far.w) ctx.drawImage(far.r, x, Math.round(horizon - far.h + 10));
    for (var i = 0; i < 6; i++) {
      var cxp = ((i * 113 - v.x * 0.3 - state.frame * 0.05) % 340 + 340) % 340 - 48;
      ctx.drawImage(cloud.r, Math.round(cxp), Math.round(horizon - 120 + (i * 37) % 60));
    }
    var hx = -Math.round(v.x * 0.4) % hills.w;
    for (var x2 = hx - hills.w; x2 < VW + hills.w; x2 += hills.w) ctx.drawImage(hills.r, x2, Math.round(horizon - hills.h + 34));
    ctx.fillStyle = PAL.G;
    ctx.fillRect(0, Math.round(horizon + 34), VW, VH);
  }

  function drawTiles(state, v) {
    var world = state.world;
    state.world.caves.forEach(function (cv) {
      if (cv.x1 < v.x || cv.x0 > v.x + VW) return;
      ctx.fillStyle = PAL.N;
      ctx.fillRect(cv.x0 - v.x, cv.top - v.y, cv.x1 - cv.x0, world.groundRow * T - cv.top);
    });
    var c0 = Math.floor(v.x / T), c1 = Math.floor((v.x + VW) / T);
    var r0 = Math.max(0, Math.floor(v.y / T)), r1 = Math.min(world.h - 1, Math.floor((v.y + VH) / T));
    for (var r = r0; r <= r1; r++) {
      for (var c = c0; c <= c1; c++) {
        var t = Physics.tileAt(world, c, r);
        if (t === TL.EMPTY || c < 0 || c >= world.w) continue;
        var name = 'tile_stone';
        if (t === TL.GROUND) name = Physics.isSolid(Physics.tileAt(world, c, r - 1)) || r === 0 ? 'tile_dirt' : 'tile_grass';
        else if (t === TL.PLATFORM) name = 'tile_platform';
        else if (t === TL.STAR) name = 'tile_star';
        else if (t === TL.SPIKES) name = 'tile_spikes';
        ctx.drawImage(Sprites.get(name).r, c * T - v.x, r * T - v.y);
      }
    }
  }

  function groundBelow(world, x) {
    var c = Math.floor(x / T);
    for (var r = 0; r < world.h; r++) if (Physics.isSolid(Physics.tileAt(world, c, r))) return r * T;
    return world.h * T;
  }

  function drawProps(state, v) {
    var world = state.world, f = state.frame;
    world.signs.forEach(function (s) {
      if (s.x < v.x - 80 || s.x > v.x + VW + 80) return;
      var gy = groundBelow(world, s.x);
      sprite('sign', s.x - 8 - v.x, gy - 16 - v.y);
      var w = Font.measure(s.text) + 6;
      ctx.globalAlpha = 0.75; ctx.fillStyle = PAL.K;
      ctx.fillRect(Math.round(s.x - w / 2 - v.x), gy - 30 - v.y, w, 9);
      ctx.globalAlpha = 1;
      Font.draw(ctx, s.text, s.x - v.x, gy - 28 - v.y, 'w', { align: 'center' });
    });
    world.checkpoints.forEach(function (cp) {
      var on = cp.index <= state.checkpoint;
      sprite(on ? (Math.floor(f / 12) % 2 ? 'checkpoint_on1' : 'checkpoint_on0') : 'checkpoint_off', cp.x - 3 - v.x, cp.y + cp.h - 26 - v.y);
    });
    world.items.forEach(function (it) {
      if (state.collected[it.id] || it.x < v.x - 16 || it.x > v.x + VW) return;
      var bob = Math.round(Math.sin((f + it.id * 9) * 0.08) * 1.5);
      var name = it.kind === 'star' ? 'pointstar' + (Math.floor((f + it.id * 5) / 8) % 4) : it.kind;
      var s = Sprites.get(name);
      sprite(name, it.x + it.w / 2 - s.w / 2 - v.x, it.y + it.h / 2 - s.h / 2 - v.y + bob);
    });
    var wp = state.warp;
    if (wp && wp.active) {
      var wy = Math.round(Math.sin(f * 0.07) * 3);
      sprite('warp' + (Math.floor(f / 10) % 2), wp.x - 2 - v.x, wp.y - 2 - v.y + wy);
      if (f % 6 === 0) spawn(wp.x + 12, wp.y + 12, 1, { speed: 0.6, sprite: 'pointstar0', life: 30 });
    }
  }

  function drawBoss(state, v) {
    var b = state.boss;
    if (!b) return;
    var name = 'boss_idle';
    if (b.state === 'dead' || b.state === 'dying') name = 'boss_dead';
    else if (b.invuln > 0) name = 'boss_hurt';
    else if (b.mouthOpen > 0) name = 'boss_blow';
    if ((b.invuln > 0 || b.state === 'dying') && Math.floor(state.frame / 3) % 2) return;
    var jx = b.state === 'dying' || b.state === 'intro' ? Math.round(Math.sin(state.frame * 1.7) * 1.5) : 0;
    sprite(name, b.x - 20 - v.x + jx, b.y + b.h - 120 - v.y);
  }

  function enemySprite(e, f) {
    switch (e.type) {
      case 'walker': return 'walker' + (Math.floor(e.t / 12) % 2);
      case 'flyer': return 'flyer' + (Math.floor(e.t / 7) % 2);
      case 'hopper': return e.onGround && e.timer < C.HOPPER_WAIT - 12 ? 'hopper0' : 'hopper1';
      case 'spiky': return 'spiky' + (Math.floor(e.t / 10) % 2);
      case 'apple': return 'apple';
      case 'bosspuff': return 'bosspuff';
      default: return e.kind === 'block' ? 'tile_star' : 'spit12_' + (Math.floor(f / 4) % 4);
    }
  }

  function drawEnemies(state, v) {
    state.enemies.forEach(function (e) {
      if (e.x + e.w < v.x - 24 || e.x > v.x + VW + 24) return;
      if (e.type === 'loose' && e.life < 60 && Math.floor(state.frame / 3) % 2) return;
      var jitter = (e.caught || e.stun > 0) ? (Math.floor(state.frame / 2) % 2 ? 1 : -1) : 0;
      var name = enemySprite(e, state.frame);
      var s = Sprites.get(name);
      var cx = e.x + e.w / 2 - v.x + jitter, by = e.y + e.h - v.y;
      if (e.type === 'flyer' || e.type === 'spiky' || e.type === 'bosspuff') by = e.y + e.h / 2 + s.h / 2 - v.y;
      ctx.drawImage(e.facing < 0 ? s.l : s.r, Math.round(cx - s.w / 2), Math.round(by - s.h));
    });
    state.projectiles.forEach(function (pr) {
      var name = pr.kind === 'air' ? 'airpuff' : 'spit' + (pr.big ? 16 : 12) + '_' + (Math.floor(state.frame / 3) % 4);
      sprite(name, pr.x - v.x, pr.y - v.y, pr.vx < 0);
    });
  }

  function kirbyFrame(state) {
    var p = state.player, t = p.animT;
    if (state.mode === 'dying' || p.hurtTimer > 0) return 'hurt';
    if (p.inhaling) return Math.floor(state.frame / 4) % 2 ? 'inhale1' : 'inhale0';
    if (p.spitAnim > 0) return 'spit';
    if (p.flying) return p.flapAnim > C.FLAP_ANIM_TICKS / 2 ? 'fly1' : (p.flapAnim > 0 ? 'fly0' : (Math.floor(t / 16) % 2 ? 'fly0' : 'fly1'));
    if (p.mouth) return p.onGround && Math.abs(p.vx) > 0.2 ? (Math.floor(t / 8) % 2 ? 'full1' : 'full2') : 'full0';
    if (!p.onGround) return p.vy < 0 ? 'jump' : 'fall';
    if (Math.abs(p.vx) > 0.2) return 'run' + (Math.floor(t / 4) % 4);
    if (t % 180 < 6) return 'blink';
    return Math.floor(t / 32) % 2 ? 'idle1' : 'idle0';
  }

  function drawInhaleWind(p, v, f) {
    var m = Player.mouthPoint(p);
    ctx.fillStyle = PAL.w;
    for (var k = 0; k < 7; k++) {
      var d = C.INHALE_RANGE - ((f * 3 + k * 23) % C.INHALE_RANGE);
      var spread = (C.INHALE_HALF_HEIGHT + d * C.INHALE_SPREAD) * (((k * 37) % 11) / 5.5 - 1);
      var x = m.x + p.facing * d - v.x, y = m.y + spread * (d / C.INHALE_RANGE) - v.y;
      ctx.globalAlpha = 0.4 + 0.6 * (1 - d / C.INHALE_RANGE);
      ctx.fillRect(Math.round(x - (p.facing > 0 ? 0 : 4)), Math.round(y), 5, 1);
    }
    ctx.globalAlpha = 1;
  }

  function drawPlayer(state, v) {
    var p = state.player, f = state.frame;
    if (state.mode === 'dying') {
      var dt = C.DEATH_TICKS - state.deathTimer, lift = 0;
      if (dt > 30) { var k = dt - 30; lift = k * 3.5 - 0.09 * k * k; }
      onBody('kirby_hurt', p, v, Math.floor(dt / 8) % 2 === 0, -lift);
      return;
    }
    if (p.invuln > 0 && p.hurtTimer === 0 && Math.floor(f / 3) % 2) return;
    if (p.inhaling) drawInhaleWind(p, v, f);
    onBody('kirby_' + kirbyFrame(state), p, v, p.facing < 0);
  }

  function drawParticles(v) {
    particles.forEach(function (p) {
      if (p.sprite) { var s = Sprites.get(p.sprite); ctx.drawImage(s.r, Math.round(p.x - s.w / 2 - v.x), Math.round(p.y - s.h / 2 - v.y)); return; }
      ctx.fillStyle = PAL[p.color];
      var sz = Math.max(1, Math.round(p.size * (p.life / p.max + 0.3)));
      ctx.fillRect(Math.round(p.x - v.x - sz / 2), Math.round(p.y - v.y - sz / 2), sz, sz);
    });
    floaters.forEach(function (fl) {
      ctx.globalAlpha = Math.min(1, fl.life / 15);
      Font.draw(ctx, fl.text, fl.x - v.x, fl.y - v.y, fl.color, { align: 'center', shadow: 'K' });
    });
    ctx.globalAlpha = 1;
  }

  function drawWind(state, v) {
    var push = World.windAt(state.world, v.x + VW / 2, state.time);
    if (!push) return;
    var s = Sprites.get('wind_streak');
    ctx.globalAlpha = 0.6;
    windStreaks.forEach(function (w) {
      w.x += push * w.s * 2;
      if (w.x < -16) { w.x = VW + Math.random() * 40; w.y = Math.random() * VH; }
      ctx.drawImage(s.r, Math.round(w.x), Math.round(w.y));
    });
    ctx.globalAlpha = 1;
  }

  function draw(state, opts) {
    var v = view();
    drawBackground(state, v);
    drawTiles(state, v);
    drawProps(state, v);
    drawBoss(state, v);
    drawEnemies(state, v);
    if (state.mode !== 'title') drawPlayer(state, v);
    drawParticles(v);
    drawWind(state, v);
    if (flash > 0) { ctx.globalAlpha = flash / 12; ctx.fillStyle = PAL.w; ctx.fillRect(0, 0, VW, VH); ctx.globalAlpha = 1; }
    Hud.draw(ctx, state, { banner: state.mode === 'playing' ? banner : null, muted: opts && opts.muted });
  }

  return { init: init, tick: tick, onEvent: onEvent, draw: draw, snapCamera: snapCamera };
})();
8:43 PM
Now the audio: Web Audio sound effects and two original chiptune loops.



Write C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\js\audio.js
219 lines
// Chiptune sound effects and music, synthesised with Web Audio. No audio files.
// The browser only allows sound after a key press, so unlock() runs on the first key.
var GameAudio = (function () {
  'use strict';
  var VOL = { MASTER: 0.5, SFX: 0.55, MUSIC: 0.2, DUCK: 0.35 };
  var LOOKAHEAD = 0.12, SCHEDULE_MS = 25;

  var ac = null, master = null, sfxBus = null, musicBus = null, noiseBuf = null;
  var muted = false, ducked = false;
  var inhale = null;
  var music = { name: null, song: null, step: 0, next: 0, timer: null };

  // Original tunes. One token per eighth note: note name, '-' holds the previous note, '.' rests.
  var SONGS = {
    level: {
      bpm: 140,
      lead: 'E5 - G5 - C6 - G5 - A5 G5 E5 - D5 - . . F5 - A5 - D6 - A5 - B5 A5 G5 - - - . . ' +
        'E5 - G5 - C6 - E6 - D6 C6 A5 - G5 - E5 - F5 - D5 - G5 - B4 - C5 - - - . . G4 .',
      bass: 'C3 . G3 . C3 . G3 . A2 . E3 . A2 . E3 . D3 . A3 . D3 . A3 . G2 . D3 . G2 . B2 . ' +
        'C3 . G3 . C3 . G3 . F2 . C3 . F2 . C3 . D3 . A2 . G2 . G3 . C3 . G2 . C3 . . .',
      drums: 'k.h.s.h.'
    },
    boss: {
      bpm: 170,
      lead: 'A4 . C5 A4 E5 . D5 C5 B4 . G4 B4 D5 . C5 B4 A4 . C5 A4 E5 . G5 F5 E5 - - D#5 E5 - . .',
      bass: 'A2 A3 A2 A3 A2 A3 A2 A3 G2 G3 G2 G3 G2 G3 G2 G3 F2 F3 F2 F3 F2 F3 F2 F3 E2 E3 E2 E3 E2 E3 B2 E3',
      drums: 'k.hsk.hs'
    }
  };
  var NOTE = { C: 0, 'C#': 1, D: 2, 'D#': 3, E: 4, F: 5, 'F#': 6, G: 7, 'G#': 8, A: 9, 'A#': 10, B: 11 };

  function freq(name) {
    var m = /^([A-G]#?)(\d)$/.exec(name);
    return 440 * Math.pow(2, (NOTE[m[1]] + (Number(m[2]) + 1) * 12 - 69) / 12);
  }

  function parse(song) {
    return {
      bpm: song.bpm,
      lead: song.lead.trim().split(/\s+/),
      bass: song.bass.trim().split(/\s+/),
      drums: song.drums
    };
  }

  function unlock() {
    if (!ac) {
      var Ctor = window.AudioContext || window.webkitAudioContext;
      if (!Ctor) return;
      ac = new Ctor();
      master = ac.createGain();
      master.gain.value = muted ? 0 : VOL.MASTER;
      master.connect(ac.destination);
      sfxBus = ac.createGain(); sfxBus.gain.value = VOL.SFX; sfxBus.connect(master);
      musicBus = ac.createGain(); musicBus.gain.value = VOL.MUSIC; musicBus.connect(master);
      noiseBuf = ac.createBuffer(1, ac.sampleRate, ac.sampleRate);
      var d = noiseBuf.getChannelData(0);
      for (var i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    }
    if (ac.state === 'suspended') ac.resume();
  }

  function env(g, t, vol, dur) {
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(vol, t + 0.005);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  }

  function tone(type, f0, f1, dur, vol, delay, bus, at) {
    if (!ac) return;
    var t = (at || ac.currentTime) + (delay || 0);
    var o = ac.createOscillator(), g = ac.createGain();
    o.type = type;
    o.frequency.setValueAtTime(f0, t);
    if (f1 && f1 !== f0) o.frequency.exponentialRampToValueAtTime(f1, t + dur);
    env(g, t, vol, dur);
    o.connect(g); g.connect(bus || sfxBus);
    o.start(t); o.stop(t + dur + 0.02);
  }

  function noise(dur, vol, f0, f1, delay, bus, at) {
    if (!ac) return;
    var t = (at || ac.currentTime) + (delay || 0);
    var src = ac.createBufferSource(), flt = ac.createBiquadFilter(), g = ac.createGain();
    src.buffer = noiseBuf;
    flt.type = 'bandpass';
    flt.frequency.setValueAtTime(f0, t);
    if (f1) flt.frequency.exponentialRampToValueAtTime(f1, t + dur);
    env(g, t, vol, dur);
    src.connect(flt); flt.connect(g); g.connect(bus || sfxBus);
    src.start(t); src.stop(t + dur + 0.02);
  }

  function arp(notes, step, type, vol) {
    notes.forEach(function (n, i) { tone(type || 'square', freq(n), 0, step * 1.4, vol || 0.12, i * step); });
  }

  function startInhale() {
    if (!ac || inhale) return;
    var src = ac.createBufferSource(), flt = ac.createBiquadFilter(), g = ac.createGain();
    src.buffer = noiseBuf; src.loop = true;
    flt.type = 'bandpass'; flt.Q.value = 2;
    flt.frequency.setValueAtTime(400, ac.currentTime);
    flt.frequency.exponentialRampToValueAtTime(2400, ac.currentTime + 0.6);
    g.gain.setValueAtTime(0.0001, ac.currentTime);
    g.gain.exponentialRampToValueAtTime(0.22, ac.currentTime + 0.08);
    src.connect(flt); flt.connect(g); g.connect(sfxBus);
    src.start();
    inhale = { src: src, g: g };
  }

  function stopInhale() {
    if (!inhale) return;
    var t = ac.currentTime;
    inhale.g.gain.cancelScheduledValues(t);
    inhale.g.gain.setValueAtTime(inhale.g.gain.value, t);
    inhale.g.gain.exponentialRampToValueAtTime(0.0001, t + 0.08);
    inhale.src.stop(t + 0.1);
    inhale = null;
  }

  var SFX = {
    jump: function () { tone('square', 320, 640, 0.12, 0.12); },
    flap: function () { tone('triangle', 520, 820, 0.08, 0.16); noise(0.05, 0.05, 2000); },
    inhaleStart: startInhale,
    inhaleStop: stopInhale,
    swallow: function () { stopInhale(); tone('square', 520, 110, 0.18, 0.16); },
    spit: function (e) { tone('square', e.big ? 700 : 950, 240, 0.15, 0.15); noise(0.08, 0.1, 3000); },
    exhale: function () { noise(0.18, 0.14, 1400, 500); },
    deflate: function () { noise(0.12, 0.08, 1000, 400); },
    defeat: function () { arp(['E6', 'G6', 'C7'], 0.04, 'square', 0.09); },
    blockGrab: function () { tone('triangle', 300, 600, 0.06, 0.1); },
    blockBreak: function () { noise(0.14, 0.22, 900, 200); tone('square', 220, 70, 0.12, 0.08); },
    hurt: function () { tone('sawtooth', 400, 90, 0.3, 0.16); },
    drop: function () { tone('triangle', 600, 300, 0.15, 0.1); },
    death: function () { arp(['C5', 'G4', 'E4', 'C4'], 0.12, 'square', 0.12); },
    pickup: function (e) {
      if (e.kind === 'star') arp(['E6', 'B6'], 0.05, 'square', 0.08);
      else arp(['C5', 'E5', 'G5', 'C6', 'E6'], 0.06, 'square', 0.1);
    },
    oneUp: function () { arp(['E5', 'G5', 'E6', 'C6', 'D6', 'G6'], 0.07, 'square', 0.1); },
    checkpoint: function () { arp(['G5', 'C6', 'E6'], 0.08, 'triangle', 0.16); },
    clink: function () { tone('square', 2100, 1800, 0.05, 0.07); },
    noFly: function () { tone('square', 180, 150, 0.08, 0.08); },
    starPoof: function () { noise(0.06, 0.05, 2500); },
    pause: function () { tone('triangle', 880, 0, 0.06, 0.12); },
    resume: function () { tone('triangle', 660, 0, 0.06, 0.12); },
    arenaLock: function () { noise(0.5, 0.3, 200, 80); tone('square', 110, 55, 0.5, 0.12); },
    bossWake: function () { tone('sawtooth', 90, 60, 0.8, 0.1); },
    appleDrop: function () { tone('triangle', 900, 300, 0.25, 0.07); },
    bossBlow: function () { noise(0.35, 0.13, 700, 250); },
    bossHit: function () { noise(0.2, 0.3, 500, 150); tone('square', 160, 60, 0.25, 0.16); },
    bossBoom: function () { noise(0.3, 0.22, 300, 80); },
    bossDefeated: function () { arp(['C5', 'E5', 'G5', 'C6', 'G5', 'C6', 'E6'], 0.09, 'square', 0.12); },
    win: function () { arp(['G4', 'C5', 'E5', 'G5', 'E5', 'G5', 'C6', 'C6', 'D6', 'E6'], 0.11, 'square', 0.12); },
    gameOver: function () { arp(['G4', 'F#4', 'F4', 'E4', 'D#4', 'C4'], 0.18, 'triangle', 0.18); }
  };

  function play(ev) {
    if (!ac || !SFX[ev.type]) return;
    SFX[ev.type](ev);
  }

  function scheduleStep(song, i, t) {
    var dur = 60 / song.bpm / 2;
    var n = song.lead[i % song.lead.length];
    if (n !== '.' && n !== '-') {
      var hold = 1;
      while (song.lead[(i + hold) % song.lead.length] === '-') hold++;
      tone('square', freq(n), 0, dur * hold * 0.9, 0.12, 0, musicBus, t);
    }
    var b = song.bass[i % song.bass.length];
    if (b !== '.' && b !== '-') tone('triangle', freq(b), 0, dur * 0.9, 0.3, 0, musicBus, t);
    var d = song.drums[i % song.drums.length];
    if (d === 'k') tone('sine', 150, 45, 0.12, 0.35, 0, musicBus, t);
    else if (d === 'h') noise(0.03, 0.08, 7000, 0, 0, musicBus, t);
    else if (d === 's') noise(0.09, 0.14, 1800, 0, 0, musicBus, t);
  }

  function pump() {
    if (!ac || !music.song) return;
    var song = music.song, dur = 60 / song.bpm / 2;
    if (music.next < ac.currentTime) music.next = ac.currentTime + 0.02;
    while (music.next < ac.currentTime + LOOKAHEAD) {
      scheduleStep(song, music.step, music.next);
      music.step = (music.step + 1) % song.lead.length;
      music.next += dur;
    }
  }

  function setMusic(name) {
    if (name === music.name) return;
    music.name = name;
    music.song = name ? parse(SONGS[name]) : null;
    music.step = 0;
    music.next = 0;
    if (music.song && !music.timer) music.timer = setInterval(pump, SCHEDULE_MS);
    if (!music.song && music.timer) { clearInterval(music.timer); music.timer = null; }
  }

  function setDucked(on) {
    if (on === ducked) return;
    ducked = on;
    if (musicBus) musicBus.gain.setTargetAtTime(on ? VOL.MUSIC * VOL.DUCK : VOL.MUSIC, ac.currentTime, 0.05);
    if (on) stopInhale();
  }

  function toggleMute() {
    muted = !muted;
    if (master) master.gain.setTargetAtTime(muted ? 0 : VOL.MASTER, ac.currentTime, 0.02);
    return muted;
  }

  return {
    unlock: unlock, play: play, setMusic: setMusic, setDucked: setDucked, toggleMute: toggleMute,
    isMuted: function () { return muted; }
  };
})();
8:44 PM
Now main.js (the fixed-timestep loop) and index.html:



Write C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\js\main.js
87 lines
// Boots the game: fixed 60 Hz logic updates, rendering on requestAnimationFrame.
(function () {
  'use strict';
  var C = CONST;
  var STEP_MS = 1000 / C.TICKS_PER_SECOND;
  var BEST_KEY = 'kirby-dream-meadows-best';

  function loadBest() {
    try { return Number(localStorage.getItem(BEST_KEY)) || 0; } catch (e) { return 0; }
  }
  function saveBest(v) {
    try { localStorage.setItem(BEST_KEY, String(v)); } catch (e) { /* storage blocked: best score is per session */ }
  }

  var canvas = document.getElementById('game');
  canvas.width = C.VIEW_W;
  canvas.height = C.VIEW_H;
  var ctx = canvas.getContext('2d');
  ctx.imageSmoothingEnabled = false;

  Sprites.init();
  Renderer.init(ctx);

  var input = KirbyInput.create();
  KirbyInput.attach(input, window, GameAudio.unlock);
  var state = Game.create(LEVEL_1, { best: loadBest() });
  Renderer.snapCamera(state);

  function musicFor(s) {
    if (s.mode === 'dying' || s.mode === 'gameover' || s.mode === 'win') return null;
    var b = s.boss;
    if (s.arenaLocked && b && b.state !== 'dead' && b.state !== 'dying') return 'boss';
    return 'level';
  }

  function tick() {
    var snap = input.poll();
    if (snap.mutePressed) GameAudio.toggleMute();
    Game.update(state, snap);
    for (var i = 0; i < state.events.length; i++) {
      var ev = state.events[i];
      GameAudio.play(ev);
      Renderer.onEvent(ev, state);
      if (ev.type === 'win' || ev.type === 'gameOver') saveBest(state.best);
    }
    GameAudio.setMusic(musicFor(state));
    GameAudio.setDucked(state.mode === 'paused' || state.mode === 'confirm' || state.mode === 'title');
    Renderer.tick(state);
  }

  var acc = 0, last = performance.now();
  function frame(now) {
    acc += Math.min(now - last, 250);
    last = now;
    var steps = 0;
    while (acc >= STEP_MS && steps < C.MAX_STEPS_PER_FRAME) {
      tick();
      acc -= STEP_MS;
      steps++;
    }
    if (steps === C.MAX_STEPS_PER_FRAME) acc = 0;
    Renderer.draw(state, { muted: GameAudio.isMuted() });
    requestAnimationFrame(frame);
  }

  function resize() {
    var scale = Math.max(1, Math.floor(Math.min(window.innerWidth / C.VIEW_W, (window.innerHeight - 32) / C.VIEW_H)));
    canvas.style.width = C.VIEW_W * scale + 'px';
    canvas.style.height = C.VIEW_H * scale + 'px';
  }
  window.addEventListener('resize', resize);
  resize();

  // Pause automatically when the window loses focus.
  window.addEventListener('blur', function () { Game.pause(state); });

  // Hook used by the browser smoke test to step the real game with simulated keys.
  window.KirbyDebug = {
    state: function () { return state; },
    input: input,
    tick: tick,
    draw: function () { Renderer.draw(state, { muted: GameAudio.isMuted() }); }
  };

  requestAnimationFrame(frame);
})();
Write C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\index.html
40 lines
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Kirby: Dream Meadows</title>
  <style>
    html, body { margin: 0; height: 100%; background: #1d1130; color: #cdeeff; }
    body { display: flex; flex-direction: column; align-items: center; justify-content: center;
      font: 12px/1.4 monospace; overflow: hidden; }
    canvas { display: block; image-rendering: pixelated; image-rendering: crisp-edges;
      box-shadow: 0 0 0 4px #46435f, 0 8px 32px #000; }
    p { margin: 8px 0 0; opacity: 0.8; text-align: center; }
    kbd { color: #ffd83d; }
  </style>
</head>
<body>
  <canvas id="game" width="256" height="224" tabindex="0"></canvas>
  <p><kbd>&larr; &rarr;</kbd> / <kbd>A D</kbd> move &middot; <kbd>Space</kbd> jump, tap again in the air to fly &middot;
    <kbd>Enter</kbd> hold to inhale, press to spit &middot; <kbd>P</kbd>/<kbd>Esc</kbd> pause &middot;
    <kbd>M</kbd> mute &middot; <kbd>R</kbd> restart</p>

  <script src="js/logic/constants.js"></script>
  <script src="js/logic/physics.js"></script>
  <script src="js/logic/world.js"></script>
  <script src="js/logic/enemies.js"></script>
  <script src="js/logic/player.js"></script>
  <script src="js/logic/boss.js"></script>
  <script src="js/logic/game.js"></script>
  <script src="js/level.js"></script>
  <script src="js/input.js"></script>
  <script src="js/sprites.js"></script>
  <script src="js/sprites-world.js"></script>
  <script src="js/hud.js"></script>
  <script src="js/render.js"></script>
  <script src="js/audio.js"></script>
  <script src="js/main.js"></script>
</body>
</html>
Edit C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\js\logic\game.js
Added 7 lines
8:46 PM
Before the tests, I need the automated player ("bot") that drives the game with key events only. It reads the game state to decide what to do, but only acts by pressing and releasing keys:



Write C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\tests\bot.js
155 lines
// An automated player for the playthrough tests. It READS the game state to decide,
// but it can only ACT by pressing and releasing keys on the input tracker, like a person would.
// Works in Node (require) and in the browser (injected by tests/smoke.mjs).
var KirbyBot = (function () {
  'use strict';
  var isNode = typeof module !== 'undefined';
  var C = isNode ? require('../js/logic/constants.js').CONST : CONST;
  var P = isNode ? require('../js/logic/physics.js').Physics : Physics;
  var PL = isNode ? require('../js/logic/player.js').Player : Player;
  var T = C.TILE, TL = P.TILES;
  var CODES = { left: 'ArrowLeft', right: 'ArrowRight', jump: 'Space', action: 'Enter' };
  var LOOKAHEAD_COLS = 4, SCAN_UP_ROWS = 4, CRUISE = 26, CLEARANCE = 10, DANGER_X = 52, DANGER_Y = 22;

  function create() {
    var mem = { held: {}, lastGroundY: null, inhaleTicks: 0, keyEvents: 0 };

    function solidOrPlatform(t) { return P.isSolid(t) || t === TL.PLATFORM; }

    // y of the first surface at or below (feetRow - SCAN_UP_ROWS) in a column, or null for a pit.
    function surface(world, c, feetRow) {
      for (var r = Math.max(0, feetRow - SCAN_UP_ROWS); r < world.h; r++) {
        if (solidOrPlatform(P.tileAt(world, c, r))) return r * T;
      }
      return null;
    }

    function tap(want, k) { want[k] = !mem.held[k]; }

    function bossFight(state, want) {
      var p = state.player, b = state.boss, world = state.world;
      var home = world.gateCol * T + 52;
      var px = p.x + p.w / 2;
      if (b.state === 'dead') return false;
      var dodge = 0;
      state.enemies.forEach(function (e) {
        if (e.type === 'apple' && !e.rolling && !e.caught && Math.abs(e.x + e.w / 2 - px) < 14 && e.y < p.y) dodge = 1;
      });
      var puff = state.enemies.some(function (e) {
        return e.type === 'bosspuff' && e.x - (p.x + p.w) < 30 && e.x + e.w > p.x && Math.abs(e.y + e.h / 2 - (p.y + p.h / 2)) < 12;
      });
      if (p.mouth) { if (p.facing > 0) tap(want, 'action'); else want.right = true; return true; }
      if (puff && p.onGround) { tap(want, 'jump'); return true; }
      if (p.jumping) { want.jump = true; return true; }
      if (dodge) { want.right = true; return true; }
      if (px < home - 6) { want.right = true; return true; }
      if (px > home + 24) { want.left = true; return true; }
      if (p.facing < 0) { want.right = true; return true; }
      var apple = state.enemies.some(function (e) { return e.type === 'apple' && PL.inInhaleCone(p, e); });
      want.action = apple || (p.inhaling && mem.inhaleTicks < 90);
      return true;
    }

    function decide(state) {
      var want = { left: false, right: false, jump: false, action: false };
      if (state.mode === 'title' || state.mode === 'gameover') { tap(want, 'jump'); return want; }
      if (state.mode !== 'playing') return want;
      var p = state.player, world = state.world;
      mem.inhaleTicks = p.inhaling ? mem.inhaleTicks + 1 : 0;
      if (p.onGround) mem.lastGroundY = p.y + p.h;
      if (mem.lastGroundY === null) mem.lastGroundY = p.y + p.h;

      if (state.arenaLocked && state.boss && bossFight(state, want)) return want;

      var px = p.x + p.w / 2, feet = p.y + p.h;
      var col = Math.floor(px / T), feetRow = Math.floor((feet - 1) / T), midRow = Math.floor((p.y + p.h / 2) / T);
      var aheadCol = Math.floor((p.x + p.w + 2) / T);

      // Warp star: go and touch it.
      if (state.warp && state.warp.active) {
        var wx = state.warp.x + state.warp.w / 2, wy = state.warp.y + state.warp.h / 2;
        if (wx > px + 2) want.right = true; else if (wx < px - 2) want.left = true;
        if (wy < p.y && !p.jumping) tap(want, 'jump');
        if (p.jumping) want.jump = true;
        return want;
      }

      // Mouth full: spit forward straight away (it clears the way and lets Kirby fly again).
      if (p.mouth) {
        want.right = true;
        if (p.facing > 0) tap(want, 'action');
        return want;
      }

      // Star block in front: stop and inhale it.
      var starAhead = P.tileAt(world, aheadCol, midRow) === TL.STAR || P.tileAt(world, aheadCol + 1, midRow) === TL.STAR;
      if (starAhead && !p.flying && p.facing > 0) {
        want.action = true;
        return want;
      }

      // Inhalable enemy in the cone: keep inhaling (on the ground or mid-jump).
      var prey = state.enemies.filter(function (e) {
        return e.inhalable && !e.dead && (e.caught || PL.inInhaleCone(p, e));
      });
      if (prey.length && !p.flying && p.facing > 0 && mem.inhaleTicks < 120) {
        want.action = true;
        return want;
      }
      // Flying into an enemy: blow an air puff at it.
      var close = state.enemies.some(function (e) {
        return e.harmful && e.type !== 'spiky' && e.type !== 'bosspuff' &&
          e.x > p.x && e.x - (p.x + p.w) < 26 && Math.abs(e.y + e.h / 2 - (p.y + p.h / 2)) < 14;
      });
      if (close && p.flying) { tap(want, 'action'); want.right = true; return want; }

      // Navigation: keep moving right, climbing over walls and flying over pits.
      want.right = true;
      var target = Infinity, pit = false;
      for (var c = col; c <= col + LOOKAHEAD_COLS; c++) {
        var s = surface(world, c, feetRow);
        if (s === null) pit = true;
        else target = Math.min(target, s - CLEARANCE);
      }
      if (pit) target = Math.min(target, mem.lastGroundY - CRUISE);
      var wall = P.isSolid(P.tileAt(world, aheadCol, midRow)) || P.isSolid(P.tileAt(world, aheadCol, feetRow));
      if (wall) target = Math.min(target, p.y - T);

      // Steer around spikies vertically.
      state.enemies.forEach(function (e) {
        if (e.type !== 'spiky') return;
        var dx = e.x - (p.x + p.w), dy = (e.y + e.h / 2) - (p.y + p.h / 2);
        if (dx > -8 && dx < DANGER_X && Math.abs(dy) < DANGER_Y + e.h / 2) {
          if (dy > 0) target = Math.min(target, e.y - 4);
          else if (!p.onGround) target = Math.max(target, e.y + e.h + p.h + 4);
        }
      });

      var needUp = feet > target;
      if (p.jumping) want.jump = needUp || p.vy < -2;
      else if (needUp && (p.onGround || p.vy > -0.6)) tap(want, 'jump');
      return want;
    }

    function apply(state, input) {
      var want = decide(state);
      for (var k in CODES) {
        if (want[k] && !mem.held[k]) { input.keyDown(CODES[k]); mem.keyEvents++; }
        if (!want[k] && mem.held[k]) { input.keyUp(CODES[k]); mem.keyEvents++; }
        mem.held[k] = want[k];
      }
    }

    function releaseAll(input) {
      for (var k in CODES) if (mem.held[k]) input.keyUp(CODES[k]);
      mem.held = {};
    }

    return { apply: apply, releaseAll: releaseAll, mem: mem };
  }

  return { create: create, CODES: CODES };
})();

if (typeof module !== 'undefined') module.exports = { KirbyBot };
8:46 PM
Now a quick runner to see how far the bot gets:



Bash Run the bot through the level and log progress
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && cat > .tmp/run.js <<'EOF'
const { Game } = require('../js/logic/game.js');
const { LEVEL_1 } = require('../js/level.js');
const { KirbyInput } = require('../js/input.js');
const { KirbyBot } = require('../tests/bot.js');
const s = Game.create(LEVEL_1, {});
const input = KirbyInput.create();
const bot = KirbyBot.create();
const MAX = +process.argv[2] || 60 * 60 * 12;
let lastLog = 0, maxX = 0;
const log = [];
for (let t = 0; t < MAX; t++) {
  bot.apply(s, input);
  Game.update(s, input.poll());
  for (const e of s.events) {
    if (['hurt', 'death', 'checkpoint', 'section', 'gameOver', 'respawn', 'arenaLock', 'bossHit', 'bossDefeated', 'win'].includes(e.type))
      log.push(`${t} ${e.type} ${e.name || ''} x=${(s.player.x / 16).toFixed(1)} y=${(s.player.y / 16).toFixed(1)} hp=${s.player.health} lives=${s.lives}`);
  }
  maxX = Math.max(maxX, s.player.x);
  if (s.mode === 'win') break;
  if (t - lastLog > 600) { lastLog = t; log.push(`  .. t=${t} mode=${s.mode} x=${(s.player.x / 16).toFixed(1)} y=${(s.player.y / 16).toFixed(1)} fly=${s.player.flying} inh=${s.player.inhaling} mouth=${!!s.player.mouth}`); }
}
console.log(log.join('\n'));
console.log('END mode', s.mode, 'time', (s.time / 60).toFixed(1) + 's', 'maxCol', (maxX / 16).toFixed(1), 'score', s.score, 'deaths', s.deaths, 'continues', s.continues);
EOF
node .tmp/run.js 2>&1 | tail -60

OUT
  .. t=7813 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=8414 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=9015 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=9616 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=10217 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=10818 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=11419 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=12020 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=12621 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=13222 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=13823 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=14424 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=15025 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=15626 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=16227 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=16828 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=17429 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=18030 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=18631 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=19232 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=19833 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=20434 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=21035 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=21636 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=22237 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=22838 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=23439 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=24040 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=24641 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=25242 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=25843 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=26444 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=27045 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=27646 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=28247 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=28848 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=29449 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=30050 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=30651 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=31252 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=31853 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=32454 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=33055 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=33656 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=34257 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=34858 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=35459 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=36060 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=36661 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=37262 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=37863 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=38464 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=39065 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=39666 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=40267 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=40868 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=41469 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=42070 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
  .. t=42671 mode=playing x=155.3 y=11.0 fly=true inh=false mouth=false
END mode playing time 719.3s maxCol 155.3 score 2550 deaths 0 continues 0
I see the bot getting stuck flying against the first star-block wall. I'll fix this by excluding star-block walls from "climb over" logic and having the bot exhale to drop and inhale when flying toward one.
Bash Fix bot star-wall handling and rerun
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && python - <<'EOF'
p='tests/bot.js'; s=open(p,encoding='utf8').read()
s=s.replace("""      var starAhead = P.tileAt(world, aheadCol, midRow) === TL.STAR || P.tileAt(world, aheadCol + 1, midRow) === TL.STAR;
      if (starAhead && !p.flying && p.facing > 0) {
        want.action = true;
        return want;
      }""","""      var starAhead = P.tileAt(world, aheadCol, midRow) === TL.STAR || P.tileAt(world, aheadCol + 1, midRow) === TL.STAR;
      if (starAhead && p.facing > 0) {
        if (p.flying) tap(want, 'action'); // exhale to stop flying, then inhale
        else want.action = true;
        return want;
      }""")
s=s.replace("""      var wall = P.isSolid(P.tileAt(world, aheadCol, midRow)) || P.isSolid(P.tileAt(world, aheadCol, feetRow));""","""      function hardWall(r) { var t = P.tileAt(world, aheadCol, r); return P.isSolid(t) && t !== TL.STAR; }
      var wall = hardWall(midRow) || hardWall(feetRow);""")
open(p,'w',encoding='utf8').write(s)
EOF
node .tmp/run.js 2>&1 | grep -v "^  \.\." | tail -50; node .tmp/run.js 2>&1 | tail -4

OUT
34568 hurt  x=155.3 y=17.3 hp=3 lives=2
34658 hurt  x=155.3 y=17.3 hp=2 lives=2
34748 hurt  x=155.3 y=17.3 hp=1 lives=2
34838 hurt  x=155.3 y=17.3 hp=0 lives=2
34838 death  x=155.3 y=17.3 hp=0 lives=2
34958 respawn  x=138.1 y=17.3 hp=6 lives=1
35121 hurt  x=150.3 y=15.7 hp=5 lives=1
35389 hurt  x=155.3 y=17.3 hp=4 lives=1
35479 hurt  x=155.3 y=17.3 hp=3 lives=1
35569 hurt  x=155.3 y=17.3 hp=2 lives=1
35659 hurt  x=155.3 y=17.3 hp=1 lives=1
35749 hurt  x=155.3 y=17.3 hp=0 lives=1
35749 death  x=155.3 y=17.3 hp=0 lives=1
35869 gameOver  x=155.3 y=17.3 hp=0 lives=0
35914 respawn  x=138.1 y=17.3 hp=6 lives=3
36346 hurt  x=155.3 y=17.3 hp=5 lives=3
36464 hurt  x=153.1 y=17.3 hp=4 lives=3
36554 hurt  x=150.9 y=17.3 hp=3 lives=3
36888 hurt  x=155.3 y=16.5 hp=2 lives=3
37640 hurt  x=171.3 y=17.3 hp=1 lives=3
38387 hurt  x=172.3 y=17.3 hp=0 lives=3
38387 death  x=172.3 y=17.3 hp=0 lives=3
38507 respawn  x=138.1 y=17.3 hp=6 lives=2
38670 hurt  x=150.3 y=15.7 hp=5 lives=2
38938 hurt  x=155.3 y=17.3 hp=4 lives=2
39028 hurt  x=155.3 y=17.3 hp=3 lives=2
39118 hurt  x=155.3 y=17.3 hp=2 lives=2
39208 hurt  x=155.3 y=17.3 hp=1 lives=2
39298 hurt  x=155.3 y=17.3 hp=0 lives=2
39298 death  x=155.3 y=17.3 hp=0 lives=2
39418 respawn  x=138.1 y=17.3 hp=6 lives=1
39581 hurt  x=150.3 y=15.7 hp=5 lives=1
39849 hurt  x=155.3 y=17.3 hp=4 lives=1
39939 hurt  x=155.3 y=17.3 hp=3 lives=1
40029 hurt  x=155.3 y=17.3 hp=2 lives=1
40119 hurt  x=155.3 y=17.3 hp=1 lives=1
40209 hurt  x=155.3 y=17.3 hp=0 lives=1
40209 death  x=155.3 y=17.3 hp=0 lives=1
40329 gameOver  x=155.3 y=17.3 hp=0 lives=0
40374 respawn  x=138.1 y=17.3 hp=6 lives=3
40806 hurt  x=155.3 y=17.3 hp=5 lives=3
40924 hurt  x=153.1 y=17.3 hp=4 lives=3
41014 hurt  x=150.9 y=17.3 hp=3 lives=3
41348 hurt  x=155.3 y=16.5 hp=2 lives=3
42100 hurt  x=171.3 y=17.3 hp=1 lives=3
42847 hurt  x=172.3 y=17.3 hp=0 lives=3
42847 death  x=172.3 y=17.3 hp=0 lives=3
42967 respawn  x=138.1 y=17.3 hp=6 lives=2
43130 hurt  x=150.3 y=15.7 hp=5 lives=2
END mode playing time 656.5s maxCol 172.3 score 450 deaths 28 continues 9
42847 death  x=172.3 y=17.3 hp=0 lives=3
42967 respawn  x=138.1 y=17.3 hp=6 lives=2
43130 hurt  x=150.3 y=15.7 hp=5 lives=2
END mode playing time 656.5s maxCol 172.3 score 450 deaths 28 continues 9
8:46 PM
The bot is taking repeated damage at the wall. Let me see what's hitting it:



Bash Debug what hurts the bot near the wall
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && cat > .tmp/dbg.js <<'EOF'
const { Game } = require('../js/logic/game.js');
const { LEVEL_1 } = require('../js/level.js');
const { KirbyInput } = require('../js/input.js');
const { KirbyBot } = require('../tests/bot.js');
const s = Game.create(LEVEL_1, {});
const input = KirbyInput.create();
const bot = KirbyBot.create();
let n = 0;
for (let t = 0; t < 40000 && n < +(process.argv[2] || 4); t++) {
  bot.apply(s, input);
  const snap = input.poll();
  Game.update(s, snap);
  if (s.events.some(e => e.type === 'hurt' || e.type === 'death')) {
    n++;
    const p = s.player;
    console.log(t, s.events.map(e => e.type).join(','), 'P', p.x.toFixed(1), p.y.toFixed(1), 'inh', p.inhaling, 'mouth', JSON.stringify(p.mouth), 'held', JSON.stringify(bot.mem.held));
    s.enemies.filter(e => Math.abs(e.x - p.x) < 40 && Math.abs(e.y - p.y) < 40).forEach(e => console.log('   ', e.type, e.kind || '', e.x.toFixed(1), e.y.toFixed(1), 'caught', e.caught, 'stun', e.stun, 'harm', e.harmful));
  }
}
EOF
node .tmp/dbg.js 6

OUT
533 hurt P 666.4 187.9 inh false mouth null held {"left":false,"right":true,"jump":false,"action":false}
    flyer  663.9 199.3 caught false stun 0 harm true
1076 hurt P 1365.7 237.9 inh false mouth null held {"left":false,"right":true,"jump":false,"action":false}
    spiky  1377.0 226.4 caught false stun 0 harm true
1451 hurt P 1756.6 232.7 inh false mouth null held {"left":false,"right":true,"jump":false,"action":false}
    walker  1762.5 244.0 caught false stun 0 harm true
1763 exhale,hurt P 2052.2 264.2 inh false mouth null held {"left":false,"right":true,"jump":false,"action":true}
    walker  2047.4 276.0 caught false stun 0 harm true
    hopper  2088.4 276.0 caught false stun 0 harm true
1966 hurt P 2320.1 265.5 inh false mouth null held {"left":false,"right":true,"jump":false,"action":false}
    walker  2323.3 276.0 caught false stun 0 harm true
2707 hurt,death P 2484.0 276.0 inh false mouth null held {"left":false,"right":false,"jump":false,"action":true}
    walker  2472.1 276.0 caught false stun 0 harm true
    hopper  2512.0 244.2 caught false stun 0 harm true
8:47 PM
Two bot problems: it kept holding Enter after spitting (the game correctly requires a fresh press to inhale again), and it ignored enemies coming from behind. I'll fix both in the bot:



Bash Improve bot enemy handling and rerun
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && python - <<'EOF'
p='tests/bot.js'; s=open(p,encoding='utf8').read()
old_start = s.index("      // Star block in front: stop and inhale it.")
old_end = s.index("      // Navigation: keep moving right")
new = """      // Star block in front: stop and inhale it.
      var starAhead = P.tileAt(world, aheadCol, midRow) === TL.STAR || P.tileAt(world, aheadCol + 1, midRow) === TL.STAR;
      if (starAhead && p.facing > 0) {
        if (p.flying) tap(want, 'action'); // exhale to stop flying, then inhale
        else inhale(want, p);
        return want;
      }

      // Nearby enemy in front or behind: turn to face it and inhale it (or blow air at it while flying).
      var threat = null, best = Infinity;
      state.enemies.forEach(function (e) {
        if (e.dead || !e.inhalable || e.type === 'loose') return;
        var dx = (e.x + e.w / 2) - px, dy = Math.abs((e.y + e.h / 2) - (p.y + p.h / 2));
        if (e.caught || (Math.abs(dx) < THREAT_X && dy < THREAT_Y)) {
          var d = e.caught ? -1 : Math.abs(dx);
          if (d < best) { best = d; threat = e; }
        }
      });
      if (threat && mem.inhaleTicks < 120) {
        var dir = (threat.x + threat.w / 2) < px ? -1 : 1;
        if (p.facing !== dir && !p.inhaling) {
          if (dir < 0) want.left = true; else want.right = true;
          return want;
        }
        if (p.flying) { if (Math.abs(threat.x - p.x) < AIR_PUFF_X) tap(want, 'action'); }
        else { inhale(want, p); return want; }
      }

"""
s = s[:old_start] + new + s[old_end:]
s = s.replace("""    function tap(want, k) { want[k] = !mem.held[k]; }""","""    function tap(want, k) { want[k] = !mem.held[k]; }

    // Hold Enter to inhale; if Enter is still held from an earlier spit, let go first.
    function inhale(want, p) { want.action = p.inhaling || !mem.held.action; }""")
s = s.replace("CLEARANCE = 10, DANGER_X = 52, DANGER_Y = 22;","CLEARANCE = 10, DANGER_X = 52, DANGER_Y = 22;\n  var THREAT_X = 56, THREAT_Y = 18, AIR_PUFF_X = 30;")
s = s.replace("""      want.action = apple || (p.inhaling && mem.inhaleTicks < 90);""","""      if (apple || (p.inhaling && mem.inhaleTicks < 90)) inhale(want, p);""")
open(p,'w',encoding='utf8').write(s)
EOF
node .tmp/run.js 2>&1 | grep -v "^  \.\." | grep -v hurt | tail -40

OUT
16409 death  x=118.0 y=24.2 hp=0 lives=3
16529 respawn  x=3.1 y=17.3 hp=6 lives=2
18022 death  x=118.0 y=24.2 hp=0 lives=2
18142 respawn  x=3.1 y=17.3 hp=6 lives=1
19635 death  x=118.0 y=24.2 hp=0 lives=1
19755 gameOver  x=118.0 y=24.2 hp=0 lives=0
19800 respawn  x=3.1 y=17.3 hp=6 lives=3
21348 death  x=118.0 y=24.2 hp=0 lives=3
21468 respawn  x=3.1 y=17.3 hp=6 lives=2
22961 death  x=118.0 y=24.2 hp=0 lives=2
23081 respawn  x=3.1 y=17.3 hp=6 lives=1
24574 death  x=118.0 y=24.2 hp=0 lives=1
24694 gameOver  x=118.0 y=24.2 hp=0 lives=0
24739 respawn  x=3.1 y=17.3 hp=6 lives=3
26287 death  x=118.0 y=24.2 hp=0 lives=3
26407 respawn  x=3.1 y=17.3 hp=6 lives=2
27900 death  x=118.0 y=24.2 hp=0 lives=2
28020 respawn  x=3.1 y=17.3 hp=6 lives=1
29513 death  x=118.0 y=24.2 hp=0 lives=1
29633 gameOver  x=118.0 y=24.2 hp=0 lives=0
29678 respawn  x=3.1 y=17.3 hp=6 lives=3
31226 death  x=118.0 y=24.2 hp=0 lives=3
31346 respawn  x=3.1 y=17.3 hp=6 lives=2
32839 death  x=118.0 y=24.2 hp=0 lives=2
32959 respawn  x=3.1 y=17.3 hp=6 lives=1
34452 death  x=118.0 y=24.2 hp=0 lives=1
34572 gameOver  x=118.0 y=24.2 hp=0 lives=0
34617 respawn  x=3.1 y=17.3 hp=6 lives=3
36165 death  x=118.0 y=24.2 hp=0 lives=3
36285 respawn  x=3.1 y=17.3 hp=6 lives=2
37778 death  x=118.0 y=24.2 hp=0 lives=2
37898 respawn  x=3.1 y=17.3 hp=6 lives=1
39391 death  x=118.0 y=24.2 hp=0 lives=1
39511 gameOver  x=118.0 y=24.2 hp=0 lives=0
39556 respawn  x=3.1 y=17.3 hp=6 lives=3
41104 death  x=118.0 y=24.2 hp=0 lives=3
41224 respawn  x=3.1 y=17.3 hp=6 lives=2
42717 death  x=118.0 y=24.2 hp=0 lives=2
42837 respawn  x=3.1 y=17.3 hp=6 lives=1
END mode playing time 661.3s maxCol 118.0 score 4700 deaths 26 continues 8
I found two issues: checkpoints only trigger on touch, letting Kirby skip them by flying over, and the bot inhales enemies while over pits, filling its mouth and causing it to fall (which is intended behavior the bot should just avoid). I'll fix checkpoints to activate at any height, then adjust the bot's logic to avoid inhaling over pits.
Bash Make checkpoints trigger on pass and rerun bot
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && python - <<'EOF'
p='js/logic/game.js'; s=open(p,encoding='utf8').read()
s=s.replace("""    world.checkpoints.forEach(function (cp) {
      if (cp.index > state.checkpoint && P.overlaps(p, cp)) {""","""    // A checkpoint counts as soon as Kirby passes it, even flying high above it.
    world.checkpoints.forEach(function (cp) {
      if (cp.index > state.checkpoint && p.x + p.w / 2 >= cp.x) {""")
open(p,'w',encoding='utf8').write(s)
p='tests/bot.js'; s=open(p,encoding='utf8').read()
s=s.replace("""      if (threat && mem.inhaleTicks < 120) {""","""      var pitBelow = !p.onGround && surface(world, col, feetRow) === null;
      if (threat && mem.inhaleTicks < 120 && !(pitBelow && !p.flying && !threat.caught)) {""")
open(p,'w',encoding='utf8').write(s)
EOF
node .tmp/run.js 2>&1 | grep -v "^  \.\." | grep -v hurt | tail -30

OUT
44 section MEADOW x=3.1 y=17.3 hp=6 lives=3
800 section CLIFFS x=63.6 y=14.9 hp=6 lives=3
816 checkpoint  x=64.9 y=14.2 hp=6 lives=3
1864 section STAR BLOCK FORT x=135.7 y=15.6 hp=3 lives=3
1893 checkpoint  x=137.9 y=16.3 hp=3 lives=3
2697 section THE CLIMB x=199.6 y=13.4 hp=2 lives=3
2713 checkpoint  x=200.9 y=12.0 hp=2 lives=3
END mode playing time 719.3s maxCol 203.3 score 4350 deaths 0 continues 0
Made it through the Meadow, Cliffs, and Fort, but the bot's now stuck at the Climb's cave entrance, trying to scale a wall above the actual opening. I'll adjust it to search for the nearest open row in the wall, whether up or down.
Bash Teach bot to find openings in walls and rerun
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && python - <<'EOF'
p='tests/bot.js'; s=open(p,encoding='utf8').read()
s=s.replace("""      var wall = hardWall(midRow) || hardWall(feetRow);
      if (wall) target = Math.min(target, p.y - T);""","""      if (hardWall(midRow) || hardWall(feetRow)) {
        // Find the nearest open row in the wall ahead and head for it (up or down).
        for (var k = 1; k < world.h; k++) {
          if (midRow + k < world.h && !hardWall(midRow + k)) { target = (midRow + k + 1) * T; break; }
          if (midRow - k >= 0 && !hardWall(midRow - k)) { target = (midRow - k + 1) * T - 2; break; }
        }
      }""")
open(p,'w',encoding='utf8').write(s)
EOF
node .tmp/run.js 2>&1 | grep -v "^  \.\." | grep -v hurt | tail -30

OUT
44 section MEADOW x=3.1 y=17.3 hp=6 lives=3
800 section CLIFFS x=63.6 y=14.9 hp=6 lives=3
816 checkpoint  x=64.9 y=14.2 hp=6 lives=3
1864 section STAR BLOCK FORT x=135.7 y=15.6 hp=3 lives=3
1893 checkpoint  x=137.9 y=16.3 hp=3 lives=3
2697 section THE CLIMB x=199.6 y=13.4 hp=2 lives=3
2713 checkpoint  x=200.9 y=12.0 hp=2 lives=3
END mode playing time 719.3s maxCol 203.3 score 4350 deaths 0 continues 0
Bash Trace bot state at the stuck point
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && cat > .tmp/at.js <<'EOF'
const { Game } = require('../js/logic/game.js');
const { LEVEL_1 } = require('../js/level.js');
const { KirbyInput } = require('../js/input.js');
const { KirbyBot } = require('../tests/bot.js');
const s = Game.create(LEVEL_1, {});
const input = KirbyInput.create();
const bot = KirbyBot.create();
const [from, to, every] = process.argv.slice(2).map(Number);
for (let t = 0; t < to; t++) {
  bot.apply(s, input);
  Game.update(s, input.poll());
  if (t >= from && (t - from) % (every || 1) === 0) {
    const p = s.player;
    console.log(t, s.mode, 'x', (p.x/16).toFixed(2), 'y', (p.y/16).toFixed(2), 'vx', p.vx.toFixed(2), 'vy', p.vy.toFixed(2), 'gr', p.onGround, 'fly', p.flying, 'inh', p.inhaling, 'mouth', !!p.mouth, 'face', p.facing, 'held', Object.entries(bot.mem.held).filter(([k, v]) => v).map(([k]) => k).join('+'), s.events.map(e => e.type).join(','));
  }
}
EOF
node .tmp/at.js 3000 3040 2

OUT
3000 playing x 203.25 y 10.30 vx 0.00 vy 0.45 gr false fly true inh false mouth false face 1 held right 
3002 playing x 203.25 y 10.38 vx 0.00 vy 0.67 gr false fly true inh false mouth false face 1 held right 
3004 playing x 203.25 y 10.49 vx 0.00 vy 0.89 gr false fly true inh false mouth false face 1 held right 
3006 playing x 203.25 y 10.62 vx 0.00 vy 1.10 gr false fly true inh false mouth false face 1 held right 
3008 playing x 203.25 y 10.75 vx 0.00 vy 1.10 gr false fly true inh false mouth false face 1 held right 
3010 playing x 203.25 y 10.89 vx 0.00 vy 1.10 gr false fly true inh false mouth false face 1 held right 
3012 playing x 203.25 y 11.03 vx 0.00 vy 1.10 gr false fly true inh false mouth false face 1 held right 
3014 playing x 203.25 y 11.17 vx 0.00 vy 1.10 gr false fly true inh false mouth false face 1 held right 
3016 playing x 203.25 y 11.30 vx 0.00 vy 1.10 gr false fly true inh false mouth false face 1 held right 
3018 playing x 203.25 y 11.44 vx 0.00 vy 1.10 gr false fly true inh false mouth false face 1 held right 
3020 playing x 203.25 y 11.58 vx 0.00 vy 1.10 gr false fly true inh false mouth false face 1 held right 
3022 playing x 203.25 y 11.51 vx 0.00 vy -2.19 gr false fly true inh false mouth false face 1 held right+jump flap
3024 playing x 203.25 y 11.26 vx 0.00 vy -1.97 gr false fly true inh false mouth false face 1 held right 
3026 playing x 203.25 y 11.03 vx 0.00 vy -1.75 gr false fly true inh false mouth false face 1 held right 
3028 playing x 203.25 y 10.83 vx 0.00 vy -1.53 gr false fly true inh false mouth false face 1 held right 
3030 playing x 203.25 y 10.66 vx 0.00 vy -1.31 gr false fly true inh false mouth false face 1 held right 
3032 playing x 203.25 y 10.52 vx 0.00 vy -1.09 gr false fly true inh false mouth false face 1 held right 
3034 playing x 203.25 y 10.40 vx 0.00 vy -0.87 gr false fly true inh false mouth false face 1 held right 
3036 playing x 203.25 y 10.32 vx 0.00 vy -0.65 gr false fly true inh false mouth false face 1 held right 
3038 playing x 203.25 y 10.26 vx 0.00 vy -0.43 gr false fly true inh false mouth false face 1 held right
8:48 PM
The bot's ground scan was catching the cave ceiling and treating it as a floor. I'll scan down from the feet and leave walls to the wall logic:



Bash Fix bot surface scanning and rerun
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && python - <<'EOF'
p='tests/bot.js'; s=open(p,encoding='utf8').read()
s=s.replace("""    // y of the first surface at or below (feetRow - SCAN_UP_ROWS) in a column, or null for a pit.
    function surface(world, c, feetRow) {
      for (var r = Math.max(0, feetRow - SCAN_UP_ROWS); r < world.h; r++) {""","""    // y of the first surface at or below the feet in a column, or null for a pit.
    function surface(world, c, feetRow) {
      for (var r = Math.max(0, feetRow); r < world.h; r++) {""")
s=s.replace("LOOKAHEAD_COLS = 4, SCAN_UP_ROWS = 4, CRUISE","LOOKAHEAD_COLS = 4, CRUISE")
s=s.replace("""      for (var c = col; c <= col + LOOKAHEAD_COLS; c++) {
        var s = surface(world, c, feetRow);""","""      for (var c = col; c <= col + LOOKAHEAD_COLS; c++) {
        if (P.isSolid(P.tileAt(world, c, midRow))) break; // a wall: handled below
        var s = surface(world, c, feetRow);""")
open(p,'w',encoding='utf8').write(s)
EOF
node .tmp/run.js 2>&1 | grep -v "^  \.\." | grep -v hurt | tail -30

OUT
38050 arenaLock  x=386.5 y=15.5 hp=6 lives=3
38275 bossHit  x=387.9 y=17.3 hp=5 lives=3
38545 bossHit  x=387.8 y=17.3 hp=3 lives=3
38779 bossHit  x=387.8 y=17.3 hp=2 lives=3
38935 death  x=386.9 y=17.3 hp=0 lives=3
39055 respawn  x=381.1 y=17.3 hp=6 lives=2
39131 arenaLock  x=386.5 y=16.1 hp=6 lives=2
39361 bossHit  x=387.9 y=17.3 hp=5 lives=2
39625 bossHit  x=387.9 y=17.3 hp=3 lives=2
39860 bossHit  x=387.8 y=17.3 hp=2 lives=2
40016 death  x=386.9 y=17.3 hp=0 lives=2
40136 respawn  x=381.1 y=17.3 hp=6 lives=1
40212 arenaLock  x=386.5 y=16.1 hp=6 lives=1
40442 bossHit  x=387.9 y=17.3 hp=5 lives=1
40706 bossHit  x=387.9 y=17.3 hp=3 lives=1
40941 bossHit  x=387.8 y=17.3 hp=2 lives=1
41097 death  x=386.9 y=17.3 hp=0 lives=1
41217 gameOver  x=386.9 y=17.3 hp=0 lives=0
41262 respawn  x=381.1 y=17.3 hp=6 lives=3
41325 arenaLock  x=386.5 y=15.5 hp=6 lives=3
41550 bossHit  x=387.9 y=17.3 hp=5 lives=3
41820 bossHit  x=387.8 y=17.3 hp=3 lives=3
42054 bossHit  x=387.8 y=17.3 hp=2 lives=3
42210 death  x=386.9 y=17.3 hp=0 lives=3
42330 respawn  x=381.1 y=17.3 hp=6 lives=2
42406 arenaLock  x=386.5 y=16.1 hp=6 lives=2
42636 bossHit  x=387.9 y=17.3 hp=5 lives=2
42900 bossHit  x=387.9 y=17.3 hp=3 lives=2
43135 bossHit  x=387.8 y=17.3 hp=2 lives=2
END mode playing time 643.0s maxCol 392.2 score 450 deaths 34 continues 11
8:48 PM
The bot now gets through the whole level to the boss. It lands 3 hits and then dies. Let me look at the run up to the arena:



Bash Show the start of the bot run log
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && node .tmp/run.js 2>&1 | grep -v "^  \.\." | head -60

OUT
44 section MEADOW x=3.1 y=17.3 hp=6 lives=3
798 section CLIFFS x=63.6 y=15.4 hp=6 lives=3
814 checkpoint  x=64.9 y=14.4 hp=6 lives=3
1746 section STAR BLOCK FORT x=135.7 y=15.3 hp=6 lives=3
1775 checkpoint  x=137.9 y=16.5 hp=6 lives=3
1866 hurt  x=145.0 y=16.6 hp=5 lives=3
2107 hurt  x=159.5 y=16.2 hp=4 lives=3
2473 hurt  x=188.4 y=15.6 hp=3 lives=3
2694 section THE CLIMB x=199.7 y=16.2 hp=3 lives=3
2710 checkpoint  x=200.9 y=17.3 hp=3 lives=3
3169 hurt  x=222.1 y=5.4 hp=2 lives=3
3440 checkpoint  x=243.9 y=4.5 hp=2 lives=3
3488 section WINDY SKY x=247.6 y=3.4 hp=2 lives=3
3541 hurt  x=250.6 y=3.9 hp=1 lives=3
4774 section GAUNTLET x=319.6 y=5.8 hp=1 lives=3
4804 checkpoint  x=321.9 y=7.3 hp=1 lives=3
5400 hurt  x=362.0 y=13.8 hp=0 lives=3
5400 death  x=362.0 y=13.8 hp=0 lives=3
5520 respawn  x=322.1 y=17.3 hp=6 lives=2
6309 checkpoint  x=380.9 y=15.3 hp=6 lives=2
6345 section GNARLWOOD ARENA x=383.7 y=15.4 hp=6 lives=2
6381 arenaLock  x=386.5 y=16.1 hp=6 lives=2
6525 hurt  x=387.7 y=17.3 hp=5 lives=2
6607 bossHit  x=387.8 y=17.3 hp=5 lives=2
6675 hurt  x=387.8 y=17.3 hp=4 lives=2
6786 hurt  x=388.0 y=17.3 hp=3 lives=2
6875 bossHit  x=387.9 y=17.3 hp=3 lives=2
6951 hurt  x=387.9 y=16.3 hp=2 lives=2
7108 bossHit  x=387.9 y=17.3 hp=2 lives=2
7173 hurt  x=388.4 y=15.8 hp=1 lives=2
7266 hurt  x=386.9 y=17.3 hp=0 lives=2
7266 death  x=386.9 y=17.3 hp=0 lives=2
7386 respawn  x=381.1 y=17.3 hp=6 lives=1
7462 arenaLock  x=386.5 y=16.1 hp=6 lives=1
7608 hurt  x=387.8 y=17.3 hp=5 lives=1
7692 bossHit  x=387.9 y=17.3 hp=5 lives=1
7757 hurt  x=387.9 y=17.3 hp=4 lives=1
7867 hurt  x=388.0 y=17.3 hp=3 lives=1
7956 bossHit  x=387.9 y=17.3 hp=3 lives=1
8032 hurt  x=387.9 y=16.3 hp=2 lives=1
8191 bossHit  x=387.8 y=17.3 hp=2 lives=1
8254 hurt  x=388.3 y=15.8 hp=1 lives=1
8347 hurt  x=386.9 y=17.3 hp=0 lives=1
8347 death  x=386.9 y=17.3 hp=0 lives=1
8467 gameOver  x=386.9 y=17.3 hp=0 lives=0
8512 respawn  x=381.1 y=17.3 hp=6 lives=3
8575 arenaLock  x=386.5 y=15.5 hp=6 lives=3
8719 hurt  x=387.7 y=17.3 hp=5 lives=3
8800 bossHit  x=387.9 y=17.3 hp=5 lives=3
8870 hurt  x=387.9 y=17.3 hp=4 lives=3
8980 hurt  x=388.0 y=17.3 hp=3 lives=3
9070 bossHit  x=387.8 y=17.3 hp=3 lives=3
9146 hurt  x=387.8 y=16.3 hp=2 lives=3
9304 bossHit  x=387.8 y=17.3 hp=2 lives=3
9367 hurt  x=388.3 y=15.8 hp=1 lives=3
9460 hurt  x=386.9 y=17.3 hp=0 lives=3
9460 death  x=386.9 y=17.3 hp=0 lives=3
9580 respawn  x=381.1 y=17.3 hp=6 lives=2
9656 arenaLock  x=386.5 y=16.1 hp=6 lives=2
9802 hurt  x=387.8 y=17.3 hp=5 lives=2
Bash Show what hurts the bot in the boss arena
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && sed -i 's/for (let t = 0; t < 40000 \&\& n < +(process.argv\[2\] || 4); t++) {/for (let t = 0; t < 40000 \&\& n < +(process.argv[2] || 4); t++) { if (t < +(process.argv[3] || 0)) { bot.apply(s, input); Game.update(s, input.poll()); continue; }/' .tmp/dbg.js && node .tmp/dbg.js 8 6381

OUT
6525 hurt P 6203.1 276.0 inh false mouth null held {"left":false,"right":false,"jump":false,"action":false}
    apple  6191.4 276.0 caught false stun 0 harm true
6675 hurt P 6205.6 276.0 inh false mouth null held {"left":false,"right":false,"jump":false,"action":false}
    apple  6193.6 276.0 caught false stun 0 harm true
6786 inhaleStop,hurt P 6208.3 276.0 inh false mouth null held {"left":false,"right":false,"jump":false,"action":true}
    apple  6197.2 276.0 caught false stun 0 harm true
6951 hurt P 6205.7 260.2 inh false mouth null held {"left":false,"right":false,"jump":false,"action":false}
    bosspuff  6198.0 269.7 caught false stun 0 harm true
    bosspuff  6237.0 243.9 caught false stun 0 harm true
7173 hurt P 6214.8 252.1 inh false mouth null held {"left":false,"right":false,"jump":true,"action":false}
    bosspuff  6225.0 240.6 caught false stun 0 harm true
    bosspuff  6240.0 270.0 caught false stun 0 harm true
7266 hurt,death P 6189.7 276.0 inh false mouth null held {"left":false,"right":false,"jump":false,"action":false}
    apple  6178.4 276.0 caught false stun 0 harm true
    apple  6168.8 276.0 caught false stun 0 harm true
7608 hurt P 6204.9 276.0 inh false mouth null held {"left":false,"right":false,"jump":false,"action":false}
    apple  6193.0 276.0 caught false stun 0 harm true
    apple  6244.4 250.1 caught false stun 0 harm true
7757 hurt P 6205.7 276.0 inh false mouth null held {"left":false,"right":false,"jump":false,"action":false}
    apple  6194.4 276.0 caught false stun 0 harm true
Found the arena damage comes from apples approaching from behind and puffs hitting mid-jump. I'll space the boss's puffs further apart (40 ticks) for a fairer rhythm, and update the bot to turn and inhale apples from either side before facing the boss to spit.
Bash Rework puff timing and bot boss tactics, rerun
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && python - <<'EOF'
p='js/logic/constants.js'; s=open(p,encoding='utf8').read()
s=s.replace("  BOSS_BLOW_WAIT: 110,","  BOSS_BLOW_WAIT: 150,")
s=s.replace("  BOSS_PUFF_GAP: 26,","  BOSS_PUFF_GAP: 40,")
open(p,'w',encoding='utf8').write(s)
p='tests/bot.js'; s=open(p,encoding='utf8').read()
a=s.index("    function bossFight(state, want) {")
b=s.index("    function decide(state) {")
s=s[:a]+"""    function bossFight(state, want) {
      var p = state.player, b = state.boss, world = state.world;
      if (b.state === 'dead') return false;
      var home = world.gateCol * T + BOSS_HOME_X;
      var px = p.x + p.w / 2, pcy = p.y + p.h / 2;
      if (p.jumping) { want.jump = true; return true; }
      if (p.mouth) {
        if (p.facing > 0) tap(want, 'action'); else want.right = true;
        return true;
      }
      var lowPuff = state.enemies.some(function (e) {
        return e.type === 'bosspuff' && e.x - (p.x + p.w) < PUFF_JUMP_X && e.x + e.w > p.x && Math.abs(e.y + e.h / 2 - pcy) < 12;
      });
      if (lowPuff && p.onGround) { tap(want, 'jump'); return true; }
      var overhead = null, roller = null, rollerD = Infinity;
      state.enemies.forEach(function (e) {
        if (e.type !== 'apple' || e.caught) return;
        var dx = e.x + e.w / 2 - px;
        if (!e.rolling && Math.abs(dx) < APPLE_DODGE_X && e.y < p.y) overhead = e;
        if (e.rolling && Math.abs(dx) < rollerD && Math.abs(dx) < APPLE_CHASE_X) { rollerD = Math.abs(dx); roller = e; }
      });
      var caught = state.enemies.some(function (e) { return e.caught; });
      if (caught) { inhale(want, p); return true; }
      if (overhead) { if (overhead.x + overhead.w / 2 <= px) want.right = true; else want.left = true; return true; }
      if (roller) {
        var dir = roller.x + roller.w / 2 < px ? -1 : 1;
        if (p.facing !== dir) { if (dir < 0) want.left = true; else want.right = true; return true; }
        inhale(want, p);
        return true;
      }
      if (px < home - 8) want.right = true;
      else if (px > home + 8) want.left = true;
      else if (p.facing < 0) want.right = true;
      return true;
    }

"""+s[b:]
s=s.replace("  var THREAT_X = 56, THREAT_Y = 18, AIR_PUFF_X = 30;","  var THREAT_X = 56, THREAT_Y = 18, AIR_PUFF_X = 30;\n  var BOSS_HOME_X = 96, PUFF_JUMP_X = 30, APPLE_DODGE_X = 16, APPLE_CHASE_X = 80;")
open(p,'w',encoding='utf8').write(s)
EOF
node .tmp/run.js 2>&1 | grep -v "^  \.\." | sed -n '/arenaLock/,$p' | head -40

OUT
6381 arenaLock  x=386.5 y=16.1 hp=6 lives=2
6530 hurt  x=390.1 y=17.3 hp=5 lives=2
6747 hurt  x=389.5 y=16.0 hp=4 lives=2
6835 bossHit  x=391.5 y=17.3 hp=4 lives=2
6985 hurt  x=389.7 y=16.0 hp=3 lives=2
7189 bossHit  x=389.3 y=17.3 hp=3 lives=2
7311 hurt  x=389.2 y=16.0 hp=2 lives=2
7396 bossHit  x=392.0 y=17.3 hp=2 lives=2
7416 hurt  x=392.0 y=17.3 hp=1 lives=2
7478 bossHit  x=389.3 y=14.5 hp=1 lives=2
7514 hurt  x=389.3 y=14.6 hp=0 lives=2
7514 death  x=389.3 y=14.6 hp=0 lives=2
7634 respawn  x=381.1 y=17.3 hp=6 lives=1
7710 arenaLock  x=386.5 y=16.1 hp=6 lives=1
7859 hurt  x=389.6 y=17.3 hp=5 lives=1
8075 hurt  x=389.6 y=16.0 hp=4 lives=1
8164 bossHit  x=391.4 y=17.3 hp=4 lives=1
8313 hurt  x=389.8 y=16.0 hp=3 lives=1
8517 bossHit  x=389.4 y=17.3 hp=3 lives=1
8639 hurt  x=389.2 y=16.0 hp=2 lives=1
8724 bossHit  x=392.0 y=17.3 hp=2 lives=1
8745 hurt  x=392.0 y=17.3 hp=1 lives=1
8807 bossHit  x=389.3 y=14.5 hp=1 lives=1
8843 hurt  x=389.3 y=14.6 hp=0 lives=1
8843 death  x=389.3 y=14.6 hp=0 lives=1
8963 gameOver  x=389.3 y=14.6 hp=0 lives=0
9008 respawn  x=381.1 y=17.3 hp=6 lives=3
9071 arenaLock  x=386.5 y=15.5 hp=6 lives=3
9220 hurt  x=389.6 y=17.3 hp=5 lives=3
9437 hurt  x=389.5 y=16.0 hp=4 lives=3
9525 bossHit  x=391.5 y=17.3 hp=4 lives=3
9675 hurt  x=389.7 y=16.0 hp=3 lives=3
9879 bossHit  x=389.3 y=17.3 hp=3 lives=3
10001 hurt  x=389.2 y=16.0 hp=2 lives=3
10086 bossHit  x=392.0 y=17.3 hp=2 lives=3
10106 hurt  x=392.0 y=17.3 hp=1 lives=3
10168 bossHit  x=389.3 y=14.5 hp=1 lives=3
10204 hurt  x=389.3 y=14.6 hp=0 lives=3
10204 death  x=389.3 y=14.6 hp=0 lives=3
10324 respawn  x=381.1 y=17.3 hp=6 lives=2
Bash Show arena damage sources after the change
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && node .tmp/dbg.js 7 6381 2>&1 | head -40

OUT
6530 inhaleStop,hurt P 6241.8 276.0 inh false mouth null held {"left":false,"right":false,"jump":false,"action":true}
    apple  6242.0 264.5 caught false stun 0 harm true
6747 hurt P 6232.0 256.5 inh false mouth null held {"left":false,"right":false,"jump":false,"action":false}
    bosspuff  6225.0 266.6 caught false stun 0 harm true
6985 hurt P 6235.3 256.5 inh false mouth null held {"left":false,"right":false,"jump":false,"action":false}
    bosspuff  6228.0 267.4 caught false stun 0 harm true
7311 hurt P 6226.4 256.5 inh false mouth null held {"left":false,"right":false,"jump":false,"action":false}
    bosspuff  6219.0 266.0 caught false stun 0 harm true
7416 inhaleStart,inhaleStop,hurt P 6271.9 276.0 inh false mouth null held {"left":false,"right":false,"jump":false,"action":true}
    apple  6273.8 264.5 caught false stun 0 harm true
7514 hurt,death P 6228.5 233.0 inh false mouth null held {"left":false,"right":false,"jump":true,"action":false}
    bosspuff  6198.0 269.7 caught false stun 0 harm true
    bosspuff  6240.0 244.0 caught false stun 0 harm true
7859 inhaleStop,hurt P 6233.0 276.0 inh false mouth null held {"left":false,"right":false,"jump":false,"action":true}
    apple  6195.4 276.0 caught false stun 0 harm true
    apple  6242.0 264.5 caught false stun 0 harm true
8:49 PM
Puff hits come from jumping too early (it lands on the puff), and apple hits from apples falling while it's busy inhaling. I'll tune the bot's jump timing and dodge priority:



Bash Tune bot boss timing and rerun
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && python - <<'EOF'
p='tests/bot.js'; s=open(p,encoding='utf8').read()
s=s.replace("PUFF_JUMP_X = 30,","PUFF_JUMP_X = 14,")
s=s.replace("""      if (caught) { inhale(want, p); return true; }
      if (overhead) { if (overhead.x + overhead.w / 2 <= px) want.right = true; else want.left = true; return true; }""","""      if (overhead) { if (overhead.x + overhead.w / 2 <= px) want.right = true; else want.left = true; return true; }
      if (caught) { inhale(want, p); return true; }""")
open(p,'w',encoding='utf8').write(s)
EOF
node .tmp/run.js 2>&1 | grep -v "^  \.\." | sed -n '/arenaLock/,$p' | head -30; node .tmp/run.js | tail -1

OUT
6381 arenaLock  x=386.5 y=16.1 hp=6 lives=2
6530 hurt  x=390.1 y=17.3 hp=5 lives=2
6855 bossHit  x=389.2 y=17.3 hp=5 lives=2
6922 bossHit  x=389.2 y=17.3 hp=5 lives=2
7192 bossHit  x=388.9 y=17.3 hp=5 lives=2
7337 hurt  x=390.8 y=17.3 hp=4 lives=2
7380 bossHit  x=392.6 y=17.3 hp=4 lives=2
7461 bossHit  x=391.3 y=17.3 hp=4 lives=2
7536 hurt  x=390.3 y=17.3 hp=3 lives=2
7581 bossHit  x=392.3 y=17.3 hp=3 lives=2
7731 bossDefeated  x=389.7 y=17.3 hp=3 lives=3
7770 win  x=392.2 y=12.2 hp=3 lives=3
END mode win time 126.8s maxCol 392.9 score 24730 deaths 1 continues 0
END mode win time 126.8s maxCol 392.9 score 24730 deaths 1 continues 0
8:49 PM
You've hit your session limit · resets 12:30am (America/Denver)

DESIGN.md
continue where you left off
Idle 12h 47m. The prompt cache has likely expired, so your next message will re-cache about 263k tokens.
continue where you left off
Continuing the step that was interrupted when the window reloaded.
The bot now clears the entire level, boss included, with only one death in about 2 minutes of game time. Now I'll verify the visuals in a real browser, starting with a Chrome DevTools helper that the smoke test will also use.
Write c:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\tests\cdp.mjs
124 lines
// Minimal headless-Chrome driver over the DevTools protocol. No dependencies:
// uses child_process, fetch and Node's built-in WebSocket (Node 22+).
import { spawn, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export function findChrome() {
  const local = process.env.LOCALAPPDATA || '';
  const candidates = [
    process.env.CHROME_PATH,
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
    local && path.join(local, 'Google/Chrome/Application/chrome.exe'),
    'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
    'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser'
  ];
  return candidates.find((p) => p && fs.existsSync(p));
}

class Client {
  constructor(ws) {
    this.ws = ws;
    this.nextId = 0;
    this.pending = new Map();
    this.listeners = [];
    ws.addEventListener('message', (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject } = this.pending.get(msg.id);
        this.pending.delete(msg.id);
        if (msg.error) reject(new Error(msg.error.message)); else resolve(msg.result);
      } else if (msg.method) {
        this.listeners.forEach((fn) => fn(msg));
      }
    });
  }
  send(method, params = {}) {
    const id = ++this.nextId;
    this.ws.send(JSON.stringify({ id, method, params }));
    return new Promise((resolve, reject) => this.pending.set(id, { resolve, reject }));
  }
  on(fn) { this.listeners.push(fn); }
  async evaluate(expression) {
    const r = await this.send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    if (r.exceptionDetails) throw new Error('Page evaluate failed: ' + (r.exceptionDetails.exception?.description || r.exceptionDetails.text));
    return r.result.value;
  }
  async screenshot(file) {
    const r = await this.send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(file, Buffer.from(r.data, 'base64'));
  }
}

const KEYS = {
  Space: { key: ' ', vk: 32 }, Enter: { key: 'Enter', vk: 13 }, ArrowLeft: { key: 'ArrowLeft', vk: 37 },
  ArrowRight: { key: 'ArrowRight', vk: 39 }, KeyP: { key: 'p', vk: 80 }, KeyM: { key: 'm', vk: 77 },
  KeyR: { key: 'r', vk: 82 }, Escape: { key: 'Escape', vk: 27 }
};

export async function key(client, code, type) {
  const k = KEYS[code];
  await client.send('Input.dispatchKeyEvent', {
    type, code, key: k.key, windowsVirtualKeyCode: k.vk, nativeVirtualKeyCode: k.vk,
    text: type === 'keyDown' && k.key === ' ' ? ' ' : undefined
  });
}

// Launches headless Chrome with a throwaway profile and returns a connected page client.
export async function launch(profileDir, { width = 900, height = 760 } = {}) {
  const exe = findChrome();
  if (!exe) throw new Error('Chrome/Edge not found. Set CHROME_PATH.');
  fs.rmSync(profileDir, { recursive: true, force: true });
  fs.mkdirSync(profileDir, { recursive: true });
  const proc = spawn(exe, [
    '--headless=new', '--remote-debugging-port=0', `--user-data-dir=${profileDir}`,
    '--no-first-run', '--no-default-browser-check', '--disable-extensions', '--disable-sync',
    '--disable-background-networking', '--mute-audio', '--autoplay-policy=no-user-gesture-required',
    `--window-size=${width},${height}`, 'about:blank'
  ], { stdio: 'ignore' });
  const browser = { proc, profileDir, client: null };
  try {
    const portFile = path.join(profileDir, 'DevToolsActivePort');
    let port = 0;
    for (let i = 0; i < 200 && !port; i++) {
      if (fs.existsSync(portFile)) port = Number(fs.readFileSync(portFile, 'utf8').split('\n')[0]) || 0;
      if (!port) await sleep(100);
    }
    if (!port) throw new Error('Chrome did not open a DevTools port');
    let page = null;
    for (let i = 0; i < 50 && !page; i++) {
      const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
      page = list.find((t) => t.type === 'page');
      if (!page) await sleep(100);
    }
    const ws = new WebSocket(page.webSocketDebuggerUrl);
    await new Promise((res, rej) => { ws.addEventListener('open', res, { once: true }); ws.addEventListener('error', rej, { once: true }); });
    browser.client = new Client(ws);
    return browser;
  } catch (err) {
    await close(browser);
    throw err;
  }
}

// Always stops Chrome (and its child processes) and deletes the throwaway profile.
export async function close(browser) {
  if (!browser) return;
  try { if (browser.client) { await Promise.race([browser.client.send('Browser.close'), sleep(1500)]); browser.client.ws.close(); } } catch { /* already gone */ }
  const { proc } = browser;
  if (proc && proc.exitCode === null) {
    if (process.platform === 'win32') spawnSync('taskkill', ['/pid', String(proc.pid), '/T', '/F'], { stdio: 'ignore' });
    else proc.kill('SIGKILL');
  }
  for (let i = 0; i < 30; i++) {
    try { fs.rmSync(browser.profileDir, { recursive: true, force: true }); return; } catch { await sleep(200); }
  }
}

export { sleep };
9:38 AM
Continuing. Next I'll take screenshots in headless Chrome to check how it looks:



Bash Take browser screenshots of the game
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && cat > .tmp/shots.mjs <<'EOF'
import { launch, close, key, sleep } from '../tests/cdp.mjs';
import { pathToFileURL } from 'node:url';
import path from 'node:path';
const root = path.resolve('.');
const b = await launch(path.join(root, '.tmp', 'profile-shots'));
const errors = [];
try {
  const c = b.client;
  c.on((m) => {
    if (m.method === 'Runtime.exceptionThrown') errors.push(m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text);
    if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') errors.push(m.params.args.map(a => a.value || a.description).join(' '));
    if (m.method === 'Log.entryAdded' && m.params.entry.level === 'error') errors.push(m.params.entry.text + ' ' + (m.params.entry.url || ''));
  });
  await c.send('Runtime.enable'); await c.send('Log.enable'); await c.send('Page.enable');
  await c.send('Emulation.setDeviceMetricsOverride', { width: 768, height: 700, deviceScaleFactor: 1, mobile: false });
  await c.send('Page.navigate', { url: pathToFileURL(path.join(root, 'index.html')).href });
  await sleep(1200);
  await c.screenshot('.tmp/s1-title.png');
  await key(c, 'Space', 'keyDown'); await sleep(60); await key(c, 'Space', 'keyUp');
  await sleep(700);
  await key(c, 'ArrowRight', 'keyDown'); await sleep(1500); await key(c, 'ArrowRight', 'keyUp');
  await c.screenshot('.tmp/s2-run.png');
  await key(c, 'Enter', 'keyDown'); await sleep(300); await c.screenshot('.tmp/s3-inhale.png'); await sleep(600); await key(c, 'Enter', 'keyUp');
  await sleep(200);
  await c.screenshot('.tmp/s4-after.png');
  console.log('errors', errors);
} finally { await close(b); }
EOF
node .tmp/shots.mjs

OUT
errors []
Read C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\.tmp\s1-title.png
Read C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\.tmp\s2-run.png
Read C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\.tmp\s3-inhale.png
Everything renders correctly with no console errors, but I spotted two polish issues: missing spaces in the controls bar text and a missing outline on the title. I'll fix those, then write the smoke test to capture the rest of the level.
Bash Fix controls bar spacing and title outline
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && python - <<'EOF'
p='js/hud.js'; s=open(p,encoding='utf8').read()
s=s.replace("""      ['\\u2190\\u2192/AD', 'y'], ['MOVE ', 'w'], ['SPACE', 'y'], ['JUMP/FLY ', 'w'],
      ['ENTER', 'y'], ['INHALE/SPIT ', 'w'], ['P', 'y'], ['PAUSE ', 'w'], ['M', 'y'], ['MUTE', 'w']""","""      ['\\u2190\\u2192/AD', 'y'], [' MOVE  ', 'w'], ['SPACE', 'y'], [' JUMP/FLY  ', 'w'],
      ['ENTER', 'y'], [' INHALE/SPIT  ', 'w'], ['P', 'y'], [' PAUSE  ', 'w'], ['M', 'y'], [' MUTE', 'w']""")
s=s.replace("""    Font.draw(ctx, 'KIRBY', VW / 2, 22, 'p', { scale: 5, align: 'center', shadow: 'K' });""","""    [[-1, 0], [1, 0], [0, -1], [0, 1], [2, 2]].forEach(function (o) {
      Font.draw(ctx, 'KIRBY', VW / 2 + o[0], 22 + o[1], 'K', { scale: 5, align: 'center' });
    });
    Font.draw(ctx, 'KIRBY', VW / 2, 22, 'p', { scale: 5, align: 'center' });""")
open(p,'w',encoding='utf8').write(s)
EOF
grep -n "MOVE  \|'KIRBY'" js/hud.js | head

OUT
123:      ['←→/AD', 'y'], [' MOVE  ', 'w'], ['SPACE', 'y'], [' JUMP/FLY  ', 'w'],
150:      Font.draw(ctx, 'KIRBY', VW / 2 + o[0], 22 + o[1], 'K', { scale: 5, align: 'center' });
152:    Font.draw(ctx, 'KIRBY', VW / 2, 22, 'p', { scale: 5, align: 'center' });
9:39 AM
Now the browser smoke test:



Write C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\tests\smoke.mjs
152 lines
// Browser smoke test: opens index.html over file:// in headless Chrome (DevTools protocol,
// no dependencies), plays with real key events, then lets the test bot drive the real page's
// input to the boss and the win screen. Fails on any console error. Screenshots go to .tmp/.
// Run: node tests/smoke.mjs
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { launch, close, key, sleep } from './cdp.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const tmp = path.join(root, '.tmp');
const shots = path.join(tmp, 'screenshots');
fs.mkdirSync(shots, { recursive: true });

const errors = [];
let browser = null;
let failed = false;

async function hold(c, code, ms) {
  await key(c, code, 'keyDown');
  await sleep(ms);
  await key(c, code, 'keyUp');
}

async function step(name, fn) {
  try {
    await fn();
    console.log('ok   ' + name);
  } catch (err) {
    failed = true;
    console.log('FAIL ' + name + '\n     ' + err.message);
    throw err;
  }
}

try {
  browser = await launch(path.join(tmp, 'chrome-profile-' + process.pid));
  const c = browser.client;
  c.on((m) => {
    if (m.method === 'Runtime.exceptionThrown') {
      const d = m.params.exceptionDetails;
      errors.push('exception: ' + (d.exception?.description || d.text));
    }
    if (m.method === 'Runtime.consoleAPICalled' && (m.params.type === 'error' || m.params.type === 'assert')) {
      errors.push('console.' + m.params.type + ': ' + m.params.args.map((a) => a.value ?? a.description).join(' '));
    }
    if (m.method === 'Log.entryAdded' && m.params.entry.level === 'error') {
      errors.push('log: ' + m.params.entry.text + ' ' + (m.params.entry.url || ''));
    }
  });
  await c.send('Runtime.enable');
  await c.send('Log.enable');
  await c.send('Page.enable');
  await c.send('Emulation.setDeviceMetricsOverride', { width: 800, height: 720, deviceScaleFactor: 1, mobile: false });
  const state = (expr) => c.evaluate(`(function(){ var s = KirbyDebug.state(); return ${expr}; })()`);

  await step('page loads over file:// with no errors', async () => {
    await c.send('Page.navigate', { url: pathToFileURL(path.join(root, 'index.html')).href });
    await sleep(1500);
    assert.equal(await c.evaluate('typeof KirbyDebug'), 'object', 'game did not boot');
    assert.equal(await state('s.mode'), 'title');
    const colors = await c.evaluate(`(function(){
      var cv = document.getElementById('game'), d = cv.getContext('2d').getImageData(0, 0, cv.width, cv.height).data, seen = {};
      for (var i = 0; i < d.length; i += 4) seen[d[i] + ',' + d[i + 1] + ',' + d[i + 2]] = 1;
      return Object.keys(seen).length; })()`);
    assert.ok(colors > 8, 'canvas looks blank (' + colors + ' colours)');
    await c.screenshot(path.join(shots, '01-title.png'));
  });

  await step('Space starts the game', async () => {
    await hold(c, 'Space', 80);
    await sleep(600);
    assert.equal(await state('s.mode'), 'playing');
  });

  await step('arrow keys move Kirby right', async () => {
    const x0 = await state('s.player.x');
    await hold(c, 'ArrowRight', 900);
    const x1 = await state('s.player.x');
    assert.ok(x1 > x0 + 20, `x only went ${x0} -> ${x1}`);
    await c.screenshot(path.join(shots, '02-run.png'));
  });

  await step('holding Enter inhales', async () => {
    await key(c, 'Enter', 'keyDown');
    await sleep(300);
    assert.equal(await state('s.player.inhaling'), true);
    await c.screenshot(path.join(shots, '03-inhale.png'));
    await key(c, 'Enter', 'keyUp');
    await sleep(100);
  });

  await step('Space in the air flies', async () => {
    await hold(c, 'Space', 250);
    await sleep(100);
    await hold(c, 'Space', 60);
    await sleep(80);
    await hold(c, 'Space', 60);
    await sleep(120);
    assert.equal(await state('s.player.flying || !!s.player.mouth'), true, 'Kirby should be flying (or have a full mouth)');
    await c.screenshot(path.join(shots, '04-fly.png'));
    await sleep(1200);
  });

  await step('P pauses and resumes', async () => {
    await hold(c, 'KeyP', 60);
    await sleep(150);
    assert.equal(await state('s.mode'), 'paused');
    await c.screenshot(path.join(shots, '05-pause.png'));
    await hold(c, 'KeyP', 60);
    await sleep(150);
    assert.equal(await state('s.mode'), 'playing');
  });

  // Fast-forward with the test bot: it presses keys on the page's real input tracker.
  await c.evaluate(fs.readFileSync(path.join(root, 'tests', 'bot.js'), 'utf8'));
  const runBot = (until, maxTicks) => c.evaluate(`(function(){
    var bot = window.__bot || (window.__bot = KirbyBot.create());
    var s = KirbyDebug.state(), n = 0;
    while (n < ${maxTicks} && !(${until})) { bot.apply(s, KirbyDebug.input); KirbyDebug.tick(); n++; }
    bot.releaseAll(KirbyDebug.input);
    KirbyDebug.draw();
    return { ticks: n, mode: s.mode, x: s.player.x, boss: s.boss && s.boss.state };
  })()`);

  await step('bot reaches the boss arena using key presses', async () => {
    const r = await runBot(`s.arenaLocked && s.boss.state === 'blow' && s.boss.timer > 30`, 60 * 60 * 15);
    assert.ok(r.boss === 'blow', 'did not reach the boss: ' + JSON.stringify(r));
    await c.screenshot(path.join(shots, '06-boss.png'));
  });

  await step('bot beats the boss and wins', async () => {
    const r = await runBot(`s.mode === 'win' && s.screenTimer === 0`, 60 * 60 * 15);
    assert.equal(r.mode, 'win', 'did not win: ' + JSON.stringify(r));
    await sleep(100);
    await c.screenshot(path.join(shots, '07-win.png'));
  });

  await step('no console errors', async () => {
    assert.deepEqual(errors, []);
  });
} catch (err) {
  failed = true;
  if (!String(err.message).includes('FAIL')) console.error(err);
} finally {
  await close(browser);
  if (errors.length) console.log('console errors:\n  ' + errors.join('\n  '));
  console.log(failed ? '\nSMOKE TEST FAILED' : '\nSMOKE TEST PASSED (screenshots in .tmp/screenshots)');
  process.exitCode = failed ? 1 : 0;
}
Bash Run the browser smoke test
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && node tests/smoke.mjs; ls .tmp; tasklist 2>/dev/null | grep -i chrome | head -3

OUT
ok   page loads over file:// with no errors
ok   Space starts the game
ok   arrow keys move Kirby right
ok   holding Enter inhales
ok   Space in the air flies
ok   P pauses and resumes
ok   bot reaches the boss arena using key presses
ok   bot beats the boss and wins
ok   no console errors

SMOKE TEST PASSED (screenshots in .tmp/screenshots)
at.js
dbg.js
dump.js
run.js
s1-title.png
s2-run.png
s3-inhale.png
s4-after.png
screenshots/
shots.mjs
sim.js
9:40 AM
The smoke test passes, Chrome is closed, and the profile folder was deleted. Let me look at the screenshots:



Read C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\.tmp\screenshots\04-fly.png
Read C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\.tmp\screenshots\06-boss.png
Read C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\.tmp\screenshots\07-win.png
The boss, flying sprite, and win screen all look correct, but the control bar arrow glyphs render as "++" — I'll redraw them as thinner arrowheads, then screenshot the Fort, Climb, Windy Sky, and Gauntlet sections.
Bash Fix arrow glyphs and take a screenshot tour
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && python - <<'EOF'
p='js/hud.js'; s=open(p,encoding='utf8').read()
import re
s=re.sub(r"'(\\u2190|←)': '[^']*', '(\\u2192|→)': '[^']*',", lambda m: "'\\u2190': '..#../.#.../#####/.#.../..#..', '\\u2192': '..#../...#./#####/...#./..#..',", s)
open(p,'w',encoding='utf8').write(s)
EOF
grep -n "u2190\|←" js/hud.js | head -3
cat > .tmp/tour.mjs <<'EOF'
import { launch, close } from '../tests/cdp.mjs';
import { pathToFileURL } from 'node:url';
import fs from 'node:fs';
import path from 'node:path';
const root = path.resolve('.');
const b = await launch(path.join(root, '.tmp', 'profile-tour'));
try {
  const c = b.client;
  await c.send('Runtime.enable'); await c.send('Page.enable');
  await c.send('Emulation.setDeviceMetricsOverride', { width: 560, height: 500, deviceScaleFactor: 1, mobile: false });
  await c.send('Page.navigate', { url: pathToFileURL(path.join(root, 'index.html')).href });
  await new Promise(r => setTimeout(r, 1200));
  await c.evaluate(fs.readFileSync('tests/bot.js', 'utf8'));
  const cols = process.argv.slice(2).map(Number);
  for (const col of cols) {
    const r = await c.evaluate(`(function(){ var bot = window.__bot || (window.__bot = KirbyBot.create()); var s = KirbyDebug.state(), n = 0;
      while (n < 60000 && !(s.mode === 'playing' && s.player.x > ${col * 16})) { bot.apply(s, KirbyDebug.input); KirbyDebug.tick(); n++; }
      for (var k = 0; k < 20; k++) { bot.apply(s, KirbyDebug.input); KirbyDebug.tick(); }
      KirbyDebug.draw(); return s.player.x / 16; })()`);
    await c.screenshot(`.tmp/tour-${col}.png`);
    console.log(col, r);
  }
} finally { await close(b); }
EOF
node .tmp/tour.mjs 70 125 160 215 235 270 300 345

OUT
19:    '←': '..#../.#.../#####/.#.../..#..', '→': '..#../...#./#####/...#./..#..',
123:      ['←→/AD', 'y'], [' MOVE  ', 'w'], ['SPACE', 'y'], [' JUMP/FLY  ', 'w'],
159:      [['← →  OR  A D', 'y'], [' MOVE', 'w']],
70 71.67312500000016
125 126.58625000000019
160 162.28124999999991
215 216.5699999999989
235 236.57562499999963
270 271.2674202814452
300 301.31533380899026
345 345.25
Read C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\.tmp\tour-160.png
Read C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\.tmp\tour-215.png
Read C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\.tmp\tour-270.png
Read C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\.tmp\tour-125.png
9:41 AM
The middle stretches render well: the cave backdrop in the Fort, the shaft in the Climb, the windy sky with flyers and spikies, and the Cliffs. Now the unit tests. First a shared helper:



Write C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\tests\helpers.js
63 lines
// Shared helpers for the unit tests: small hand-made levels and input snapshots.
const { CONST } = require('../js/logic/constants.js');
const { Physics } = require('../js/logic/physics.js');
const { World } = require('../js/logic/world.js');
const { Enemies } = require('../js/logic/enemies.js');
const { Player } = require('../js/logic/player.js');
const { Boss } = require('../js/logic/boss.js');
const { Game } = require('../js/logic/game.js');

const T = CONST.TILE;
const GROUND_ROW = 9;
const FLOOR_Y = GROUND_ROW * T;

// A one-section test level: flat ground at GROUND_ROW, plus whatever is passed in.
function level(section) {
  return { name: 'test', height: 12, groundRow: GROUND_ROW, sections: [Object.assign({ name: 'TEST', width: 40, put: [[2, 8, 'P']] }, section)] };
}

// An input snapshot with every key up unless overridden.
function keys(o) {
  return Object.assign({
    left: false, right: false, jump: false, action: false, pause: false, mute: false, restart: false,
    leftPressed: false, rightPressed: false, jumpPressed: false, actionPressed: false,
    pausePressed: false, mutePressed: false, restartPressed: false
  }, o);
}
const NONE = keys({});
const JUMP = keys({ jump: true, jumpPressed: true });
const ACTION = keys({ action: true, actionPressed: true });
const HOLD_ACTION = keys({ action: true });

// Creates a game already in the playing state.
function playing(section, opts) {
  const s = Game.create(level(section || {}), opts);
  s.screenTimer = 0;
  Game.update(s, JUMP);
  if (s.mode !== 'playing') throw new Error('test game did not start');
  return s;
}

function run(state, n, input) {
  for (let i = 0; i < n; i++) Game.update(state, input || NONE);
}

// Ticks until the player stands on the ground (or gives up).
function settle(state) {
  for (let i = 0; i < 200 && !state.player.onGround; i++) Game.update(state, NONE);
}

function eventsDuring(state, n, input) {
  const seen = [];
  for (let i = 0; i < n; i++) {
    Game.update(state, typeof input === 'function' ? input(i) : (input || NONE));
    seen.push(...state.events);
  }
  return seen;
}

module.exports = {
  CONST, Physics, World, Enemies, Player, Boss, Game, T, GROUND_ROW, FLOOR_Y,
  level, keys, NONE, JUMP, ACTION, HOLD_ACTION, playing, run, settle, eventsDuring
};
Write C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\tests\physics.test.js
80 lines
const test = require('node:test');
const assert = require('node:assert/strict');
const { Physics, World, T, level, FLOOR_Y } = require('./helpers.js');

function body(x, y, vx, vy) {
  return { x, y, w: 12, h: 12, vx, vy };
}

test('a very fast body stops at a one-tile wall instead of tunnelling through it', () => {
  const world = World.build(level({ put: [[2, 8, 'P'], [10, 8, '#']] }));
  for (const speed of [5, 17, 40, 100, 500]) {
    const b = body(4 * T, 8 * T + 2, speed, 0);
    Physics.moveBody(world, b);
    assert.equal(b.x, 10 * T - b.w, `speed ${speed}`);
    assert.equal(b.hitWall, 1);
    assert.equal(b.vx, 0);
  }
});

test('moving left into a wall also stops flush against it', () => {
  const world = World.build(level({ put: [[2, 8, 'P'], [3, 8, '#']] }));
  const b = body(12 * T, 8 * T + 2, -300, 0);
  Physics.moveBody(world, b);
  assert.equal(b.x, 4 * T);
  assert.equal(b.hitWall, -1);
});

test('a very fast fall lands on a one-tile floor instead of passing through', () => {
  const world = World.build(level({ gaps: [[0, 40]], put: [[2, 8, 'P'], [6, 6, '#']] }));
  const b = body(6 * T + 2, 0, 0, 250);
  Physics.moveBody(world, b);
  assert.equal(b.y, 6 * T - b.h);
  assert.equal(b.onGround, true);
});

test('a fast upward move stops under a one-tile ceiling', () => {
  const world = World.build(level({ put: [[2, 8, 'P'], [6, 3, '=']] }));
  const b = body(6 * T + 2, 7 * T, 0, -200);
  Physics.moveBody(world, b);
  assert.equal(b.y, 4 * T);
  assert.equal(b.hitCeiling, true);
});

test('diagonal speed is split into sub-steps no bigger than MAX_SUBSTEP', () => {
  const world = World.build(level({ put: [[2, 8, 'P'], [12, 7, '##'], [12, 8, '##']] }));
  const b = body(4 * T, 7 * T, 90, 30);
  Physics.moveBody(world, b);
  assert.ok(b.x + b.w <= 12 * T, 'went through the block');
});

test('one-way platforms hold you from above but let you jump up through them', () => {
  const world = World.build(level({ put: [[2, 8, 'P'], [6, 6, '---']] }));
  const falling = body(6 * T + 2, 6 * T - 20, 0, 12);
  Physics.moveBody(world, falling);
  assert.equal(falling.y, 6 * T - 12);
  assert.equal(falling.onGround, true);
  const rising = body(6 * T + 2, 7 * T, 0, -12);
  Physics.moveBody(world, rising);
  assert.equal(rising.y, 7 * T - 12, 'should pass through from below');
});

test('the level edges act as walls; the ground stops falling bodies', () => {
  const world = World.build(level({}));
  const b = body(10, FLOOR_Y - 30, -50, 50);
  Physics.moveBody(world, b);
  assert.equal(b.x, 0);
  assert.equal(b.y, FLOOR_Y - 12);
});

test('gaps in the level are detected as pits', () => {
  const world = World.build(level({ gaps: [[5, 8], [20, 21]] }));
  assert.deepEqual(world.gaps, [{ x0: 5 * T, x1: 8 * T }, { x0: 20 * T, x1: 21 * T }]);
});

test('line of sight is blocked by solid tiles', () => {
  const world = World.build(level({ put: [[2, 8, 'P'], [6, 7, '=']] }));
  assert.equal(Physics.clearLine(world, 4 * T, 7.5 * T, 9 * T, 7.5 * T), false);
  assert.equal(Physics.clearLine(world, 4 * T, 5.5 * T, 9 * T, 5.5 * T), true);
});
Write C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\tests\movement.test.js
113 lines
// Jumping, flying and their limits.
const test = require('node:test');
const assert = require('node:assert/strict');
const { CONST, playing, run, settle, keys, NONE, JUMP, eventsDuring, FLOOR_Y } = require('./helpers.js');

const HOLD_JUMP = keys({ jump: true });

function jumpHeight(state, hold) {
  settle(state);
  const y0 = state.player.y;
  let minY = y0;
  Game_update(state, JUMP);
  for (let i = 0; i < 200 && !state.player.onGround; i++) {
    Game_update(state, i < hold ? HOLD_JUMP : NONE);
    minY = Math.min(minY, state.player.y);
  }
  return y0 - minY;
}
const { Game } = require('./helpers.js');
const Game_update = Game.update;

test('a held jump reaches the expected height, under three tiles', () => {
  const s = playing();
  const h = jumpHeight(s, 100);
  const expected = CONST.JUMP_VY * CONST.JUMP_VY / (2 * CONST.GRAVITY);
  assert.ok(Math.abs(h - expected) < 4, `jump height ${h}, expected about ${expected}`);
  assert.ok(h < 3 * CONST.TILE);
});

test('releasing Space early gives a shorter jump', () => {
  const s = playing();
  const tall = jumpHeight(s, 100);
  const short = jumpHeight(s, 2);
  assert.ok(short < tall * 0.6, `short ${short} vs tall ${tall}`);
});

test('tapping Space in the air starts flying and each flap rises at a capped speed', () => {
  const s = playing();
  settle(s);
  Game.update(s, JUMP);
  run(s, 20);
  Game.update(s, JUMP);
  assert.equal(s.player.flying, true);
  assert.ok(s.player.vy >= CONST.FLAP_VY - 1e-9, 'a flap must not exceed FLAP_VY');
});

test('flight is unlimited: hundreds of flaps keep Kirby airborne', () => {
  const s = playing();
  settle(s);
  let airborneAfter = 0;
  for (let i = 0; i < 400; i++) {
    Game.update(s, i % 12 === 0 ? JUMP : NONE);
    if (i > 30 && !s.player.onGround) airborneAfter++;
  }
  assert.equal(s.player.flying, true);
  assert.equal(airborneAfter, 400 - 31);
});

test('flying can never go above the fly ceiling', () => {
  const s = playing();
  settle(s);
  let minY = Infinity;
  for (let i = 0; i < 600; i++) {
    Game.update(s, i % 4 === 0 ? JUMP : NONE);
    minY = Math.min(minY, s.player.y);
  }
  assert.equal(minY, CONST.FLY_CEILING);
});

test('falling while flying is slow (floaty) and landing deflates', () => {
  const s = playing();
  settle(s);
  Game.update(s, JUMP);
  run(s, 5);
  Game.update(s, JUMP);
  let maxFall = 0;
  const seen = eventsDuring(s, 300, () => { maxFall = Math.max(maxFall, s.player.vy); return NONE; });
  assert.ok(maxFall <= CONST.FLY_MAX_FALL + 1e-9);
  assert.ok(seen.some((e) => e.type === 'deflate'));
  assert.equal(s.player.flying, false);
});

test('with a full mouth Kirby cannot fly: Space in the air does nothing but warn', () => {
  const s = playing();
  settle(s);
  s.player.mouth = { kind: 'walker', count: 1 };
  Game.update(s, JUMP);
  run(s, 10);
  const seen = eventsDuring(s, 1, JUMP);
  assert.equal(s.player.flying, false);
  assert.ok(seen.some((e) => e.type === 'noFly'));
  settle(s);
  assert.equal(s.player.y, FLOOR_Y - CONST.PLAYER_H);
});

test('a full mouth also makes Kirby jump lower and run slower', () => {
  const s = playing();
  const normal = jumpHeight(s, 100);
  s.player.mouth = { kind: 'walker', count: 1 };
  const full = jumpHeight(s, 100);
  assert.ok(full < normal * 0.75, `full ${full} vs normal ${normal}`);
  run(s, 120, keys({ right: true }));
  assert.ok(Math.abs(s.player.vx) <= CONST.FULL_MAX_SPEED + 1e-9);
});

test('running accelerates to RUN_MAX and no further', () => {
  const s = playing();
  settle(s);
  run(s, 60, keys({ right: true }));
  assert.equal(s.player.vx, CONST.RUN_MAX);
  assert.equal(s.player.facing, 1);
});
9:41 AM
I left an awkward alias at the top of movement.test.js; tidying it before running:



Bash Run physics and movement tests
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && python - <<'EOF'
p='tests/movement.test.js'; s=open(p,encoding='utf8').read()
s=s.replace("const { CONST, playing, run, settle, keys, NONE, JUMP, eventsDuring, FLOOR_Y } = require('./helpers.js');","const { CONST, Game, playing, run, settle, keys, NONE, JUMP, eventsDuring, FLOOR_Y } = require('./helpers.js');")
s=s.replace("""const { Game } = require('./helpers.js');
const Game_update = Game.update;
""","")
s=s.replace("Game_update(","Game.update(")
open(p,'w',encoding='utf8').write(s)
EOF
node --test tests/physics.test.js tests/movement.test.js 2>&1 | grep -E "^not ok|^# (pass|fail)|Error|expected|actual" | head -30

OUT
# Subtest: a held jump reaches the expected height, under three tiles
ok 1 - a held jump reaches the expected height, under three tiles
not ok 3 - tapping Space in the air starts flying and each flap rises at a capped speed
  name: 'AssertionError'
  expected: true
  actual: false
not ok 10 - a very fast body stops at a one-tile wall instead of tunnelling through it
  name: 'AssertionError'
  expected: 148
  actual: 69
# pass 16
# fail 2
9:41 AM
Both failures are mistakes in the tests, not the game. One test let Kirby land before the second press, and the other used speeds too slow to reach the wall in a single move:



Bash Fix the two test mistakes and rerun
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && python - <<'EOF'
p='tests/movement.test.js'; s=open(p,encoding='utf8').read()
s=s.replace("""  Game.update(s, JUMP);
  run(s, 20);
  Game.update(s, JUMP);
  assert.equal(s.player.flying, true);""","""  Game.update(s, JUMP);
  run(s, 5, HOLD_JUMP);
  Game.update(s, JUMP);
  assert.equal(s.player.flying, true);""")
open(p,'w',encoding='utf8').write(s)
p='tests/physics.test.js'; s=open(p,encoding='utf8').read()
s=s.replace("""  for (const speed of [5, 17, 40, 100, 500]) {""","""  // The wall is 84px away: every one of these speeds would skip past it in a single naive step.
  for (const speed of [100, 250, 1000, 5000]) {""")
open(p,'w',encoding='utf8').write(s)
EOF
node --test tests/physics.test.js tests/movement.test.js 2>&1 | grep -E "^not ok|^# (pass|fail)|expected|actual" | head

OUT
# Subtest: a held jump reaches the expected height, under three tiles
ok 1 - a held jump reaches the expected height, under three tiles
# pass 18
# fail 0
9:42 AM
Physics and movement tests pass. Next, the inhale, swallow and spit tests:



Write C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\tests\inhale.test.js
206 lines
// Inhale cone, swallowing, spitting and star blocks.
const test = require('node:test');
const assert = require('node:assert/strict');
const {
  CONST, Physics, Player, Enemies, Game, T, playing, run, settle, keys, NONE, ACTION, HOLD_ACTION, eventsDuring
} = require('./helpers.js');

function kirbyAt(x, y, facing) {
  const p = Player.create(x, y);
  p.facing = facing;
  return p;
}
function box(cx, cy, size) {
  return { x: cx - (size || 12) / 2, y: cy - (size || 12) / 2, w: size || 12, h: size || 12 };
}

test('inhale cone: in front and in range is inside; behind or too far is outside', () => {
  const p = kirbyAt(100, 100, 1);
  const m = Player.mouthPoint(p);
  assert.equal(Player.inInhaleCone(p, box(m.x + 20, m.y)), true);
  assert.equal(Player.inInhaleCone(p, box(m.x + CONST.INHALE_RANGE - 1, m.y)), true);
  assert.equal(Player.inInhaleCone(p, box(m.x + CONST.INHALE_RANGE + 2, m.y)), false);
  assert.equal(Player.inInhaleCone(p, box(m.x - 20, m.y)), false, 'behind Kirby');
});

test('inhale cone widens with distance', () => {
  const p = kirbyAt(100, 100, 1);
  const m = Player.mouthPoint(p);
  const dy = CONST.INHALE_HALF_HEIGHT + 8;
  assert.equal(Player.inInhaleCone(p, box(m.x + 4, m.y - dy)), false, 'too high near the mouth');
  assert.equal(Player.inInhaleCone(p, box(m.x + 50, m.y - dy)), true, 'same height further out is inside');
});

test('inhale cone follows the facing direction', () => {
  const p = kirbyAt(100, 100, -1);
  const m = Player.mouthPoint(p);
  assert.equal(m.x, 100);
  assert.equal(Player.inInhaleCone(p, box(m.x - 20, m.y)), true);
  assert.equal(Player.inInhaleCone(p, box(m.x + 30, m.y)), false);
});

test('holding Enter pulls a walker in and swallows it: mouth fills and score goes up', () => {
  const s = playing({ put: [[2, 8, 'P'], [6, 8, 'w']] });
  settle(s);
  const score = s.score;
  const seen = eventsDuring(s, 90, HOLD_ACTION);
  assert.ok(seen.some((e) => e.type === 'swallow'));
  assert.deepEqual(s.player.mouth, { kind: 'walker', count: 1 });
  assert.equal(s.score - score, CONST.SCORE.walker);
  assert.equal(s.enemies.filter((e) => e.type === 'walker').length, 0);
  assert.equal(s.player.inhaling, false, 'inhaling stops once something is swallowed');
});

test('enemies behind Kirby are not pulled in', () => {
  const s = playing({ put: [[8, 8, 'P'], [4, 8, 'w']] });
  settle(s);
  const w = s.enemies[0];
  s.player.facing = 1;
  s.player.inhaling = true;
  Player.applyInhale(s);
  assert.equal(w.caught, false);
});

test('a spiky enemy inside the cone is never pulled in', () => {
  const s = playing({ put: [[2, 8, 'P'], [5, 8, 'g']] });
  settle(s);
  const spiky = s.enemies[0];
  const p = s.player;
  spiky.y = p.y + p.h / 2 - spiky.h / 2;
  assert.equal(Player.inInhaleCone(p, spiky), true, 'test setup: spiky is in the cone');
  p.inhaling = true;
  for (let i = 0; i < 60; i++) Player.applyInhale(s);
  assert.equal(spiky.caught, false);
  assert.equal(p.mouth, null);
});

test('walls block the inhale (line of sight)', () => {
  const s = playing({ put: [[2, 8, 'P'], [5, 7, '='], [5, 8, '='], [7, 8, 'w']] });
  settle(s);
  run(s, 100, HOLD_ACTION);
  assert.equal(s.player.mouth, null);
  assert.equal(s.enemies.filter((e) => e.type === 'walker').length, 1);
});

test('Kirby cannot walk while inhaling', () => {
  const s = playing();
  settle(s);
  run(s, 30, keys({ right: true }));
  run(s, 40, keys({ right: true, action: true }));
  assert.equal(s.player.inhaling, true);
  assert.equal(s.player.vx, 0);
});

test('pressing Enter with a full mouth spits a star that defeats another enemy', () => {
  const s = playing({ put: [[2, 8, 'P'], [6, 8, 'w'], [16, 8, 'w']] });
  settle(s);
  run(s, 90, HOLD_ACTION);
  assert.ok(s.player.mouth);
  run(s, 1, NONE);
  const before = s.score;
  const seen = eventsDuring(s, 1, ACTION);
  assert.equal(s.player.mouth, null);
  assert.ok(seen.some((e) => e.type === 'spit'));
  assert.equal(s.projectiles.length, 1);
  assert.equal(s.projectiles[0].kind, 'star');
  assert.equal(s.projectiles[0].vx, CONST.SPIT_SPEED);
  const later = eventsDuring(s, 60, NONE);
  assert.ok(later.some((e) => e.type === 'defeat' && e.kind === 'walker'));
  assert.equal(s.score - before, CONST.SCORE.walker);
  assert.equal(s.projectiles.length, 0, 'star is used up by the hit');
});

test('after spitting, Enter must be released before Kirby can inhale again', () => {
  const s = playing({ put: [[2, 8, 'P'], [6, 8, 'w']] });
  settle(s);
  run(s, 90, HOLD_ACTION);
  run(s, 1, NONE);
  run(s, 1, ACTION);
  run(s, 20, HOLD_ACTION);
  assert.equal(s.player.inhaling, false, 'still holding from the spit press');
  run(s, 1, NONE);
  run(s, 2, ACTION);
  assert.equal(s.player.inhaling, true);
});

test('inhaling a star block takes one block out of the wall; the spit star breaks the next', () => {
  const s = playing({ fill: [[5, 7, 1, 2, 'S'], [9, 7, 1, 2, 'S']] });
  settle(s);
  const score = s.score;
  run(s, 60, HOLD_ACTION);
  assert.deepEqual(s.player.mouth, { kind: 'block', count: 1 });
  assert.equal(Physics.tileAt(s.world, 5, 8), Physics.TILES.EMPTY, 'block at Kirby height is gone');
  assert.equal(Physics.tileAt(s.world, 5, 7), Physics.TILES.STAR, 'the block above stays');
  assert.equal(s.score - score, CONST.SCORE.block);
  run(s, 1, NONE);
  const seen = eventsDuring(s, 40, (i) => (i === 0 ? ACTION : NONE));
  assert.ok(seen.some((e) => e.type === 'blockBreak'));
  assert.equal(Physics.tileAt(s.world, 9, 8), Physics.TILES.EMPTY);
});

test('getting hit with a full mouth drops the swallowed thing, which can be inhaled again', () => {
  const s = playing();
  settle(s);
  s.player.mouth = { kind: 'walker', count: 1 };
  Player.hurt(s, s.player.x - 10);
  assert.equal(s.player.mouth, null);
  const loose = s.enemies.find((e) => e.type === 'loose');
  assert.ok(loose && loose.inhalable && !loose.harmful);
  s.player.invuln = 0;
  s.player.hurtTimer = 0;
  run(s, 40);
  loose.x = s.player.x + s.player.w + 6;
  loose.y = s.player.y;
  loose.vx = 0;
  run(s, 30, HOLD_ACTION);
  assert.deepEqual(s.player.mouth, { kind: 'walker', count: 1 });
});

test('swallowing two things at once makes a big star that pierces', () => {
  const s = playing({ put: [[2, 8, 'P'], [6, 8, 'w'], [7, 8, 'w']] });
  settle(s);
  const p = s.player;
  const m = Player.mouthPoint(p);
  s.enemies.forEach((e) => { e.x = m.x + 1; e.y = m.y - e.h / 2; });
  p.inhaling = true;
  Player.applyInhale(s);
  assert.deepEqual(p.mouth, { kind: 'walker', count: 2 });
  run(s, 1, NONE);
  run(s, 1, ACTION);
  assert.equal(s.projectiles[0].big, true);
  assert.equal(s.projectiles[0].pierce, true);
});

test('releasing Enter lets go of a half-inhaled enemy, which is stunned briefly', () => {
  const s = playing({ put: [[2, 8, 'P'], [6, 8, 'w']] });
  settle(s);
  run(s, 3, HOLD_ACTION);
  const w = s.enemies[0];
  assert.equal(w.caught, true);
  run(s, 1, NONE);
  assert.equal(w.caught, false);
  assert.ok(w.stun > 0);
});

test('exhaling while flying shoots an air puff that defeats an enemy', () => {
  const s = playing({ put: [[2, 8, 'P'], [6, 8, 'w']] });
  settle(s);
  s.player.flying = true;
  s.enemies[0].x = s.player.x + 20;
  s.enemies[0].y = s.player.y;
  const seen = eventsDuring(s, 10, (i) => (i === 0 ? ACTION : NONE));
  assert.ok(seen.some((e) => e.type === 'exhale'));
  assert.ok(seen.some((e) => e.type === 'defeat'));
  assert.equal(s.player.flying, false);
});

test('Enemies.defeat removes the enemy and awards its score', () => {
  const s = playing({ put: [[2, 8, 'P'], [10, 4, 'f']] });
  const f = s.enemies[0];
  Enemies.defeat(s, f);
  Enemies.removeDead(s);
  assert.equal(s.enemies.length, 0);
  assert.equal(s.score, CONST.SCORE.flyer);
  assert.equal(Game, Game);
});
Bash Run inhale tests
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && sed -i '/assert.equal(Game, Game);/d; s/  CONST, Physics, Player, Enemies, Game, T, playing/  CONST, Physics, Player, Enemies, playing/' tests/inhale.test.js && node --test tests/inhale.test.js 2>&1 | grep -E "^not ok|^# (pass|fail)|expected|actual|message" | head -30

OUT
not ok 13 - swallowing two things at once makes a big star that pierces
# pass 15
# fail 1
Bash Show the big-star test failure details
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && node --test --test-name-pattern="big star" tests/inhale.test.js 2>&1 | grep -B2 -A14 "^not ok" | head -40

OUT
TAP version 13
# Subtest: swallowing two things at once makes a big star that pierces
not ok 1 - swallowing two things at once makes a big star that pierces
  ---
  duration_ms: 5.2307
  type: 'test'
  location: 'C:\\Users\\ethan\\Documents\\GitHub\\Agent Engineering\\Lecture 2a - Codex and Vibecoding\\homework\\4. agent.md + skills\\tests\\inhale.test.js:159:1'
  failureType: 'testCodeFailure'
  error: "Cannot read properties of undefined (reading 'big')"
  code: 'ERR_TEST_FAILURE'
  name: 'TypeError'
  stack: |-
    TestContext.<anonymous> (C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\tests\inhale.test.js:170:33)
    Test.runInAsyncScope (node:async_hooks:214:14)
    Test.run (node:internal/test_runner/test:1047:25)
    Test.start (node:internal/test_runner/test:944:17)
    startSubtestAfterBootstrap (node:internal/test_runner/harness:296:17)
9:42 AM
The spit was blocked by the short post-swallow lock (SWALLOW_LOCK_TICKS), which is intended. I'll make the test wait it out:



Bash Fix big-star test timing and rerun
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && python - <<'EOF'
p='tests/inhale.test.js'; s=open(p,encoding='utf8').read()
s=s.replace("""  assert.deepEqual(p.mouth, { kind: 'walker', count: 2 });
  run(s, 1, NONE);""","""  assert.deepEqual(p.mouth, { kind: 'walker', count: 2 });
  run(s, CONST.SWALLOW_LOCK_TICKS, NONE);""")
open(p,'w',encoding='utf8').write(s)
EOF
node --test tests/inhale.test.js 2>&1 | grep -E "^not ok|^# (pass|fail)"

OUT
not ok 13 - swallowing two things at once makes a big star that pierces
# pass 15
# fail 1
Bash Debug the big-star spit sequence
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && cat > .tmp/big.js <<'EOF'
const h = require('../tests/helpers.js');
const s = h.playing({ put: [[2, 8, 'P'], [6, 8, 'w'], [7, 8, 'w']] });
h.settle(s);
const p = s.player, m = h.Player.mouthPoint(p);
s.enemies.forEach((e) => { e.x = m.x + 1; e.y = m.y - e.h / 2; });
p.inhaling = true; h.Player.applyInhale(s);
console.log(p.mouth, p.swallowLock, p.actionNeedsRelease);
h.run(s, h.CONST.SWALLOW_LOCK_TICKS, h.NONE);
console.log(p.swallowLock, p.mouth, p.hurtTimer, p.invuln, s.mode);
h.Game.update(s, h.ACTION); console.log(s.projectiles.length, p.mouth, s.events.map(e=>e.type));
EOF
node .tmp/big.js

OUT
{ kind: 'walker', count: 2 } 12 true
0 { kind: 'walker', count: 2 } 0 0 playing
0 null [ 'spit', 'starPoof' ]
9:43 AM
The test found a real bug: a big star is 16px tall, so when spat on flat ground it overlapped the floor and burst instantly. I'll keep the star's bottom level with Kirby's feet:



Bash Fix big star clipping floor and rerun tests
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && python - <<'EOF'
p='js/logic/player.js'; s=open(p,encoding='utf8').read()
s=s.replace("""      kind: 'star', big: big, x: p.facing > 0 ? m.x - 2 : m.x - size + 2, y: m.y - size / 2,""","""      // Keep the star's bottom no lower than Kirby's feet so a big star doesn't clip the floor.
      kind: 'star', big: big, x: p.facing > 0 ? m.x - 2 : m.x - size + 2, y: Math.min(m.y - size / 2, p.y + p.h - size),""")
open(p,'w',encoding='utf8').write(s)
EOF
node --test tests/ 2>&1 | grep -E "^not ok|^# (pass|fail)"

OUT
not ok 1 - tests
# pass 0
# fail 1
9:43 AM
(Passing the folder to node --test doesn't work; the documented command is plain node --test.)



Bash Run all unit tests with node --test
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && node --test 2>&1 | grep -E "^not ok|^# (pass|fail|tests)"

OUT
# tests 34
# pass 34
# fail 0
9:43 AM
All 34 pass. Next, game-state tests (lives, score, checkpoints, boss, win, game over, restart and pause):



Write C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\tests\game.test.js
226 lines
// Lives, health, score, checkpoints, boss, win, game over, continue, restart and pause.
const test = require('node:test');
const assert = require('node:assert/strict');
const {
  CONST, Player, Boss, Game, T, level, keys, playing, run, settle, NONE, JUMP, eventsDuring
} = require('./helpers.js');

const RESTART = keys({ restart: true, restartPressed: true });
const PAUSE = keys({ pause: true, pausePressed: true });

function die(s) {
  Player.kill(s);
  run(s, CONST.DEATH_TICKS);
}

test('the game starts on the title screen and Space starts a run', () => {
  const s = Game.create(level({}));
  assert.equal(s.mode, 'title');
  run(s, 1, JUMP);
  assert.equal(s.mode, 'title', 'title ignores input for a moment so a held key does not skip it');
  run(s, CONST.SCREEN_INPUT_DELAY);
  run(s, 1, JUMP);
  assert.equal(s.mode, 'playing');
  assert.equal(s.lives, CONST.START_LIVES);
  assert.equal(s.player.health, CONST.MAX_HEALTH);
  assert.equal(s.score, 0);
});

test('touching an enemy costs one health pip, knocks Kirby back, and gives brief invulnerability', () => {
  const s = playing({ put: [[2, 8, 'P'], [3, 8, 'w']] });
  const seen = eventsDuring(s, 5);
  assert.equal(seen.filter((e) => e.type === 'hurt').length, 1);
  assert.equal(s.player.health, CONST.MAX_HEALTH - 1);
  assert.ok(s.player.invuln > 0);
  run(s, 30);
  assert.equal(s.player.health, CONST.MAX_HEALTH - 1, 'no second hit while invulnerable');
});

test('spikes hurt', () => {
  const s = playing({ put: [[2, 8, 'P'], [2, 9, '^']] });
  run(s, 5);
  assert.equal(s.player.health, CONST.MAX_HEALTH - 1);
});

test('running out of health costs a life and respawns at the last checkpoint with full health', () => {
  const s = playing({ put: [[2, 8, 'P'], [10, 8, 'C']] });
  run(s, 120, keys({ right: true }));
  assert.equal(s.checkpoint, 0, 'passed the checkpoint');
  for (let i = 0; i < CONST.MAX_HEALTH; i++) { s.player.invuln = 0; Player.hurt(s, s.player.x + 20); }
  assert.equal(s.mode, 'dying');
  run(s, CONST.DEATH_TICKS);
  assert.equal(s.mode, 'playing');
  assert.equal(s.lives, CONST.START_LIVES - 1);
  assert.equal(s.player.health, CONST.MAX_HEALTH);
  const cp = s.world.checkpoints[0];
  assert.ok(Math.abs(s.player.x + s.player.w / 2 - (cp.x + cp.w / 2)) < 1);
});

test('falling into a pit costs a whole life even at full health', () => {
  const s = playing({ gaps: [[4, 8]] });
  const seen = eventsDuring(s, 300, keys({ right: true }));
  assert.ok(seen.some((e) => e.type === 'death'));
  assert.equal(s.lives, CONST.START_LIVES - 1);
});

test('losing the last life shows game over; Space continues from the checkpoint with score reset', () => {
  const s = playing({ put: [[2, 8, 'P'], [10, 8, 'C'], [12, 6, 'o']] });
  run(s, 200, keys({ right: true }));
  assert.ok(s.score > 0);
  for (let i = 0; i < CONST.START_LIVES; i++) die(s);
  assert.equal(s.mode, 'gameover');
  assert.equal(s.lives, 0);
  assert.ok(s.best >= s.score && s.best > 0, 'best score is kept');
  run(s, 1, JUMP);
  assert.equal(s.mode, 'gameover', 'waits briefly before accepting input');
  run(s, CONST.SCREEN_INPUT_DELAY);
  run(s, 1, JUMP);
  assert.equal(s.mode, 'playing');
  assert.equal(s.lives, CONST.START_LIVES);
  assert.equal(s.score, 0);
  assert.equal(s.checkpoint, 0);
  assert.equal(s.continues, 1);
});

test('R on the game-over screen restarts from the very beginning', () => {
  const s = playing({ put: [[2, 8, 'P'], [10, 8, 'C']] });
  run(s, 200, keys({ right: true }));
  for (let i = 0; i < CONST.START_LIVES; i++) die(s);
  run(s, CONST.SCREEN_INPUT_DELAY);
  run(s, 1, RESTART);
  assert.equal(s.mode, 'playing');
  assert.equal(s.checkpoint, -1);
  assert.equal(s.player.x, s.world.start.x);
  assert.equal(s.time, 0);
});

test('R while playing asks for confirmation: R again restarts, P cancels', () => {
  const s = playing({ put: [[2, 8, 'P'], [12, 6, 'o']] });
  run(s, 100, keys({ right: true }));
  run(s, 1, RESTART);
  assert.equal(s.mode, 'confirm');
  run(s, 1, PAUSE);
  assert.equal(s.mode, 'playing');
  assert.ok(s.score > 0, 'cancel keeps progress');
  run(s, 1, RESTART);
  run(s, 1, RESTART);
  assert.equal(s.mode, 'playing');
  assert.equal(s.score, 0);
  assert.equal(s.player.x, s.world.start.x);
});

test('P pauses: nothing moves and the clock stops until P again', () => {
  const s = playing({ put: [[2, 8, 'P'], [12, 8, 'w']] });
  run(s, 10);
  run(s, 1, PAUSE);
  const snap = JSON.stringify({ t: s.time, p: s.player, e: s.enemies });
  run(s, 100, keys({ right: true }));
  assert.equal(JSON.stringify({ t: s.time, p: s.player, e: s.enemies }), snap);
  run(s, 1, PAUSE);
  assert.equal(s.mode, 'playing');
});

test('point stars, food and extra lives', () => {
  const s = playing({ put: [[2, 8, 'P'], [5, 8, 'o'], [8, 8, 'T'], [11, 8, '1']] });
  s.player.health = 2;
  run(s, 200, keys({ right: true }));
  assert.equal(s.score, CONST.SCORE.star + CONST.SCORE.food);
  assert.equal(s.player.health, CONST.MAX_HEALTH);
  assert.equal(s.lives, CONST.START_LIVES + 1);
  run(s, 200, keys({ left: true }));
  assert.equal(s.score, CONST.SCORE.star + CONST.SCORE.food, 'items are collected only once');
});

test('reaching the extra-life score awards one life, once', () => {
  const s = playing({ put: [[2, 8, 'P'], [5, 8, 'o']] });
  s.score = CONST.EXTRA_LIFE_SCORE - CONST.SCORE.star;
  run(s, 100, keys({ right: true }));
  assert.equal(s.lives, CONST.START_LIVES + 1);
  s.score += CONST.EXTRA_LIFE_SCORE;
  run(s, 10);
  assert.equal(s.lives, CONST.START_LIVES + 1);
});

function arena() {
  return playing({
    width: 30,
    put: [[2, 8, 'P'], [6, 8, 'A'], [24, 8, 'B'], [14, 5, 'W']],
    ceiling: [[6, 30, 1]]
  });
}

test('the arena gate closes behind Kirby and wakes the boss', () => {
  const s = arena();
  assert.equal(s.boss.state, 'dormant');
  run(s, 200, keys({ right: true }));
  assert.equal(s.arenaLocked, true);
  assert.notEqual(s.boss.state, 'dormant');
  assert.ok(s.world.tiles[5 * s.world.w + 6] !== 0, 'gate column is solid');
});

test('only a spat star hurts the boss; air puffs and touching it do not', () => {
  const s = arena();
  run(s, 200, keys({ right: true }));
  const b = s.boss;
  run(s, CONST.BOSS_INTRO_TICKS);
  s.projectiles.push({ kind: 'air', x: b.x - 4, y: b.y + 20, w: 10, h: 10, vx: 1, life: 10, power: 1 });
  run(s, 3);
  assert.equal(b.hp, CONST.BOSS_HP);
  s.projectiles.push({ kind: 'star', x: b.x - 4, y: b.y + 20, w: 12, h: 12, vx: 1, life: 10, power: 1 });
  run(s, 3);
  assert.equal(b.hp, CONST.BOSS_HP - 1);
  assert.ok(b.invuln > 0);
});

test('the boss drops inhalable apples and blows puffs that cannot be inhaled', () => {
  const s = arena();
  run(s, 200, keys({ right: true }));
  run(s, CONST.BOSS_INTRO_TICKS + CONST.BOSS_APPLE_WAIT + CONST.BOSS_PUFF_GAP + 5);
  const apples = s.enemies.filter((e) => e.type === 'apple');
  const puffs = s.enemies.filter((e) => e.type === 'bosspuff');
  assert.ok(apples.length >= 1, 'apples dropped');
  assert.ok(puffs.length >= 1, 'puffs blown');
  assert.equal(apples[0].inhalable, true);
  assert.equal(puffs[0].inhalable, false);
});

test('beating the boss reveals the warp star; touching it wins with a time bonus', () => {
  const s = arena();
  run(s, 200, keys({ right: true }));
  run(s, CONST.BOSS_INTRO_TICKS);
  assert.equal(s.warp.active, false);
  for (let i = 0; i < CONST.BOSS_HP; i++) { s.boss.invuln = 0; Boss.hit(s, 1); }
  assert.equal(s.boss.state, 'dying');
  const before = s.score;
  run(s, CONST.BOSS_DEATH_TICKS + 1);
  assert.equal(s.boss.state, 'dead');
  assert.equal(s.warp.active, true);
  assert.equal(s.score - before, CONST.SCORE.boss);
  s.player.x = s.warp.x; // unit test of the win rule only; the playthrough test reaches it with keys
  s.player.y = s.warp.y;
  const seen = eventsDuring(s, 1);
  assert.ok(seen.some((e) => e.type === 'win'));
  assert.equal(s.mode, 'win');
  const seconds = Math.floor(s.time / CONST.TICKS_PER_SECOND);
  assert.equal(s.winBonus, Math.max(0, CONST.TIME_BONUS_MAX - seconds * CONST.TIME_BONUS_PER_SECOND));
  assert.equal(s.best, s.score);
  run(s, CONST.SCREEN_INPUT_DELAY);
  run(s, 1, JUMP);
  assert.equal(s.mode, 'playing', 'Space on the win screen plays again');
  assert.equal(s.score, 0);
});

test('dying in the arena reopens the gate and resets the boss', () => {
  const s = arena();
  run(s, 200, keys({ right: true }));
  run(s, CONST.BOSS_INTRO_TICKS);
  s.boss.invuln = 0;
  Boss.hit(s, 1);
  die(s);
  assert.equal(s.arenaLocked, false);
  assert.equal(s.boss.state, 'dormant');
  assert.equal(s.boss.hp, CONST.BOSS_HP);
  assert.equal(s.world.tiles[5 * s.world.w + 6], 0, 'gate is open again');
  settle(s);
});
Bash Run game state tests
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && node --test tests/game.test.js 2>&1 | grep -E "^not ok|^# (pass|fail)|error:|expected|actual" | head -30

OUT
not ok 2 - touching an enemy costs one health pip, knocks Kirby back, and gives brief invulnerability
  error: |-
  expected: 1
  actual: 0
not ok 6 - losing the last life shows game over; Space continues from the checkpoint with score reset
  error: |-
  expected: true
  actual: false
not ok 8 - R while playing asks for confirmation: R again restarts, P cancels
  error: 'cancel keeps progress'
  expected: true
  actual: false
# pass 13
# fail 3
9:44 AM
These three are test-setup mistakes: the walker needed more time to reach Kirby, and the point stars were placed above Kirby's head. Fixing the setups:



Bash Fix game test setups and rerun
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && python - <<'EOF'
p='tests/game.test.js'; s=open(p,encoding='utf8').read()
s=s.replace("[12, 6, 'o']","[12, 8, 'o']")
s=s.replace("""  const s = playing({ put: [[2, 8, 'P'], [3, 8, 'w']] });
  const seen = eventsDuring(s, 5);
  assert.equal(seen.filter((e) => e.type === 'hurt').length, 1);
  assert.equal(s.player.health, CONST.MAX_HEALTH - 1);
  assert.ok(s.player.invuln > 0);
  run(s, 30);""","""  const s = playing({ put: [[2, 8, 'P'], [3, 8, 'w']] });
  const seen = eventsDuring(s, 30);
  assert.equal(seen.filter((e) => e.type === 'hurt').length, 1);
  assert.equal(s.player.health, CONST.MAX_HEALTH - 1);
  assert.ok(s.player.invuln > 0);
  assert.ok(s.player.vx < 0 || s.player.x < s.world.start.x, 'knocked back away from the walker');
  run(s, 30);""")
open(p,'w',encoding='utf8').write(s)
EOF
node --test tests/game.test.js 2>&1 | grep -E "^not ok|^# (pass|fail)|error:|expected|actual" | head -30

OUT
# pass 16
# fail 0
9:44 AM
Next: input tests, a structure test (enforces the CLAUDE.md rules on file size, pure logic and classic scripts), and the playthrough test:



Write C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\tests\input.test.js
63 lines
const test = require('node:test');
const assert = require('node:assert/strict');
const { KirbyInput } = require('../js/input.js');

test('only the requested keys are bound to movement, jump/fly and inhale/spit', () => {
  const byAction = {};
  for (const [code, action] of Object.entries(KirbyInput.BINDINGS)) (byAction[action] = byAction[action] || []).push(code);
  assert.deepEqual(byAction.left.sort(), ['ArrowLeft', 'KeyA']);
  assert.deepEqual(byAction.right.sort(), ['ArrowRight', 'KeyD']);
  assert.deepEqual(byAction.jump, ['Space']);
  assert.deepEqual(byAction.action, ['Enter']);
  for (const code of ['ArrowUp', 'ArrowDown', 'KeyW', 'KeyS', 'KeyX', 'KeyZ', 'KeyJ', 'NumpadEnter', 'ShiftLeft']) {
    assert.equal(KirbyInput.BINDINGS[code], undefined, code + ' must not be bound');
  }
});

test('a tap shorter than one tick still counts as a press and as held for that tick', () => {
  const input = KirbyInput.create();
  input.keyDown('Space');
  input.keyUp('Space');
  const snap = input.poll();
  assert.equal(snap.jumpPressed, true);
  assert.equal(snap.jump, true);
  const next = input.poll();
  assert.equal(next.jumpPressed, false);
  assert.equal(next.jump, false);
});

test('holding a key reports one press, then held', () => {
  const input = KirbyInput.create();
  input.keyDown('Enter');
  assert.equal(input.poll().actionPressed, true);
  input.keyDown('Enter'); // auto-repeat
  const snap = input.poll();
  assert.equal(snap.actionPressed, false);
  assert.equal(snap.action, true);
});

test('either binding of a direction works, and releasing one keeps the other held', () => {
  const input = KirbyInput.create();
  input.keyDown('KeyA');
  input.keyDown('ArrowLeft');
  input.keyUp('KeyA');
  assert.equal(input.poll().left, true);
  input.keyUp('ArrowLeft');
  assert.equal(input.poll().left, false);
});

test('unbound keys are ignored', () => {
  const input = KirbyInput.create();
  assert.equal(input.keyDown('KeyQ'), false);
  const snap = input.poll();
  assert.ok(Object.values(snap).every((v) => v === false));
});

test('releaseAll (window blur) lets go of every key', () => {
  const input = KirbyInput.create();
  input.keyDown('ArrowRight');
  input.poll();
  input.releaseAll();
  assert.equal(input.poll().right, false);
});
Write C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\tests\structure.test.js
60 lines
// Project rules from CLAUDE.md that can be checked mechanically, plus a sanity check of the level.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { World } = require('../js/logic/world.js');
const { LEVEL_1 } = require('../js/level.js');

const root = path.join(__dirname, '..');
const jsFiles = (dir) => fs.readdirSync(path.join(root, dir)).filter((f) => f.endsWith('.js')).map((f) => path.join(dir, f));
const sources = [...jsFiles('js'), ...jsFiles('js/logic')];

test('every source file stays under 400 lines', () => {
  for (const f of sources) {
    const lines = fs.readFileSync(path.join(root, f), 'utf8').split('\n').length;
    assert.ok(lines < 400, `${f} has ${lines} lines`);
  }
});

test('logic files never touch the DOM or canvas and export for Node', () => {
  for (const f of jsFiles('js/logic')) {
    const src = fs.readFileSync(path.join(root, f), 'utf8');
    assert.doesNotMatch(src, /\b(document|window|canvas|getContext|requestAnimationFrame|localStorage)\b/, f);
    assert.match(src.trim().split('\n').pop(), /^if \(typeof module !== 'undefined'\) module\.exports = \{.*\};$/, f);
  }
});

test('index.html loads every script as a classic local script (works over file://)', () => {
  const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  assert.doesNotMatch(html, /type=["']module["']/);
  assert.doesNotMatch(html, /(src|href)=["']https?:/, 'no external assets');
  const scripts = [...html.matchAll(/<script src="([^"]+)"/g)].map((m) => m[1]);
  assert.ok(scripts.length >= 10);
  for (const s of scripts) assert.ok(fs.existsSync(path.join(root, s)), s + ' is missing');
  for (const f of sources) assert.ok(scripts.includes(f.replace(/\\/g, '/')), f + ' is not loaded by index.html');
});

test('no image or audio files: all art and sound is made in code', () => {
  const walk = (dir) => fs.readdirSync(dir, { withFileTypes: true }).flatMap((d) =>
    d.name.startsWith('.') ? [] : d.isDirectory() ? walk(path.join(dir, d.name)) : [d.name]);
  const assets = walk(root).filter((n) => /\.(png|jpe?g|gif|bmp|webp|mp3|wav|ogg)$/i.test(n));
  assert.deepEqual(assets, []);
});

test('the level has every required ingredient', () => {
  const w = World.build(LEVEL_1);
  const types = new Set(w.spawns.map((s) => s.type));
  for (const t of ['walker', 'flyer', 'hopper', 'spiky']) assert.ok(types.has(t), 'missing ' + t);
  assert.ok(w.bossSpawn, 'boss');
  assert.ok(w.warp, 'warp star goal');
  assert.ok(w.gateCol > 0, 'arena gate');
  assert.ok(w.gaps.length >= 8, 'plenty of gaps');
  assert.ok(w.checkpoints.length >= 6, 'a checkpoint roughly every stretch');
  assert.ok(w.sections.length >= 7, 'six stretches plus the arena');
  assert.ok(w.items.some((i) => i.kind === 'food') && w.items.some((i) => i.kind === 'oneup'));
  assert.ok(w.winds.length >= 1, 'windy section');
  assert.ok(w.tiles.includes(4), 'star blocks');
  assert.ok(w.tiles.includes(5), 'spikes');
});
Write C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\tests\playthrough.test.js
62 lines
// Automated playthrough: the bot plays the real level using simulated key events only
// (keyDown/keyUp on the same input tracker the browser uses). No teleporting and no
// writes to game state: the test only reads state to check what happened.
const test = require('node:test');
const assert = require('node:assert/strict');
const { CONST } = require('../js/logic/constants.js');
const { Game } = require('../js/logic/game.js');
const { LEVEL_1 } = require('../js/level.js');
const { KirbyInput } = require('../js/input.js');
const { KirbyBot } = require('./bot.js');

const MAX_TICKS = 60 * 60 * 20; // 20 minutes of game time
const MAX_STEP_PX = 8;          // nothing moves further than this in one tick except a respawn

function play() {
  const state = Game.create(LEVEL_1);
  const input = KirbyInput.create();
  const bot = KirbyBot.create();
  const log = { events: {}, landedAfterGap: new Set(), maxStep: 0, ticks: 0 };
  const gaps = state.world.gaps;
  let prev = null;
  for (let t = 0; t < MAX_TICKS && state.mode !== 'win'; t++) {
    bot.apply(state, input);
    Game.update(state, input.poll());
    log.ticks = t;
    const respawned = state.events.some((e) => e.type === 'respawn' || e.type === 'start');
    state.events.forEach((e) => { log.events[e.type] = (log.events[e.type] || 0) + 1; });
    const p = state.player;
    if (prev && !respawned && state.mode === 'playing') {
      log.maxStep = Math.max(log.maxStep, Math.abs(p.x - prev.x), Math.abs(p.y - prev.y));
    }
    prev = { x: p.x, y: p.y };
    if (p.onGround) gaps.forEach((g, i) => { if (p.x >= g.x1) log.landedAfterGap.add(i); });
  }
  return { state, log, bot };
}

test('the bot finishes the level with key presses only', () => {
  const { state, log, bot } = play();
  const p = state.player;
  const summary = `mode=${state.mode} x=${(p.x / CONST.TILE).toFixed(1)} ticks=${log.ticks} deaths=${state.deaths} continues=${state.continues}`;
  assert.equal(state.mode, 'win', 'did not win: ' + summary);
  assert.ok(bot.mem.keyEvents > 100, 'driven by key events');

  // Every gap in the level was crossed: Kirby later stood on solid ground past its far edge.
  state.world.gaps.forEach((g, i) => {
    assert.ok(log.landedAfterGap.has(i), `gap ${i} (cols ${g.x0 / CONST.TILE}-${g.x1 / CONST.TILE}) was never crossed`);
  });

  // No teleporting: movement per tick stays small.
  assert.ok(log.maxStep <= MAX_STEP_PX, 'player jumped ' + log.maxStep + 'px in one tick');

  // The core mechanics were all exercised along the way.
  for (const ev of ['swallow', 'spit', 'flap', 'blockBreak', 'defeat', 'checkpoint', 'arenaLock', 'bossHit', 'bossDefeated', 'win']) {
    assert.ok(log.events[ev] > 0, 'never saw ' + ev);
  }
  assert.equal(state.boss.state, 'dead');
  assert.ok(log.events.bossHit >= CONST.BOSS_HP / 2, 'boss took hits from spat stars');
  assert.ok(state.score > 0);
  console.log('playthrough: ' + summary + ` time=${(state.time / 60).toFixed(0)}s score=${state.score}`);
});
Bash Run the full unit test suite
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && node --test 2>&1 | grep -E "^not ok|^# (pass|fail|tests)|error:|expected|actual|playthrough:" | head -30

OUT
# Subtest: a held jump reaches the expected height, under three tiles
ok 39 - a held jump reaches the expected height, under three tiles
# playthrough: mode=win x=392.2 ticks=7770 deaths=1 continues=0 time=127s score=24730
not ok 59 - logic files never touch the DOM or canvas and export for Node
  error: 'js\\logic\\physics.js'
  expected:
  actual: |-
# tests 62
# pass 61
# fail 1
9:44 AM
The only failure is my structure check catching the word "canvas" in a comment ("no DOM, no canvas"). I'll strip comments before checking:



Bash Ignore comments in DOM check and rerun all tests
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && python - <<'EOF'
p='tests/structure.test.js'; s=open(p,encoding='utf8').read()
s=s.replace("""    const src = fs.readFileSync(path.join(root, f), 'utf8');
    assert.doesNotMatch(src, /""","""    const src = fs.readFileSync(path.join(root, f), 'utf8');
    const code = src.replace(/\\/\\/.*$/gm, '');
    assert.doesNotMatch(code, /""")
open(p,'w',encoding='utf8').write(s)
EOF
grep -n "const code" tests/structure.test.js; node --test 2>&1 | grep -E "^not ok|^# (pass|fail|tests)|playthrough:"

OUT
<stdin>:4: SyntaxWarning: invalid escape sequence '\/'
23:    const code = src.replace(/\/\/.*$/gm, '');
# playthrough: mode=win x=392.2 ticks=7770 deaths=1 continues=0 time=127s score=24730
# tests 62
# pass 62
# fail 0
9:45 AM
All 62 tests pass, including the full playthrough, which wins with key events only. Now a polish pass. First a sprite-sheet check of every frame, scaled up:



Bash Render a sprite sheet for visual review
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && cat > .tmp/sheet.html <<'EOF'
<!DOCTYPE html><html><body style="margin:0;background:#86ccff"><canvas id="c" width="760" height="560" style="image-rendering:pixelated"></canvas>
<script src="../js/sprites.js"></script><script src="../js/sprites-world.js"></script>
<script>
Sprites.init();
var ctx = document.getElementById('c').getContext('2d'); ctx.imageSmoothingEnabled = false;
var names = ['kirby_idle0','kirby_idle1','kirby_blink','kirby_run0','kirby_run1','kirby_run2','kirby_run3','kirby_jump','kirby_fall','kirby_fly0','kirby_fly1','kirby_inhale0','kirby_inhale1','kirby_full0','kirby_full1','kirby_full2','kirby_spit','kirby_hurt',
 'walker0','walker1','flyer0','flyer1','hopper0','hopper1','spiky0','spiky1','apple','bosspuff','airpuff','spit12_0','spit16_1','pointstar0','food','oneup','sign','checkpoint_off','checkpoint_on0','warp0','tile_grass','tile_dirt','tile_stone','tile_platform','tile_star','tile_spikes'];
var x = 4, y = 4, S = 3;
names.forEach(function (n) { var s = Sprites.get(n); if (x + s.w * S > 760) { x = 4; y += 26 * S; } ctx.drawImage(s.r, x, y, s.w * S, s.h * S); x += s.w * S + 8; });
['boss_idle','boss_blow','boss_hurt','boss_dead'].forEach(function (n, i) { var s = Sprites.get(n); ctx.drawImage(s.r, 4 + i * 170, 330, s.w * 1.8, s.h * 1.8); });
</script></body></html>
EOF
cat > .tmp/sheet.mjs <<'EOF'
import { launch, close, sleep } from '../tests/cdp.mjs';
import { pathToFileURL } from 'node:url';
import path from 'node:path';
const b = await launch(path.resolve('.tmp/profile-sheet'));
try { const c = b.client; await c.send('Page.enable'); await c.send('Emulation.setDeviceMetricsOverride', { width: 760, height: 560, deviceScaleFactor: 1, mobile: false });
  await c.send('Page.navigate', { url: pathToFileURL(path.resolve('.tmp/sheet.html')).href }); await sleep(800); await c.screenshot('.tmp/sheet.png'); } finally { await close(b); }
EOF
node .tmp/sheet.mjs && echo done

OUT
done
Read C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\.tmp\sheet.png
Sprites look good, but the boss trunk's right edge has an odd pink shade—I'll switch it to dark brown. I'll also improve inhaling by shrinking objects as they near Kirby's mouth and adding denser wind lines, and move the warp-star sparkle spawning into the fixed tick so it's frame-rate independent.
Bash Polish inhale visuals, boss trunk colour, warp sparkle timing
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && python - <<'EOF'
p='js/sprites-world.js'; s=open(p,encoding='utf8').read()
s=s.replace("      P.rect(57, 52, 2, 68, 'd');","      P.rect(55, 52, 4, 68, 'B');")
open(p,'w',encoding='utf8').write(s)
p='js/render.js'; s=open(p,encoding='utf8').read()
s=s.replace("""      if (f % 6 === 0) spawn(wp.x + 12, wp.y + 12, 1, { speed: 0.6, sprite: 'pointstar0', life: 30 });
""","")
s=s.replace("""    if (banner && --banner.timer <= 0) banner = null;""","""    if (banner && --banner.timer <= 0) banner = null;
    var wp = state.warp;
    if (wp && wp.active && state.frame % FX.SPARKLE_EVERY === 0) spawn(wp.x + wp.w / 2, wp.y + wp.h / 2, 1, { speed: 0.6, sprite: 'pointstar0', life: 30 });""")
s=s.replace("""    SHAKE_DECAY: 0.85, FLOATER_TICKS: 50, NOFLY_COOLDOWN: 60, WIND_STREAKS: 14""","""    SHAKE_DECAY: 0.85, FLOATER_TICKS: 50, NOFLY_COOLDOWN: 60, WIND_STREAKS: 14, SPARKLE_EVERY: 6,
    INHALE_LINES: 11, SWALLOW_SHRINK_DIST: 28, SWALLOW_MIN_SCALE: 0.35""")
# caught enemies shrink toward the mouth
s=s.replace("""      ctx.drawImage(e.facing < 0 ? s.l : s.r, Math.round(cx - s.w / 2), Math.round(by - s.h));
    });""","""      var img = e.facing < 0 ? s.l : s.r;
      if (e.caught) {
        // Being swallowed: shrink as it nears Kirby's mouth.
        var m = Player.mouthPoint(state.player);
        var d = Math.hypot(e.x + e.w / 2 - m.x, e.y + e.h / 2 - m.y);
        var k = Math.max(FX.SWALLOW_MIN_SCALE, Math.min(1, d / FX.SWALLOW_SHRINK_DIST));
        var w = Math.round(s.w * k), h = Math.round(s.h * k);
        ctx.drawImage(img, Math.round(e.x + e.w / 2 - v.x - w / 2), Math.round(e.y + e.h / 2 - v.y - h / 2), w, h);
        return;
      }
      ctx.drawImage(img, Math.round(cx - s.w / 2), Math.round(by - s.h));
    });""")
s=s.replace("""    for (var k = 0; k < 7; k++) {
      var d = C.INHALE_RANGE - ((f * 3 + k * 23) % C.INHALE_RANGE);""","""    for (var k = 0; k < FX.INHALE_LINES; k++) {
      var d = C.INHALE_RANGE - ((f * 4 + k * 23) % C.INHALE_RANGE);""")
s=s.replace("""      ctx.fillRect(Math.round(x - (p.facing > 0 ? 0 : 4)), Math.round(y), 5, 1);""","""      var len = 3 + Math.round(5 * d / C.INHALE_RANGE);
      ctx.fillRect(Math.round(x - (p.facing > 0 ? 0 : len - 1)), Math.round(y), len, 1);""")
open(p,'w',encoding='utf8').write(s)
EOF
grep -n "SPARKLE_EVERY\|INHALE_LINES\|SWALLOW_SHRINK" js/render.js | head; wc -l js/*.js js/logic/*.js tests/*.js tests/*.mjs

OUT
10:    SHAKE_DECAY: 0.85, FLOATER_TICKS: 50, NOFLY_COOLDOWN: 60, WIND_STREAKS: 14, SPARKLE_EVERY: 6,
11:    INHALE_LINES: 11, SWALLOW_SHRINK_DIST: 28, SWALLOW_MIN_SCALE: 0.35
117:    if (wp && wp.active && state.frame % FX.SPARKLE_EVERY === 0) spawn(wp.x + wp.w / 2, wp.y + wp.h / 2, 1, { speed: 0.6, sprite: 'pointstar0', life: 30 });
257:        var k = Math.max(FX.SWALLOW_MIN_SCALE, Math.min(1, d / FX.SWALLOW_SHRINK_DIST));
286:    for (var k = 0; k < FX.INHALE_LINES; k++) {
   218 js/audio.js
   219 js/hud.js
    72 js/input.js
    92 js/level.js
    86 js/main.js
   352 js/render.js
   317 js/sprites-world.js
   215 js/sprites.js
   119 js/logic/boss.js
   148 js/logic/constants.js
   203 js/logic/enemies.js
   269 js/logic/game.js
   137 js/logic/physics.js
   283 js/logic/player.js
   155 js/logic/world.js
   185 tests/bot.js
   226 tests/game.test.js
    62 tests/helpers.js
   204 tests/inhale.test.js
    62 tests/input.test.js
   110 tests/movement.test.js
    80 tests/physics.test.js
    61 tests/playthrough.test.js
    60 tests/structure.test.js
   123 tests/cdp.mjs
   151 tests/smoke.mjs
  4209 total
I noticed the arena gate isn't opening after the boss is beaten, as DESIGN.md specifies—I'll fix that and ensure it stays open.
Bash Reopen arena gate after boss defeat and rerun tests
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && python - <<'EOF'
p='js/logic/boss.js'; s=open(p,encoding='utf8').read()
s=s.replace("""  var W = typeof World !== 'undefined' ? World : require('./world.js').World;""","""  var P = typeof Physics !== 'undefined' ? Physics : require('./physics.js').Physics;
  var W = typeof World !== 'undefined' ? World : require('./world.js').World;""")
s=s.replace("""        b.state = 'dead';
        state.warp.active = true;""","""        b.state = 'dead';
        state.warp.active = true;
        openGate(state);""")
s=s.replace("""  // A spat star hit the boss.""","""  // Restores the gate column to how the level drew it, so the arena opens up again.
  function openGate(state) {
    var w = state.world;
    for (var r = 0; r < w.groundRow; r++) P.setTile(w, w.gateCol, r, w.original[r * w.w + w.gateCol]);
    state.arenaLocked = false;
  }

  // A spat star hit the boss.""")
open(p,'w',encoding='utf8').write(s)
p='js/logic/game.js'; s=open(p,encoding='utf8').read()
s=s.replace("""    if (!state.arenaLocked && world.gateCol >= 0 && p.x > world.gateCol * T + C.ARENA_LOCK_OFFSET) lockArena(state);""","""    var bossWaiting = state.boss && state.boss.state === 'dormant';
    if (!state.arenaLocked && bossWaiting && p.x > world.gateCol * T + C.ARENA_LOCK_OFFSET) lockArena(state);""")
open(p,'w',encoding='utf8').write(s)
p='tests/game.test.js'; s=open(p,encoding='utf8').read()
s=s.replace("""  assert.equal(s.score - before, CONST.SCORE.boss);
""","""  assert.equal(s.score - before, CONST.SCORE.boss);
  assert.equal(s.world.tiles[5 * s.world.w + 6], 0, 'the arena gate opens again');
  run(s, 5);
  assert.equal(s.world.tiles[5 * s.world.w + 6], 0, 'and stays open');
""")
open(p,'w',encoding='utf8').write(s)
EOF
node --test 2>&1 | grep -E "^not ok|^# (pass|fail|tests)|playthrough:"

OUT
# playthrough: mode=win x=392.2 ticks=7770 deaths=1 continues=0 time=127s score=24730
# tests 62
# pass 62
# fail 0
All 62 tests pass and the deterministic seeded playthrough is stable. Now I'll check that the bot also wins across different random seeds to confirm robustness.
Bash Run the bot across several random seeds
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && cat > .tmp/seeds.js <<'EOF'
const { Game } = require('../js/logic/game.js'); const { LEVEL_1 } = require('../js/level.js');
const { KirbyInput } = require('../js/input.js'); const { KirbyBot } = require('../tests/bot.js');
for (const seed of [1, 2, 3, 42, 777, 9001]) {
  const s = Game.create(LEVEL_1, { seed }); const input = KirbyInput.create(); const bot = KirbyBot.create();
  let t = 0; for (; t < 72000 && s.mode !== 'win'; t++) { bot.apply(s, input); Game.update(s, input.poll()); }
  console.log('seed', seed, s.mode, 'time', (s.time / 60).toFixed(0) + 's', 'deaths', s.deaths, 'continues', s.continues);
}
EOF
node .tmp/seeds.js

OUT
seed 1 win time 130s deaths 1 continues 0
seed 2 win time 167s deaths 2 continues 0
seed 3 win time 132s deaths 1 continues 0
seed 42 playing time 1116s deaths 37 continues 12
seed 777 win time 122s deaths 1 continues 0
seed 9001 win time 126s deaths 1 continues 0
Bash Inspect the failing seed in the boss fight
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && cat > .tmp/seed42.js <<'EOF'
const { Game } = require('../js/logic/game.js'); const { LEVEL_1 } = require('../js/level.js');
const { KirbyInput } = require('../js/input.js'); const { KirbyBot } = require('../tests/bot.js');
const s = Game.create(LEVEL_1, { seed: 42 }); const input = KirbyInput.create(); const bot = KirbyBot.create();
let n = 0;
for (let t = 0; t < 20000 && n < 14; t++) { bot.apply(s, input); Game.update(s, input.poll());
  for (const e of s.events) if (['hurt','death','arenaLock','bossHit'].includes(e.type)) { n++; const p = s.player;
    console.log(t, e.type, 'P', p.x.toFixed(0), p.y.toFixed(0), 'mouth', !!p.mouth, 'boss', s.boss.state, s.boss.hp, s.enemies.filter(q => Math.abs(q.x - p.x) < 30).map(q => q.type + '@' + q.x.toFixed(0) + ',' + q.y.toFixed(0) + (q.rolling ? 'R' : '')).join(' ')); } }
EOF
node .tmp/seed42.js

OUT
1866 hurt P 2321 265 mouth false boss dormant 6 walker@2323,276
2107 hurt P 2551 259 mouth false boss dormant 6 hopper@2550,268
2473 hurt P 3014 250 mouth false boss dormant 6 spiky@3025,241
3169 hurt P 3553 86 mouth false boss dormant 6 flyer@3552,77
3541 hurt P 4010 63 mouth false boss dormant 6 flyer@4017,73
5400 hurt P 5791 221 mouth false boss dormant 6 spiky@5793,207
5400 death P 5791 221 mouth false boss dormant 6 spiky@5793,207
6381 arenaLock P 6184 257 mouth false boss intro 6 
6531 hurt P 6242 276 mouth false boss apples 6 apple@6228,196R apple@6242,264R
6590 bossHit P 6204 276 mouth false boss apples 5 
6826 hurt P 6240 276 mouth false boss apples 5 apple@6253,196R apple@6242,264R
6935 bossHit P 6228 276 mouth false boss blow 4 
7096 hurt P 6232 276 mouth false boss apples 4 apple@6242,264R
7382 hurt P 6232 276 mouth false boss apples 4 apple@6206,276R apple@6242,264R
All 62 tests pass, and the bot wins 5 of 6 random seeds—the failure is a bot weakness where its dodge logic ignores apples that roll off platforms rather than only freshly dropped ones. I'll fix the bot's dodge logic now.
Bash Improve bot apple dodging and rerun seeds
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && python - <<'EOF'
p='tests/bot.js'; s=open(p,encoding='utf8').read()
old="if (!e.rolling && Math.abs(dx) < APPLE_DODGE_X && e.y < p.y) overhead = e;"
assert old in s
s=s.replace(old,"if (!e.onGround && Math.abs(dx) < APPLE_DODGE_X && e.y + e.h <= p.y + 2) overhead = e;")
s=s.replace("if (e.rolling && Math.abs(dx) < rollerD","if (e.rolling && e.onGround && Math.abs(dx) < rollerD")
open(p,'w',encoding='utf8').write(s)
EOF
node .tmp/seeds.js

OUT
seed 1 win time 128s deaths 1 continues 0
seed 2 win time 129s deaths 1 continues 0
seed 3 win time 133s deaths 1 continues 0
seed 42 win time 123s deaths 1 continues 0
seed 777 win time 122s deaths 1 continues 0
seed 9001 win time 123s deaths 1 continues 0
9:46 AM
All six seeds now win. Next I'll add a short README, note the build-time changes in DESIGN.md, then rerun everything.



Write C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\README.md
36 lines
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
Edit C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\DESIGN.md
Added 5 lines
Bash Clean scratch files and run all tests plus smoke test
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && rm -f .tmp/*.js .tmp/*.mjs .tmp/*.html .tmp/*.png && node --test 2>&1 | grep -E "^not ok|^# (pass|fail|tests)|playthrough:" && node tests/smoke.mjs && ls .tmp .tmp/screenshots && (tasklist //FI "IMAGENAME eq chrome.exe" 2>/dev/null | grep -c chrome || true)

OUT
# playthrough: mode=win x=392.2 ticks=7716 deaths=1 continues=0 time=126s score=24900
# tests 62
# pass 62
# fail 0
ok   page loads over file:// with no errors
ok   Space starts the game
ok   arrow keys move Kirby right
ok   holding Enter inhales
ok   Space in the air flies
ok   P pauses and resumes
ok   bot reaches the boss arena using key presses
ok   bot beats the boss and wins
ok   no console errors

SMOKE TEST PASSED (screenshots in .tmp/screenshots)
.tmp:
screenshots/

.tmp/screenshots:
01-title.png
02-run.png
03-inhale.png
04-fly.png
05-pause.png
06-boss.png
07-win.png
0
9:47 AM
Everything passes, and no Chrome processes are left running. A last visual check of the new inhale effect and the pause screen:



Read C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\.tmp\screenshots\03-inhale.png
Read C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\.tmp\screenshots\05-pause.png
9:47 AM
The pause screen looks right. One small visual flaw: the inhale wind lines are drawn through the hill. I'll skip any line that falls inside solid ground:



Bash Clip inhale wind lines at walls and rerun tests
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/4. agent.md + skills" && python - <<'EOF'
p='js/render.js'; s=open(p,encoding='utf8').read()
s=s.replace("function drawInhaleWind(p, v, f) {","function drawInhaleWind(p, v, f, world) {")
s=s.replace("if (p.inhaling) drawInhaleWind(p, v, f);","if (p.inhaling) drawInhaleWind(p, v, f, state.world);")
old="""      var x = m.x + p.facing * d - v.x, y = m.y + spread * (d / C.INHALE_RANGE) - v.y;"""
assert old in s
s=s.replace(old, old + """
      if (!Physics.clearLine(world, m.x, m.y, x + v.x, y + v.y)) continue;""")
open(p,'w',encoding='utf8').write(s)
EOF
node --test 2>&1 | grep -E "^not ok|^# (pass|fail)" && node tests/smoke.mjs | tail -2

OUT
# pass 62
# fail 0

SMOKE TEST PASSED (screenshots in .tmp/screenshots)
Read C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\4. agent.md + skills\.tmp\screenshots\03-inhale.png
9:47 AM
The game is built and every test passes: 62 unit tests, including a full playthrough that wins using only simulated key presses, plus the headless Chrome smoke test with no console errors. Chrome is closed afterwards, and nothing is committed.

How to run: double-click index.html. Space starts the game, the controls are shown on screen, and M mutes.

How to test (needs Node 22 or newer):


node --test            # 62 tests, including the full playthrough (~10 s)
node tests/smoke.mjs   # headless Chrome; screenshots saved to .tmp/screenshots
What's in it:

Six stretches plus the boss arena: Meadow, Cliffs, Star Block Fort, The Climb, Windy Sky (with a headwind), Gauntlet, then the tree boss Old Gnarlwood.
Four enemy types: walker, flyer, hopper, and spiky (which can't be inhaled). Star blocks can be inhaled and spat.
Health and lives: 3 lives with 6 health pips each, knockback, and a checkpoint at the start of every stretch.
Screens: game over offers Continue (score resets) or R for a full restart; the win screen shows time bonus and best score (saved between sessions); there's also a title and pause screen.
Sound: original chiptune effects plus two looping tunes, one for the level and one for the boss.
Checked against the request and DESIGN.md: everything is in. Where I fell short of the spec:

Level length: the bot finishes in about 2 minutes, with one death, knowing the level perfectly. I don't know if a first-time player takes the 5–7 minutes we aimed for.
Palette: 18 colours rather than about 16.
Constants: all gameplay numbers are in one constants block. Camera and effects tuning has its own small block in js/render.js, and the pixel coordinates in the sprite code are written inline.
Debug hook: the page exposes window.KirbyDebug so the smoke test can fast-forward to the boss. It still acts only through key presses.
Changes made during the build (also noted in DESIGN.md):

Checkpoints now activate when Kirby passes them at any height; before, flying over one silently skipped it.
The boss's air puffs are spaced further apart so the dodge rhythm is fair.
The tests caught a real bug: a big star (two things swallowed at once) burst against the floor the moment it was spat. That's fixed.
Extras I added:

Tutorial signs, banners naming each stretch, and floating score/hint text (including "SPIT FIRST!").
Screen shake and flashes, and enemies shrinking as they're swallowed.
Spike tiles.
Exhaling an air puff while flying (it can defeat enemies).
A big piercing star when two things are swallowed at once.
Auto-pause when the window loses focus.
A controls line under the game, and a short README.
What I couldn't verify:

How the sound and music actually sound. I only checked they cause no errors.
How the movement feels in real play, and how hard the level is for a person.
Browsers other than Chrome.
Known issues:

No sound until the first key press (a browser rule).
The wind in Windy Sky also pushes Kirby while he's standing on islands.
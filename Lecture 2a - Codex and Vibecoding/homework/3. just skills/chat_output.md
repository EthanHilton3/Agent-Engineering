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
7:54 PM
I'll start by looking at what's already in this directory.



Bash List project files and read any docs
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/3. just skills" && find . -path ./.git -prune -o -type f -print | head -50 && cat CLAUDE.md AGENTS.md README.md 2>/dev/null

OUT
Exit code 1
./.claude/skills/grill-me/SKILL.md
./kirby_game_prompt.txt
Bash Read the game prompt file
IN
cd "c:/Users/ethan/Documents/GitHub/Agent Engineering/Lecture 2a - Codex and Vibecoding/homework/3. just skills" && cat kirby_game_prompt.txt

OUT
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
7:54 PM
The directory is empty except for kirby_game_prompt.txt, which matches your request, and the grill-me skill. So this is a new project with no existing code or conventions to follow. One fixed constraint is that it has to run from index.html opened directly from disk (file://). That rules out ES module imports and any fetch-loaded data, so the game will use plain <script> tags or a single file.

Q1 of ~7: How limited should flight be?

Why it matters: in the original Kirby games you can fly forever, which makes every gap and pit trivial. Every later decision depends on this one: how gaps are placed, where the flying enemies go, and whether the level has any challenge at all.

My recommendation: allow unlimited flaps, but have each flap give a smaller lift than a jump, cap the rise speed, and make Kirby sink slowly between flaps. Flying also blocks inhaling: Kirby has to exhale a small air puff, which is also a weak attack, before he can inhale. That's faithful to the originals and stays fun. The challenge then comes from flying enemies patrolling the gaps and a low ceiling in places, not from a stamina meter.

Alternatives:

Flap cap: for example 6 flaps before Kirby gets tired and drops, reset on landing. This makes gaps a real threat, but it's less Kirby-like.
Stamina bar: a visible meter that drains while flying and refills on the ground. It's the most tunable, but it adds UI.


kirby_game_prompt.txt
use your recommendation
7:55 PM
Decision recorded: unlimited flaps with weak lift, a capped rise speed and a slow sink between flaps. Flying blocks inhaling, and exhaling an air puff (a weak attack) ends the flight.

Q2 of ~7: How does Kirby take damage?

Why it matters: this sets the difficulty and the HUD layout. It also decides what "surprisingly strong" means in practice. Pits are fatal in both options, which makes gaps dangerous even with unlimited flight.

My recommendation: Kirby gets a health bar of 6 pips per life, as in the classic games. Touching an enemy costs 1 pip, knocks him back and gives about 1.5 s of flashing invincibility. Falling into a pit costs a whole life. Kirby starts with 3 lives, and the level has a few heal pickups (food). It's forgiving enough that new players can enjoy the inhale and spit, and the pits still matter.

Alternatives:

One hit = one life, like Mario without power-ups: tense and simple, but harsh for a game built around getting close to enemies to inhale them.
3 pips per life: halfway between the two.


yes, do that
7:56 PM
Decision recorded: 6 health pips per life, enemy contact costs 1 pip with knockback and about 1.5 s of invincibility, pits cost a whole life, 3 lives to start, and a few food pickups that heal.

Q3 of ~7: Which enemies, and how many types?

Why it matters: every enemy type needs its own AI, sprite and animations, and each one changes how inhaling plays. This is the biggest scope decision after flight.

My recommendation: three types.

Walker (a Waddle Dee-style enemy): patrols and turns around at walls and ledges. It's the easy one to inhale.
Flyer (a Bronto Burt-style enemy): flies in a sine wave and sometimes swoops toward Kirby. It guards the gaps, so flying isn't free.
Hopper/shooter (a Gordo-free, cannon-ish enemy): stays put and periodically throws a slow projectile in an arc. Kirby can inhale the projectile and spit it back. That gives inhaling a defensive use and makes "objects" matter, not just enemies.
Alternatives:

Two types (walker and flyer): the minimum in your spec, and fastest to build.
Add an uninhalable spiky enemy (Gordo-style) as a fourth type: it forces Kirby to fly around it. It's nice for pacing but means more scope.


add an uninhalable spiky enemy and also include a final boss at the end fo the level
7:57 PM
Decision recorded: four enemy types (walker, flyer, cannon/shooter whose projectiles Kirby can inhale, and an uninhalable spiky enemy) plus a final boss.

Q4 of ~7: What is the boss, and how does it tie to the end of the level?

Why it matters: the boss needs its own arena, attack patterns and win condition. The spec says Kirby can't damage things directly except by spitting what he's swallowed, so the boss fight has to supply ammo.

My recommendation: a Whispy Woods-style tree boss in a locked arena at the end of the level, where the camera stops scrolling.

Attacks: it drops apples from its canopy, and Kirby can inhale them and spit them back as ammo. It also blows slow air puffs that cost a pip but can't be inhaled.
Health and phase 2: it has 6 HP shown as a boss bar. At half health it gets faster and starts dropping a spiky enemy now and then.
Ending: when it's defeated, a warp star appears. Touching the star is the goal and triggers the win screen.
A stationary boss is the right fit for the inhale-and-spit mechanic, it's readable, and it stays a reasonable scope.

Alternatives:

Mobile King Dedede-style boss that jumps and slams, with the shockwaves spawning stars that Kirby can inhale: more dynamic, but its AI is more complex.
A tougher mini-boss that guards the goal door without its own arena: the cheapest option.


i love the tree boss idea
7:58 PM
Decision recorded: a Whispy-style tree boss in a locked arena at the end of the level. It has 6 HP and a second phase, drops apples Kirby can inhale and spit back, and blows air puffs he can't inhale. When it's defeated a warp star appears, and touching the star wins the game.

Q5 of ~7: How should "surprisingly strong" show up in the inhale?

Why it matters: this defines the signature mechanic. It decides what objects exist in the level besides enemies, and how much spitting rewards the player.

My recommendation:

Star blocks made of breakable terrain, which Kirby can inhale to open paths and hidden areas (some hold food or score bonuses).
Big heavy objects: Kirby can also inhale a few oversized items, like a boulder 2× his size. He visibly strains, the screen shakes, and the pull is slower. That's the "surprisingly strong" moment.
Projectile: a spat star flies straight, defeats every regular enemy in its path, and breaks when it hits a wall. Spitting a large object fires a bigger star that pierces and is worth more points.
Swallowing: pressing Down while full swallows the item for a small score bonus and nothing else. Copy abilities are out of scope.
Alternatives:

Enemies and projectiles only, no level objects: the simplest version, but the inhale feels less special.
Copy abilities (swallowing an enemy gives a power): very Kirby, but it's a large scope increase.


add a copy abilty as well
7:59 PM
Decision recorded: my inhale recommendation (star blocks, big heavy objects with a strain effect and screen shake, piercing big stars, Down to swallow), plus copy abilities.

Q6 of ~8: Which copy abilities, and how do they work?

Why it matters: each ability is a new attack with its own sprite, hat, hitbox and balance against the boss. It also changes how the Enter key works, because with an ability equipped Kirby can't inhale.

My recommendation: one ability, from the cannon/shooter enemy only: a Fire ability.

Getting it: swallow the shooter with Down to get Fire, shown by a flame crown on Kirby.
Using it: holding Enter breathes a short flame stream in front of Kirby that hurts all regular enemies and the boss.
Dropping it: pressing Shift (or losing a pip) drops the ability as a bouncing star that Kirby can re-inhale.
Other enemies: walkers and flyers give no ability, as in the original, so the classic inhale-and-spit loop stays the core.
Boss balance: fire deals 1 damage per second of contact to the boss. It's slower than spitting apples (1 per hit), so both strategies work.
The ability icon and name go in the HUD.

Alternatives:

Two abilities: Fire from the shooter and Spark from the flyer (a radial zap around Kirby). More variety, about twice the work.
Sword from the walker: a melee slash that's simpler to tune, though giving walkers an ability means the most common enemy almost always grants a power.


can you make a new creature that is specifically a fire creature that when inhaled and shallowed, gives kirby teh fire power? That way the enemeies stay consistent with the abilities they are giving kirby
8:01 PM
Decision recorded: a new fire creature (Hot Head-style) is the only source of the Fire ability. The cannon/shooter gives no ability. Each ability-granting enemy visibly matches its power.

That makes six enemy types: walker, flyer, shooter, spiky, fire creature and the tree boss. For behavior, I'll have the fire creature walk slowly, pause, and puff a short flame forward every few seconds. That makes it dangerous to approach head-on, which is the risk you take for its reward.

Q7 of ~8: How long is the level, and is there a checkpoint?

Why it matters: with six enemy types, star blocks, heavy objects and a boss, the level needs room to introduce each one. And losing a life at the boss shouldn't send you back through the whole level.

My recommendation: about 3 to 4 minutes of play for a first run, about 200 tiles wide, in four sections that each introduce one idea:

Grassland: walkers and star blocks teach inhale and spit.
Cliffs and gaps: flyers, pits and a low ceiling test flight.
Hill: shooters, a spiky enemy and the first boulder (the "strong" moment).
Fire grove: fire creatures, then a checkpoint door right before the boss arena.
Losing a life respawns Kirby at the last checkpoint passed: the start, the midpoint flag or the boss door. Game over restarts the whole level, and score resets on restart.

Alternatives:

Shorter, about 2 minutes: tighter, but the enemies get crowded together.
No checkpoints: more old-school and harsher, but the boss fight becomes a slog.


go with your recommendation
8:02 PM
Decision recorded: a level of about 200 tiles in four sections, with checkpoints at the start, the midpoint and the boss door. Game over restarts the whole level.

Q8 of 8 (last one): Should the game have sound, and how should it be presented?

Why it matters: the spec says "polished and fun" but doesn't mention audio. Sound is a big part of what makes an inhale feel satisfying, and the whole presentation (resolution, scaling, title screen) is easier to settle now than to retrofit.

My recommendation:

Sound: synthesized Web Audio effects with no files, for jump, flap, the inhale whoosh, swallow, spit, hit, enemy pop, fire, boss hit and win and lose jingles. M toggles mute. Audio starts on the first keypress because browsers require that. No background music, since it's costly to make sound good.
Resolution: a 256×224 internal canvas (the SNES resolution) scaled up by an integer factor to fill the window, with image-rendering: pixelated.
Palette: one fixed palette of about 24 colors.
Screens: a title screen ("Press Enter"), a pause on P/Esc, and the controls always visible in a small strip below the game.
Alternatives:

Silent: less work, but the game feels noticeably less polished.
Sound effects plus a simple chiptune loop: the most charming, at the cost of a sequencer and composing time.


go with your rec
Write C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\3. just skills\DESIGN.md
41 lines
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
8:03 PM
Written for you and any later coding session that builds from this spec.

The spec is in DESIGN.md. It records your eight answers, including the three you changed from my recommendations:

a spiky enemy that can't be inhaled,
the tree boss,
a dedicated fire creature as the only source of the Fire ability.
I chose two things you didn't weigh in on; they're marked "(default)":

Scoring: what earns points.
Files: index.html plus a few plain scripts in js/, which still works when the page is opened straight from disk.
The new mechanics also needed three keys your original spec didn't list: Down to swallow, Shift to drop an ability, and P/Esc to pause.

I won't write any game code until you approve the spec or ask for changes.



DESIGN.md
implement the design.md
8:20 PM
I'll build it now. The plan is index.html plus six plain scripts in js/: core utilities and audio, sprites, the level, entities, Kirby, and the game loop.



Write C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\3. just skills\index.html
42 lines
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kirby's Pixel Quest</title>
<style>
  :root { --bg: #0e0818; --ink: #1b1029; --pink: #ff9ccb; --text: #fff8f0; --dim: #9aa0b4; }
  html, body { margin: 0; height: 100%; background: var(--bg); color: var(--text); overflow: hidden;
    font-family: ui-monospace, "Cascadia Mono", Consolas, monospace; }
  #wrap { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; gap: 12px; }
  canvas { display: block; image-rendering: pixelated; image-rendering: crisp-edges;
    box-shadow: 0 0 0 4px var(--ink), 0 0 0 6px #ff9ccb66, 0 10px 40px #000a; }
  #controls { display: flex; flex-wrap: wrap; justify-content: center; gap: 6px 16px; padding: 0 16px;
    max-width: 960px; font-size: 13px; color: var(--dim); }
  #controls span { white-space: nowrap; }
  kbd { display: inline-block; min-width: 1.2em; padding: 1px 5px; margin: 0 1px; border-radius: 3px; text-align: center;
    background: #241838; color: var(--pink); border: 1px solid #ff9ccb55; border-bottom-width: 3px; font: inherit; }
</style>
</head>
<body>
<div id="wrap">
  <canvas id="game" width="256" height="224"></canvas>
  <div id="controls">
    <span><kbd>&larr;</kbd><kbd>&rarr;</kbd> / <kbd>A</kbd><kbd>D</kbd> Move</span>
    <span><kbd>Space</kbd> Jump &middot; tap in air to Fly</span>
    <span><kbd>Enter</kbd> hold: Inhale &middot; tap: Spit / Exhale &middot; with Fire: breathe</span>
    <span><kbd>&darr;</kbd> Swallow</span>
    <span><kbd>Shift</kbd> Drop ability</span>
    <span><kbd>P</kbd> Pause</span>
    <span><kbd>M</kbd> Mute</span>
  </div>
</div>
<script src="js/core.js"></script>
<script src="js/sprites.js"></script>
<script src="js/level.js"></script>
<script src="js/entities.js"></script>
<script src="js/kirby.js"></script>
<script src="js/game.js"></script>
</body>
</html>
Write C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\3. just skills\js\core.js
323 lines
'use strict';
// Core: constants, palette, pixel raster helpers, bitmap font, input, synthesized audio.

const TILE = 16;
const VIEW_W = 256, VIEW_H = 192, SCREEN_H = 224;

// One fixed palette for everything in the game.
const PAL = {
  ink: '#1b1029', white: '#fff8f0', navy: '#1e2a5a', blue: '#3a6ee8',
  sky: '#8fd3ff', skyL: '#c9ecff',
  pinkL: '#ffd2e6', pink: '#ff9ccb', pinkD: '#e06aa0',
  red: '#e8303c', redD: '#9c1838', orange: '#ff9a3c', dusk: '#ff9d6e',
  tan: '#ffd9a0', yellow: '#ffe24a', gold: '#e0a01c',
  greenL: '#a8f07c', green: '#5ccf4a', greenD: '#2b8a3e', teal: '#6cc4a8',
  brown: '#b0682c', brownD: '#6b3a1e',
  purple: '#9a5ad8', purpleD: '#5b2f8f', gray: '#9aa0b4', grayD: '#565c78',
};

const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
const rand = (a, b) => a + Math.random() * (b - a);
const pick = (arr) => arr[(Math.random() * arr.length) | 0];
const overlap = (a, b) => a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
const approach = (v, t, s) => (v < t ? Math.min(v + s, t) : Math.max(v - s, t));

function makeCanvas(w, h) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  return c;
}

// Draws an image at integer coords, optionally mirrored horizontally around its own center.
function blit(ctx, img, x, y, flip) {
  x = Math.round(x); y = Math.round(y);
  if (!flip) { ctx.drawImage(img, x, y); return; }
  ctx.save();
  ctx.translate(x + img.width, y);
  ctx.scale(-1, 1);
  ctx.drawImage(img, 0, 0);
  ctx.restore();
}

// ---------- Pixel raster helper: every shape is rasterized pixel by pixel, so edges stay crisp ----------
class Pix {
  constructor(w, h) {
    this.c = makeCanvas(w, h);
    this.g = this.c.getContext('2d');
  }
  px(x, y, col) { this.g.fillStyle = col; this.g.fillRect(x | 0, y | 0, 1, 1); }
  rect(x, y, w, h, col) { this.g.fillStyle = col; this.g.fillRect(x, y, w, h); }
  // Fills every pixel where inside(x,y); colorAt picks the color (edge = touches the outside).
  shape(x0, y0, x1, y1, inside, colorAt) {
    for (let y = y0; y < y1; y++) {
      for (let x = x0; x < x1; x++) {
        if (!inside(x, y)) continue;
        const edge = !inside(x - 1, y) || !inside(x + 1, y) || !inside(x, y - 1) || !inside(x, y + 1);
        const col = colorAt(x, y, edge);
        if (col) this.px(x, y, col);
      }
    }
  }
  ellipse(cx, cy, rx, ry, fill, outline, shade, light) {
    const inside = (x, y) => {
      const dx = (x + 0.5 - cx) / rx, dy = (y + 0.5 - cy) / ry;
      return dx * dx + dy * dy <= 1;
    };
    this.shape(Math.floor(cx - rx - 1), Math.floor(cy - ry - 1), Math.ceil(cx + rx + 1), Math.ceil(cy + ry + 1), inside,
      (x, y, edge) => {
        if (edge && outline) return outline;
        const dx = (x + 0.5 - cx) / rx, dy = (y + 0.5 - cy) / ry;
        if (light && (dx + 0.42) ** 2 + (dy + 0.45) ** 2 < 0.06) return light;
        if (shade && dx * 0.35 + dy > 0.55) return shade;
        return fill;
      });
  }
  poly(pts, fill, outline, shade) {
    const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
    const inside = (x, y) => pointInPoly(pts, x + 0.5, y + 0.5);
    const cy = (Math.min(...ys) + Math.max(...ys)) / 2, h = Math.max(...ys) - Math.min(...ys);
    this.shape(Math.floor(Math.min(...xs)) - 1, Math.floor(Math.min(...ys)) - 1, Math.ceil(Math.max(...xs)) + 1, Math.ceil(Math.max(...ys)) + 1,
      inside, (x, y, edge) => {
        if (edge && outline) return outline;
        if (shade && y + 0.5 > cy + h * 0.22) return shade;
        return fill;
      });
  }
}

function pointInPoly(pts, x, y) {
  let c = false;
  for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
    const [xi, yi] = pts[i], [xj, yj] = pts[j];
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) c = !c;
  }
  return c;
}

function starPoints(cx, cy, ro, ri, rot) {
  const pts = [];
  for (let i = 0; i < 10; i++) {
    const r = i % 2 ? ri : ro, a = -Math.PI / 2 + rot + (i * Math.PI) / 5;
    pts.push([cx + Math.cos(a) * r, cy + Math.sin(a) * r]);
  }
  return pts;
}

// ---------- 5x7 bitmap font ----------
const FONT = {
  A: [14, 17, 17, 31, 17, 17, 17], B: [30, 17, 17, 30, 17, 17, 30], C: [14, 17, 16, 16, 16, 17, 14],
  D: [30, 17, 17, 17, 17, 17, 30], E: [31, 16, 16, 30, 16, 16, 31], F: [31, 16, 16, 30, 16, 16, 16],
  G: [14, 17, 16, 23, 17, 17, 15], H: [17, 17, 17, 31, 17, 17, 17], I: [14, 4, 4, 4, 4, 4, 14],
  J: [7, 2, 2, 2, 2, 18, 12], K: [17, 18, 20, 24, 20, 18, 17], L: [16, 16, 16, 16, 16, 16, 31],
  M: [17, 27, 21, 21, 17, 17, 17], N: [17, 17, 25, 21, 19, 17, 17], O: [14, 17, 17, 17, 17, 17, 14],
  P: [30, 17, 17, 30, 16, 16, 16], Q: [14, 17, 17, 17, 21, 18, 13], R: [30, 17, 17, 30, 20, 18, 17],
  S: [15, 16, 16, 14, 1, 1, 30], T: [31, 4, 4, 4, 4, 4, 4], U: [17, 17, 17, 17, 17, 17, 14],
  V: [17, 17, 17, 17, 17, 10, 4], W: [17, 17, 17, 21, 21, 21, 10], X: [17, 17, 10, 4, 10, 17, 17],
  Y: [17, 17, 17, 10, 4, 4, 4], Z: [31, 1, 2, 4, 8, 16, 31],
  0: [14, 17, 19, 21, 25, 17, 14], 1: [4, 12, 4, 4, 4, 4, 14], 2: [14, 17, 1, 2, 4, 8, 31],
  3: [31, 2, 4, 2, 1, 17, 14], 4: [2, 6, 10, 18, 31, 2, 2], 5: [31, 16, 30, 1, 1, 17, 14],
  6: [6, 8, 16, 30, 17, 17, 14], 7: [31, 1, 2, 4, 8, 8, 8], 8: [14, 17, 17, 14, 17, 17, 14],
  9: [14, 17, 17, 15, 1, 2, 12],
  '!': [4, 4, 4, 4, 4, 0, 4], '.': [0, 0, 0, 0, 0, 12, 12], ',': [0, 0, 0, 0, 12, 4, 8],
  ':': [0, 12, 12, 0, 12, 12, 0], '-': [0, 0, 0, 31, 0, 0, 0], '/': [0, 1, 2, 4, 8, 16, 0],
  '?': [14, 17, 1, 2, 4, 0, 4], "'": [4, 4, 8, 0, 0, 0, 0], '+': [0, 4, 4, 31, 4, 4, 0],
  '(': [2, 4, 8, 8, 8, 4, 2], ')': [8, 4, 2, 2, 2, 4, 8], '=': [0, 0, 31, 0, 31, 0, 0],
  '<': [2, 4, 8, 16, 8, 4, 2], '>': [8, 4, 2, 1, 2, 4, 8], '*': [0, 21, 14, 31, 14, 21, 0],
};
const glyphCache = new Map();
function getGlyph(ch, col) {
  const key = ch + col;
  let c = glyphCache.get(key);
  if (!c) {
    const rows = FONT[ch] || FONT['?'];
    c = makeCanvas(5, 7);
    const g = c.getContext('2d');
    g.fillStyle = col;
    rows.forEach((r, y) => { for (let x = 0; x < 5; x++) if (r & (16 >> x)) g.fillRect(x, y, 1, 1); });
    glyphCache.set(key, c);
  }
  return c;
}
function textWidth(s, scale = 1) { return (String(s).length * 6 - 1) * scale; }
// opts: scale, align ('left'|'center'|'right'), shadow (color), outline (color)
function drawText(ctx, s, x, y, col, o = {}) {
  s = String(s).toUpperCase();
  const sc = o.scale || 1;
  const w = textWidth(s, sc);
  if (o.align === 'center') x -= w / 2;
  else if (o.align === 'right') x -= w;
  x = Math.round(x); y = Math.round(y);
  const pass = (c, ox, oy) => {
    for (let i = 0; i < s.length; i++) {
      if (s[i] === ' ') continue;
      ctx.drawImage(getGlyph(s[i], c), x + i * 6 * sc + ox, y + oy, 5 * sc, 7 * sc);
    }
  };
  if (o.outline) {
    const d = o.ow || 1;
    for (const [ox, oy] of [[-d, 0], [d, 0], [0, -d], [0, d], [-d, -d], [d, d], [-d, d], [d, -d]]) pass(o.outline, ox, oy);
    if (o.shadow) pass(o.shadow, d + 1, d + 1);
  } else if (o.shadow) pass(o.shadow, 1, 1);
  pass(col, 0, 0);
}

// ---------- Input ----------
const Input = (() => {
  const MAP = {
    ArrowLeft: 'left', KeyA: 'left', ArrowRight: 'right', KeyD: 'right',
    ArrowDown: 'down', KeyS: 'down', ArrowUp: 'up', KeyW: 'up',
    Space: 'jump', Enter: 'action', NumpadEnter: 'action',
    ShiftLeft: 'drop', ShiftRight: 'drop', KeyP: 'pause', Escape: 'pause', KeyM: 'mute',
  };
  const codes = new Set(), hits = new Set();
  addEventListener('keydown', (e) => {
    const a = MAP[e.code];
    if (!a) return;
    e.preventDefault();
    Sound.init();
    if (!codes.has(e.code)) hits.add(a);
    codes.add(e.code);
  });
  addEventListener('keyup', (e) => { if (MAP[e.code]) { codes.delete(e.code); e.preventDefault(); } });
  addEventListener('blur', () => codes.clear());
  return {
    held(a) { for (const c of codes) if (MAP[c] === a) return true; return false; },
    hit(a) { return hits.has(a); },
    endStep() { hits.clear(); },
  };
})();

// ---------- Synthesized sound (Web Audio, no files) ----------
const Sound = (() => {
  let ac = null, master = null, noiseBuf = null, muted = false;
  const loops = {};
  const VOL = 0.32;

  function init() {
    if (!ac) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return;
      ac = new AC();
      master = ac.createGain();
      master.gain.value = muted ? 0 : VOL;
      master.connect(ac.destination);
      noiseBuf = ac.createBuffer(1, ac.sampleRate, ac.sampleRate);
      const d = noiseBuf.getChannelData(0);
      for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    }
    if (ac.state === 'suspended') ac.resume();
  }
  function env(g, t0, v, d) {
    g.gain.setValueAtTime(0.0001, t0);
    g.gain.linearRampToValueAtTime(v, t0 + 0.005);
    g.gain.exponentialRampToValueAtTime(0.0001, t0 + d);
  }
  function tone(f, d, o = {}) {
    if (!ac) return;
    const t0 = ac.currentTime + (o.at || 0);
    const osc = ac.createOscillator(), g = ac.createGain();
    osc.type = o.type || 'square';
    osc.frequency.setValueAtTime(f, t0);
    if (o.to) osc.frequency.exponentialRampToValueAtTime(o.to, t0 + d);
    env(g, t0, o.vol ?? 0.15, d);
    osc.connect(g); g.connect(master);
    osc.start(t0); osc.stop(t0 + d + 0.05);
  }
  function noise(d, o = {}) {
    if (!ac) return;
    const t0 = ac.currentTime + (o.at || 0);
    const src = ac.createBufferSource();
    src.buffer = noiseBuf;
    const f = ac.createBiquadFilter();
    f.type = o.filter || 'bandpass';
    f.frequency.setValueAtTime(o.f || 1200, t0);
    if (o.to) f.frequency.exponentialRampToValueAtTime(o.to, t0 + d);
    f.Q.value = o.q ?? 1;
    const g = ac.createGain();
    env(g, t0, o.vol ?? 0.2, d);
    src.connect(f); f.connect(g); g.connect(master);
    src.start(t0, Math.random() * 0.5); src.stop(t0 + d + 0.05);
  }
  function seq(notes, o = {}) {
    let t = 0;
    for (const [f, d] of notes) { if (f) tone(f, d * 0.95, { ...o, at: t }); t += d; }
  }
  // Continuous sounds (inhale wind, fire breath); calling with the same state is a no-op.
  function loop(name, on) {
    if (!ac) return;
    const L = loops[name];
    if (on && !L) {
      const t0 = ac.currentTime;
      const src = ac.createBufferSource();
      src.buffer = noiseBuf; src.loop = true;
      const f = ac.createBiquadFilter(), g = ac.createGain();
      g.gain.setValueAtTime(0.0001, t0);
      let lfo = null;
      if (name === 'inhale') {
        f.type = 'bandpass'; f.Q.value = 3;
        f.frequency.setValueAtTime(300, t0);
        f.frequency.exponentialRampToValueAtTime(1700, t0 + 0.5);
        g.gain.linearRampToValueAtTime(0.22, t0 + 0.08);
      } else {
        f.type = 'lowpass'; f.Q.value = 5; f.frequency.setValueAtTime(800, t0);
        g.gain.linearRampToValueAtTime(0.16, t0 + 0.04);
        lfo = ac.createOscillator(); lfo.frequency.value = 17;
        const lg = ac.createGain(); lg.gain.value = 0.07;
        lfo.connect(lg); lg.connect(g.gain); lfo.start(t0);
      }
      src.connect(f); f.connect(g); g.connect(master);
      src.start(t0);
      loops[name] = { src, g, lfo };
    } else if (!on && L) {
      const t0 = ac.currentTime;
      L.g.gain.cancelScheduledValues(t0);
      L.g.gain.setValueAtTime(Math.max(0.0001, L.g.gain.value), t0);
      L.g.gain.linearRampToValueAtTime(0, t0 + 0.06);
      L.src.stop(t0 + 0.08);
      if (L.lfo) L.lfo.stop(t0 + 0.08);
      delete loops[name];
    }
  }

  return {
    init, loop,
    stopLoops() { for (const k of Object.keys(loops)) loop(k, false); },
    toggleMute() { muted = !muted; if (master) master.gain.value = muted ? 0 : VOL; return muted; },
    get muted() { return muted; },
    jump() { tone(300, 0.15, { to: 620, vol: 0.12 }); },
    flap() { tone(600, 0.07, { to: 900, type: 'triangle', vol: 0.12 }); noise(0.08, { f: 3000, vol: 0.04 }); },
    puffUp() { tone(250, 0.12, { to: 520, type: 'triangle', vol: 0.12 }); },
    puff() { noise(0.18, { f: 1800, to: 500, vol: 0.18 }); tone(500, 0.1, { to: 200, type: 'triangle', vol: 0.08 }); },
    land() { noise(0.06, { f: 400, vol: 0.08, filter: 'lowpass' }); },
    spit(big) { tone(big ? 500 : 900, 0.15, { to: big ? 110 : 250, vol: 0.15 }); noise(0.1, { f: 2000, vol: 0.1 }); },
    gulp() { tone(420, 0.08, { to: 150, type: 'triangle', vol: 0.2 }); tone(190, 0.09, { at: 0.08, to: 120, type: 'triangle', vol: 0.15 }); },
    swallow() { seq([[392, 0.06], [330, 0.06], [262, 0.1]], { type: 'triangle', vol: 0.15 }); },
    power() { seq([[523, 0.07], [659, 0.07], [784, 0.07], [1047, 0.18]], { vol: 0.12 }); },
    drop() { tone(700, 0.2, { to: 300, vol: 0.1 }); },
    hurt() { tone(220, 0.25, { to: 70, vol: 0.18 }); noise(0.15, { f: 900, vol: 0.12 }); },
    die() { seq([[784, 0.1], [659, 0.1], [523, 0.1], [392, 0.25], [0, 0.1], [262, 0.4]], { vol: 0.12 }); },
    pop() { noise(0.12, { f: 2500, to: 800, vol: 0.15 }); tone(880, 0.08, { to: 1400, vol: 0.08 }); },
    clink() { tone(1800, 0.08, { type: 'triangle', vol: 0.12 }); tone(2400, 0.12, { type: 'triangle', vol: 0.08, at: 0.03 }); },
    crumble() { noise(0.15, { f: 900, to: 300, vol: 0.18, filter: 'lowpass' }); },
    rumble() { noise(0.18, { f: 120, vol: 0.25, filter: 'lowpass' }); },
    rip() { noise(0.35, { f: 300, to: 2000, vol: 0.25 }); tone(90, 0.3, { to: 200, type: 'sawtooth', vol: 0.12 }); },
    thud() { noise(0.12, { f: 200, vol: 0.25, filter: 'lowpass' }); tone(110, 0.1, { to: 60, type: 'sine', vol: 0.2 }); },
    heal() { seq([[659, 0.06], [784, 0.06], [988, 0.06], [1319, 0.12]], { type: 'triangle', vol: 0.14 }); },
    checkpoint() { seq([[523, 0.08], [784, 0.08], [1047, 0.16]], { vol: 0.1 }); },
    door() { seq([[392, 0.08], [523, 0.08], [659, 0.08], [784, 0.2]], { type: 'triangle', vol: 0.13 }); },
    bossIntro() { seq([[196, 0.2], [0, 0.05], [196, 0.12], [233, 0.12], [262, 0.35]], { type: 'sawtooth', vol: 0.09 }); },
    bossHit() { tone(160, 0.22, { to: 70, type: 'sawtooth', vol: 0.18 }); noise(0.15, { f: 600, vol: 0.15 }); },
    bossDie() { seq([[392, 0.12], [330, 0.12], [262, 0.12], [196, 0.12], [131, 0.5]], { type: 'sawtooth', vol: 0.1 }); noise(1.2, { f: 400, to: 100, vol: 0.15, filter: 'lowpass' }); },
    blow() { noise(0.35, { f: 600, to: 1500, vol: 0.15 }); },
    rustle() { noise(0.2, { f: 3500, vol: 0.08 }); },
    lob() { tone(180, 0.1, { to: 90, vol: 0.1 }); noise(0.08, { f: 500, vol: 0.1, filter: 'lowpass' }); },
    fireBurst() { noise(0.45, { f: 500, vol: 0.12, filter: 'lowpass' }); },
    star() { seq([[784, 0.06], [988, 0.06], [1175, 0.06], [1568, 0.2]], { type: 'triangle', vol: 0.12 }); },
    bonus() { seq([[1047, 0.05], [1319, 0.05], [1568, 0.1]], { type: 'triangle', vol: 0.1 }); },
    win() { seq([[523, 0.12], [523, 0.12], [523, 0.12], [523, 0.3], [415, 0.3], [466, 0.3], [523, 0.15], [0, 0.08], [466, 0.12], [523, 0.5]], { vol: 0.11 }); },
    gameOver() { seq([[392, 0.25], [330, 0.25], [262, 0.25], [196, 0.6]], { type: 'triangle', vol: 0.15 }); },
    start() { seq([[523, 0.08], [659, 0.08], [784, 0.08], [1047, 0.2]], { vol: 0.1 }); },
    pause() { tone(880, 0.08, { type: 'triangle', vol: 0.1 }); tone(660, 0.08, { type: 'triangle', vol: 0.1, at: 0.08 }); },
  };
})();
Write C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\3. just skills\js\sprites.js
319 lines
'use strict';
// All sprites are rasterized in code at startup. Every sprite faces right; blit() mirrors for left.

const SPR = {};

// ---------- Kirby (24x24 frames, feet rest on row 22) ----------
const KIRBY_FOOT = 22;

function drawEyes(p, kind, L, R, y) {
  const I = PAL.ink;
  for (const x of [L, R]) {
    switch (kind) {
      case 'open': p.rect(x, y, 2, 4, I); p.px(x, y, PAL.white); p.rect(x, y + 3, 2, 1, PAL.blue); break;
      case 'wide': p.rect(x, y - 1, 2, 5, I); p.rect(x, y - 1, 1, 2, PAL.white); p.rect(x, y + 3, 2, 1, PAL.blue); break;
      case 'blink': p.rect(x, y + 2, 2, 1, I); break;
      case 'shut': p.rect(x, y + 2, 2, 1, I); p.px(x === L ? x + 1 : x, y + 1, I); break;
      case 'happy': p.px(x, y + 2, I); p.px(x + 1, y + 1, I); p.px(x + 2, y + 2, I); break;
      case 'x': p.px(x, y, I); p.px(x + 2, y, I); p.px(x + 1, y + 1, I); p.px(x, y + 2, I); p.px(x + 2, y + 2, I); break;
      case 'strain':
        if (x === L) { p.px(x, y, I); p.px(x + 1, y + 1, I); p.px(x, y + 2, I); }
        else { p.px(x + 1, y, I); p.px(x, y + 1, I); p.px(x + 1, y + 2, I); }
        break;
    }
  }
}

function kirbyFrame(o = {}) {
  const p = new Pix(24, 24);
  const cx = 12 + (o.dx || 0), cy = o.cy ?? 15, rx = o.rx ?? 6.5, ry = o.ry ?? 6;
  const arm = (x, y) => p.ellipse(x, y, 2.3, 1.9, PAL.pink, PAL.ink, PAL.pinkD);
  switch (o.arms || 'side') {
    case 'side': arm(cx - rx + 0.6, cy + 1.6); arm(cx + rx - 0.6, cy + 1.6); break;
    case 'up': arm(cx - rx + 1.2, cy - ry + 3); arm(cx + rx - 1.2, cy - ry + 3); break;
    case 'down': arm(cx - rx + 0.2, cy + 3.4); arm(cx + rx - 0.2, cy + 3.4); break;
    case 'back': arm(cx - rx + 0.2, cy - 0.5); arm(cx - rx + 1.6, cy + 3); break;
    case 'wide': arm(cx - rx - 0.6, cy - 1.5); arm(cx + rx + 0.6, cy - 1.5); break;
  }
  p.ellipse(cx, cy, rx, ry, PAL.pink, PAL.ink, PAL.pinkD, PAL.pinkL);
  const bottom = cy + ry, f = o.feet || [0, 0, 0, 0];
  p.ellipse(cx - 3.4 + f[0], bottom - 0.6 + f[1], 3, 1.75, PAL.red, PAL.ink, PAL.redD);
  p.ellipse(cx + 3.4 + f[2], bottom - 0.6 + f[3], 3, 1.75, PAL.red, PAL.ink, PAL.redD);

  const ex = Math.round(cx + (o.eyeDx ?? 1.5));
  const ey = Math.round(cy - 3.5 + (o.eyeDy || 0));
  const L = ex - 3, R = ex + 1;
  // mouth first so the eyes always read on top
  const my = ey + 5;
  switch (o.mouth || 'smile') {
    case 'smile': p.rect(ex - 1, my, 2, 1, PAL.redD); break;
    case 'o': p.ellipse(ex, my + 0.5, 1.5, 1.6, PAL.redD, PAL.ink); break;
    case 'open': p.ellipse(ex + 0.5, my + 0.6, 2, 2.2, PAL.redD, PAL.ink); break;
    case 'puff': p.rect(ex - 1, my + 1, 2, 1, PAL.ink); break;
    case 'big': {
      const mx = cx + rx - 3.2, mcy = cy + 1.8;
      p.ellipse(mx, mcy, 3, 3.6, PAL.redD, PAL.ink);
      p.rect(Math.round(mx) - 1, Math.round(mcy + 1.5), 2, 1, PAL.pinkD);
      break;
    }
  }
  drawEyes(p, o.eyes || 'open', L, R, ey);
  if (o.blush !== false) { p.px(L - 2, ey + 5, PAL.red); p.px(L - 1, ey + 5, PAL.red); p.px(R + 2, ey + 5, PAL.red); }
  return { c: p.c, top: Math.round(cy - ry) };
}

function buildKirby() {
  const K = {};
  K.idle = kirbyFrame({});
  K.blink = kirbyFrame({ eyes: 'blink' });
  K.run0 = kirbyFrame({ cy: 14.5, feet: [2, -1, -1, 0], arms: 'down' });
  K.run1 = kirbyFrame({ cy: 15 });
  K.run2 = kirbyFrame({ cy: 14.5, feet: [-1, 0, 2, -1], arms: 'down' });
  K.run3 = kirbyFrame({ cy: 15 });
  K.jump = kirbyFrame({ rx: 6, ry: 6.6, cy: 14.4, arms: 'up', feet: [0.5, -0.5, -0.5, -0.5] });
  K.fall = kirbyFrame({ rx: 7, ry: 5.7, cy: 15.3, arms: 'wide' });
  K.land = kirbyFrame({ rx: 7.6, ry: 5.1, cy: 15.9, eyes: 'blink' });
  K.fly0 = kirbyFrame({ rx: 8.2, ry: 7.6, cy: 13.4, arms: 'up', mouth: 'puff', eyeDy: -0.5 });
  K.fly1 = kirbyFrame({ rx: 8.4, ry: 7.3, cy: 13.6, arms: 'down', mouth: 'puff', eyeDy: -0.5 });
  K.inhale0 = kirbyFrame({ rx: 7, ry: 6.4, cy: 14.6, dx: -0.5, arms: 'back', eyes: 'shut', eyeDx: -2, mouth: 'big', feet: [-1, 0, 1, 0] });
  K.inhale1 = kirbyFrame({ rx: 7.2, ry: 6.7, cy: 14.3, dx: -0.5, arms: 'back', eyes: 'shut', eyeDx: -2, mouth: 'big', feet: [-1, 0, 1, 0] });
  K.strain0 = kirbyFrame({ rx: 7.3, ry: 6.2, cy: 14.8, dx: -1.5, arms: 'back', eyes: 'strain', eyeDx: -2, mouth: 'big', feet: [-2, 0, 2, 0] });
  K.strain1 = kirbyFrame({ rx: 7.6, ry: 6, cy: 15, dx: -1.5, arms: 'back', eyes: 'strain', eyeDx: -2, mouth: 'big', feet: [-2, 0, 2, 0] });
  K.full = kirbyFrame({ rx: 8, ry: 6.8, cy: 14.2, mouth: 'puff' });
  K.fullRun0 = kirbyFrame({ rx: 8, ry: 6.8, cy: 14, mouth: 'puff', feet: [1.5, -1, -1, 0] });
  K.fullRun1 = kirbyFrame({ rx: 8, ry: 6.8, cy: 14, mouth: 'puff', feet: [-1, 0, 1.5, -1] });
  K.spit = kirbyFrame({ rx: 6.4, ry: 6.2, dx: -1, mouth: 'o', arms: 'back' });
  K.swallow = kirbyFrame({ rx: 7.2, ry: 5.6, cy: 15.4, eyes: 'happy', mouth: 'smile', arms: 'up' });
  K.hurt = kirbyFrame({ rx: 7, ry: 5.5, cy: 15.5, eyes: 'x', mouth: 'o', arms: 'up' });
  K.dead = kirbyFrame({ eyes: 'wide', mouth: 'o', arms: 'wide' });
  K.fire0 = kirbyFrame({ rx: 6.8, ry: 6.2, dx: -0.5, mouth: 'open', arms: 'back', eyes: 'shut' });
  K.fire1 = kirbyFrame({ rx: 7, ry: 6.4, cy: 14.8, dx: -0.5, mouth: 'open', arms: 'back', eyes: 'shut' });
  return K;
}

function crownFrame(f) {
  const p = new Pix(14, 9);
  p.ellipse(4 + f * 0.5, 6, 2.4, 3.2, PAL.orange, PAL.red);
  p.ellipse(10 - f * 0.5, 6, 2.4, 3.2, PAL.orange, PAL.red);
  p.ellipse(7, 4.5 + f * 0.5, 2.8, 4.4, PAL.orange, PAL.red);
  p.ellipse(7, 5.5, 1.4, 2.4, PAL.yellow);
  return p.c;
}

// ---------- Enemies ----------
function walkerFrame(step) {
  const p = new Pix(16, 16);
  const fo = step ? 1 : -1;
  p.ellipse(5 - fo, 14.3, 2.6, 1.6, PAL.gold, PAL.ink, PAL.brown);
  p.ellipse(8, 8.6, 6.6, 6.2, PAL.orange, PAL.ink, PAL.brown, PAL.tan);
  p.ellipse(10.2, 9.2, 4.2, 3.8, PAL.tan);
  p.rect(9, 7, 1, 3, PAL.ink); p.rect(12, 7, 1, 3, PAL.ink);
  p.px(8, 11, PAL.pinkD); p.px(13, 11, PAL.pinkD);
  p.ellipse(11 + fo, 14.3, 2.6, 1.6, PAL.gold, PAL.ink, PAL.brown);
  return p.c;
}

function flyerFrame(up) {
  const p = new Pix(16, 16);
  if (up) p.ellipse(5, 4.5, 3.4, 2.5, PAL.white, PAL.ink, PAL.skyL);
  else p.ellipse(4, 10, 3.4, 2.3, PAL.white, PAL.ink, PAL.skyL);
  p.ellipse(8.5, 9, 5.6, 5.2, PAL.purple, PAL.ink, PAL.purpleD, PAL.pinkL);
  p.rect(10, 7, 1, 3, PAL.ink); p.rect(12, 7, 1, 3, PAL.ink);
  p.px(9, 11, PAL.pink); p.px(13, 11, PAL.pink);
  p.rect(6, 14, 2, 1, PAL.orange); p.rect(10, 14, 2, 1, PAL.orange);
  if (up) p.ellipse(8, 3, 2.6, 2, PAL.white, PAL.ink);
  else p.ellipse(7.5, 11, 2.6, 1.8, PAL.white, PAL.ink);
  return p.c;
}

function shooterFrame(firing) {
  const p = new Pix(16, 16);
  const by = firing ? 2 : 0;
  p.rect(9, 1 + by, 5, 7, PAL.ink);
  p.rect(10, 2 + by, 3, 6, PAL.grayD);
  p.rect(10, 2 + by, 3, 1, firing ? PAL.yellow : PAL.ink);
  p.ellipse(8, 10.5 + by * 0.25, 7, 5.6 - by * 0.25, PAL.gray, PAL.ink, PAL.grayD, PAL.white);
  p.ellipse(8.5, 10, 1.7, 2.2, PAL.white, PAL.ink); p.ellipse(12.2, 10, 1.7, 2.2, PAL.white, PAL.ink);
  p.px(9, 10, PAL.ink); p.px(12, 10, PAL.ink);
  p.rect(3, 15, 3, 1, PAL.ink); p.rect(10, 15, 3, 1, PAL.ink);
  return p.c;
}

function spikyFrame(f) {
  const p = new Pix(18, 18), c = 9;
  for (let i = 0; i < 8; i++) {
    const a = (i * Math.PI) / 4 + (f * Math.PI) / 8;
    p.poly([
      [c + Math.cos(a) * 8.8, c + Math.sin(a) * 8.8],
      [c + Math.cos(a + 0.45) * 4.6, c + Math.sin(a + 0.45) * 4.6],
      [c + Math.cos(a - 0.45) * 4.6, c + Math.sin(a - 0.45) * 4.6],
    ], PAL.white, PAL.ink);
  }
  p.ellipse(c, c, 5.8, 5.8, PAL.navy, PAL.ink, null, PAL.blue);
  p.rect(6, 6, 2, 4, PAL.white); p.rect(10, 6, 2, 4, PAL.white);
  p.rect(7, 7, 1, 2, PAL.ink); p.rect(11, 7, 1, 2, PAL.ink);
  return p.c;
}

function hotheadFrame(f, flash) {
  const p = new Pix(16, 18);
  p.ellipse(8 + (f ? 0.7 : -0.7), 6, 4.6, 5.4, PAL.orange, PAL.redD);
  p.ellipse(8 + (f ? 2 : -2), 2, 1.6, 2.4, PAL.orange, PAL.redD);
  p.ellipse(8 + (f ? -0.5 : 0.5), 6, 2.2, 3.4, PAL.yellow);
  p.ellipse(8, 11.6, 6.4, 5.6, flash ? PAL.yellow : PAL.red, PAL.ink, flash ? PAL.orange : PAL.redD, PAL.orange);
  p.ellipse(9.6, 10.6, 1.5, 2, PAL.white, PAL.ink); p.ellipse(12.6, 10.6, 1.5, 2, PAL.white, PAL.ink);
  p.px(10, 11, PAL.ink); p.px(13, 11, PAL.ink);
  p.rect(10, 14, 3, 1, PAL.redD);
  p.rect(4, 17, 3, 1, PAL.ink); p.rect(10, 17, 3, 1, PAL.ink);
  return p.c;
}

// ---------- Items & projectiles ----------
function starSprite(size, ro, ri, rot, fill, outline, shade) {
  const p = new Pix(size, size);
  p.poly(starPoints(size / 2, size / 2 + 0.4, ro, ri, rot), fill, outline, shade);
  return p.c;
}

function puffSprite(size, f) {
  const p = new Pix(size, size), c = size / 2, r = size * 0.28;
  const g = f ? 0.8 : 1;
  p.ellipse(c - r * 0.6, c + 0.5, r * g, r * 0.9 * g, PAL.white, PAL.gray, PAL.skyL);
  p.ellipse(c + r * 0.6, c + 0.5, r * g, r * 0.9 * g, PAL.white, PAL.gray, PAL.skyL);
  p.ellipse(c, c - r * 0.4, r * 1.05 * g, r * g, PAL.white, PAL.gray, PAL.skyL);
  return p.c;
}

function buildItems() {
  SPR.star = [0, 1, 2, 3].map((i) => starSprite(12, 5.8, 2.6, (i * Math.PI) / 10, PAL.yellow, PAL.gold, PAL.yellow));
  SPR.bigStar = [0, 1, 2, 3].map((i) => starSprite(18, 8.8, 3.9, (i * Math.PI) / 10, PAL.yellow, PAL.ink, PAL.gold));
  SPR.tinyStar = starSprite(7, 3.4, 1.5, 0, PAL.yellow, PAL.gold);
  SPR.abilityStar = [PAL.yellow, PAL.pink, PAL.skyL].map((c) => starSprite(14, 6.6, 2.9, 0, c, PAL.ink, PAL.white));
  SPR.puff = [puffSprite(10, 0), puffSprite(10, 1)];
  SPR.bossPuff = [puffSprite(16, 0), puffSprite(16, 1)];

  let p = new Pix(8, 8);
  p.ellipse(4, 4, 3.6, 3.6, PAL.grayD, PAL.ink, PAL.navy, PAL.gray);
  SPR.rock = p.c;

  p = new Pix(10, 11);
  p.ellipse(5, 6, 4.4, 4.4, PAL.red, PAL.ink, PAL.redD, PAL.white);
  p.rect(5, 0, 1, 3, PAL.brownD); p.rect(6, 1, 3, 1, PAL.green); p.px(7, 0, PAL.green);
  SPR.apple = p.c;

  p = new Pix(16, 16);
  p.rect(0, 0, 16, 16, PAL.ink); p.rect(1, 1, 14, 14, PAL.tan);
  p.rect(1, 1, 14, 1, PAL.white); p.rect(1, 1, 1, 14, PAL.white);
  p.rect(1, 14, 14, 1, PAL.gold); p.rect(14, 1, 1, 14, PAL.gold);
  p.poly(starPoints(8, 8.4, 5.4, 2.3, 0), PAL.yellow, PAL.gold);
  SPR.block = p.c;

  p = new Pix(32, 32);
  p.ellipse(16, 17, 15.4, 14.6, PAL.gray, PAL.ink, PAL.grayD, PAL.white);
  for (const [x, y] of [[8, 20], [21, 10], [24, 22], [12, 26], [18, 16], [7, 13]]) p.rect(x, y, 2, 1, PAL.grayD);
  for (const [x, y] of [[14, 6], [15, 7], [15, 8], [16, 9], [17, 9], [18, 10], [10, 19], [11, 20], [12, 20], [13, 21]]) p.px(x, y, PAL.ink);
  SPR.boulder = p.c;

  p = new Pix(14, 14);
  p.ellipse(3, 11, 2.1, 1.7, PAL.white, PAL.ink); p.ellipse(4.6, 12.2, 1.7, 1.6, PAL.white, PAL.ink);
  p.rect(4, 9, 3, 2, PAL.white);
  p.ellipse(8.5, 6, 5, 4.6, PAL.brown, PAL.ink, PAL.brownD, PAL.tan);
  SPR.drumstick = p.c;

  p = new Pix(14, 14);
  p.ellipse(7, 8, 6.4, 5.6, PAL.red, PAL.ink, PAL.redD, PAL.white);
  p.ellipse(7, 2.8, 3.4, 1.6, PAL.green, PAL.ink, PAL.greenD);
  for (const [x, y] of [[5, 7], [5, 8], [5, 9], [6, 8], [7, 9], [8, 8], [9, 7], [9, 8], [9, 9]]) p.px(x, y, PAL.white);
  SPR.tomato = p.c;

  p = new Pix(28, 24);
  p.poly(starPoints(14, 12.6, 11.5, 5, -0.15), PAL.yellow, PAL.ink, PAL.gold);
  p.rect(9, 9, 2, 2, PAL.white); p.px(11, 8, PAL.white);
  SPR.warpStar = p.c;

  p = new Pix(12, 9);
  p.poly([[0, 0], [12, 4.5], [0, 9]], PAL.pink, PAL.ink, PAL.pinkD);
  SPR.flagOn = p.c;
  p = new Pix(12, 9);
  p.poly([[0, 0], [12, 4.5], [0, 9]], PAL.gray, PAL.ink, PAL.grayD);
  SPR.flagOff = p.c;

  p = new Pix(20, 34);
  p.ellipse(10, 11, 10, 10.5, PAL.grayD, PAL.ink, null, PAL.gray);
  p.rect(0, 11, 20, 23, PAL.ink); p.rect(1, 11, 18, 23, PAL.grayD);
  p.ellipse(10, 12.5, 6.5, 7, PAL.ink);
  p.rect(4, 12, 12, 22, PAL.ink);
  for (let y = 10; y < 34; y += 2) for (let x = 5 + (y % 4 ? 1 : 0); x < 15; x += 2) p.px(x, y, PAL.navy);
  SPR.door = p.c;

  // HUD bits
  p = new Pix(6, 9); p.ellipse(3, 4.5, 2.9, 4.4, PAL.pink, PAL.ink, PAL.pinkD, PAL.white); SPR.pip = p.c;
  p = new Pix(6, 9); p.ellipse(3, 4.5, 2.9, 4.4, PAL.white, PAL.ink, PAL.pinkL); SPR.pipLow = p.c;
  p = new Pix(6, 9); p.ellipse(3, 4.5, 2.9, 4.4, PAL.navy, PAL.grayD); SPR.pipEmpty = p.c;
  p = new Pix(10, 10);
  p.ellipse(5, 5, 4.6, 4.4, PAL.pink, PAL.ink, PAL.pinkD);
  p.rect(4, 3, 1, 2, PAL.ink); p.rect(6, 3, 1, 2, PAL.ink); p.px(2, 6, PAL.red); p.px(8, 6, PAL.red);
  SPR.face = p.c;
  p = new Pix(10, 10);
  p.ellipse(5, 5.5, 3.8, 4.2, PAL.orange, PAL.red); p.ellipse(5, 6.5, 1.8, 2.4, PAL.yellow); p.ellipse(6.5, 2, 1, 1.6, PAL.orange);
  SPR.fireIcon = p.c;
  SPR.normalIcon = starSprite(10, 4.8, 2.1, 0, PAL.white, PAL.grayD);
}

// ---------- Boss (Whispy-style tree) ----------
function buildBoss() {
  // trunk: 64x140, drawn at world (3144, 24); the face lives on the left part of the trunk
  let p = new Pix(64, 140);
  p.ellipse(6, 134, 9, 6, PAL.brown, PAL.ink, PAL.brownD);
  p.ellipse(58, 134, 9, 6, PAL.brown, PAL.ink, PAL.brownD);
  p.rect(8, 0, 48, 140, PAL.ink);
  p.rect(9, 0, 46, 140, PAL.brown);
  p.rect(47, 0, 8, 140, PAL.brownD);
  for (let i = 0; i < 8; i++) {
    const bx = 13 + i * 5;
    for (let y = 0; y < 140; y++) {
      if ((y + i * 7) % 23 >= 16) continue;
      if (bx > 18 && bx < 46 && y > 46 && y < 106) continue; // keep the face area clean
      p.px(bx + Math.round(Math.sin((y + i * 13) * 0.12) * 1.2), y, PAL.brownD);
    }
  }
  p.ellipse(32, 76, 14, 32, PAL.brown); // smooth face plate
  SPR.tree = p.c;

  // canopy across the top of the arena
  p = new Pix(300, 64);
  for (let i = 0; i < 16; i++) {
    p.ellipse(10 + i * 19 + (i % 3) * 3, 26 + (i % 2) * 9 + (i % 3 === 0 ? 4 : 0), 17 + (i % 4) * 2, 14 + (i % 3) * 2,
      PAL.green, PAL.ink, PAL.greenD, PAL.greenL);
  }
  for (const [x, y] of [[40, 40], [120, 34], [200, 44], [260, 30]]) { p.ellipse(x, y, 3, 3, PAL.red, PAL.ink, PAL.redD); }
  SPR.canopy = p.c;

  // face parts
  const eye = (kind) => {
    const q = new Pix(10, 14);
    if (kind === 'open') { q.ellipse(5, 7, 4.2, 6, PAL.ink); q.rect(3, 3, 2, 2, PAL.white); }
    else if (kind === 'hurt') { for (let i = 0; i < 8; i++) { q.px(1 + i, 4 + Math.abs(i - 3.5) | 0, PAL.ink); q.px(1 + i, 5 + Math.abs(i - 3.5) | 0, PAL.ink); } }
    else if (kind === 'closed') { for (let i = 0; i < 8; i++) { q.px(1 + i, 9 - (Math.abs(i - 3.5) < 2 ? 1 : 0), PAL.ink); } }
    else if (kind === 'dead') { for (let i = 0; i < 7; i++) { q.px(1 + i, 3 + i, PAL.ink); q.px(7 - i, 3 + i, PAL.ink); q.px(2 + i, 3 + i, PAL.ink); q.px(8 - i, 3 + i, PAL.ink); } }
    return q.c;
  };
  SPR.bossEye = { open: eye('open'), hurt: eye('hurt'), closed: eye('closed'), dead: eye('dead') };
  let q = new Pix(14, 6); q.ellipse(7, 3, 6, 2.2, PAL.ink); SPR.bossMouth = { closed: q.c };
  q = new Pix(14, 16); q.ellipse(7, 8, 5.5, 7.4, PAL.ink); q.ellipse(7, 10, 3.2, 3.6, PAL.redD); SPR.bossMouth.open = q.c;
  q = new Pix(14, 10); q.ellipse(7, 5, 3.6, 4, PAL.ink); SPR.bossMouth.o = q.c;
  q = new Pix(12, 5); for (let i = 0; i < 11; i++) { q.px(i, (i * 0.35) | 0, PAL.ink); q.px(i, ((i * 0.35) | 0) + 1, PAL.ink); } SPR.bossBrow = q.c;
}

function buildSprites() {
  SPR.kirby = buildKirby();
  SPR.crown = [crownFrame(0), crownFrame(1)];
  SPR.walker = [walkerFrame(0), walkerFrame(1)];
  SPR.flyer = [flyerFrame(true), flyerFrame(false)];
  SPR.shooter = [shooterFrame(false), shooterFrame(true)];
  SPR.spiky = [spikyFrame(0), spikyFrame(1)];
  SPR.hothead = [hotheadFrame(0, false), hotheadFrame(1, false), hotheadFrame(0, true)];
  buildItems();
  buildBoss();
}
Write C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\3. just skills\js\level.js
259 lines
'use strict';
// Level layout, tile rendering, tile collision and the parallax background.

const T = { EMPTY: 0, GROUND: 1, PLAT: 2, STONE: 3, STAR: 4, HIDDEN: 5 };
const LW = 200, LH = 12;
const DUSK_X = 148;                       // fire grove starts here (tile x)
const FLAG_TX = 96;                       // midpoint checkpoint flag
const DOOR = { x: 182 * TILE, y: 8 * TILE, w: 16, h: 32 };
const ARENA = { camX: 184 * TILE, left: 185 * TILE, right: 197 * TILE };
const CAM_MAX = 185 * TILE - VIEW_W;      // the camera never peeks into the arena before the door
const isSolidT = (t) => t === T.GROUND || t === T.STONE || t === T.STAR || t === T.HIDDEN;

function buildLevelData() {
  const tiles = new Uint8Array(LW * LH);
  const set = (x, y, t) => { if (x >= 0 && x < LW && y >= 0 && y < LH) tiles[y * LW + x] = t; };
  const fill = (x0, x1, y0, y1, t) => { for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) set(x, y, t); };
  const ground = (x0, x1, top) => fill(x0, x1, top, LH - 1, T.GROUND);
  const plat = (x0, x1, y) => fill(x0, x1, y, y, T.PLAT);
  const spawns = [], signs = [], blockItems = {};
  const S = (kind, tx, ty, opts = {}) => spawns.push({ kind, tx, ty, opts });
  const sign = (tx, ty, text) => signs.push({ x: tx * TILE, y: ty * TILE, text });
  const star = (tx, ty, item) => { set(tx, ty, T.STAR); if (item) blockItems[tx + ',' + ty] = item; };

  // ---- 1. Grassland: walkers and star blocks teach inhale & spit ----
  ground(0, 21, 10); ground(22, 25, 8); ground(26, 33, 10); ground(36, 49, 10);
  plat(8, 10, 7); S('food', 9, 6);
  star(18, 9); star(18, 8, 'bonus');
  plat(28, 32, 7); star(29, 6); star(30, 6, 'food'); star(31, 6);
  S('walker', 12, 9); S('walker', 29, 9); S('walker', 40, 9); S('walker', 46, 9);
  S('flyer', 44, 5);
  sign(2, 2, 'HOLD ENTER TO INHALE!');
  sign(2, 3, 'TAP ENTER AGAIN TO SPIT');

  // ---- 2. Cliffs & gaps: flyers, pits and a low ceiling test flight ----
  ground(55, 60, 9);
  fill(62, 72, 0, 3, T.STONE);
  plat(63, 65, 7);
  ground(68, 78, 10);
  plat(81, 83, 8);
  ground(86, 104, 10);
  S('flyer', 52, 5); S('flyer', 58, 3); S('flyer', 65, 5); S('flyer', 71, 6); S('flyer', 82, 5); S('flyer', 89, 6);
  S('walker', 57, 8); S('walker', 74, 9); S('walker', 92, 9);
  S('food', 70, 9);
  sign(46, 2, 'TAP SPACE IN THE AIR TO FLY!');
  sign(46, 3, 'ENTER WHILE FLYING: AIR PUFF');

  // ---- 3. Hill: shooters, spikes and the boulder ----
  ground(105, 110, 8); ground(111, 118, 6); ground(119, 124, 8); ground(125, 131, 10);
  ground(136, 155, 10);
  fill(140, 147, 0, 7, T.STONE);
  fill(140, 141, 8, 9, T.HIDDEN); S('boulder', 140, 8);
  S('shooter', 108, 7); S('shooter', 116, 5); S('shooter', 128, 9);
  S('walker', 113, 5);
  S('spiky', 121, 7, { axis: 'x', range: 26, speed: 0.025 });
  S('spiky', 133.5, 6, { axis: 'y', range: 30, speed: 0.035 });
  S('walker', 144, 9); S('walker', 146, 9);
  sign(118, 2, 'SPIKY FOES CAN NOT BE INHALED');
  sign(133, 3, 'INHALE THE BOULDER!');

  // ---- 4. Fire grove: fire creatures grant Fire ----
  ground(156, 159, 8); ground(160, 163, 10);
  ground(167, 199, 10);
  S('hothead', 151, 9); S('hothead', 162, 9); S('hothead', 170, 9); S('hothead', 176, 9);
  S('walker', 158, 7); S('flyer', 168, 5);
  star(173, 9); star(173, 8);
  plat(177, 179, 7); S('tomato', 178, 6);
  fill(183, 184, 0, 9, T.STONE);
  sign(149, 2, 'SWALLOW A FIRE FOE (DOWN)');
  sign(149, 3, 'TO GAIN THE FIRE ABILITY!');

  // ---- Boss arena (camera locks here) ----
  fill(197, 199, 0, 9, T.HIDDEN);   // tree trunk
  fill(185, 196, 0, 1, T.HIDDEN);   // leaf canopy ceiling

  return { tiles, spawns, signs, blockItems };
}

function hash2(x, y) {
  let h = (x * 374761393 + y * 668265263) | 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
}

const TILE_THEME = {
  day: { grass: PAL.green, grassL: PAL.greenL, grassD: PAL.greenD, dirt: PAL.brown, dirtD: PAL.brownD, dirtL: PAL.orange },
  dusk: { grass: PAL.orange, grassL: PAL.yellow, grassD: PAL.red, dirt: PAL.brownD, dirtD: PAL.ink, dirtL: PAL.brown },
};

class Level {
  constructor() {
    const d = buildLevelData();
    this.tiles = d.tiles; this.spawns = d.spawns; this.signs = d.signs; this.blockItems = d.blockItems;
    this.canvas = makeCanvas(LW * TILE, LH * TILE);
    this.g = this.canvas.getContext('2d');
    for (let y = 0; y < LH; y++) for (let x = 0; x < LW; x++) this.drawTile(x, y);
  }
  raw(tx, ty) { return tx < 0 || tx >= LW || ty < 0 || ty >= LH ? T.EMPTY : this.tiles[ty * LW + tx]; }
  // Outside the map: walls left/right/top, open below (pits).
  get(tx, ty) {
    if (tx < 0 || tx >= LW || ty < 0) return T.STONE;
    if (ty >= LH) return T.EMPTY;
    return this.tiles[ty * LW + tx];
  }
  solidAt(px, py) { return isSolidT(this.get(Math.floor(px / TILE), Math.floor(py / TILE))); }
  standAt(px, py) { const t = this.get(Math.floor(px / TILE), Math.floor(py / TILE)); return isSolidT(t) || t === T.PLAT; }
  set(tx, ty, t) {
    if (tx < 0 || tx >= LW || ty < 0 || ty >= LH) return;
    this.tiles[ty * LW + tx] = t;
    for (let y = ty - 1; y <= ty + 1; y++) for (let x = tx - 1; x <= tx + 1; x++) this.drawTile(x, y);
  }
  drawTile(tx, ty) {
    if (tx < 0 || tx >= LW || ty < 0 || ty >= LH) return;
    const g = this.g, px = tx * TILE, py = ty * TILE, t = this.raw(tx, ty);
    const th = tx >= DUSK_X ? TILE_THEME.dusk : TILE_THEME.day;
    const fr = (x, y, w, h, c) => { g.fillStyle = c; g.fillRect(px + x, py + y, w, h); };
    g.clearRect(px, py, TILE, TILE);
    if (t === T.GROUND) {
      fr(0, 0, 16, 16, th.dirt);
      for (let i = 0; i < 5; i++) {
        fr(Math.floor(hash2(tx * 7 + i, ty) * 14), Math.floor(hash2(tx, ty * 5 + i) * 15), 2, 1, th.dirtD);
      }
      fr(Math.floor(hash2(tx, ty + 99) * 14), Math.floor(hash2(tx + 99, ty) * 14), 1, 1, th.dirtL);
      const leftOpen = !isSolidT(this.raw(tx - 1, ty)) && tx > 0;
      const rightOpen = !isSolidT(this.raw(tx + 1, ty)) && tx < LW - 1;
      if (leftOpen) fr(0, 0, 1, 16, th.dirtD);
      if (rightOpen) fr(15, 0, 1, 16, th.dirtD);
      if (!isSolidT(this.raw(tx, ty - 1))) {
        g.clearRect(px, py, 16, 2);
        for (let x = 0; x < 16; x++) {
          const h = hash2(tx * 16 + x, ty);
          if (h > 0.55) fr(x, 0, 1, 2, h > 0.8 ? th.grassL : th.grass);
          else if (h > 0.2) fr(x, 1, 1, 1, th.grass);
          const drip = 5 + (hash2(tx * 16 + x, ty + 7) > 0.6 ? 1 : 0) + (x % 5 === 2 ? 1 : 0);
          fr(x, 2, 1, drip - 2, th.grass);
          fr(x, drip, 1, 1, th.grassD);
        }
        fr(0, 2, 16, 1, th.grassL);
        if (leftOpen) { fr(0, 2, 1, 5, th.grassD); }
        if (rightOpen) { fr(15, 2, 1, 5, th.grassD); }
      }
    } else if (t === T.STONE) {
      fr(0, 0, 16, 16, PAL.gray);
      fr(0, 0, 16, 1, PAL.white);
      fr(0, 7, 16, 1, PAL.grayD); fr(0, 15, 16, 1, PAL.grayD);
      const o = ty % 2 ? 4 : 12;
      fr(o, 0, 1, 7, PAL.grayD); fr((o + 8) % 16, 8, 1, 7, PAL.grayD);
      fr(o + 1, 1, 1, 1, PAL.white); fr(((o + 8) % 16) + 1, 9, 1, 1, PAL.white);
      if (!isSolidT(this.raw(tx, ty + 1)) && ty < LH - 1) fr(0, 15, 16, 1, PAL.ink);
      if (!isSolidT(this.raw(tx - 1, ty))) fr(0, 0, 1, 16, PAL.ink);
      if (!isSolidT(this.raw(tx + 1, ty))) fr(15, 0, 1, 16, PAL.ink);
    } else if (t === T.PLAT) {
      fr(0, 0, 16, 6, PAL.brown);
      fr(0, 0, 16, 1, PAL.tan);
      fr(0, 5, 16, 1, PAL.brownD);
      fr(7, 1, 1, 4, PAL.brownD);
      fr(3, 2, 1, 1, PAL.brownD); fr(12, 3, 1, 1, PAL.brownD);
      if (this.raw(tx - 1, ty) !== T.PLAT) { fr(0, 0, 1, 6, PAL.ink); }
      if (this.raw(tx + 1, ty) !== T.PLAT) { fr(15, 0, 1, 6, PAL.ink); }
      fr(2, 6, 2, 3, PAL.brownD); fr(12, 6, 2, 3, PAL.brownD);
    } else if (t === T.STAR) {
      g.drawImage(SPR.block, px, py);
    }
  }
}

// ---------- Tile collision (axis separated) ----------
function moveX(e, lv) {
  if (!e.vx) return false;
  e.x += e.vx;
  const y0 = Math.floor(e.y / TILE), y1 = Math.floor((e.y + e.h - 0.001) / TILE);
  if (e.vx > 0) {
    const tx = Math.floor((e.x + e.w - 0.001) / TILE);
    for (let ty = y0; ty <= y1; ty++) if (isSolidT(lv.get(tx, ty))) { e.x = tx * TILE - e.w; e.vx = 0; return true; }
  } else {
    const tx = Math.floor(e.x / TILE);
    for (let ty = y0; ty <= y1; ty++) if (isSolidT(lv.get(tx, ty))) { e.x = (tx + 1) * TILE; e.vx = 0; return true; }
  }
  return false;
}

function moveY(e, lv) {
  const prevBottom = e.y + e.h;
  e.y += e.vy;
  e.onGround = false;
  const x0 = Math.floor(e.x / TILE), x1 = Math.floor((e.x + e.w - 0.001) / TILE);
  if (e.vy > 0) {
    const ty = Math.floor((e.y + e.h - 0.001) / TILE);
    for (let tx = x0; tx <= x1; tx++) {
      const t = lv.get(tx, ty);
      if (isSolidT(t) || (t === T.PLAT && prevBottom <= ty * TILE + 0.5)) {
        e.y = ty * TILE - e.h; e.vy = 0; e.onGround = true; return 1;
      }
    }
  } else if (e.vy < 0) {
    const ty = Math.floor(e.y / TILE);
    for (let tx = x0; tx <= x1; tx++) if (isSolidT(lv.get(tx, ty))) { e.y = (ty + 1) * TILE; e.vy = 0; return -1; }
  }
  return 0;
}

function groundAhead(e, lv) {
  return lv.standAt(e.facing > 0 ? e.x + e.w + 1 : e.x - 1, e.y + e.h + 2);
}

// ---------- Parallax background (day fades to dusk in the fire grove) ----------
const BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]];
const BG = {
  build() {
    this.day = this.make({ top: PAL.sky, bot: PAL.skyL, far: PAL.teal, farEdge: PAL.greenD, near: PAL.greenD, nearEdge: PAL.ink, nearSpot: PAL.green, cloud: PAL.white, cloudEdge: PAL.skyL });
    this.dusk = this.make({ top: PAL.purpleD, bot: PAL.dusk, far: PAL.purple, farEdge: PAL.purpleD, near: PAL.redD, nearEdge: PAL.ink, nearSpot: PAL.red, cloud: PAL.pinkL, cloudEdge: PAL.pink });
  },
  make(c) {
    const sky = new Pix(VIEW_W, VIEW_H);
    for (let y = 0; y < VIEW_H; y++) {
      const k = clamp((y - 40) / 90, 0, 1);
      for (let x = 0; x < VIEW_W; x++) sky.px(x, y, k * 16 > BAYER[y & 3][x & 3] ? c.bot : c.top);
    }
    const far = new Pix(512, VIEW_H);
    for (let x = 0; x < 512; x++) {
      const a = (x / 512) * Math.PI * 2;
      const h = 74 + 16 * Math.sin(a * 2 + 0.5) + 9 * Math.sin(a * 5 + 1.3) + 4 * Math.sin(a * 11);
      const top = Math.round(VIEW_H - h);
      far.rect(x, top, 1, VIEW_H - top, c.far);
      far.rect(x, top, 1, 1, c.farEdge);
    }
    const near = new Pix(512, VIEW_H);
    for (const [cx, cy, rx, ry] of [[60, 186, 58, 52], [200, 192, 72, 60], [330, 186, 50, 44], [455, 190, 66, 58]]) {
      for (const off of [-512, 0, 512]) near.ellipse(cx + off, cy, rx, ry, c.near, c.nearEdge, c.nearSpot);
    }
    const clouds = new Pix(512, 90);
    for (const [x, y] of [[40, 30], [180, 56], [300, 22], [420, 48]]) {
      clouds.ellipse(x, y, 14, 8, c.cloud, c.cloudEdge, c.cloudEdge);
      clouds.ellipse(x + 13, y - 4, 12, 9, c.cloud, c.cloudEdge, c.cloudEdge);
      clouds.ellipse(x + 26, y, 13, 7, c.cloud, c.cloudEdge, c.cloudEdge);
    }
    return { sky: sky.c, far: far.c, near: near.c, clouds: clouds.c };
  },
  layer(ctx, img, off, y) {
    const w = img.width;
    let x = -(((Math.round(off) % w) + w) % w);
    for (; x < VIEW_W; x += w) ctx.drawImage(img, x, y);
  },
  drawSet(ctx, s, camX, t) {
    ctx.drawImage(s.sky, 0, 0);
    this.layer(ctx, s.clouds, camX * 0.1 + t * 0.08, 6);
    this.layer(ctx, s.far, camX * 0.25, 0);
    this.layer(ctx, s.near, camX * 0.5, 0);
  },
  draw(ctx, camX, t) {
    const k = clamp((camX + VIEW_W / 2 - (DUSK_X * TILE - 160)) / 320, 0, 1);
    if (k < 1) this.drawSet(ctx, this.day, camX, t);
    if (k > 0) {
      ctx.globalAlpha = k;
      this.drawSet(ctx, this.dusk, camX, t);
      ctx.globalAlpha = 1;
    }
  },
};
Write C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\3. just skills\js\entities.js
550 lines
'use strict';
// Enemies, projectiles, pickups, the boss, and particle helpers.

// ---------- Particles & effects ----------
function addPart(p) {
  G.parts.push(Object.assign({ vx: 0, vy: 0, g: 0, drag: 1, t: 0, size: 1, col: PAL.white, type: 'dot', life: 20 }, p));
}
function burst(x, y, n, cols, sp = 2, o = {}) {
  for (let i = 0; i < n; i++) {
    const a = Math.random() * Math.PI * 2, s = sp * (0.4 + Math.random() * 0.8);
    addPart({ x, y, vx: Math.cos(a) * s, vy: Math.sin(a) * s, life: o.life || (rand(14, 26) | 0), col: cols[i % cols.length],
      size: o.size || (Math.random() < 0.5 ? 1 : 2), drag: 0.9, g: o.g || 0, type: o.type || 'dot' });
  }
}
function starBurst(x, y, n = 6) {
  for (let i = 0; i < n; i++) {
    const a = (i * Math.PI * 2) / n + 0.3;
    addPart({ x: x - 3, y: y - 3, vx: Math.cos(a) * 2.2, vy: Math.sin(a) * 2.2, life: 18, type: 'star', drag: 0.92 });
  }
  addPart({ x: x - 5, y: y - 5, life: 14, type: 'cloud' });
}
function dust(x, y, n = 3) {
  for (let i = 0; i < n; i++) addPart({ x: x + rand(-4, 4), y: y - 2, vx: rand(-0.6, 0.6), vy: rand(-0.6, -0.1), life: rand(10, 18) | 0, col: PAL.white, size: 2, drag: 0.92 });
}
function defeat(e, pts) {
  if (e.dead) return;
  e.dead = true;
  starBurst(e.cx, e.cy);
  Sound.pop();
  if (pts) G.addScore(pts, e.cx, e.y - 4);
}
// A star block was destroyed (by a projectile or fire) at tile tx,ty.
function breakBlock(tx, ty) {
  G.level.set(tx, ty, T.EMPTY);
  burst(tx * TILE + 8, ty * TILE + 8, 10, [PAL.tan, PAL.yellow, PAL.gold], 2.2, { g: 0.15 });
  Sound.crumble();
  G.addScore(50, tx * TILE + 8, ty * TILE);
  spawnBlockItem(tx, ty);
}
function spawnBlockItem(tx, ty) {
  const key = tx + ',' + ty, item = G.level.blockItems[key];
  if (!item) return;
  delete G.level.blockItems[key];
  if (item === 'food') {
    const f = new Food(tx * TILE + 2, ty * TILE + 2, 'food');
    f.vy = -2.5;
    G.ents.push(f);
  } else if (item === 'bonus') {
    G.addScore(1000, tx * TILE + 8, ty * TILE - 6);
    burst(tx * TILE + 8, ty * TILE + 8, 12, [PAL.yellow, PAL.white], 2.5);
    Sound.bonus();
  }
}
function clearHazards() {
  for (const e of G.ents) {
    if (!e.dead && ['apple', 'bosspuff', 'rollspiky', 'rock'].includes(e.kind)) { e.dead = true; starBurst(e.cx, e.cy, 4); }
  }
}

// ---------- Base entity ----------
class Ent {
  constructor(w, h) {
    this.x = 0; this.y = 0; this.w = w; this.h = h; this.vx = 0; this.vy = 0;
    this.t = 0; this.dead = false; this.facing = -1; this.onGround = false;
    this.caughtTimer = 0; this.pullT = 0;
    this.kind = 'ent';
    this.enemy = false;       // can be defeated by stars, puffs and fire
    this.inhalable = false;
    this.harmful = false;     // hurts Kirby on contact
    this.invincible = false;  // blocks stars, can't be hurt
    this.heavy = false;
    this.gives = null;        // copy ability granted when swallowed
  }
  get cx() { return this.x + this.w / 2; }
  get cy() { return this.y + this.h / 2; }
  at(x, y) { this.x = x; this.y = y; return this; }
  // stand the entity on the floor of tile cell (tx, ty)
  onCell(tx, ty) { this.x = tx * TILE + (TILE - this.w) / 2; this.y = (ty + 1) * TILE - this.h; return this; }
  fall(g = 0.22, max = 4) {
    this.vy = Math.min(this.vy + g, max);
    const hit = moveX(this, G.level);
    moveY(this, G.level);
    return hit;
  }
  patrol(speed) {
    this.vx = this.facing * speed;
    const hit = this.fall();
    if (hit || (this.onGround && !groundAhead(this, G.level))) this.facing = -this.facing;
  }
  jitter() { return this.caughtTimer > 0 ? ((this.t >> 1) & 1 ? 1 : -1) : 0; }
  drawFoot(ctx, img, foot, flip) { blit(ctx, img, Math.round(this.cx - img.width / 2) + this.jitter(), Math.round(this.y + this.h - foot), flip); }
  drawMid(ctx, img, flip) { blit(ctx, img, Math.round(this.cx - img.width / 2) + this.jitter(), Math.round(this.cy - img.height / 2), flip); }
  update() {}
  onRelease() {}
  draw() {}
}

// ---------- Enemies ----------
class Walker extends Ent {
  constructor() { super(12, 12); Object.assign(this, { kind: 'walker', enemy: true, inhalable: true, harmful: true }); }
  update() { this.t++; this.patrol(0.45); }
  draw(ctx) { this.drawFoot(ctx, SPR.walker[(this.t >> 3) & 1], 16, this.facing < 0); }
}

class Flyer extends Ent {
  constructor() {
    super(12, 10);
    Object.assign(this, { kind: 'flyer', enemy: true, inhalable: true, harmful: true });
    this.phase = Math.random() * 6; this.swoopT = 0; this.cool = 90; this.ready = false;
  }
  wave() { return Math.sin(this.t * 0.05 + this.phase) * 10; }
  update() {
    if (!this.ready) { this.baseX = this.x; this.baseY = this.y; this.ready = true; }
    this.t++;
    this.x += this.facing * 0.55;
    if (this.x < this.baseX - 48) this.facing = 1;
    if (this.x > this.baseX + 48) this.facing = -1;
    let off = this.wave();
    const k = G.kirby;
    if (this.swoopT > 0) {
      this.swoopT--;
      off += Math.sin((1 - this.swoopT / 70) * Math.PI) * this.swoopDepth;
    } else if (--this.cool <= 0 && k && !k.dead && Math.abs(k.cx - this.cx) < 72 && k.cy > this.cy + 10) {
      this.swoopT = 70; this.swoopDepth = Math.min(k.cy - this.cy, 64); this.cool = 160;
      this.facing = k.cx > this.cx ? 1 : -1;
    }
    this.y = this.baseY + off;
  }
  onRelease() { this.baseX = this.x; this.baseY = this.y - this.wave(); this.swoopT = 0; }
  draw(ctx) { this.drawMid(ctx, SPR.flyer[(this.t >> 2) & 1], this.facing < 0); }
}

class Shooter extends Ent {
  constructor() {
    super(14, 13);
    Object.assign(this, { kind: 'shooter', enemy: true, inhalable: true, harmful: true });
    this.cool = 60 + Math.random() * 60; this.tele = 0; this.recoil = 0;
  }
  update() {
    this.t++;
    this.fall();
    if (this.recoil > 0) this.recoil--;
    const k = G.kirby;
    if (!k || k.dead) return;
    const dx = k.cx - this.cx;
    this.facing = dx > 0 ? 1 : -1;
    if (this.tele > 0) {
      if (--this.tele === 0) {
        const Tt = 56, g = 0.13;
        const vx = clamp(dx / Tt, -2.4, 2.4);
        const vy = clamp((k.cy - this.y - 0.5 * g * Tt * Tt) / Tt, -5, -1.5);
        G.ents.push(new Rock(vx, vy).at(this.cx - 4 + this.facing * 3, this.y - 6));
        Sound.lob();
        this.recoil = 10;
      }
    } else if (--this.cool <= 0 && Math.abs(dx) < 170 && Math.abs(dx) > 18) {
      this.tele = 24; this.cool = 150;
    }
  }
  draw(ctx) {
    const shake = this.tele > 0 && (this.t >> 1) & 1 ? 1 : 0;
    blit(ctx, SPR.shooter[this.recoil > 0 ? 1 : 0], Math.round(this.cx - 8) + shake + this.jitter(), Math.round(this.y + this.h - 16), this.facing < 0);
  }
}

class Rock extends Ent {
  constructor(vx, vy) {
    super(8, 8);
    Object.assign(this, { kind: 'rock', enemy: true, inhalable: true, harmful: true, vx, vy });
    this.life = 300;
  }
  update() {
    this.t++;
    this.vy = Math.min(this.vy + 0.13, 4.5);
    this.x += this.vx; this.y += this.vy;
    if (G.level.solidAt(this.cx, this.cy) || --this.life <= 0) {
      this.dead = true;
      burst(this.cx, this.cy, 6, [PAL.grayD, PAL.gray], 1.5, { g: 0.15 });
    }
  }
  draw(ctx) { this.drawMid(ctx, SPR.rock); }
}

class Spiky extends Ent {
  constructor(o = {}) {
    super(14, 14);
    Object.assign(this, { kind: 'spiky', enemy: true, harmful: true, invincible: true });
    this.axis = o.axis || 'y'; this.range = o.range || 24; this.speed = o.speed || 0.03; this.ready = false;
  }
  update() {
    if (!this.ready) { this.bx = this.x; this.by = this.y; this.ready = true; }
    this.t++;
    const s = Math.sin(this.t * this.speed) * this.range;
    if (this.axis === 'y') this.y = this.by + s; else this.x = this.bx + s;
  }
  draw(ctx) { this.drawMid(ctx, SPR.spiky[(this.t >> 4) & 1]); }
}

// Dropped by the boss in its second phase: falls, bounces, rolls toward Kirby's side.
class RollingSpiky extends Ent {
  constructor() {
    super(14, 14);
    Object.assign(this, { kind: 'rollspiky', enemy: true, harmful: true, invincible: true });
    this.bounced = false; this.life = 420;
  }
  update() {
    this.t++;
    this.vy = Math.min(this.vy + 0.2, 4.5);
    const hit = moveX(this, G.level);
    moveY(this, G.level);
    if (this.onGround && !this.bounced) { this.bounced = true; this.vy = -2.4; this.vx = -1.1; Sound.thud(); }
    if (hit || this.x < ARENA.left + 2 || --this.life <= 0) { this.dead = true; starBurst(this.cx, this.cy, 4); }
  }
  draw(ctx) { this.drawMid(ctx, SPR.spiky[(this.t >> 2) & 1]); }
}

class HotHead extends Ent {
  constructor() {
    super(12, 13);
    Object.assign(this, { kind: 'hothead', enemy: true, inhalable: true, harmful: true, gives: 'fire' });
    this.mode = 'walk'; this.modeT = 100 + Math.random() * 80;
  }
  flameBox() {
    return { x: this.facing > 0 ? this.x + this.w : this.x - 28, y: this.y + 2, w: 28, h: 9 };
  }
  update() {
    this.t++;
    const k = G.kirby;
    if (this.mode === 'walk') {
      this.patrol(0.3);
      if (--this.modeT <= 0) {
        if (k && !k.dead && Math.abs(k.cx - this.cx) < 130) {
          this.mode = 'charge'; this.modeT = 30;
          this.facing = k.cx > this.cx ? 1 : -1;
        } else this.modeT = 40;
      }
    } else if (this.mode === 'charge') {
      this.vx = 0; this.fall();
      if (--this.modeT <= 0) { this.mode = 'breathe'; this.modeT = 50; Sound.fireBurst(); }
    } else {
      this.vx = 0; this.fall();
      for (let i = 0; i < 2; i++) {
        addPart({ type: 'flame', x: this.cx + this.facing * 6, y: this.cy - 1 + rand(-2, 2), vx: this.facing * rand(1.8, 2.6), vy: rand(-0.3, 0.3), life: 12, size: 4 });
      }
      if (k && overlap(this.flameBox(), k)) k.damage(this.cx);
      if (--this.modeT <= 0) { this.mode = 'walk'; this.modeT = 140 + Math.random() * 60; }
    }
  }
  onRelease() { this.mode = 'walk'; this.modeT = 90; }
  draw(ctx) {
    let f = (this.t >> 3) & 1;
    if (this.mode === 'charge' && (this.t >> 2) & 1) f = 2;
    this.drawFoot(ctx, SPR.hothead[f], 18, this.facing < 0);
  }
}

// ---------- Boss projectiles ----------
class Apple extends Ent {
  constructor() { super(10, 10); Object.assign(this, { kind: 'apple', inhalable: true, harmful: true }); this.bounced = false; this.life = 480; }
  update() {
    this.t++;
    this.vy = Math.min(this.vy + 0.18, 4.5);
    const vx = this.vx;
    if (moveX(this, G.level)) this.vx = -vx * 0.6;
    moveY(this, G.level);
    if (this.onGround) {
      if (!this.bounced) { this.bounced = true; this.vy = -1.8; this.vx = -0.6; Sound.thud(); }
      else this.vx = approach(this.vx, 0, 0.004);
    }
    this.harmful = !this.bounced;
    if (--this.life <= 0) { this.dead = true; starBurst(this.cx, this.cy, 4); }
  }
  draw(ctx) {
    if (this.life < 90 && (this.t >> 2) & 1) return;
    this.drawFoot(ctx, SPR.apple, 11);
  }
}

class BossPuff extends Ent {
  constructor(targetY, speed) { super(14, 14); Object.assign(this, { kind: 'bosspuff', harmful: true }); this.vx = -speed; this.ty = targetY; }
  update() {
    this.t++;
    this.x += this.vx;
    this.y += (this.ty - 7 - this.y) * 0.06;
    if (this.t % 4 === 0) addPart({ x: this.x + this.w, y: this.cy + rand(-4, 4), vx: 0.5, life: 10, col: PAL.white, size: 1 });
    if (this.x < ARENA.left - 4) { this.dead = true; addPart({ x: this.x, y: this.y, life: 12, type: 'cloud' }); }
  }
  draw(ctx) { this.drawMid(ctx, SPR.bossPuff[(this.t >> 3) & 1]); }
}

// ---------- Kirby's projectiles ----------
class StarShot extends Ent {
  constructor(dir, big) {
    super(big ? 16 : 10, big ? 16 : 10);
    this.kind = 'shot'; this.vx = dir * (big ? 4 : 4.6); this.big = big;
    this.life = big ? 80 : 60; this.combo = 0;
  }
  update() {
    this.t++;
    this.x += this.vx;
    if (this.t % 2 === 0) addPart({ x: this.cx - this.vx * 2 + rand(-2, 2), y: this.cy + rand(-3, 3), life: 14, col: this.t % 4 ? PAL.yellow : PAL.white });
    const b = G.boss;
    if (b && b.vulnerable && overlap(this, b.hitbox)) { b.hit(1); this.pop(); return; }
    for (const e of G.ents) {
      if (e === this || e.dead || !e.enemy || e.caughtTimer > 0 || !overlap(this, e)) continue;
      if (e.invincible) { Sound.clink(); burst(this.cx, this.cy, 8, [PAL.white, PAL.yellow], 2.5); this.pop(); return; }
      this.combo++;
      defeat(e, 200 * this.combo);
      if (!this.big) { this.pop(); return; }
    }
    const lv = G.level;
    const lead = Math.floor((this.vx > 0 ? this.x + this.w - 2 : this.x + 2) / TILE);
    for (let ty = Math.floor((this.y + 3) / TILE); ty <= Math.floor((this.y + this.h - 3) / TILE); ty++) {
      const t = lv.get(lead, ty);
      if (t === T.STAR) { breakBlock(lead, ty); if (!this.big) { this.pop(); return; } }
      else if (isSolidT(t)) { this.pop(); return; }
    }
    if (--this.life <= 0) this.pop();
  }
  pop() { this.dead = true; starBurst(this.cx, this.cy, 4); }
  draw(ctx) { this.drawMid(ctx, (this.big ? SPR.bigStar : SPR.star)[(this.t >> 2) % 4]); }
}

class AirPuff extends Ent {
  constructor(dir) { super(10, 10); this.kind = 'airpuff'; this.vx = dir * 3.4; this.life = 22; }
  update() {
    this.t++;
    this.x += this.vx; this.vx *= 0.93;
    for (const e of G.ents) {
      if (e.dead || !e.enemy || e.invincible || e.caughtTimer > 0 || !overlap(this, e)) continue;
      defeat(e, 200); this.dead = true; return;
    }
    const tx = Math.floor(this.cx / TILE), ty = Math.floor(this.cy / TILE), t = G.level.get(tx, ty);
    if (t === T.STAR) { breakBlock(tx, ty); this.dead = true; return; }
    if (isSolidT(t) || --this.life <= 0) { this.dead = true; addPart({ x: this.x, y: this.y, life: 10, type: 'cloud' }); }
  }
  draw(ctx) { this.drawMid(ctx, SPR.puff[this.t < 12 ? 0 : 1]); }
}

class AbilityStar extends Ent {
  constructor(dir) {
    super(12, 12);
    Object.assign(this, { kind: 'abilitystar', inhalable: true, gives: 'fire' });
    this.vx = dir * 1.4; this.vy = -3; this.life = 480;
  }
  update() {
    this.t++;
    this.vy = Math.min(this.vy + 0.14, 3);
    const vx = this.vx;
    if (moveX(this, G.level)) this.vx = -vx;
    moveY(this, G.level);
    if (this.onGround) this.vy = -2.8;
    if (this.t % 6 === 0) addPart({ x: this.cx + rand(-6, 6), y: this.cy + rand(-6, 6), life: 12, col: pick([PAL.yellow, PAL.white, PAL.pink]) });
    if (--this.life <= 0 || this.y > LH * TILE + 20) { this.dead = true; starBurst(this.cx, this.cy, 4); }
  }
  draw(ctx) {
    if (this.life < 120 && (this.t >> 2) & 1) return;
    this.drawMid(ctx, SPR.abilityStar[(this.t >> 3) % 3]);
  }
}

// A star block pulled out of the ground by inhaling.
class BlockChunk extends Ent {
  constructor() { super(14, 14); Object.assign(this, { kind: 'block', inhalable: true }); this.life = 600; }
  update() { this.t++; this.fall(); if (--this.life <= 0) { this.dead = true; starBurst(this.cx, this.cy, 4); } }
  draw(ctx) { blit(ctx, SPR.block, Math.round(this.x - 1) + this.jitter(), Math.round(this.y - 1)); }
}

class Boulder extends Ent {
  constructor(tx, ty) {
    super(32, 32);
    Object.assign(this, { kind: 'boulder', inhalable: true, heavy: true });
    this.tx = tx; this.ty = ty; this.x = tx * TILE; this.y = ty * TILE;
    this.anchored = true; this.strain = 0; this.strained = false;
  }
  pullOn() {
    this.strained = true;
    this.strain++;
    if (this.strain % 12 === 1) Sound.rumble();
    if (this.strain % 4 === 0) dust(this.x + (G.kirby.cx < this.cx ? 0 : 32), this.y + 32, 1);
    if (this.strain >= 70) this.rip();
  }
  rip() {
    this.anchored = false;
    for (let dy = 0; dy < 2; dy++) for (let dx = 0; dx < 2; dx++) G.level.set(this.tx + dx, this.ty + dy, T.EMPTY);
    G.shake = 12;
    Sound.rip();
    burst(this.cx, this.y + 30, 14, [PAL.gray, PAL.grayD, PAL.white], 2.5, { g: 0.12 });
  }
  update() {
    this.t++;
    if (this.anchored) {
      if (!this.strained) this.strain = Math.max(0, this.strain - 2);
      this.strained = false;
    } else this.fall(0.25, 5);
  }
  draw(ctx) {
    let ox = 0;
    if (this.anchored && this.strain > 0) {
      const dir = G.kirby && G.kirby.cx < this.cx ? -1 : 1;
      ox = Math.round(dir * Math.min(this.strain * 0.06, 4)) + (this.strain > 15 ? ((this.t >> 1) & 1 ? 1 : -1) : 0);
    }
    blit(ctx, SPR.boulder, Math.round(this.x) + ox + this.jitter(), Math.round(this.y));
  }
}

// ---------- Pickups ----------
class Food extends Ent {
  constructor(x, y, type) { super(12, 12); this.x = x; this.y = y; this.kind = type; }
  update() { this.t++; this.fall(0.2, 3); }
  collect(k) {
    this.dead = true;
    if (this.kind === 'tomato') { k.hp = k.maxHp; G.addScore(500, this.cx, this.y); G.showBanner('FULL HEALTH!'); }
    else { k.hp = Math.min(k.maxHp, k.hp + 2); G.addScore(100, this.cx, this.y); }
    Sound.heal();
    burst(this.cx, this.cy, 10, [PAL.pink, PAL.white, PAL.yellow], 2);
  }
  draw(ctx) {
    const img = this.kind === 'tomato' ? SPR.tomato : SPR.drumstick;
    blit(ctx, img, Math.round(this.cx - img.width / 2), Math.round(this.y + this.h - img.height + (Math.sin(this.t * 0.1) > 0 ? -1 : 0)));
  }
}

class WarpStar extends Ent {
  constructor(x, y) { super(26, 20); this.kind = 'warp'; this.x = x - 13; this.baseY = y - 10; this.y = -30; this.arrived = false; }
  update() {
    this.t++;
    if (!this.arrived) { this.y += 2; if (this.y >= this.baseY) { this.y = this.baseY; this.arrived = true; } }
    else this.y = this.baseY + Math.sin(this.t * 0.08) * 3;
    if (this.t % 3 === 0) addPart({ x: this.cx + rand(-14, 14), y: this.cy + rand(-10, 10), life: 16, col: pick([PAL.yellow, PAL.white, PAL.pink]), vy: 0.3 });
  }
  draw(ctx) { blit(ctx, SPR.warpStar, Math.round(this.cx - 14), Math.round(this.cy - 12)); }
}

// ---------- Boss: Whispy Woods ----------
class Boss {
  constructor() {
    this.x = ARENA.right; this.w = 48;
    this.hp = 6; this.maxHp = 6;
    this.state = 'sleep'; this.t = 0; this.st = 0;
    this.flash = 0; this.shakeT = 0; this.fireAcc = 0; this.bar = 0;
    this.spawned = 0; this.lastAtk = 'blow';
  }
  get hitbox() { return { x: this.x, y: 56, w: 48, h: 104 }; }
  get vulnerable() { return this.state === 'idle' || this.state === 'apples' || this.state === 'blow'; }
  get rage() { return this.hp <= 3; }
  set(s) { this.state = s; this.st = 0; this.spawned = 0; }
  start() { this.set('intro'); }
  update() {
    this.t++; this.st++;
    if (this.flash > 0) this.flash--;
    if (this.shakeT > 0) this.shakeT--;
    const r = this.rage, k = G.kirby;
    switch (this.state) {
      case 'intro':
        this.bar = Math.min(1, this.st / 70);
        if (this.st === 30) Sound.bossIntro();
        if (this.st > 110) this.set('idle');
        break;
      case 'idle':
        if (this.st > (r ? 50 : 90)) {
          let a = this.lastAtk === 'apples' ? 'blow' : 'apples';
          if (Math.random() < 0.25) a = this.lastAtk;
          this.lastAtk = a;
          this.set(a);
        }
        break;
      case 'apples': {
        const n = r ? 3 : 2, gap = r ? 18 : 26;
        if (this.st % gap === 1 && this.spawned < n) {
          this.spawned++;
          this.shakeT = 10;
          Sound.rustle();
          const x = this.spawned === 1 && k ? clamp(k.cx, ARENA.left + 10, ARENA.right - 24) : rand(ARENA.left + 10, ARENA.right - 30);
          if (r && this.spawned === n && Math.random() < 0.6) G.ents.push(new RollingSpiky().at(x - 7, 26));
          else G.ents.push(new Apple().at(x - 5, 30));
          for (let i = 0; i < 3; i++) addPart({ type: 'leaf', x: x + rand(-8, 8), y: 30, vx: rand(-0.5, 0.5), vy: rand(0.3, 1), life: 40, col: PAL.green });
        }
        if (this.st > n * gap + 40) this.set('idle');
        break;
      }
      case 'blow': {
        const n = r ? 4 : 3, gap = r ? 20 : 28, tele = 40;
        if (this.st > tele && (this.st - tele) % gap === 1 && this.spawned < n) {
          this.spawned++;
          const low = Math.random() < (r ? 0.5 : 0.7);
          G.ents.push(new BossPuff(low ? 152 : 122, r ? 2.1 : 1.6).at(this.x - 6, 112));
          Sound.blow();
        }
        if (this.st > tele + n * gap + 30) this.set('idle');
        break;
      }
      case 'dying':
        this.shakeT = 2;
        if (this.st % 6 === 0) {
          burst(this.x + rand(0, 48), rand(50, 150), 6, [PAL.green, PAL.greenL, PAL.yellow, PAL.white], 2.5);
          if (this.st % 18 === 0) Sound.pop();
        }
        if (this.st % 4 === 0) addPart({ type: 'leaf', x: rand(ARENA.left, ARENA.right), y: 30, vx: rand(-0.5, 0.5), vy: rand(0.4, 1), life: 80, col: pick([PAL.green, PAL.greenD]) });
        if (this.st === 150) {
          this.set('dead');
          G.ents.push(new WarpStar(ARENA.left + 88, 120));
          Sound.star();
          G.showBanner('GRAB THE WARP STAR!');
        }
        break;
    }
  }
  hit(dmg) {
    if (!this.vulnerable) return;
    this.hp = Math.max(0, this.hp - dmg);
    this.flash = 24; this.shakeT = 12;
    G.shake = Math.max(G.shake, 6);
    G.addScore(500, this.x + 10, 70);
    Sound.bossHit();
    if (this.hp === 0) {
      this.set('dying');
      G.addScore(10000, this.x - 20, 56);
      Sound.bossDie();
      clearHazards();
    } else if (this.hp === 3) G.showBanner('WHISPY IS ANGRY!');
  }
  fireTick() {
    if (!this.vulnerable) return;
    if (++this.fireAcc >= 60) { this.fireAcc = 0; this.hit(1); }
    else if (this.fireAcc % 12 === 0) this.flash = Math.max(this.flash, 4);
  }
  draw(ctx) {
    const sx = this.shakeT > 0 ? ((this.t >> 1) & 1 ? 1 : -1) : 0;
    const X = this.x - 8 + sx;
    blit(ctx, SPR.tree, X, 24);
    if (this.flash > 0 && (this.flash >> 1) & 1) {
      ctx.globalAlpha = 0.55; ctx.fillStyle = PAL.white; ctx.fillRect(X + 9, 24, 46, 136); ctx.globalAlpha = 1;
    }
    let eye = 'open', mouth = 'closed';
    const s = this.state;
    if (s === 'sleep' || (s === 'intro' && this.st < 40)) eye = 'closed';
    else if (s === 'dying' || s === 'dead') { eye = 'dead'; mouth = 'o'; }
    else if (this.flash > 6) { eye = 'hurt'; mouth = 'o'; }
    else if (s === 'blow') mouth = this.st > 30 ? 'open' : 'o';
    else if ((this.t % 200) < 6) eye = 'closed';
    const fx = X + 18;
    blit(ctx, SPR.bossEye[eye], fx, 74);
    blit(ctx, SPR.bossEye[eye], fx + 18, 74);
    if (this.rage && eye !== 'dead') { blit(ctx, SPR.bossBrow, fx - 1, 68, true); blit(ctx, SPR.bossBrow, fx + 17, 68); }
    const m = SPR.bossMouth[mouth];
    blit(ctx, m, fx + 14 - m.width / 2, 112 - m.height / 2);
  }
}
Edit C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\3. just skills\js\entities.js
Modified
Write C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\3. just skills\js\kirby.js
270 lines
'use strict';
// Kirby: movement, flight, inhale / spit / swallow, Fire ability, damage.

const K_PHYS = {
  runMax: 1.65, flyMax: 1.2, fullMax: 1.3, fullBigMax: 0.95,
  accGround: 0.22, accAir: 0.16, turnBoost: 1.8,
  frictionGround: 0.25, frictionAir: 0.07, frictionFly: 0.04,
  gravity: 0.26, maxFall: 4.2,
  jumpVel: -5.2, jumpCut: -2,          // ~3.25 tiles high; release early for a short hop
  flyGravity: 0.07, flyMaxFall: 0.9,   // slow sink between flaps
  flapVel: -1.8,                       // weak lift per flap, also the rise-speed cap
  coyote: 6,
};

class Kirby {
  constructor(x, y) {
    this.x = x; this.y = y; this.w = 12; this.h = 13; this.vx = 0; this.vy = 0;
    this.facing = 1; this.onGround = false;
    this.hp = 6; this.maxHp = 6;
    this.puffed = false; this.inhaling = false; this.straining = false; this.firing = false;
    this.held = null; this.ability = null;
    this.invuln = 60; this.hurtT = 0; this.spitT = 0; this.swallowT = 0; this.catchT = 0; this.flapT = 0; this.landT = 0;
    this.coyote = 0; this.jumping = false; this.needRelease = true;
    this.anim = 0; this.t = 0; this.dead = false; this.deadT = 0; this.riding = false;
  }
  get cx() { return this.x + this.w / 2; }
  get cy() { return this.y + this.h / 2; }

  update() {
    this.t++;
    if (this.dead) {
      this.deadT++;
      if (this.deadT > 30) { this.vy = Math.min(this.vy + 0.2, 5); this.y += this.vy; }
      return;
    }
    if (this.riding) return;
    for (const k of ['invuln', 'hurtT', 'spitT', 'swallowT', 'catchT', 'flapT', 'landT']) if (this[k] > 0) this[k]--;
    if (!Input.held('action')) this.needRelease = false;
    const free = this.hurtT === 0;

    // --- one-shot actions ---
    if (free && Input.hit('action')) { if (this.puffed) this.exhale(); else if (this.held) this.spit(); }
    if (free && Input.hit('down')) { if (this.held) this.swallow(); else if (this.puffed) this.exhale(); }
    if (free && Input.hit('drop') && this.ability) this.dropAbility();

    // --- held actions: inhale (normal) or fire breath (Fire ability) ---
    const act = free && Input.held('action') && !this.needRelease && !this.puffed && !this.held;
    this.inhaling = act && !this.ability;
    this.firing = act && this.ability === 'fire';
    if (!this.inhaling) this.straining = false;
    Sound.loop('inhale', this.inhaling);
    Sound.loop('fire', this.firing);

    // --- jump & fly ---
    if (this.onGround) { this.coyote = K_PHYS.coyote; this.jumping = false; } else if (this.coyote > 0) this.coyote--;
    if (free && Input.hit('jump') && !this.inhaling && !this.firing) {
      if (this.coyote > 0 && !this.puffed) {
        this.vy = K_PHYS.jumpVel; this.coyote = 0; this.jumping = true; this.onGround = false;
        Sound.jump(); dust(this.cx, this.y + this.h, 2);
      } else if (!this.held) {
        if (!this.puffed) { this.puffed = true; Sound.puffUp(); }
        this.vy = K_PHYS.flapVel; this.flapT = 12; this.jumping = false;
        Sound.flap();
        addPart({ x: this.cx - 5, y: this.y + this.h - 2, vy: 0.6, life: 12, type: 'cloud' });
      }
    }
    if (this.jumping && this.vy < K_PHYS.jumpCut && !Input.held('jump')) this.vy = K_PHYS.jumpCut;

    // --- horizontal ---
    let dir = 0;
    if (free && !this.inhaling && !this.firing) dir = (Input.held('right') ? 1 : 0) - (Input.held('left') ? 1 : 0);
    if (dir) this.facing = dir;
    const max = this.puffed ? K_PHYS.flyMax : this.held ? (this.held.big ? K_PHYS.fullBigMax : K_PHYS.fullMax) : K_PHYS.runMax;
    if (dir) {
      let a = this.onGround ? K_PHYS.accGround : K_PHYS.accAir;
      if (Math.sign(this.vx) === -dir) a *= K_PHYS.turnBoost;
      this.vx += dir * a;
      if (Math.abs(this.vx) > max) this.vx = approach(this.vx, dir * max, 0.3);
    } else {
      this.vx = approach(this.vx, 0, this.onGround ? K_PHYS.frictionGround : this.puffed ? K_PHYS.frictionFly : K_PHYS.frictionAir);
    }

    // --- gravity ---
    if (this.puffed) {
      this.vy = Math.min(this.vy + K_PHYS.flyGravity, K_PHYS.flyMaxFall);
      if (this.vy < K_PHYS.flapVel) this.vy = K_PHYS.flapVel;
    } else {
      const slow = this.inhaling || this.firing;
      this.vy = Math.min(this.vy + (slow ? 0.2 : K_PHYS.gravity), slow ? 2.5 : K_PHYS.maxFall);
    }

    const wasGround = this.onGround, fallV = this.vy;
    moveX(this, G.level);
    moveY(this, G.level);
    if (this.onGround && !wasGround && fallV > 2.2) { this.landT = 6; dust(this.cx, this.y + this.h, 4); Sound.land(); }
    if (this.onGround && dir && Math.abs(this.vx) > 1.3 && this.t % 9 === 0) dust(this.cx - dir * 5, this.y + this.h, 1);
    if (this.y > LH * TILE + 16) { this.die(true); return; }

    if (this.inhaling) this.doInhale();
    if (this.firing) this.doFire();
    this.anim += this.onGround ? Math.abs(this.vx) : 1;
  }

  mouth() { return { x: this.cx + this.facing * 6, y: this.cy + 1 }; }

  doInhale() {
    const zw = 60, zh = 30;
    const zone = { x: this.facing > 0 ? this.x + this.w - 2 : this.x - zw + 2, y: this.cy - zh / 2, w: zw, h: zh };
    const m = this.mouth();
    // wind streaks rushing into the mouth
    for (let i = 0; i < 2; i++) {
      const d = rand(16, zw), life = Math.max(4, Math.floor(d / 3.4));
      const y = this.cy + rand(-zh / 2, zh / 2) * (d / zw);
      addPart({ type: 'wind', x: this.cx + this.facing * d, y, vx: -this.facing * 3.4, vy: (m.y - y) / life, life, col: Math.random() < 0.5 ? PAL.white : PAL.skyL });
    }
    // star blocks get ripped out of the terrain
    const lv = G.level;
    for (let ty = Math.floor(zone.y / TILE); ty <= Math.floor((zone.y + zone.h - 1) / TILE); ty++) {
      for (let tx = Math.floor(zone.x / TILE); tx <= Math.floor((zone.x + zone.w - 1) / TILE); tx++) {
        if (lv.get(tx, ty) !== T.STAR) continue;
        lv.set(tx, ty, T.EMPTY);
        spawnBlockItem(tx, ty);
        const b = new BlockChunk().at(tx * TILE + 1, ty * TILE + 1);
        b.caughtTimer = 3;
        G.ents.push(b);
      }
    }
    let heavy = false;
    for (const e of G.ents) {
      if (e.dead || !e.inhalable) continue;
      if (e.heavy && e.anchored) {
        if (overlap(zone, e)) { e.pullOn(); heavy = true; }
        continue;
      }
      const dx = m.x - e.cx, dy = m.y - e.cy, d = Math.hypot(dx, dy) || 1;
      if (!(overlap(zone, e) || (e.caughtTimer > 0 && d < 110))) continue;
      e.caughtTimer = 3;
      e.pullT++;
      if (e.heavy) heavy = true;
      const sp = e.heavy ? Math.min(0.5 + e.pullT * 0.05, 3) : Math.min(1 + e.pullT * 0.22, 5.5);
      if (d <= sp + 5) { this.catchItem(e); break; }
      e.x += (dx / d) * sp;
      e.y += (dy / d) * sp;
    }
    this.straining = heavy;
    if (heavy) G.shake = Math.max(G.shake, 2);
  }

  catchItem(e) {
    e.dead = true;
    this.held = { kind: e.kind, big: !!e.heavy, gives: e.gives || null };
    this.inhaling = false; this.straining = false; this.needRelease = true; this.catchT = 10;
    Sound.loop('inhale', false);
    Sound.gulp();
    if (e.heavy) { G.shake = 10; Sound.thud(); }
  }

  spit() {
    const big = this.held.big;
    this.held = null; this.spitT = 12; this.needRelease = true;
    G.ents.push(new StarShot(this.facing, big).at(this.cx + this.facing * 8 - (big ? 8 : 5), this.cy - (big ? 8 : 5)));
    this.vx -= this.facing * (big ? 1.5 : 0.6);
    Sound.spit(big);
    if (big) G.shake = Math.max(G.shake, 5);
  }

  swallow() {
    const h = this.held;
    this.held = null; this.swallowT = 22;
    if (h.gives) {
      this.ability = h.gives;
      Sound.power();
      G.showBanner('FIRE!');
      G.addScore(300, this.cx, this.y - 6);
      burst(this.cx, this.cy, 16, [PAL.yellow, PAL.orange, PAL.red, PAL.white], 3);
    } else {
      Sound.swallow();
      G.addScore(100, this.cx, this.y - 6);
    }
  }

  exhale() {
    this.puffed = false; this.spitT = 10; this.needRelease = true;
    G.ents.push(new AirPuff(this.facing).at(this.cx + this.facing * 8 - 5, this.cy - 5));
    Sound.puff();
  }

  dropAbility() {
    this.ability = null;
    G.ents.push(new AbilityStar(-this.facing).at(this.cx - 6, this.cy - 10));
    Sound.drop();
  }

  doFire() {
    const reach = 40;
    const box = { x: this.facing > 0 ? this.x + this.w : this.x - reach, y: this.cy - 7, w: reach, h: 14 };
    for (let i = 0; i < 2; i++) {
      addPart({ type: 'flame', x: this.cx + this.facing * 7, y: this.cy + rand(-2, 2), vx: this.facing * rand(2.6, 3.6), vy: rand(-0.5, 0.5), life: rand(10, 14) | 0, size: 4 });
    }
    for (const e of G.ents) {
      if (!e.dead && e.enemy && !e.invincible && e.caughtTimer === 0 && overlap(box, e)) defeat(e, 200);
    }
    const b = G.boss;
    if (b && G.inArena && overlap(box, b.hitbox)) b.fireTick();
    const lv = G.level;
    for (let ty = Math.floor(box.y / TILE); ty <= Math.floor((box.y + box.h - 1) / TILE); ty++) {
      for (let tx = Math.floor(box.x / TILE); tx <= Math.floor((box.x + box.w - 1) / TILE); tx++) {
        if (lv.get(tx, ty) === T.STAR) breakBlock(tx, ty);
      }
    }
  }

  damage(srcX) {
    if (this.dead || this.invuln > 0 || this.riding || G.state !== 'playing') return;
    this.hp--;
    this.invuln = 90; this.hurtT = 18;
    this.vx = (this.cx < srcX ? -1 : 1) * 2.2; this.vy = -2.6; this.onGround = false;
    this.puffed = false; this.inhaling = false; this.straining = false; this.firing = false; this.held = null;
    Sound.stopLoops();
    if (this.ability) this.dropAbility();
    G.shake = Math.max(G.shake, 6);
    Sound.hurt();
    burst(this.cx, this.cy, 8, [PAL.white, PAL.yellow], 2.5);
    if (this.hp <= 0) this.die(false);
  }

  die(pit) {
    this.dead = true; this.deadT = 0; this.vx = 0; this.vy = pit ? 0 : -4.5;
    this.inhaling = false; this.firing = false; this.puffed = false;
    if (pit) { this.hp = 0; this.y = LH * TILE + 40; }
    Sound.stopLoops();
    Sound.die();
    G.state = 'dying'; G.stateT = 0;
  }

  frame() {
    const K = SPR.kirby;
    if (this.dead) return K.dead;
    if (this.riding) return K.swallow;
    if (this.hurtT > 0) return K.hurt;
    if (this.straining) return (this.t >> 2) & 1 ? K.strain0 : K.strain1;
    if (this.inhaling) return (this.t >> 3) & 1 ? K.inhale0 : K.inhale1;
    if (this.firing) return (this.t >> 2) & 1 ? K.fire0 : K.fire1;
    if (this.catchT > 0) return K.full;
    if (this.spitT > 0) return K.spit;
    if (this.swallowT > 0) return K.swallow;
    if (this.puffed) {
      if (this.flapT > 6) return K.fly1;
      return this.flapT === 0 && !this.onGround && (this.t >> 4) & 1 ? K.fly1 : K.fly0;
    }
    if (this.held) return this.onGround && Math.abs(this.vx) > 0.2 ? ((this.anim / 8) | 0) % 2 ? K.fullRun0 : K.fullRun1 : K.full;
    if (!this.onGround) return this.vy < 0 ? K.jump : K.fall;
    if (this.landT > 0) return K.land;
    if (Math.abs(this.vx) > 0.25) return K['run' + (((this.anim / 7) | 0) % 4)];
    return this.t % 200 < 8 ? K.blink : K.idle;
  }

  draw(ctx) {
    if (this.dead && this.y > LH * TILE + 30) return;
    if (this.invuln > 0 && !this.hurtT && !this.dead && !this.riding && (this.t >> 2) & 1) return;
    const f = this.frame();
    const ox = this.straining ? ((this.t >> 1) & 1) : 0;
    const x = Math.round(this.cx - 12) + ox, y = Math.round(this.y + this.h - KIRBY_FOOT);
    blit(ctx, f.c, x, y, this.facing < 0);
    if (this.ability === 'fire' && !this.dead) {
      blit(ctx, SPR.crown[(this.t >> 3) & 1], Math.round(this.cx - 7) + ox, y + f.top - 6, this.facing < 0);
    }
  }
}
8:25 PM
Kirby, the enemies, the boss and the level are written. The last piece is the game loop, HUD and screens; then I'll run it in a headless browser to check it.



Write C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\3. just skills\js\game.js
381 lines
'use strict';
// Game flow: states, spawning, camera, HUD, screens and the main loop.

const G = {
  state: 'title', stateT: 0, frame: 0,
  level: null, kirby: null, boss: null, ents: [], parts: [], pops: [],
  camX: 0, shake: 0, fade: 0, banner: null,
  score: 0, lives: 3, checkpoint: 0, inArena: false, flagAnim: 0, winBonus: 0, warp: null,
  addScore(n, x, y) { G.score += n; if (x !== undefined) G.pops.push({ x, y, text: String(n), t: 0 }); },
  showBanner(text) { G.banner = { text, t: 0 }; },
};

const CHECKPOINTS = [2 * TILE + 2, FLAG_TX * TILE + 24, 186 * TILE];

function spawnEntities() {
  G.ents = [];
  for (const s of G.level.spawns) {
    let e;
    switch (s.kind) {
      case 'walker': e = new Walker(); break;
      case 'flyer': e = new Flyer(); break;
      case 'shooter': e = new Shooter(); break;
      case 'hothead': e = new HotHead(); break;
      case 'spiky': e = new Spiky(s.opts); break;
      case 'boulder': G.ents.push(new Boulder(s.tx, s.ty)); continue;
      case 'food': case 'tomato': e = new Food(0, 0, s.kind); break;
    }
    G.ents.push(e.onCell(s.tx, s.ty));
  }
}

// (Re)builds the level and puts Kirby at the current checkpoint. Enemies and blocks reset; score doesn't.
function loadAttempt() {
  G.level = new Level();
  spawnEntities();
  G.parts = []; G.pops = []; G.banner = null; G.shake = 0;
  G.boss = new Boss();
  G.kirby = new Kirby(CHECKPOINTS[G.checkpoint], 10 * TILE - 13);
  G.inArena = false;
  if (G.checkpoint === 2) enterArena();
  G.camX = cameraTarget();
  G.state = 'playing'; G.stateT = 0; G.fade = 1;
}

function startGame() {
  G.score = 0; G.lives = 3; G.checkpoint = 0; G.flagAnim = 0;
  loadAttempt();
  Sound.start();
}

function enterArena() {
  const k = G.kirby;
  G.inArena = true; G.checkpoint = 2;
  k.x = 186 * TILE; k.y = 10 * TILE - k.h; k.vx = 0; k.vy = 0; k.facing = 1;
  k.puffed = false; k.inhaling = false; k.firing = false; k.straining = false;
  G.ents = G.ents.filter((e) => e.x < 183 * TILE);
  G.boss = new Boss();
  G.boss.start();
  G.showBanner('WHISPY WOODS');
}

function cameraTarget() {
  if (G.inArena) return ARENA.camX;
  const k = G.kirby;
  return clamp(k.cx - VIEW_W / 2 + k.facing * 20, 0, CAM_MAX);
}

// ---------- Update ----------
function update() {
  G.frame++; G.stateT++;
  if (Input.hit('mute')) G.showBanner(Sound.toggleMute() ? 'SOUND OFF' : 'SOUND ON');
  if (G.fade > 0 && G.state === 'playing') G.fade = Math.max(0, G.fade - 0.06);

  switch (G.state) {
    case 'title':
      if (Input.hit('action') || Input.hit('jump')) startGame();
      break;
    case 'playing': updatePlaying(); break;
    case 'paused':
      if (Input.hit('pause')) { G.state = 'playing'; Sound.pause(); }
      break;
    case 'door':
      updateFx();
      G.fade = G.stateT < 24 ? G.stateT / 24 : Math.max(0, 1 - (G.stateT - 24) / 24);
      if (G.stateT === 24) { enterArena(); G.camX = ARENA.camX; }
      if (G.stateT >= 48) { G.state = 'playing'; G.fade = 0; }
      break;
    case 'dying':
      G.kirby.update();
      updateFx();
      if (G.stateT >= 110) {
        G.lives--;
        if (G.lives > 0) loadAttempt();
        else { G.state = 'gameover'; G.stateT = 0; Sound.gameOver(); }
      }
      break;
    case 'winning': {
      const w = G.warp, k = G.kirby;
      w.t++;
      if (G.stateT > 30) { w.x += 0.5 + (G.stateT - 30) * 0.05; w.y -= 0.6 + (G.stateT - 30) * 0.035; }
      else w.y = w.baseY + Math.sin(w.t * 0.3) * 2;
      k.x = w.cx - k.w / 2; k.y = w.y - k.h + 6; k.t++;
      if (G.stateT % 2 === 0) addPart({ x: w.x + rand(0, 8), y: w.cy + rand(-4, 6), vx: -1, life: 24, col: pick([PAL.yellow, PAL.white, PAL.pink]), size: 2 });
      updateFx();
      if (G.stateT === 150) {
        G.winBonus = G.lives * 5000;
        G.score += G.winBonus;
        G.state = 'win'; G.stateT = 0;
        Sound.win();
      }
      break;
    }
    case 'gameover':
    case 'win':
      if (G.stateT > 40 && Input.hit('action')) startGame();
      break;
  }
}

function updateFx() {
  for (const p of G.parts) {
    p.t++; p.vy += p.g; p.x += p.vx; p.y += p.vy;
    if (p.drag !== 1) { p.vx *= p.drag; p.vy *= p.drag; }
  }
  G.parts = G.parts.filter((p) => p.t < p.life);
  for (const p of G.pops) { p.t++; p.y -= 0.5; }
  G.pops = G.pops.filter((p) => p.t < 45);
  if (G.banner && ++G.banner.t > 110) G.banner = null;
  if (G.shake > 0) G.shake--;
}

function updatePlaying() {
  if (Input.hit('pause')) { G.state = 'paused'; Sound.stopLoops(); Sound.pause(); return; }
  const k = G.kirby;
  k.update();
  if (G.state !== 'playing') { updateFx(); return; } // Kirby died this step

  for (let i = 0, n = G.ents.length; i < n; i++) {
    const e = G.ents[i];
    if (e.dead) continue;
    if (e.caughtTimer > 0) {
      e.caughtTimer--; e.t++;
      if (e.caughtTimer === 0) { e.pullT = 0; e.onRelease(); }
      continue;
    }
    e.update();
    if (e.y > LH * TILE + 40) e.dead = true;
  }
  G.ents = G.ents.filter((e) => !e.dead);
  if (G.inArena) G.boss.update();

  // Kirby vs the world
  const hb = { x: k.x + 1, y: k.y + 2, w: k.w - 2, h: k.h - 2 };
  for (const e of G.ents) {
    if (e.dead || k.dead) continue;
    if (e instanceof Food) { if (overlap(k, e)) e.collect(k); }
    else if (e instanceof WarpStar) {
      if (e.arrived && overlap(k, e)) {
        G.state = 'winning'; G.stateT = 0; G.warp = e;
        k.riding = true; k.facing = 1; k.puffed = false; k.held = null;
        Sound.stopLoops(); Sound.star();
        return;
      }
    } else if (e.harmful && e.caughtTimer === 0 && overlap(hb, e)) k.damage(e.cx);
  }
  if (G.state !== 'playing') { updateFx(); return; }

  // checkpoint flag
  if (G.checkpoint < 1 && k.x > FLAG_TX * TILE) {
    G.checkpoint = 1;
    Sound.checkpoint();
    G.showBanner('CHECKPOINT!');
  }
  if (G.checkpoint >= 1) G.flagAnim = Math.min(1, G.flagAnim + 0.04);

  // boss door
  if (!G.inArena && k.onGround && overlap(k, { x: DOOR.x + 4, y: DOOR.y, w: 8, h: DOOR.h })) {
    G.state = 'door'; G.stateT = 0;
    k.inhaling = false; k.firing = false; Sound.stopLoops();
    Sound.door();
  }

  // camera
  if (G.inArena) G.camX = ARENA.camX;
  else G.camX += (cameraTarget() - G.camX) * 0.15;

  updateFx();
}

// ---------- Rendering ----------
const canvas = document.getElementById('game');
const ctx = canvas.getContext('2d');
ctx.imageSmoothingEnabled = false;

function drawWorld(camX) {
  const cam = Math.round(camX);
  let sx = 0, sy = 0;
  if (G.shake > 0) { const m = Math.min(3, Math.ceil(G.shake / 3)); sx = Math.round(rand(-m, m)); sy = Math.round(rand(-m, m)); }
  ctx.save();
  ctx.beginPath(); ctx.rect(0, 0, VIEW_W, VIEW_H); ctx.clip();
  BG.draw(ctx, cam, G.frame);
  ctx.translate(-cam + sx, sy);
  const lv = G.level, x0 = Math.max(0, cam - 8);
  ctx.drawImage(lv.canvas, x0, 0, VIEW_W + 16, VIEW_H, x0, 0, VIEW_W + 16, VIEW_H);

  for (const s of lv.signs) if (s.x < cam + VIEW_W && s.x + 200 > cam) drawText(ctx, s.text, s.x, s.y, PAL.white, { shadow: PAL.ink });

  // checkpoint flag
  const fx = FLAG_TX * TILE + 4, top = 10 * TILE - 46;
  ctx.fillStyle = PAL.ink; ctx.fillRect(fx - 1, top, 4, 46);
  ctx.fillStyle = PAL.white; ctx.fillRect(fx, top, 2, 46);
  blit(ctx, SPR.tinyStar, fx - 2, top - 5);
  blit(ctx, G.checkpoint >= 1 ? SPR.flagOn : SPR.flagOff, fx + 2, Math.round(top + 30 - G.flagAnim * 28));

  // boss door
  blit(ctx, SPR.door, DOOR.x - 2, DOOR.y - 2);
  blit(ctx, SPR.star[(G.frame >> 3) % 4], DOOR.x + 2, DOOR.y - 16);

  if (cam + VIEW_W > ARENA.camX) G.boss.draw(ctx);
  for (const e of G.ents) e.draw(ctx);
  if (G.state === 'winning' && G.warp) G.warp.draw(ctx);
  G.kirby.draw(ctx);
  drawParts();
  if (cam + VIEW_W > ARENA.camX - 20) blit(ctx, SPR.canopy, ARENA.camX - 14, -22);
  for (const p of G.pops) drawText(ctx, p.text, p.x, p.y, p.t % 8 < 4 ? PAL.white : PAL.yellow, { align: 'center', shadow: PAL.ink });
  ctx.restore();

  if (G.banner && !(G.banner.t > 90 && (G.banner.t >> 2) & 1)) {
    drawText(ctx, G.banner.text, VIEW_W / 2, 40, PAL.yellow, { scale: 2, align: 'center', outline: PAL.ink });
  }
}

function drawParts() {
  for (const p of G.parts) {
    const k = p.t / p.life, x = Math.round(p.x), y = Math.round(p.y);
    switch (p.type) {
      case 'dot': ctx.fillStyle = p.col; ctx.fillRect(x, y, p.size, p.size); break;
      case 'wind': ctx.fillStyle = p.col; ctx.fillRect(x, y, 3, 1); break;
      case 'leaf': ctx.fillStyle = p.col; ctx.fillRect(x + Math.round(Math.sin(p.t * 0.2) * 2), y, 2, 2); break;
      case 'star': blit(ctx, SPR.tinyStar, x, y); break;
      case 'cloud': blit(ctx, SPR.puff[k < 0.5 ? 0 : 1], x, y); break;
      case 'flame': {
        ctx.fillStyle = k < 0.3 ? PAL.yellow : k < 0.6 ? PAL.orange : k < 0.85 ? PAL.red : PAL.redD;
        const s = Math.max(1, Math.round(p.size * (1 - k * 0.6)));
        ctx.fillRect(x - (s >> 1), y - (s >> 1), s, s);
        break;
      }
    }
  }
}

function drawHUD() {
  const k = G.kirby, y1 = 197, y2 = 211;
  ctx.fillStyle = PAL.navy; ctx.fillRect(0, VIEW_H, VIEW_W, SCREEN_H - VIEW_H);
  ctx.fillStyle = PAL.ink; ctx.fillRect(0, VIEW_H, VIEW_W, 1);
  ctx.fillStyle = PAL.pinkD; ctx.fillRect(0, VIEW_H + 1, VIEW_W, 1);
  const sh = { shadow: PAL.ink };
  drawText(ctx, 'KIRBY', 6, y1, PAL.pink, sh);
  for (let i = 0; i < k.maxHp; i++) {
    const full = i < k.hp, low = k.hp <= 2 && (G.frame >> 3) & 1;
    blit(ctx, full ? (low ? SPR.pipLow : SPR.pip) : SPR.pipEmpty, 40 + i * 8, y1 - 1);
  }
  drawText(ctx, 'SCORE', 144, y1, PAL.white, sh);
  drawText(ctx, String(G.score).padStart(7, '0'), 250, y1, PAL.yellow, { align: 'right', shadow: PAL.ink });

  blit(ctx, SPR.face, 5, y2 - 2);
  drawText(ctx, 'X' + Math.max(0, G.lives), 17, y2, PAL.white, sh);
  const fire = k.ability === 'fire';
  blit(ctx, fire ? SPR.fireIcon : SPR.normalIcon, 40, y2 - 2);
  drawText(ctx, fire ? 'FIRE' : 'NORMAL', 52, y2, fire ? PAL.orange : PAL.gray, sh);

  const b = G.boss;
  if (G.inArena && b && b.state !== 'sleep' && b.state !== 'dead') {
    drawText(ctx, 'WHISPY', 100, y2, PAL.green, sh);
    const bx = 142, bw = 108;
    ctx.fillStyle = PAL.ink; ctx.fillRect(bx - 1, y2 - 1, bw + 2, 9);
    ctx.fillStyle = PAL.purpleD; ctx.fillRect(bx, y2, bw, 7);
    const w = Math.round(bw * (b.hp / b.maxHp) * b.bar);
    ctx.fillStyle = b.flash > 0 && (b.flash >> 1) & 1 ? PAL.white : PAL.red; ctx.fillRect(bx, y2, w, 7);
    ctx.fillStyle = PAL.orange; ctx.fillRect(bx, y2, w, 2);
  } else {
    let hint = '';
    if (k.held) hint = 'ENTER SPIT  DOWN SWALLOW';
    else if (k.puffed) hint = 'ENTER: EXHALE';
    else if (fire) hint = 'ENTER FIRE  SHIFT DROP';
    drawText(ctx, hint, 250, y2, PAL.gray, { align: 'right' });
  }
}

function drawControlsPanel(y) {
  ctx.fillStyle = PAL.navy; ctx.fillRect(10, y, VIEW_W - 20, 66);
  ctx.fillStyle = PAL.pinkD; ctx.fillRect(10, y, VIEW_W - 20, 1); ctx.fillRect(10, y + 65, VIEW_W - 20, 1);
  const rows = [
    ['MOVE', 'ARROWS OR A / D'],
    ['JUMP / FLY', 'SPACE (TAP IN AIR)'],
    ['INHALE', 'HOLD ENTER'],
    ['SPIT / EXHALE', 'ENTER     SWALLOW: DOWN'],
    ['DROP ABILITY', 'SHIFT  PAUSE P  MUTE M'],
  ];
  rows.forEach(([a, b], i) => {
    drawText(ctx, a, 18, y + 5 + i * 12, PAL.pink);
    drawText(ctx, b, 100, y + 5 + i * 12, PAL.white);
  });
}

function drawTitle() {
  const cam = Math.round(300 + Math.sin(G.frame * 0.003) * 300);
  ctx.save();
  BG.draw(ctx, cam, G.frame);
  ctx.translate(-cam, 32);
  ctx.drawImage(G.level.canvas, cam, 0, VIEW_W, VIEW_H, cam, 0, VIEW_W, VIEW_H);
  ctx.restore();
  ctx.fillStyle = PAL.ink; ctx.fillRect(0, VIEW_H + 32, VIEW_W, 0);
  drawText(ctx, 'KIRBY', VIEW_W / 2, 14, PAL.pink, { scale: 4, align: 'center', outline: PAL.ink, ow: 2, shadow: PAL.purpleD });
  drawText(ctx, 'PIXEL QUEST', VIEW_W / 2, 50, PAL.yellow, { scale: 2, align: 'center', outline: PAL.ink });
  const K = SPR.kirby, f = (G.frame >> 3) & 1 ? K.fly0 : K.fly1;
  blit(ctx, f.c, VIEW_W / 2 - 12, 74 + Math.round(Math.sin(G.frame * 0.06) * 4));
  if ((G.frame >> 5) & 1) drawText(ctx, 'PRESS ENTER TO START', VIEW_W / 2, 104, PAL.white, { align: 'center', outline: PAL.ink });
  drawControlsPanel(120);
  drawText(ctx, 'SOUND: ' + (Sound.muted ? 'OFF' : 'ON') + ' (M)', VIEW_W / 2, 194, PAL.white, { align: 'center', outline: PAL.ink });
}

function dim(a) { ctx.globalAlpha = a; ctx.fillStyle = PAL.ink; ctx.fillRect(0, 0, VIEW_W, SCREEN_H); ctx.globalAlpha = 1; }

function render() {
  ctx.fillStyle = PAL.ink;
  ctx.fillRect(0, 0, VIEW_W, SCREEN_H);
  if (G.state === 'title') { drawTitle(); return; }
  drawWorld(G.camX);
  drawHUD();
  if (G.fade > 0) { ctx.globalAlpha = G.fade; ctx.fillStyle = PAL.ink; ctx.fillRect(0, 0, VIEW_W, VIEW_H); ctx.globalAlpha = 1; }

  if (G.state === 'paused') {
    dim(0.65);
    drawText(ctx, 'PAUSED', VIEW_W / 2, 30, PAL.yellow, { scale: 3, align: 'center', outline: PAL.ink });
    drawControlsPanel(70);
    drawText(ctx, 'PRESS P TO RESUME', VIEW_W / 2, 150, PAL.white, { align: 'center' });
  } else if (G.state === 'gameover') {
    dim(Math.min(0.8, G.stateT / 40));
    drawText(ctx, 'GAME OVER', VIEW_W / 2, 60, PAL.red, { scale: 3, align: 'center', outline: PAL.ink });
    drawText(ctx, 'SCORE ' + G.score, VIEW_W / 2, 100, PAL.white, { align: 'center' });
    blit(ctx, SPR.kirby.hurt.c, VIEW_W / 2 - 12, 112);
    if (G.stateT > 40 && (G.frame >> 5) & 1) drawText(ctx, 'PRESS ENTER TO TRY AGAIN', VIEW_W / 2, 150, PAL.yellow, { align: 'center' });
  } else if (G.state === 'win') {
    dim(Math.min(0.75, G.stateT / 40));
    drawText(ctx, 'YOU WIN!', VIEW_W / 2, 30, PAL.yellow, { scale: 3, align: 'center', outline: PAL.ink });
    const K = SPR.kirby, f = (G.frame >> 4) & 1 ? K.swallow : K.jump;
    blit(ctx, f.c, VIEW_W / 2 - 12, 62 - ((G.frame >> 4) & 1 ? 0 : 4));
    drawText(ctx, 'LIFE BONUS  ' + G.lives + ' X 5000 = ' + G.winBonus, VIEW_W / 2, 98, PAL.white, { align: 'center' });
    drawText(ctx, 'FINAL SCORE  ' + G.score, VIEW_W / 2, 114, PAL.pink, { scale: 1, align: 'center' });
    if (G.stateT > 40 && (G.frame >> 5) & 1) drawText(ctx, 'PRESS ENTER TO PLAY AGAIN', VIEW_W / 2, 150, PAL.yellow, { align: 'center' });
  }
}

// ---------- Boot & loop ----------
function resize() {
  const strip = document.getElementById('controls').offsetHeight + 40;
  const s = Math.max(1, Math.floor(Math.min((innerWidth - 24) / VIEW_W, (innerHeight - strip) / SCREEN_H)));
  canvas.style.width = VIEW_W * s + 'px';
  canvas.style.height = SCREEN_H * s + 'px';
}

buildSprites();
BG.build();
G.level = new Level();
addEventListener('resize', resize);
resize();

const STEP = 1000 / 60;
let last = performance.now(), acc = 0;
function loop(now) {
  acc += Math.min(now - last, 250);
  last = now;
  let n = 0;
  while (acc >= STEP && n < 5) { update(); Input.endStep(); acc -= STEP; n++; }
  if (n === 5) acc = 0;
  render();
  requestAnimationFrame(loop);
}
requestAnimationFrame(loop);
Edit C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\3. just skills\js\game.js
Removed 1 line
Edit C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\3. just skills\js\game.js
Removed 1 line
PowerShell Find an installed browser and Node
IN
$paths = @("${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe", "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe", "$env:ProgramFiles\Google\Chrome\Application\chrome.exe", "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe"); $paths | Where-Object { Test-Path $_ }; (Get-Command node -ErrorAction SilentlyContinue).Source

OUT
C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe
C:\Program Files\Google\Chrome\Application\chrome.exe
C:\nvm4w\nodejs\node.exe
8:27 PM
The code is written. I'll add a small headless smoke test in tests/ that drives the real game logic through each mechanic, then run it in Edge.



Write C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\3. just skills\tests\smoke.html
211 lines
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Kirby smoke tests</title>
<style>
  body { margin: 0; background: #111; color: #eee; font: 12px monospace; }
  canvas { image-rendering: pixelated; width: 768px; height: 672px; }
  #controls { display: none; }
</style>
</head>
<body>
<!-- Headless smoke test: drives the real game code step by step with synthetic key events.
     Run:  msedge --headless --disable-gpu --virtual-time-budget=20000 --dump-dom tests/smoke.html
     Add ?shot=<scene> to render a scene for a screenshot instead (title, play, fly, inhale, boulder, fire, boss, win). -->
<canvas id="game" width="256" height="224"></canvas>
<div id="controls"></div>
<pre id="out">RUNNING</pre>
<script>
  window.__errors = [];
  addEventListener('error', (e) => window.__errors.push(e.message + ' @' + e.lineno));
  window.requestAnimationFrame = () => 0; // the test drives update() itself
</script>
<script src="../js/core.js"></script>
<script src="../js/sprites.js"></script>
<script src="../js/level.js"></script>
<script src="../js/entities.js"></script>
<script src="../js/kirby.js"></script>
<script src="../js/game.js"></script>
<script>
(function () {
  const CODES = { left: 'ArrowLeft', right: 'ArrowRight', down: 'ArrowDown', jump: 'Space', action: 'Enter', drop: 'ShiftLeft', pause: 'KeyP' };
  const press = (a) => dispatchEvent(new KeyboardEvent('keydown', { code: CODES[a] }));
  const release = (a) => dispatchEvent(new KeyboardEvent('keyup', { code: CODES[a] }));
  const step = (n = 1) => { for (let i = 0; i < n; i++) { update(); Input.endStep(); } };
  const tap = (a, after = 1) => { press(a); step(1); release(a); step(after); };
  const results = [];
  const check = (name, cond, info = '') => results.push((cond ? 'PASS ' : 'FAIL ') + name + (info ? '  [' + info + ']' : ''));
  const k = () => G.kirby;
  const put = (e, x, y) => { e.x = x; e.y = y; G.ents.push(e); return e; };
  const ground = 10 * TILE;
  const reset = (x) => { G.checkpoint = 0; loadAttempt(); G.ents = G.ents.filter((e) => e.kind === 'boulder'); k().x = x; k().y = ground - 13; k().invuln = 0; step(2); };

  function runTests() {
    check('boots to title', G.state === 'title');
    tap('action', 2);
    check('Enter starts the game', G.state === 'playing');
    check('Kirby at start, full health, 3 lives', k().hp === 6 && G.lives === 3);

    reset(40);
    const x0 = k().x; press('right'); step(60); release('right'); step(20);
    check('runs right', k().x > x0 + 60, 'dx=' + (k().x - x0).toFixed(1));
    check('stands on ground', k().onGround);

    reset(40);
    let top = k().y; press('jump'); for (let i = 0; i < 40; i++) { step(1); top = Math.min(top, k().y); } release('jump'); step(40);
    const jh = ground - 13 - top;
    check('jump height about 3 tiles', jh > 40 && jh < 60, jh.toFixed(1) + 'px');
    reset(40);
    tap('jump', 1); let shortTop = k().y; for (let i = 0; i < 40; i++) { step(1); shortTop = Math.min(shortTop, k().y); }
    check('tap jump is a short hop', ground - 13 - shortTop < jh - 10, (ground - 13 - shortTop).toFixed(1) + 'px');

    reset(40);
    tap('jump', 10);
    for (let i = 0; i < 12; i++) tap('jump', 8);
    check('repeated Space flies upward', k().puffed && k().y < ground - 13 - 70, 'y=' + k().y.toFixed(1));
    const yBefore = k().y; step(30);
    check('slow sink between flaps', k().y > yBefore && k().y - yBefore < 30, 'sank ' + (k().y - yBefore).toFixed(1));
    tap('action', 2);
    check('Enter in flight exhales an air puff', !k().puffed && G.ents.some((e) => e.kind === 'airpuff'));

    reset(100);
    const w = put(new Walker(), 140, ground - 12);
    press('action'); step(60);
    check('holding Enter inhales a walker', k().held && k().held.kind === 'walker' && w.dead, k().held ? k().held.kind : 'nothing');
    release('action'); step(2);
    const w2 = put(new Walker(), 200, ground - 12); const s0 = G.score;
    tap('action', 30);
    check('Enter spits a star that defeats an enemy', w2.dead && G.score > s0, 'score +' + (G.score - s0));

    reset(100);
    const sp = put(new Spiky(), 130, ground - 30);
    press('action'); step(60); release('action'); step(2);
    check('spiky enemy cannot be inhaled', !k().held && !sp.dead && sp.caughtTimer === 0);

    reset(100);
    G.level.set(9, 9, T.STAR);
    k().x = 120; k().facing = 1;
    press('action'); step(40); release('action'); step(2);
    check('star blocks can be inhaled', G.level.get(9, 9) !== T.STAR || (k().held && k().held.kind === 'block'));

    reset(139 * TILE - 13);
    k().facing = 1;
    check('boulder blocks the passage', G.level.solidAt(140 * TILE + 4, 9 * TILE));
    press('action');
    let strained = false;
    for (let i = 0; i < 200 && !k().held; i++) { step(1); strained = strained || k().straining; }
    release('action'); step(2);
    check('Kirby strains against the boulder', strained);
    check('boulder can be inhaled (big)', k().held && k().held.big);
    check('passage cleared', !G.level.solidAt(140 * TILE + 4, 9 * TILE));
    tap('action', 1);
    const big = G.ents.find((e) => e.kind === 'shot');
    check('spitting a big object fires a big star', big && big.big);

    reset(100);
    put(new HotHead(), 135, ground - 13);
    press('action'); step(60); release('action'); step(2);
    check('fire creature inhaled', k().held && k().held.gives === 'fire');
    tap('down', 2);
    check('Down swallows it and grants Fire', k().ability === 'fire' && !k().held);
    const w3 = put(new Walker(), k().x + 30, ground - 12);
    press('action'); step(20); release('action'); step(2);
    check('fire breath defeats enemies', w3.dead && !k().held);
    tap('drop', 2);
    check('Shift drops the ability as a star', k().ability === null && G.ents.some((e) => e.kind === 'abilitystar'));

    reset(100);
    const w4 = put(new Walker(), 110, ground - 12);
    step(3);
    check('touching an enemy costs one health pip', k().hp === 5 && k().invuln > 0, 'hp=' + k().hp);
    w4.dead = true;

    reset(100);
    const lives0 = G.lives; k().x = 51 * TILE; k().y = 7 * TILE; step(120);
    check('falling in a pit costs a life', G.lives === lives0 - 1 && G.state === 'playing', 'lives=' + G.lives);

    reset(100);
    k().x = FLAG_TX * TILE + 4; step(2);
    check('midpoint flag sets the checkpoint', G.checkpoint === 1);
    k().x = 182 * TILE; k().y = ground - 13; step(2);
    check('door starts the transition', G.state === 'door');
    step(50);
    check('door leads into the boss arena', G.state === 'playing' && G.inArena && G.camX === ARENA.camX);
    step(120);
    check('boss wakes up', G.boss.vulnerable, G.boss.state);
    let hits = 0;
    for (let i = 0; i < 6; i++) { G.ents.push(new StarShot(1, false).at(ARENA.right - 20, 100)); step(3); hits++; }
    check('stars damage the boss down to 0', G.boss.hp === 0 && G.boss.state === 'dying', 'hp=' + G.boss.hp);
    step(160);
    const warp = G.ents.find((e) => e.kind === 'warp');
    check('defeated boss drops the warp star', !!warp);
    step(30);
    k().x = warp.x + 6; k().y = warp.y; k().invuln = 0; step(2);
    check('touching the warp star wins', G.state === 'winning');
    step(160);
    check('win screen shows with life bonus', G.state === 'win' && G.winBonus === G.lives * 5000);
    render();
    step(50); tap('action', 2);
    check('Enter restarts from the win screen', G.state === 'playing' && G.score === 0 && G.checkpoint === 0);

    G.checkpoint = 2; loadAttempt(); step(130);
    check('respawn at the boss door resets the boss', G.inArena && G.boss.hp === 6);
    G.ents.push(new StarShot(1, false).at(ARENA.right - 20, 100)); step(3);
    const hp1 = G.boss.hp;
    k().x = ARENA.right - 12 - 4; k().facing = 1; k().ability = 'fire';
    press('action'); step(130); release('action'); step(2);
    check('fire breath damages the boss about once per second', G.boss.hp <= hp1 - 2, 'hp ' + hp1 + ' -> ' + G.boss.hp);

    G.lives = 1; k().invuln = 0; k().hp = 1; k().damage(k().cx + 10); step(130);
    check('losing the last life shows game over', G.state === 'gameover');
    render();
    step(50); tap('action', 2);
    check('Enter restarts after game over', G.state === 'playing' && G.lives === 3);

    // pause
    tap('pause', 2);
    check('P pauses', G.state === 'paused'); render();
    tap('pause', 2);
    check('P resumes', G.state === 'playing');

    // soak: play the whole level with random inputs for a while, rendering every frame
    reset(40);
    const acts = ['left', 'right', 'jump', 'action', 'down', 'drop'];
    for (let i = 0; i < 6000; i++) {
      if (i % 7 === 0) { const a = acts[(Math.random() * acts.length) | 0]; Math.random() < 0.5 ? press(a) : release(a); }
      if (i % 4 === 0) press('right');
      if (G.state === 'gameover' || G.state === 'win') { tap('action', 1); }
      step(1); render();
    }
    check('6000 random frames with no errors', window.__errors.length === 0);
    check('no runtime errors at all', window.__errors.length === 0, window.__errors.join(' | '));
  }

  function scene(name) {
    if (name === 'title') { step(10); render(); return; }
    tap('action', 2);
    const kb = k();
    kb.invuln = 0;
    if (name === 'play') { kb.x = 150; step(30); }
    if (name === 'fly') { kb.x = 51 * TILE; kb.y = 100; kb.puffed = true; G.camX = 46 * TILE; step(1); }
    if (name === 'inhale') { G.ents = []; kb.x = 100; put(new Walker(), 150, ground - 12); put(new Walker(), 175, ground - 12); press('action'); step(6); }
    if (name === 'boulder') { G.ents = G.ents.filter((e) => e.kind === 'boulder' || e.kind === 'walker' && e.x > 2200); kb.x = 139 * TILE - 13; kb.facing = 1; G.camX = 130 * TILE; press('action'); step(40); }
    if (name === 'fire') { kb.x = 152 * TILE; kb.ability = 'fire'; G.camX = 146 * TILE; press('action'); step(20); }
    if (name === 'hill') { kb.x = 106 * TILE; kb.y = 7 * TILE; G.camX = 104 * TILE; step(60); }
    if (name === 'boss') { G.checkpoint = 2; loadAttempt(); step(200); G.boss.hp = 3; step(80); }
    if (name === 'win') { G.checkpoint = 2; loadAttempt(); step(130); G.boss.hit(6); step(170); const w = G.ents.find((e) => e.kind === 'warp'); kb.riding = false; G.kirby.x = w.x; G.kirby.y = w.y; step(320); }
    render();
  }

  const shot = new URLSearchParams(location.search).get('shot');
  try { if (shot) scene(shot); else runTests(); }
  catch (e) { results.push('FAIL exception: ' + e.message + '\n' + e.stack); }
  if (window.__errors.length) results.push('ERRORS: ' + window.__errors.join(' | '));
  document.getElementById('out').textContent = shot ? 'SHOT ' + shot : results.join('\n') +
    '\n\n' + results.filter((r) => r.startsWith('PASS')).length + '/' + results.length + ' passed';
})();
</script>
</body>
</html>
PowerShell Run the headless smoke tests in Edge
IN
$edge = "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"; $f = (Resolve-Path "tests\smoke.html").Path -replace '\\','/'; $out = & $edge --headless=new --disable-gpu --no-first-run --allow-file-access-from-files --virtual-time-budget=30000 --dump-dom "file:///$f" 2>$null | Out-String; $m = [regex]::Match($out, '<pre id="out">([\s\S]*?)</pre>'); if ($m.Success) { [System.Net.WebUtility]::HtmlDecode($m.Groups[1].Value) } else { $out.Substring(0, [Math]::Min(3000, $out.Length)) }

OUT
PASS boots to title
PASS Enter starts the game
PASS Kirby at start, full health, 3 lives
PASS runs right  [dx=98.3]
PASS stands on ground
PASS jump height about 3 tiles  [49.4px]
PASS tap jump is a short hop  [11.7px]
PASS repeated Space flies upward  [y=2.5]
PASS slow sink between flaps  [sank 26.3]
PASS Enter in flight exhales an air puff
PASS holding Enter inhales a walker  [walker]
PASS Enter spits a star that defeats an enemy  [score +200]
PASS spiky enemy cannot be inhaled
PASS star blocks can be inhaled
PASS boulder blocks the passage
PASS Kirby strains against the boulder
PASS boulder can be inhaled (big)
PASS passage cleared
PASS spitting a big object fires a big star
PASS fire creature inhaled
PASS Down swallows it and grants Fire
PASS fire breath defeats enemies
PASS Shift drops the ability as a star
PASS touching an enemy costs one health pip  [hp=5]
FAIL falling in a pit costs a life  [lives=3]
PASS midpoint flag sets the checkpoint
PASS door starts the transition
PASS door leads into the boss arena
PASS boss wakes up  [idle]
PASS stars damage the boss down to 0  [hp=0]
PASS defeated boss drops the warp star
FAIL touching the warp star wins
FAIL win screen shows with life bonus
FAIL Enter restarts from the win screen
PASS respawn at the boss door resets the boss
PASS fire breath damages the boss about once per second  [hp 5 -> 3]
PASS losing the last life shows game over
PASS Enter restarts after game over
PASS P pauses
PASS P resumes
PASS 6000 random frames with no errors
PASS no runtime errors at all

38/42 passed
8:28 PM
Two of the failures are timing mistakes in the test, not bugs in the game. The pit death and the warp star's descent each take longer than the frames I gave them. I'll fix the test.



Edit C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\3. just skills\tests\smoke.html
Modified
Edit C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\3. just skills\tests\smoke.html
Added 1 line
PowerShell Re-run smoke tests, show failures only
IN
$edge = "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"; $f = (Resolve-Path "tests\smoke.html").Path -replace '\\','/'; $out = & $edge --headless=new --disable-gpu --no-first-run --allow-file-access-from-files --virtual-time-budget=30000 --dump-dom "file:///$f" 2>$null | Out-String; $m = [regex]::Match($out, '<pre id="out">([\s\S]*?)</pre>'); [System.Net.WebUtility]::HtmlDecode($m.Groups[1].Value) | Select-String -Pattern 'FAIL|passed|ERROR'

OUT
PASS boots to title
PASS Enter starts the game
PASS Kirby at start, full health, 3 lives
PASS runs right  [dx=98.3]
PASS stands on ground
PASS jump height about 3 tiles  [49.4px]
PASS tap jump is a short hop  [11.7px]
PASS repeated Space flies upward  [y=2.5]
PASS slow sink between flaps  [sank 26.3]
PASS Enter in flight exhales an air puff
PASS holding Enter inhales a walker  [walker]
PASS Enter spits a star that defeats an enemy  [score +200]
PASS spiky enemy cannot be inhaled
PASS star blocks can be inhaled
PASS boulder blocks the passage
PASS Kirby strains against the boulder
PASS boulder can be inhaled (big)
PASS passage cleared
PASS spitting a big object fires a big star
PASS fire creature inhaled
PASS Down swallows it and grants Fire
PASS fire breath defeats enemies
PASS Shift drops the ability as a star
PASS touching an enemy costs one health pip  [hp=5]
PASS falling in a pit costs a life  [lives=2]
PASS midpoint flag sets the checkpoint
PASS door starts the transition
PASS door leads into the boss arena
PASS boss wakes up  [idle]
PASS stars damage the boss down to 0  [hp=0]
PASS defeated boss drops the warp star
PASS warp star has landed
PASS touching the warp star wins
PASS win screen shows with life bonus
PASS Enter restarts from the win screen
PASS respawn at the boss door resets the boss
PASS fire breath damages the boss about once per second  [hp 5 -> 3]
PASS losing the last life shows game over
PASS Enter restarts after game over
PASS P pauses
PASS P resumes
PASS 6000 random frames with no errors
PASS no runtime errors at all

43/43 passed
8:28 PM
All 43 checks pass. Next I'll take screenshots to check how it looks.



PowerShell Render scene screenshots with headless Edge
IN
$edge = "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"; $f = (Resolve-Path "tests\smoke.html").Path -replace '\\','/'; New-Item -ItemType Directory -Force tests\shots | Out-Null; foreach ($s in 'title','play','inhale','boulder','fire','hill','boss','win','fly') { $png = (Join-Path (Resolve-Path tests\shots) "$s.png"); & $edge --headless=new --disable-gpu --no-first-run --allow-file-access-from-files --virtual-time-budget=8000 --window-size=780,690 --hide-scrollbars "--screenshot=$png" "file:///$f`?shot=$s" 2>$null | Out-Null }; Get-ChildItem tests\shots | Select-Object Name, Length

OUT
Name        Length
----        ------
boss.png     11721
boulder.png  11221
fire.png     13053
fly.png      11038
hill.png     10335
inhale.png   10266
play.png     10254
title.png     9788
win.png      11233
Read C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\3. just skills\tests\shots\title.png
Read C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\3. just skills\tests\shots\inhale.png
Read C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\3. just skills\tests\shots\boulder.png
Read C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\3. just skills\tests\shots\boss.png
Read C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\3. just skills\tests\shots\fire.png
Read C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\3. just skills\tests\shots\win.png
Read C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\3. just skills\tests\shots\hill.png
Edit C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\3. just skills\tests\smoke.html
Modified
PowerShell Re-render the win screen screenshot
IN
$edge = "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"; $f = (Resolve-Path "tests\smoke.html").Path -replace '\\','/'; foreach ($s in 'win') { $png = (Join-Path (Resolve-Path tests\shots) "$s.png"); & $edge --headless=new --disable-gpu --no-first-run --allow-file-access-from-files --virtual-time-budget=8000 --window-size=780,690 --hide-scrollbars "--screenshot=$png" "file:///$f`?shot=$s" 2>$null | Out-Null }

OUT
(PowerShell completed with no output)
Read C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\3. just skills\tests\shots\fly.png
Read C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\3. just skills\tests\shots\win.png
8:29 PM
Everything renders correctly, including the win screen. I'll delete the generated screenshots so only the test page stays in the repo.



PowerShell Remove screenshots and list project files
IN
Remove-Item -Recurse -Force tests\shots -Confirm:$false; Get-ChildItem -Recurse -File -Exclude *.md | Where-Object { $_.FullName -notmatch '\\.claude\\' } | Select-Object @{n='File';e={$_.FullName.Substring((Get-Location).Path.Length+1)}}, Length

OUT
File                  Length
----                  ------
js\core.js             15174
js\entities.js         22276
js\game.js             14728
js\kirby.js            11439
js\level.js            11673
js\sprites.js          15439
tests\smoke.html       10769
index.html              1953
kirby_game_prompt.txt   1325
8:29 PM
I've built the game to match DESIGN.md: double-click index.html to play. It uses no images, libraries or build step.

An automated test I wrote passes all 43 checks. It drives the real game code in headless Edge and covers every mechanic from start to win, plus 6,000 frames of random input with no errors. I also looked at screenshots of the title, the boulder passage, the fire grove, the boss fight and the win screen, and they render as intended. Two things it can't check: whether the controls feel good in a human playthrough, and whether the sounds are pleasant, because the test runs with no speakers.

What's in it

Kirby: runs, does a variable-height jump of about 3 tiles, and flies with Space (weak lift per flap, capped rise speed, slow sink). Pressing Enter while flying fires an air puff.
Inhale and spit: holding Enter pulls things in with visible wind streaks. Enter again spits a star that defeats enemies, and Down swallows.
The boulder blocking the passage makes Kirby strain, rumble and shake the screen before it rips loose. Spitting it fires a big star that passes through enemies.
Fire: only the fire creature gives it. Kirby gets a flame crown and breathes fire while you hold Enter; Shift drops it as a bouncing star he can inhale again.
Enemies: walker, flyer that swoops, shooter whose lobbed balls Kirby can inhale, spiky enemy he can't inhale, and the fire creature.
Level: four sections, each with a hint sign the first time something new appears, followed by the tree boss (Whispy Woods) behind a door.
The boss drops apples to use as ammo and blows air puffs. At half health it gets faster, drops spiky enemies and frowns.
Beating it brings down a warp star; touching the star wins.
Lives and screens:
6 health pips per life and 3 lives. Pits cost a whole life.
Checkpoints are the start, a midpoint flag and the boss door.
The HUD shows a hint for the current action.
There are title, pause, game-over and win screens; the win screen adds a 5,000-point bonus per life left. Enter restarts.
Where to adjust the feel: all of Kirby's movement numbers (gravity, jump, flap lift, speeds) are in one block, K_PHYS, at the top of js/kirby.js.

Running the tests: open tests/smoke.html in a browser, or run:


msedge --headless --virtual-time-budget=30000 --dump-dom tests/smoke.html
Where it differs from the spec:

The palette has 26 colors, slightly over the "about 24" in DESIGN.md.
When Kirby takes damage he loses whatever is in his mouth. DESIGN.md doesn't say what should happen in that case.
I haven't committed anything.



Idle 13h 19m. The prompt cache has likely expired, so your next message will re-cache about 229k tokens.
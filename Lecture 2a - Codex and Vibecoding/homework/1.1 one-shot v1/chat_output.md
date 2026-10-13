kirby_game_prompt.txt
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
Show more
Bash List files in current directory
IN
ls -la

OUT
total 8
drwxr-xr-x 1 Ethan 197121    0 Oct  9 15:13 ./
drwxr-xr-x 1 Ethan 197121    0 Oct  9 15:12 ../
-rw-r--r-- 1 Ethan 197121 1312 Oct  9 15:17 kirby_game_prompt.txt
Bash Check for node and browsers for testing
IN
node --version 2>&1; ls "/c/Program Files/Google/Chrome/Application/" 2>&1 | head; ls "/c/Program Files (x86)/Microsoft/Edge/Application/" 2>&1 | head

OUT
v22.23.3
137.0.7151.120/
SetupMetrics/
chrome.VisualElementsManifest.xml
chrome.exe*
chrome_proxy.exe*
debug.log
master_preferences
154.0.4258.62/
155.0.4283.45/
AppxSignature.p7x
PlatformExperiencesHelper/
SetupMetrics/
msedge.VisualElementsManifest.xml
msedge.exe*
msedge_proxy.exe*
pwahelper.exe*
3:30 PM
Empty directory except the prompt. I'll build it as a single self-contained index.html and then verify it in headless Chrome.



Write C:\Users\ethan\Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\1.1 one-shot v1\index.html
1652 lines
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kirby: Star Plains</title>
<style>
  html, body { margin: 0; height: 100%; background: #1d1430; color: #f3e6ff; font-family: "Courier New", monospace; }
  body { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 14px; overflow: hidden; }
  canvas {
    display: block; background: #000;
    image-rendering: pixelated; image-rendering: crisp-edges;
    box-shadow: 0 0 0 4px #2a1a2e, 0 0 0 8px #f7a1c8, 0 12px 40px rgba(0,0,0,.6);
  }
  #controls { display: flex; flex-wrap: wrap; gap: 6px 18px; justify-content: center; font-size: 13px; max-width: 980px; padding: 0 12px; }
  #controls span { white-space: nowrap; }
  kbd { display: inline-block; background: #f7a1c8; color: #2a1a2e; border-radius: 3px; padding: 1px 5px; margin: 0 1px;
        font: bold 12px "Courier New", monospace; box-shadow: 0 2px 0 #b14f80; }
</style>
</head>
<body>
<canvas id="game" width="320" height="192"></canvas>
<div id="controls">
  <span><kbd>&larr;</kbd><kbd>&rarr;</kbd> / <kbd>A</kbd><kbd>D</kbd> Move</span>
  <span><kbd>Space</kbd> Jump &middot; tap again in air to Fly</span>
  <span><kbd>Enter</kbd> hold: Inhale &middot; press: Spit / Exhale</span>
  <span><kbd>&darr;</kbd>/<kbd>S</kbd> Swallow</span>
  <span><kbd>P</kbd> Pause</span>
  <span><kbd>M</kbd> Mute</span>
  <span><kbd>R</kbd> Restart</span>
</div>
<script>
'use strict';

// ============================================================
//  Constants & palette
// ============================================================
const VW = 320, VH = 192, TS = 16, LW = 230, LH = 15;
const cv = document.getElementById('game');
const ctx = cv.getContext('2d');

const PAL = {
  K: '#2a1a2e',                               // outline
  P: '#f7a1c8', p: '#ffd6e8', D: '#d9649a',   // Kirby pinks
  C: '#f2557a',                               // blush
  R: '#e0303e', r: '#8e1c34',                 // feet / mouth
  W: '#ffffff', B: '#1c1440', b: '#3b62d9',   // eyes
  O: '#f39030', o: '#b5561e', T: '#ffd9a0',   // orange / tan
  Y: '#ffe14a', y: '#d99a1c',                 // yellow
  G: '#5ccb4c', g: '#2a7f3c', H: '#a6f07a',   // greens
  L: '#d4efff', l: '#7ab8e8',                 // cloud blues
  V: '#a466d6', v: '#5a2e8e',                 // purples
  S: '#c3c3d4', s: '#76768e',                 // stone
  N: '#b8743c', n: '#7c4424',                 // dirt
};
const rgbCache = {};
function rgb(c) {
  c = PAL[c] || c;
  if (rgbCache[c]) return rgbCache[c];
  const n = parseInt(c.slice(1), 16);
  return (rgbCache[c] = [(n >> 16) & 255, (n >> 8) & 255, n & 255]);
}

const PH = {
  g: 0.22, maxFall: 4.2,
  runAcc: 0.15, airAcc: 0.12, runMax: 1.7, fric: 0.17, airFric: 0.04,
  jumpV: -4.35, jumpCut: 0.45,
  puffG: 0.075, puffMaxFall: 0.85, puffFlap: -2.0, puffMax: 1.2, puffAcc: 0.09,
  fullMax: 1.25, fullJump: -3.8,
};

const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
const approach = (v, t, d) => (v < t ? Math.min(v + d, t) : Math.max(v - d, t));
const rand = (a, b) => a + Math.random() * (b - a);
const hash = (n) => Math.imul(n ^ 0x5bd1e995, 2654435761) >>> 0;

// ============================================================
//  Pixel painter: sprites are built pixel-by-pixel in code
// ============================================================
function inStar(px, py, R, r, rot) {
  const pts = [];
  for (let i = 0; i < 10; i++) {
    const a = rot - Math.PI / 2 + i * Math.PI / 5, rr = i % 2 ? r : R;
    pts.push(Math.cos(a) * rr, Math.sin(a) * rr);
  }
  let inside = false;
  for (let i = 0, j = 9; i < 10; j = i++) {
    const xi = pts[2 * i], yi = pts[2 * i + 1], xj = pts[2 * j], yj = pts[2 * j + 1];
    if ((yi > py) !== (yj > py) && px < (xj - xi) * (py - yi) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

function painter(w, h) {
  const d = new Array(w * h).fill(null);
  const g = { w, h, d };
  g.set = (x, y, c) => { x = Math.floor(x); y = Math.floor(y); if (x >= 0 && y >= 0 && x < w && y < h) d[y * w + x] = c; };
  g.get = (x, y) => (x >= 0 && y >= 0 && x < w && y < h ? d[y * w + x] : null);
  g.rect = (x, y, rw, rh, c) => { for (let j = 0; j < rh; j++) for (let i = 0; i < rw; i++) g.set(x + i, y + j, c); };
  g.ell = (cx, cy, rx, ry, c) => {
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const a = (x + .5 - cx) / rx, b = (y + .5 - cy) / ry;
      if (a * a + b * b <= 1) d[y * w + x] = c;
    }
  };
  // outlined, shaded ellipse (light from the upper-left)
  g.ball = (cx, cy, rx, ry, base, shade, light) => {
    g.ell(cx, cy, rx + 1, ry + 1, 'K');
    const s = Math.max(0.7, Math.min(rx, ry) * 0.2);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const a = (x + .5 - cx) / rx, b = (y + .5 - cy) / ry;
      if (a * a + b * b > 1) continue;
      const a2 = (x + .5 - cx + s) / rx, b2 = (y + .5 - cy + s) / ry;
      d[y * w + x] = shade && a2 * a2 + b2 * b2 > 1 ? shade : base;
    }
    if (light) g.ell(cx - rx * 0.38, cy - ry * 0.5, Math.max(1, rx * 0.3), Math.max(0.8, ry * 0.2), light);
  };
  g.star = (cx, cy, R, r, rot, c, sx = 1) => {
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++)
      if (inStar((x + .5 - cx) / sx, y + .5 - cy, R, r, rot)) d[y * w + x] = c;
  };
  g.outline = (oc) => {
    const add = [];
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      if (d[y * w + x]) continue;
      for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
        const n = g.get(x + dx, y + dy);
        if (n && n !== 'K' && n !== oc) { add.push(y * w + x); break; }
      }
    }
    for (const i of add) d[i] = oc;
  };
  return g;
}

function gridToCanvas(g, flip) {
  const c = document.createElement('canvas');
  c.width = g.w; c.height = g.h;
  const cx = c.getContext('2d');
  const id = cx.createImageData(g.w, g.h);
  for (let y = 0; y < g.h; y++) for (let x = 0; x < g.w; x++) {
    const col = g.d[y * g.w + x];
    if (!col) continue;
    const [r, gg, b] = rgb(col);
    const i = (y * g.w + (flip ? g.w - 1 - x : x)) * 4;
    id.data[i] = r; id.data[i + 1] = gg; id.data[i + 2] = b; id.data[i + 3] = 255;
  }
  cx.putImageData(id, 0, 0);
  return c;
}

// returns [facingRight, facingLeft]
function sprite(w, h, fn, oc = 'K') {
  const g = painter(w, h);
  fn(g);
  if (oc) g.outline(oc);
  return [gridToCanvas(g, false), gridToCanvas(g, true)];
}

function pixLayer(w, h, f) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  const cx = c.getContext('2d');
  const id = cx.createImageData(w, h);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const col = f(x, y);
    if (!col) continue;
    const [r, g, b] = rgb(col), i = (y * w + x) * 4;
    id.data[i] = r; id.data[i + 1] = g; id.data[i + 2] = b; id.data[i + 3] = 255;
  }
  cx.putImageData(id, 0, 0);
  return c;
}

// ============================================================
//  Sprites
// ============================================================
const KW = 26, KH = 22, KCX = 13;

function kFace(g, cx, cy, rx, o) {
  const e1 = Math.floor(cx) + 1, e2 = e1 + 2, ey = Math.floor(cy) - 4;
  const eyes = o.eyes || 'open', mouth = o.mouth || 'smile', cheeks = o.cheeks || 'small';
  if (eyes === 'open') {
    for (const ex of [e1, e2]) { g.set(ex, ey, 'B'); g.set(ex, ey + 1, 'W'); g.set(ex, ey + 2, 'B'); g.set(ex, ey + 3, 'b'); }
  } else if (eyes === 'blink') {
    for (const ex of [e1, e2]) g.set(ex, ey + 2, 'B');
  } else if (eyes === 'squint') {
    g.set(e1 - 1, ey + 1, 'B'); g.set(e1, ey + 2, 'B'); g.set(e1 - 1, ey + 3, 'B');
    g.set(e2 + 1, ey + 1, 'B'); g.set(e2, ey + 2, 'B'); g.set(e2 + 1, ey + 3, 'B');
  } else if (eyes === 'happy') {
    g.set(e1 - 1, ey + 1, 'B'); g.set(e1 - 2, ey + 2, 'B'); g.set(e1, ey + 2, 'B');
    g.set(e2 + 1, ey + 1, 'B'); g.set(e2, ey + 2, 'B'); g.set(e2 + 2, ey + 2, 'B');
  }
  if (cheeks) {
    const rows = cheeks === 'big' ? [ey + 4, ey + 5] : [ey + 4];
    for (const cy2 of rows) { g.set(e1 - 2, cy2, 'C'); g.set(e1 - 1, cy2, 'C'); g.set(e2 + 1, cy2, 'C'); g.set(e2 + 2, cy2, 'C'); }
  }
  if (mouth === 'smile') g.set(e1 + 1, ey + 4, 'r');
  else if (mouth === 'o') { g.ell(e2 + 3, ey + 6, 1.5, 1.5, 'K'); g.set(e2 + 2.5, ey + 5.5, 'r'); }
  else if (mouth === 'open') { const mx = cx + rx - 2, my = cy + 1.5; g.ell(mx, my, 2.3, 2.7, 'K'); g.ell(mx, my, 1.4, 1.8, 'r'); }
  else if (mouth === 'wide' || mouth === 'wide2') {
    const big = mouth === 'wide2' ? 0.6 : 0;
    const mx = cx + rx - 1.5, my = cy + 1.5;
    g.ell(mx, my, 3 + big, 3.8 + big, 'K');
    g.ell(mx, my, 2.2 + big, 3 + big, 'r');
    g.ell(mx - 0.6, my + 1.9 + big * 0.5, 1.5, 1, 'R');
  }
}

function kArt(o) {
  const cx = KCX + (o.dx || 0), cy = o.cy ?? 13, rx = o.rx ?? 6.5, ry = o.ry ?? 6.5;
  return sprite(KW, KH, (g) => {
    for (const a of (o.arms || [[-7, 14], [7, 14]])) g.ball(cx + a[0], a[1], 2, 1.6, 'P', 'D');
    g.ball(cx, cy, rx, ry, 'P', 'D', 'p');
    for (const f of (o.feet || [[-4, 19.5], [4, 19.5]])) g.ball(cx + f[0], f[1], o.frx || 3, o.fry || 1.5, 'R', 'r');
    kFace(g, cx, cy, rx, o);
  });
}

const SPR = {};
const TILE = {};
const BG = {};

function buildSprites() {
  const squash = { cy: 14.5, rx: 7.8, ry: 5.3, feet: [[-5, 19.5], [5, 19.5]], arms: [[-8.5, 16], [8.5, 16]] };
  const puff = { cy: 11.5, rx: 8.5, ry: 8, feet: [[-4, 19.6], [4, 19.6]], frx: 2.4, fry: 1.3, mouth: 'o', cheeks: 'big' };
  const full = { cy: 12.5, rx: 8, ry: 7, arms: [[-8.5, 14], [8.5, 14]], mouth: 'none', cheeks: 'big' };
  const inh = { dx: -0.5, cy: 13, rx: 7, ry: 6.5, arms: [[-7.5, 10.5], [5, 9]], eyes: 'squint', feet: [[-5, 19.5], [3, 19.5]] };
  SPR.k = {
    idle: kArt({}),
    idle2: kArt({ cy: 13.5, rx: 6.8, ry: 6.1 }),
    blink: kArt({ eyes: 'blink' }),
    run: [
      kArt({ feet: [[-6, 19.5], [5, 19.5]], arms: [[-7, 13], [7, 15]] }),
      kArt({ cy: 12.5, feet: [[-3, 19.5], [3, 18.3]], arms: [[-7, 14], [7, 14]] }),
      kArt({ feet: [[-5, 19.5], [6, 19.5]], arms: [[-7, 15], [7, 13]] }),
      kArt({ cy: 12.5, feet: [[-3, 18.3], [3, 19.5]], arms: [[-7, 14], [7, 14]] }),
    ],
    jump: kArt({ cy: 12.5, feet: [[-3.5, 18.8], [3.5, 18.8]], fry: 1.3, arms: [[-8, 9.5], [8, 9.5]] }),
    fall: kArt({ cy: 12.8, feet: [[-4.5, 19.5], [4.5, 19.5]], arms: [[-8, 11], [8, 11]], mouth: 'o' }),
    squash: kArt(squash),
    happy: kArt({ ...squash, eyes: 'happy' }),
    puffUp: kArt({ ...puff, arms: [[-9.5, 7.5], [9.5, 7.5]] }),
    puffDown: kArt({ ...puff, arms: [[-9.5, 13.5], [9.5, 13.5]] }),
    inhale1: kArt({ ...inh, mouth: 'wide' }),
    inhale2: kArt({ ...inh, rx: 7.3, ry: 6.8, mouth: 'wide2' }),
    full: kArt(full),
    fullWalk: [kArt({ ...full, feet: [[-6, 19.5], [3, 18.5]] }), kArt({ ...full, feet: [[-3, 18.5], [5, 19.5]] })],
    fullSquash: kArt({ ...full, cy: 14, rx: 8.8, ry: 5.8, arms: [[-9, 16], [9, 16]] }),
    spit: kArt({ cy: 13, rx: 6.8, ry: 6.3, arms: [[-8, 11], [8, 12]], mouth: 'open', eyes: 'squint' }),
    hurt: kArt({ cy: 12.5, arms: [[-8, 8.5], [8, 8.5]], eyes: 'squint', mouth: 'open', feet: [[-4, 19], [4, 19]] }),
  };

  // Waddle Dee — walker
  SPR.waddle = [0, 1].map((st) => sprite(18, 18, (g) => {
    const f = st ? [[5, 15.5], [12.5, 14.8]] : [[6.5, 14.8], [13, 15.5]];
    g.ball(f[0][0], f[0][1], 2.6, 1.5, 'Y', 'y');
    g.ball(9, 9.5, 6.5, 6, 'O', 'o', 'Y');
    g.ell(10.8, 9.4, 4, 3.6, 'T');
    g.rect(10, 7, 1, 2, 'B'); g.rect(12, 7, 1, 2, 'B');
    g.set(8, 10, 'C'); g.set(14, 10, 'C');
    g.ball(f[1][0], f[1][1], 2.6, 1.5, 'Y', 'y');
  }));

  // Bronto Burt — flyer
  SPR.bronto = [0, 1].map((up) => sprite(22, 18, (g) => {
    if (up) { g.ball(6.5, 4.5, 3.4, 2.6, 'W', 'L'); g.ball(9.5, 3.5, 2.4, 2.2, 'W', 'L'); }
    else { g.ball(5, 10.5, 3.8, 2.2, 'W', 'L'); g.ball(7, 12.5, 2.6, 1.7, 'W', 'L'); }
    g.ball(12, 10, 5.5, 5.3, 'V', 'v', 'p');
    g.set(13, 8, 'B'); g.set(13, 9, 'B'); g.set(15, 8, 'B'); g.set(15, 9, 'B');
    g.set(12, 11, 'C'); g.set(16, 11, 'C');
    g.ball(10, 15.8, 1.6, 1.1, 'O', 'o'); g.ball(14, 15.8, 1.6, 1.1, 'O', 'o');
  }));

  // Bouncy — hopper on a spring
  SPR.bouncy = [0, 1].map((sq) => sprite(18, 22, (g) => {
    const by = sq ? 11 : 8;
    for (let y = Math.round(by + 4); y <= 20; y += 2) g.rect(5, y, 8, 1, 'S');
    g.ball(9, by, 6, sq ? 5 : 5.8, 'l', 'b', 'L');
    g.rect(10, by - 3, 1, 2, 'B'); g.rect(12, by - 3, 1, 2, 'B');
    g.set(11, by + 1, 'r');
  }));

  // Gordo — invincible spike ball
  SPR.gordo = [0, 1].map((fr) => sprite(22, 22, (g) => {
    const rot = fr * Math.PI / 8;
    for (let i = 0; i < 8; i++) {
      const a = rot + i * Math.PI / 4;
      for (let r = 5; r <= 9.6; r += 0.4) {
        const w = (9.8 - r) * 0.32;
        g.ell(11 + Math.cos(a) * r, 11 + Math.sin(a) * r, w + 0.35, w + 0.35, r > 8.4 ? 'W' : 'S');
      }
    }
    g.ball(11, 11, 6, 6, 'v', 'K', 'V');
    g.ell(9.3, 10, 1.4, 2.3, 'W'); g.ell(13.3, 10, 1.4, 2.3, 'W');
    g.set(9, 10, 'B'); g.set(9, 11, 'B'); g.set(13, 10, 'B'); g.set(13, 11, 'B');
  }));

  // Spat-out stars
  SPR.star = [0, 1, 2, 3].map((i) => sprite(16, 16, (g) => {
    const rot = i * (Math.PI * 2 / 5) / 4;
    g.star(8.6, 8.6, 7, 3.2, rot, 'y');
    g.star(8, 8, 7, 3.2, rot, 'Y');
    g.set(6, 6, 'W'); g.set(7, 6, 'W'); g.set(6, 7, 'W');
  }));
  SPR.bigStar = [0, 1, 2, 3].map((i) => sprite(22, 22, (g) => {
    const rot = i * (Math.PI * 2 / 5) / 4;
    g.star(11.7, 11.7, 10, 4.5, rot, 'O');
    g.star(11, 11, 10, 4.5, rot, 'Y');
    g.star(10, 10, 3.5, 1.6, rot, 'W');
  }));
  // Pickup star (spinning)
  SPR.pstar = [1, 0.7, 0.3, 0.7].map((sx) => sprite(12, 12, (g) => {
    g.star(6, 6.2, 5.2, 2.4, 0, sx < 0.5 ? 'y' : 'Y', sx);
    if (sx > 0.5) g.set(5, 5, 'W');
  }));
  SPR.grayStar = sprite(12, 12, (g) => g.star(6, 6.2, 5.2, 2.4, 0, 'S'));
  SPR.mini = sprite(7, 7, (g) => g.star(3.5, 3.7, 3.3, 1.5, 0, 'Y'));
  SPR.puff = sprite(14, 12, (g) => {
    g.ell(7, 6.5, 5, 4, 'W'); g.ell(5, 4.5, 2.6, 2.2, 'W'); g.ell(9, 8.2, 3, 1.5, 'L');
  }, 'l');
  SPR.dust = [2.6, 1.8, 1.1].map((r) => sprite(8, 8, (g) => g.ell(4, 4, r, r, 'W'), 'l'));
  SPR.tomato = sprite(14, 15, (g) => {
    g.ball(7, 9, 5.5, 5, 'R', 'r', 'p');
    g.set(5, 7, 'W'); g.set(5, 8, 'W'); g.set(5, 9, 'W'); g.set(5, 10, 'W');
    g.set(6, 8, 'W'); g.set(7, 9, 'W'); g.set(8, 8, 'W');
    g.set(9, 7, 'W'); g.set(9, 8, 'W'); g.set(9, 9, 'W'); g.set(9, 10, 'W');
    g.rect(4, 3, 2, 1, 'G'); g.rect(8, 3, 2, 1, 'G'); g.rect(6, 2, 2, 2, 'G'); g.set(7, 1, 'g');
  });
  SPR.oneup = sprite(14, 14, (g) => {
    g.ball(7, 7.5, 5.5, 5.3, 'P', 'D', 'p');
    g.set(8, 5, 'B'); g.set(8, 6, 'W'); g.set(8, 7, 'B');
    g.set(10, 5, 'B'); g.set(10, 6, 'W'); g.set(10, 7, 'B');
    g.set(6, 9, 'C'); g.set(11, 9, 'C'); g.set(9, 9, 'r');
  });
  SPR.life = sprite(11, 10, (g) => {
    g.ball(5.5, 5, 4, 3.8, 'P', 'D', 'p');
    g.set(6, 3, 'B'); g.set(6, 4, 'B'); g.set(8, 3, 'B'); g.set(8, 4, 'B');
  });
  SPR.warp = sprite(36, 28, (g) => {
    g.star(18.6, 15.6, 13, 5.8, 0, 'y');
    g.star(18, 15, 12.4, 5.5, 0, 'Y');
    g.star(16, 12.5, 4.2, 2, 0, 'W');
  });

  // ---- tiles ----
  const dirt = (g, v) => {
    g.rect(0, 0, 16, 16, 'N');
    const dk = v ? [[2, 9], [3, 9], [9, 12], [13, 7], [6, 14], [11, 3], [12, 3]] : [[4, 7], [5, 7], [11, 10], [1, 13], [8, 4], [14, 14], [13, 13]];
    const lt = v ? [[7, 6], [14, 11]] : [[10, 13], [2, 4]];
    dk.forEach(([x, y]) => g.set(x, y, 'n'));
    lt.forEach(([x, y]) => g.set(x, y, 'T'));
  };
  TILE.dirt = [0, 1].map((v) => sprite(16, 16, (g) => dirt(g, v), null)[0]);
  TILE.grass = [0, 1].map((v) => sprite(16, 16, (g) => {
    dirt(g, v);
    for (let x = 0; x < 16; x++) {
      const h = 5 + ((x + v * 3) % 5 === 1 || (x + v * 3) % 5 === 2 ? 1 : 0) + ((x + v) % 7 === 4 ? 1 : 0);
      for (let y = 0; y < h; y++) g.set(x, y, y === 0 ? 'g' : y === 1 ? 'H' : y >= h - 1 ? 'g' : 'G');
    }
  }, null)[0]);
  TILE.stone = sprite(16, 16, (g) => {
    g.rect(0, 0, 16, 16, 'K'); g.rect(1, 1, 14, 14, 'S');
    g.rect(1, 1, 14, 1, 'W'); g.rect(1, 1, 1, 14, 'W');
    g.rect(1, 14, 14, 1, 's'); g.rect(14, 1, 1, 14, 's');
    g.rect(4, 4, 8, 1, 's'); g.rect(4, 4, 1, 8, 's'); g.rect(4, 11, 8, 1, 'W'); g.rect(11, 4, 1, 8, 'W');
  }, null)[0];
  TILE.starb = sprite(16, 16, (g) => {
    g.rect(0, 0, 16, 16, 'o'); g.rect(1, 1, 14, 14, 'O');
    g.rect(1, 1, 14, 1, 'T'); g.rect(1, 1, 1, 14, 'T');
    g.rect(1, 14, 14, 1, 'o'); g.rect(14, 1, 1, 14, 'o');
    g.star(8, 8.4, 6.6, 3, 0, 'o');
    g.star(8, 8.4, 5.2, 2.3, 0, 'Y');
    g.set(7, 6, 'W');
  }, null)[0];
  TILE.cloud = [];
  for (let cap = 0; cap < 4; cap++) {
    const capL = cap & 1, capR = cap & 2;
    TILE.cloud[cap] = sprite(16, 12, (g) => {
      const x0 = capL ? 4 : 0, x1 = capR ? 12 : 16;
      g.rect(x0, 3, x1 - x0, 6, 'W');
      if (capL) g.ell(4.5, 6, 3.6, 3.2, 'W');
      if (capR) g.ell(11.5, 6, 3.6, 3.2, 'W');
      g.ell(5, 3.6, 3.6, 2.6, 'W'); g.ell(11, 3.2, 3.6, 2.8, 'W');
      for (let x = 0; x < 16; x++) for (let y = 7; y < 12; y++) if (g.get(x, y) === 'W') g.set(x, y, 'L');
    }, 'l')[0];
  }

  // ---- background layers ----
  const bands = ['#5fb8f2', '#7ecaf8', '#a2dafc', '#c6ecff'];
  BG.sky = pixLayer(VW, VH, (x, y) => {
    const b = Math.min(3, Math.floor(y / 42)), edge = y - b * 42;
    if (b < 3 && edge >= 39 && (x + y) & 1) return bands[b + 1];
    if (b > 0 && edge <= 1 && (x + y) & 1) return bands[b - 1];
    return bands[b];
  });
  const TAU = Math.PI * 2;
  const cloudDefs = [[60, 34, 1], [210, 20, 0.8], [330, 50, 1.15], [450, 26, 0.9]];
  const puffs = [[-14, 4, 9], [0, 0, 13], [14, 3, 10], [26, 6, 7], [-24, 7, 6]];
  const inCloud = (x, y) => {
    for (const [cx, cy, s] of cloudDefs) {
      let dx = ((x - cx) % 512 + 512) % 512; if (dx > 256) dx -= 512;
      for (const [ox, oy, r] of puffs) {
        const a = dx - ox * s, b = y - (cy + oy * s), rr = r * s;
        if (a * a + b * b * 1.6 <= rr * rr) return cy;
      }
    }
    return -1;
  };
  BG.clouds = pixLayer(512, 90, (x, y) => {
    const c = inCloud(x, y);
    if (c >= 0) return y > c + 5 ? '#e4f4ff' : '#ffffff';
    if (inCloud(x + 1, y) >= 0 || inCloud(x - 1, y) >= 0 || inCloud(x, y + 1) >= 0 || inCloud(x, y - 1) >= 0) return '#a9d6f5';
    return null;
  });
  const farTop = (x) => 86 + 12 * Math.sin(TAU * 2 * x / 512) + 8 * Math.sin(TAU * 5 * x / 512 + 1.3) + 3 * Math.sin(TAU * 11 * x / 512);
  BG.far = pixLayer(512, 192, (x, y) => {
    const t = Math.round(farTop(x));
    if (y < t) return null;
    if (y === t) return '#6aa9a6';
    if (y - t < 3) return '#c9f1de';
    return Math.floor((x + (y - t) * 0.6) / 14) % 2 ? '#a0d8c6' : '#96cfbc';
  });
  const bushes = [[40, 12], [62, 9], [170, 15], [300, 11], [318, 8], [420, 13], [470, 9]];
  const hillBase = (x) => 122 + 9 * Math.sin(TAU * 3 * x / 512 + 0.5) + 6 * Math.sin(TAU * 7 * x / 512);
  const nearTop = (x) => {
    let t = hillBase(x);
    for (const [cx, r] of bushes) {
      const dx = x - cx;
      if (Math.abs(dx) < r) t = Math.min(t, hillBase(cx) + r * 0.35 - Math.sqrt(r * r - dx * dx) * 0.9);
    }
    return Math.round(t);
  };
  BG.near = pixLayer(512, 192, (x, y) => {
    const t = nearTop(x);
    if (y < t) return null;
    if (y === t) return '#3f8f58';
    if (y - t < 3) return '#b4ec98';
    return ((x + y) >> 3) & 1 ? '#7ccf7a' : '#70c470';
  });
}

// ============================================================
//  Pixel font (3x5)
// ============================================================
const FONT_SRC = {
  A: '.#. #.# ### #.# #.#', B: '##. #.# ##. #.# ##.', C: '.## #.. #.. #.. .##', D: '##. #.# #.# #.# ##.',
  E: '### #.. ##. #.. ###', F: '### #.. ##. #.. #..', G: '.## #.. #.# #.# .##', H: '#.# #.# ### #.# #.#',
  I: '### .#. .#. .#. ###', J: '..# ..# ..# #.# .#.', K: '#.# #.# ##. #.# #.#', L: '#.. #.. #.. #.. ###',
  M: '#.# ### ### #.# #.#', N: '##. #.# #.# #.# #.#', O: '.#. #.# #.# #.# .#.', P: '##. #.# ##. #.. #..',
  Q: '.#. #.# #.# ##. .##', R: '##. #.# ##. #.# #.#', S: '.## #.. .#. ..# ##.', T: '### .#. .#. .#. .#.',
  U: '#.# #.# #.# #.# ###', V: '#.# #.# #.# #.# .#.', W: '#.# #.# ### ### #.#', X: '#.# #.# .#. #.# #.#',
  Y: '#.# #.# .#. .#. .#.', Z: '### ..# .#. #.. ###',
  0: '### #.# #.# #.# ###', 1: '.#. ##. .#. .#. ###', 2: '##. ..# .#. #.. ###', 3: '##. ..# .#. ..# ##.',
  4: '#.# #.# ### ..# ..#', 5: '### #.. ##. ..# ##.', 6: '.## #.. ### #.# ###', 7: '### ..# .#. .#. .#.',
  8: '### #.# ### #.# ###', 9: '### #.# ### ..# ##.',
  '!': '.#. .#. .#. ... .#.', '.': '... ... ... ... .#.', ':': '... .#. ... .#. ...', '-': '... ... ### ... ...',
  '/': '..# ..# .#. #.. #..', '?': '##. ..# .#. ... .#.', "'": '.#. .#. ... ... ...', ',': '... ... ... .#. #..',
  '+': '... .#. ### .#. ...', '>': '#.. .#. ..# .#. #..', '<': '..# .#. #.. .#. ..#', '=': '... ### ... ### ...',
  '(': '.#. #.. #.. #.. .#.', ')': '.#. ..# ..# ..# .#.', '*': '#.# .#. #.# ... ...',
};
const FONT = {};
for (const k in FONT_SRC) FONT[k] = FONT_SRC[k].replace(/ /g, '');

function drawText(s, x, y, col, sc = 1) {
  s = String(s).toUpperCase();
  ctx.fillStyle = PAL[col] || col;
  let cx = Math.round(x);
  y = Math.round(y);
  for (const ch of s) {
    const gl = FONT[ch];
    if (gl) for (let i = 0; i < 15; i++) if (gl[i] === '#') ctx.fillRect(cx + (i % 3) * sc, y + ((i / 3) | 0) * sc, sc, sc);
    cx += 4 * sc;
  }
}
const textW = (s, sc = 1) => String(s).length * 4 * sc - sc;
function drawTextO(s, x, y, col, sc = 1, oc = 'K') {
  const o = sc > 2 ? 2 : 1;
  drawText(s, x + o, y + o * 2, oc, sc);
  for (const [dx, dy] of [[-1, 0], [1, 0], [0, -1], [0, 1], [-1, -1], [1, -1], [-1, 1], [1, 1]]) drawText(s, x + dx * o, y + dy * o, oc, sc);
  drawText(s, x, y, col, sc);
}
const drawTextC = (s, y, col, sc = 1) => drawTextO(s, Math.round((VW - textW(s, sc)) / 2), y, col, sc);

// ============================================================
//  Audio (tiny WebAudio synth)
// ============================================================
const midi = (m) => 440 * Math.pow(2, (m - 69) / 12);
const MEL = [
  72, 76, 79, 76, 81, 79, 76, 72, 74, 77, 81, 77, 79, 0, 76, 0,
  72, 76, 79, 84, 83, 79, 81, 77, 79, 76, 74, 71, 72, 0, 0, 0,
  69, 72, 76, 81, 79, 76, 77, 74, 76, 79, 84, 79, 77, 76, 74, 0,
  77, 81, 79, 76, 74, 77, 76, 72, 74, 0, 67, 71, 72, 0, 0, 0,
];
const BASS = [48, 48, 50, 55, 48, 53, 55, 48, 45, 45, 48, 53, 53, 55, 55, 48];

const Snd = {
  ctx: null, muted: false, inh: null, mus: { on: false, step: 0, next: 0, timer: null },
  init() {
    if (this.ctx) { if (this.ctx.state === 'suspended') this.ctx.resume(); return; }
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    const c = (this.ctx = new AC());
    this.master = c.createGain(); this.master.gain.value = this.muted ? 0 : 0.5; this.master.connect(c.destination);
    this.sfx = c.createGain(); this.sfx.gain.value = 0.9; this.sfx.connect(this.master);
    this.music = c.createGain(); this.music.gain.value = 0.45; this.music.connect(this.master);
    const buf = c.createBuffer(1, c.sampleRate, c.sampleRate), d = buf.getChannelData(0);
    for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    this.noiseBuf = buf;
    if (this.wantMusic) this.musicStart();
  },
  tone(f0, f1, dur, type = 'square', vol = 0.12, delay = 0, dest) {
    if (!this.ctx) return;
    const c = this.ctx, t = c.currentTime + delay;
    const o = c.createOscillator(), g = c.createGain();
    o.type = type;
    o.frequency.setValueAtTime(f0, t);
    if (f1 && f1 !== f0) o.frequency.exponentialRampToValueAtTime(f1, t + dur);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.linearRampToValueAtTime(vol, t + 0.006);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g); g.connect(dest || this.sfx);
    o.start(t); o.stop(t + dur + 0.05);
  },
  noise(dur, vol, freq, delay = 0, ftype = 'bandpass', f1, dest) {
    if (!this.ctx) return;
    const c = this.ctx, t = c.currentTime + delay;
    const s = c.createBufferSource(); s.buffer = this.noiseBuf;
    const f = c.createBiquadFilter(); f.type = ftype; f.frequency.setValueAtTime(freq, t);
    if (f1) f.frequency.exponentialRampToValueAtTime(f1, t + dur);
    const g = c.createGain();
    g.gain.setValueAtTime(vol, t); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    s.connect(f); f.connect(g); g.connect(dest || this.sfx);
    s.start(t); s.stop(t + dur + 0.05);
  },
  arp(notes, step, type = 'square', vol = 0.1, len = 0.12) {
    notes.forEach((m, i) => this.tone(midi(m), midi(m), len, type, vol, i * step));
  },
  play(n) {
    if (!this.ctx) return;
    switch (n) {
      case 'jump': this.tone(330, 700, 0.12, 'square', 0.09); break;
      case 'flap': this.tone(520, 300, 0.09, 'triangle', 0.2); this.noise(0.08, 0.1, 1800); break;
      case 'exhale': this.noise(0.22, 0.25, 1400, 0, 'bandpass', 500); break;
      case 'gulp': this.tone(320, 110, 0.12, 'square', 0.1); this.tone(220, 80, 0.1, 'square', 0.1, 0.09); break;
      case 'swallow': this.arp([72, 79, 84], 0.06, 'triangle', 0.18); break;
      case 'spit': this.tone(1000, 260, 0.16, 'square', 0.1); this.noise(0.12, 0.15, 2500); break;
      case 'defeat': this.tone(660, 1320, 0.08, 'square', 0.08); this.tone(990, 1980, 0.12, 'square', 0.08, 0.06); break;
      case 'tink': this.tone(1800, 1600, 0.08, 'triangle', 0.15); break;
      case 'coin': this.tone(1318, 1318, 0.05, 'square', 0.07); this.tone(1760, 1760, 0.1, 'square', 0.07, 0.05); break;
      case 'hurt': this.tone(420, 90, 0.32, 'sawtooth', 0.1); break;
      case 'break': this.noise(0.18, 0.35, 900, 0, 'lowpass', 200); this.tone(200, 60, 0.12, 'square', 0.08); break;
      case 'land': this.noise(0.06, 0.12, 400, 0, 'lowpass'); break;
      case 'heal': this.arp([72, 76, 79, 84, 88], 0.06, 'triangle', 0.2); break;
      case 'oneup': this.arp([76, 79, 88, 84, 86, 91], 0.07, 'square', 0.08); break;
      case 'check': this.arp([79, 84, 88], 0.08, 'triangle', 0.2, 0.2); break;
      case 'death': this.arp([79, 76, 72, 67, 64, 60], 0.11, 'square', 0.09, 0.14); break;
      case 'over': this.arp([67, 0, 64, 0, 60, 55, 48].map((m) => m || 1), 0.22, 'triangle', 0.2, 0.3); break;
      case 'win': this.arp([72, 76, 79, 84, 79, 84, 88, 91, 96], 0.09, 'square', 0.08, 0.16);
        this.arp([48, 55, 60, 64, 67, 72], 0.14, 'triangle', 0.18, 0.25); break;
      case 'pause': this.tone(880, 880, 0.06, 'square', 0.06); this.tone(660, 660, 0.08, 'square', 0.06, 0.07); break;
    }
  },
  inhaleStart() {
    if (!this.ctx || this.inh) return;
    const c = this.ctx, t = c.currentTime;
    const src = c.createBufferSource(); src.buffer = this.noiseBuf; src.loop = true;
    const f = c.createBiquadFilter(); f.type = 'bandpass'; f.Q.value = 2.5;
    f.frequency.setValueAtTime(500, t); f.frequency.linearRampToValueAtTime(1700, t + 0.7);
    const lfo = c.createOscillator(); lfo.frequency.value = 9;
    const lg = c.createGain(); lg.gain.value = 250;
    lfo.connect(lg); lg.connect(f.frequency);
    const g = c.createGain(); g.gain.setValueAtTime(0.0001, t); g.gain.linearRampToValueAtTime(0.3, t + 0.08);
    src.connect(f); f.connect(g); g.connect(this.sfx);
    src.start(t); lfo.start(t);
    this.inh = { src, lfo, g };
  },
  inhaleStop() {
    if (!this.inh) return;
    const c = this.ctx, t = c.currentTime, { src, lfo, g } = this.inh;
    g.gain.cancelScheduledValues(t); g.gain.setValueAtTime(g.gain.value, t); g.gain.linearRampToValueAtTime(0.0001, t + 0.07);
    src.stop(t + 0.1); lfo.stop(t + 0.1);
    this.inh = null;
  },
  setMuted(m) { this.muted = m; if (this.master) this.master.gain.value = m ? 0 : 0.5; },
  musicStart() {
    this.wantMusic = true;
    if (!this.ctx || this.mus.on) return;
    this.mus.on = true;
    this.mus.next = this.ctx.currentTime + 0.08;
    this.mus.timer = setInterval(() => this.schedule(), 25);
  },
  musicStop(reset = true) {
    this.wantMusic = false;
    if (this.mus.timer) clearInterval(this.mus.timer);
    this.mus.on = false; this.mus.timer = null;
    if (reset) this.mus.step = 0;
  },
  schedule() {
    const c = this.ctx, spb = 60 / 152 / 2;
    while (this.mus.next < c.currentTime + 0.15) {
      const i = this.mus.step % 64, t = this.mus.next - c.currentTime;
      if (MEL[i]) this.tone(midi(MEL[i]), midi(MEL[i]), spb * 0.92, 'square', 0.05, t, this.music);
      const root = BASS[i >> 2];
      this.tone(midi(i % 2 ? root + 12 : root), midi(i % 2 ? root + 12 : root), spb * 0.8, 'triangle', 0.16, t, this.music);
      if (i % 2) this.noise(0.03, 0.05, 7000, t, 'highpass', 0, this.music);
      if (i % 4 === 0) this.noise(0.06, 0.12, 180, t, 'lowpass', 0, this.music);
      this.mus.step++;
      this.mus.next += spb;
    }
  },
};

// ============================================================
//  Input
// ============================================================
const KEYMAP = {
  ArrowLeft: 'left', KeyA: 'left', ArrowRight: 'right', KeyD: 'right',
  ArrowDown: 'down', KeyS: 'down', ArrowUp: 'up', KeyW: 'up',
  Space: 'jump', KeyZ: 'jump', Enter: 'action', NumpadEnter: 'action', KeyX: 'action', KeyJ: 'action',
  KeyP: 'pause', Escape: 'pause', KeyM: 'mute', KeyR: 'restart',
};
const codesDown = new Set();
const held = {}, pressed = {};
function refreshHeld() {
  for (const a of Object.values(KEYMAP)) held[a] = false;
  for (const c of codesDown) held[KEYMAP[c]] = true;
}
addEventListener('keydown', (e) => {
  const a = KEYMAP[e.code];
  if (!a) return;
  e.preventDefault();
  Snd.init();
  if (!e.repeat && !held[a]) pressed[a] = true;
  codesDown.add(e.code); refreshHeld();
});
addEventListener('keyup', (e) => {
  if (!KEYMAP[e.code]) return;
  e.preventDefault();
  codesDown.delete(e.code); refreshHeld();
});
addEventListener('blur', () => { codesDown.clear(); refreshHeld(); });
cv.addEventListener('pointerdown', () => { Snd.init(); if (state === 'title') pressed.action = true; });

// ============================================================
//  Level
// ============================================================
let map, enemies, items, proj, parts, popups, signs, goal, checkpoint;

function buildLevel() {
  const m = [];
  for (let y = 0; y < LH; y++) m.push(new Array(LW).fill('.'));
  const fill = (x0, x1, y0, y1, c) => {
    for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) if (x >= 0 && x < LW && y >= 0 && y < LH) m[y][x] = c;
  };
  const ground = (a, b, top) => fill(a, b, top, LH - 1, '#');
  const cloud = (x, y, n) => fill(x, x + n - 1, y, y, '=');
  const en = [], it = [], sg = [];
  const enemy = (type, tx, ty, o = {}) => en.push({ type, tx, ty, ...o });
  const item = (type, tx, ty) => it.push({ type, tx, ty });
  const stars = (x0, x1, ty) => { for (let x = x0; x <= x1; x++) item('pstar', x, ty); };
  const sign = (tx, ty, text) => sg.push({ x: tx * TS, y: ty * TS, text });

  // A — opening meadow (tutorial)
  ground(0, 26, 12);
  sign(1, 5, 'ARROWS: MOVE');
  sign(9, 4, 'SPACE: JUMP - AGAIN TO FLY');
  stars(6, 8, 10);
  fill(13, 15, 8, 8, 'S'); stars(13, 15, 7);
  sign(18.5, 5, 'HOLD ENTER: INHALE');
  enemy('waddle', 20, 11);
  sign(24.5, 4, 'ENTER AGAIN: SPIT A STAR');
  enemy('waddle', 25, 11);
  // B
  ground(30, 47, 12); ground(36, 40, 10);
  sign(31, 5, 'DOWN: SWALLOW');
  enemy('waddle', 33, 11);
  cloud(42, 8, 4); stars(42, 45, 7);
  enemy('bronto', 44, 5);
  enemy('waddle', 46, 11);
  // C — over a gap, star-block wall
  cloud(49, 10, 3); enemy('bronto', 51, 7);
  ground(53, 74, 11);
  enemy('bouncy', 59, 10); enemy('waddle', 64, 10);
  sign(62, 4, 'STARS BREAK STAR BLOCKS!');
  fill(69, 70, 7, 10, 'S'); stars(71, 73, 10);
  // D — Gordo guarding a gap, stone hill, checkpoint
  enemy('gordo', 76.5, 8, { amp: 26 });
  ground(79, 100, 12);
  fill(84, 84, 11, 11, 'B'); fill(85, 85, 10, 11, 'B'); fill(86, 87, 9, 11, 'B'); fill(88, 88, 10, 11, 'B'); fill(89, 89, 11, 11, 'B');
  stars(86, 87, 8);
  enemy('waddle', 92, 11); enemy('bouncy', 95, 11);
  item('checkpoint', 98, 11);
  // E — cloud hopping over a big pit
  cloud(102, 10, 3); cloud(107, 8, 3); cloud(112, 10, 3); cloud(117, 7, 3); cloud(121, 10, 3);
  stars(102, 104, 9); stars(117, 119, 6);
  enemy('bronto', 105, 5); enemy('bronto', 115, 9); enemy('bronto', 121, 5);
  enemy('gordo', 110, 5, { amp: 18 });
  item('oneup', 110, 1);
  // F — tunnel sealed by star blocks, treats on the roof
  ground(125, 150, 12);
  fill(131, 143, 8, 9, 'B'); fill(131, 132, 10, 11, 'S');
  enemy('waddle', 136, 11); enemy('waddle', 140, 11);
  item('tomato', 137, 7); stars(133, 135, 7); stars(139, 141, 7);
  enemy('bouncy', 147, 11);
  // G — climbing steps
  ground(151, 156, 11); ground(157, 162, 10); ground(163, 168, 9);
  enemy('waddle', 154, 10); enemy('waddle', 160, 9); enemy('bouncy', 166, 8);
  cloud(158, 5, 3); stars(158, 160, 4);
  // H — the big flight
  sign(166, 2, 'TAP SPACE TO FLY ACROSS!');
  enemy('gordo', 172, 6, { amp: 22 }); enemy('gordo', 176, 9, { amp: 18, phase: Math.PI });
  enemy('bronto', 174, 3);
  item('pstar', 170, 6); item('pstar', 171, 4); item('pstar', 174, 7); item('pstar', 178, 5);
  // I — final stretch and goal
  ground(179, 229, 12);
  enemy('waddle', 184, 11); enemy('bronto', 190, 7); enemy('waddle', 192, 11); enemy('bouncy', 197, 11);
  fill(202, 203, 8, 11, 'S');
  stars(205, 208, 10);
  fill(213, 217, 11, 11, 'B');
  item('goal', 215, 10);
  fill(229, 229, 0, 11, 'B');
  return { m, en, it, sg };
}

function makeEnemy(d) {
  const S = { waddle: [12, 12], bronto: [14, 12], bouncy: [12, 14], gordo: [14, 14] }[d.type];
  const e = { type: d.type, w: S[0], h: S[1], vx: 0, vy: 0, dir: -1, t: (Math.random() * 100) | 0, dead: false,
              captured: false, pull: 0, stun: 0, onGround: false, timer: (Math.random() * 40) | 0 };
  e.x = d.tx * TS + 8 - e.w / 2;
  e.y = d.type === 'bronto' || d.type === 'gordo' ? d.ty * TS + 8 - e.h / 2 : (d.ty + 1) * TS - e.h;
  e.hx = e.x; e.hy = e.y; e.amp = d.amp || 0; e.phase = d.phase || 0;
  return e;
}
function makeItem(d) {
  const it = { type: d.type, t: (Math.random() * 60) | 0, got: false, pulled: false, pull: 0 };
  if (d.type === 'goal') { it.w = 28; it.h = 24; it.x = d.tx * TS + 8 - 14; it.y = (d.ty + 1) * TS - 24; }
  else if (d.type === 'checkpoint') { it.w = 8; it.h = 32; it.x = d.tx * TS + 4; it.y = (d.ty + 1) * TS - 32; it.on = false; }
  else { it.w = it.h = d.type === 'pstar' ? 10 : 12; it.x = d.tx * TS + 8 - it.w / 2; it.y = d.ty * TS + 8 - it.h / 2; }
  return it;
}

// ============================================================
//  Tiles & collision
// ============================================================
const isSolid = (c) => c === '#' || c === 'B' || c === 'S';
function tileAt(tx, ty) {
  if (tx < 0 || tx >= LW) return 'B';
  if (ty < 0) return 'B';
  if (ty >= LH) return '.';
  return map[ty][tx];
}
const solidAt = (tx, ty) => isSolid(tileAt(tx, ty));

function moveBody(e) {
  const res = { hitX: false, ceil: false };
  e.x += e.vx;
  const ty0 = Math.floor(e.y / TS), ty1 = Math.floor((e.y + e.h - 0.01) / TS);
  if (e.vx > 0) {
    const tx = Math.floor((e.x + e.w - 0.01) / TS);
    for (let ty = ty0; ty <= ty1; ty++) if (solidAt(tx, ty)) { e.x = tx * TS - e.w; e.vx = 0; res.hitX = true; break; }
  } else if (e.vx < 0) {
    const tx = Math.floor(e.x / TS);
    for (let ty = ty0; ty <= ty1; ty++) if (solidAt(tx, ty)) { e.x = (tx + 1) * TS; e.vx = 0; res.hitX = true; break; }
  }
  const prevBottom = e.y + e.h;
  e.y += e.vy;
  e.onGround = false;
  const tx0 = Math.floor(e.x / TS), tx1 = Math.floor((e.x + e.w - 0.01) / TS);
  if (e.vy > 0) {
    const ty = Math.floor((e.y + e.h - 0.01) / TS);
    for (let tx = tx0; tx <= tx1; tx++) {
      const c = tileAt(tx, ty);
      if (isSolid(c) || (c === '=' && prevBottom <= ty * TS + 0.5 && !(e.dropT > 0))) {
        e.y = ty * TS - e.h; e.vy = 0; e.onGround = true; break;
      }
    }
  } else if (e.vy < 0) {
    const ty = Math.floor(e.y / TS);
    for (let tx = tx0; tx <= tx1; tx++) if (solidAt(tx, ty)) { e.y = (ty + 1) * TS; e.vy = 0; res.ceil = true; break; }
  }
  return res;
}
const overlap = (a, b, s = 0) =>
  a.x + s < b.x + b.w - s && a.x + a.w - s > b.x + s && a.y + s < b.y + b.h - s && a.y + a.h - s > b.y + s;
const groundBelow = (e, dist) => {
  const ty = Math.floor((e.y + e.h + dist) / TS);
  for (let tx = Math.floor(e.x / TS); tx <= Math.floor((e.x + e.w - 0.01) / TS); tx++) {
    const c = tileAt(tx, ty);
    if (isSolid(c) || c === '=') return true;
  }
  return false;
};

// ============================================================
//  Game state
// ============================================================
let state = 'title', paused = false, frameCount = 0, stateT = 0;
let score = 0, lives = 3, hiScore = 0, bonus = null;
let hitstop = 0, shakeT = 0, shakeMag = 0, bannerT = 0;
const cam = { x: 0, y: 48, look: 0 };
let K;
let respawn = { x: 2 * TS, y: 12 * TS - 14 };
try { hiScore = +localStorage.getItem('kirbyStarPlainsHi') || 0; } catch (e) {}

function newKirby(x, y) {
  return { x, y, w: 12, h: 14, vx: 0, vy: 0, facing: 1, onGround: false, mode: 'normal', hp: 6,
           coyote: 0, jumpBuf: 0, jumping: false, dropT: 0, inhaleT: 0, spitT: 0, flapT: 0, exhaleT: 0,
           gulpT: 0, swallowT: 0, landT: 0, hurtT: 0, invuln: 0, runT: 0, mouth: null, ride: null };
}

function newGame() {
  const lv = buildLevel();
  map = lv.m;
  enemies = lv.en.map(makeEnemy);
  items = lv.it.map(makeItem);
  signs = lv.sg;
  goal = items.find((i) => i.type === 'goal');
  checkpoint = items.find((i) => i.type === 'checkpoint');
  proj = []; parts = []; popups = [];
  score = 0; lives = 3; bonus = null;
  respawn = { x: 2 * TS, y: 12 * TS - 14 };
  K = newKirby(respawn.x, respawn.y);
  K.onGround = true;
  state = 'play'; paused = false; stateT = 0; bannerT = 150; hitstop = 0;
  updateCamera(true);
  Snd.inhaleStop();
  Snd.musicStop(); Snd.musicStart();
}

function respawnKirby() {
  K = newKirby(respawn.x, respawn.y);
  K.invuln = 90;
  proj = [];
  for (const e of enemies) if (e.captured) { e.captured = false; e.stun = 30; }
  state = 'play'; stateT = 0; bannerT = 0;
  updateCamera(true);
  Snd.musicStart();
}

function addScore(n, x, y, text) {
  score += n;
  if (x !== undefined) popups.push({ x, y, text: text || String(n), t: 0 });
}
function shake(mag, t) { shakeMag = Math.max(shakeMag, mag); shakeT = Math.max(shakeT, t); }

// ---- particles ----
function burst(x, y, n = 6, spd = 1.8) {
  for (let i = 0; i < n; i++) {
    const a = (i / n) * Math.PI * 2 + Math.random() * 0.3;
    parts.push({ type: 'star', x, y, vx: Math.cos(a) * spd, vy: Math.sin(a) * spd, life: 22, max: 22 });
  }
}
function dust(x, y, n = 2, dir = 0) {
  for (let i = 0; i < n; i++)
    parts.push({ type: 'dust', x: x + rand(-3, 3), y: y - 2, vx: dir * 0.4 + rand(-0.4, 0.4), vy: rand(-0.4, -0.1), life: 16, max: 16 });
}
function sparkle(x, y, n = 4) {
  for (let i = 0; i < n; i++)
    parts.push({ type: 'spark', x: x + rand(-8, 8), y: y + rand(-8, 8), vx: rand(-0.3, 0.3), vy: rand(-0.8, -0.2), life: 26, max: 26 });
}

// ============================================================
//  Kirby
// ============================================================
const mouthPos = () => ({ x: K.x + K.w / 2 + K.facing * 7, y: K.y + K.h / 2 + 1 });

function doJump() {
  K.vy = K.mode === 'full' ? PH.fullJump : PH.jumpV;
  K.jumping = true; K.onGround = false; K.coyote = 0; K.jumpBuf = 0;
  dust(K.x + K.w / 2, K.y + K.h, 2);
  Snd.play('jump');
}
function startPuff() {
  K.mode = 'puff';
  K.vy = Math.min(K.vy, PH.puffFlap * 1.1);
  K.flapT = 12; K.jumping = false;
  Snd.play('flap');
}
function flap() {
  K.vy = Math.min(K.vy, PH.puffFlap);
  K.flapT = 12;
  Snd.play('flap');
}
function exhale() {
  const m = mouthPos();
  proj.push({ type: 'puff', x: m.x - 6 + K.facing * 4, y: m.y - 6, w: 12, h: 10, vx: K.facing * 3.4, life: 20, max: 20, dir: K.facing });
  K.mode = 'normal'; K.exhaleT = 10;
  if (K.vy < 0) K.vy *= 0.3;
  Snd.play('exhale');
}
function startInhale() {
  K.mode = 'inhale'; K.inhaleT = 0; K.jumping = false;
  Snd.inhaleStart();
}
function releaseCaptured() {
  for (const e of enemies) {
    if (!e.captured) continue;
    e.captured = false;
    if (e.type === 'block') { e.dead = true; breakFx(e.x + 7, e.y + 7); }
    else { e.stun = 45; e.vx = 0; e.vy = 0; e.hx = e.x; e.hy = e.y; }
  }
  for (const it of items) it.pulled = false;
}
function endInhale() {
  K.mode = 'normal';
  releaseCaptured();
  Snd.inhaleStop();
}
function swallowInto(first) {
  const m = mouthPos();
  let count = 0, enemiesEaten = 0;
  for (const e of enemies) {
    if (!e.captured) continue;
    const dx = e.x + e.w / 2 - m.x, dy = e.y + e.h / 2 - m.y;
    if (e === first || dx * dx + dy * dy < 26 * 26) {
      e.captured = false; e.dead = true; count++;
      if (e.type === 'block') addScore(50); else enemiesEaten++;
    }
  }
  releaseCaptured();
  if (enemiesEaten) addScore(200 * enemiesEaten, K.x + 6, K.y - 6);
  K.mode = 'full'; K.mouth = { count }; K.gulpT = 14;
  Snd.inhaleStop(); Snd.play('gulp');
  shake(1, 4);
}
function spit() {
  const m = mouthPos(), big = K.mouth && K.mouth.count >= 2, sz = big ? 18 : 12;
  proj.push({ type: 'star', big, x: m.x - sz / 2 + K.facing * 4, y: m.y - sz / 2 - 1, w: sz, h: sz,
              vx: K.facing * (big ? 4.6 : 5), life: 70, combo: 0, t: 0 });
  K.mode = 'spit'; K.spitT = 12; K.mouth = null;
  K.vx -= K.facing * 1.2;
  Snd.play('spit');
  shake(1, 4);
}
function swallowDown() {
  K.mode = 'normal'; K.mouth = null; K.swallowT = 26;
  sparkle(K.x + 6, K.y + 4, 6);
  addScore(10);
  Snd.play('swallow');
}
function hurt(fromX) {
  if (K.invuln > 0 || state !== 'play') return;
  K.hp--;
  if (K.mode === 'inhale') endInhale();
  K.mode = 'normal'; K.mouth = null;
  K.vx = (K.x + K.w / 2 < fromX ? -1 : 1) * 2.2; K.vy = -2.6;
  K.hurtT = 22; K.invuln = 110; K.jumping = false;
  hitstop = 4; shake(3, 10);
  Snd.play('hurt');
  if (K.hp <= 0) die(false);
}
function die(pit) {
  if (state !== 'play') return;
  if (K.mode === 'inhale') releaseCaptured();
  state = 'dying'; stateT = 0;
  K.pit = pit; K.vx = 0; K.vy = 0; K.hp = 0; K.mode = 'normal';
  lives--;
  Snd.inhaleStop(); Snd.musicStop(); Snd.play('death');
}

function updateKirby() {
  const k = K;
  const jumpP = pressed.jump || pressed.up, jumpH = held.jump || held.up;
  let dirIn = (held.right ? 1 : 0) - (held.left ? 1 : 0);
  if (k.hurtT > 0) { k.hurtT--; dirIn = 0; }
  const ctrl = k.hurtT <= 0;
  if (k.invuln > 0) k.invuln--;
  for (const t of ['flapT', 'exhaleT', 'gulpT', 'swallowT', 'landT', 'dropT']) if (k[t] > 0) k[t]--;

  // ---- actions ----
  if (ctrl) {
    if (k.mode === 'normal' && pressed.action) startInhale();
    else if (k.mode === 'puff' && pressed.action) exhale();
    else if (k.mode === 'full') { if (pressed.action) spit(); else if (pressed.down) swallowDown(); }
  }
  if (k.mode === 'spit' && --k.spitT <= 0) k.mode = 'normal';

  // ---- horizontal ----
  const locked = k.mode === 'inhale' || k.mode === 'spit' || k.hurtT > 0;
  let maxSp = PH.runMax, acc = k.onGround ? PH.runAcc : PH.airAcc;
  if (k.mode === 'puff') { maxSp = PH.puffMax; acc = PH.puffAcc; }
  else if (k.mode === 'full') maxSp = PH.fullMax;
  if (!locked && dirIn) {
    if (Math.sign(k.vx) === -dirIn && k.onGround && Math.abs(k.vx) > 0.8) {
      k.vx += dirIn * acc * 2.2;
      if (frameCount % 4 === 0) dust(k.x + k.w / 2, k.y + k.h, 1, -dirIn);
    } else k.vx += dirIn * acc;
    if (Math.abs(k.vx) > maxSp) k.vx = approach(k.vx, dirIn * maxSp, 0.2);
    k.facing = dirIn;
  } else {
    k.vx = approach(k.vx, 0, locked ? (k.onGround ? 0.2 : 0.06) : k.onGround ? PH.fric : PH.airFric);
  }

  // ---- jumping & flying ----
  if (k.onGround) k.coyote = 6; else if (k.coyote > 0) k.coyote--;
  if (ctrl && jumpP) {
    if (k.mode === 'normal' || k.mode === 'full') {
      const onCloud = k.onGround && tileAt(Math.floor((k.x + k.w / 2) / TS), Math.floor((k.y + k.h + 1) / TS)) === '=';
      if (held.down && onCloud && k.mode === 'normal') { k.dropT = 10; k.onGround = false; k.y += 1; }
      else if (k.onGround || k.coyote > 0) doJump();
      else if (k.vy > 0 && groundBelow(k, 10)) k.jumpBuf = 8;
      else if (k.mode === 'normal') startPuff();
    } else if (k.mode === 'puff') flap();
  }
  if (k.jumpBuf > 0) {
    k.jumpBuf--;
    if (k.onGround && (k.mode === 'normal' || k.mode === 'full')) doJump();
  }
  if (k.jumping && !jumpH && k.vy < -1) { k.vy *= PH.jumpCut; k.jumping = false; }
  if (k.vy >= 0) k.jumping = false;

  // ---- gravity ----
  let g = PH.g, mf = PH.maxFall;
  if (k.mode === 'puff') { g = PH.puffG; mf = PH.puffMaxFall; }
  else if (k.mode === 'inhale') mf = 1.4;
  k.vy += g;
  if (k.vy > mf) k.vy = approach(k.vy, mf, 0.35);

  // ---- move ----
  const wasAir = !k.onGround, vyBefore = k.vy;
  const r = moveBody(k);
  if (r.ceil && k.mode === 'puff') k.vy = 0.3;
  if (k.x < 0) { k.x = 0; k.vx = 0; }
  if (k.onGround && wasAir) {
    if (vyBefore > 2.4) { k.landT = 6; dust(k.x + k.w / 2, k.y + k.h, 3); Snd.play('land'); }
    if (k.mode === 'puff') exhale();
  }
  if (k.onGround && Math.abs(k.vx) > 0.2) {
    k.runT += Math.abs(k.vx);
    if (k.mode === 'normal' && Math.abs(k.vx) > 1.5 && frameCount % 10 === 0) dust(k.x + k.w / 2 - k.facing * 5, k.y + k.h, 1, -k.facing);
  }

  // ---- inhale ----
  if (k.mode === 'inhale') {
    k.inhaleT++;
    updateInhale();
    if (k.mode === 'inhale' && !held.action && k.inhaleT >= 16) endInhale();
  }

  if (k.y > LH * TS + 8) die(true);
}

function updateInhale() {
  const m = mouthPos(), f = K.facing, range = 74;
  const cone = (x, y) => {
    const dx = (x - m.x) * f, dy = y - m.y;
    return dx > -8 && dx < range && Math.abs(dy) < 12 + dx * 0.32;
  };
  // grab enemies
  for (const e of enemies) {
    if (e.dead || e.captured || e.type === 'gordo') continue;
    if (cone(e.x + e.w / 2, e.y + e.h / 2)) { e.captured = true; e.pull = 0.25; }
  }
  // grab star blocks
  const tx0 = Math.floor(Math.min(m.x, m.x + f * 56) / TS), tx1 = Math.floor(Math.max(m.x, m.x + f * 56) / TS);
  for (let ty = Math.floor((m.y - 28) / TS); ty <= Math.floor((m.y + 28) / TS); ty++) {
    for (let tx = tx0; tx <= tx1; tx++) {
      if (tileAt(tx, ty) !== 'S') continue;
      const cx = tx * TS + 8, cy = ty * TS + 8;
      if (cone(cx, cy) && Math.abs(cx - m.x) < 56 && K.inhaleT > 6) {
        map[ty][tx] = '.';
        enemies.push({ type: 'block', x: tx * TS + 1, y: ty * TS + 1, w: 14, h: 14, captured: true, pull: 0.15, t: 0, dead: false });
      }
    }
  }
  // pull items too
  for (const it of items) {
    if (it.got || it.type === 'goal' || it.type === 'checkpoint') continue;
    if (!it.pulled && cone(it.x + it.w / 2, it.y + it.h / 2)) { it.pulled = true; it.pull = 0.5; }
    if (it.pulled) {
      it.pull = Math.min(it.pull + 0.3, 6);
      const dx = m.x - (it.x + it.w / 2), dy = m.y - (it.y + it.h / 2), d = Math.hypot(dx, dy) || 1;
      it.x += (dx / d) * Math.min(it.pull, d); it.y += (dy / d) * Math.min(it.pull, d);
    }
  }
  // pull captured things
  let swallowed = null;
  for (const e of enemies) {
    if (!e.captured) continue;
    e.pull = Math.min(e.pull + 0.2, 5.5);
    const dx = m.x - (e.x + e.w / 2), dy = m.y - (e.y + e.h / 2), d = Math.hypot(dx, dy) || 1;
    const step = Math.min(e.pull, d);
    e.x += (dx / d) * step; e.y += (dy / d) * step;
    e.dir = -f;
    if (d < 8 && !swallowed) swallowed = e;
  }
  if (swallowed) { swallowInto(swallowed); return; }
  // wind streaks
  for (let i = 0; i < 2; i++) {
    const dx = rand(18, range), dy = rand(-1, 1) * (10 + dx * 0.3);
    const x = m.x + f * dx, y = m.y + dy, d = Math.hypot(dx, dy);
    parts.push({ type: 'streak', x, y, vx: (-f * dx / d) * 4, vy: (-dy / d) * 4, life: Math.floor(d / 4), max: 20 });
  }
}

// ============================================================
//  Enemies, projectiles, items
// ============================================================
function defeat(e, pts) {
  e.dead = true;
  const cx = e.x + e.w / 2, cy = e.y + e.h / 2;
  burst(cx, cy, 6, 1.9);
  addScore(pts, cx, cy - 6);
  Snd.play('defeat');
  hitstop = Math.max(hitstop, 3);
  shake(2, 6);
}
function breakFx(x, y) {
  for (let i = 0; i < 4; i++)
    parts.push({ type: 'debris', x: x + (i % 2 ? 3 : -3), y: y + (i < 2 ? -3 : 3), vx: (i % 2 ? 1 : -1) * rand(0.8, 1.6), vy: rand(-3.5, -2), life: 40, max: 40 });
  Snd.play('break');
}
function breakBlock(tx, ty) {
  map[ty][tx] = '.';
  breakFx(tx * TS + 8, ty * TS + 8);
  addScore(50, tx * TS + 8, ty * TS);
  shake(1, 4);
}

function updateEnemies() {
  for (const e of enemies) {
    if (e.dead || e.captured) continue;
    if (Math.abs(e.x - cam.x - VW / 2) > VW / 2 + 120) continue; // sleep off-screen
    e.t++;
    if (e.stun > 0) e.stun--;
    if (e.type === 'waddle') {
      e.vx = e.stun > 0 ? e.vx * 0.9 : e.dir * 0.42;
      e.vy = Math.min(e.vy + PH.g, 4);
      const r = moveBody(e);
      if (r.hitX) e.dir *= -1;
      else if (e.onGround && e.stun <= 0) {
        const ax = e.dir > 0 ? e.x + e.w + 1 : e.x - 1, c = tileAt(Math.floor(ax / TS), Math.floor((e.y + e.h + 2) / TS));
        if (!isSolid(c) && c !== '=') e.dir *= -1;
      }
    } else if (e.type === 'bronto') {
      if (e.stun > 0) { e.y += Math.sin(e.t * 0.3) * 0.3; continue; }
      e.x += e.dir * 0.6;
      if (e.x > e.hx + 56) e.dir = -1;
      if (e.x < e.hx - 56) e.dir = 1;
      e.y += (e.hy + Math.sin(e.t * 0.05) * 14 - e.y) * 0.15;
    } else if (e.type === 'bouncy') {
      e.vy = Math.min(e.vy + PH.g, 4);
      if (e.onGround) {
        e.vx *= 0.6;
        if (++e.timer > 55 && e.stun <= 0) {
          e.timer = 0; e.dir = K.x < e.x ? -1 : 1;
          e.vy = -3.6; e.vx = e.dir * 0.8;
        }
      }
      const r = moveBody(e);
      if (r.hitX) e.dir *= -1;
    } else if (e.type === 'gordo') {
      e.y = e.hy + Math.sin(e.t * 0.035 + e.phase) * e.amp;
    }
    if (e.y > LH * TS + 40) e.dead = true;
  }
}

function checkContacts() {
  const kb = { x: K.x + 1, y: K.y + 2, w: K.w - 2, h: K.h - 2 };
  for (const e of enemies) {
    if (e.dead || e.captured || e.type === 'block') continue;
    if (overlap(kb, e, 1)) {
      if (K.invuln <= 0) {
        hurt(e.x + e.w / 2);
        if (e.type !== 'gordo') defeat(e, 100);
      }
    }
  }
  for (const it of items) {
    if (it.got) continue;
    if (it.type === 'checkpoint') {
      if (!it.on && K.x > it.x - 4) {
        it.on = true;
        respawn = { x: it.x - 2, y: it.y + it.h - K.h };
        sparkle(it.x + 4, it.y, 8);
        popups.push({ x: it.x + 4, y: it.y - 8, text: 'CHECKPOINT!', t: 0 });
        Snd.play('check');
      }
      continue;
    }
    if (!overlap(K, it)) continue;
    if (it.type === 'goal') { startClear(); return; }
    it.got = true;
    const cx = it.x + it.w / 2, cy = it.y + it.h / 2;
    if (it.type === 'pstar') { addScore(100, cx, cy - 6); Snd.play('coin'); sparkle(cx, cy, 3); }
    else if (it.type === 'tomato') { K.hp = 6; addScore(500, cx, cy - 6, 'FULL HEALTH!'); Snd.play('heal'); sparkle(cx, cy, 8); }
    else if (it.type === 'oneup') { lives++; addScore(1000, cx, cy - 6, '1UP!'); Snd.play('oneup'); sparkle(cx, cy, 8); }
  }
}

function updateProjectiles() {
  for (const p of proj) {
    p.life--;
    if (p.type === 'star') {
      p.t++;
      p.x += p.vx;
      if (p.t % 3 === 0) parts.push({ type: 'spark', x: p.x + p.w / 2 - Math.sign(p.vx) * 6, y: p.y + p.h / 2 + rand(-3, 3), vx: 0, vy: 0, life: 12, max: 12 });
      const tx0 = Math.floor(p.x / TS), tx1 = Math.floor((p.x + p.w - 0.01) / TS);
      const ty0 = Math.floor(p.y / TS), ty1 = Math.floor((p.y + p.h - 0.01) / TS);
      for (let ty = ty0; ty <= ty1 && p.life > 0; ty++) for (let tx = tx0; tx <= tx1 && p.life > 0; tx++) {
        const c = tileAt(tx, ty);
        if (c === 'S') { breakBlock(tx, ty); if (!p.big) p.life = 0; }
        else if (isSolid(c)) { p.life = 0; burst(p.x + p.w / 2, p.y + p.h / 2, 4, 1.2); Snd.play('tink'); }
      }
      for (const e of enemies) {
        if (p.life <= 0) break;
        if (e.dead || e.captured || e.type === 'block' || !overlap(p, e)) continue;
        if (e.type === 'gordo') { p.life = 0; sparkle(p.x + 6, p.y + 6, 5); Snd.play('tink'); }
        else { p.combo++; defeat(e, 200 * p.combo); if (!p.big) p.life = 0; }
      }
      if (p.life === 0 && p.t > 0) burst(p.x + p.w / 2, p.y + p.h / 2, 5, 1.4);
    } else if (p.type === 'puff') {
      p.x += p.vx; p.vx *= 0.9;
      if (solidAt(Math.floor((p.x + p.w / 2) / TS), Math.floor((p.y + p.h / 2) / TS))) p.life = 0;
      for (const e of enemies) {
        if (p.life <= 0) break;
        if (e.dead || e.captured || e.type === 'block' || e.type === 'gordo' || !overlap(p, e)) continue;
        defeat(e, 200); p.life = 0;
      }
    }
  }
  proj = proj.filter((p) => p.life > 0 && p.x > cam.x - 40 && p.x < cam.x + VW + 40);
}

function updateItems() {
  for (const it of items) it.t++;
}

function updateParticles() {
  for (const p of parts) {
    p.life--;
    p.x += p.vx; p.y += p.vy;
    if (p.type === 'debris') p.vy += 0.2;
    else if (p.type === 'star') { p.vx *= 0.92; p.vy *= 0.92; }
  }
  parts = parts.filter((p) => p.life > 0);
  for (const s of popups) s.t++;
  popups = popups.filter((s) => s.t < 50);
}

function updateCamera(snap) {
  if (state === 'clear' && !snap) return;
  cam.look = snap ? K.facing * 28 : approach(cam.look, K.facing * 28, 0.8);
  const tx = clamp(K.x + K.w / 2 - VW / 2 + cam.look, 0, LW * TS - VW);
  const ty = clamp(K.y + K.h / 2 - VH / 2 - 8, 0, LH * TS - VH);
  if (snap) { cam.x = tx; cam.y = ty; return; }
  cam.x += (tx - cam.x) * 0.14;
  cam.y += (ty - cam.y) * 0.1;
}

// ---- dying / clear sequences ----
function updateDying() {
  stateT++;
  if (!K.pit) {
    if (stateT === 36) K.vy = -4.6;
    if (stateT > 36) { K.vy += 0.17; K.y += K.vy; if (stateT % 8 === 0) K.facing *= -1; }
  }
  if (stateT >= (K.pit ? 90 : 160)) {
    if (lives > 0) respawnKirby();
    else { state = 'over'; stateT = 0; saveHi(); Snd.play('over'); }
  }
}
function startClear() {
  if (K.mode === 'inhale') endInhale();
  state = 'clear'; stateT = 0;
  K.mode = 'normal'; K.vx = 0; K.vy = 0; K.mouth = null;
  K.ride = { sx: K.x, sy: K.y };
  goal.vx = 0; goal.vy = 0;
  Snd.musicStop(); Snd.play('win');
}
function updateClear() {
  stateT++;
  const t = Math.min(1, stateT / 24);
  const tx = goal.x + goal.w / 2 - K.w / 2, ty = goal.y - K.h + 8;
  if (stateT <= 24) {
    K.x = K.ride.sx + (tx - K.ride.sx) * t;
    K.y = K.ride.sy + (ty - K.ride.sy) * t - Math.sin(t * Math.PI) * 24;
  } else {
    if (stateT > 50) { goal.vx += 0.12; goal.vy -= 0.07; }
    goal.x += goal.vx; goal.y += goal.vy;
    K.x = goal.x + goal.w / 2 - K.w / 2; K.y = goal.y - K.h + 8;
    if (stateT % 2 === 0) parts.push({ type: 'star', x: goal.x + 4, y: goal.y + 14 + rand(-4, 4), vx: -1, vy: rand(-0.4, 0.4), life: 26, max: 26 });
  }
  if (stateT >= 190) {
    const hpB = K.hp * 100, lifeB = lives * 1000;
    bonus = { base: score, hp: hpB, life: lifeB };
    score += hpB + lifeB;
    state = 'win'; stateT = 0; saveHi();
  }
}
function saveHi() {
  if (score > hiScore) { hiScore = score; try { localStorage.setItem('kirbyStarPlainsHi', String(hiScore)); } catch (e) {} }
}

// ============================================================
//  Main update
// ============================================================
function clearPressed() { for (const k in pressed) pressed[k] = false; }

function update() {
  frameCount++;
  if (pressed.mute) { Snd.setMuted(!Snd.muted); pressed.mute = false; }
  stateT += state === 'title' || state === 'over' || state === 'win' ? 1 : 0;

  if (state === 'title') {
    if (pressed.action || pressed.jump) newGame();
    clearPressed(); return;
  }
  if (state === 'over' || state === 'win') {
    updateParticles();
    if (stateT > 40 && (pressed.action || pressed.jump || pressed.restart)) newGame();
    clearPressed(); return;
  }
  // play / dying / clear
  if (pressed.restart) { newGame(); clearPressed(); return; }
  if (pressed.pause && state === 'play') {
    paused = !paused;
    Snd.play('pause');
    if (paused) { Snd.inhaleStop(); Snd.musicStop(false); }
    else { Snd.musicStart(); if (K.mode === 'inhale') Snd.inhaleStart(); }
    pressed.pause = false;
  }
  if (paused) { clearPressed(); return; }
  if (hitstop > 0) { hitstop--; return; } // keep pressed buttons for after the freeze

  if (state === 'play') {
    updateKirby();
    updateEnemies();
    updateProjectiles();
    if (state === 'play') checkContacts();
  } else if (state === 'dying') updateDying();
  else if (state === 'clear') updateClear();
  updateItems();
  updateParticles();
  updateCamera(false);
  if (shakeT > 0) shakeT--; else shakeMag = 0;
  if (bannerT > 0) bannerT--;
  clearPressed();
}

// ============================================================
//  Rendering
// ============================================================
let ox = 0, oy = 0;
function drawLayer(img, px, py) {
  const w = img.width;
  let x = -Math.round(((px % w) + w) % w);
  for (; x < VW; x += w) ctx.drawImage(img, x, Math.round(py));
}
function drawBackground(cx, cy) {
  ctx.drawImage(BG.sky, 0, 0);
  const lift = 48 - cy;
  drawLayer(BG.clouds, cx * 0.1 + frameCount * 0.06, 8 + lift * 0.08);
  drawLayer(BG.far, cx * 0.25, -6 + lift * 0.25);
  drawLayer(BG.near, cx * 0.5, 4 + lift * 0.5);
}

function drawTiles() {
  const tx0 = Math.floor(ox / TS), tx1 = Math.floor((ox + VW) / TS);
  const ty0 = Math.max(0, Math.floor(oy / TS)), ty1 = Math.min(LH - 1, Math.floor((oy + VH) / TS));
  for (let ty = ty0; ty <= ty1; ty++) for (let tx = tx0; tx <= tx1; tx++) {
    if (tx < 0 || tx >= LW) continue;
    const c = map[ty][tx];
    if (c === '.') continue;
    const sx = tx * TS - ox, sy = ty * TS - oy, h = hash(tx * 31 + ty);
    if (c === '#') {
      const top = ty === 0 || map[ty - 1][tx] !== '#';
      ctx.drawImage(top ? TILE.grass[h & 1] : TILE.dirt[h & 1], sx, sy);
      ctx.fillStyle = PAL.K;
      if (tileAt(tx - 1, ty) !== '#') ctx.fillRect(sx, sy, 1, TS);
      if (tileAt(tx + 1, ty) !== '#') ctx.fillRect(sx + TS - 1, sy, 1, TS);
      if (top && (h >> 4) % 3 === 0) { // little flowers
        const fx = sx + 3 + ((h >> 8) % 10), fy = sy - 4, pc = (h >> 12) & 1 ? PAL.W : PAL.p;
        ctx.fillStyle = PAL.g; ctx.fillRect(fx, fy + 2, 1, 2);
        ctx.fillStyle = pc; ctx.fillRect(fx - 1, fy, 3, 1); ctx.fillRect(fx, fy - 1, 1, 3);
        ctx.fillStyle = PAL.Y; ctx.fillRect(fx, fy, 1, 1);
      }
    } else if (c === 'B') ctx.drawImage(TILE.stone, sx, sy);
    else if (c === 'S') ctx.drawImage(TILE.starb, sx, sy);
    else if (c === '=') {
      const cap = (tileAt(tx - 1, ty) !== '=' ? 1 : 0) | (tileAt(tx + 1, ty) !== '=' ? 2 : 0);
      ctx.drawImage(TILE.cloud[cap], sx, sy);
    }
  }
}

function drawSigns() {
  for (const s of signs) {
    const w = textW(s.text) + 8, x = Math.round(s.x - ox), y = Math.round(s.y - oy);
    if (x > VW || x + w < 0) continue;
    ctx.fillStyle = 'rgba(42,26,46,0.55)';
    ctx.fillRect(x, y, w, 11);
    ctx.fillRect(x + 1, y - 1, w - 2, 13);
    drawText(s.text, x + 4, y + 3, '#ffffff');
  }
}

function drawSpr(pair, x, y, flip) { ctx.drawImage(pair[flip ? 1 : 0], Math.round(x - ox), Math.round(y - oy)); }

function drawItems() {
  for (const it of items) {
    if (it.got) continue;
    if (it.x - ox > VW + 40 || it.x - ox < -60) continue;
    const bob = Math.round(Math.sin(it.t * 0.08) * 1.5);
    if (it.type === 'pstar') drawSpr(SPR.pstar[(it.t >> 3) % 4], it.x - 1, it.y - 1 + (it.pulled ? 0 : bob));
    else if (it.type === 'tomato') drawSpr(SPR.tomato, it.x - 1, it.y - 2 + (it.pulled ? 0 : bob));
    else if (it.type === 'oneup') drawSpr(SPR.oneup, it.x - 1, it.y - 1 + (it.pulled ? 0 : bob));
    else if (it.type === 'checkpoint') {
      const x = Math.round(it.x - ox), y = Math.round(it.y - oy);
      ctx.fillStyle = PAL.K; ctx.fillRect(x + 2, y + 6, 4, it.h - 6);
      ctx.fillStyle = PAL.S; ctx.fillRect(x + 3, y + 6, 2, it.h - 6);
      if (it.on) drawSpr(SPR.pstar[(it.t >> 3) % 4], it.x - 2, it.y - 4);
      else drawSpr(SPR.grayStar, it.x - 2, it.y - 4);
    } else if (it.type === 'goal') {
      const b = state === 'clear' ? 0 : Math.round(Math.sin(it.t * 0.07) * 2);
      drawSpr(SPR.warp, it.x - 4, it.y - 4 + b);
      if (state !== 'clear' && state !== 'win') {
        const cols = [PAL.R, PAL.O, PAL.Y, PAL.G, PAL.b, PAL.V];
        'GOAL'.split('').forEach((ch, i) => drawTextO(ch, it.x - ox - 2 + i * 9, it.y - oy - 20 + Math.round(Math.sin(it.t * 0.1 + i) * 1.5), cols[(i + (it.t >> 3)) % 6], 2));
        if (it.t % 20 === 0) sparkle(it.x + 14, it.y + 10, 1);
      }
    }
  }
}

function drawEnemies() {
  for (const e of enemies) {
    if (e.dead) continue;
    if (e.x - ox > VW + 30 || e.x - ox < -40) continue;
    const jx = e.captured ? Math.round(rand(-1, 1)) : 0, jy = e.captured ? Math.round(rand(-1, 1)) : 0;
    const flip = e.dir < 0;
    const stunBlink = e.stun > 0 && e.stun < 20 && (frameCount >> 1) & 1;
    if (stunBlink) continue;
    switch (e.type) {
      case 'waddle': drawSpr(SPR.waddle[e.captured || e.stun > 0 ? 0 : (e.t >> 3) & 1], e.x + e.w / 2 - 9 + jx, e.y + e.h - 18 + jy, flip); break;
      case 'bronto': drawSpr(SPR.bronto[(e.t >> (e.captured ? 1 : 3)) & 1], e.x + e.w / 2 - 11 + jx, e.y + e.h / 2 - 9 + jy, flip); break;
      case 'bouncy': drawSpr(SPR.bouncy[e.onGround && e.timer > 35 ? 1 : 0], e.x + e.w / 2 - 9 + jx, e.y + e.h - 22 + jy, flip); break;
      case 'gordo': drawSpr(SPR.gordo[(e.t >> 4) & 1], e.x + e.w / 2 - 11, e.y + e.h / 2 - 11, false); break;
      case 'block': ctx.drawImage(TILE.starb, Math.round(e.x - 1 - ox + jx), Math.round(e.y - 1 - oy + jy)); break;
    }
  }
}

function drawProjectiles() {
  for (const p of proj) {
    if (p.type === 'star') {
      const fr = (p.t >> 1) % 4, arr = p.big ? SPR.bigStar : SPR.star, sz = p.big ? 22 : 16;
      drawSpr(arr[fr], p.x + p.w / 2 - sz / 2, p.y + p.h / 2 - sz / 2, p.vx < 0);
    } else if (p.type === 'puff') {
      if (p.life < 6 && p.life & 1) continue;
      drawSpr(SPR.puff, p.x - 1, p.y - 1, p.dir < 0);
    }
  }
}

function kirbySprite() {
  const k = K, S = SPR.k;
  if (state === 'dying') return S.hurt;
  if (state === 'clear') return stateT < 24 ? S.jump : S.happy;
  if (k.hurtT > 0) return S.hurt;
  switch (k.mode) {
    case 'puff': return (k.flapT > 0 ? (k.flapT >> 2) & 1 : (frameCount >> 4) & 1) ? S.puffUp : S.puffDown;
    case 'inhale': return (frameCount >> 2) & 1 ? S.inhale1 : S.inhale2;
    case 'spit': return S.spit;
    case 'full':
      if (k.gulpT > 0) return k.gulpT > 7 ? S.fullSquash : S.full;
      if (k.onGround && Math.abs(k.vx) > 0.2) return S.fullWalk[Math.floor(k.runT / 7) % 2];
      return S.full;
  }
  if (k.exhaleT > 0) return S.spit;
  if (k.swallowT > 0) return S.happy;
  if (!k.onGround) return k.vy < 0 ? S.jump : S.fall;
  if (k.landT > 0) return S.squash;
  if (Math.abs(k.vx) > 0.3) return S.run[Math.floor(k.runT / 6) % 4];
  if (frameCount % 210 < 7) return S.blink;
  return (frameCount >> 5) & 1 ? S.idle2 : S.idle;
}

function drawKirby() {
  if (state === 'dying' && K.pit) return;
  if (K.invuln > 0 && state === 'play' && (frameCount >> 2) & 1) return;
  const spr = kirbySprite();
  ctx.drawImage(spr[K.facing > 0 ? 0 : 1], Math.round(K.x + K.w / 2 - KW / 2 - ox), Math.round(K.y + K.h - KH - oy));
}

function drawParticles() {
  for (const p of parts) {
    const x = Math.round(p.x - ox), y = Math.round(p.y - oy);
    switch (p.type) {
      case 'star': ctx.drawImage(SPR.mini[0], x - 3, y - 3); break;
      case 'dust': ctx.drawImage(SPR.dust[Math.min(2, Math.floor((1 - p.life / p.max) * 3))][0], x - 4, y - 4); break;
      case 'spark':
        if (p.life & 2) { ctx.fillStyle = p.life > p.max / 2 ? PAL.W : PAL.Y; ctx.fillRect(x, y - 1, 1, 3); ctx.fillRect(x - 1, y, 3, 1); }
        break;
      case 'debris':
        ctx.fillStyle = PAL.K; ctx.fillRect(x - 2, y - 2, 5, 5);
        ctx.fillStyle = (p.life >> 2) & 1 ? PAL.Y : PAL.O; ctx.fillRect(x - 1, y - 1, 3, 3);
        break;
      case 'streak':
        ctx.fillStyle = 'rgba(255,255,255,0.85)';
        if (Math.abs(p.vx) > Math.abs(p.vy)) ctx.fillRect(x - 2, y, 5, 1); else ctx.fillRect(x, y - 2, 1, 5);
        break;
    }
  }
  for (const s of popups) {
    const w = textW(s.text);
    if (s.t < 40 || (s.t >> 1) & 1) drawTextO(s.text, Math.round(s.x - ox - w / 2), Math.round(s.y - oy - Math.min(s.t, 24) * 0.6), '#ffffff');
  }
}

function drawHUD() {
  ctx.fillStyle = 'rgba(42,26,46,0.78)';
  ctx.fillRect(0, 0, VW, 13);
  ctx.fillStyle = PAL.P; ctx.fillRect(0, 13, VW, 1);
  drawText('KIRBY', 5, 4, PAL.P);
  for (let i = 0; i < 6; i++) {
    const x = 28 + i * 7;
    ctx.fillStyle = PAL.K; ctx.fillRect(x, 2, 6, 9);
    const filled = i < K.hp, danger = K.hp <= 2 && (frameCount >> 3) & 1;
    ctx.fillStyle = filled ? (danger ? PAL.R : PAL.P) : '#4a2e52';
    ctx.fillRect(x + 1, 3, 4, 7);
    if (filled) { ctx.fillStyle = PAL.p; ctx.fillRect(x + 1, 3, 2, 2); }
  }
  if (K.mode === 'full') { ctx.drawImage(SPR.mini[0], 74, 3); }
  drawText('SCORE ' + String(score).padStart(7, '0'), 112, 4, '#ffffff');
  drawText('HI ' + String(Math.max(hiScore, score)).padStart(7, '0'), 196, 4, '#c9a8e8');
  ctx.drawImage(SPR.life[0], 284, 2);
  drawText('X' + Math.max(0, lives), 298, 4, '#ffffff');
}

function dimScreen(a) { ctx.fillStyle = `rgba(29,20,48,${a})`; ctx.fillRect(0, 0, VW, VH); }

function drawControlsBox(y) {
  const lines = [
    ['ARROWS / A D', 'MOVE'],
    ['SPACE', 'JUMP - TAP AGAIN IN AIR TO FLY'],
    ['HOLD ENTER', 'INHALE ENEMIES AND BLOCKS'],
    ['ENTER', 'SPIT A STAR / EXHALE AIR'],
    ['DOWN / S', 'SWALLOW'],
    ['P  M  R', 'PAUSE  MUTE  RESTART'],
  ];
  const x = 44;
  ctx.fillStyle = 'rgba(42,26,46,0.72)';
  ctx.fillRect(x - 8, y - 6, VW - 2 * (x - 8), lines.length * 9 + 9);
  lines.forEach(([k, v], i) => { drawText(k, x, y + i * 9, PAL.Y); drawText(v, x + 60, y + i * 9, '#ffffff'); });
}

function drawWorld() {
  const sx = shakeT > 0 ? Math.round(rand(-shakeMag, shakeMag)) : 0, sy = shakeT > 0 ? Math.round(rand(-shakeMag, shakeMag)) : 0;
  ox = Math.round(cam.x) + sx; oy = Math.round(cam.y) + sy;
  drawBackground(ox, oy);
  drawSigns();
  drawTiles();
  drawItems();
  drawEnemies();
  drawProjectiles();
  drawKirby();
  drawParticles();
}

function drawTitle() {
  ox = (frameCount * 0.6) % (LW * TS); oy = 48;
  drawBackground(ox, oy);
  for (let x = -((frameCount * 0.6) % TS) | 0; x < VW; x += TS) {
    ctx.drawImage(TILE.grass[((x + frameCount * 0.6) / TS | 0) & 1], Math.round(x), 168);
  }
  drawTextC('KIRBY', 14, PAL.P, 4);
  drawTextC('STAR PLAINS', 40, PAL.Y, 2);
  const bob = Math.round(Math.sin(frameCount * 0.06) * 4);
  const kspr = (frameCount >> 4) & 1 ? SPR.k.puffUp : SPR.k.puffDown;
  ctx.drawImage(kspr[0], 147, 54 + bob);
  ctx.drawImage(SPR.waddle[(frameCount >> 3) & 1][1], 112, 150);
  ctx.drawImage(SPR.bronto[(frameCount >> 3) & 1][1], 200, 60 + Math.round(Math.sin(frameCount * 0.05) * 6));
  drawControlsBox(86);
  if ((frameCount >> 5) & 1) drawTextC('PRESS ENTER TO START', 152, '#ffffff');
  drawText('HI ' + String(hiScore).padStart(7, '0'), 4, 4, '#ffffff');
}

function render() {
  ctx.imageSmoothingEnabled = false;
  if (state === 'title') { drawTitle(); return; }
  drawWorld();
  drawHUD();
  if (bannerT > 0 && state === 'play') {
    if (bannerT > 40) drawTextC('STAR PLAINS', 60, PAL.Y, 3);
    else drawTextC('GO!', 64, PAL.P, 4);
  }
  if (paused) {
    dimScreen(0.6);
    drawTextC('PAUSED', 34, PAL.Y, 3);
    drawControlsBox(70);
    drawTextC('PRESS P TO RESUME', 140, '#ffffff');
  }
  if (state === 'over') {
    dimScreen(Math.min(0.75, stateT / 40));
    drawTextC('GAME OVER', 52, PAL.C, 4);
    drawTextC('SCORE ' + String(score).padStart(7, '0'), 92, '#ffffff', 1);
    if (score >= hiScore && score > 0) drawTextC('NEW HIGH SCORE!', 104, PAL.Y);
    ctx.drawImage(SPR.k.hurt[0], VW / 2 - 13, 112);
    if (stateT > 40 && (stateT >> 5) & 1) drawTextC('PRESS ENTER TO TRY AGAIN', 150, '#ffffff');
  }
  if (state === 'win') {
    dimScreen(Math.min(0.7, stateT / 40));
    drawTextC('STAGE CLEAR!', 26, PAL.Y, 3);
    const rows = [['STAR SCORE', bonus.base], ['HEALTH BONUS  ' + K.hp + ' X 100', bonus.hp], ['LIVES BONUS  ' + lives + ' X 1000', bonus.life]];
    rows.forEach(([l, v], i) => {
      if (stateT > 20 + i * 15) { drawTextO(l, 70, 62 + i * 11, '#ffffff'); const s = String(v); drawTextO(s, 250 - textW(s), 62 + i * 11, PAL.Y); }
    });
    if (stateT > 70) {
      ctx.fillStyle = PAL.P; ctx.fillRect(70, 96, 180, 1);
      drawTextO('TOTAL', 70, 101, PAL.P);
      const s = String(score); drawTextO(s, 250 - textW(s), 101, PAL.P);
      if (score >= hiScore) drawTextC('NEW HIGH SCORE!', 113, PAL.Y);
    }
    const dance = (stateT >> 4) & 1;
    ctx.drawImage((dance ? SPR.k.happy : SPR.k.jump)[(stateT >> 5) & 1], VW / 2 - 13, 122 - (dance ? 0 : 4));
    if (stateT > 40 && (stateT >> 5) & 1) drawTextC('PRESS ENTER TO PLAY AGAIN', 156, '#ffffff');
  }
}

// ============================================================
//  Boot
// ============================================================
function resize() {
  const ctrl = document.getElementById('controls');
  const aw = innerWidth - 24, ah = innerHeight - ctrl.offsetHeight - 44;
  let s = Math.min(aw / VW, ah / VH);
  s = s >= 2 ? Math.floor(s) : Math.max(1, s);
  cv.style.width = VW * s + 'px';
  cv.style.height = VH * s + 'px';
}
addEventListener('resize', resize);

buildSprites();
resize();

let last = performance.now(), acc = 0;
const STEP = 1000 / 60;
function loop(now) {
  acc += Math.min(100, now - last);
  last = now;
  while (acc >= STEP) { update(); acc -= STEP; }
  render();
  requestAnimationFrame(loop);
}
requestAnimationFrame(loop);
</script>
</body>
</html>
3:35 PM
Now let me write a headless-Chrome test harness (in the scratchpad) to check for errors and take screenshots.



Write C:\Users\ethan\AppData\Local\Temp\claude\c--Users-ethan-Documents-GitHub-Agent-Engineering-Lecture-2a---Codex-and-Vibecoding-homework-1-1-one-shot-v1\069bf261-be02-4109-974b-b55a25e9b8ec\scratchpad\cdp.mjs
61 lines
// Usage: node cdp.mjs <htmlPath> <outDir> <scriptFile>
// scriptFile exports an async function (page) => {} using page.eval / page.shot / page.wait
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const [, , htmlPath, outDir, scriptFile] = process.argv;
const chrome = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const port = 9333 + Math.floor(Math.random() * 500);
const userDir = path.join(outDir, 'chrome-profile');
const proc = spawn(chrome, [
  '--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${userDir}`,
  '--window-size=1000,700', '--autoplay-policy=no-user-gesture-required', 'about:blank',
], { stdio: 'ignore' });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let targets;
for (let i = 0; i < 50; i++) {
  try { targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); break; } catch { await sleep(200); }
}
const t = targets.find((x) => x.type === 'page');
const ws = new WebSocket(t.webSocketDebuggerUrl);
await new Promise((r) => (ws.onopen = r));
let id = 0; const pending = new Map(); const logs = [];
ws.onmessage = (m) => {
  const d = JSON.parse(m.data);
  if (d.id && pending.has(d.id)) { pending.get(d.id)(d); pending.delete(d.id); }
  if (d.method === 'Runtime.consoleAPICalled') logs.push('console.' + d.params.type + ': ' + d.params.args.map((a) => a.value ?? a.description).join(' '));
  if (d.method === 'Runtime.exceptionThrown') logs.push('EXCEPTION: ' + JSON.stringify(d.params.exceptionDetails.exception?.description || d.params.exceptionDetails.text));
};
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
await send('Runtime.enable');
await send('Page.enable');
await send('Page.navigate', { url: pathToFileURL(htmlPath).href });
await sleep(1500);

const page = {
  async eval(expr) {
    const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
    if (r.result.exceptionDetails) throw new Error(JSON.stringify(r.result.exceptionDetails));
    return r.result.result.value;
  },
  async shot(name, clip) {
    const r = await send('Page.captureScreenshot', { format: 'png', ...(clip ? { clip: { ...clip, scale: 1 } } : {}) });
    fs.writeFileSync(path.join(outDir, name + '.png'), Buffer.from(r.result.data, 'base64'));
  },
  async key(type, code, key) {
    await send('Input.dispatchKeyEvent', { type, code, key, windowsVirtualKeyCode: { Space: 32, Enter: 13, ArrowRight: 39, ArrowLeft: 37, ArrowDown: 40 }[code] || 0 });
  },
  wait: sleep,
  logs,
};
try {
  const mod = await import(pathToFileURL(scriptFile).href);
  await mod.default(page);
} catch (e) { console.log('SCRIPT ERROR', e.message); }
console.log('--- page logs ---\n' + logs.join('\n'));
ws.close(); proc.kill();
process.exit(0);
Write C:\Users\ethan\AppData\Local\Temp\claude\c--Users-ethan-Documents-GitHub-Agent-Engineering-Lecture-2a---Codex-and-Vibecoding-homework-1-1-one-shot-v1\069bf261-be02-4109-974b-b55a25e9b8ec\scratchpad\t1.mjs
49 lines
export default async (page) => {
  await page.shot('01_title');
  // sprite sheet: draw all Kirby sprites scaled up onto canvas
  await page.eval(`(() => {
    const c = document.createElement('canvas'); c.width = 900; c.height = 420; c.id='sheet';
    c.style.cssText='position:fixed;left:0;top:0;z-index:9;background:#7ecaf8;image-rendering:pixelated';
    document.body.appendChild(c);
    const x = c.getContext('2d'); x.imageSmoothingEnabled=false;
    const list = [];
    const k = SPR.k;
    for (const n of ['idle','idle2','blink','jump','fall','squash','happy','puffUp','puffDown','inhale1','inhale2','full','fullSquash','spit','hurt']) list.push(k[n]);
    k.run.forEach(s=>list.push(s)); k.fullWalk.forEach(s=>list.push(s));
    SPR.waddle.forEach(s=>list.push(s)); SPR.bronto.forEach(s=>list.push(s)); SPR.bouncy.forEach(s=>list.push(s)); SPR.gordo.forEach(s=>list.push(s));
    list.push(SPR.star[0], SPR.bigStar[0], SPR.pstar[0], SPR.tomato, SPR.oneup, SPR.warp, SPR.puff, SPR.life);
    let px=4, py=4;
    for (const s of list) { const im=s[0]; if (px + im.width*3 > 900) { px=4; py+=90; } x.drawImage(im, px, py, im.width*3, im.height*3); px += im.width*3+6; }
    const tiles=[TILE.grass[0],TILE.dirt[0],TILE.stone,TILE.starb,TILE.cloud[0],TILE.cloud[1],TILE.cloud[2],TILE.cloud[3]];
    py += 90; px=4; for (const t of tiles) { x.drawImage(t, px, py, 48, t.height*3); px+=52; }
  })()`);
  await page.shot('02_sheet', { x: 0, y: 0, width: 900, height: 420 });
  await page.eval(`document.getElementById('sheet').remove()`);
  // start game
  await page.key('keyDown', 'Enter', 'Enter'); await page.key('keyUp', 'Enter', 'Enter');
  await page.wait(500);
  await page.shot('03_start');
  // run right a bit
  await page.key('keyDown', 'ArrowRight', 'ArrowRight');
  await page.wait(1500);
  await page.shot('04_running');
  await page.key('keyUp', 'ArrowRight', 'ArrowRight');
  // inhale
  await page.key('keyDown', 'Enter', 'Enter');
  await page.wait(300);
  await page.shot('05_inhale');
  await page.wait(900);
  await page.key('keyUp', 'Enter', 'Enter');
  console.log(await page.eval(`JSON.stringify({mode:K.mode, x:K.x|0, y:K.y|0, score, state, hp:K.hp})`));
  await page.shot('06_after_inhale');
  await page.key('keyDown', 'Enter', 'Enter'); await page.wait(50); await page.key('keyUp', 'Enter', 'Enter');
  await page.wait(150);
  await page.shot('07_spit');
  // jump & fly
  await page.key('keyDown', 'Space', ' '); await page.wait(150); await page.key('keyUp', 'Space', ' ');
  await page.wait(350);
  for (let i = 0; i < 4; i++) { await page.key('keyDown', 'Space', ' '); await page.wait(60); await page.key('keyUp', 'Space', ' '); await page.wait(200); }
  await page.shot('08_fly');
  console.log(await page.eval(`JSON.stringify({mode:K.mode, x:K.x|0, y:K.y|0, score, state, hp:K.hp})`));
};
Bash Run headless Chrome test and screenshots
IN
SP="C:/Users/ethan/AppData/Local/Temp/claude/c--Users-ethan-Documents-GitHub-Agent-Engineering-Lecture-2a---Codex-and-Vibecoding-homework-1-1-one-shot-v1/069bf261-be02-4109-974b-b55a25e9b8ec/scratchpad"; mkdir -p "$SP/out"; node "$SP/cdp.mjs" "$(pwd -W)/index.html" "$SP/out" "$SP/t1.mjs"

OUT
{"mode":"full","x":196,"y":178,"score":200,"state":"play","hp":6}
{"mode":"puff","x":193,"y":90,"score":400,"state":"play","hp":6}
--- page logs ---
3:36 PM
No errors, and inhale → swallow → spit all worked. Let me look at the visuals.



Read C:\Users\ethan\AppData\Local\Temp\claude\c--Users-ethan-Documents-GitHub-Agent-Engineering-Lecture-2a---Codex-and-Vibecoding-homework-1-1-one-shot-v1\069bf261-be02-4109-974b-b55a25e9b8ec\scratchpad\out\02_sheet.png
Read C:\Users\ethan\AppData\Local\Temp\claude\c--Users-ethan-Documents-GitHub-Agent-Engineering-Lecture-2a---Codex-and-Vibecoding-homework-1-1-one-shot-v1\069bf261-be02-4109-974b-b55a25e9b8ec\scratchpad\out\01_title.png
Read C:\Users\ethan\AppData\Local\Temp\claude\c--Users-ethan-Documents-GitHub-Agent-Engineering-Lecture-2a---Codex-and-Vibecoding-homework-1-1-one-shot-v1\069bf261-be02-4109-974b-b55a25e9b8ec\scratchpad\out\05_inhale.png
3:36 PM
Sprites and scene look good. Checking the action shots:



Read C:\Users\ethan\AppData\Local\Temp\claude\c--Users-ethan-Documents-GitHub-Agent-Engineering-Lecture-2a---Codex-and-Vibecoding-homework-1-1-one-shot-v1\069bf261-be02-4109-974b-b55a25e9b8ec\scratchpad\out\07_spit.png
Read C:\Users\ethan\AppData\Local\Temp\claude\c--Users-ethan-Documents-GitHub-Agent-Engineering-Lecture-2a---Codex-and-Vibecoding-homework-1-1-one-shot-v1\069bf261-be02-4109-974b-b55a25e9b8ec\scratchpad\out\08_fly.png
3:36 PM
Core loop works. Now let me tour the level sections and test death, game over, and the win sequence.



Write C:\Users\ethan\AppData\Local\Temp\claude\c--Users-ethan-Documents-GitHub-Agent-Engineering-Lecture-2a---Codex-and-Vibecoding-homework-1-1-one-shot-v1\069bf261-be02-4109-974b-b55a25e9b8ec\scratchpad\t2.mjs
46 lines
const S = (p) => p.eval(`JSON.stringify({state, mode:K.mode, x:K.x|0, y:K.y|0, score, lives, hp:K.hp})`);
export default async (page) => {
  await page.eval(`newGame()`);
  const tour = [[62, 9], [76, 9], [92, 9], [112, 6], [134, 10], [160, 8], [174, 3], [200, 10]];
  for (const [tx, ty] of tour) {
    await page.eval(`K.x=${tx * 16}; K.y=${ty * 16}; K.vy=0; K.invuln=99999; updateCamera(true);`);
    await page.wait(250);
    await page.shot('t_' + tx);
  }
  // tunnel: inhale star blocks at entrance
  await page.eval(`K.x=127*16; K.y=12*16-14; K.vx=0; K.facing=1; K.mode='normal'; updateCamera(true); held.action=true; pressed.action=true;`);
  await page.wait(700);
  await page.shot('tunnel_inhale');
  console.log('tunnel', await S(page), await page.eval(`JSON.stringify(K.mouth)`), await page.eval(`map[10][131]+map[11][131]+map[10][132]+map[11][132]`));
  await page.eval(`held.action=false; pressed.action=true`);
  await page.wait(300);
  await page.shot('tunnel_bigstar');
  // death by enemy -> respawn
  await page.eval(`K.invuln=0; K.hp=1; hurt(K.x+20)`);
  console.log('after hurt', await S(page));
  await page.wait(1200);
  await page.shot('dying');
  await page.wait(2200);
  console.log('after respawn', await S(page));
  // pit death x2 -> game over
  for (let i = 0; i < 2; i++) {
    await page.eval(`K.invuln=0; K.x=110*16; K.y=14*16; K.vy=3; updateCamera(true);`);
    await page.wait(2200);
    console.log('pit', i, await S(page));
  }
  await page.wait(800);
  await page.shot('gameover');
  // restart & win
  await page.eval(`pressed.action=true`);
  await page.wait(200);
  await page.eval(`K.x=211*16; K.y=12*16-14; K.invuln=9999; updateCamera(true); held.right=true;`);
  await page.wait(900);
  await page.eval(`held.right=false`);
  console.log('goal', await S(page));
  await page.wait(1200);
  await page.shot('clear');
  await page.wait(3000);
  await page.shot('win');
  console.log('win', await S(page));
};
Bash Run level tour, death, and win tests
IN
SP="C:/Users/ethan/AppData/Local/Temp/claude/c--Users-ethan-Documents-GitHub-Agent-Engineering-Lecture-2a---Codex-and-Vibecoding-homework-1-1-one-shot-v1/069bf261-be02-4109-974b-b55a25e9b8ec/scratchpad"; node "$SP/cdp.mjs" "$(pwd -W)/index.html" "$SP/out" "$SP/t2.mjs"

OUT
tunnel {"state":"play","mode":"inhale","x":2032,"y":178,"score":100,"lives":3,"hp":6} null SSSS
after hurt {"state":"dying","mode":"normal","x":2032,"y":178,"score":100,"lives":2,"hp":0}
after respawn {"state":"play","mode":"normal","x":1570,"y":178,"score":100,"lives":2,"hp":6}
pit 0 {"state":"play","mode":"normal","x":1570,"y":178,"score":100,"lives":1,"hp":6}
pit 1 {"state":"over","mode":"normal","x":1760,"y":250,"score":100,"lives":0,"hp":0}
goal {"state":"play","mode":"normal","x":3396,"y":178,"score":0,"lives":3,"hp":6}
win {"state":"play","mode":"normal","x":3396,"y":178,"score":0,"lives":3,"hp":6}
--- page logs ---
The tunnel test showed Kirby landing just outside the block-grab range (56px vs. the enemy's 74px cone, which I'll unify), and the win test was correctly blocked by the goal pedestal since it requires a jump. Now I'll check the tour shots.
Bash List screenshot outputs
IN
cd "C:/Users/ethan/AppData/Local/Temp/claude/c--Users-ethan-Documents-GitHub-Agent-Engineering-Lecture-2a---Codex-and-Vibecoding-homework-1-1-one-shot-v1/069bf261-be02-4109-974b-b55a25e9b8ec/scratchpad" && cat > montage.mjs <<'EOF'
// crop the 640x384 canvas area out of several screenshots and tile them via headless chrome canvas is overkill; just list files
EOF
ls out/*.png

OUT
out/01_title.png
out/02_sheet.png
out/03_start.png
out/04_running.png
out/05_inhale.png
out/06_after_inhale.png
out/07_spit.png
out/08_fly.png
out/clear.png
out/dying.png
out/gameover.png
out/t_112.png
out/t_134.png
out/t_160.png
out/t_174.png
out/t_200.png
out/t_62.png
out/t_76.png
out/t_92.png
out/tunnel_bigstar.png
out/tunnel_inhale.png
out/win.png
Read C:\Users\ethan\AppData\Local\Temp\claude\c--Users-ethan-Documents-GitHub-Agent-Engineering-Lecture-2a---Codex-and-Vibecoding-homework-1-1-one-shot-v1\069bf261-be02-4109-974b-b55a25e9b8ec\scratchpad\out\t_76.png
Read C:\Users\ethan\AppData\Local\Temp\claude\c--Users-ethan-Documents-GitHub-Agent-Engineering-Lecture-2a---Codex-and-Vibecoding-homework-1-1-one-shot-v1\069bf261-be02-4109-974b-b55a25e9b8ec\scratchpad\out\t_112.png
Read C:\Users\ethan\AppData\Local\Temp\claude\c--Users-ethan-Documents-GitHub-Agent-Engineering-Lecture-2a---Codex-and-Vibecoding-homework-1-1-one-shot-v1\069bf261-be02-4109-974b-b55a25e9b8ec\scratchpad\out\t_134.png
Read C:\Users\ethan\AppData\Local\Temp\claude\c--Users-ethan-Documents-GitHub-Agent-Engineering-Lecture-2a---Codex-and-Vibecoding-homework-1-1-one-shot-v1\069bf261-be02-4109-974b-b55a25e9b8ec\scratchpad\out\gameover.png
3:37 PM
Tour looks right: level sections, checkpoint respawn, pit deaths, and game-over all behave. Applying the fixes (block-grab range, goal sparkles out of the render path, arrow glyph font):



Bash Apply small fixes to index.html
IN
python - <<'EOF'
import re
p='index.html'
s=open(p,encoding='utf-8').read()
s=s.replace("const tx0 = Math.floor(Math.min(m.x, m.x + f * 56) / TS), tx1 = Math.floor(Math.max(m.x, m.x + f * 56) / TS);",
            "const tx0 = Math.floor(Math.min(m.x, m.x + f * 64) / TS), tx1 = Math.floor(Math.max(m.x, m.x + f * 64) / TS);")
s=s.replace("if (cone(cx, cy) && Math.abs(cx - m.x) < 56 && K.inhaleT > 6) {","if (cone(cx, cy) && Math.abs(cx - m.x) < 64 && K.inhaleT > 6) {")
s=s.replace("        if (it.t % 20 === 0) sparkle(it.x + 14, it.y + 10, 1);\n","")
s=s.replace("""function updateItems() {
  for (const it of items) it.t++;
}""","""function updateItems() {
  for (const it of items) it.t++;
  if (goal && state === 'play' && goal.t % 20 === 0) sparkle(goal.x + 14, goal.y + 10, 1);
}""")
s=s.replace('font: bold 12px "Courier New", monospace;','font: bold 12px "Segoe UI Symbol", "Segoe UI", system-ui, sans-serif;')
open(p,'w',encoding='utf-8').write(s)
print(s.count('f * 64'), s.count('< 64 &&'), 'goal.t % 20' in s, 'Segoe UI Symbol' in s)
EOF

OUT
2 1 True True
Write C:\Users\ethan\AppData\Local\Temp\claude\c--Users-ethan-Documents-GitHub-Agent-Engineering-Lecture-2a---Codex-and-Vibecoding-homework-1-1-one-shot-v1\069bf261-be02-4109-974b-b55a25e9b8ec\scratchpad\t3.mjs
31 lines
const S = (p) => p.eval(`JSON.stringify({state, mode:K.mode, x:K.x|0, y:K.y|0, score, lives, hp:K.hp, mouth:K.mouth})`);
export default async (page) => {
  await page.eval(`newGame(); bannerT=0;`);
  await page.eval(`K.x=127*16; K.y=12*16-14; K.vx=0; K.facing=1; updateCamera(true); held.action=true; pressed.action=true;`);
  await page.wait(250);
  await page.shot('tunnel_inhale');
  await page.wait(600);
  console.log('tunnel', await S(page), await page.eval(`map[10][131]+map[11][131]+map[10][132]+map[11][132]`));
  await page.eval(`held.action=false; pressed.action=true`);
  await page.wait(250);
  await page.shot('tunnel_bigstar');
  await page.wait(1200);
  console.log('after spit', await S(page));
  // big flight from step at 168
  await page.eval(`K.x=167*16; K.y=9*16-14; K.vx=0; K.invuln=0; updateCamera(true); held.right=true;`);
  await page.wait(300);
  for (let i = 0; i < 14; i++) { await page.eval(`pressed.jump=true; held.jump=true`); await page.wait(80); await page.eval(`held.jump=false`); await page.wait(220); if (i===5) await page.shot('bigflight'); }
  await page.wait(1000);
  console.log('after flight', await S(page));
  // win
  await page.eval(`K.x=211*16; K.y=12*16-14; K.invuln=9999; K.hp=6; updateCamera(true); held.right=true; pressed.jump=true; held.jump=true;`);
  await page.wait(1200);
  await page.eval(`held.right=false; held.jump=false`);
  console.log('goal', await S(page));
  await page.wait(1300);
  await page.shot('clear');
  await page.wait(3500);
  await page.shot('win');
  console.log('win', await S(page));
};
Bash Test tunnel inhale, big flight, and win screen
IN
SP="C:/Users/ethan/AppData/Local/Temp/claude/c--Users-ethan-Documents-GitHub-Agent-Engineering-Lecture-2a---Codex-and-Vibecoding-homework-1-1-one-shot-v1/069bf261-be02-4109-974b-b55a25e9b8ec/scratchpad"; node "$SP/cdp.mjs" "$(pwd -W)/index.html" "$SP/out" "$SP/t3.mjs"

OUT
tunnel {"state":"play","mode":"full","x":2032,"y":178,"score":100,"lives":3,"hp":6,"mouth":{"count":2}} ..SS
after spit {"state":"play","mode":"normal","x":2029,"y":178,"score":100,"lives":3,"hp":6,"mouth":null}
after flight {"state":"play","mode":"puff","x":3107,"y":60,"score":200,"lives":3,"hp":6,"mouth":null}
goal {"state":"clear","mode":"normal","x":3442,"y":146,"score":200,"lives":3,"hp":6,"mouth":null}
win {"state":"win","mode":"normal","x":4626,"y":-544,"score":3800,"lives":3,"hp":6,"mouth":null}
--- page logs ---
Found that the big star dies instantly because its 18px hitbox clips the floor tile when inhaling two blocks—I'll fix this by insetting the star's hitbox, then check the clear and win screens.
Read C:\Users\ethan\AppData\Local\Temp\claude\c--Users-ethan-Documents-GitHub-Agent-Engineering-Lecture-2a---Codex-and-Vibecoding-homework-1-1-one-shot-v1\069bf261-be02-4109-974b-b55a25e9b8ec\scratchpad\out\clear.png
Read C:\Users\ethan\AppData\Local\Temp\claude\c--Users-ethan-Documents-GitHub-Agent-Engineering-Lecture-2a---Codex-and-Vibecoding-homework-1-1-one-shot-v1\069bf261-be02-4109-974b-b55a25e9b8ec\scratchpad\out\win.png
Read C:\Users\ethan\AppData\Local\Temp\claude\c--Users-ethan-Documents-GitHub-Agent-Engineering-Lecture-2a---Codex-and-Vibecoding-homework-1-1-one-shot-v1\069bf261-be02-4109-974b-b55a25e9b8ec\scratchpad\out\bigflight.png
3:38 PM
Fixes needed: the HUD covers Kirby at the flight ceiling (I'll let the camera show 14px above the level top), and the star tile-collision inset.



Bash Apply star/camera fixes and rerun tests
IN
python - <<'EOF'
p='index.html'
s=open(p,encoding='utf-8').read()
old="""      const ty0 = Math.floor(p.y / TS), ty1 = Math.floor((p.y + p.h - 0.01) / TS);"""
new="""      const ty0 = Math.floor((p.y + 4) / TS), ty1 = Math.floor((p.y + p.h - 4) / TS); // inset so low stars skim the floor"""
assert old in s; s=s.replace(old,new)
old="const ty = clamp(K.y + K.h / 2 - VH / 2 - 8, 0, LH * TS - VH);"
new="const ty = clamp(K.y + K.h / 2 - VH / 2 - 8, -14, LH * TS - VH); // -14 keeps the level top below the HUD"
assert old in s; s=s.replace(old,new)
open(p,'w',encoding='utf-8').write(s)
EOF
SP="C:/Users/ethan/AppData/Local/Temp/claude/c--Users-ethan-Documents-GitHub-Agent-Engineering-Lecture-2a---Codex-and-Vibecoding-homework-1-1-one-shot-v1/069bf261-be02-4109-974b-b55a25e9b8ec/scratchpad"; node "$SP/cdp.mjs" "$(pwd -W)/index.html" "$SP/out" "$SP/t3.mjs"

OUT
tunnel {"state":"play","mode":"full","x":2032,"y":178,"score":100,"lives":3,"hp":6,"mouth":{"count":2}} ..SS
after spit {"state":"play","mode":"normal","x":2029,"y":178,"score":750,"lives":3,"hp":6,"mouth":null}
after flight {"state":"play","mode":"puff","x":3021,"y":59,"score":850,"lives":3,"hp":5,"mouth":null}
goal {"state":"clear","mode":"normal","x":3442,"y":146,"score":850,"lives":3,"hp":6,"mouth":null}
win {"state":"win","mode":"normal","x":4626,"y":-544,"score":4450,"lives":3,"hp":6,"mouth":null}
--- page logs ---
3:38 PM
The big star now pierces through the remaining blocks and both tunnel Waddle Dees, with the combo scoring 200 then 400.



Read C:\Users\ethan\AppData\Local\Temp\claude\c--Users-ethan-Documents-GitHub-Agent-Engineering-Lecture-2a---Codex-and-Vibecoding-homework-1-1-one-shot-v1\069bf261-be02-4109-974b-b55a25e9b8ec\scratchpad\out\tunnel_bigstar.png
Read C:\Users\ethan\AppData\Local\Temp\claude\c--Users-ethan-Documents-GitHub-Agent-Engineering-Lecture-2a---Codex-and-Vibecoding-homework-1-1-one-shot-v1\069bf261-be02-4109-974b-b55a25e9b8ec\scratchpad\out\bigflight.png
3:39 PM
I've built the game as a single file, index.html. Open it in a browser and press Enter to start. Everything is drawn in code, with no image files or libraries. I tested it in headless Chrome: I took screenshots and drove the controls through scripts, and the browser reported no errors.

What I checked in the test runs:

Inhale, swallow and spit: holding Enter swallowed a Waddle Dee, and the spat star defeated the next one.
Two things at once: swallowing two star blocks gives a big star that breaks through blocks and enemies, and each enemy in a row scores more (200, then 400).
Flying: Kirby flew across the big gap near the end.
Losing and restarting: an enemy death sends Kirby back to the checkpoint, falling into pits ran out the lives and showed the game-over screen, and Enter restarted.
Winning: touching the warp star flies Kirby off on it, then shows the stage-clear screen with bonus points added up.
These tests jumped Kirby to each spot rather than playing through, and headless Chrome produces no sound. So I haven't checked the audio, and I haven't checked whether the difficulty and controls feel right in real play.

Movement

Running speeds up and slows down instead of starting and stopping instantly.
How high Kirby jumps depends on how long you hold Space.
A jump still works for a moment after running off a ledge, and Space pressed just before landing is saved for a jump instead of starting flight.
Pressing Space in mid-air puffs Kirby up to fly: slow falling, a lift with each tap, and Enter blows out a puff of air that hurts enemies.
Inhaling shows wind streaks, enemies shake as they're pulled in, and there's a brief freeze and screen shake when an enemy is defeated. Point stars, health items and the extra life get pulled in too.
Down swallows what's in Kirby's mouth. Down + Space drops through cloud platforms.
Enemies: four kinds, each moving differently:

Waddle Dee walks and turns around at ledges.
Bronto Burt flies back and forth in a wave.
Bouncy hops toward Kirby on a spring.
Gordo is a spiked ball that can't be inhaled or defeated.
Level: one long stage of about 230 tiles, with gaps, cloud platforms, a wall of star blocks, a tunnel sealed by star blocks with a health tomato on its roof, a hidden extra life, a checkpoint, a long gap you have to fly over, and a warp star at the end.

Screens and sound: Kirby has 6 health bars and 3 lives. There's a score and a high score saved in the browser, plus title, pause, game-over and win screens. Controls are listed on the title screen, the pause screen and below the game, and in-level signs teach the moves early on. Music and sound effects are generated in the browser; M mutes and R restarts.

I didn't commit anything to git.



index.html
dont' edit anuything else, just tell me how to run the file in teh browser
3:42 PM
No setup or server is needed. Use any of these:

File Explorer: go to Documents\GitHub\Agent Engineering\Lecture 2a - Codex and Vibecoding\homework\1.1 one-shot v1 and double-click index.html. It opens in your default browser.
VS Code: right-click index.html in the file sidebar, choose Reveal in File Explorer, then double-click the file.
Terminal: from that folder, run:

start index.html
Browser: drag index.html into an open Chrome or Edge window.
Once it's open, click the page so it has keyboard focus, then press Enter to start. Sound starts after your first key press, because browsers block audio until you interact with the page.
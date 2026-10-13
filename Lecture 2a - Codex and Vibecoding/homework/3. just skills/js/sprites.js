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

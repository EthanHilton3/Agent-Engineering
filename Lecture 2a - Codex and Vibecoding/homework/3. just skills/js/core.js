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

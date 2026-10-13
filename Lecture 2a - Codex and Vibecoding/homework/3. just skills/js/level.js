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

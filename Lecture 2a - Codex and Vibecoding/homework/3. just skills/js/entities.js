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
    if (this.rage && eye !== 'dead') { blit(ctx, SPR.bossBrow, fx - 1, 68); blit(ctx, SPR.bossBrow, fx + 17, 68, true); }
    const m = SPR.bossMouth[mouth];
    blit(ctx, m, fx + 14 - m.width / 2, 112 - m.height / 2);
  }
}

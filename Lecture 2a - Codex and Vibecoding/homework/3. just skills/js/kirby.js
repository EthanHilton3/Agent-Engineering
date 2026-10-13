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

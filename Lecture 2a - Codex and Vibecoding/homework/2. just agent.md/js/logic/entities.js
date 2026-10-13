// Enemies, pickups and projectiles: creation and per-tick behaviour.
var KB = (typeof KB !== 'undefined') ? KB : {};
if (typeof module !== 'undefined') Object.assign(KB, require('./constants.js'), require('./physics.js'));

KB.Entities = (function () {
  const C = KB.C;
  const T = C.T;
  const P = KB.Physics;

  // ---- shared helpers -------------------------------------------------------
  function emit(g, type, data) { g.events.push(Object.assign({ type }, data || {})); }
  function addScore(g, points, x, y) {
    g.score += points;
    emit(g, 'score', { value: points, x, y });
  }
  function center(o) { return { x: o.x + o.w / 2, y: o.y + o.h / 2 }; }
  function nextId(g) { g.nextId = (g.nextId || 0) + 1; return g.nextId; }

  // ---- creation -------------------------------------------------------------
  function createEnemy(g, kind, tx, ty) {
    const S = C.TILE;
    const size = kind === 'gordo' ? C.GORDO_SIZE : C.ENEMY_SIZE;
    const e = {
      id: nextId(g), kind, w: size, h: size,
      x: tx * S + (S - size) / 2, y: ty * S + S - size,
      vx: 0, vy: 0, dir: -1, t: 0, onGround: false,
      pulled: false, inhalable: kind !== 'gordo', harmless: false,
    };
    if (kind === 'flyer' || kind === 'gordo') {
      e.y = ty * S + (S - size) / 2;
      e.homeX = e.x; e.homeY = e.y;
    }
    if (kind === 'hopper') e.wait = C.HOPPER_WAIT_TICKS + (tx * C.HOPPER_STAGGER) % C.HOPPER_WAIT_TICKS;
    return e;
  }

  // A star block pulled out of the ground by the inhale. Harmless; popped if the inhale stops.
  function createBlock(g, tx, ty) {
    const S = C.TILE;
    return {
      id: nextId(g), kind: 'block', x: tx * S, y: ty * S, w: S, h: S, vx: 0, vy: 0, dir: 1, t: 0,
      pulled: true, inhalable: true, harmless: true,
    };
  }

  function createPickup(g, kind, tx, ty) {
    const S = C.TILE;
    const size = kind === 'tomato' ? C.TOMATO_SIZE : C.PICKUP_SIZE;
    return { id: nextId(g), kind, w: size, h: size, x: tx * S + (S - size) / 2, y: ty * S + (S - size) / 2, pulled: false };
  }

  // ---- enemy behaviour ------------------------------------------------------
  function applyGravity(e) {
    e.vy = Math.min(e.vy + (e.vy < 0 ? C.GRAVITY : C.FALL_GRAVITY) * C.DT, C.MAX_FALL_SPEED);
  }

  function updateWalker(g, e) {
    e.vx = e.dir * C.WALKER_SPEED;
    applyGravity(e);
    P.moveBody(e, g.world, e.vx * C.DT, e.vy * C.DT);
    if (e.hitWall) e.dir = -e.dir;
    else if (e.onGround) {
      const aheadX = e.dir > 0 ? e.x + e.w + 1 : e.x - 1;
      if (!P.hasFloorAt(g.world, aheadX, e.y + e.h + 1)) e.dir = -e.dir;
    }
  }

  function updateFlyer(e) {
    if (Math.abs(e.x + e.dir - e.homeX) > C.FLYER_RANGE) e.dir = e.x > e.homeX ? -1 : 1;
    e.x += e.dir * C.FLYER_SPEED * C.DT;
    const targetY = e.homeY + Math.sin(e.t * C.DT * C.FLYER_FREQ) * C.FLYER_AMP;
    e.y += (targetY - e.y) * C.FLYER_EASE;  // ease, so a flyer let go mid-inhale drifts back instead of snapping
  }

  function updateHopper(g, e, player) {
    applyGravity(e);
    if (e.onGround) {
      e.vx = 0;
      e.wait--;
      if (e.wait <= 0) {
        e.dir = player.x < e.x ? -1 : 1;
        e.vx = e.dir * C.HOPPER_SPEED_X;
        e.vy = -C.HOPPER_JUMP_SPEED;
        e.wait = C.HOPPER_WAIT_TICKS;
        emit(g, 'hop', { x: e.x + e.w / 2, y: e.y + e.h });
      }
    }
    P.moveBody(e, g.world, e.vx * C.DT, e.vy * C.DT);
  }

  function updateGordo(e) {
    e.y = e.homeY + Math.sin(e.t * C.DT * C.GORDO_FREQ) * C.GORDO_AMP;
  }

  function updateEnemies(g) {
    const pc = center(g.player);
    const fallOut = g.world.h * C.TILE + C.TILE * 2;
    for (const e of g.enemies) {
      if (e.pulled || e.kind === 'block') continue;
      if (Math.abs(e.x + e.w / 2 - pc.x) > C.ACTIVATE_DIST) continue;
      e.t++;
      if (e.kind === 'walker') updateWalker(g, e);
      else if (e.kind === 'flyer') updateFlyer(e);
      else if (e.kind === 'hopper') updateHopper(g, e, g.player);
      else if (e.kind === 'gordo') updateGordo(e);
      if (e.y > fallOut) e.removed = true;
    }
    g.enemies = g.enemies.filter(e => !e.removed);
  }

  function defeatEnemy(g, e, points) {
    e.removed = true;
    const c = center(e);
    emit(g, 'defeat', { kind: e.kind, x: c.x, y: c.y });
    if (points) addScore(g, points, c.x, e.y);
  }

  // ---- projectiles ----------------------------------------------------------
  function createStar(g, x, y, dir) {
    const s = C.STAR_SIZE;
    return { id: nextId(g), kind: 'star', x: dir > 0 ? x - s / 3 : x - s + s / 3, y: y - s / 2, w: s, h: s,
      vx: dir * C.STAR_SPEED, life: C.STAR_LIFE_TICKS, hits: 0, hitIds: [] };
  }
  function createPuff(g, x, y, dir) {
    const s = C.PUFF_SIZE;
    return { id: nextId(g), kind: 'puff', x: dir > 0 ? x : x - s, y: y - s / 2, w: s, h: s,
      vx: dir * C.PUFF_SPEED, life: C.PUFF_LIFE_TICKS, hits: 0, hitIds: [] };
  }

  // Returns false once the projectile is used up.
  function projectileHitsTiles(g, p) {
    const S = C.TILE;
    const tx = Math.floor((p.vx > 0 ? p.x + p.w : p.x) / S);
    for (let ty = Math.floor(p.y / S); ty <= Math.floor((p.y + p.h - 0.001) / S); ty++) {
      const t = P.tileAt(g.world, tx, ty);
      if (p.kind === 'star' && t === T.STAR_BLOCK) {
        P.setTile(g.world, tx, ty, T.EMPTY);
        emit(g, 'blockBreak', { x: tx * S + S / 2, y: ty * S + S / 2 });
      } else if (P.isSolid(t)) {
        emit(g, p.kind === 'star' ? 'starBurst' : 'puffGone', center(p));
        return false;
      }
    }
    return true;
  }

  function projectileHitsEnemies(g, p) {
    for (const e of g.enemies) {
      if (e.removed || e.harmless || p.hitIds.includes(e.id) || !P.overlaps(p, e)) continue;
      p.hitIds.push(e.id);
      if (e.kind === 'gordo') {           // nothing hurts Gordo
        emit(g, 'clink', center(p));
        return false;
      }
      if (p.kind === 'star') {            // Kirby's star pierces through a whole line of enemies
        defeatEnemy(g, e, C.SCORE_STAR_HIT * Math.pow(2, p.hits));
        p.hits++;
      } else {
        defeatEnemy(g, e, C.SCORE_PUFF_HIT);
        return false;
      }
    }
    return true;
  }

  function updateProjectiles(g) {
    for (const p of g.projectiles) {
      const steps = Math.max(1, Math.ceil(Math.abs(p.vx * C.DT) / C.MAX_SUBSTEP));
      let alive = true;
      for (let i = 0; i < steps && alive; i++) {
        p.x += p.vx * C.DT / steps;
        alive = projectileHitsTiles(g, p) && projectileHitsEnemies(g, p);
      }
      p.life--;
      if (alive && p.life <= 0) {
        emit(g, p.kind === 'star' ? 'starBurst' : 'puffGone', center(p));
        alive = false;
      }
      if (!alive) p.removed = true;
    }
    g.projectiles = g.projectiles.filter(p => !p.removed);
    g.enemies = g.enemies.filter(e => !e.removed);
  }

  return {
    emit, addScore, center,
    createEnemy, createBlock, createPickup, createStar, createPuff,
    updateEnemies, updateProjectiles, defeatEnemy,
  };
})();

if (typeof module !== 'undefined') module.exports = { Entities: KB.Entities };

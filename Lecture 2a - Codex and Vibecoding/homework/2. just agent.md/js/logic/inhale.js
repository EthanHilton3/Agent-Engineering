// Inhaling, swallowing, spitting stars and exhaling air puffs.
var KB = (typeof KB !== 'undefined') ? KB : {};
if (typeof module !== 'undefined') {
  Object.assign(KB, require('./constants.js'), require('./physics.js'), require('./entities.js'));
}

KB.Inhale = (function () {
  const C = KB.C;
  const T = C.T;
  const P = KB.Physics;
  const E = KB.Entities;

  function mouth(p) {
    return { x: p.facing > 0 ? p.x + p.w : p.x, y: p.y + p.h * C.MOUTH_Y_RATIO };
  }

  // Is the point (x, y) inside the cone in front of Kirby's mouth?
  function pointInCone(p, x, y) {
    const m = mouth(p);
    const dx = (x - m.x) * p.facing;
    const dy = y - m.y;
    if (dx < -C.INHALE_BEHIND || dx > C.INHALE_RANGE) return false;
    return Math.abs(dy) <= C.INHALE_HALF_HEIGHT + Math.max(0, dx) * C.INHALE_SPREAD;
  }

  // Is this entity inside the cone with nothing solid in between? `tile` lets a star block ignore itself.
  function inCone(p, target, world, tile) {
    if (target.inhalable === false) return false;
    const c = E.center(target);
    if (!pointInCone(p, c.x, c.y)) return false;
    if (!world) return true;
    const m = mouth(p);
    return P.lineOfSight(world, m.x, m.y, c.x, c.y, tile);
  }

  // Star blocks inside the cone come loose and become pulled objects.
  function loosenBlocks(g, p) {
    const S = C.TILE;
    const m = mouth(p);
    const reach = C.INHALE_HALF_HEIGHT + C.INHALE_RANGE * C.INHALE_SPREAD;
    const x0 = Math.floor(Math.min(m.x, m.x + p.facing * C.INHALE_RANGE) / S);
    const x1 = Math.floor(Math.max(m.x, m.x + p.facing * C.INHALE_RANGE) / S);
    for (let ty = Math.floor((m.y - reach) / S); ty <= Math.floor((m.y + reach) / S); ty++) {
      for (let tx = x0; tx <= x1; tx++) {
        if (P.tileAt(g.world, tx, ty) !== T.STAR_BLOCK) continue;
        const box = { x: tx * S, y: ty * S, w: S, h: S };
        if (!inCone(p, box, g.world, { tx, ty })) continue;
        P.setTile(g.world, tx, ty, T.EMPTY);
        g.enemies.push(E.createBlock(g, tx, ty));
        E.emit(g, 'blockLoose', { x: tx * S + S / 2, y: ty * S + S / 2 });
      }
    }
  }

  function pullToward(o, m) {
    const c = E.center(o);
    const dx = m.x - c.x, dy = m.y - c.y;
    const dist = Math.hypot(dx, dy);
    if (dist < 0.001) return 0;
    const closeness = Math.max(0, 1 - dist / C.INHALE_RANGE);
    const step = Math.min(dist, (C.INHALE_PULL_SPEED + C.INHALE_PULL_BOOST * closeness) * C.DT);
    o.x += dx / dist * step;
    o.y += dy / dist * step;
    return dist - step;
  }

  // Let go of everything: enemies wake up again, loose blocks crumble.
  function releaseAll(g) {
    for (const e of g.enemies) {
      if (!e.pulled) continue;
      e.pulled = false;
      e.vx = 0; e.vy = 0;
      if (e.kind === 'block') {
        e.removed = true;
        E.emit(g, 'blockPop', E.center(e));
      }
    }
    for (const k of g.pickups) k.pulled = false;
    g.enemies = g.enemies.filter(e => !e.removed);
  }

  function update(g) {
    const p = g.player;
    if (p.mode !== 'inhale') {
      if (g.enemies.some(e => e.pulled) || g.pickups.some(k => k.pulled)) releaseAll(g);
      return;
    }
    // Once something is caught by the inhale it stays caught until Kirby lets go.
    for (const e of g.enemies) if (!e.pulled && inCone(p, e, g.world)) e.pulled = true;
    for (const k of g.pickups) if (!k.pulled && inCone(p, k, g.world)) k.pulled = true;
    loosenBlocks(g, p);

    const m = mouth(p);
    const swallowed = [];
    for (const e of g.enemies) {
      if (!e.pulled) continue;
      const left = pullToward(e, m);
      if (left <= C.INHALE_SWALLOW_DIST || P.overlaps(e, p)) {
        e.removed = true;
        swallowed.push(e.kind);
      }
    }
    for (const k of g.pickups) if (k.pulled) pullToward(k, m);
    g.enemies = g.enemies.filter(e => !e.removed);

    if (swallowed.length) {
      p.mode = 'full';
      p.held = { kinds: swallowed, count: swallowed.length };
      const enemies = swallowed.filter(k => k !== 'block').length;
      if (enemies) E.addScore(g, C.SCORE_SWALLOW * enemies, m.x, p.y);
      E.emit(g, 'swallow', { x: m.x, y: m.y, count: swallowed.length });
      releaseAll(g);
    }
  }

  function spit(g) {
    const p = g.player;
    const m = mouth(p);
    g.projectiles.push(E.createStar(g, m.x, m.y, p.facing));
    p.mode = 'normal';
    p.held = null;
    p.spitTimer = C.SPIT_ANIM_TICKS;
    E.emit(g, 'spit', { x: m.x, y: m.y });
  }

  function exhale(g) {
    const p = g.player;
    const m = mouth(p);
    g.projectiles.push(E.createPuff(g, m.x, m.y, p.facing));
    p.mode = 'normal';
    p.spitTimer = C.SPIT_ANIM_TICKS;
    E.emit(g, 'exhale', { x: m.x, y: m.y });
  }

  return { mouth, pointInCone, inCone, update, releaseAll, spit, exhale };
})();

if (typeof module !== 'undefined') module.exports = { Inhale: KB.Inhale };

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
      // Keep the star's bottom no lower than Kirby's feet so a big star doesn't clip the floor.
      kind: 'star', big: big, x: p.facing > 0 ? m.x - 2 : m.x - size + 2, y: Math.min(m.y - size / 2, p.y + p.h - size),
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

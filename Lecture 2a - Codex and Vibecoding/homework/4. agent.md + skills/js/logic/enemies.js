// Enemy and object behaviour: walker, flyer, hopper, spiky, loose objects, apples, boss puffs. Pure logic.
var Enemies = (function () {
  'use strict';
  var C = typeof CONST !== 'undefined' ? CONST : require('./constants.js').CONST;
  var P = typeof Physics !== 'undefined' ? Physics : require('./physics.js').Physics;
  var W = typeof World !== 'undefined' ? World : require('./world.js').World;
  var T = C.TILE;

  var INHALABLE = { walker: true, flyer: true, hopper: true, apple: true, loose: true };
  var HARMFUL = { walker: true, flyer: true, hopper: true, spiky: true, apple: true, bosspuff: true };
  var DEFEATABLE = { walker: true, flyer: true, hopper: true, apple: true };
  var nextId = 1;

  function base(type, x, y, w, h) {
    return {
      id: nextId++, type: type, x: x, y: y, w: w, h: h, vx: 0, vy: 0, facing: -1,
      onGround: false, hitWall: 0, active: false, caught: false, pull: 0, stun: 0, t: 0, timer: 0,
      dead: false, inhalable: !!INHALABLE[type], harmful: !!HARMFUL[type]
    };
  }

  function fromSpawn(sp) {
    var S = C.ENEMY_SIZE, x = sp.col * T, y = sp.row * T, e;
    if (sp.type === 'walker' || sp.type === 'hopper') return base(sp.type, x + (T - S) / 2, y + T - S, S, S);
    if (sp.type === 'flyer') {
      e = base('flyer', x + (T - S) / 2, y + (T - C.FLYER_H) / 2, S, C.FLYER_H);
      e.baseY = e.y; e.spawnX = e.x; e.spawnY = e.y;
      return e;
    }
    e = base('spiky', x + (T - C.SPIKY_SIZE) / 2, y + (T - C.SPIKY_SIZE) / 2, C.SPIKY_SIZE, C.SPIKY_SIZE);
    e.baseX = e.x; e.baseY = e.y; e.patrol = !!sp.patrol;
    return e;
  }

  function spawnAll(world) {
    return world.spawns.map(fromSpawn);
  }

  function makeLoose(kind, x, y, vx, score) {
    var e = base('loose', x, y, C.ENEMY_SIZE, C.ENEMY_SIZE);
    e.kind = kind; e.vx = vx; e.vy = C.LOOSE_BOUNCE; e.life = C.LOOSE_LIFE;
    e.score = score || 0; e.active = true; e.bounce = C.LOOSE_BOUNCE;
    return e;
  }

  function makeApple(x, y) {
    var e = base('apple', x, y, C.APPLE_SIZE, C.APPLE_SIZE);
    e.life = C.APPLE_LIFE; e.active = true; e.rolling = false;
    return e;
  }

  function makePuff(x, y, vx) {
    var e = base('bosspuff', x, y, C.BOSS_PUFF_SIZE, C.BOSS_PUFF_SIZE);
    e.vx = vx; e.baseY = y; e.active = true;
    return e;
  }

  function fall(world, e) {
    e.vy = Math.min(e.vy + C.GRAVITY, C.MAX_FALL);
    P.moveBody(world, e);
  }

  function updateWalker(state, e) {
    var world = state.world;
    if (e.onGround) {
      var fx = e.facing > 0 ? e.x + e.w + 1 : e.x - 1;
      var below = P.tileAt(world, Math.floor(fx / T), Math.floor((e.y + e.h + 1) / T));
      if (!P.isSolid(below) && below !== P.TILES.PLATFORM) e.facing = -e.facing;
    }
    e.vx = e.facing * C.WALKER_SPEED;
    fall(world, e);
    if (e.hitWall) e.facing = -e.facing;
  }

  function updateHopper(state, e) {
    var p = state.player;
    if (e.onGround) {
      e.vx = 0;
      e.timer++;
      var dx = (p.x + p.w / 2) - (e.x + e.w / 2);
      if (e.timer >= C.HOPPER_WAIT && Math.abs(dx) < C.HOPPER_SENSE) {
        e.facing = dx < 0 ? -1 : 1;
        e.vy = C.HOPPER_JUMP_VY;
        e.vx = e.facing * C.HOPPER_HOP_VX;
        e.timer = 0;
      }
    }
    fall(state.world, e);
  }

  function updateFlyer(state, e) {
    var p = state.player;
    var dx = p.x - e.x, dy = p.y - e.baseY;
    if (Math.abs(dx) < C.FLYER_SENSE && Math.abs(dy) < C.FLYER_SENSE) {
      e.facing = dx < 0 ? -1 : 1;
      e.baseY += Math.max(-C.FLYER_HOMING, Math.min(C.FLYER_HOMING, dy));
      e.baseY = Math.max(e.spawnY - C.FLYER_LEASH, Math.min(e.spawnY + C.FLYER_LEASH, e.baseY));
      e.x += e.facing * C.FLYER_SPEED;
    } else {
      if (Math.abs(e.x - e.spawnX) > C.FLYER_PATROL) e.facing = e.x < e.spawnX ? 1 : -1;
      e.x += e.facing * C.FLYER_PATROL_SPEED;
    }
    e.y = e.baseY + C.FLYER_AMP * Math.sin(e.t * C.FLYER_FREQ);
  }

  function updateSpiky(state, e) {
    var s = Math.sin(e.t * C.SPIKY_FREQ);
    if (e.patrol) e.x = e.baseX + C.SPIKY_PATROL * s;
    else e.y = e.baseY + C.SPIKY_AMP * s;
  }

  function updateLoose(state, e) {
    fall(state.world, e);
    if (e.onGround) {
      e.vx *= C.LOOSE_FRICTION;
      e.bounce *= C.LOOSE_BOUNCE_DECAY;
      if (e.bounce < C.LOOSE_MIN_BOUNCE) e.vy = e.bounce;
    }
    if (--e.life <= 0) e.dead = true;
  }

  function updateApple(state, e) {
    var p = state.player;
    if (e.rolling) e.vx = e.facing * C.APPLE_ROLL_SPEED;
    fall(state.world, e);
    if (e.onGround && !e.rolling) {
      e.rolling = true;
      e.facing = p.x + p.w / 2 < e.x + e.w / 2 ? -1 : 1;
      W.emit(state, 'appleLand', e.x + e.w / 2, e.y + e.h);
    }
    if (e.hitWall) e.facing = -e.facing;
    if (--e.life <= 0) e.dead = true;
  }

  function updatePuff(state, e) {
    e.x += e.vx;
    e.y = e.baseY + C.BOSS_PUFF_WOBBLE * Math.sin(e.t * C.BOSS_PUFF_WOBBLE_FREQ);
    if (P.solidAtPoint(state.world, e.x + e.w / 2, e.y + e.h / 2)) {
      e.dead = true;
      W.emit(state, 'puffPop', e.x + e.w / 2, e.y + e.h / 2);
    }
  }

  var UPDATERS = {
    walker: updateWalker, hopper: updateHopper, flyer: updateFlyer, spiky: updateSpiky,
    loose: updateLoose, apple: updateApple, bosspuff: updatePuff
  };
  var GROUNDED = { walker: true, hopper: true, loose: true, apple: true };

  function update(state) {
    var p = state.player, world = state.world;
    for (var i = 0; i < state.enemies.length; i++) {
      var e = state.enemies[i];
      if (e.dead || e.caught) continue;
      if (!e.active) {
        if (Math.abs(e.x - p.x) < C.ACTIVATION_RANGE) e.active = true;
        else continue;
      }
      e.t++;
      if (e.stun > 0) {
        e.stun--;
        e.vx = 0;
        if (GROUNDED[e.type]) fall(world, e);
        continue;
      }
      UPDATERS[e.type](state, e);
      if (e.y > world.h * T + C.PIT_MARGIN) e.dead = true;
    }
  }

  // Called when the inhale lets go of something it was pulling.
  function release(e) {
    e.caught = false;
    e.pull = 0;
    e.stun = C.STUN_TICKS;
    if (e.type === 'flyer') { e.baseY = e.y; e.t = 0; }
  }

  function defeat(state, e) {
    e.dead = true;
    W.addScore(state, C.SCORE[e.type] || 0);
    W.emit(state, 'defeat', e.x + e.w / 2, e.y + e.h / 2, { kind: e.type });
  }

  function removeDead(state) {
    state.enemies = state.enemies.filter(function (e) { return !e.dead; });
  }

  return {
    DEFEATABLE: DEFEATABLE,
    fromSpawn: fromSpawn,
    spawnAll: spawnAll,
    makeLoose: makeLoose,
    makeApple: makeApple,
    makePuff: makePuff,
    update: update,
    release: release,
    defeat: defeat,
    removeDead: removeDead
  };
})();

if (typeof module !== 'undefined') module.exports = { Enemies };

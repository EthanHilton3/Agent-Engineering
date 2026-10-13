// Old Gnarlwood, the tree boss: drops apples (inhalable ammo) and blows air puffs.
// Only spat stars hurt it. Pure logic.
var Boss = (function () {
  'use strict';
  var C = typeof CONST !== 'undefined' ? CONST : require('./constants.js').CONST;
  var P = typeof Physics !== 'undefined' ? Physics : require('./physics.js').Physics;
  var W = typeof World !== 'undefined' ? World : require('./world.js').World;
  var E = typeof Enemies !== 'undefined' ? Enemies : require('./enemies.js').Enemies;
  var T = C.TILE;

  function create(world) {
    if (!world.bossSpawn) return null;
    return {
      x: world.bossSpawn.x, y: world.bossSpawn.y, w: C.BOSS_W, h: C.BOSS_H,
      hp: C.BOSS_HP, state: 'dormant', timer: 0, invuln: 0, t: 0, cycle: 0, mouthOpen: 0
    };
  }

  function alive(b) {
    return !!b && b.state !== 'dormant' && b.state !== 'dying' && b.state !== 'dead';
  }

  function enraged(b) {
    return b.hp <= C.BOSS_RAGE_HP;
  }

  function wait(b, ticks) {
    return Math.round(enraged(b) ? ticks * C.BOSS_RAGE_SPEEDUP : ticks);
  }

  function floorY(state) {
    return state.world.groundRow * T;
  }

  function wake(state) {
    var b = state.boss;
    if (!b || b.state !== 'dormant') return;
    b.state = 'intro';
    b.timer = 0;
    W.emit(state, 'bossWake', b.x + b.w / 2, b.y);
  }

  function dropApples(state, b) {
    var n = enraged(b) ? C.BOSS_RAGE_APPLES : C.BOSS_APPLES;
    var left = state.world.gateCol * T + C.BOSS_APPLE_MARGIN;
    var right = b.x - C.BOSS_APPLE_MARGIN;
    var top = state.world.arenaTop;
    for (var i = 0; i < n; i++) {
      // Spread apples across the arena in equal lanes, jittered inside each lane.
      var lane = (right - left) / n;
      var x = left + lane * i + W.rand(state) * (lane - C.APPLE_SIZE);
      state.enemies.push(E.makeApple(Math.round(x), top));
    }
    W.emit(state, 'appleDrop', b.x, b.y);
  }

  function blowPuff(state, b, k) {
    var low = (k + b.cycle) % 2 === 0;
    var cy = floorY(state) - (low ? C.BOSS_PUFF_LOW : C.BOSS_PUFF_HIGH);
    state.enemies.push(E.makePuff(b.x - C.BOSS_PUFF_SIZE, cy - C.BOSS_PUFF_SIZE / 2, -C.BOSS_PUFF_SPEED));
    b.mouthOpen = C.BOSS_PUFF_GAP;
    W.emit(state, 'bossBlow', b.x, cy);
  }

  function update(state) {
    var b = state.boss;
    if (!b || b.state === 'dormant' || b.state === 'dead') return;
    b.t++;
    if (b.invuln > 0) b.invuln--;
    if (b.mouthOpen > 0) b.mouthOpen--;
    b.timer++;
    if (b.state === 'intro') {
      if (b.timer >= C.BOSS_INTRO_TICKS) { b.state = 'apples'; b.timer = 0; }
    } else if (b.state === 'apples') {
      if (b.timer === 1) dropApples(state, b);
      if (b.timer >= wait(b, C.BOSS_APPLE_WAIT)) { b.state = 'blow'; b.timer = 0; }
    } else if (b.state === 'blow') {
      var gap = wait(b, C.BOSS_PUFF_GAP);
      if (b.timer % gap === 0 && b.timer / gap <= C.BOSS_PUFFS) blowPuff(state, b, b.timer / gap);
      if (b.timer >= wait(b, C.BOSS_BLOW_WAIT)) { b.state = 'apples'; b.timer = 0; b.cycle++; }
    } else if (b.state === 'dying') {
      if (b.timer % C.BOSS_BOOM_EVERY === 0) {
        W.emit(state, 'bossBoom', b.x + W.rand(state) * b.w, b.y + W.rand(state) * b.h);
      }
      if (b.timer >= C.BOSS_DEATH_TICKS) {
        b.state = 'dead';
        state.warp.active = true;
        openGate(state);
        W.addScore(state, C.SCORE.boss);
        W.emit(state, 'bossDefeated', b.x + b.w / 2, b.y + b.h / 2);
      }
    }
  }

  // Restores the gate column to how the level drew it, so the arena opens up again.
  function openGate(state) {
    var w = state.world;
    for (var r = 0; r < w.groundRow; r++) P.setTile(w, w.gateCol, r, w.original[r * w.w + w.gateCol]);
    state.arenaLocked = false;
  }

  // A spat star hit the boss. Returns true if it took damage.
  function hit(state, power) {
    var b = state.boss;
    if (!alive(b) || b.invuln > 0) return false;
    b.hp = Math.max(0, b.hp - power);
    b.invuln = C.BOSS_HIT_INVULN;
    W.emit(state, 'bossHit', b.x + b.w / 2, b.y + b.h / 3, { hp: b.hp });
    if (b.hp === 0) {
      b.state = 'dying';
      b.timer = 0;
      state.enemies.forEach(function (e) {
        if (e.type === 'apple' || e.type === 'bosspuff') e.dead = true;
      });
    }
    return true;
  }

  return {
    create: create,
    alive: alive,
    wake: wake,
    update: update,
    hit: hit
  };
})();

if (typeof module !== 'undefined') module.exports = { Boss };

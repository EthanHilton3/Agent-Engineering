// An automated player for the playthrough tests. It READS the game state to decide,
// but it can only ACT by pressing and releasing keys on the input tracker, like a person would.
// Works in Node (require) and in the browser (injected by tests/smoke.mjs).
var KirbyBot = (function () {
  'use strict';
  var isNode = typeof module !== 'undefined';
  var C = isNode ? require('../js/logic/constants.js').CONST : CONST;
  var P = isNode ? require('../js/logic/physics.js').Physics : Physics;
  var PL = isNode ? require('../js/logic/player.js').Player : Player;
  var T = C.TILE, TL = P.TILES;
  var CODES = { left: 'ArrowLeft', right: 'ArrowRight', jump: 'Space', action: 'Enter' };
  var LOOKAHEAD_COLS = 4, CRUISE = 26, CLEARANCE = 10, DANGER_X = 52, DANGER_Y = 22;
  var THREAT_X = 56, THREAT_Y = 18, AIR_PUFF_X = 30;
  var BOSS_HOME_X = 96, PUFF_JUMP_X = 14, APPLE_DODGE_X = 16, APPLE_CHASE_X = 80;

  function create() {
    var mem = { held: {}, lastGroundY: null, inhaleTicks: 0, keyEvents: 0 };

    function solidOrPlatform(t) { return P.isSolid(t) || t === TL.PLATFORM; }

    // y of the first surface at or below the feet in a column, or null for a pit.
    function surface(world, c, feetRow) {
      for (var r = Math.max(0, feetRow); r < world.h; r++) {
        if (solidOrPlatform(P.tileAt(world, c, r))) return r * T;
      }
      return null;
    }

    function tap(want, k) { want[k] = !mem.held[k]; }

    // Hold Enter to inhale; if Enter is still held from an earlier spit, let go first.
    function inhale(want, p) { want.action = p.inhaling || !mem.held.action; }

    function bossFight(state, want) {
      var p = state.player, b = state.boss, world = state.world;
      if (b.state === 'dead') return false;
      var home = world.gateCol * T + BOSS_HOME_X;
      var px = p.x + p.w / 2, pcy = p.y + p.h / 2;
      if (p.jumping) { want.jump = true; return true; }
      if (p.mouth) {
        if (p.facing > 0) tap(want, 'action'); else want.right = true;
        return true;
      }
      var lowPuff = state.enemies.some(function (e) {
        return e.type === 'bosspuff' && e.x - (p.x + p.w) < PUFF_JUMP_X && e.x + e.w > p.x && Math.abs(e.y + e.h / 2 - pcy) < 12;
      });
      if (lowPuff && p.onGround) { tap(want, 'jump'); return true; }
      var overhead = null, roller = null, rollerD = Infinity;
      state.enemies.forEach(function (e) {
        if (e.type !== 'apple' || e.caught) return;
        var dx = e.x + e.w / 2 - px;
        if (!e.onGround && Math.abs(dx) < APPLE_DODGE_X && e.y + e.h <= p.y + 2) overhead = e;
        if (e.rolling && e.onGround && Math.abs(dx) < rollerD && Math.abs(dx) < APPLE_CHASE_X) { rollerD = Math.abs(dx); roller = e; }
      });
      var caught = state.enemies.some(function (e) { return e.caught; });
      if (overhead) { if (overhead.x + overhead.w / 2 <= px) want.right = true; else want.left = true; return true; }
      if (caught) { inhale(want, p); return true; }
      if (roller) {
        var dir = roller.x + roller.w / 2 < px ? -1 : 1;
        if (p.facing !== dir) { if (dir < 0) want.left = true; else want.right = true; return true; }
        inhale(want, p);
        return true;
      }
      if (px < home - 8) want.right = true;
      else if (px > home + 8) want.left = true;
      else if (p.facing < 0) want.right = true;
      return true;
    }

    function decide(state) {
      var want = { left: false, right: false, jump: false, action: false };
      if (state.mode === 'title' || state.mode === 'gameover') { tap(want, 'jump'); return want; }
      if (state.mode !== 'playing') return want;
      var p = state.player, world = state.world;
      mem.inhaleTicks = p.inhaling ? mem.inhaleTicks + 1 : 0;
      if (p.onGround) mem.lastGroundY = p.y + p.h;
      if (mem.lastGroundY === null) mem.lastGroundY = p.y + p.h;

      if (state.arenaLocked && state.boss && bossFight(state, want)) return want;

      var px = p.x + p.w / 2, feet = p.y + p.h;
      var col = Math.floor(px / T), feetRow = Math.floor((feet - 1) / T), midRow = Math.floor((p.y + p.h / 2) / T);
      var aheadCol = Math.floor((p.x + p.w + 2) / T);

      // Warp star: go and touch it.
      if (state.warp && state.warp.active) {
        var wx = state.warp.x + state.warp.w / 2, wy = state.warp.y + state.warp.h / 2;
        if (wx > px + 2) want.right = true; else if (wx < px - 2) want.left = true;
        if (wy < p.y && !p.jumping) tap(want, 'jump');
        if (p.jumping) want.jump = true;
        return want;
      }

      // Mouth full: spit forward straight away (it clears the way and lets Kirby fly again).
      if (p.mouth) {
        want.right = true;
        if (p.facing > 0) tap(want, 'action');
        return want;
      }

      // Star block in front: stop and inhale it.
      var starAhead = P.tileAt(world, aheadCol, midRow) === TL.STAR || P.tileAt(world, aheadCol + 1, midRow) === TL.STAR;
      if (starAhead && p.facing > 0) {
        if (p.flying) tap(want, 'action'); // exhale to stop flying, then inhale
        else inhale(want, p);
        return want;
      }

      // Nearby enemy in front or behind: turn to face it and inhale it (or blow air at it while flying).
      var threat = null, best = Infinity;
      state.enemies.forEach(function (e) {
        if (e.dead || !e.inhalable || e.type === 'loose') return;
        var dx = (e.x + e.w / 2) - px, dy = Math.abs((e.y + e.h / 2) - (p.y + p.h / 2));
        if (e.caught || (Math.abs(dx) < THREAT_X && dy < THREAT_Y)) {
          var d = e.caught ? -1 : Math.abs(dx);
          if (d < best) { best = d; threat = e; }
        }
      });
      var pitBelow = !p.onGround && surface(world, col, feetRow) === null;
      if (threat && mem.inhaleTicks < 120 && !(pitBelow && !p.flying && !threat.caught)) {
        var dir = (threat.x + threat.w / 2) < px ? -1 : 1;
        if (p.facing !== dir && !p.inhaling) {
          if (dir < 0) want.left = true; else want.right = true;
          return want;
        }
        if (p.flying) { if (Math.abs(threat.x - p.x) < AIR_PUFF_X) tap(want, 'action'); }
        else { inhale(want, p); return want; }
      }

      // Navigation: keep moving right, climbing over walls and flying over pits.
      want.right = true;
      var target = Infinity, pit = false;
      for (var c = col; c <= col + LOOKAHEAD_COLS; c++) {
        if (P.isSolid(P.tileAt(world, c, midRow))) break; // a wall: handled below
        var s = surface(world, c, feetRow);
        if (s === null) pit = true;
        else target = Math.min(target, s - CLEARANCE);
      }
      if (pit) target = Math.min(target, mem.lastGroundY - CRUISE);
      function hardWall(r) { var t = P.tileAt(world, aheadCol, r); return P.isSolid(t) && t !== TL.STAR; }
      if (hardWall(midRow) || hardWall(feetRow)) {
        // Find the nearest open row in the wall ahead and head for it (up or down).
        for (var k = 1; k < world.h; k++) {
          if (midRow + k < world.h && !hardWall(midRow + k)) { target = (midRow + k + 1) * T; break; }
          if (midRow - k >= 0 && !hardWall(midRow - k)) { target = (midRow - k + 1) * T - 2; break; }
        }
      }

      // Steer around spikies vertically.
      state.enemies.forEach(function (e) {
        if (e.type !== 'spiky') return;
        var dx = e.x - (p.x + p.w), dy = (e.y + e.h / 2) - (p.y + p.h / 2);
        if (dx > -8 && dx < DANGER_X && Math.abs(dy) < DANGER_Y + e.h / 2) {
          if (dy > 0) target = Math.min(target, e.y - 4);
          else if (!p.onGround) target = Math.max(target, e.y + e.h + p.h + 4);
        }
      });

      var needUp = feet > target;
      if (p.jumping) want.jump = needUp || p.vy < -2;
      else if (needUp && (p.onGround || p.vy > -0.6)) tap(want, 'jump');
      return want;
    }

    function apply(state, input) {
      var want = decide(state);
      for (var k in CODES) {
        if (want[k] && !mem.held[k]) { input.keyDown(CODES[k]); mem.keyEvents++; }
        if (!want[k] && mem.held[k]) { input.keyUp(CODES[k]); mem.keyEvents++; }
        mem.held[k] = want[k];
      }
    }

    function releaseAll(input) {
      for (var k in CODES) if (mem.held[k]) input.keyUp(CODES[k]);
      mem.held = {};
    }

    return { apply: apply, releaseAll: releaseAll, mem: mem };
  }

  return { create: create, CODES: CODES };
})();

if (typeof module !== 'undefined') module.exports = { KirbyBot };

// Turns level data (sections of tile placements) into a playable world. Pure logic.
var World = (function () {
  'use strict';
  var C = typeof CONST !== 'undefined' ? CONST : require('./constants.js').CONST;
  var P = typeof Physics !== 'undefined' ? Physics : require('./physics.js').Physics;
  var T = C.TILE, TL = P.TILES;

  var CHAR_TILES = { '#': TL.GROUND, '=': TL.STONE, '-': TL.PLATFORM, 'S': TL.STAR, '^': TL.SPIKES, ' ': TL.EMPTY };
  var ENEMY_CHARS = { w: 'walker', f: 'flyer', h: 'hopper', g: 'spiky', q: 'spiky' };
  var ITEM_CHARS = { o: 'star', T: 'food', '1': 'oneup' };

  function build(level) {
    var h = level.height;
    var w = level.sections.reduce(function (s, sec) { return s + sec.width; }, 0);
    var world = {
      w: w, h: h, tiles: new Uint8Array(w * h), groundRow: level.groundRow,
      spawns: [], items: [], checkpoints: [], signs: [], gaps: [], winds: [], caves: [], sections: [],
      start: null, bossSpawn: null, warp: null, gateCol: -1
    };
    var x0 = 0;

    level.sections.forEach(function (sec) {
      function place(ch, col, row) {
        if (col < 0 || col >= sec.width || row < 0 || row >= h) {
          throw new Error('Section "' + sec.name + '": placement out of bounds at ' + col + ',' + row);
        }
        var ax = x0 + col;
        if (CHAR_TILES[ch] !== undefined) { world.tiles[row * w + ax] = CHAR_TILES[ch]; return; }
        var px = ax * T, py = row * T;
        if (ENEMY_CHARS[ch]) {
          world.spawns.push({ type: ENEMY_CHARS[ch], col: ax, row: row, patrol: ch === 'q' });
        } else if (ITEM_CHARS[ch]) {
          world.items.push({ id: world.items.length, kind: ITEM_CHARS[ch], x: px + 3, y: py + 3, w: 10, h: 10 });
        } else if (ch === 'C') {
          world.checkpoints.push({ x: px + 4, y: py + T - 24, w: 8, h: 24 });
        } else if (ch === 'P') {
          world.start = { x: px + 2, y: py + T - C.PLAYER_H };
        } else if (ch === 'B') {
          world.bossSpawn = { x: px, y: py + T - C.BOSS_H };
        } else if (ch === 'W') {
          world.warp = { x: px - 4, y: py - 4, w: 24, h: 24 };
        } else if (ch === 'A') {
          world.gateCol = ax;
        } else {
          throw new Error('Section "' + sec.name + '": unknown level character "' + ch + '"');
        }
      }

      world.sections.push({ name: sec.name, x0: x0 * T, x1: (x0 + sec.width) * T });

      for (var c = 0; c < sec.width; c++) {
        var inGap = (sec.gaps || []).some(function (g) { return c >= g[0] && c < g[1]; });
        if (inGap) continue;
        for (var r = level.groundRow; r < h; r++) world.tiles[r * w + x0 + c] = TL.GROUND;
      }
      (sec.ceiling || []).forEach(function (cl) {
        for (var cc = cl[0]; cc < cl[1]; cc++) for (var rr = 0; rr <= cl[2]; rr++) place('=', cc, rr);
        world.caves.push({ x0: (x0 + cl[0]) * T, x1: (x0 + cl[1]) * T, top: (cl[2] + 1) * T });
      });
      (sec.fill || []).forEach(function (f) {
        for (var i = 0; i < f[2]; i++) for (var j = 0; j < f[3]; j++) place(f[4], f[0] + i, f[1] + j);
      });
      (sec.put || []).forEach(function (pt) {
        for (var i = 0; i < pt[2].length; i++) if (pt[2][i] !== '.') place(pt[2][i], pt[0] + i, pt[1]);
      });
      (sec.signs || []).forEach(function (s) {
        world.signs.push({ x: (x0 + s[0]) * T + T / 2, text: s[1] });
      });
      if (sec.wind) world.winds.push({ x0: x0 * T, x1: (x0 + sec.width) * T, strength: sec.wind });
      x0 += sec.width;
    });

    if (!world.start) throw new Error('Level has no player start (P)');
    world.checkpoints.sort(function (a, b) { return a.x - b.x; });
    world.checkpoints.forEach(function (cp, i) { cp.index = i; });

    // Gaps are runs of columns with no floor in the bottom row: falling there is a pit.
    var run = -1;
    for (var col = 0; col <= w; col++) {
      var open = col < w && !P.isSolid(world.tiles[(h - 1) * w + col]);
      if (open && run < 0) run = col;
      if (!open && run >= 0) { world.gaps.push({ x0: run * T, x1: col * T }); run = -1; }
    }
    // The arena's open area starts below its ceiling; apples drop from there.
    world.arenaTop = 0;
    if (world.gateCol >= 0) {
      var r0 = 0;
      while (r0 < h && P.isSolid(world.tiles[r0 * w + world.gateCol + 1])) r0++;
      world.arenaTop = r0 * T;
    }
    world.original = world.tiles.slice();
    return world;
  }

  function resetTiles(world) {
    world.tiles.set(world.original);
  }

  // Signed horizontal wind push (px/tick) at a position and time.
  function windAt(world, x, time) {
    for (var i = 0; i < world.winds.length; i++) {
      var wd = world.winds[i];
      if (x >= wd.x0 && x < wd.x1) {
        var gust = C.WIND_GUST_MIN + (1 - C.WIND_GUST_MIN) * (0.5 + 0.5 * Math.sin(time * 2 * Math.PI / C.WIND_GUST_PERIOD));
        return wd.strength * gust;
      }
    }
    return 0;
  }

  function sectionIndexAt(world, x) {
    for (var i = 0; i < world.sections.length; i++) {
      if (x < world.sections[i].x1) return i;
    }
    return world.sections.length - 1;
  }

  // Small deterministic RNG (mulberry32) so runs and tests are reproducible.
  function rand(state) {
    state.rngState = (state.rngState + 0x6D2B79F5) | 0;
    var t = state.rngState;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }

  // Logic reports what happened through events; the renderer and audio react to them.
  function emit(state, type, x, y, extra) {
    var ev = { type: type, x: x || 0, y: y || 0 };
    if (extra) for (var k in extra) ev[k] = extra[k];
    state.events.push(ev);
    return ev;
  }

  function addScore(state, n) {
    state.score += n;
    if (!state.extraLifeAwarded && state.score >= C.EXTRA_LIFE_SCORE) {
      state.extraLifeAwarded = true;
      state.lives += 1;
      emit(state, 'oneUp', state.player.x, state.player.y);
    }
  }

  return {
    build: build,
    resetTiles: resetTiles,
    windAt: windAt,
    sectionIndexAt: sectionIndexAt,
    rand: rand,
    emit: emit,
    addScore: addScore
  };
})();

if (typeof module !== 'undefined') module.exports = { World };

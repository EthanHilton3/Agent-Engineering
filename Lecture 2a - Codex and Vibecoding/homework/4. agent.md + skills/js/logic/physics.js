// Tile collision and movement. Pure logic: no DOM, no canvas.
var Physics = (function () {
  'use strict';
  var C = typeof CONST !== 'undefined' ? CONST : require('./constants.js').CONST;
  var T = C.TILE;
  var EPS = 0.001;

  var TILES = { EMPTY: 0, GROUND: 1, STONE: 2, PLATFORM: 3, STAR: 4, SPIKES: 5 };

  function isSolid(t) {
    return t === TILES.GROUND || t === TILES.STONE || t === TILES.STAR || t === TILES.SPIKES;
  }

  // Outside the level sideways is a wall; above and below is open air.
  function tileAt(world, tx, ty) {
    if (tx < 0 || tx >= world.w) return TILES.STONE;
    if (ty < 0 || ty >= world.h) return TILES.EMPTY;
    return world.tiles[ty * world.w + tx];
  }

  function setTile(world, tx, ty, t) {
    if (tx < 0 || tx >= world.w || ty < 0 || ty >= world.h) return;
    world.tiles[ty * world.w + tx] = t;
  }

  function solidAtPoint(world, x, y) {
    return isSolid(tileAt(world, Math.floor(x / T), Math.floor(y / T)));
  }

  function overlaps(a, b) {
    return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
  }

  function stepX(world, body, dx) {
    var nx = body.x + dx;
    var top = Math.floor(body.y / T);
    var bottom = Math.floor((body.y + body.h - EPS) / T);
    var col = dx > 0 ? Math.floor((nx + body.w - EPS) / T) : Math.floor(nx / T);
    for (var r = top; r <= bottom; r++) {
      if (isSolid(tileAt(world, col, r))) {
        body.x = dx > 0 ? col * T - body.w : (col + 1) * T;
        body.vx = 0;
        body.hitWall = dx > 0 ? 1 : -1;
        return false;
      }
    }
    body.x = nx;
    return true;
  }

  function stepY(world, body, dy) {
    var ny = body.y + dy;
    var left = Math.floor(body.x / T);
    var right = Math.floor((body.x + body.w - EPS) / T);
    if (dy > 0) {
      var row = Math.floor((ny + body.h - EPS) / T);
      var rowTop = row * T;
      var wasAbove = body.y + body.h <= rowTop + EPS;
      for (var c = left; c <= right; c++) {
        var t = tileAt(world, c, row);
        if (isSolid(t) || (t === TILES.PLATFORM && wasAbove)) {
          body.y = rowTop - body.h;
          body.vy = 0;
          body.onGround = true;
          return false;
        }
      }
    } else {
      var rowUp = Math.floor(ny / T);
      for (var c2 = left; c2 <= right; c2++) {
        if (isSolid(tileAt(world, c2, rowUp))) {
          body.y = (rowUp + 1) * T;
          body.vy = 0;
          body.hitCeiling = true;
          return false;
        }
      }
    }
    body.y = ny;
    return true;
  }

  // Moves a body by its velocity (plus any pushX, such as wind) in small sub-steps,
  // resolving x then y each sub-step. Sets onGround, hitWall and hitCeiling.
  function moveBody(world, body) {
    body.onGround = false;
    body.hitWall = 0;
    body.hitCeiling = false;
    var dx = body.vx + (body.pushX || 0);
    var dy = body.vy;
    var steps = Math.max(1, Math.ceil(Math.max(Math.abs(dx), Math.abs(dy)) / C.MAX_SUBSTEP));
    var sx = dx / steps, sy = dy / steps;
    for (var i = 0; i < steps; i++) {
      if (sx !== 0 && !stepX(world, body, sx)) sx = 0;
      if (sy !== 0 && !stepY(world, body, sy)) sy = 0;
    }
  }

  // True when the body stands on a spike tile.
  function onSpikes(world, body) {
    if (!body.onGround) return false;
    var row = Math.round((body.y + body.h) / T);
    var left = Math.floor(body.x / T);
    var right = Math.floor((body.x + body.w - EPS) / T);
    for (var c = left; c <= right; c++) {
      if (tileAt(world, c, row) === TILES.SPIKES) return true;
    }
    return false;
  }

  // Samples points along a segment; true when no solid tile is in the way.
  // Points inside skipBox (the target itself) are ignored.
  function clearLine(world, x0, y0, x1, y1, skipBox) {
    var len = Math.hypot(x1 - x0, y1 - y0);
    var n = Math.max(1, Math.ceil(len / C.LOS_STEP));
    for (var i = 1; i < n; i++) {
      var x = x0 + (x1 - x0) * i / n, y = y0 + (y1 - y0) * i / n;
      if (skipBox && x >= skipBox.x && x < skipBox.x + skipBox.w && y >= skipBox.y && y < skipBox.y + skipBox.h) continue;
      if (isSolid(tileAt(world, Math.floor(x / T), Math.floor(y / T)))) return false;
    }
    return true;
  }

  return {
    TILES: TILES,
    isSolid: isSolid,
    tileAt: tileAt,
    setTile: setTile,
    solidAtPoint: solidAtPoint,
    overlaps: overlaps,
    moveBody: moveBody,
    onSpikes: onSpikes,
    clearLine: clearLine
  };
})();

if (typeof module !== 'undefined') module.exports = { Physics };

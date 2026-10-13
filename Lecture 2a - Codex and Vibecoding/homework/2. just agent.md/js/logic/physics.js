// Tile collision. Bodies are axis-aligned boxes { x, y, w, h, vx, vy } with x,y at the top-left.
var KB = (typeof KB !== 'undefined') ? KB : {};
if (typeof module !== 'undefined') Object.assign(KB, require('./constants.js'));

KB.Physics = (function () {
  const C = KB.C;
  const T = C.T;
  const EPS = 0.001;

  // The world: `tiles` is the live tile array (star blocks can disappear), `level` gives the size.
  function tileAt(world, tx, ty) {
    if (tx < 0 || tx >= world.w) return T.BRICK;  // invisible walls at both ends
    if (ty < 0 || ty >= world.h) return T.EMPTY;  // open sky above, pits below
    return world.tiles[ty * world.w + tx];
  }
  function setTile(world, tx, ty, t) {
    if (tx >= 0 && tx < world.w && ty >= 0 && ty < world.h) world.tiles[ty * world.w + tx] = t;
  }
  function isSolid(t) { return t === T.GROUND || t === T.BRICK || t === T.STAR_BLOCK; }
  function isSolidAt(world, tx, ty) { return isSolid(tileAt(world, tx, ty)); }

  function overlaps(a, b) {
    return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
  }

  function stepX(body, world, sx) {
    const S = C.TILE;
    const nx = body.x + sx;
    const ty0 = Math.floor(body.y / S), ty1 = Math.floor((body.y + body.h - EPS) / S);
    const tx = sx > 0 ? Math.floor((nx + body.w - EPS) / S) : Math.floor(nx / S);
    for (let ty = ty0; ty <= ty1; ty++) {
      if (isSolidAt(world, tx, ty)) {
        body.x = sx > 0 ? tx * S - body.w : (tx + 1) * S;
        body.vx = 0;
        body.hitWall = sx > 0 ? 1 : -1;
        return true;
      }
    }
    body.x = nx;
    return false;
  }

  function stepY(body, world, sy) {
    const S = C.TILE;
    const ny = body.y + sy;
    const tx0 = Math.floor(body.x / S), tx1 = Math.floor((body.x + body.w - EPS) / S);
    const ty = sy > 0 ? Math.floor((ny + body.h - EPS) / S) : Math.floor(ny / S);
    for (let tx = tx0; tx <= tx1; tx++) {
      const t = tileAt(world, tx, ty);
      // Clouds only stop you from above: your feet must have been at or over the cloud top.
      const cloudStops = t === T.CLOUD && sy > 0 && body.y + body.h <= ty * S + EPS;
      if (isSolid(t) || cloudStops) {
        if (sy > 0) { body.y = ty * S - body.h; body.onGround = true; }
        else { body.y = (ty + 1) * S; body.hitCeiling = true; }
        body.vy = 0;
        return true;
      }
    }
    body.y = ny;
    return false;
  }

  // Move a body by (dx, dy) in sub-steps no larger than MAX_SUBSTEP so fast bodies can't skip tiles.
  function moveBody(body, world, dx, dy) {
    body.onGround = false;
    body.hitWall = 0;
    body.hitCeiling = false;
    const steps = Math.max(1, Math.ceil(Math.max(Math.abs(dx), Math.abs(dy)) / C.MAX_SUBSTEP));
    const sx = dx / steps, sy = dy / steps;
    let blockedX = false, blockedY = false;
    for (let i = 0; i < steps; i++) {
      if (!blockedX && sx !== 0) blockedX = stepX(body, world, sx);
      if (!blockedY && sy !== 0) blockedY = stepY(body, world, sy);
    }
    return body;
  }

  // True if a box overlaps any solid tile.
  function boxHitsSolid(world, x, y, w, h) {
    const S = C.TILE;
    for (let ty = Math.floor(y / S); ty <= Math.floor((y + h - EPS) / S); ty++) {
      for (let tx = Math.floor(x / S); tx <= Math.floor((x + w - EPS) / S); tx++) {
        if (isSolidAt(world, tx, ty)) return true;
      }
    }
    return false;
  }

  // Is there floor under the point (x, y)? Used by walkers to turn at ledges.
  function hasFloorAt(world, x, y) {
    const t = tileAt(world, Math.floor(x / C.TILE), Math.floor(y / C.TILE));
    return isSolid(t) || t === T.CLOUD;
  }

  // Walk the line between two points; true if no solid tile (other than `ignore` tiles) is in the way.
  function lineOfSight(world, x0, y0, x1, y1, ignore) {
    const S = C.TILE;
    const dist = Math.hypot(x1 - x0, y1 - y0);
    const steps = Math.max(1, Math.ceil(dist / (S / 4)));
    for (let i = 1; i < steps; i++) {
      const tx = Math.floor((x0 + (x1 - x0) * i / steps) / S);
      const ty = Math.floor((y0 + (y1 - y0) * i / steps) / S);
      if (ignore && ignore.tx === tx && ignore.ty === ty) continue;
      if (isSolidAt(world, tx, ty)) return false;
    }
    return true;
  }

  return { tileAt, setTile, isSolid, isSolidAt, overlaps, moveBody, boxHitsSolid, hasFloorAt, lineOfSight };
})();

if (typeof module !== 'undefined') module.exports = { Physics: KB.Physics };

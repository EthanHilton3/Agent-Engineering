const test = require('node:test');
const assert = require('node:assert/strict');
const { C, S } = require('./helpers.js');
const { Physics } = require('../js/logic/physics.js');
const { Level } = require('../js/level.js');

function world(rows) {
  const l = Level.parse(rows);
  return { w: l.w, h: l.h, tiles: l.tiles.slice() };
}
const body = (x, y) => ({ x, y, w: 12, h: 14, vx: 0, vy: 0 });

test('fast horizontal movement stops at a one-tile wall instead of tunnelling', () => {
  const w = world([
    '..........',
    'P....#....',
    '##########',
  ]);
  const b = body(0, S * 2 - 14);
  Physics.moveBody(b, w, 500, 0);  // far more than a tile in one call
  assert.equal(b.x, 5 * S - b.w);
  assert.equal(b.hitWall, 1);
});

test('fast fall lands on a one-tile-thick floor instead of passing through', () => {
  const w = world([
    'P.........',
    '..........',
    '..........',
    '##########',
    '..........',
    '..........',
  ]);
  const b = body(16, 0);
  Physics.moveBody(b, w, 0, 400);
  assert.equal(b.y + b.h, 3 * S);
  assert.equal(b.onGround, true);
});

test('fast diagonal movement does not slip through a corner gap', () => {
  const w = world([
    'P.........',
    '.....#....',
    '.....#....',
    '##########',
  ]);
  const b = body(0, 0);
  Physics.moveBody(b, w, 300, 300);
  assert.ok(b.x + b.w <= 5 * S, 'stays left of the pillar');
  assert.equal(b.y + b.h, 3 * S, 'lands on the floor');
});

test('moving up into a ceiling stops and flags it', () => {
  const w = world([
    '##########',
    'P.........',
    '..........',
    '##########',
  ]);
  const b = body(16, 2 * S);
  Physics.moveBody(b, w, 0, -100);
  assert.equal(b.y, S);
  assert.equal(b.hitCeiling, true);
});

test('clouds can be jumped through from below but stood on from above', () => {
  const w = world([
    'P.........',
    '..........',
    '..====....',
    '..........',
    '##########',
  ]);
  const up = body(40, 3 * S);
  Physics.moveBody(up, w, 0, -40);
  assert.ok(up.y < 2 * S, 'passes up through the cloud');
  const down = body(40, 0);
  Physics.moveBody(down, w, 0, 100);
  assert.equal(down.y + down.h, 2 * S, 'lands on top of the cloud');
  assert.equal(down.onGround, true);
});

test('the level edges are walls and the space below the level is open', () => {
  const w = world(['P..', '###']);
  assert.ok(Physics.isSolidAt(w, -1, 0));
  assert.ok(Physics.isSolidAt(w, 3, 0));
  assert.equal(Physics.isSolidAt(w, 1, 5), false);
});

test('line of sight is blocked by solid tiles', () => {
  const w = world([
    'P...#....',
    '#########',
  ]);
  assert.equal(Physics.lineOfSight(w, 8, 8, 56, 8), true);
  assert.equal(Physics.lineOfSight(w, 8, 8, 120, 8), false);
});

test('the real level parses, has a start, a goal and several gaps', () => {
  const l = Level.load();
  assert.equal(l.h, Level.ROWS);
  assert.ok(l.start && l.goal);
  assert.ok(Level.findGaps(l).length >= 4);
  const kinds = new Set(l.enemies.map(e => e.kind));
  assert.ok(kinds.has('walker') && kinds.has('flyer'), 'has walking and flying enemies');
});

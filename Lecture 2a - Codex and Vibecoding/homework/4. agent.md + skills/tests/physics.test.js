const test = require('node:test');
const assert = require('node:assert/strict');
const { Physics, World, T, level, FLOOR_Y } = require('./helpers.js');

function body(x, y, vx, vy) {
  return { x, y, w: 12, h: 12, vx, vy };
}

test('a very fast body stops at a one-tile wall instead of tunnelling through it', () => {
  const world = World.build(level({ put: [[2, 8, 'P'], [10, 8, '#']] }));
  // The wall is 84px away: every one of these speeds would skip past it in a single naive step.
  for (const speed of [100, 250, 1000, 5000]) {
    const b = body(4 * T, 8 * T + 2, speed, 0);
    Physics.moveBody(world, b);
    assert.equal(b.x, 10 * T - b.w, `speed ${speed}`);
    assert.equal(b.hitWall, 1);
    assert.equal(b.vx, 0);
  }
});

test('moving left into a wall also stops flush against it', () => {
  const world = World.build(level({ put: [[2, 8, 'P'], [3, 8, '#']] }));
  const b = body(12 * T, 8 * T + 2, -300, 0);
  Physics.moveBody(world, b);
  assert.equal(b.x, 4 * T);
  assert.equal(b.hitWall, -1);
});

test('a very fast fall lands on a one-tile floor instead of passing through', () => {
  const world = World.build(level({ gaps: [[0, 40]], put: [[2, 8, 'P'], [6, 6, '#']] }));
  const b = body(6 * T + 2, 0, 0, 250);
  Physics.moveBody(world, b);
  assert.equal(b.y, 6 * T - b.h);
  assert.equal(b.onGround, true);
});

test('a fast upward move stops under a one-tile ceiling', () => {
  const world = World.build(level({ put: [[2, 8, 'P'], [6, 3, '=']] }));
  const b = body(6 * T + 2, 7 * T, 0, -200);
  Physics.moveBody(world, b);
  assert.equal(b.y, 4 * T);
  assert.equal(b.hitCeiling, true);
});

test('diagonal speed is split into sub-steps no bigger than MAX_SUBSTEP', () => {
  const world = World.build(level({ put: [[2, 8, 'P'], [12, 7, '##'], [12, 8, '##']] }));
  const b = body(4 * T, 7 * T, 90, 30);
  Physics.moveBody(world, b);
  assert.ok(b.x + b.w <= 12 * T, 'went through the block');
});

test('one-way platforms hold you from above but let you jump up through them', () => {
  const world = World.build(level({ put: [[2, 8, 'P'], [6, 6, '---']] }));
  const falling = body(6 * T + 2, 6 * T - 20, 0, 12);
  Physics.moveBody(world, falling);
  assert.equal(falling.y, 6 * T - 12);
  assert.equal(falling.onGround, true);
  const rising = body(6 * T + 2, 7 * T, 0, -12);
  Physics.moveBody(world, rising);
  assert.equal(rising.y, 7 * T - 12, 'should pass through from below');
});

test('the level edges act as walls; the ground stops falling bodies', () => {
  const world = World.build(level({}));
  const b = body(10, FLOOR_Y - 30, -50, 50);
  Physics.moveBody(world, b);
  assert.equal(b.x, 0);
  assert.equal(b.y, FLOOR_Y - 12);
});

test('gaps in the level are detected as pits', () => {
  const world = World.build(level({ gaps: [[5, 8], [20, 21]] }));
  assert.deepEqual(world.gaps, [{ x0: 5 * T, x1: 8 * T }, { x0: 20 * T, x1: 21 * T }]);
});

test('line of sight is blocked by solid tiles', () => {
  const world = World.build(level({ put: [[2, 8, 'P'], [6, 7, '=']] }));
  assert.equal(Physics.clearLine(world, 4 * T, 7.5 * T, 9 * T, 7.5 * T), false);
  assert.equal(Physics.clearLine(world, 4 * T, 5.5 * T, 9 * T, 5.5 * T), true);
});

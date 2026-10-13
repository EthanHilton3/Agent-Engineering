// Jumping, flying and their limits.
const test = require('node:test');
const assert = require('node:assert/strict');
const { CONST, Game, playing, run, settle, keys, NONE, JUMP, eventsDuring, FLOOR_Y } = require('./helpers.js');

const HOLD_JUMP = keys({ jump: true });

function jumpHeight(state, hold) {
  settle(state);
  const y0 = state.player.y;
  let minY = y0;
  Game.update(state, JUMP);
  for (let i = 0; i < 200 && !state.player.onGround; i++) {
    Game.update(state, i < hold ? HOLD_JUMP : NONE);
    minY = Math.min(minY, state.player.y);
  }
  return y0 - minY;
}

test('a held jump reaches the expected height, under three tiles', () => {
  const s = playing();
  const h = jumpHeight(s, 100);
  const expected = CONST.JUMP_VY * CONST.JUMP_VY / (2 * CONST.GRAVITY);
  assert.ok(Math.abs(h - expected) < 4, `jump height ${h}, expected about ${expected}`);
  assert.ok(h < 3 * CONST.TILE);
});

test('releasing Space early gives a shorter jump', () => {
  const s = playing();
  const tall = jumpHeight(s, 100);
  const short = jumpHeight(s, 2);
  assert.ok(short < tall * 0.6, `short ${short} vs tall ${tall}`);
});

test('tapping Space in the air starts flying and each flap rises at a capped speed', () => {
  const s = playing();
  settle(s);
  Game.update(s, JUMP);
  run(s, 5, HOLD_JUMP);
  Game.update(s, JUMP);
  assert.equal(s.player.flying, true);
  assert.ok(s.player.vy >= CONST.FLAP_VY - 1e-9, 'a flap must not exceed FLAP_VY');
});

test('flight is unlimited: hundreds of flaps keep Kirby airborne', () => {
  const s = playing();
  settle(s);
  let airborneAfter = 0;
  for (let i = 0; i < 400; i++) {
    Game.update(s, i % 12 === 0 ? JUMP : NONE);
    if (i > 30 && !s.player.onGround) airborneAfter++;
  }
  assert.equal(s.player.flying, true);
  assert.equal(airborneAfter, 400 - 31);
});

test('flying can never go above the fly ceiling', () => {
  const s = playing();
  settle(s);
  let minY = Infinity;
  for (let i = 0; i < 600; i++) {
    Game.update(s, i % 4 === 0 ? JUMP : NONE);
    minY = Math.min(minY, s.player.y);
  }
  assert.equal(minY, CONST.FLY_CEILING);
});

test('falling while flying is slow (floaty) and landing deflates', () => {
  const s = playing();
  settle(s);
  Game.update(s, JUMP);
  run(s, 5);
  Game.update(s, JUMP);
  let maxFall = 0;
  const seen = eventsDuring(s, 300, () => { maxFall = Math.max(maxFall, s.player.vy); return NONE; });
  assert.ok(maxFall <= CONST.FLY_MAX_FALL + 1e-9);
  assert.ok(seen.some((e) => e.type === 'deflate'));
  assert.equal(s.player.flying, false);
});

test('with a full mouth Kirby cannot fly: Space in the air does nothing but warn', () => {
  const s = playing();
  settle(s);
  s.player.mouth = { kind: 'walker', count: 1 };
  Game.update(s, JUMP);
  run(s, 10);
  const seen = eventsDuring(s, 1, JUMP);
  assert.equal(s.player.flying, false);
  assert.ok(seen.some((e) => e.type === 'noFly'));
  settle(s);
  assert.equal(s.player.y, FLOOR_Y - CONST.PLAYER_H);
});

test('a full mouth also makes Kirby jump lower and run slower', () => {
  const s = playing();
  const normal = jumpHeight(s, 100);
  s.player.mouth = { kind: 'walker', count: 1 };
  const full = jumpHeight(s, 100);
  assert.ok(full < normal * 0.75, `full ${full} vs normal ${normal}`);
  run(s, 120, keys({ right: true }));
  assert.ok(Math.abs(s.player.vx) <= CONST.FULL_MAX_SPEED + 1e-9);
});

test('running accelerates to RUN_MAX and no further', () => {
  const s = playing();
  settle(s);
  run(s, 60, keys({ right: true }));
  assert.equal(s.player.vx, CONST.RUN_MAX);
  assert.equal(s.player.facing, 1);
});

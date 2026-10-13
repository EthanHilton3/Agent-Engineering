// Inhale cone, swallowing, spitting and star blocks.
const test = require('node:test');
const assert = require('node:assert/strict');
const {
  CONST, Physics, Player, Enemies, playing, run, settle, keys, NONE, ACTION, HOLD_ACTION, eventsDuring
} = require('./helpers.js');

function kirbyAt(x, y, facing) {
  const p = Player.create(x, y);
  p.facing = facing;
  return p;
}
function box(cx, cy, size) {
  return { x: cx - (size || 12) / 2, y: cy - (size || 12) / 2, w: size || 12, h: size || 12 };
}

test('inhale cone: in front and in range is inside; behind or too far is outside', () => {
  const p = kirbyAt(100, 100, 1);
  const m = Player.mouthPoint(p);
  assert.equal(Player.inInhaleCone(p, box(m.x + 20, m.y)), true);
  assert.equal(Player.inInhaleCone(p, box(m.x + CONST.INHALE_RANGE - 1, m.y)), true);
  assert.equal(Player.inInhaleCone(p, box(m.x + CONST.INHALE_RANGE + 2, m.y)), false);
  assert.equal(Player.inInhaleCone(p, box(m.x - 20, m.y)), false, 'behind Kirby');
});

test('inhale cone widens with distance', () => {
  const p = kirbyAt(100, 100, 1);
  const m = Player.mouthPoint(p);
  const dy = CONST.INHALE_HALF_HEIGHT + 8;
  assert.equal(Player.inInhaleCone(p, box(m.x + 4, m.y - dy)), false, 'too high near the mouth');
  assert.equal(Player.inInhaleCone(p, box(m.x + 50, m.y - dy)), true, 'same height further out is inside');
});

test('inhale cone follows the facing direction', () => {
  const p = kirbyAt(100, 100, -1);
  const m = Player.mouthPoint(p);
  assert.equal(m.x, 100);
  assert.equal(Player.inInhaleCone(p, box(m.x - 20, m.y)), true);
  assert.equal(Player.inInhaleCone(p, box(m.x + 30, m.y)), false);
});

test('holding Enter pulls a walker in and swallows it: mouth fills and score goes up', () => {
  const s = playing({ put: [[2, 8, 'P'], [6, 8, 'w']] });
  settle(s);
  const score = s.score;
  const seen = eventsDuring(s, 90, HOLD_ACTION);
  assert.ok(seen.some((e) => e.type === 'swallow'));
  assert.deepEqual(s.player.mouth, { kind: 'walker', count: 1 });
  assert.equal(s.score - score, CONST.SCORE.walker);
  assert.equal(s.enemies.filter((e) => e.type === 'walker').length, 0);
  assert.equal(s.player.inhaling, false, 'inhaling stops once something is swallowed');
});

test('enemies behind Kirby are not pulled in', () => {
  const s = playing({ put: [[8, 8, 'P'], [4, 8, 'w']] });
  settle(s);
  const w = s.enemies[0];
  s.player.facing = 1;
  s.player.inhaling = true;
  Player.applyInhale(s);
  assert.equal(w.caught, false);
});

test('a spiky enemy inside the cone is never pulled in', () => {
  const s = playing({ put: [[2, 8, 'P'], [5, 8, 'g']] });
  settle(s);
  const spiky = s.enemies[0];
  const p = s.player;
  spiky.y = p.y + p.h / 2 - spiky.h / 2;
  assert.equal(Player.inInhaleCone(p, spiky), true, 'test setup: spiky is in the cone');
  p.inhaling = true;
  for (let i = 0; i < 60; i++) Player.applyInhale(s);
  assert.equal(spiky.caught, false);
  assert.equal(p.mouth, null);
});

test('walls block the inhale (line of sight)', () => {
  const s = playing({ put: [[2, 8, 'P'], [5, 7, '='], [5, 8, '='], [7, 8, 'w']] });
  settle(s);
  run(s, 100, HOLD_ACTION);
  assert.equal(s.player.mouth, null);
  assert.equal(s.enemies.filter((e) => e.type === 'walker').length, 1);
});

test('Kirby cannot walk while inhaling', () => {
  const s = playing();
  settle(s);
  run(s, 30, keys({ right: true }));
  run(s, 40, keys({ right: true, action: true }));
  assert.equal(s.player.inhaling, true);
  assert.equal(s.player.vx, 0);
});

test('pressing Enter with a full mouth spits a star that defeats another enemy', () => {
  const s = playing({ put: [[2, 8, 'P'], [6, 8, 'w'], [16, 8, 'w']] });
  settle(s);
  run(s, 90, HOLD_ACTION);
  assert.ok(s.player.mouth);
  run(s, 1, NONE);
  const before = s.score;
  const seen = eventsDuring(s, 1, ACTION);
  assert.equal(s.player.mouth, null);
  assert.ok(seen.some((e) => e.type === 'spit'));
  assert.equal(s.projectiles.length, 1);
  assert.equal(s.projectiles[0].kind, 'star');
  assert.equal(s.projectiles[0].vx, CONST.SPIT_SPEED);
  const later = eventsDuring(s, 60, NONE);
  assert.ok(later.some((e) => e.type === 'defeat' && e.kind === 'walker'));
  assert.equal(s.score - before, CONST.SCORE.walker);
  assert.equal(s.projectiles.length, 0, 'star is used up by the hit');
});

test('after spitting, Enter must be released before Kirby can inhale again', () => {
  const s = playing({ put: [[2, 8, 'P'], [6, 8, 'w']] });
  settle(s);
  run(s, 90, HOLD_ACTION);
  run(s, 1, NONE);
  run(s, 1, ACTION);
  run(s, 20, HOLD_ACTION);
  assert.equal(s.player.inhaling, false, 'still holding from the spit press');
  run(s, 1, NONE);
  run(s, 2, ACTION);
  assert.equal(s.player.inhaling, true);
});

test('inhaling a star block takes one block out of the wall; the spit star breaks the next', () => {
  const s = playing({ fill: [[5, 7, 1, 2, 'S'], [9, 7, 1, 2, 'S']] });
  settle(s);
  const score = s.score;
  run(s, 60, HOLD_ACTION);
  assert.deepEqual(s.player.mouth, { kind: 'block', count: 1 });
  assert.equal(Physics.tileAt(s.world, 5, 8), Physics.TILES.EMPTY, 'block at Kirby height is gone');
  assert.equal(Physics.tileAt(s.world, 5, 7), Physics.TILES.STAR, 'the block above stays');
  assert.equal(s.score - score, CONST.SCORE.block);
  run(s, 1, NONE);
  const seen = eventsDuring(s, 40, (i) => (i === 0 ? ACTION : NONE));
  assert.ok(seen.some((e) => e.type === 'blockBreak'));
  assert.equal(Physics.tileAt(s.world, 9, 8), Physics.TILES.EMPTY);
});

test('getting hit with a full mouth drops the swallowed thing, which can be inhaled again', () => {
  const s = playing();
  settle(s);
  s.player.mouth = { kind: 'walker', count: 1 };
  Player.hurt(s, s.player.x - 10);
  assert.equal(s.player.mouth, null);
  const loose = s.enemies.find((e) => e.type === 'loose');
  assert.ok(loose && loose.inhalable && !loose.harmful);
  s.player.invuln = 0;
  s.player.hurtTimer = 0;
  run(s, 40);
  loose.x = s.player.x + s.player.w + 6;
  loose.y = s.player.y;
  loose.vx = 0;
  run(s, 30, HOLD_ACTION);
  assert.deepEqual(s.player.mouth, { kind: 'walker', count: 1 });
});

test('swallowing two things at once makes a big star that pierces', () => {
  const s = playing({ put: [[2, 8, 'P'], [6, 8, 'w'], [7, 8, 'w']] });
  settle(s);
  const p = s.player;
  const m = Player.mouthPoint(p);
  s.enemies.forEach((e) => { e.x = m.x + 1; e.y = m.y - e.h / 2; });
  p.inhaling = true;
  Player.applyInhale(s);
  assert.deepEqual(p.mouth, { kind: 'walker', count: 2 });
  run(s, CONST.SWALLOW_LOCK_TICKS, NONE);
  run(s, 1, ACTION);
  assert.equal(s.projectiles[0].big, true);
  assert.equal(s.projectiles[0].pierce, true);
});

test('releasing Enter lets go of a half-inhaled enemy, which is stunned briefly', () => {
  const s = playing({ put: [[2, 8, 'P'], [6, 8, 'w']] });
  settle(s);
  run(s, 3, HOLD_ACTION);
  const w = s.enemies[0];
  assert.equal(w.caught, true);
  run(s, 1, NONE);
  assert.equal(w.caught, false);
  assert.ok(w.stun > 0);
});

test('exhaling while flying shoots an air puff that defeats an enemy', () => {
  const s = playing({ put: [[2, 8, 'P'], [6, 8, 'w']] });
  settle(s);
  s.player.flying = true;
  s.enemies[0].x = s.player.x + 20;
  s.enemies[0].y = s.player.y;
  const seen = eventsDuring(s, 10, (i) => (i === 0 ? ACTION : NONE));
  assert.ok(seen.some((e) => e.type === 'exhale'));
  assert.ok(seen.some((e) => e.type === 'defeat'));
  assert.equal(s.player.flying, false);
});

test('Enemies.defeat removes the enemy and awards its score', () => {
  const s = playing({ put: [[2, 8, 'P'], [10, 4, 'f']] });
  const f = s.enemies[0];
  Enemies.defeat(s, f);
  Enemies.removeDead(s);
  assert.equal(s.enemies.length, 0);
  assert.equal(s.score, CONST.SCORE.flyer);
});

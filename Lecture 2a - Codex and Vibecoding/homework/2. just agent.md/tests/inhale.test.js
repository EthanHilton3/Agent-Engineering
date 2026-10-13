const test = require('node:test');
const assert = require('node:assert/strict');
const { C, S, inp, makeGame, run, settle, Game } = require('./helpers.js');
const { Inhale } = require('../js/logic/inhale.js');

const kirby = (x, y, facing) => ({ x, y, w: C.PLAYER_W, h: C.PLAYER_H, facing });
const box = (cx, cy, size) => ({ x: cx - (size || 12) / 2, y: cy - (size || 12) / 2, w: size || 12, h: size || 12 });

function level(enemyRow) {
  return [
    '..............................',
    '..............................',
    '..............................',
    '..............................',
    '..............................',
    '..............................',
    '..............................',
    '..............................',
    '..............................',
    enemyRow.padEnd(30, '.'),
    '##############################',
  ];
}

test('the inhale cone: in front and close is in, behind or far is out', () => {
  const p = kirby(100, 100, 1);
  const m = Inhale.mouth(p);
  assert.equal(Inhale.inCone(p, box(m.x + 20, m.y)), true, 'right in front');
  assert.equal(Inhale.inCone(p, box(m.x + C.INHALE_RANGE - 2, m.y)), true, 'at the edge of range');
  assert.equal(Inhale.inCone(p, box(m.x + C.INHALE_RANGE + 10, m.y)), false, 'too far');
  assert.equal(Inhale.inCone(p, box(m.x - 30, m.y)), false, 'behind Kirby');
  assert.equal(Inhale.inCone(p, box(m.x + 20, m.y - 40)), false, 'too high');
  assert.equal(Inhale.inCone(p, box(m.x + 20, m.y + 40)), false, 'too low');
});

test('the inhale cone widens with distance', () => {
  const p = kirby(100, 100, 1);
  const m = Inhale.mouth(p);
  const dy = C.INHALE_HALF_HEIGHT + 8;
  assert.equal(Inhale.pointInCone(p, m.x + 4, m.y - dy), false, 'close and high: out');
  assert.equal(Inhale.pointInCone(p, m.x + 50, m.y - dy), true, 'far and equally high: in');
});

test('the inhale cone follows the way Kirby faces', () => {
  const p = kirby(100, 100, -1);
  const m = Inhale.mouth(p);
  assert.equal(Inhale.inCone(p, box(m.x - 20, m.y)), true);
  assert.equal(Inhale.inCone(p, box(m.x + 20, m.y)), false);
});

test('Gordo can never be inhaled, and walls block the inhale', () => {
  const p = kirby(100, 100, 1);
  const m = Inhale.mouth(p);
  const gordo = Object.assign(box(m.x + 20, m.y), { inhalable: false });
  assert.equal(Inhale.inCone(p, gordo), false);

  const g = settle(makeGame(level('..P.#.W')));
  const walker = g.enemies[0];
  assert.equal(Inhale.inCone(g.player, walker), true, 'in the cone ignoring walls');
  assert.equal(Inhale.inCone(g.player, walker, g.world), false, 'but the wall is in the way');
});

test('holding Enter pulls an enemy in and swallows it', () => {
  const g = settle(makeGame(level('..P...W')));
  const score = g.score;
  Game.update(g, inp({ action: true, actionPressed: true }));
  assert.equal(g.player.mode, 'inhale');
  let pulled = false;
  for (let i = 0; i < 60 && g.player.mode === 'inhale'; i++) {
    Game.update(g, inp({ action: true }));
    pulled = pulled || g.enemies.some(e => e.pulled);
  }
  assert.ok(pulled, 'the walker was being pulled');
  assert.equal(g.player.mode, 'full');
  assert.equal(g.enemies.length, 0);
  assert.deepEqual(g.player.held.kinds, ['walker']);
  assert.equal(g.score, score + C.SCORE_SWALLOW);
});

test('Kirby stays put while inhaling', () => {
  const g = settle(makeGame(level('..P')));
  const x = g.player.x;
  Game.update(g, inp({ action: true, actionPressed: true, right: true }));
  run(g, 30, inp({ action: true, right: true }));
  assert.equal(g.player.x, x);
});

test('letting go of Enter releases an enemy that was being pulled', () => {
  const g = settle(makeGame(level('..P...W')));
  Game.update(g, inp({ action: true, actionPressed: true }));
  run(g, 3, inp({ action: true }));
  assert.ok(g.enemies[0].pulled);
  run(g, 2, inp());
  assert.equal(g.player.mode, 'normal');
  assert.equal(g.enemies[0].pulled, false);
});

test('pressing Enter when full spits a star and empties Kirby', () => {
  const g = settle(makeGame(level('..P...W')));
  Game.update(g, inp({ action: true, actionPressed: true }));
  run(g, 60, inp({ action: true }));
  assert.equal(g.player.mode, 'full');
  run(g, 2, inp());
  assert.equal(g.player.mode, 'full', 'releasing Enter keeps the mouthful');
  Game.update(g, inp({ action: true, actionPressed: true }));
  assert.equal(g.player.mode, 'normal');
  assert.equal(g.player.held, null);
  assert.equal(g.projectiles.length, 1);
  assert.equal(g.projectiles[0].kind, 'star');
  assert.ok(g.projectiles[0].vx > 0);
});

test('a full Kirby cannot fly', () => {
  const g = settle(makeGame(level('..P...W')));
  Game.update(g, inp({ action: true, actionPressed: true }));
  run(g, 60, inp({ action: true }));
  run(g, 2);
  Game.update(g, inp({ jump: true, jumpPressed: true }));
  run(g, 10, inp({ jump: true }));
  Game.update(g, inp({ jump: true, jumpPressed: true }));
  assert.equal(g.player.mode, 'full');
});

test('a spat star defeats a line of enemies, doubling the score each time', () => {
  const g = settle(makeGame(level('..P..W..........W.W')));
  Game.update(g, inp({ action: true, actionPressed: true }));
  run(g, 60, inp({ action: true }));
  assert.equal(g.player.mode, 'full');
  assert.equal(g.enemies.length, 2);
  const score = g.score;
  Game.update(g, inp({ action: true, actionPressed: true }));
  run(g, C.STAR_LIFE_TICKS);
  assert.equal(g.enemies.length, 0, 'both enemies were hit');
  assert.equal(g.score, score + C.SCORE_STAR_HIT + C.SCORE_STAR_HIT * 2);
});

test('Gordo shrugs off a star and the star is used up', () => {
  const g = settle(makeGame(level('..P..W.......G')));
  Game.update(g, inp({ action: true, actionPressed: true }));
  run(g, 60, inp({ action: true }));
  Game.update(g, inp({ action: true, actionPressed: true }));
  run(g, C.STAR_LIFE_TICKS);
  assert.equal(g.enemies.length, 1);
  assert.equal(g.enemies[0].kind, 'gordo');
  assert.equal(g.projectiles.length, 0);
});

test('star blocks can be inhaled, and a spat star breaks the ones behind', () => {
  const g = settle(makeGame(level('..P...S.S.S')));
  const T = C.T;
  const row = 9;
  const tileAt = tx => g.world.tiles[row * g.world.w + tx];
  Game.update(g, inp({ action: true, actionPressed: true }));
  run(g, 60, inp({ action: true }));
  assert.equal(g.player.mode, 'full');
  assert.equal(tileAt(6), T.EMPTY, 'the nearest block was inhaled');
  assert.equal(tileAt(8), T.STAR_BLOCK, 'blocks behind it are still there');
  run(g, 2);
  Game.update(g, inp({ action: true, actionPressed: true }));
  run(g, C.STAR_LIFE_TICKS);
  assert.equal(tileAt(8), T.EMPTY);
  assert.equal(tileAt(10), T.EMPTY);
});

test('inhaling in mid-air slows the fall', () => {
  const g = settle(makeGame(level('..P')));
  Game.update(g, inp({ jump: true, jumpPressed: true }));
  run(g, 10, inp({ jump: true }));
  Game.update(g, inp({ action: true, actionPressed: true }));
  run(g, 40, inp({ action: true }));
  assert.equal(g.player.mode, 'inhale');
  assert.ok(g.player.vy <= C.INHALE_AIR_MAX_FALL);
});

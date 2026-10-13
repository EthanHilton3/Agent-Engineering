const test = require('node:test');
const assert = require('node:assert/strict');
const { C, S, inp, makeGame, run, settle, Game } = require('./helpers.js');

const OPEN = [
  '..............................',
  '..............................',
  '..............................',
  '..............................',
  '..............................',
  '..............................',
  '..............................',
  '..............................',
  '..............................',
  '..P...........................',
  '##############################',
];

test('Kirby runs right and left at no more than run speed', () => {
  const g = settle(makeGame(OPEN));
  const x0 = g.player.x;
  run(g, 60, inp({ right: true }));
  assert.ok(g.player.x > x0 + 60, 'moved right');
  assert.ok(Math.abs(g.player.vx) <= C.RUN_SPEED + 1e-9);
  assert.equal(g.player.facing, 1);
  run(g, 30, inp({ left: true }));
  assert.equal(g.player.facing, -1);
});

test('a held jump reaches the expected height and no higher', () => {
  const g = settle(makeGame(OPEN));
  const ground = g.player.y;
  Game.update(g, inp({ jump: true, jumpPressed: true }));
  let top = g.player.y;
  for (let i = 0; i < 90; i++) { Game.update(g, inp({ jump: true })); top = Math.min(top, g.player.y); }
  const height = ground - top;
  const ideal = C.JUMP_SPEED * C.JUMP_SPEED / (2 * C.GRAVITY);
  assert.ok(height > ideal * 0.9 && height <= ideal + 1, 'jump height ' + height + ' vs ' + ideal);
  assert.equal(g.player.onGround, true, 'lands again');
  assert.equal(g.player.y, ground);
});

test('letting go of jump early gives a lower hop', () => {
  const g = settle(makeGame(OPEN));
  const ground = g.player.y;
  Game.update(g, inp({ jump: true, jumpPressed: true }));
  let top = g.player.y;
  for (let i = 0; i < 60; i++) { Game.update(g, inp()); top = Math.min(top, g.player.y); }
  assert.ok(ground - top < 20, 'short hop was ' + (ground - top));
});

test('Kirby cannot jump again in mid-air without flying', () => {
  const g = settle(makeGame(OPEN));
  Game.update(g, inp({ jump: true, jumpPressed: true }));
  run(g, 5, inp({ jump: true }));
  assert.equal(g.player.mode, 'normal');
  assert.ok(g.player.vy < 0);
});

test('pressing jump in the air starts flying; each press is one flap', () => {
  const g = settle(makeGame(OPEN));
  Game.update(g, inp({ jump: true, jumpPressed: true }));
  run(g, 10, inp({ jump: true }));
  Game.update(g, inp({ jump: true, jumpPressed: true }));
  assert.equal(g.player.mode, 'fly');
  assert.equal(g.player.flaps, 1);
  assert.ok(Math.abs(g.player.vy + C.FLY_FLAP_SPEED) < 1e-6 || g.player.vy < 0);
});

test('flying is limited: flaps stop lifting after FLY_MAX_FLAPS and Kirby comes down', () => {
  const g = settle(makeGame(OPEN));
  Game.update(g, inp({ jump: true, jumpPressed: true }));
  run(g, 10);
  for (let i = 0; i < C.FLY_MAX_FLAPS; i++) {
    Game.update(g, inp({ jump: true, jumpPressed: true }));
    run(g, 25);
  }
  assert.equal(g.player.flaps, C.FLY_MAX_FLAPS);
  for (let i = 0; i < 3; i++) {
    const vyBefore = g.player.vy;
    Game.update(g, inp({ jump: true, jumpPressed: true }));
    assert.equal(g.player.onGround, false);
    assert.ok(g.player.vy >= vyBefore, 'an extra flap gives no lift');
    assert.equal(g.player.flaps, C.FLY_MAX_FLAPS);
    run(g, 10);
  }
  run(g, 60 * 10);
  assert.equal(g.player.onGround, true, 'comes back down');
  assert.equal(g.player.flaps, 0, 'flaps reset on landing');
  assert.equal(g.player.mode, 'normal', 'lets the air out when landing');
});

test('flying never goes above the ceiling', () => {
  const g = settle(makeGame(OPEN));
  Game.update(g, inp({ jump: true, jumpPressed: true }));
  for (let i = 0; i < 200; i++) Game.update(g, inp({ jump: true, jumpPressed: i % 6 === 0 }));
  assert.ok(g.player.y >= C.FLY_CEILING);
});

test('flying falls slowly and moves slower than running', () => {
  const g = settle(makeGame(OPEN));
  Game.update(g, inp({ jump: true, jumpPressed: true }));
  run(g, 5);
  Game.update(g, inp({ jump: true, jumpPressed: true }));
  run(g, 60, inp({ right: true }));
  assert.equal(g.player.mode, 'fly');
  assert.ok(g.player.vy <= C.FLY_MAX_FALL);
  assert.ok(g.player.vx <= C.FLY_SPEED_X);
});

test('pressing Enter while flying exhales an air puff and ends the flight', () => {
  const g = settle(makeGame(OPEN));
  Game.update(g, inp({ jump: true, jumpPressed: true }));
  run(g, 5);
  Game.update(g, inp({ jump: true, jumpPressed: true }));
  Game.update(g, inp({ action: true, actionPressed: true }));
  assert.equal(g.player.mode, 'normal');
  assert.equal(g.projectiles.length, 1);
  assert.equal(g.projectiles[0].kind, 'puff');
});

test('Kirby can walk off a ledge and still jump for a few frames (coyote time)', () => {
  const g = settle(makeGame([
    '..........',
    '..........',
    '..........',
    '.P........',
    '###.......',
  ]));
  while (g.player.x < 3 * S) Game.update(g, inp({ right: true }));
  assert.equal(g.player.onGround, false);
  Game.update(g, inp({ jump: true, jumpPressed: true }));
  assert.equal(g.player.mode, 'normal', 'a ground jump, not a flap');
  assert.ok(g.player.vy < -C.JUMP_SPEED * 0.9);
});

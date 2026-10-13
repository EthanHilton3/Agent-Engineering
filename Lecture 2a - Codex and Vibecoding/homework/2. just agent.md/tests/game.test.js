const test = require('node:test');
const assert = require('node:assert/strict');
const { C, S, inp, makeGame, run, settle, Game } = require('./helpers.js');

function level(row9, extra) {
  const rows = [];
  for (let i = 0; i < 9; i++) rows.push(((extra && extra[i]) || '').padEnd(30, '.'));
  rows.push(row9.padEnd(30, '.'));
  rows.push(((extra && extra[10]) || '##############################').padEnd(30, '#'));
  return rows;
}

test('the game starts on the title screen and Enter or Space starts it', () => {
  const g = Game.create();
  assert.equal(g.mode, 'title');
  Game.update(g, inp());
  assert.equal(g.mode, 'title');
  Game.update(g, inp({ actionPressed: true }));
  assert.equal(g.mode, 'playing');
  const g2 = Game.create();
  Game.update(g2, inp({ jumpPressed: true }));
  assert.equal(g2.mode, 'playing');
});

test('P pauses and nothing moves until P again', () => {
  const g = settle(makeGame(level('..P')));
  Game.update(g, inp({ pausePressed: true }));
  assert.equal(g.mode, 'paused');
  const x = g.player.x;
  run(g, 30, inp({ right: true }));
  assert.equal(g.player.x, x);
  Game.update(g, inp({ pausePressed: true }));
  assert.equal(g.mode, 'playing');
});

test('starting values: lives, health and score', () => {
  const g = makeGame(level('..P'));
  assert.equal(g.lives, C.START_LIVES);
  assert.equal(g.player.hp, C.MAX_HP);
  assert.equal(g.score, 0);
});

test('bumping into an enemy costs health, knocks Kirby back, and knocks the enemy out', () => {
  const g = settle(makeGame(level('..P.W')));
  const score = g.score;
  run(g, 60, inp({ right: true }));
  assert.equal(g.player.hp, C.MAX_HP - 1);
  assert.ok(g.player.invuln > 0);
  assert.equal(g.enemies.length, 0);
  assert.equal(g.score, score + C.SCORE_BUMP);
});

test('Gordo hurts but survives, and Kirby is safe for a moment after a hit', () => {
  const g = settle(makeGame(level('..PG')));
  const gordo = g.enemies[0];
  gordo.homeY = g.player.y;  // hold Gordo at Kirby's height for this test
  Game.hurtPlayer(g, gordo);
  assert.equal(g.player.hp, C.MAX_HP - 1);
  assert.equal(Game.hurtPlayer(g, gordo), false, 'invulnerable right after a hit');
  assert.equal(g.player.hp, C.MAX_HP - 1);
  assert.equal(g.enemies.length, 1);
});

test('running out of health loses a life and respawns with full health', () => {
  const g = settle(makeGame(level('..P')));
  const spawn = { x: g.player.x, y: g.player.y };
  for (let i = 0; i < C.MAX_HP; i++) { g.player.invuln = 0; Game.hurtPlayer(g, { x: 0, y: 0, w: 1, h: 1 }); }
  assert.equal(g.mode, 'dying');
  assert.equal(g.lives, C.START_LIVES - 1);
  run(g, C.DEATH_TICKS);
  assert.equal(g.mode, 'playing');
  assert.equal(g.player.hp, C.MAX_HP);
  assert.equal(g.player.x, spawn.x);
});

test('falling into a pit loses a life', () => {
  const g = settle(makeGame(level('..P', { 10: '#####.........................' })));
  for (let i = 0; i < 200 && g.mode === 'playing'; i++) Game.update(g, inp({ right: true }));
  assert.equal(g.mode, 'dying');
  assert.equal(g.lives, C.START_LIVES - 1);
});

test('respawn happens at the last checkpoint passed', () => {
  const g = settle(makeGame(level('..P.....C......', { 10: '##############................' })));
  const cp = g.level.checkpoints[0];
  while (g.mode === 'playing' && g.lives === C.START_LIVES) Game.update(g, inp({ right: true }));
  assert.equal(g.checkpointIndex, 0);
  run(g, C.DEATH_TICKS);
  assert.equal(g.player.x, cp.x);
  assert.equal(g.mode, 'playing');
});

test('losing the last life is game over; Enter restarts a fresh game', () => {
  const g = settle(makeGame(level('..P')));
  for (let life = 0; life < C.START_LIVES; life++) {
    Game.killPlayer(g);
    run(g, C.DEATH_TICKS);
  }
  assert.equal(g.lives, 0);
  assert.equal(g.mode, 'gameover');
  Game.update(g, inp({ actionPressed: true }));
  assert.equal(g.mode, 'gameover', 'mashing right away does not skip the screen');
  run(g, C.END_INPUT_DELAY_TICKS);
  g.score = 999;
  Game.update(g, inp({ actionPressed: true }));
  assert.equal(g.mode, 'playing');
  assert.equal(g.lives, C.START_LIVES);
  assert.equal(g.score, 0);
});

test('point stars add score and a tomato restores health', () => {
  const g = settle(makeGame(level('..P.*..T')));
  g.player.hp = 1;
  run(g, 90, inp({ right: true }));
  assert.equal(g.pickups.length, 0);
  assert.equal(g.score, C.SCORE_PICKUP + C.SCORE_TOMATO);
  assert.equal(g.player.hp, C.MAX_HP);
});

test('touching the warp star wins, adds the bonus, and Enter plays again', () => {
  const g = settle(makeGame(level('..P....E')));
  run(g, 120, inp({ right: true }));
  assert.equal(g.mode, 'won');
  assert.equal(g.score, C.SCORE_GOAL + C.START_LIVES * C.SCORE_LIFE_BONUS);
  Game.update(g, inp({ actionPressed: true }));
  assert.equal(g.mode, 'won', 'the win screen stays up for a moment');
  run(g, C.WIN_SCREEN_TICKS);
  Game.update(g, inp({ jumpPressed: true }));
  assert.equal(g.mode, 'playing');
  assert.equal(g.score, 0);
});

test('R restarts at any time and keeps the same level', () => {
  const g = settle(makeGame(level('..P.*')));
  run(g, 60, inp({ right: true }));
  assert.ok(g.score > 0);
  Game.update(g, inp({ restartPressed: true }));
  assert.equal(g.mode, 'playing');
  assert.equal(g.score, 0);
  assert.equal(g.pickups.length, 1);
  assert.equal(g.level.w, 30);
});

test('enemies far from Kirby stay frozen until he gets close', () => {
  const rows = level('').map(r => r + (r[0] === '#' ? '#' : '.').repeat(30));
  rows[9] = '..P'.padEnd(50, '.') + 'W'.padEnd(10, '.');
  const g = settle(Game.create({ rows, mode: 'playing' }));
  const e = g.enemies[0];
  const x = e.x;
  run(g, 30);
  assert.ok(e.x + e.w / 2 - g.player.x > C.ACTIVATE_DIST);
  assert.equal(e.x, x, 'did not move');
});

// Lives, health, score, checkpoints, boss, win, game over, continue, restart and pause.
const test = require('node:test');
const assert = require('node:assert/strict');
const {
  CONST, Player, Boss, Game, T, level, keys, playing, run, settle, NONE, JUMP, eventsDuring
} = require('./helpers.js');

const RESTART = keys({ restart: true, restartPressed: true });
const PAUSE = keys({ pause: true, pausePressed: true });

function die(s) {
  Player.kill(s);
  run(s, CONST.DEATH_TICKS);
}

test('the game starts on the title screen and Space starts a run', () => {
  const s = Game.create(level({}));
  assert.equal(s.mode, 'title');
  run(s, 1, JUMP);
  assert.equal(s.mode, 'title', 'title ignores input for a moment so a held key does not skip it');
  run(s, CONST.SCREEN_INPUT_DELAY);
  run(s, 1, JUMP);
  assert.equal(s.mode, 'playing');
  assert.equal(s.lives, CONST.START_LIVES);
  assert.equal(s.player.health, CONST.MAX_HEALTH);
  assert.equal(s.score, 0);
});

test('touching an enemy costs one health pip, knocks Kirby back, and gives brief invulnerability', () => {
  const s = playing({ put: [[2, 8, 'P'], [3, 8, 'w']] });
  const seen = eventsDuring(s, 30);
  assert.equal(seen.filter((e) => e.type === 'hurt').length, 1);
  assert.equal(s.player.health, CONST.MAX_HEALTH - 1);
  assert.ok(s.player.invuln > 0);
  assert.ok(s.player.vx < 0 || s.player.x < s.world.start.x, 'knocked back away from the walker');
  run(s, 30);
  assert.equal(s.player.health, CONST.MAX_HEALTH - 1, 'no second hit while invulnerable');
});

test('spikes hurt', () => {
  const s = playing({ put: [[2, 8, 'P'], [2, 9, '^']] });
  run(s, 5);
  assert.equal(s.player.health, CONST.MAX_HEALTH - 1);
});

test('running out of health costs a life and respawns at the last checkpoint with full health', () => {
  const s = playing({ put: [[2, 8, 'P'], [10, 8, 'C']] });
  run(s, 120, keys({ right: true }));
  assert.equal(s.checkpoint, 0, 'passed the checkpoint');
  for (let i = 0; i < CONST.MAX_HEALTH; i++) { s.player.invuln = 0; Player.hurt(s, s.player.x + 20); }
  assert.equal(s.mode, 'dying');
  run(s, CONST.DEATH_TICKS);
  assert.equal(s.mode, 'playing');
  assert.equal(s.lives, CONST.START_LIVES - 1);
  assert.equal(s.player.health, CONST.MAX_HEALTH);
  const cp = s.world.checkpoints[0];
  assert.ok(Math.abs(s.player.x + s.player.w / 2 - (cp.x + cp.w / 2)) < 1);
});

test('falling into a pit costs a whole life even at full health', () => {
  const s = playing({ gaps: [[4, 8]] });
  const seen = eventsDuring(s, 300, keys({ right: true }));
  assert.ok(seen.some((e) => e.type === 'death'));
  assert.equal(s.lives, CONST.START_LIVES - 1);
});

test('losing the last life shows game over; Space continues from the checkpoint with score reset', () => {
  const s = playing({ put: [[2, 8, 'P'], [10, 8, 'C'], [12, 8, 'o']] });
  run(s, 200, keys({ right: true }));
  assert.ok(s.score > 0);
  for (let i = 0; i < CONST.START_LIVES; i++) die(s);
  assert.equal(s.mode, 'gameover');
  assert.equal(s.lives, 0);
  assert.ok(s.best >= s.score && s.best > 0, 'best score is kept');
  run(s, 1, JUMP);
  assert.equal(s.mode, 'gameover', 'waits briefly before accepting input');
  run(s, CONST.SCREEN_INPUT_DELAY);
  run(s, 1, JUMP);
  assert.equal(s.mode, 'playing');
  assert.equal(s.lives, CONST.START_LIVES);
  assert.equal(s.score, 0);
  assert.equal(s.checkpoint, 0);
  assert.equal(s.continues, 1);
});

test('R on the game-over screen restarts from the very beginning', () => {
  const s = playing({ put: [[2, 8, 'P'], [10, 8, 'C']] });
  run(s, 200, keys({ right: true }));
  for (let i = 0; i < CONST.START_LIVES; i++) die(s);
  run(s, CONST.SCREEN_INPUT_DELAY);
  run(s, 1, RESTART);
  assert.equal(s.mode, 'playing');
  assert.equal(s.checkpoint, -1);
  assert.equal(s.player.x, s.world.start.x);
  assert.equal(s.time, 0);
});

test('R while playing asks for confirmation: R again restarts, P cancels', () => {
  const s = playing({ put: [[2, 8, 'P'], [12, 8, 'o']] });
  run(s, 100, keys({ right: true }));
  run(s, 1, RESTART);
  assert.equal(s.mode, 'confirm');
  run(s, 1, PAUSE);
  assert.equal(s.mode, 'playing');
  assert.ok(s.score > 0, 'cancel keeps progress');
  run(s, 1, RESTART);
  run(s, 1, RESTART);
  assert.equal(s.mode, 'playing');
  assert.equal(s.score, 0);
  assert.equal(s.player.x, s.world.start.x);
});

test('P pauses: nothing moves and the clock stops until P again', () => {
  const s = playing({ put: [[2, 8, 'P'], [12, 8, 'w']] });
  run(s, 10);
  run(s, 1, PAUSE);
  const snap = JSON.stringify({ t: s.time, p: s.player, e: s.enemies });
  run(s, 100, keys({ right: true }));
  assert.equal(JSON.stringify({ t: s.time, p: s.player, e: s.enemies }), snap);
  run(s, 1, PAUSE);
  assert.equal(s.mode, 'playing');
});

test('point stars, food and extra lives', () => {
  const s = playing({ put: [[2, 8, 'P'], [5, 8, 'o'], [8, 8, 'T'], [11, 8, '1']] });
  s.player.health = 2;
  run(s, 200, keys({ right: true }));
  assert.equal(s.score, CONST.SCORE.star + CONST.SCORE.food);
  assert.equal(s.player.health, CONST.MAX_HEALTH);
  assert.equal(s.lives, CONST.START_LIVES + 1);
  run(s, 200, keys({ left: true }));
  assert.equal(s.score, CONST.SCORE.star + CONST.SCORE.food, 'items are collected only once');
});

test('reaching the extra-life score awards one life, once', () => {
  const s = playing({ put: [[2, 8, 'P'], [5, 8, 'o']] });
  s.score = CONST.EXTRA_LIFE_SCORE - CONST.SCORE.star;
  run(s, 100, keys({ right: true }));
  assert.equal(s.lives, CONST.START_LIVES + 1);
  s.score += CONST.EXTRA_LIFE_SCORE;
  run(s, 10);
  assert.equal(s.lives, CONST.START_LIVES + 1);
});

function arena() {
  return playing({
    width: 30,
    put: [[2, 8, 'P'], [6, 8, 'A'], [24, 8, 'B'], [14, 5, 'W']],
    ceiling: [[6, 30, 1]]
  });
}

test('the arena gate closes behind Kirby and wakes the boss', () => {
  const s = arena();
  assert.equal(s.boss.state, 'dormant');
  run(s, 200, keys({ right: true }));
  assert.equal(s.arenaLocked, true);
  assert.notEqual(s.boss.state, 'dormant');
  assert.ok(s.world.tiles[5 * s.world.w + 6] !== 0, 'gate column is solid');
});

test('only a spat star hurts the boss; air puffs and touching it do not', () => {
  const s = arena();
  run(s, 200, keys({ right: true }));
  const b = s.boss;
  run(s, CONST.BOSS_INTRO_TICKS);
  s.projectiles.push({ kind: 'air', x: b.x - 4, y: b.y + 20, w: 10, h: 10, vx: 1, life: 10, power: 1 });
  run(s, 3);
  assert.equal(b.hp, CONST.BOSS_HP);
  s.projectiles.push({ kind: 'star', x: b.x - 4, y: b.y + 20, w: 12, h: 12, vx: 1, life: 10, power: 1 });
  run(s, 3);
  assert.equal(b.hp, CONST.BOSS_HP - 1);
  assert.ok(b.invuln > 0);
});

test('the boss drops inhalable apples and blows puffs that cannot be inhaled', () => {
  const s = arena();
  run(s, 200, keys({ right: true }));
  run(s, CONST.BOSS_INTRO_TICKS + CONST.BOSS_APPLE_WAIT + CONST.BOSS_PUFF_GAP + 5);
  const apples = s.enemies.filter((e) => e.type === 'apple');
  const puffs = s.enemies.filter((e) => e.type === 'bosspuff');
  assert.ok(apples.length >= 1, 'apples dropped');
  assert.ok(puffs.length >= 1, 'puffs blown');
  assert.equal(apples[0].inhalable, true);
  assert.equal(puffs[0].inhalable, false);
});

test('beating the boss reveals the warp star; touching it wins with a time bonus', () => {
  const s = arena();
  run(s, 200, keys({ right: true }));
  run(s, CONST.BOSS_INTRO_TICKS);
  assert.equal(s.warp.active, false);
  for (let i = 0; i < CONST.BOSS_HP; i++) { s.boss.invuln = 0; Boss.hit(s, 1); }
  assert.equal(s.boss.state, 'dying');
  const before = s.score;
  run(s, CONST.BOSS_DEATH_TICKS + 1);
  assert.equal(s.boss.state, 'dead');
  assert.equal(s.warp.active, true);
  assert.equal(s.score - before, CONST.SCORE.boss);
  assert.equal(s.world.tiles[5 * s.world.w + 6], 0, 'the arena gate opens again');
  run(s, 5);
  assert.equal(s.world.tiles[5 * s.world.w + 6], 0, 'and stays open');
  s.player.x = s.warp.x; // unit test of the win rule only; the playthrough test reaches it with keys
  s.player.y = s.warp.y;
  const seen = eventsDuring(s, 1);
  assert.ok(seen.some((e) => e.type === 'win'));
  assert.equal(s.mode, 'win');
  const seconds = Math.floor(s.time / CONST.TICKS_PER_SECOND);
  assert.equal(s.winBonus, Math.max(0, CONST.TIME_BONUS_MAX - seconds * CONST.TIME_BONUS_PER_SECOND));
  assert.equal(s.best, s.score);
  run(s, CONST.SCREEN_INPUT_DELAY);
  run(s, 1, JUMP);
  assert.equal(s.mode, 'playing', 'Space on the win screen plays again');
  assert.equal(s.score, 0);
});

test('dying in the arena reopens the gate and resets the boss', () => {
  const s = arena();
  run(s, 200, keys({ right: true }));
  run(s, CONST.BOSS_INTRO_TICKS);
  s.boss.invuln = 0;
  Boss.hit(s, 1);
  die(s);
  assert.equal(s.arenaLocked, false);
  assert.equal(s.boss.state, 'dormant');
  assert.equal(s.boss.hp, CONST.BOSS_HP);
  assert.equal(s.world.tiles[5 * s.world.w + 6], 0, 'gate is open again');
  settle(s);
});

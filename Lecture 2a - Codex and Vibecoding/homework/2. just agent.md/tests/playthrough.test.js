// Plays the real level from the title screen to the warp star using only simulated key events.
const test = require('node:test');
const assert = require('node:assert/strict');
const { playThrough } = require('./bot.js');
const { C } = require('../js/logic/constants.js');

test('the level can be finished with keyboard input alone, crossing every gap', () => {
  const r = playThrough(C.TICKS_PER_SEC * 60 * 5);
  const where = 'Kirby at x=' + Math.round(r.game.player.x) + ', bot log: ' + r.log.join(' | ');
  assert.equal(r.game.mode, 'won', 'reached the warp star (' + where + ')');
  assert.ok(r.gaps.length >= 4, 'the level has gaps to cross');
  r.gaps.forEach(gp => assert.ok(gp.crossed, 'crossed the gap at columns ' + gp.from + '-' + gp.to));
  assert.equal(r.deaths, 0, 'no lives lost, so no gap was skipped by respawning');
  assert.ok(r.counts.flap > 0, 'had to fly');
  assert.ok(r.counts.swallow > 0 && r.counts.spit > 0, 'had to inhale and spit (the star block wall)');
  assert.ok(r.counts.blockBreak > 0 || r.counts.blockLoose > 0, 'cleared star blocks');
});

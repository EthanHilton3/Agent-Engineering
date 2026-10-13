// Automated playthrough: the bot plays the real level using simulated key events only
// (keyDown/keyUp on the same input tracker the browser uses). No teleporting and no
// writes to game state: the test only reads state to check what happened.
const test = require('node:test');
const assert = require('node:assert/strict');
const { CONST } = require('../js/logic/constants.js');
const { Game } = require('../js/logic/game.js');
const { LEVEL_1 } = require('../js/level.js');
const { KirbyInput } = require('../js/input.js');
const { KirbyBot } = require('./bot.js');

const MAX_TICKS = 60 * 60 * 20; // 20 minutes of game time
const MAX_STEP_PX = 8;          // nothing moves further than this in one tick except a respawn

function play() {
  const state = Game.create(LEVEL_1);
  const input = KirbyInput.create();
  const bot = KirbyBot.create();
  const log = { events: {}, landedAfterGap: new Set(), maxStep: 0, ticks: 0 };
  const gaps = state.world.gaps;
  let prev = null;
  for (let t = 0; t < MAX_TICKS && state.mode !== 'win'; t++) {
    bot.apply(state, input);
    Game.update(state, input.poll());
    log.ticks = t;
    const respawned = state.events.some((e) => e.type === 'respawn' || e.type === 'start');
    state.events.forEach((e) => { log.events[e.type] = (log.events[e.type] || 0) + 1; });
    const p = state.player;
    if (prev && !respawned && state.mode === 'playing') {
      log.maxStep = Math.max(log.maxStep, Math.abs(p.x - prev.x), Math.abs(p.y - prev.y));
    }
    prev = { x: p.x, y: p.y };
    if (p.onGround) gaps.forEach((g, i) => { if (p.x >= g.x1) log.landedAfterGap.add(i); });
  }
  return { state, log, bot };
}

test('the bot finishes the level with key presses only', () => {
  const { state, log, bot } = play();
  const p = state.player;
  const summary = `mode=${state.mode} x=${(p.x / CONST.TILE).toFixed(1)} ticks=${log.ticks} deaths=${state.deaths} continues=${state.continues}`;
  assert.equal(state.mode, 'win', 'did not win: ' + summary);
  assert.ok(bot.mem.keyEvents > 100, 'driven by key events');

  // Every gap in the level was crossed: Kirby later stood on solid ground past its far edge.
  state.world.gaps.forEach((g, i) => {
    assert.ok(log.landedAfterGap.has(i), `gap ${i} (cols ${g.x0 / CONST.TILE}-${g.x1 / CONST.TILE}) was never crossed`);
  });

  // No teleporting: movement per tick stays small.
  assert.ok(log.maxStep <= MAX_STEP_PX, 'player jumped ' + log.maxStep + 'px in one tick');

  // The core mechanics were all exercised along the way.
  for (const ev of ['swallow', 'spit', 'flap', 'blockBreak', 'defeat', 'checkpoint', 'arenaLock', 'bossHit', 'bossDefeated', 'win']) {
    assert.ok(log.events[ev] > 0, 'never saw ' + ev);
  }
  assert.equal(state.boss.state, 'dead');
  assert.ok(log.events.bossHit >= CONST.BOSS_HP / 2, 'boss took hits from spat stars');
  assert.ok(state.score > 0);
  console.log('playthrough: ' + summary + ` time=${(state.time / 60).toFixed(0)}s score=${state.score}`);
});

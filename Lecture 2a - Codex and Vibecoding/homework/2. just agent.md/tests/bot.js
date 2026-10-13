// A scripted player for the playthrough test. It looks at the game state (read only) and answers
// with simulated keyboard events fed through input.js. It never moves Kirby or edits state directly.
const { C } = require('../js/logic/constants.js');
const { Physics } = require('../js/logic/physics.js');
const { Inhale } = require('../js/logic/inhale.js');
const { Input } = require('../js/input.js');
const { Game } = require('../js/logic/game.js');

const S = C.TILE;
const KEY = {
  right: { code: 'ArrowRight', key: 'ArrowRight' },
  jump: { code: 'Space', key: ' ' },
  action: { code: 'Enter', key: 'Enter' },
};

function createBot(game) {
  const input = Input.create();
  const down = { right: false, jump: false, action: false };
  const bot = { state: 'walk', phase: 'climb', timer: 0, targetY: 0, holdJump: 0, log: [] };

  function set(name, isDown) {
    if (down[name] === isDown) return;
    down[name] = isDown;
    Input.handleEvent(input, Object.assign({ type: isDown ? 'keydown' : 'keyup', repeat: false }, KEY[name]));
  }
  // A tap is a keydown now and a keyup on the next tick (only if the key was up).
  function tap(name) { if (!down[name]) set(name, true); }

  const g = () => game;
  const tile = (tx, ty) => Physics.tileAt(g().world, tx, ty);
  const pitColumn = tx => tile(tx, g().world.h - 1) === C.T.EMPTY;

  function enemyAhead(maxDist, inhalableOnly) {
    const p = g().player;
    let best = null;
    for (const e of g().enemies) {
      if (e.kind === 'block' || (inhalableOnly && !e.inhalable)) continue;
      const dx = e.x - (p.x + p.w);
      const dy = (e.y + e.h / 2) - (p.y + p.h / 2);
      if (dx > -e.w && dx < maxDist && Math.abs(dy) < S * 1.5 && (!best || dx < best.dx)) best = { e, dx, dy };
    }
    return best;
  }

  function starBlockAhead() {
    const p = g().player;
    const tx = Math.floor((p.x + p.w + S * 1.5) / S);
    const rows = [Math.floor(p.y / S), Math.floor((p.y + p.h - 1) / S)];
    return rows.some(ty => tile(tx, ty) === C.T.STAR_BLOCK || tile(tx - 1, ty) === C.T.STAR_BLOCK);
  }

  // Height of the obstacle right in front of Kirby (0 if none): a wall in his way.
  function wallTopAhead() {
    const p = g().player;
    const tx = Math.floor((p.x + p.w + 3) / S);
    const ty1 = Math.floor((p.y + p.h - 1) / S);
    if (!Physics.isSolidAt(g().world, tx, ty1) || tile(tx, ty1) === C.T.STAR_BLOCK) return 0;
    let ty = ty1;
    while (ty > 0 && Physics.isSolidAt(g().world, tx, ty - 1)) ty--;
    return ty * S;
  }

  function gapAhead() {
    const p = g().player;
    const front = Math.floor((p.x + p.w + 6) / S);
    return pitColumn(front);
  }

  function overSafeGround() {
    const p = g().player;
    return !pitColumn(Math.floor(p.x / S)) && !pitColumn(Math.floor((p.x + p.w) / S)) && !gapAhead();
  }

  function startCross(targetY, why) {
    bot.state = 'cross';
    bot.targetY = targetY;
    bot.timer = 0;
    bot.phase = 'climb';
    bot.log.push(why + ' at x=' + Math.round(g().player.x));
  }

  // Decide this tick's keys. Called once per tick before the game updates.
  function think() {
    const game = g();
    const p = game.player;
    // Release taps from the previous tick so the next press is a fresh one.
    if (bot.holdJump > 0) bot.holdJump--;
    else if (down.jump) set('jump', false);
    if (game.mode === 'title') { set('action', false); tap('action'); return; }
    if (game.mode !== 'playing') { set('right', false); set('action', false); bot.state = 'walk'; return; }
    bot.timer++;

    if (p.mode === 'full') {          // spit as soon as something is in our mouth
      set('right', false);
      if (down.action) set('action', false); else tap('action');
      bot.state = 'walk';
      return;
    }

    if (bot.state === 'inhale') {
      set('right', false);
      const target = enemyAhead(C.INHALE_RANGE, true);
      if (bot.timer > 90 || (!target && !starBlockAhead() && !game.enemies.some(e => e.pulled))) {
        set('action', false);
        bot.state = 'walk';
      } else set('action', true);
      return;
    }
    if (down.action) set('action', false);

    if (bot.state === 'cross') {
      // Phase 1 (climb): rise straight up to the target height. Phase 2 (go): fly right, holding
      // that height until there is safe ground below, then drift down and land.
      if (p.y <= bot.targetY + 4) bot.phase = 'go';
      set('right', bot.phase === 'go');
      const threat = enemyAhead(36, true);
      if (p.mode === 'fly' && threat && Math.abs(threat.dy) < 14) { tap('action'); return; }  // puff it away
      const needLift = bot.phase === 'climb' || !overSafeGround();
      if (p.onGround && bot.phase === 'climb') { set('jump', true); bot.holdJump = 18; }
      else if (needLift && !p.onGround && bot.holdJump <= 0 && (p.vy > 0 || p.mode !== 'fly') && p.y > bot.targetY) tap('jump');
      if (p.onGround && bot.phase === 'go') bot.state = 'walk';
      if (bot.timer > 60 * 20) bot.state = 'walk';
      return;
    }

    // Walking.
    const target = enemyAhead(C.INHALE_RANGE - 4, true);
    if (p.onGround && target && Inhale.inCone(p, target.e, game.world)) {
      set('right', false); set('action', true);
      bot.state = 'inhale'; bot.timer = 0;
      return;
    }
    if (p.onGround && starBlockAhead()) {
      set('right', false); set('action', true);
      bot.state = 'inhale'; bot.timer = 0;
      return;
    }
    // Hoppers in mid-air or Gordo close by: wait for a better moment.
    const wary = enemyAhead(S * 3, false);
    if (wary && wary.e.kind === 'hopper' && !wary.e.onGround) { set('right', false); return; }
    if (p.onGround && gapAhead()) { set('right', false); startCross(S * 2.5, 'gap'); return; }
    const wall = wallTopAhead();
    if (p.onGround && wall) { set('right', false); startCross(wall - p.h - S, 'wall'); return; }
    set('right', true);
  }

  return { input, think, bot, down };
}

// Run a whole game with the bot. Returns a summary for the test to check.
function playThrough(maxTicks) {
  const game = Game.create();
  const { input, think, bot } = createBot(game);
  const { Level } = require('../js/level.js');
  const gaps = Level.findGaps(game.level).map(gp => ({ ...gp, crossed: false }));
  const startLives = game.lives;
  let ticks = 0;
  let deaths = 0;
  const counts = {};
  for (; ticks < maxTicks && game.mode !== 'won' && game.mode !== 'gameover'; ticks++) {
    think();
    Game.update(game, Input.snapshot(input));
    for (const e of game.events) counts[e.type] = (counts[e.type] || 0) + 1;
    if (game.events.some(e => e.type === 'die')) deaths++;
    const p = game.player;
    if (game.mode === 'playing' && p.onGround) {
      for (const gp of gaps) if (p.x > (gp.to + 1) * S) gp.crossed = true;
    }
  }
  return { game, ticks, gaps, deaths, startLives, counts, log: bot.log };
}

module.exports = { createBot, playThrough };

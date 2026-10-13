// Shared helpers for the unit tests.
const { C } = require('../js/logic/constants.js');
const { Game } = require('../js/logic/game.js');

const S = C.TILE;

// An input snapshot with nothing pressed, plus overrides.
function inp(over) {
  return Object.assign({
    left: false, right: false, jump: false, action: false,
    jumpPressed: false, actionPressed: false, pausePressed: false, mutePressed: false, restartPressed: false,
  }, over || {});
}

// A game on a small custom level, already playing.
function makeGame(rows) {
  return Game.create({ rows, mode: 'playing' });
}

// Run n ticks with the same input.
function run(g, n, input) {
  for (let i = 0; i < n; i++) Game.update(g, input || inp());
  return g;
}

// Let Kirby settle on the ground.
function settle(g) { return run(g, 20); }

module.exports = { C, S, inp, makeGame, run, settle, Game };

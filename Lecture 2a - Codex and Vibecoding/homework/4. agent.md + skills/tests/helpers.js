// Shared helpers for the unit tests: small hand-made levels and input snapshots.
const { CONST } = require('../js/logic/constants.js');
const { Physics } = require('../js/logic/physics.js');
const { World } = require('../js/logic/world.js');
const { Enemies } = require('../js/logic/enemies.js');
const { Player } = require('../js/logic/player.js');
const { Boss } = require('../js/logic/boss.js');
const { Game } = require('../js/logic/game.js');

const T = CONST.TILE;
const GROUND_ROW = 9;
const FLOOR_Y = GROUND_ROW * T;

// A one-section test level: flat ground at GROUND_ROW, plus whatever is passed in.
function level(section) {
  return { name: 'test', height: 12, groundRow: GROUND_ROW, sections: [Object.assign({ name: 'TEST', width: 40, put: [[2, 8, 'P']] }, section)] };
}

// An input snapshot with every key up unless overridden.
function keys(o) {
  return Object.assign({
    left: false, right: false, jump: false, action: false, pause: false, mute: false, restart: false,
    leftPressed: false, rightPressed: false, jumpPressed: false, actionPressed: false,
    pausePressed: false, mutePressed: false, restartPressed: false
  }, o);
}
const NONE = keys({});
const JUMP = keys({ jump: true, jumpPressed: true });
const ACTION = keys({ action: true, actionPressed: true });
const HOLD_ACTION = keys({ action: true });

// Creates a game already in the playing state.
function playing(section, opts) {
  const s = Game.create(level(section || {}), opts);
  s.screenTimer = 0;
  Game.update(s, JUMP);
  if (s.mode !== 'playing') throw new Error('test game did not start');
  return s;
}

function run(state, n, input) {
  for (let i = 0; i < n; i++) Game.update(state, input || NONE);
}

// Ticks until the player stands on the ground (or gives up).
function settle(state) {
  for (let i = 0; i < 200 && !state.player.onGround; i++) Game.update(state, NONE);
}

function eventsDuring(state, n, input) {
  const seen = [];
  for (let i = 0; i < n; i++) {
    Game.update(state, typeof input === 'function' ? input(i) : (input || NONE));
    seen.push(...state.events);
  }
  return seen;
}

module.exports = {
  CONST, Physics, World, Enemies, Player, Boss, Game, T, GROUND_ROW, FLOOR_Y,
  level, keys, NONE, JUMP, ACTION, HOLD_ACTION, playing, run, settle, eventsDuring
};

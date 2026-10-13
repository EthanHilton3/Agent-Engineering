// Keyboard input. Tracks held keys and presses between fixed-step polls,
// so a tap shorter than one tick is never lost. The tracker itself has no DOM
// dependency (tests feed it key events); attach() wires it to the page.
var KirbyInput = (function () {
  'use strict';

  // Only the keys the game asks for. Utility keys: P/Esc pause, M mute, R restart.
  var BINDINGS = {
    ArrowLeft: 'left', KeyA: 'left',
    ArrowRight: 'right', KeyD: 'right',
    Space: 'jump',
    Enter: 'action',
    KeyP: 'pause', Escape: 'pause',
    KeyM: 'mute',
    KeyR: 'restart'
  };
  var ACTIONS = ['left', 'right', 'jump', 'action', 'pause', 'mute', 'restart'];

  function create() {
    var down = {};
    var pressed = {};

    function held(action) {
      for (var code in down) if (down[code] && BINDINGS[code] === action) return true;
      return false;
    }

    return {
      keyDown: function (code) {
        var action = BINDINGS[code];
        if (!action) return false;
        if (!down[code]) pressed[action] = true;
        down[code] = true;
        return true;
      },
      keyUp: function (code) {
        if (!BINDINGS[code]) return false;
        down[code] = false;
        return true;
      },
      releaseAll: function () {
        down = {};
      },
      // One snapshot per fixed update. Presses are consumed by the poll.
      poll: function () {
        var snap = {};
        ACTIONS.forEach(function (a) {
          snap[a] = held(a) || !!pressed[a];
          snap[a + 'Pressed'] = !!pressed[a];
        });
        pressed = {};
        return snap;
      }
    };
  }

  function attach(input, target, onAnyKey) {
    target.addEventListener('keydown', function (e) {
      if (onAnyKey) onAnyKey();
      if (e.repeat && BINDINGS[e.code]) { e.preventDefault(); return; }
      if (input.keyDown(e.code)) e.preventDefault();
    });
    target.addEventListener('keyup', function (e) {
      if (input.keyUp(e.code)) e.preventDefault();
    });
    target.addEventListener('blur', function () { input.releaseAll(); });
  }

  return { BINDINGS: BINDINGS, create: create, attach: attach };
})();

if (typeof module !== 'undefined') module.exports = { KirbyInput };

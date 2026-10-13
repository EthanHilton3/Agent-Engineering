// Keyboard -> input snapshots. The key handling is plain functions so tests can feed it fake events.
var KB = (typeof KB !== 'undefined') ? KB : {};

KB.Input = (function () {
  // Only the keys the game asks for (physical key codes, so A/D work on any keyboard layout).
  const BINDINGS = {
    ArrowLeft: 'left', KeyA: 'left',
    ArrowRight: 'right', KeyD: 'right',
    Space: 'jump',
    Enter: 'action',
  };
  const UTILITY = { KeyP: 'pause', KeyM: 'mute', KeyR: 'restart' };

  function create() {
    return {
      held: { left: false, right: false, jump: false, action: false },
      pressed: { jump: 0, action: 0, pause: 0, mute: 0, restart: 0 },
    };
  }

  function actionFor(ev) { return BINDINGS[ev.code] || null; }

  // Feed one keydown/keyup event. Returns true if the game used it.
  function handleEvent(state, ev) {
    const down = ev.type === 'keydown';
    const action = actionFor(ev);
    if (action) {
      if (down && !ev.repeat && !state.held[action] && action in state.pressed) state.pressed[action]++;
      state.held[action] = down;
    } else if (UTILITY[ev.code]) {
      if (down && !ev.repeat) state.pressed[UTILITY[ev.code]]++;
    } else {
      return false;
    }
    if (ev.preventDefault) ev.preventDefault();
    return true;
  }

  function releaseAll(state) {
    Object.keys(state.held).forEach(k => { state.held[k] = false; });
  }

  // What the game sees for one tick. Presses are latched until the next snapshot, so a quick tap
  // between two ticks is never lost.
  function snapshot(state) {
    const h = state.held, p = state.pressed;
    const snap = {
      left: h.left, right: h.right, jump: h.jump, action: h.action,
      jumpPressed: p.jump > 0, actionPressed: p.action > 0,
      pausePressed: p.pause > 0, mutePressed: p.mute > 0, restartPressed: p.restart > 0,
    };
    Object.keys(p).forEach(k => { p[k] = 0; });
    return snap;
  }

  function attach(target, state, onKey) {
    const handler = ev => { if (handleEvent(state, ev) && onKey) onKey(ev); };
    target.addEventListener('keydown', handler);
    target.addEventListener('keyup', handler);
    target.addEventListener('blur', () => releaseAll(state));
  }

  return { create, handleEvent, snapshot, releaseAll, attach };
})();

if (typeof module !== 'undefined') module.exports = { Input: KB.Input };

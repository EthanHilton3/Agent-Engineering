const test = require('node:test');
const assert = require('node:assert/strict');
const { Input } = require('../js/input.js');

const ev = (type, code, key, extra) => Object.assign({ type, code, key: key || code, preventDefault() { this.prevented = true; } }, extra);

test('only the requested keys drive Kirby', () => {
  const s = Input.create();
  for (const [code, key, name] of [['ArrowLeft', 'ArrowLeft', 'left'], ['KeyA', 'a', 'left'], ['ArrowRight', 'ArrowRight', 'right'],
    ['KeyD', 'd', 'right'], ['Space', ' ', 'jump'], ['Enter', 'Enter', 'action']]) {
    Input.handleEvent(s, ev('keydown', code, key));
    assert.equal(s.held[name], true, code);
    Input.handleEvent(s, ev('keyup', code, key));
    assert.equal(s.held[name], false, code);
  }
  for (const code of ['KeyW', 'ArrowUp', 'ArrowDown', 'KeyS', 'KeyZ', 'KeyX', 'KeyJ', 'ShiftLeft', 'NumpadEnter']) {
    assert.equal(Input.handleEvent(s, ev('keydown', code)), false, code + ' is not bound');
  }
});

test('a quick tap between two ticks is still seen once, and key repeat is ignored', () => {
  const s = Input.create();
  Input.handleEvent(s, ev('keydown', 'Space', ' '));
  Input.handleEvent(s, ev('keyup', 'Space', ' '));
  let snap = Input.snapshot(s);
  assert.equal(snap.jumpPressed, true);
  assert.equal(snap.jump, false);
  snap = Input.snapshot(s);
  assert.equal(snap.jumpPressed, false, 'a press is reported only once');

  Input.handleEvent(s, ev('keydown', 'Enter'));
  Input.snapshot(s);
  Input.handleEvent(s, ev('keydown', 'Enter', 'Enter', { repeat: true }));
  snap = Input.snapshot(s);
  assert.equal(snap.actionPressed, false);
  assert.equal(snap.action, true);
});

test('utility keys: pause, mute, restart', () => {
  const s = Input.create();
  Input.handleEvent(s, ev('keydown', 'KeyP', 'p'));
  Input.handleEvent(s, ev('keydown', 'KeyM', 'm'));
  Input.handleEvent(s, ev('keydown', 'KeyR', 'r'));
  const snap = Input.snapshot(s);
  assert.ok(snap.pausePressed && snap.mutePressed && snap.restartPressed);
});

test('handled keys stop the browser from scrolling', () => {
  const s = Input.create();
  const e = ev('keydown', 'Space', ' ');
  Input.handleEvent(s, e);
  assert.equal(e.prevented, true);
});

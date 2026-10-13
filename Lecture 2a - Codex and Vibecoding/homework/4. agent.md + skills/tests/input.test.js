const test = require('node:test');
const assert = require('node:assert/strict');
const { KirbyInput } = require('../js/input.js');

test('only the requested keys are bound to movement, jump/fly and inhale/spit', () => {
  const byAction = {};
  for (const [code, action] of Object.entries(KirbyInput.BINDINGS)) (byAction[action] = byAction[action] || []).push(code);
  assert.deepEqual(byAction.left.sort(), ['ArrowLeft', 'KeyA']);
  assert.deepEqual(byAction.right.sort(), ['ArrowRight', 'KeyD']);
  assert.deepEqual(byAction.jump, ['Space']);
  assert.deepEqual(byAction.action, ['Enter']);
  for (const code of ['ArrowUp', 'ArrowDown', 'KeyW', 'KeyS', 'KeyX', 'KeyZ', 'KeyJ', 'NumpadEnter', 'ShiftLeft']) {
    assert.equal(KirbyInput.BINDINGS[code], undefined, code + ' must not be bound');
  }
});

test('a tap shorter than one tick still counts as a press and as held for that tick', () => {
  const input = KirbyInput.create();
  input.keyDown('Space');
  input.keyUp('Space');
  const snap = input.poll();
  assert.equal(snap.jumpPressed, true);
  assert.equal(snap.jump, true);
  const next = input.poll();
  assert.equal(next.jumpPressed, false);
  assert.equal(next.jump, false);
});

test('holding a key reports one press, then held', () => {
  const input = KirbyInput.create();
  input.keyDown('Enter');
  assert.equal(input.poll().actionPressed, true);
  input.keyDown('Enter'); // auto-repeat
  const snap = input.poll();
  assert.equal(snap.actionPressed, false);
  assert.equal(snap.action, true);
});

test('either binding of a direction works, and releasing one keeps the other held', () => {
  const input = KirbyInput.create();
  input.keyDown('KeyA');
  input.keyDown('ArrowLeft');
  input.keyUp('KeyA');
  assert.equal(input.poll().left, true);
  input.keyUp('ArrowLeft');
  assert.equal(input.poll().left, false);
});

test('unbound keys are ignored', () => {
  const input = KirbyInput.create();
  assert.equal(input.keyDown('KeyQ'), false);
  const snap = input.poll();
  assert.ok(Object.values(snap).every((v) => v === false));
});

test('releaseAll (window blur) lets go of every key', () => {
  const input = KirbyInput.create();
  input.keyDown('ArrowRight');
  input.poll();
  input.releaseAll();
  assert.equal(input.poll().right, false);
});

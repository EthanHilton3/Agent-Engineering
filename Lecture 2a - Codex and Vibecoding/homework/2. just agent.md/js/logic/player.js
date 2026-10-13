// Kirby: running, jumping, flying and the action key.
// Modes: 'normal' | 'fly' (puffed up) | 'inhale' (holding the action key) | 'full' (mouthful).
var KB = (typeof KB !== 'undefined') ? KB : {};
if (typeof module !== 'undefined') {
  Object.assign(KB, require('./constants.js'), require('./physics.js'), require('./entities.js'), require('./inhale.js'));
}

KB.Player = (function () {
  const C = KB.C;
  const E = KB.Entities;

  function create(x, y) {
    return {
      x, y, w: C.PLAYER_W, h: C.PLAYER_H, vx: 0, vy: 0, facing: 1,
      onGround: false, mode: 'normal', hp: C.MAX_HP, invuln: 0,
      flaps: 0, coyote: 0, jumpBuffer: 0, jumping: false,
      held: null, spitTimer: 0, landTimer: 0, anim: 0,
    };
  }

  function approach(v, target, rate) {
    return v < target ? Math.min(v + rate, target) : Math.max(v - rate, target);
  }

  function handleAction(g, p, inp) {
    if (inp.actionPressed) {
      if (p.mode === 'full') KB.Inhale.spit(g);
      else if (p.mode === 'fly') KB.Inhale.exhale(g);
      else if (p.mode === 'normal') {
        p.mode = 'inhale';
        E.emit(g, 'inhaleStart', KB.Inhale.mouth(p));
      }
    }
    if (p.mode === 'inhale' && !inp.action) p.mode = 'normal';
  }

  function handleRun(p, inp) {
    const dir = (inp.right ? 1 : 0) - (inp.left ? 1 : 0);
    if (dir && p.mode !== 'inhale') p.facing = dir;
    let max = C.RUN_SPEED;
    let accel = p.onGround ? C.GROUND_ACCEL : C.AIR_ACCEL;
    if (p.mode === 'fly') { max = C.FLY_SPEED_X; accel = C.FLY_ACCEL; }
    if (p.mode === 'full') max *= C.FULL_SPEED_FACTOR;
    if (p.mode === 'inhale') max *= C.INHALE_MOVE_FACTOR;
    const target = dir * max;
    const braking = target === 0 || Math.sign(target) !== Math.sign(p.vx);
    const rate = (p.onGround && braking ? C.GROUND_DECEL : accel) * C.DT;
    p.vx = approach(p.vx, target, rate);
  }

  function handleJump(g, p, inp) {
    if (inp.jumpPressed) p.jumpBuffer = C.JUMP_BUFFER_TICKS;
    const airborne = !p.onGround && p.coyote <= 0;
    const canFly = p.mode === 'normal' || p.mode === 'fly';
    const canJump = (p.onGround || p.coyote > 0) && (p.mode === 'normal' || p.mode === 'full');

    if (inp.jumpPressed && airborne && canFly) {
      // Every tap in the air is one flap, until the flap budget runs out.
      if (p.flaps < C.FLY_MAX_FLAPS) {
        if (p.mode !== 'fly') E.emit(g, 'puffUp', { x: p.x + p.w / 2, y: p.y });
        p.mode = 'fly';
        p.vy = -C.FLY_FLAP_SPEED;
        p.flaps++;
        E.emit(g, 'flap', { x: p.x + p.w / 2, y: p.y + p.h, flaps: p.flaps });
      } else {
        E.emit(g, 'tired', { x: p.x + p.w / 2, y: p.y });
      }
      p.jumping = false;
      p.jumpBuffer = 0;
    } else if (p.jumpBuffer > 0 && canJump) {
      p.vy = -C.JUMP_SPEED;
      p.jumping = true;
      p.jumpBuffer = 0;
      p.coyote = 0;
      E.emit(g, 'jump', { x: p.x + p.w / 2, y: p.y + p.h });
    }

    // Short hop: letting go of Space early cuts the jump.
    if (p.jumping && !inp.jump && p.vy < -C.JUMP_CUT_SPEED) p.vy = -C.JUMP_CUT_SPEED;
    if (p.vy >= 0) p.jumping = false;
  }

  function applyGravity(p) {
    if (p.mode === 'fly') {
      p.vy = Math.min(p.vy + C.FLY_GRAVITY * C.DT, C.FLY_MAX_FALL);
    } else if (p.mode === 'inhale' && !p.onGround) {
      p.vy = Math.min(p.vy + C.GRAVITY * C.DT, C.INHALE_AIR_MAX_FALL);
    } else {
      p.vy = Math.min(p.vy + (p.vy < 0 ? C.GRAVITY : C.FALL_GRAVITY) * C.DT, C.MAX_FALL_SPEED);
    }
  }

  function update(g, inp) {
    const p = g.player;
    p.anim++;
    if (p.invuln > 0) p.invuln--;
    if (p.spitTimer > 0) p.spitTimer--;
    if (p.landTimer > 0) p.landTimer--;
    if (p.jumpBuffer > 0) p.jumpBuffer--;
    if (p.coyote > 0) p.coyote--;

    handleAction(g, p, inp);
    handleRun(p, inp);
    handleJump(g, p, inp);
    applyGravity(p);

    const wasOnGround = p.onGround;
    const fallSpeed = p.vy;
    KB.Physics.moveBody(p, g.world, p.vx * C.DT, p.vy * C.DT);
    if (p.y < C.FLY_CEILING) {
      p.y = C.FLY_CEILING;
      if (p.vy < 0) p.vy = 0;
    }

    if (p.onGround) {
      p.coyote = C.COYOTE_TICKS;
      p.flaps = 0;
      p.jumping = false;
      if (p.mode === 'fly') KB.Inhale.exhale(g);  // touching down lets the air out
      if (!wasOnGround) {
        p.landTimer = C.LAND_SQUASH_TICKS;
        E.emit(g, 'land', { x: p.x + p.w / 2, y: p.y + p.h, speed: fallSpeed });
      }
    }
  }

  return { create, update };
})();

if (typeof module !== 'undefined') module.exports = { Player: KB.Player };

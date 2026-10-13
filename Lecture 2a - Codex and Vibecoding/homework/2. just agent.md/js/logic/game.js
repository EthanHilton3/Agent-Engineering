// Game state: modes, lives, score, checkpoints, win and game over.
// Modes: 'title' | 'playing' | 'paused' | 'dying' | 'gameover' | 'won'.
var KB = (typeof KB !== 'undefined') ? KB : {};
if (typeof module !== 'undefined') {
  Object.assign(KB, require('./constants.js'), require('../level.js'), require('./physics.js'),
    require('./entities.js'), require('./inhale.js'), require('./player.js'));
}

KB.Game = (function () {
  const C = KB.C;
  const E = KB.Entities;
  const Phys = KB.Physics;

  // opts.rows: custom level rows (tests). opts.mode: starting mode (default 'title').
  function create(opts) {
    opts = opts || {};
    const level = opts.rows ? KB.Level.parse(opts.rows) : KB.Level.load();
    const g = {
      mode: opts.mode || 'title',
      level,
      world: { w: level.w, h: level.h, tiles: level.tiles.slice() },
      score: 0,
      lives: C.START_LIVES,
      tick: 0,
      endTimer: 0,
      deathTimer: 0,
      checkpointIndex: -1,
      checkpoint: { x: level.start.x, y: level.start.y },
      events: [],
      enemies: [],
      pickups: [],
      projectiles: [],
      nextId: 0,
      customRows: opts.rows || null,
    };
    g.player = KB.Player.create(level.start.x, level.start.y);
    g.enemies = level.enemies.map(s => E.createEnemy(g, s.kind, s.tx, s.ty));
    g.pickups = level.pickups.map(s => E.createPickup(g, s.kind, s.tx, s.ty));
    g.goal = level.goal ? Object.assign({}, level.goal) : null;
    return g;
  }

  function restart(g) {
    const fresh = create({ rows: g.customRows, mode: 'playing' });
    Object.keys(g).forEach(k => delete g[k]);
    Object.assign(g, fresh);
    E.emit(g, 'restart');
  }

  function shrink(o, by) { return { x: o.x + by, y: o.y + by, w: o.w - by * 2, h: o.h - by * 2 }; }

  function killPlayer(g) {
    const p = g.player;
    KB.Inhale.releaseAll(g);
    g.mode = 'dying';
    g.deathTimer = C.DEATH_TICKS;
    g.lives--;
    p.vx = 0;
    p.vy = -C.DEATH_POP_SPEED;
    p.mode = 'normal';
    p.held = null;
    E.emit(g, 'die', { x: p.x + p.w / 2, y: p.y });
  }

  function hurtPlayer(g, from) {
    const p = g.player;
    if (p.invuln > 0) return false;
    p.hp--;
    if (p.hp <= 0) { killPlayer(g); return true; }
    p.invuln = C.INVULN_TICKS;
    p.vx = (p.x + p.w / 2 < from.x + from.w / 2 ? -1 : 1) * C.KNOCKBACK_X;
    p.vy = -C.KNOCKBACK_Y;
    if (p.mode === 'fly' || p.mode === 'inhale') p.mode = 'normal';
    E.emit(g, 'hurt', { x: p.x + p.w / 2, y: p.y });
    return true;
  }

  function respawn(g) {
    const cp = g.checkpoint;
    g.player = KB.Player.create(cp.x, cp.y);
    g.player.invuln = C.INVULN_TICKS;
    g.projectiles = [];
    g.mode = 'playing';
    E.emit(g, 'respawn', { x: cp.x, y: cp.y });
  }

  function checkContacts(g) {
    const p = g.player;
    const body = shrink(p, C.CONTACT_INSET);
    for (const e of g.enemies) {
      if (g.mode !== 'playing') break;
      if (e.harmless || e.pulled || !Phys.overlaps(body, e)) continue;
      // Bumping into a regular enemy hurts Kirby but also knocks the enemy out. Gordo just hurts.
      if (hurtPlayer(g, e) && e.kind !== 'gordo') E.defeatEnemy(g, e, C.SCORE_BUMP);
    }
    g.enemies = g.enemies.filter(e => !e.removed);
  }

  function checkPickups(g) {
    const p = g.player;
    for (const k of g.pickups) {
      if (!Phys.overlaps(p, k)) continue;
      k.removed = true;
      const cx = k.x + k.w / 2;
      if (k.kind === 'tomato') {
        p.hp = C.MAX_HP;
        E.addScore(g, C.SCORE_TOMATO, cx, k.y);
        E.emit(g, 'heal', { x: cx, y: k.y });
      } else {
        E.addScore(g, C.SCORE_PICKUP, cx, k.y);
        E.emit(g, 'pickup', { x: cx, y: k.y });
      }
    }
    g.pickups = g.pickups.filter(k => !k.removed);
  }

  function checkCheckpoints(g) {
    const cps = g.level.checkpoints;
    for (let i = g.checkpointIndex + 1; i < cps.length; i++) {
      if (g.player.x >= cps[i].x) {
        g.checkpointIndex = i;
        g.checkpoint = { x: cps[i].x, y: cps[i].y };
        E.emit(g, 'checkpoint', { x: cps[i].x, y: cps[i].y, index: i });
      }
    }
  }

  function win(g) {
    g.mode = 'won';
    g.endTimer = 0;
    KB.Inhale.releaseAll(g);
    const bonus = C.SCORE_GOAL + g.lives * C.SCORE_LIFE_BONUS;
    E.addScore(g, bonus, g.goal.x + g.goal.w / 2, g.goal.y);
    E.emit(g, 'win', { bonus });
  }

  function stepPlaying(g, inp) {
    KB.Player.update(g, inp);
    KB.Inhale.update(g);
    E.updateEnemies(g);
    E.updateProjectiles(g);
    checkPickups(g);
    checkCheckpoints(g);
    if (g.goal && Phys.overlaps(g.player, g.goal)) { win(g); return; }
    checkContacts(g);
    if (g.mode === 'playing' && g.player.y > g.world.h * C.TILE) killPlayer(g);
  }

  function stepDying(g) {
    const p = g.player;
    g.deathTimer--;
    // Hang in the air for a moment, then fall off the screen.
    if (g.deathTimer < C.DEATH_TICKS - C.DEATH_HANG_TICKS) {
      p.vy = Math.min(p.vy + C.GRAVITY * C.DT, C.MAX_FALL_SPEED);
      p.y += p.vy * C.DT;
    }
    if (g.deathTimer <= 0) {
      if (g.lives <= 0) {
        g.mode = 'gameover';
        g.endTimer = 0;
        E.emit(g, 'gameover');
      } else {
        respawn(g);
      }
    }
  }

  // Advance one fixed tick. `inp` is an input snapshot (see input.js).
  function update(g, inp) {
    g.events = [];
    g.tick++;
    if (inp.restartPressed && g.mode !== 'title') { restart(g); return g; }
    const confirm = inp.jumpPressed || inp.actionPressed;
    switch (g.mode) {
      case 'title':
        if (confirm || inp.restartPressed) { g.mode = 'playing'; E.emit(g, 'start'); }
        break;
      case 'paused':
        if (inp.pausePressed) g.mode = 'playing';
        break;
      case 'playing':
        if (inp.pausePressed) { g.mode = 'paused'; break; }
        stepPlaying(g, inp);
        break;
      case 'dying':
        stepDying(g);
        break;
      case 'gameover':
      case 'won': {
        g.endTimer++;
        const wait = g.mode === 'won' ? C.WIN_SCREEN_TICKS : C.END_INPUT_DELAY_TICKS;
        if (confirm && g.endTimer > wait) restart(g);
        break;
      }
    }
    return g;
  }

  return { create, update, restart, hurtPlayer, killPlayer };
})();

if (typeof module !== 'undefined') module.exports = { Game: KB.Game };

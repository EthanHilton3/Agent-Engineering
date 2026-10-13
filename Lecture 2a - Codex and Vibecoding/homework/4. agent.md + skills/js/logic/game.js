// Game state machine: title, playing, paused, confirm-restart, dying, game over, win.
// Owns projectiles and every player-vs-world interaction. Pure logic.
var Game = (function () {
  'use strict';
  var C = typeof CONST !== 'undefined' ? CONST : require('./constants.js').CONST;
  var P = typeof Physics !== 'undefined' ? Physics : require('./physics.js').Physics;
  var W = typeof World !== 'undefined' ? World : require('./world.js').World;
  var E = typeof Enemies !== 'undefined' ? Enemies : require('./enemies.js').Enemies;
  var PL = typeof Player !== 'undefined' ? Player : require('./player.js').Player;
  var B = typeof Boss !== 'undefined' ? Boss : require('./boss.js').Boss;
  var T = C.TILE;
  var DEFAULT_SEED = 20261009;

  function create(level, opts) {
    opts = opts || {};
    var state = {
      level: level, world: W.build(level), mode: 'title', events: [], frame: 0, time: 0,
      score: 0, lives: C.START_LIVES, best: opts.best || 0, seed: opts.seed || DEFAULT_SEED,
      collected: {}, checkpoint: -1, extraLifeAwarded: false, screenTimer: C.SCREEN_INPUT_DELAY,
      deathTimer: 0, maxSection: 0, arenaLocked: false, winBonus: 0, continues: 0, deaths: 0
    };
    state.rngState = state.seed;
    placeAtCheckpoint(state);
    return state;
  }

  function spawnPoint(state) {
    var world = state.world;
    if (state.checkpoint < 0) return world.start;
    var cp = world.checkpoints[state.checkpoint];
    return { x: cp.x + cp.w / 2 - C.PLAYER_W / 2, y: cp.y + cp.h - C.PLAYER_H };
  }

  // Rebuilds everything that resets on a lost life: tiles, enemies, boss, gate.
  // Collected items, score and checkpoint progress survive.
  function placeAtCheckpoint(state) {
    var world = state.world;
    W.resetTiles(world);
    var sp = spawnPoint(state);
    state.player = PL.create(sp.x, sp.y);
    state.enemies = E.spawnAll(world);
    state.projectiles = [];
    state.boss = B.create(world);
    state.warp = world.warp ? { x: world.warp.x, y: world.warp.y, w: world.warp.w, h: world.warp.h, active: false } : null;
    state.arenaLocked = false;
    state.rngState = state.seed;
  }

  function newRun(state) {
    state.score = 0;
    state.lives = C.START_LIVES;
    state.time = 0;
    state.collected = {};
    state.checkpoint = -1;
    state.extraLifeAwarded = false;
    state.maxSection = 0;
    state.continues = 0;
    state.deaths = 0;
    state.winBonus = 0;
    placeAtCheckpoint(state);
    state.mode = 'playing';
    W.emit(state, 'start', state.player.x, state.player.y);
    W.emit(state, 'section', 0, 0, { name: state.world.sections[0].name });
  }

  function respawn(state) {
    placeAtCheckpoint(state);
    state.player.invuln = C.RESPAWN_INVULN_TICKS;
    state.mode = 'playing';
    W.emit(state, 'respawn', state.player.x, state.player.y);
  }

  function continueRun(state) {
    state.lives = C.START_LIVES;
    state.score = 0;
    state.extraLifeAwarded = false;
    state.continues++;
    respawn(state);
  }

  function update(state, input) {
    state.events.length = 0;
    state.frame++;
    if (state.screenTimer > 0) state.screenTimer--;
    var ready = state.screenTimer === 0;
    switch (state.mode) {
      case 'title':
        if (ready && input.jumpPressed) newRun(state);
        break;
      case 'playing':
        if (input.pausePressed) { state.mode = 'paused'; W.emit(state, 'pause'); }
        else if (input.restartPressed) { state.mode = 'confirm'; W.emit(state, 'pause'); }
        else step(state, input);
        break;
      case 'paused':
        if (input.pausePressed) { state.mode = 'playing'; W.emit(state, 'resume'); }
        else if (input.restartPressed) state.mode = 'confirm';
        break;
      case 'confirm':
        if (input.restartPressed) newRun(state);
        else if (input.pausePressed) { state.mode = 'playing'; W.emit(state, 'resume'); }
        break;
      case 'dying':
        if (--state.deathTimer <= 0) loseLife(state);
        break;
      case 'gameover':
        if (ready && input.jumpPressed) continueRun(state);
        else if (ready && input.restartPressed) newRun(state);
        break;
      case 'win':
        if (ready && (input.jumpPressed || input.restartPressed)) newRun(state);
        break;
    }
  }

  function loseLife(state) {
    state.lives -= 1;
    state.deaths += 1;
    if (state.lives <= 0) {
      state.mode = 'gameover';
      state.best = Math.max(state.best, state.score);
      state.screenTimer = C.SCREEN_INPUT_DELAY;
      W.emit(state, 'gameOver');
    } else {
      respawn(state);
    }
  }

  function step(state, input) {
    state.time++;
    PL.update(state, input);
    PL.applyInhale(state);
    E.update(state);
    B.update(state);
    updateProjectiles(state);
    interact(state);
    E.removeDead(state);
  }

  function starHitsTiles(state, pr) {
    var world = state.world;
    var c0 = Math.floor(pr.x / T), c1 = Math.floor((pr.x + pr.w - 1) / T);
    var r0 = Math.floor(pr.y / T), r1 = Math.floor((pr.y + pr.h - 1) / T);
    for (var c = c0; c <= c1; c++) {
      for (var r = r0; r <= r1; r++) {
        var t = P.tileAt(world, c, r);
        if (t === P.TILES.STAR) {
          P.setTile(world, c, r, P.TILES.EMPTY);
          W.addScore(state, C.SCORE.block);
          W.emit(state, 'blockBreak', c * T + T / 2, r * T + T / 2);
          if (!pr.pierce) pr.dead = true;
        } else if (P.isSolid(t)) {
          pr.dead = true;
        }
      }
    }
    if (pr.dead) W.emit(state, 'starPoof', pr.x + pr.w / 2, pr.y + pr.h / 2);
  }

  function projectileHitsEnemies(state, pr) {
    for (var i = 0; i < state.enemies.length && !pr.dead; i++) {
      var e = state.enemies[i];
      if (e.dead || e.caught || !P.overlaps(pr, e)) continue;
      if (e.type === 'spiky') {
        pr.dead = true;
        W.emit(state, 'clink', pr.x + pr.w / 2, pr.y + pr.h / 2);
      } else if (E.DEFEATABLE[e.type]) {
        E.defeat(state, e);
        if (!pr.pierce) pr.dead = true;
      }
    }
    var b = state.boss;
    if (!pr.dead && b && B.alive(b) && P.overlaps(pr, b)) {
      if (pr.kind === 'star') B.hit(state, pr.power);
      pr.dead = true;
      W.emit(state, 'starPoof', pr.x + pr.w / 2, pr.y + pr.h / 2);
    }
  }

  function updateProjectiles(state) {
    state.projectiles.forEach(function (pr) {
      pr.x += pr.vx;
      if (pr.kind === 'air') pr.vx *= C.AIR_PUFF_DRAG;
      if (pr.kind === 'star') starHitsTiles(state, pr);
      else if (P.solidAtPoint(state.world, pr.x + pr.w / 2, pr.y + pr.h / 2)) pr.dead = true;
      if (!pr.dead) projectileHitsEnemies(state, pr);
      if (--pr.life <= 0 && !pr.dead) {
        pr.dead = true;
        if (pr.kind === 'star') W.emit(state, 'starPoof', pr.x + pr.w / 2, pr.y + pr.h / 2);
      }
    });
    state.projectiles = state.projectiles.filter(function (pr) { return !pr.dead; });
  }

  function collect(state, it) {
    var p = state.player;
    state.collected[it.id] = true;
    if (it.kind === 'star') W.addScore(state, C.SCORE.star);
    if (it.kind === 'food') { p.health = C.MAX_HEALTH; W.addScore(state, C.SCORE.food); }
    if (it.kind === 'oneup') state.lives += 1;
    W.emit(state, 'pickup', it.x + it.w / 2, it.y + it.h / 2, { kind: it.kind });
  }

  function lockArena(state) {
    var world = state.world;
    state.arenaLocked = true;
    for (var r = 0; r < world.groundRow; r++) P.setTile(world, world.gateCol, r, P.TILES.STONE);
    B.wake(state);
    W.emit(state, 'arenaLock', world.gateCol * T, 0);
  }

  function win(state) {
    var seconds = Math.floor(state.time / C.TICKS_PER_SECOND);
    state.winBonus = Math.max(0, C.TIME_BONUS_MAX - seconds * C.TIME_BONUS_PER_SECOND);
    W.addScore(state, state.winBonus);
    state.best = Math.max(state.best, state.score);
    state.mode = 'win';
    state.screenTimer = C.SCREEN_INPUT_DELAY;
    W.emit(state, 'win', state.warp.x, state.warp.y);
  }

  function interact(state) {
    var p = state.player, world = state.world, i;
    if (p.y > world.h * T + C.PIT_MARGIN) { PL.kill(state); return; }
    if (P.onSpikes(world, p)) PL.hurt(state, p.x + p.w / 2 + p.facing);

    for (i = 0; i < state.enemies.length && state.mode === 'playing'; i++) {
      var e = state.enemies[i];
      if (!e.dead && e.harmful && !e.caught && P.overlaps(p, e)) PL.hurt(state, e.x + e.w / 2);
    }
    var b = state.boss;
    if (b && B.alive(b) && state.mode === 'playing' && P.overlaps(p, b)) PL.hurt(state, b.x + b.w / 2);
    if (state.mode !== 'playing') return;

    world.items.forEach(function (it) {
      if (!state.collected[it.id] && P.overlaps(p, it)) collect(state, it);
    });
    // A checkpoint counts as soon as Kirby passes it, even flying high above it.
    world.checkpoints.forEach(function (cp) {
      if (cp.index > state.checkpoint && p.x + p.w / 2 >= cp.x) {
        state.checkpoint = cp.index;
        W.emit(state, 'checkpoint', cp.x + cp.w / 2, cp.y);
      }
    });
    var bossWaiting = state.boss && state.boss.state === 'dormant';
    if (!state.arenaLocked && bossWaiting && p.x > world.gateCol * T + C.ARENA_LOCK_OFFSET) lockArena(state);
    if (state.warp && state.warp.active && P.overlaps(p, state.warp)) { win(state); return; }

    var si = W.sectionIndexAt(world, p.x + p.w / 2);
    if (si > state.maxSection) {
      state.maxSection = si;
      W.emit(state, 'section', 0, 0, { name: world.sections[si].name });
    }
  }

  function pause(state) {
    if (state.mode !== 'playing') return;
    state.mode = 'paused';
    W.emit(state, 'pause');
  }

  return {
    create: create,
    update: update,
    newRun: newRun,
    pause: pause
  };
})();

if (typeof module !== 'undefined') module.exports = { Game };

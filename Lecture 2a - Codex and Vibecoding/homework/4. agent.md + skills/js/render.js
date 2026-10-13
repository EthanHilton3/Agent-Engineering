// Draws the game state. Owns only visual state: camera, particles, floating text, shake, banners.
var Renderer = (function () {
  'use strict';
  var C = CONST, T = C.TILE, VW = C.VIEW_W, VH = C.VIEW_H;
  var TL = Physics.TILES, PAL = Sprites.PAL;

  // Visual-only tuning (camera feel and effects); gameplay numbers live in CONST.
  var FX = {
    CAM_LERP: 0.12, CAM_LEAD: 28, CAM_LEAD_SPEED: 0.8, CAM_Y_OFFSET: 130,
    SHAKE_DECAY: 0.85, FLOATER_TICKS: 50, NOFLY_COOLDOWN: 60, WIND_STREAKS: 14, SPARKLE_EVERY: 6,
    INHALE_LINES: 11, SWALLOW_SHRINK_DIST: 28, SWALLOW_MIN_SCALE: 0.35
  };

  var ctx = null;
  var cam = { x: 0, y: 0, lead: FX.CAM_LEAD, shake: 0 };
  var particles = [], floaters = [], banner = null, flash = 0, noFlyCooldown = 0;
  var windStreaks = [];

  function init(context) {
    ctx = context;
    for (var i = 0; i < FX.WIND_STREAKS; i++) windStreaks.push({ x: Math.random() * VW, y: Math.random() * VH, s: 2 + Math.random() * 3 });
  }

  function camTarget(state) {
    var p = state.player, world = state.world;
    var minX = state.arenaLocked ? world.gateCol * T : 0;
    var tx = Math.max(minX, Math.min(world.w * T - VW, p.x + p.w / 2 - VW / 2 + cam.lead));
    var ty = Math.max(0, Math.min(world.h * T - VH, p.y + p.h / 2 - FX.CAM_Y_OFFSET));
    return { x: tx, y: ty };
  }

  function snapCamera(state) {
    cam.lead = state.player.facing * FX.CAM_LEAD;
    var t = camTarget(state);
    cam.x = t.x; cam.y = t.y;
  }

  function spawn(x, y, n, opts) {
    for (var i = 0; i < n; i++) {
      var a = (opts.angle !== undefined ? opts.angle : Math.random() * Math.PI * 2) + (Math.random() - 0.5) * (opts.spread || 0);
      var sp = (opts.speed || 1) * (0.5 + Math.random() * 0.8);
      particles.push({
        x: x, y: y, vx: Math.cos(a) * sp, vy: Math.sin(a) * sp, g: opts.g || 0, life: opts.life || 20,
        max: opts.life || 20, color: opts.color || 'w', size: opts.size || 2, sprite: opts.sprite
      });
    }
  }

  function floater(x, y, text, color) {
    floaters.push({ x: x, y: y, text: text, color: color || 'w', life: FX.FLOATER_TICKS });
  }

  function onEvent(ev, state) {
    var x = ev.x, y = ev.y;
    switch (ev.type) {
      case 'start': case 'respawn': snapCamera(state); particles = []; break;
      case 'jump': case 'land': case 'appleLand': spawn(x, y, 4, { angle: -Math.PI / 2, spread: 2.6, speed: 0.8, color: 'S', life: 14 }); break;
      case 'flap': spawn(x, y, 2, { angle: Math.PI / 2, spread: 1.2, speed: 0.7, color: 'w', life: 12 }); break;
      case 'deflate': spawn(x + ev.facing * 8, y, 5, { angle: ev.facing > 0 ? 0 : Math.PI, spread: 1, speed: 1.4, color: 'w', size: 3, life: 14 }); break;
      case 'defeat':
        spawn(x, y, 8, { speed: 1.8, sprite: 'pointstar0', life: 22 });
        floater(x, y - 8, '+' + (C.SCORE[ev.kind] || 0), 'y');
        cam.shake = Math.max(cam.shake, 2);
        break;
      case 'swallow':
        spawn(x, y, 6, { speed: 1.2, color: 'p', life: 12 });
        floater(x, y - 14, ev.count > 1 ? 'BIG STAR!' : 'GULP!', 'p');
        break;
      case 'spit': spawn(x, y, 5, { angle: ev.facing > 0 ? 0 : Math.PI, spread: 1.4, speed: 1.6, color: 'y', life: 12 }); break;
      case 'exhale': break;
      case 'blockGrab': spawn(x, y, 4, { speed: 0.8, color: 'o', life: 12 }); break;
      case 'blockBreak':
        spawn(x, y, 8, { speed: 2, g: 0.15, color: 'o', size: 3, life: 26 });
        spawn(x, y, 4, { speed: 1.5, g: 0.15, color: 'y', size: 2, life: 22 });
        break;
      case 'starPoof': spawn(x, y, 6, { speed: 1.2, color: 'y', life: 12 }); break;
      case 'clink': spawn(x, y, 6, { speed: 1.6, color: 'w', size: 1, life: 10 }); floater(x, y - 10, 'CLINK!', 'n'); break;
      case 'puffPop': spawn(x, y, 5, { speed: 0.9, color: 'w', size: 3, life: 12 }); break;
      case 'hurt': cam.shake = Math.max(cam.shake, 4); flash = 4; spawn(x, y, 8, { speed: 1.8, color: 'r', life: 16 }); break;
      case 'drop': floater(x, y - 12, 'DROPPED IT!', 'n'); break;
      case 'death': cam.shake = 6; break;
      case 'pickup':
        spawn(x, y, 6, { speed: 1.3, color: 'y', life: 16 });
        floater(x, y - 8, ev.kind === 'star' ? '+' + C.SCORE.star : ev.kind === 'food' ? 'HEALTH UP!' : '1UP!', ev.kind === 'star' ? 'y' : 'p');
        break;
      case 'oneUp': floater(x, y - 20, '1UP!', 'p'); break;
      case 'checkpoint': spawn(x, y, 10, { speed: 1.6, sprite: 'pointstar0', life: 24 }); floater(x, y - 8, 'CHECKPOINT!', 'y'); break;
      case 'noFly':
        if (noFlyCooldown === 0) { floater(x, y - 10, 'SPIT FIRST!', 'r'); noFlyCooldown = FX.NOFLY_COOLDOWN; }
        break;
      case 'section': banner = { text: ev.name, timer: C.BANNER_TICKS }; break;
      case 'arenaLock': cam.shake = 6; banner = { text: 'OLD GNARLWOOD', timer: C.BANNER_TICKS }; break;
      case 'bossHit': cam.shake = 6; flash = 3; spawn(x, y, 10, { speed: 2.2, sprite: 'pointstar0', life: 20 }); break;
      case 'bossBoom': spawn(x, y, 6, { speed: 1.5, color: 'w', size: 4, life: 18 }); spawn(x, y, 4, { speed: 1, color: 'y', size: 3, life: 14 }); cam.shake = 3; break;
      case 'bossDefeated': flash = 10; cam.shake = 10; floater(x, y - 30, '+' + C.SCORE.boss, 'y'); break;
      case 'win': spawn(x + 12, y + 12, 24, { speed: 2.5, sprite: 'pointstar0', life: 40 }); break;
    }
  }

  // Called once per fixed update.
  function tick(state) {
    if (state.mode === 'playing' || state.mode === 'dying' || state.mode === 'title' || state.mode === 'win') {
      if (state.mode === 'playing') cam.lead += Math.max(-FX.CAM_LEAD_SPEED, Math.min(FX.CAM_LEAD_SPEED, state.player.facing * FX.CAM_LEAD - cam.lead));
      var t = camTarget(state);
      if (state.mode !== 'dying') {
        cam.x += (t.x - cam.x) * FX.CAM_LERP;
        cam.y += (t.y - cam.y) * FX.CAM_LERP;
      }
    }
    if (state.mode === 'paused' || state.mode === 'confirm') return;
    cam.shake *= FX.SHAKE_DECAY;
    if (cam.shake < 0.3) cam.shake = 0;
    if (flash > 0) flash--;
    if (noFlyCooldown > 0) noFlyCooldown--;
    if (banner && --banner.timer <= 0) banner = null;
    var wp = state.warp;
    if (wp && wp.active && state.frame % FX.SPARKLE_EVERY === 0) spawn(wp.x + wp.w / 2, wp.y + wp.h / 2, 1, { speed: 0.6, sprite: 'pointstar0', life: 30 });
    particles.forEach(function (p) { p.x += p.vx; p.y += p.vy; p.vy += p.g; p.life--; });
    particles = particles.filter(function (p) { return p.life > 0; });
    floaters.forEach(function (f) { f.y -= 0.4; f.life--; });
    floaters = floaters.filter(function (f) { return f.life > 0; });
  }

  // Integer camera position for this frame, including shake.
  function view() {
    var sx = cam.shake ? Math.round((Math.random() - 0.5) * cam.shake) : 0;
    var sy = cam.shake ? Math.round((Math.random() - 0.5) * cam.shake) : 0;
    return { x: Math.round(cam.x) + sx, y: Math.round(cam.y) + sy };
  }

  function sprite(name, x, y, flip) {
    var s = Sprites.get(name);
    ctx.drawImage(flip ? s.l : s.r, Math.round(x), Math.round(y));
  }

  // Draw a sprite centred on a body horizontally and standing on its bottom edge.
  function onBody(name, b, v, flip, dy) {
    var s = Sprites.get(name);
    sprite(name, b.x + b.w / 2 - s.w / 2 - v.x, b.y + b.h - s.h - v.y + (dy || 0), flip);
  }

  function drawBackground(state, v) {
    var inArena = state.arenaLocked || (state.world.gateCol >= 0 && v.x > state.world.gateCol * T - VW / 2);
    ctx.fillStyle = inArena ? PAL.v : PAL.s;
    ctx.fillRect(0, 0, VW, VH);
    var horizon = VH - 40 - (v.y - (state.world.h * T - VH)) * 0.3;
    var far = Sprites.get('bg_far'), hills = Sprites.get('bg_hills'), cloud = Sprites.get('bg_cloud');
    var fx = -Math.round(v.x * 0.15) % far.w;
    for (var x = fx - far.w; x < VW + far.w; x += far.w) ctx.drawImage(far.r, x, Math.round(horizon - far.h + 10));
    for (var i = 0; i < 6; i++) {
      var cxp = ((i * 113 - v.x * 0.3 - state.frame * 0.05) % 340 + 340) % 340 - 48;
      ctx.drawImage(cloud.r, Math.round(cxp), Math.round(horizon - 120 + (i * 37) % 60));
    }
    var hx = -Math.round(v.x * 0.4) % hills.w;
    for (var x2 = hx - hills.w; x2 < VW + hills.w; x2 += hills.w) ctx.drawImage(hills.r, x2, Math.round(horizon - hills.h + 34));
    ctx.fillStyle = PAL.G;
    ctx.fillRect(0, Math.round(horizon + 34), VW, VH);
  }

  function drawTiles(state, v) {
    var world = state.world;
    state.world.caves.forEach(function (cv) {
      if (cv.x1 < v.x || cv.x0 > v.x + VW) return;
      ctx.fillStyle = PAL.N;
      ctx.fillRect(cv.x0 - v.x, cv.top - v.y, cv.x1 - cv.x0, world.groundRow * T - cv.top);
    });
    var c0 = Math.floor(v.x / T), c1 = Math.floor((v.x + VW) / T);
    var r0 = Math.max(0, Math.floor(v.y / T)), r1 = Math.min(world.h - 1, Math.floor((v.y + VH) / T));
    for (var r = r0; r <= r1; r++) {
      for (var c = c0; c <= c1; c++) {
        var t = Physics.tileAt(world, c, r);
        if (t === TL.EMPTY || c < 0 || c >= world.w) continue;
        var name = 'tile_stone';
        if (t === TL.GROUND) name = Physics.isSolid(Physics.tileAt(world, c, r - 1)) || r === 0 ? 'tile_dirt' : 'tile_grass';
        else if (t === TL.PLATFORM) name = 'tile_platform';
        else if (t === TL.STAR) name = 'tile_star';
        else if (t === TL.SPIKES) name = 'tile_spikes';
        ctx.drawImage(Sprites.get(name).r, c * T - v.x, r * T - v.y);
      }
    }
  }

  function groundBelow(world, x) {
    var c = Math.floor(x / T);
    for (var r = 0; r < world.h; r++) if (Physics.isSolid(Physics.tileAt(world, c, r))) return r * T;
    return world.h * T;
  }

  function drawProps(state, v) {
    var world = state.world, f = state.frame;
    world.signs.forEach(function (s) {
      if (s.x < v.x - 80 || s.x > v.x + VW + 80) return;
      var gy = groundBelow(world, s.x);
      sprite('sign', s.x - 8 - v.x, gy - 16 - v.y);
      var w = Font.measure(s.text) + 6;
      ctx.globalAlpha = 0.75; ctx.fillStyle = PAL.K;
      ctx.fillRect(Math.round(s.x - w / 2 - v.x), gy - 30 - v.y, w, 9);
      ctx.globalAlpha = 1;
      Font.draw(ctx, s.text, s.x - v.x, gy - 28 - v.y, 'w', { align: 'center' });
    });
    world.checkpoints.forEach(function (cp) {
      var on = cp.index <= state.checkpoint;
      sprite(on ? (Math.floor(f / 12) % 2 ? 'checkpoint_on1' : 'checkpoint_on0') : 'checkpoint_off', cp.x - 3 - v.x, cp.y + cp.h - 26 - v.y);
    });
    world.items.forEach(function (it) {
      if (state.collected[it.id] || it.x < v.x - 16 || it.x > v.x + VW) return;
      var bob = Math.round(Math.sin((f + it.id * 9) * 0.08) * 1.5);
      var name = it.kind === 'star' ? 'pointstar' + (Math.floor((f + it.id * 5) / 8) % 4) : it.kind;
      var s = Sprites.get(name);
      sprite(name, it.x + it.w / 2 - s.w / 2 - v.x, it.y + it.h / 2 - s.h / 2 - v.y + bob);
    });
    var wp = state.warp;
    if (wp && wp.active) {
      var wy = Math.round(Math.sin(f * 0.07) * 3);
      sprite('warp' + (Math.floor(f / 10) % 2), wp.x - 2 - v.x, wp.y - 2 - v.y + wy);
    }
  }

  function drawBoss(state, v) {
    var b = state.boss;
    if (!b) return;
    var name = 'boss_idle';
    if (b.state === 'dead' || b.state === 'dying') name = 'boss_dead';
    else if (b.invuln > 0) name = 'boss_hurt';
    else if (b.mouthOpen > 0) name = 'boss_blow';
    if ((b.invuln > 0 || b.state === 'dying') && Math.floor(state.frame / 3) % 2) return;
    var jx = b.state === 'dying' || b.state === 'intro' ? Math.round(Math.sin(state.frame * 1.7) * 1.5) : 0;
    sprite(name, b.x - 20 - v.x + jx, b.y + b.h - 120 - v.y);
  }

  function enemySprite(e, f) {
    switch (e.type) {
      case 'walker': return 'walker' + (Math.floor(e.t / 12) % 2);
      case 'flyer': return 'flyer' + (Math.floor(e.t / 7) % 2);
      case 'hopper': return e.onGround && e.timer < C.HOPPER_WAIT - 12 ? 'hopper0' : 'hopper1';
      case 'spiky': return 'spiky' + (Math.floor(e.t / 10) % 2);
      case 'apple': return 'apple';
      case 'bosspuff': return 'bosspuff';
      default: return e.kind === 'block' ? 'tile_star' : 'spit12_' + (Math.floor(f / 4) % 4);
    }
  }

  function drawEnemies(state, v) {
    state.enemies.forEach(function (e) {
      if (e.x + e.w < v.x - 24 || e.x > v.x + VW + 24) return;
      if (e.type === 'loose' && e.life < 60 && Math.floor(state.frame / 3) % 2) return;
      var jitter = (e.caught || e.stun > 0) ? (Math.floor(state.frame / 2) % 2 ? 1 : -1) : 0;
      var name = enemySprite(e, state.frame);
      var s = Sprites.get(name);
      var cx = e.x + e.w / 2 - v.x + jitter, by = e.y + e.h - v.y;
      if (e.type === 'flyer' || e.type === 'spiky' || e.type === 'bosspuff') by = e.y + e.h / 2 + s.h / 2 - v.y;
      var img = e.facing < 0 ? s.l : s.r;
      if (e.caught) {
        // Being swallowed: shrink as it nears Kirby's mouth.
        var m = Player.mouthPoint(state.player);
        var d = Math.hypot(e.x + e.w / 2 - m.x, e.y + e.h / 2 - m.y);
        var k = Math.max(FX.SWALLOW_MIN_SCALE, Math.min(1, d / FX.SWALLOW_SHRINK_DIST));
        var w = Math.round(s.w * k), h = Math.round(s.h * k);
        ctx.drawImage(img, Math.round(e.x + e.w / 2 - v.x - w / 2), Math.round(e.y + e.h / 2 - v.y - h / 2), w, h);
        return;
      }
      ctx.drawImage(img, Math.round(cx - s.w / 2), Math.round(by - s.h));
    });
    state.projectiles.forEach(function (pr) {
      var name = pr.kind === 'air' ? 'airpuff' : 'spit' + (pr.big ? 16 : 12) + '_' + (Math.floor(state.frame / 3) % 4);
      sprite(name, pr.x - v.x, pr.y - v.y, pr.vx < 0);
    });
  }

  function kirbyFrame(state) {
    var p = state.player, t = p.animT;
    if (state.mode === 'dying' || p.hurtTimer > 0) return 'hurt';
    if (p.inhaling) return Math.floor(state.frame / 4) % 2 ? 'inhale1' : 'inhale0';
    if (p.spitAnim > 0) return 'spit';
    if (p.flying) return p.flapAnim > C.FLAP_ANIM_TICKS / 2 ? 'fly1' : (p.flapAnim > 0 ? 'fly0' : (Math.floor(t / 16) % 2 ? 'fly0' : 'fly1'));
    if (p.mouth) return p.onGround && Math.abs(p.vx) > 0.2 ? (Math.floor(t / 8) % 2 ? 'full1' : 'full2') : 'full0';
    if (!p.onGround) return p.vy < 0 ? 'jump' : 'fall';
    if (Math.abs(p.vx) > 0.2) return 'run' + (Math.floor(t / 4) % 4);
    if (t % 180 < 6) return 'blink';
    return Math.floor(t / 32) % 2 ? 'idle1' : 'idle0';
  }

  function drawInhaleWind(p, v, f, world) {
    var m = Player.mouthPoint(p);
    ctx.fillStyle = PAL.w;
    for (var k = 0; k < FX.INHALE_LINES; k++) {
      var d = C.INHALE_RANGE - ((f * 4 + k * 23) % C.INHALE_RANGE);
      var spread = (C.INHALE_HALF_HEIGHT + d * C.INHALE_SPREAD) * (((k * 37) % 11) / 5.5 - 1);
      var x = m.x + p.facing * d - v.x, y = m.y + spread * (d / C.INHALE_RANGE) - v.y;
      if (!Physics.clearLine(world, m.x, m.y, x + v.x, y + v.y)) continue;
      ctx.globalAlpha = 0.4 + 0.6 * (1 - d / C.INHALE_RANGE);
      var len = 3 + Math.round(5 * d / C.INHALE_RANGE);
      ctx.fillRect(Math.round(x - (p.facing > 0 ? 0 : len - 1)), Math.round(y), len, 1);
    }
    ctx.globalAlpha = 1;
  }

  function drawPlayer(state, v) {
    var p = state.player, f = state.frame;
    if (state.mode === 'dying') {
      var dt = C.DEATH_TICKS - state.deathTimer, lift = 0;
      if (dt > 30) { var k = dt - 30; lift = k * 3.5 - 0.09 * k * k; }
      onBody('kirby_hurt', p, v, Math.floor(dt / 8) % 2 === 0, -lift);
      return;
    }
    if (p.invuln > 0 && p.hurtTimer === 0 && Math.floor(f / 3) % 2) return;
    if (p.inhaling) drawInhaleWind(p, v, f, state.world);
    onBody('kirby_' + kirbyFrame(state), p, v, p.facing < 0);
  }

  function drawParticles(v) {
    particles.forEach(function (p) {
      if (p.sprite) { var s = Sprites.get(p.sprite); ctx.drawImage(s.r, Math.round(p.x - s.w / 2 - v.x), Math.round(p.y - s.h / 2 - v.y)); return; }
      ctx.fillStyle = PAL[p.color];
      var sz = Math.max(1, Math.round(p.size * (p.life / p.max + 0.3)));
      ctx.fillRect(Math.round(p.x - v.x - sz / 2), Math.round(p.y - v.y - sz / 2), sz, sz);
    });
    floaters.forEach(function (fl) {
      ctx.globalAlpha = Math.min(1, fl.life / 15);
      Font.draw(ctx, fl.text, fl.x - v.x, fl.y - v.y, fl.color, { align: 'center', shadow: 'K' });
    });
    ctx.globalAlpha = 1;
  }

  function drawWind(state, v) {
    var push = World.windAt(state.world, v.x + VW / 2, state.time);
    if (!push) return;
    var s = Sprites.get('wind_streak');
    ctx.globalAlpha = 0.6;
    windStreaks.forEach(function (w) {
      w.x += push * w.s * 2;
      if (w.x < -16) { w.x = VW + Math.random() * 40; w.y = Math.random() * VH; }
      ctx.drawImage(s.r, Math.round(w.x), Math.round(w.y));
    });
    ctx.globalAlpha = 1;
  }

  function draw(state, opts) {
    var v = view();
    drawBackground(state, v);
    drawTiles(state, v);
    drawProps(state, v);
    drawBoss(state, v);
    drawEnemies(state, v);
    if (state.mode !== 'title') drawPlayer(state, v);
    drawParticles(v);
    drawWind(state, v);
    if (flash > 0) { ctx.globalAlpha = flash / 12; ctx.fillStyle = PAL.w; ctx.fillRect(0, 0, VW, VH); ctx.globalAlpha = 1; }
    Hud.draw(ctx, state, { banner: state.mode === 'playing' ? banner : null, muted: opts && opts.muted });
  }

  return { init: init, tick: tick, onEvent: onEvent, draw: draw, snapCamera: snapCamera };
})();

// Draws the world: background, tiles, entities, Kirby and effects. Reads game state, never changes it.
var KB = (typeof KB !== 'undefined') ? KB : {};

KB.Render = (function () {
  const C = KB.C;
  const T = C.T;
  const PAL = KB.PAL;
  const S = C.TILE;
  const hash = (x, y) => KB.Tiles.hash(x, y);

  function create(ctx, sprites) {
    const r = {
      ctx, sp: sprites, camX: 0, shake: 0, particles: [], texts: [], frame: 0, hiScore: 0, muted: false,
      sky: buildSky(),
    };
    r.onEvents = events => onEvents(r, events);
    r.step = game => step(r, game);
    r.draw = game => draw(r, game);
    r.snapCamera = game => { r.camX = cameraTarget(game); };
    return r;
  }

  function buildSky() {
    const cv = document.createElement('canvas');
    cv.width = C.VIEW_W; cv.height = C.VIEW_H;
    const ctx = cv.getContext('2d');
    const bands = [PAL.skyDeep, PAL.sky, PAL.skyLight];
    const bandH = C.VIEW_H / bands.length;
    for (let y = 0; y < C.VIEW_H; y++) {
      const b = Math.min(bands.length - 1, Math.floor(y / bandH));
      const into = y - b * bandH;
      for (let x = 0; x < C.VIEW_W; x++) {
        // ordered dither into the next band for the last few rows of each band
        const next = b < bands.length - 1 && into > bandH - 8 && ((x + y) % 2 === 0) && (into > bandH - 4 || x % 4 === 0);
        ctx.fillStyle = next ? bands[b + 1] : bands[b];
        ctx.fillRect(x, y, 1, 1);
      }
    }
    return cv;
  }

  // ---- camera ----------------------------------------------------------------
  function cameraTarget(g) {
    const p = g.player;
    const maxX = g.world.w * S - C.VIEW_W;
    return Math.max(0, Math.min(maxX, p.x + p.w / 2 - C.VIEW_W / 2 + p.facing * 24));
  }

  // ---- effects ----------------------------------------------------------------
  function burst(r, x, y, n, colors, speed, life, gravity) {
    for (let i = 0; i < n; i++) {
      const a = (i / n) * Math.PI * 2 + hash(r.frame, i) * 0.6;
      const sp = speed * (0.5 + hash(i, r.frame) * 0.7);
      r.particles.push({ x, y, vx: Math.cos(a) * sp, vy: Math.sin(a) * sp, life, max: life,
        color: colors[i % colors.length], g: gravity || 0, size: 2 });
    }
  }
  function dust(r, x, y, n) {
    for (let i = 0; i < n; i++) {
      const dir = i % 2 ? 1 : -1;
      r.particles.push({ x: x + dir * 4, y: y - 1, vx: dir * (20 + i * 8), vy: -10 - i * 4, life: 16, max: 16,
        color: PAL.white, g: 0, size: 3, puff: true });
    }
  }

  function onEvents(r, events) {
    for (const ev of events) {
      switch (ev.type) {
        case 'jump': dust(r, ev.x, ev.y, 2); break;
        case 'land': if (ev.speed > 150) dust(r, ev.x, ev.y, 4); break;
        case 'flap': dust(r, ev.x, ev.y, 2); break;
        case 'swallow': burst(r, ev.x, ev.y, 8, [PAL.yellow, PAL.white], 50, 18); r.shake = Math.max(r.shake, 2); break;
        case 'spit': dust(r, ev.x, ev.y + 4, 2); r.shake = Math.max(r.shake, 1); break;
        case 'defeat': burst(r, ev.x, ev.y, 10, [PAL.yellow, PAL.white, PAL.orange], 90, 24); r.shake = Math.max(r.shake, 2); break;
        case 'blockBreak': case 'blockPop':
          burst(r, ev.x, ev.y, 8, [PAL.orangeLight, PAL.orangeDark, PAL.yellow], 80, 30, 300); r.shake = Math.max(r.shake, 2); break;
        case 'starBurst': burst(r, ev.x, ev.y, 8, [PAL.yellow, PAL.yellowLight], 60, 16); break;
        case 'puffGone': burst(r, ev.x, ev.y, 4, [PAL.white, PAL.skyLight], 30, 10); break;
        case 'clink': burst(r, ev.x, ev.y, 6, [PAL.white, PAL.stoneLight], 70, 12); break;
        case 'hurt': burst(r, ev.x, ev.y, 6, [PAL.yellow, PAL.white], 80, 20); r.shake = 5; break;
        case 'die': r.shake = 7; break;
        case 'pickup': burst(r, ev.x, ev.y, 6, [PAL.yellow, PAL.white], 40, 14); break;
        case 'heal': burst(r, ev.x, ev.y, 10, [PAL.pink, PAL.white, PAL.red], 50, 24); break;
        case 'checkpoint': burst(r, ev.x + 8, ev.y - 8, 12, [PAL.yellow, PAL.red, PAL.white, PAL.green], 70, 30, 120); break;
        case 'score': r.texts.push({ x: ev.x, y: ev.y, text: '+' + ev.value, life: 45 }); break;
        case 'respawn': case 'restart': r.particles = []; r.texts = []; r.needSnap = true; break;
      }
    }
  }

  function step(r, g) {
    for (const p of r.particles) {
      p.vy += p.g * C.DT;
      p.x += p.vx * C.DT; p.y += p.vy * C.DT;
      p.vx *= 0.94; if (!p.g) p.vy *= 0.94;
      p.life--;
    }
    r.particles = r.particles.filter(p => p.life > 0);
    for (const t of r.texts) { t.y -= 0.5; t.life--; }
    r.texts = r.texts.filter(t => t.life > 0);
    if (r.shake > 0) r.shake = Math.max(0, r.shake - 0.25);
    if (g.mode === 'won' && g.endTimer % 4 === 0) {
      const s = winStarPos(g);
      burst(r, s.x + 14, s.y + 14, 2, [PAL.yellow, PAL.pink, PAL.skyLight, PAL.white], 40, 30);
    }
    r.frame++;
  }

  // ---- drawing ------------------------------------------------------------------
  function draw(r, g) {
    const ctx = r.ctx;
    if (r.needSnap) { r.snapCamera(g); r.needSnap = false; }
    if (g.mode === 'playing' || g.mode === 'title') r.camX += (cameraTarget(g) - r.camX) * 0.12;
    const sx = r.shake ? Math.round((hash(r.frame, 1) - 0.5) * r.shake) : 0;
    const sy = r.shake ? Math.round((hash(r.frame, 2) - 0.5) * r.shake) : 0;
    const cam = Math.round(r.camX) - sx;

    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(r.sky, 0, 0);
    ctx.save();
    ctx.translate(0, sy);
    drawBackground(r, cam);
    drawBushes(r, g, cam);
    drawTiles(r, g, cam);
    drawDecor(r, g, cam);
    drawGoal(r, g, cam);
    drawPickups(r, g, cam);
    drawEnemies(r, g, cam);
    drawProjectiles(r, g, cam);
    if (g.mode !== 'won') drawPlayer(r, g, cam);
    if (g.player.mode === 'inhale' && g.mode === 'playing') drawInhaleWind(r, g, cam);
    drawParticles(r, cam);
    ctx.restore();
    KB.Hud.draw(r, g);
  }

  function tiled(ctx, img, offset, y) {
    const w = img.width;
    let x = -(((offset % w) + w) % w);
    for (; x < C.VIEW_W; x += w) ctx.drawImage(img, x, y);
  }

  function drawBackground(r, cam) {
    const ctx = r.ctx;
    const cl = r.sp.skyCloud;
    for (let i = 0; i < 4; i++) {
      const span = C.VIEW_W + cl.width * 2;
      const x = ((i * 113 - cam * 0.1 - r.frame * 0.05) % span + span) % span - cl.width;
      ctx.drawImage(cl, Math.round(x), 14 + (i % 2) * 22 + i * 3);
    }
    tiled(ctx, r.sp.bgFar, Math.round(cam * 0.2), C.VIEW_H - 90 - 22);
    tiled(ctx, r.sp.bgNear, Math.round(cam * 0.45), C.VIEW_H - 70 - 8);
  }

  function tileVisibleRange(cam) {
    return [Math.max(0, Math.floor(cam / S)), Math.ceil((cam + C.VIEW_W) / S)];
  }
  function isGround(g, tx, ty) {
    const t = KB.Physics.tileAt(g.world, tx, ty);
    return t === T.GROUND;
  }

  function drawBushes(r, g, cam) {
    const [x0, x1] = tileVisibleRange(cam);
    for (let tx = x0 - 2; tx <= x1; tx++) {
      if (hash(tx, 5) > 0.14) continue;
      for (let ty = 1; ty < g.world.h; ty++) {
        if (isGround(g, tx, ty) && !KB.Physics.isSolidAt(g.world, tx, ty - 1) && isGround(g, tx + 1, ty)) {
          r.ctx.drawImage(r.sp.bush, tx * S - cam, ty * S - 10);
          break;
        }
      }
    }
  }

  function drawTiles(r, g, cam) {
    const ctx = r.ctx;
    const tl = r.sp.tile;
    const [x0, x1] = tileVisibleRange(cam);
    for (let ty = 0; ty < g.world.h; ty++) {
      for (let tx = x0; tx <= x1 && tx < g.world.w; tx++) {
        const t = g.world.tiles[ty * g.world.w + tx];
        if (t === T.EMPTY) continue;
        const x = tx * S - cam, y = ty * S;
        if (t === T.GROUND) {
          const covered = isGround(g, tx, ty - 1) || KB.Physics.tileAt(g.world, tx, ty - 1) === T.BRICK;
          ctx.drawImage(covered ? tl.ground : tl.groundTop, x, y);
          ctx.fillStyle = PAL.brownDark;
          if (!isGround(g, tx - 1, ty) && tx > 0) ctx.fillRect(x, y + (covered ? 0 : 3), 1, S - (covered ? 0 : 3));
          if (!isGround(g, tx + 1, ty) && tx < g.world.w - 1) ctx.fillRect(x + S - 1, y + (covered ? 0 : 3), 1, S - (covered ? 0 : 3));
        } else if (t === T.BRICK) ctx.drawImage(tl.brick, x, y);
        else if (t === T.STAR_BLOCK) ctx.drawImage(tl.starBlock, x, y);
        else if (t === T.CLOUD) ctx.drawImage(tl.cloud, x, y);
      }
    }
  }

  function drawDecor(r, g, cam) {
    const ctx = r.ctx;
    const [x0, x1] = tileVisibleRange(cam);
    // flowers on open grass
    for (let tx = x0; tx <= x1; tx++) {
      const h = hash(tx, 11);
      if (h > 0.3) continue;
      for (let ty = 1; ty < g.world.h; ty++) {
        if (isGround(g, tx, ty) && KB.Physics.tileAt(g.world, tx, ty - 1) === T.EMPTY) {
          const fl = r.sp.flowers[Math.floor(hash(tx, 12) * r.sp.flowers.length)];
          ctx.drawImage(fl, tx * S - cam + Math.floor(h * 30) % 11, ty * S - 6);
          break;
        }
      }
    }
    for (const s of g.level.signs) drawSign(r, s, cam);
    g.level.checkpoints.forEach((cp, i) => {
      ctx.drawImage(r.sp.flag[g.checkpointIndex >= i ? 1 : 0], cp.tx * S + 2 - cam, cp.ty * S + S - 30);
    });
  }

  function drawSign(r, s, cam) {
    const ctx = r.ctx;
    const lines = s.text.split('|');
    const w = Math.max(...lines.map(l => KB.Font.width(l))) + 8;
    const h = lines.length * KB.Font.CH + 5;
    const cx = s.tx * S + S / 2 - cam;
    const bottom = s.ty * S + S;
    if (cx + w / 2 < 0 || cx - w / 2 > C.VIEW_W) return;
    ctx.fillStyle = PAL.brownDark; ctx.fillRect(cx - 1, bottom - 14, 3, 14);
    const x = Math.round(cx - w / 2), y = bottom - 14 - h;
    ctx.fillStyle = PAL.brownDark; ctx.fillRect(x - 1, y - 1, w + 2, h + 2);
    ctx.fillStyle = PAL.peach; ctx.fillRect(x, y, w, h);
    ctx.fillStyle = PAL.brownLight; ctx.fillRect(x, y + h - 1, w, 1);
    lines.forEach((l, i) => KB.Font.draw(ctx, l, cx, y + 3 + i * KB.Font.CH, PAL.ink, 1, 'center'));
  }

  function bob(frame, speed, amp) { return Math.round(Math.sin(frame * speed) * amp); }

  function winStarPos(g) {
    const t = g.mode === 'won' ? g.endTimer : 0;
    const lift = Math.max(0, t - 20);
    return { x: g.goal.x - 4 + lift * 2.6, y: g.goal.y - 6 - lift * 1.4 - Math.min(t, 20) * 0.4 };
  }

  function drawGoal(r, g, cam) {
    if (!g.goal) return;
    const ctx = r.ctx;
    const p = winStarPos(g);
    const y = p.y + (g.mode === 'won' ? 0 : bob(r.frame, 0.08, 2));
    const x = Math.round(p.x - cam);
    if (g.mode === 'won') {
      const colors = [PAL.red, PAL.orange, PAL.yellow, PAL.green, PAL.skyDeep, PAL.purple];
      const t = Math.max(0, g.endTimer - 20);
      for (let i = 0; i < Math.min(t, 90); i++) {
        colors.forEach((c, k) => {
          ctx.fillStyle = c;
          ctx.fillRect(x + 14 - i * 2.6, Math.round(y + 10 + k + i * 1.4), 3, 1);
        });
      }
    }
    ctx.drawImage(r.sp.warpStar[(r.frame >> 3) % 2], x, Math.round(y));
    if (g.mode === 'won') ctx.drawImage(r.sp.kirby.jump.r, x + 2, Math.round(y) - 14);
    // sparkle
    const sp = (r.frame >> 2) % 8;
    ctx.fillStyle = PAL.white;
    if (sp < 4) { ctx.fillRect(x + 24, y + 2 + sp, 1, 3); ctx.fillRect(x + 23, y + 3 + sp, 3, 1); }
  }

  function drawPickups(r, g, cam) {
    for (const k of g.pickups) {
      const x = Math.round(k.x - cam), y = Math.round(k.y + (k.pulled ? 0 : bob(r.frame + k.id * 9, 0.1, 1.5)));
      if (x < -16 || x > C.VIEW_W) continue;
      if (k.kind === 'tomato') r.ctx.drawImage(r.sp.tomato, x - 1, y - 2);
      else r.ctx.drawImage(r.sp.pickup[((r.frame + k.id * 5) >> 4) % 2], x - 1, y - 1);
    }
  }

  function drawEnemies(r, g, cam) {
    const ctx = r.ctx;
    for (const e of g.enemies) {
      let x = Math.round(e.x + e.w / 2 - 8 - cam), y = Math.round(e.y + e.h - 16);
      if (x < -24 || x > C.VIEW_W + 8) continue;
      if (e.pulled) x += (r.frame % 2) * 2 - 1;  // shiver while being sucked in
      const face = e.dir < 0 ? 'l' : 'r';
      if (e.kind === 'walker') ctx.drawImage(r.sp.walker[(e.t >> 4) % 2][face], x, y);
      else if (e.kind === 'flyer') ctx.drawImage(r.sp.flyer[(e.t >> 3) % 2][face], x, y);
      else if (e.kind === 'hopper') ctx.drawImage(r.sp.hopper[e.onGround ? 0 : 1][e.vx < 0 || (e.vx === 0 && e.dir < 0) ? 'l' : 'r'], x, y);
      else if (e.kind === 'gordo') ctx.drawImage(r.sp.gordo[(r.frame >> 4) % 2].r, Math.round(e.x + e.w / 2 - 8 - cam), Math.round(e.y + e.h / 2 - 8));
      else if (e.kind === 'block') ctx.drawImage(r.sp.tile.starBlock, Math.round(e.x - cam), Math.round(e.y));
    }
  }

  function drawProjectiles(r, g, cam) {
    for (const p of g.projectiles) {
      const cx = Math.round(p.x + p.w / 2 - cam), cy = Math.round(p.y + p.h / 2);
      if (p.kind === 'star') {
        const frames = r.sp.star;
        const f = p.vx > 0 ? (r.frame >> 1) % 4 : 3 - (r.frame >> 1) % 4;
        r.ctx.fillStyle = PAL.yellowLight;
        for (let i = 1; i <= 3; i++) r.ctx.fillRect(cx - Math.sign(p.vx) * (6 + i * 5), cy - 1 + (i % 2), 3 - (i >> 1), 1);
        r.ctx.drawImage(frames[f], cx - 8, cy - 8);
      } else {
        r.ctx.drawImage(r.sp.puff[p.life > C.PUFF_LIFE_TICKS / 2 ? 0 : 1], cx - 6, cy - 6);
      }
    }
  }

  function kirbyFrame(r, g) {
    const p = g.player, K = r.sp.kirby;
    if (g.mode === 'dying') return K.hurt;
    if (p.mode === 'inhale') return K.inhale[(p.anim >> 2) % 2];
    if (p.mode === 'fly') return K.fly[p.vy < -40 ? (p.anim >> 2) % 2 : (p.anim >> 4) % 2];
    if (p.mode === 'full') return K.full[p.onGround && Math.abs(p.vx) > 10 ? (p.anim >> 3) % 4 : 1];
    if (p.spitTimer > 0) return K.spit;
    if (p.invuln > C.INVULN_TICKS - 20) return K.hurt;
    if (!p.onGround) return p.vy < 0 ? K.jump : K.fall;
    if (p.landTimer > 0) return K.land;
    if (Math.abs(p.vx) > 10) return K.run[(p.anim >> 2) % 4];
    if (p.anim % 200 < 7) return K.blink;
    return K.idle[(p.anim >> 5) % 2];
  }

  function drawPlayer(r, g, cam) {
    const p = g.player;
    if (g.mode !== 'dying' && p.invuln > 0 && (p.invuln >> 2) % 2) return;
    const fr = kirbyFrame(r, g);
    const x = Math.round(p.x + p.w / 2 - 12 - cam), y = Math.round(p.y + p.h - 24);
    r.ctx.drawImage(p.facing < 0 ? fr.l : fr.r, x, y);
  }

  function drawInhaleWind(r, g, cam) {
    const ctx = r.ctx, p = g.player;
    const m = KB.Inhale.mouth(p);
    ctx.fillStyle = PAL.white;
    for (let i = 0; i < 9; i++) {
      const d = C.INHALE_RANGE - ((r.frame * 3 + i * 29) % C.INHALE_RANGE);
      const half = C.INHALE_HALF_HEIGHT + d * C.INHALE_SPREAD;
      const off = ((i * 53) % 100) / 100 * 2 - 1;
      const x = Math.round(m.x + p.facing * d - cam), y = Math.round(m.y + off * half * 0.9);
      const len = 2 + Math.round(d / 16);
      ctx.fillRect(p.facing > 0 ? x : x - len, y, len, 1);
    }
  }

  function drawParticles(r, cam) {
    const ctx = r.ctx;
    for (const p of r.particles) {
      const s = p.puff ? Math.max(1, Math.round(p.size * p.life / p.max) + 1) : p.size;
      ctx.fillStyle = p.color;
      ctx.fillRect(Math.round(p.x - cam - s / 2), Math.round(p.y - s / 2), s, s);
    }
    for (const t of r.texts) {
      KB.Font.drawShadowed(ctx, t.text, Math.round(t.x - cam), Math.round(t.y - 8), t.life % 8 < 4 ? PAL.yellow : PAL.white, 1, 'center');
    }
  }

  return { create, winStarPos };
})();

// HUD (lives, health, score, controls) and the title / pause / game over / win screens.
var KB = (typeof KB !== 'undefined') ? KB : {};

KB.Hud = (function () {
  const C = KB.C;
  const PAL = KB.PAL;
  const F = () => KB.Font;
  const W = C.VIEW_W, H = C.VIEW_H;

  function pad(n, len) { return String(n).padStart(len, '0'); }

  function topBar(r, g) {
    const ctx = r.ctx;
    ctx.fillStyle = 'rgba(27,16,48,0.55)';
    ctx.fillRect(0, 0, W, 13);
    ctx.drawImage(r.sp.lifeIcon, 4, 2);
    F().drawShadowed(ctx, '*' + g.lives, 16, 4, PAL.white);
    for (let i = 0; i < C.MAX_HP; i++) ctx.drawImage(r.sp.pip[i < g.player.hp ? 1 : 0], 34 + i * 9, 3);
    F().drawShadowed(ctx, 'SCORE ' + pad(g.score, 6), W - 4, 4, PAL.white, 1, 'right');
    F().drawShadowed(ctx, 'HI ' + pad(Math.max(r.hiScore, g.score), 6), W - 96, 4, PAL.yellowLight, 1, 'right');

    const p = g.player;
    let label = '';
    if (p.mode === 'fly') label = 'FLY';
    else if (p.mode === 'full') label = 'ENTER: SPIT!';
    else if (p.mode === 'inhale') label = 'INHALE!';
    if (label) F().drawShadowed(ctx, label, 66, 4, PAL.pinkLight);
    if (p.mode === 'fly') {
      for (let i = 0; i < C.FLY_MAX_FLAPS; i++) {
        ctx.fillStyle = PAL.ink; ctx.fillRect(81 + i * 5, 3, 4, 7);
        ctx.fillStyle = i < C.FLY_MAX_FLAPS - p.flaps ? PAL.skyLight : PAL.stoneDark;
        ctx.fillRect(82 + i * 5, 4, 2, 5);
      }
    }
    if (r.muted) F().drawShadowed(ctx, 'MUTED', 4, 16, PAL.stoneLight);
  }

  // The controls strip along the bottom, shown the whole time.
  function controls(r) {
    const ctx = r.ctx;
    ctx.fillStyle = 'rgba(27,16,48,0.7)';
    ctx.fillRect(0, H - 10, W, 10);
    const parts = [
      ['ARROWS/A D', PAL.yellow], [' MOVE  ', PAL.white],
      ['SPACE', PAL.yellow], [' JUMP+FLY  ', PAL.white],
      ['ENTER', PAL.yellow], [' INHALE/SPIT  ', PAL.white],
      ['P', PAL.stoneLight], [' PAUSE ', PAL.stoneLight], ['M', PAL.stoneLight], [' MUTE ', PAL.stoneLight],
      ['R', PAL.stoneLight], [' RESTART', PAL.stoneLight],
    ];
    const total = parts.reduce((n, [t]) => n + t.length, 0) * F().CW;
    let x = Math.round((W - total) / 2);
    for (const [t, col] of parts) { F().draw(ctx, t, x, H - 7, col); x += t.length * F().CW; }
  }

  function dim(ctx, alpha) {
    ctx.fillStyle = 'rgba(27,16,48,' + alpha + ')';
    ctx.fillRect(0, 0, W, H);
  }

  function panel(ctx, x, y, w, h) {
    ctx.fillStyle = PAL.ink; ctx.fillRect(x - 2, y - 2, w + 4, h + 4);
    ctx.fillStyle = PAL.pinkLight; ctx.fillRect(x - 1, y - 1, w + 2, h + 2);
    ctx.fillStyle = '#2a1c4a'; ctx.fillRect(x, y, w, h);
  }

  function blink(r) { return (r.frame >> 5) % 2 === 0; }

  function title(r, g) {
    const ctx = r.ctx;
    dim(ctx, 0.35);
    const by = Math.round(Math.sin(r.frame * 0.06) * 2);
    F().drawOutlined(ctx, 'KIRBY', W / 2, 20 + by, PAL.pink, 5, 'center', PAL.pinkLight);
    F().drawOutlined(ctx, 'DREAM DASH', W / 2, 52 + by, PAL.yellow, 2, 'center', PAL.yellowLight);
    const k = r.sp.kirby;
    const fr = (r.frame >> 5) % 3 === 2 ? k.fly[(r.frame >> 3) % 2] : k.idle[(r.frame >> 5) % 2];
    ctx.drawImage(fr.r, 0, 0, 24, 24, W / 2 - 24, 66, 48, 48);
    panel(ctx, 54, 118, W - 108, 46);
    const rows = [
      ['ARROWS / A D', 'RUN'], ['SPACE', 'JUMP  (TAP IN AIR TO FLY)'],
      ['HOLD ENTER', 'INHALE'], ['ENTER (FULL)', 'SPIT A STAR'], ['P / M / R', 'PAUSE / MUTE / RESTART'],
    ];
    rows.forEach(([key, what], i) => {
      F().draw(ctx, key, 108, 122 + i * 8, PAL.yellow, 1, 'right');
      F().draw(ctx, what, 114, 122 + i * 8, PAL.white);
    });
    if (blink(r)) F().drawShadowed(ctx, 'PRESS ENTER OR SPACE TO START', W / 2, 170, PAL.white, 1, 'center');
  }

  function endScreen(r, g, heading, color, lines, ready) {
    const ctx = r.ctx;
    dim(ctx, 0.55);
    F().drawOutlined(ctx, heading, W / 2, 40, color, 4, 'center', PAL.white);
    panel(ctx, 70, 78, W - 140, 46);
    lines.forEach(([label, value], i) => {
      F().draw(ctx, label, 80, 85 + i * 9, PAL.stoneLight);
      F().draw(ctx, value, W - 80, 85 + i * 9, PAL.white, 1, 'right');
    });
    if (ready && blink(r)) F().drawShadowed(ctx, 'PRESS ENTER OR SPACE TO PLAY AGAIN', W / 2, 140, PAL.white, 1, 'center');
  }

  function draw(r, g) {
    const ctx = r.ctx;
    if (g.mode !== 'title') topBar(r, g);
    controls(r);
    if (g.mode === 'title') title(r, g);
    else if (g.mode === 'paused') {
      dim(ctx, 0.45);
      F().drawOutlined(ctx, 'PAUSED', W / 2, 70, PAL.white, 4, 'center');
      F().drawShadowed(ctx, 'PRESS P TO RESUME', W / 2, 100, PAL.yellow, 1, 'center');
    } else if (g.mode === 'gameover') {
      endScreen(r, g, 'GAME OVER', PAL.red, [
        ['SCORE', pad(g.score, 6)], ['BEST', pad(Math.max(r.hiScore, g.score), 6)],
        ['', ''], ['TRY AGAIN, KIRBY!', ''],
      ], g.endTimer > C.END_INPUT_DELAY_TICKS);
    } else if (g.mode === 'won' && g.endTimer > C.WIN_SCREEN_TICKS) {
      endScreen(r, g, 'YOU WIN!', PAL.yellow, [
        ['SCORE', pad(g.score, 6)], ['BEST', pad(Math.max(r.hiScore, g.score), 6)],
        ['LIVES LEFT', String(g.lives)], ['DREAM LAND IS SAVED!', ''],
      ], true);
    }
  }

  return { draw };
})();

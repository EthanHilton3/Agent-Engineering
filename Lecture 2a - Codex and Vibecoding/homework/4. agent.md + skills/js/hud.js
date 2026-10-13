// Pixel font, HUD, controls bar and the full-screen overlays (title, pause, game over, win).
var Font = (function () {
  'use strict';
  var G = {
    'A': '.#./#.#/###/#.#/#.#', 'B': '##./#.#/##./#.#/##.', 'C': '.##/#../#../#../.##', 'D': '##./#.#/#.#/#.#/##.',
    'E': '###/#../##./#../###', 'F': '###/#../##./#../#..', 'G': '.##/#../#.#/#.#/.##', 'H': '#.#/#.#/###/#.#/#.#',
    'I': '###/.#./.#./.#./###', 'J': '..#/..#/..#/#.#/.#.', 'K': '#.#/#.#/##./#.#/#.#', 'L': '#../#../#../#../###',
    'M': '#.#/###/###/#.#/#.#', 'N': '##./#.#/#.#/#.#/#.#', 'O': '.#./#.#/#.#/#.#/.#.', 'P': '##./#.#/##./#../#..',
    'Q': '.#./#.#/#.#/##./.##', 'R': '##./#.#/##./#.#/#.#', 'S': '.##/#../.#./..#/##.', 'T': '###/.#./.#./.#./.#.',
    'U': '#.#/#.#/#.#/#.#/###', 'V': '#.#/#.#/#.#/#.#/.#.', 'W': '#.#/#.#/###/###/#.#', 'X': '#.#/#.#/.#./#.#/#.#',
    'Y': '#.#/#.#/.#./.#./.#.', 'Z': '###/..#/.#./#../###',
    '0': '###/#.#/#.#/#.#/###', '1': '.#./##./.#./.#./###', '2': '##./..#/.#./#../###', '3': '##./..#/.#./..#/##.',
    '4': '#.#/#.#/###/..#/..#', '5': '###/#../##./..#/##.', '6': '.##/#../###/#.#/###', '7': '###/..#/.#./.#./.#.',
    '8': '###/#.#/###/#.#/###', '9': '###/#.#/###/..#/##.',
    '.': './././././#', ',': '../../../.#/#.', '!': '#/#/#/./#', '?': '##./..#/.#./.../.#.', ':': './#/./#/.',
    '-': '.../.../###/.../...', '+': '.../.#./###/.#./...', '/': '..#/..#/.#./#../#..', "'": '#/#/././.',
    '(': '.#/#./#./#./.#', ')': '#./.#/.#/.#/#.', '<': '..#/.#./#../.#./..#', '>': '#../.#./..#/.#./#..',
    '=': '.../###/.../###/...', '*': '.../#.#/.#./#.#/...', '%': '#.#/..#/.#./#../#.#', '"': '#.#/#.#/.../.../...',
    '←': '..#../.#.../#####/.#.../..#..', '→': '..#../...#./#####/...#./..#..',
    '♥': '.#.#./#####/#####/.###./..#..',
    ' ': '../../../../..'
  };
  var glyphs = {};
  for (var ch in G) glyphs[ch] = G[ch].split('/');
  var cache = {};

  function glyph(ch, color) {
    var key = ch + color;
    if (cache[key]) return cache[key];
    var rows = glyphs[ch] || glyphs['?'];
    var cv = document.createElement('canvas');
    cv.width = rows[0].length; cv.height = 5;
    var g = cv.getContext('2d');
    g.fillStyle = Sprites.PAL[color] || color;
    rows.forEach(function (r, y) { for (var x = 0; x < r.length; x++) if (r[x] === '#') g.fillRect(x, y, 1, 1); });
    cache[key] = cv;
    return cv;
  }

  function measure(text, scale) {
    var w = 0;
    for (var i = 0; i < text.length; i++) w += ((glyphs[text[i]] || glyphs['?'])[0].length + 1) * (scale || 1);
    return Math.max(0, w - (scale || 1));
  }

  // align: 'left' | 'center' | 'right'. shadow: optional colour drawn 1px down-right.
  function draw(ctx, text, x, y, color, opts) {
    opts = opts || {};
    var s = opts.scale || 1;
    text = String(text).toUpperCase();
    var w = measure(text, s);
    var x0 = Math.round(opts.align === 'center' ? x - w / 2 : opts.align === 'right' ? x - w : x);
    y = Math.round(y);
    if (opts.shadow) draw(ctx, text, x0 + s, y + s, opts.shadow, { scale: s });
    for (var i = 0; i < text.length; i++) {
      var g = glyph(text[i], color);
      ctx.drawImage(g, x0, y, g.width * s, g.height * s);
      x0 += (g.width + 1) * s;
    }
    return w;
  }

  // Draws [text, colour] runs one after another.
  function runs(ctx, parts, x, y, align) {
    var total = parts.reduce(function (s, p) { return s + measure(p[0].toUpperCase()) + 1; }, -1);
    var cx = align === 'center' ? Math.round(x - total / 2) : x;
    parts.forEach(function (p) { cx += draw(ctx, p[0], cx, y, p[1]) + 1; });
  }

  return { draw: draw, measure: measure, runs: runs };
})();

var Hud = (function () {
  'use strict';
  var C = CONST, PAL = Sprites.PAL, VW = C.VIEW_W, VH = C.VIEW_H;

  function pad(n, len) {
    var s = String(Math.max(0, Math.floor(n)));
    while (s.length < len) s = '0' + s;
    return s;
  }

  function clock(ticks) {
    var sec = Math.floor(ticks / C.TICKS_PER_SECOND);
    return Math.floor(sec / 60) + ':' + pad(sec % 60, 2);
  }

  function panel(ctx, x, y, w, h, alpha) {
    ctx.globalAlpha = alpha === undefined ? 0.8 : alpha;
    ctx.fillStyle = PAL.K;
    ctx.fillRect(x, y, w, h);
    ctx.globalAlpha = 1;
  }

  function topBar(ctx, state, opts) {
    var p = state.player;
    panel(ctx, 0, 0, VW, 11, 0.6);
    for (var i = 0; i < C.MAX_HEALTH; i++) {
      var x = 3 + i * 7, full = i < p.health;
      ctx.fillStyle = PAL.K; ctx.fillRect(x, 2, 6, 7);
      ctx.fillStyle = full ? PAL.p : PAL.N; ctx.fillRect(x + 1, 3, 4, 5);
      if (full) { ctx.fillStyle = PAL.l; ctx.fillRect(x + 1, 3, 2, 1); }
    }
    ctx.drawImage(Sprites.get('icon_life').r, 50, 1);
    Font.draw(ctx, '*' + state.lives, 61, 3, 'w');
    if (p.mouth) Font.runs(ctx, [['MOUTH FULL', 'y']], 78, 3);
    Font.runs(ctx, [['SCORE ', 'S'], [pad(state.score, 6), 'w']], 162, 3);
    if (opts.muted) Font.draw(ctx, 'MUTED', 252, 13, 'n', { align: 'right' });
    var b = state.boss;
    if (b && b.state !== 'dormant' && b.state !== 'dead') {
      panel(ctx, 128, 11, 128, 9, 0.6);
      Font.draw(ctx, 'GNARLWOOD', 132, 13, 'g');
      for (var k = 0; k < C.BOSS_HP; k++) {
        ctx.fillStyle = PAL.K; ctx.fillRect(172 + k * 13, 13, 12, 5);
        ctx.fillStyle = k < b.hp ? PAL.r : PAL.N; ctx.fillRect(173 + k * 13, 14, 10, 3);
      }
    }
  }

  function controlsBar(ctx) {
    panel(ctx, 0, VH - 9, VW, 9, 0.6);
    Font.runs(ctx, [
      ['←→/AD', 'y'], [' MOVE  ', 'w'], ['SPACE', 'y'], [' JUMP/FLY  ', 'w'],
      ['ENTER', 'y'], [' INHALE/SPIT  ', 'w'], ['P', 'y'], [' PAUSE  ', 'w'], ['M', 'y'], [' MUTE', 'w']
    ], VW / 2, VH - 7, 'center');
  }

  function banner(ctx, text, timer) {
    var a = Math.min(1, timer / 20, (C.BANNER_TICKS - timer) / 15);
    if (a <= 0) return;
    ctx.globalAlpha = a;
    var w = Font.measure(text, 2) + 16;
    panel(ctx, VW / 2 - w / 2, 34, w, 18, 0.75);
    ctx.globalAlpha = a;
    Font.draw(ctx, text, VW / 2, 38, 'y', { scale: 2, align: 'center', shadow: 'K' });
    ctx.globalAlpha = 1;
  }

  function dim(ctx, alpha) {
    panel(ctx, 0, 0, VW, VH, alpha);
  }

  function blink(state) {
    return Math.floor(state.frame / 30) % 2 === 0;
  }

  function title(ctx, state) {
    dim(ctx, 0.45);
    [[-1, 0], [1, 0], [0, -1], [0, 1], [2, 2]].forEach(function (o) {
      Font.draw(ctx, 'KIRBY', VW / 2 + o[0], 22 + o[1], 'K', { scale: 5, align: 'center' });
    });
    Font.draw(ctx, 'KIRBY', VW / 2, 22, 'p', { scale: 5, align: 'center' });
    Font.draw(ctx, 'DREAM MEADOWS', VW / 2, 52, 'y', { scale: 2, align: 'center', shadow: 'K' });
    var frame = Math.floor(state.frame / 32) % 2 ? 'kirby_idle1' : 'kirby_idle0';
    if (state.frame % 200 < 8) frame = 'kirby_blink';
    ctx.drawImage(Sprites.get(frame).r, VW / 2 - 24, 66, 48, 48);
    panel(ctx, 20, 118, VW - 40, 64, 0.75);
    var rows = [
      [['← →  OR  A D', 'y'], [' MOVE', 'w']],
      [['SPACE', 'y'], [' JUMP - TAP AGAIN IN THE AIR TO FLY', 'w']],
      [['ENTER', 'y'], [' HOLD TO INHALE, PRESS TO SPIT', 'w']],
      [['P/ESC', 'y'], [' PAUSE  ', 'w'], ['M', 'y'], [' MUTE  ', 'w'], ['R', 'y'], [' RESTART', 'w']]
    ];
    rows.forEach(function (r, i) { Font.runs(ctx, r, VW / 2, 124 + i * 9, 'center'); });
    Font.draw(ctx, 'MOUTH FULL? YOU CAN\'T FLY - SPIT FIRST!', VW / 2, 166, 'S', { align: 'center' });
    if (blink(state)) Font.draw(ctx, 'PRESS SPACE TO START', VW / 2, 190, 'w', { scale: 1, align: 'center', shadow: 'K' });
    if (state.best) Font.draw(ctx, 'BEST ' + pad(state.best, 6), VW / 2, 202, 'y', { align: 'center', shadow: 'K' });
  }

  function centerBox(ctx, lines, y) {
    var h = lines.length * 10 + 8;
    panel(ctx, 24, y, VW - 48, h, 0.8);
    lines.forEach(function (l, i) {
      Font.draw(ctx, l[0], VW / 2, y + 6 + i * 10, l[1] || 'w', { align: 'center' });
    });
  }

  function overlays(ctx, state) {
    var m = state.mode;
    if (m === 'title') title(ctx, state);
    else if (m === 'paused') {
      dim(ctx, 0.5);
      Font.draw(ctx, 'PAUSED', VW / 2, 70, 'w', { scale: 3, align: 'center', shadow: 'K' });
      centerBox(ctx, [['P / ESC: RESUME'], ['R: RESTART'], ['M: MUTE']], 100);
    } else if (m === 'confirm') {
      dim(ctx, 0.6);
      centerBox(ctx, [['RESTART FROM THE BEGINNING?', 'y'], [''], ['R: YES      P / ESC: NO']], 90);
    } else if (m === 'gameover') {
      dim(ctx, 0.7);
      Font.draw(ctx, 'GAME OVER', VW / 2, 56, 'r', { scale: 3, align: 'center', shadow: 'K' });
      Font.draw(ctx, 'SCORE ' + pad(state.score, 6), VW / 2, 84, 'w', { align: 'center' });
      if (state.screenTimer === 0) {
        centerBox(ctx, [['SPACE: CONTINUE FROM CHECKPOINT', 'y'], ['(SCORE RESETS TO 0)', 'n'], [''],
          ['R: RESTART FROM THE BEGINNING']], 104);
      }
    } else if (m === 'win') {
      dim(ctx, 0.55);
      Font.draw(ctx, 'YOU WIN!', VW / 2, 40, 'y', { scale: 3, align: 'center', shadow: 'K' });
      var lines = [
        ['TIME        ' + clock(state.time)], ['TIME BONUS  ' + pad(state.winBonus, 6)],
        ['SCORE       ' + pad(state.score, 6), 'y'], ['BEST        ' + pad(state.best, 6), 'p']
      ];
      if (state.continues) lines.push(['CONTINUES   ' + state.continues, 'n']);
      centerBox(ctx, lines, 72);
      if (state.screenTimer === 0 && blink(state)) {
        Font.draw(ctx, 'PRESS SPACE TO PLAY AGAIN', VW / 2, 150, 'w', { align: 'center', shadow: 'K' });
      }
    }
  }

  function draw(ctx, state, opts) {
    if (state.mode !== 'title') topBar(ctx, state, opts);
    controlsBar(ctx);
    if (opts.banner) banner(ctx, opts.banner.text, opts.banner.timer);
    overlays(ctx, state);
  }

  return { draw: draw, pad: pad, clock: clock };
})();

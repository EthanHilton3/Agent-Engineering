// Pixel-art sprites drawn in code: a limited palette, a tiny pixel buffer, and Kirby's frames.
// Every sprite is rasterised once at start-up into an offscreen canvas (plus a mirrored copy).
var Sprites = (function () {
  'use strict';

  // The whole game uses only these colours.
  var PAL = {
    K: '#1d1130', // outline / ink
    p: '#f7a3c6', // Kirby pink
    l: '#ffd6e9', // light pink
    d: '#d65c95', // dark pink
    r: '#e3294f', // red
    w: '#fff7ec', // white
    y: '#ffd83d', // yellow
    o: '#f28330', // orange
    t: '#f4c891', // tan
    b: '#9c5b33', // brown
    B: '#5a321e', // dark brown
    g: '#5cc452', // green
    G: '#2c7a40', // dark green
    s: '#86ccff', // sky
    S: '#cdeeff', // pale sky
    v: '#6d43a6', // purple
    n: '#8a87a8', // stone
    N: '#46435f'  // dark stone
  };

  function Pix(w, h) {
    this.w = w;
    this.h = h;
    this.d = new Array(w * h).fill(null);
  }
  Pix.prototype.set = function (x, y, c) {
    x = Math.floor(x); y = Math.floor(y);
    if (x >= 0 && y >= 0 && x < this.w && y < this.h) this.d[y * this.w + x] = c;
  };
  Pix.prototype.get = function (x, y) {
    if (x < 0 || y < 0 || x >= this.w || y >= this.h) return null;
    return this.d[y * this.w + x];
  };
  Pix.prototype.rect = function (x, y, w, h, c) {
    for (var j = 0; j < h; j++) for (var i = 0; i < w; i++) this.set(x + i, y + j, c);
  };
  // Filled ellipse with optional lower-right shade and upper-left highlight.
  Pix.prototype.ellipse = function (cx, cy, rx, ry, c, shade, light) {
    for (var y = Math.floor(cy - ry); y <= Math.ceil(cy + ry); y++) {
      for (var x = Math.floor(cx - rx); x <= Math.ceil(cx + rx); x++) {
        var nx = (x + 0.5 - cx) / rx, ny = (y + 0.5 - cy) / ry, d = nx * nx + ny * ny;
        if (d > 1) continue;
        var col = c;
        if (shade && nx * 0.45 + ny * 0.9 > 0.6) col = shade;
        if (light && nx * 0.6 + ny * 0.8 < -0.5 && d < 0.7 && d > 0.25) col = light;
        this.set(x, y, col);
      }
    }
  };
  // Filled polygon (even-odd rule), sampled at pixel centres.
  Pix.prototype.poly = function (pts, c) {
    for (var y = 0; y < this.h; y++) {
      for (var x = 0; x < this.w; x++) {
        var px = x + 0.5, py = y + 0.5, inside = false;
        for (var i = 0, j = pts.length - 1; i < pts.length; j = i++) {
          var xi = pts[i][0], yi = pts[i][1], xj = pts[j][0], yj = pts[j][1];
          if ((yi > py) !== (yj > py) && px < (xj - xi) * (py - yi) / (yj - yi) + xi) inside = !inside;
        }
        if (inside) this.set(x, y, c);
      }
    }
  };
  // Draws pixel rows like ['.KK.', 'KyyK'] at (x, y); '.' is transparent.
  Pix.prototype.rows = function (x, y, rows) {
    for (var j = 0; j < rows.length; j++) {
      for (var i = 0; i < rows[j].length; i++) if (rows[j][i] !== '.') this.set(x + i, y + j, rows[j][i]);
    }
  };
  // Adds a 1px outline around everything drawn so far.
  Pix.prototype.outline = function (c) {
    var src = this.d.slice(), w = this.w;
    for (var y = 0; y < this.h; y++) {
      for (var x = 0; x < w; x++) {
        if (src[y * w + x] !== null) continue;
        var n = (x > 0 && src[y * w + x - 1]) || (x < w - 1 && src[y * w + x + 1]) ||
          (y > 0 && src[(y - 1) * w + x]) || (y < this.h - 1 && src[(y + 1) * w + x]);
        if (n) this.d[y * w + x] = c;
      }
    }
  };
  Pix.prototype.toCanvas = function (flip) {
    var cv = document.createElement('canvas');
    cv.width = this.w; cv.height = this.h;
    var ctx = cv.getContext('2d');
    for (var y = 0; y < this.h; y++) {
      for (var x = 0; x < this.w; x++) {
        var c = this.d[y * this.w + x];
        if (!c) continue;
        ctx.fillStyle = PAL[c] || c;
        ctx.fillRect(flip ? this.w - 1 - x : x, y, 1, 1);
      }
    }
    return cv;
  };

  // Five-pointed star outline points.
  function starPoints(cx, cy, outer, inner, rot) {
    var pts = [];
    for (var i = 0; i < 10; i++) {
      var a = rot - Math.PI / 2 + i * Math.PI / 5, r = i % 2 ? inner : outer;
      pts.push([cx + Math.cos(a) * r, cy + Math.sin(a) * r]);
    }
    return pts;
  }

  var cache = {};
  function add(name, pix) {
    cache[name] = { r: pix.toCanvas(false), l: pix.toCanvas(true), w: pix.w, h: pix.h };
  }
  function get(name) {
    var s = cache[name];
    if (!s) throw new Error('Missing sprite ' + name);
    return s;
  }
  function has(name) {
    return !!cache[name];
  }

  // ---- Kirby (24x24 frames, facing right, feet on the bottom row) ----
  var KS = 24;

  function face(P, cx, cy, rx, o) {
    var ex = Math.round(cx + 1 + (rx - 7) * 0.5), ey = Math.round(cy - 3 - (o.eyeUp || 0));
    var e2 = ex + 3;
    if (o.eyes === 'open') {
      [ex, e2].forEach(function (x) { P.set(x, ey, 'w'); P.set(x, ey + 1, 'K'); P.set(x, ey + 2, 'K'); P.set(x, ey + 3, 'K'); });
    } else if (o.eyes === 'closed') {
      [ex, e2].forEach(function (x) { P.set(x - 1, ey + 2, 'K'); P.set(x, ey + 3, 'K'); P.set(x + 1, ey + 2, 'K'); });
    } else if (o.eyes === 'squint') {
      P.rows(ex - 1, ey + 1, ['K..', '.K.', 'K..']);
      P.rows(e2 - 1, ey + 1, ['..K', '.K.', '..K']);
    } else if (o.eyes === 'x') {
      P.rows(ex - 1, ey, ['K.K', '.K.', 'K.K']);
      P.rows(e2 - 1, ey, ['K.K', '.K.', 'K.K']);
    }
    var by = ey + 4;
    if (o.blush !== false) {
      P.set(ex - 2, by, 'r'); P.set(ex - 3, by, 'r');
      P.set(e2 + 2, by, 'r');
    }
    var mx = ex + 1, my = by;
    if (o.mouth === 'smile') { P.set(mx, my, 'K'); P.set(mx + 1, my, 'K'); }
    else if (o.mouth === 'o') P.rows(mx, my - 1, ['KK', 'rr', 'KK']);
    else if (o.mouth === 'wail') P.rows(mx, my, ['KK', 'rK']);
    else if (o.mouth === 'full') P.rows(mx - 1, my, ['K.K', '.K.']);
    else if (o.mouth === 'puff') P.set(mx + 1, my, 'K');
  }

  function kirby(o) {
    var P = new Pix(KS, KS);
    var rx = o.rx || 7, ry = o.ry || 7, lift = o.lift || 0;
    var cx = 12 + (o.dx || 0), cy = 22.5 - lift - ry - (o.feetGap || 0);
    (o.feet || [[-4, 0], [3, 0]]).forEach(function (f) { P.ellipse(cx + f[0], 21.6 + f[1], o.footR || 3.2, 1.7, 'r'); });
    var arms = o.arms || [[-rx + 0.5, 1.5], [rx - 0.5, 1.5]];
    P.ellipse(cx + arms[0][0], cy + arms[0][1], 2.2, 1.8, 'p', 'd');
    P.ellipse(cx, cy, rx, ry, 'p', 'd', 'l');
    if (o.cheeks) P.ellipse(cx + rx - 2.5, cy + 1.5, 3, 2.6, 'p', 'd');
    P.ellipse(cx + arms[1][0], cy + arms[1][1], 2.2, 1.8, 'p', 'd');
    if (o.bigMouth) {
      var m = o.bigMouth;
      P.ellipse(cx + m[0], cy + m[1], m[2], m[3], 'K');
      P.ellipse(cx + m[0], cy + m[1] + m[3] * 0.5, m[2] * 0.6, m[3] * 0.4, 'r');
    }
    P.outline('K');
    face(P, cx, cy, rx, o);
    return P;
  }

  var KIRBY_FRAMES = {
    idle0: { eyes: 'open', mouth: 'smile' },
    idle1: { rx: 7.5, ry: 6.6, eyes: 'open', mouth: 'smile' },
    blink: { eyes: 'closed', mouth: 'smile' },
    run0: { lift: 1, feet: [[-6, 0], [4, -1]], arms: [[-7, 0], [6, 2]], eyes: 'open', mouth: 'smile' },
    run1: { feet: [[-3, 0], [2, 0]], eyes: 'open', mouth: 'smile' },
    run2: { lift: 1, feet: [[-5, -1], [5, 0]], arms: [[-6, 2], [7, 0]], eyes: 'open', mouth: 'smile' },
    run3: { feet: [[-2, 0], [1, 0]], eyes: 'open', mouth: 'smile' },
    jump: { rx: 6.5, ry: 7.4, feetGap: 1, feet: [[-3, 0], [2, 0]], arms: [[-6, -3], [6, -3]], eyes: 'open', mouth: 'o' },
    fall: { rx: 7.4, ry: 6.8, feetGap: 1, feet: [[-4, 0], [3, 0]], arms: [[-7, -4], [7, -4]], eyes: 'open', mouth: 'smile' },
    fly0: { rx: 9.4, ry: 9, feetGap: 1, footR: 2.6, feet: [[-4, 0], [3, 0]], arms: [[-9.5, -3], [9.5, -3]], eyes: 'open', mouth: 'puff', eyeUp: 1 },
    fly1: { rx: 9.4, ry: 8.6, feetGap: 1, footR: 2.6, feet: [[-4, 0], [3, 0]], arms: [[-9.5, 2.5], [9.5, 2.5]], eyes: 'open', mouth: 'puff', eyeUp: 1 },
    inhale0: { rx: 7.6, ry: 6.8, dx: -1, eyes: 'squint', blush: false, mouth: 'none', bigMouth: [4.5, 1.5, 2.6, 3.2], arms: [[-7, 1], [5, 3]] },
    inhale1: { rx: 7.8, ry: 6.6, dx: -1, eyes: 'squint', blush: false, mouth: 'none', bigMouth: [4.5, 1.5, 3, 3.8], arms: [[-7, 1], [5, 3]] },
    full0: { rx: 9, ry: 7.6, cheeks: true, eyes: 'open', mouth: 'full' },
    full1: { rx: 9.2, ry: 7.3, cheeks: true, lift: 1, feet: [[-5, 0], [4, -1]], eyes: 'open', mouth: 'full' },
    full2: { rx: 9.2, ry: 7.3, cheeks: true, lift: 1, feet: [[-3, -1], [5, 0]], eyes: 'open', mouth: 'full' },
    spit: { rx: 6.6, ry: 7.2, dx: -1, eyes: 'squint', mouth: 'o', arms: [[-6, 0], [6, -1]] },
    hurt: { rx: 7.6, ry: 6.6, eyes: 'x', mouth: 'wail', arms: [[-8, -3], [8, -3]], feet: [[-5, 0], [4, 0]] }
  };

  function buildKirby() {
    for (var name in KIRBY_FRAMES) add('kirby_' + name, kirby(KIRBY_FRAMES[name]));
    // Small head icon for the lives counter.
    var P = new Pix(10, 9);
    P.ellipse(5, 4.5, 4.5, 4, 'p', 'd', 'l');
    P.outline('K');
    P.set(5, 2, 'K'); P.set(5, 3, 'K'); P.set(7, 2, 'K'); P.set(7, 3, 'K'); P.set(3, 5, 'r'); P.set(8, 5, 'r');
    add('icon_life', P);
  }

  var builders = [buildKirby];
  function register(fn) { builders.push(fn); }
  function init() { builders.forEach(function (fn) { fn(); }); }

  return {
    PAL: PAL, Pix: Pix, starPoints: starPoints, add: add, get: get, has: has,
    register: register, init: init, KIRBY_SIZE: KS
  };
})();

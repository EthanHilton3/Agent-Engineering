// All sprites are drawn here, pixel by pixel, into small offscreen canvases. No image files.
var KB = (typeof KB !== 'undefined') ? KB : {};

KB.PAL = {
  ink: '#1b1030', white: '#fff8f0', shadow: '#1b103066',
  pink: '#f8a8cc', pinkLight: '#ffd8ec', pinkDark: '#d8689a', blush: '#ff6f9c',
  red: '#e0305a', redDark: '#9a1c44', mouth: '#6c1434', tongue: '#ff7096',
  eyeBlue: '#3c5cd8',
  orange: '#f07830', orangeDark: '#b04420', orangeLight: '#ffa860', peach: '#ffdcb0',
  yellow: '#ffd23c', yellowDark: '#e08a20', yellowLight: '#fff4a8',
  purple: '#c050c8', purpleDark: '#782c88', purpleLight: '#e890e8',
  green: '#58c048', greenDark: '#2c7c38', greenLight: '#a8e878',
  brown: '#a8643c', brownDark: '#6a3a28', brownLight: '#cc8c58',
  stone: '#8890c0', stoneDark: '#565c90', stoneLight: '#bcc4e8',
  sky: '#8cd4fc', skyLight: '#c8eeff', skyDeep: '#64b4f4',
  hill: '#7cd0b0', hillDark: '#5cae98', hillFar: '#a8dce8',
  navy: '#3c3c88', navyDark: '#242458',
};

KB.Sprites = (function () {
  const PAL = KB.PAL;

  // ---- a tiny pixel grid --------------------------------------------------
  function Grid(w, h) {
    this.w = w; this.h = h;
    this.c = new Array(w * h).fill(null);   // colours
    this.r = new Array(w * h).fill(null);   // region names, for outlining between parts
  }
  Grid.prototype.inside = function (x, y) { return x >= 0 && y >= 0 && x < this.w && y < this.h; };
  Grid.prototype.set = function (x, y, color, region) {
    x = Math.round(x); y = Math.round(y);
    if (!this.inside(x, y)) return;
    this.c[y * this.w + x] = color;
    this.r[y * this.w + x] = color === null ? null : (region || 'x');
  };
  Grid.prototype.region = function (x, y) { return this.inside(x, y) ? this.r[y * this.w + x] : null; };
  // Fill an ellipse; `paint(nx, ny)` picks the colour from the normalised position (-1..1).
  Grid.prototype.ellipse = function (cx, cy, rx, ry, paint, region) {
    for (let y = 0; y < this.h; y++) {
      for (let x = 0; x < this.w; x++) {
        const nx = (x + 0.5 - cx) / rx, ny = (y + 0.5 - cy) / ry;
        if (nx * nx + ny * ny <= 1) this.set(x, y, typeof paint === 'function' ? paint(nx, ny) : paint, region);
      }
    }
  };
  Grid.prototype.poly = function (pts, paint, region) {
    for (let y = 0; y < this.h; y++) {
      for (let x = 0; x < this.w; x++) {
        if (inPoly(x + 0.5, y + 0.5, pts)) this.set(x, y, typeof paint === 'function' ? paint(x, y) : paint, region);
      }
    }
  };
  Grid.prototype.rect = function (x, y, w, h, color, region) {
    for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) this.set(x + i, y + j, color, region);
  };
  // Draw string art: each character maps to a colour through `map` ('.' is skipped).
  Grid.prototype.art = function (rows, ox, oy, map, region) {
    rows.forEach((row, j) => {
      for (let i = 0; i < row.length; i++) if (map[row[i]]) this.set(ox + i, oy + j, map[row[i]], region);
    });
  };
  // Outline: edge pixels become `color`, and so do pixels of region a that touch region b.
  Grid.prototype.outline = function (color, pairs) {
    const marks = [];
    for (let y = 0; y < this.h; y++) {
      for (let x = 0; x < this.w; x++) {
        const reg = this.region(x, y);
        if (!reg) continue;
        const ns = [this.region(x + 1, y), this.region(x - 1, y), this.region(x, y + 1), this.region(x, y - 1)];
        const edge = ns.some(n => n === null) ||
          (pairs || []).some(([a, b]) => reg === a && ns.includes(b));
        if (edge) marks.push([x, y]);
      }
    }
    marks.forEach(([x, y]) => { this.c[y * this.w + x] = color; });
  };
  Grid.prototype.toCanvas = function (flip) {
    const cv = document.createElement('canvas');
    cv.width = this.w; cv.height = this.h;
    const ctx = cv.getContext('2d');
    for (let y = 0; y < this.h; y++) {
      for (let x = 0; x < this.w; x++) {
        const col = this.c[y * this.w + (flip ? this.w - 1 - x : x)];
        if (col) { ctx.fillStyle = col; ctx.fillRect(x, y, 1, 1); }
      }
    }
    return cv;
  };

  function inPoly(x, y, pts) {
    let inside = false;
    for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
      const [xi, yi] = pts[i], [xj, yj] = pts[j];
      if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) inside = !inside;
    }
    return inside;
  }
  function starPoints(cx, cy, outer, inner, rot) {
    const pts = [];
    for (let i = 0; i < 10; i++) {
      const a = rot - Math.PI / 2 + i * Math.PI / 5;
      const r = i % 2 ? inner : outer;
      pts.push([cx + Math.cos(a) * r, cy + Math.sin(a) * r]);
    }
    return pts;
  }

  // Light from the top left: pick light / mid / dark by position on a round body.
  function shade(light, mid, dark) {
    return (nx, ny) => {
      const l = -0.5 * nx - 0.8 * ny;
      return l > 0.55 ? light : (l < -0.62 ? dark : mid);
    };
  }

  // Both directions of one sprite.
  function pair(grid) { return { r: grid.toCanvas(false), l: grid.toCanvas(true) }; }

  // ---- Kirby (24x24, facing right, feet on the bottom row) ---------------
  function kirby(o) {
    const g = new Grid(24, 24);
    const b = o.body;
    (o.arms || []).forEach(a => g.ellipse(a[0], a[1], a[2], a[3], PAL.pink, 'body'));
    g.ellipse(b[0], b[1], b[2], b[3], shade(PAL.pinkLight, PAL.pink, PAL.pinkDark), 'body');
    (o.feet || []).forEach(f => g.ellipse(f[0], f[1], f[2], f[3], (nx, ny) => ny > 0.3 ? PAL.redDark : PAL.red, 'foot'));
    if (o.mouth === 'wide') {
      const m = o.mouthAt;
      g.ellipse(m[0], m[1], m[2], m[3], (nx, ny) => ny > 0.45 ? PAL.tongue : PAL.mouth, 'mouth');
    }
    g.outline(PAL.ink, [['foot', 'body'], ['body', 'mouth']]);
    face(g, o);
    return pair(g);
  }

  function face(g, o) {
    const [ex, ey] = o.eyes;   // left eye top-left; right eye sits 3px to its right
    const eyeXs = [ex, ex + 3];
    if (o.eyeStyle === 'closed') {
      eyeXs.forEach(x => g.rect(x, ey + 2, 2, 1, PAL.ink));
    } else if (o.eyeStyle === 'squint') {
      eyeXs.forEach(x => { g.set(x, ey + 1, PAL.ink); g.set(x + 1, ey + 2, PAL.ink); g.set(x, ey + 3, PAL.ink); });
    } else if (o.eyeStyle === 'x') {
      [ex - 1, ex + 3].forEach(x => { g.set(x, ey, PAL.ink); g.set(x + 2, ey, PAL.ink); g.set(x + 1, ey + 1, PAL.ink); g.set(x, ey + 2, PAL.ink); g.set(x + 2, ey + 2, PAL.ink); });
    } else {
      eyeXs.forEach(x => {
        g.set(x, ey - 1, PAL.ink); g.set(x + 1, ey - 1, PAL.ink);
        g.set(x, ey, PAL.white); g.set(x + 1, ey, PAL.ink);
        g.rect(x, ey + 1, 2, 1, PAL.ink);
        g.rect(x, ey + 2, 2, 1, PAL.eyeBlue);
      });
    }
    const by = ey + (o.blushDy || 3);
    const blushW = o.bigBlush ? 3 : 2;
    g.rect(ex - blushW - 0, by, blushW, 1, PAL.blush);
    g.rect(ex + 5, by, blushW, 1, PAL.blush);
    if (o.mouth === 'smile') g.set(ex + 2, by + 1, PAL.mouth);
    if (o.mouth === 'o') g.rect(ex + 2, by, 2, 2, PAL.mouth);
    if (o.mouth === 'puff') g.set(ex + 3, by + 1, PAL.mouth);
  }

  function buildKirby() {
    const K = {};
    const armsIdle = [[5, 16, 2.2, 2], [19, 16, 2.2, 2]];
    const feetIdle = [[9, 22, 3, 2], [16, 22, 3, 2]];
    const base = { body: [12, 15, 7, 6.6], arms: armsIdle, feet: feetIdle, eyes: [12, 10], mouth: 'smile' };
    K.idle = [
      kirby(base),
      kirby(Object.assign({}, base, { body: [12, 15.4, 7.4, 6.2], eyes: [12, 11] })),
    ];
    K.blink = kirby(Object.assign({}, base, { eyeStyle: 'closed' }));
    const runFeet = [
      [[7, 22, 3, 2], [17, 21, 3, 2]], [[9, 22, 3, 2], [15, 22, 3, 2]],
      [[7, 21, 3, 2], [17, 22, 3, 2]], [[9, 22, 3, 2], [15, 22, 3, 2]],
    ];
    const runArms = [[[5, 15, 2.2, 2], [19, 17, 2.2, 2]], armsIdle, [[5, 17, 2.2, 2], [19, 15, 2.2, 2]], armsIdle];
    K.run = runFeet.map((feet, i) => {
      const bob = i % 2 ? 0 : -1;
      return kirby({ body: [12, 15 + bob, 7, 6.6], arms: runArms[i].map(a => [a[0], a[1] + bob, a[2], a[3]]),
        feet, eyes: [13, 10 + bob], mouth: 'smile' });
    });
    K.jump = kirby({ body: [12, 14, 6.5, 7.3], arms: [[5, 10, 2, 2.2], [19, 10, 2, 2.2]],
      feet: [[10, 22, 2.5, 2], [15, 22, 2.5, 2]], eyes: [13, 9], mouth: 'o' });
    K.fall = kirby({ body: [12, 15, 7.3, 6.6], arms: [[4, 13, 2.2, 2], [20, 13, 2.2, 2]],
      feet: [[8, 22, 3, 2], [16, 22, 3, 2]], eyes: [13, 10], mouth: 'smile' });
    K.fly = [
      kirby({ body: [12, 12.5, 9.5, 9], arms: [[2.5, 8, 2.5, 2.2], [21.5, 8, 2.5, 2.2]],
        feet: [[9, 22, 2.2, 1.6], [15, 22, 2.2, 1.6]], eyes: [12, 8], mouth: 'puff', bigBlush: true, blushDy: 4 }),
      kirby({ body: [12, 12.5, 9.5, 9], arms: [[2, 15, 2.5, 2.2], [22, 15, 2.5, 2.2]],
        feet: [[9, 22, 2.2, 1.6], [15, 22, 2.2, 1.6]], eyes: [12, 8], mouth: 'puff', bigBlush: true, blushDy: 4 }),
    ];
    K.inhale = [
      kirby({ body: [11, 15, 8, 6.8], arms: [[3, 16, 2, 2]], feet: [[6, 22, 3, 2], [15, 22, 3, 2]],
        eyes: [9, 9], eyeStyle: 'squint', mouth: 'wide', mouthAt: [17.5, 15.5, 3.8, 4.6] }),
      kirby({ body: [11, 15, 8.6, 7.2], arms: [[2.5, 16, 2, 2]], feet: [[6, 22, 3, 2], [15, 22, 3, 2]],
        eyes: [9, 9], eyeStyle: 'squint', mouth: 'wide', mouthAt: [18, 15.5, 4.2, 5.2] }),
    ];
    K.full = runFeet.map((feet, i) => {
      const bob = i % 2 ? 0 : -1;
      return kirby({ body: [12, 14.6 + bob, 8.4, 7.8], arms: [[3.5, 16 + bob, 2, 2], [20.5, 16 + bob, 2, 2]],
        feet, eyes: [12, 9 + bob], mouth: 'none', bigBlush: true, blushDy: 4 });
    });
    K.spit = kirby({ body: [11.5, 15.3, 7.4, 6.4], arms: [[4, 14, 2.2, 2], [20, 14, 2.2, 2]],
      feet: feetIdle, eyes: [12, 11], eyeStyle: 'closed', mouth: 'o' });
    K.land = kirby({ body: [12, 16.2, 8, 5.6], arms: [[4, 18, 2.2, 1.8], [20, 18, 2.2, 1.8]],
      feet: [[8, 22, 3.2, 2], [16, 22, 3.2, 2]], eyes: [12, 12], mouth: 'smile' });
    K.hurt = kirby({ body: [12, 15, 7.6, 6.4], arms: [[4, 10, 2, 2.2], [20, 10, 2, 2.2]],
      feet: [[8, 22, 3, 2], [16, 22, 3, 2]], eyes: [10, 10], eyeStyle: 'x', mouth: 'o' });
    return K;
  }

  // ---- enemies (16x16, facing right) ---------------------------------------
  function walker(step) {
    const g = new Grid(16, 16);
    g.ellipse(8, 9.5, 7, 6.3, shade(PAL.orangeLight, PAL.orange, PAL.orangeDark), 'body');
    g.ellipse(10, 10, 4.6, 3.8, PAL.peach, 'face');
    const feet = step ? [[5, 14.5], [11, 15]] : [[5, 15], [11, 14.5]];
    feet.forEach(([x, y]) => g.ellipse(x, y, 2.6, 1.6, PAL.yellow, 'foot'));
    g.outline(PAL.ink, [['foot', 'body'], ['foot', 'face']]);
    g.rect(9, 8, 1, 2, PAL.ink); g.rect(12, 8, 1, 2, PAL.ink);
    g.set(8, 11, PAL.blush); g.set(13, 11, PAL.blush);
    return pair(g);
  }
  function flyer(wingUp) {
    const g = new Grid(16, 16);
    g.ellipse(4, wingUp ? 4.5 : 10, 3.4, 2.6, PAL.white, 'wing');
    g.ellipse(9, 9.5, 6, 5.6, shade(PAL.purpleLight, PAL.purple, PAL.purpleDark), 'body');
    g.ellipse(7, 15, 2, 1.3, PAL.orange, 'foot'); g.ellipse(11, 15, 2, 1.3, PAL.orange, 'foot');
    g.outline(PAL.ink, [['wing', 'body'], ['foot', 'body']]);
    g.rect(10, 7, 2, 3, PAL.white); g.rect(11, 8, 1, 2, PAL.ink);
    g.set(13, 11, PAL.blush);
    return pair(g);
  }
  function hopper(stretch) {
    const g = new Grid(16, 16);
    if (stretch) g.ellipse(8, 9.5, 5.6, 6.6, shade(PAL.greenLight, PAL.green, PAL.greenDark), 'body');
    else g.ellipse(8, 11, 7.2, 5, shade(PAL.greenLight, PAL.green, PAL.greenDark), 'body');
    const top = stretch ? 3 : 6;
    g.art(['.gg', 'gg.', '.g.'], 6, top - 3, { g: PAL.greenLight }, 'leaf');
    g.outline(PAL.ink, [['leaf', 'body']]);
    const ey = stretch ? 7 : 9;
    g.rect(9, ey, 2, 2, PAL.white); g.set(10, ey + 1, PAL.ink);
    g.rect(12, ey, 2, 2, PAL.white); g.set(13, ey + 1, PAL.ink);
    g.set(11, ey + 3, PAL.mouth);
    return pair(g);
  }
  function gordo(rot) {
    const g = new Grid(16, 16);
    for (let i = 0; i < 8; i++) {
      const a = rot + i * Math.PI / 4;
      const tip = [8 + Math.cos(a) * 8, 8 + Math.sin(a) * 8];
      const l = [8 + Math.cos(a - 0.45) * 4.5, 8 + Math.sin(a - 0.45) * 4.5];
      const r = [8 + Math.cos(a + 0.45) * 4.5, 8 + Math.sin(a + 0.45) * 4.5];
      g.poly([tip, l, r], PAL.white, 'spike');
    }
    g.ellipse(8, 8, 5.4, 5.4, shade(PAL.stone, PAL.navy, PAL.navyDark), 'body');
    g.outline(PAL.ink, [['spike', 'body']]);
    g.rect(5, 7, 2, 2, PAL.white); g.rect(9, 7, 2, 2, PAL.white);
    g.set(6, 8, PAL.ink); g.set(9, 8, PAL.ink);
    g.set(5, 5, PAL.ink); g.set(6, 6, PAL.ink); g.set(10, 5, PAL.ink); g.set(9, 6, PAL.ink);
    return pair(g);
  }

  // ---- items, projectiles, goal -------------------------------------------
  function bigStar(size, outer, inner, rot, fill) {
    const g = new Grid(size, size);
    const c = size / 2;
    const pts = starPoints(c, c, outer, inner, rot);
    g.poly(pts, (x, y) => (Math.hypot(x + 0.5 - c + 1, y + 0.5 - c + 1) < inner * 0.9 ? PAL.yellowLight : fill), 'star');
    g.outline(PAL.ink);
    return g;
  }
  function smallStar(twinkle) {
    const g = new Grid(9, 9);
    g.art(twinkle ? ['....w....', '....y....', '...yyy...', 'wyyyYyyyw', '..yyyyy..', '..yy.yy..', '.yy...yy.', '.........', '.........']
      : ['....y....', '...yyy...', 'yyyyYyyyy', '.yyyyyyy.', '..yyyyy..', '..yy.yy..', '.y.....y.', '.........', '.........'],
    0, 1, { y: PAL.yellow, Y: PAL.yellowLight, w: PAL.white });
    return g.toCanvas(false);
  }
  function tomato() {
    const g = new Grid(14, 14);
    g.ellipse(7, 8.5, 6.4, 5.6, shade(PAL.tongue, PAL.red, PAL.redDark), 'body');
    g.art(['.g.g.', 'ggggg', '.ggg.'], 5, 1, { g: PAL.green }, 'leaf');
    g.outline(PAL.ink, [['leaf', 'body']]);
    g.art(['w...w', 'ww.ww', 'w.w.w', 'w...w'], 5, 7, { w: PAL.white });
    return g.toCanvas(false);
  }
  function puff(big) {
    const g = new Grid(12, 12);
    const r = big ? 5.2 : 4;
    g.ellipse(6, 6, r, r * 0.85, shade(PAL.white, PAL.skyLight, PAL.sky), 'puff');
    g.ellipse(3.5, 5, r * 0.55, r * 0.5, PAL.white, 'puff');
    g.outline(PAL.stoneDark);
    return g.toCanvas(false);
  }

  function build() {
    const S = {};
    S.kirby = buildKirby();
    S.walker = [walker(0), walker(1)];
    S.flyer = [flyer(true), flyer(false)];
    S.hopper = [hopper(false), hopper(true)];
    S.gordo = [gordo(0), gordo(Math.PI / 8)];
    S.star = [0, 1, 2, 3].map(i => bigStar(16, 7.6, 3.4, i * Math.PI / 10, PAL.yellow).toCanvas(false));
    S.warpStar = [bigStar(28, 13.5, 6.2, 0, PAL.yellow).toCanvas(false), bigStar(28, 13, 6, 0.08, PAL.yellow).toCanvas(false)];
    S.pickup = [smallStar(false), smallStar(true)];
    S.tomato = tomato();
    S.puff = [puff(true), puff(false)];
    Object.assign(S, KB.Tiles.build(Grid, shade));
    return S;
  }

  return { build, Grid, shade };
})();

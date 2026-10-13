// World sprites drawn in code: tiles, enemies, items, the boss and background pieces.
(function () {
  'use strict';
  var Pix = Sprites.Pix, add = Sprites.add, starPoints = Sprites.starPoints;

  // Deterministic per-pixel noise so textures look hand-placed but never change.
  function hash(x, y) {
    var h = (x * 374761393 + y * 668265263) | 0;
    h = Math.imul(h ^ (h >>> 13), 1274126177);
    return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
  }

  function dirt(P, y0) {
    for (var y = y0; y < 16; y++) {
      for (var x = 0; x < 16; x++) {
        var n = hash(x, y);
        P.set(x, y, n < 0.08 ? 'B' : n > 0.95 ? 't' : 'b');
      }
    }
  }

  function tiles() {
    var P = new Pix(16, 16);
    dirt(P, 0);
    add('tile_dirt', P);

    P = new Pix(16, 16);
    dirt(P, 0);
    P.rect(0, 0, 16, 1, 'G');
    P.rect(0, 1, 16, 3, 'g');
    for (var x = 0; x < 16; x++) {
      P.set(x, 4, 'G');
      if (hash(x, 4) > 0.55) P.set(x, 5, 'G');
      if (hash(x, 1) > 0.8) P.set(x, 1, 'G');
    }
    add('tile_grass', P);

    P = new Pix(16, 16);
    P.rect(0, 0, 16, 16, 'n');
    P.rect(0, 7, 16, 1, 'N'); P.rect(0, 15, 16, 1, 'N');
    P.rect(7, 0, 1, 7, 'N'); P.rect(15, 8, 1, 7, 'N');
    P.rect(0, 0, 7, 1, 'S'); P.rect(8, 8, 7, 1, 'S');
    add('tile_stone', P);

    P = new Pix(16, 16);
    P.ellipse(4, 3.5, 4.5, 3, 'w', 'S');
    P.ellipse(11, 3, 5.5, 3.2, 'w', 'S');
    P.ellipse(8, 5, 7.5, 2.2, 'w', 'S');
    P.outline('n');
    add('tile_platform', P);

    P = new Pix(16, 16);
    P.rect(0, 0, 16, 16, 'o');
    P.rect(1, 1, 14, 1, 'y'); P.rect(1, 1, 1, 14, 'y');
    P.rect(1, 14, 14, 1, 'b'); P.rect(14, 1, 1, 14, 'b');
    P.poly(starPoints(8, 8.3, 6, 2.6, 0), 'y');
    P.set(7, 6, 'w'); P.set(8, 6, 'w');
    for (var i = 0; i < 16; i++) { P.set(i, 0, 'B'); P.set(i, 15, 'B'); P.set(0, i, 'B'); P.set(15, i, 'B'); }
    add('tile_star', P);

    P = new Pix(16, 16);
    dirt(P, 9);
    P.rect(0, 9, 16, 1, 'G');
    for (var s = 0; s < 3; s++) {
      var bx = s * 5 + 0.5;
      P.poly([[bx, 9], [bx + 2.5, 1], [bx + 5, 9]], 'w');
      P.poly([[bx + 2.5, 2], [bx + 5, 9], [bx + 2.5, 9]], 'n');
    }
    add('tile_spikes', P);
  }

  function walker() {
    [0, 1].forEach(function (f) {
      var P = new Pix(16, 16);
      P.ellipse(f ? 5.5 : 4, 14.5, 2.8, 1.6, 'B');
      P.ellipse(f ? 10.5 : 12, 14.5, 2.8, 1.6, 'B');
      P.ellipse(8, 8.5 + (f ? 0.5 : 0), 6.6, 6, 'o', 'b');
      P.ellipse(9.8, 9.2 + (f ? 0.5 : 0), 4.3, 3.6, 't');
      P.rows(7, 0 + f, ['.g.', 'gGg', '.G.']);
      P.outline('K');
      var ey = 7 + f;
      P.set(8, ey, 'K'); P.set(8, ey + 1, 'K'); P.set(11, ey, 'K'); P.set(11, ey + 1, 'K');
      P.set(13, ey + 3, 'r');
      add('walker' + f, P);
    });
  }

  function flyer() {
    [0, 1].forEach(function (f) {
      var P = new Pix(20, 16);
      if (f === 0) { P.ellipse(5, 4.5, 4.2, 2.6, 'w', 'S'); P.ellipse(4, 6.5, 3, 1.6, 'w', 'S'); }
      else { P.ellipse(5, 11.5, 4.2, 2.6, 'w', 'S'); P.ellipse(4, 9.5, 3, 1.6, 'w', 'S'); }
      P.ellipse(11, 8.5, 5.8, 5.2, 'v', 'N');
      P.ellipse(9, 14, 1.6, 1, 'y'); P.ellipse(13, 14, 1.6, 1, 'y');
      P.outline('K');
      P.rows(11, 6, ['ww.ww', 'Kw.Kw']);
      P.rows(10, 5, ['K....K']);
      P.set(13, 10, 'r'); P.set(14, 10, 'r');
      add('flyer' + f, P);
    });
  }

  function hopper() {
    var P = new Pix(16, 18);
    P.ellipse(8, 13, 7.2, 4.8, 'g', 'G');
    P.outline('K');
    P.rows(8, 10, ['ww.ww', 'wK.wK']);
    P.rows(9, 14, ['KKK']);
    add('hopper0', P);
    P = new Pix(16, 18);
    P.ellipse(8, 9.5, 5.2, 7.8, 'g', 'G');
    P.outline('K');
    P.rows(8, 5, ['ww.ww', 'wK.wK', 'wK.wK']);
    P.rows(9, 10, ['.K.', 'KrK']);
    add('hopper1', P);
  }

  function spiky() {
    [0, 1].forEach(function (f) {
      var P = new Pix(20, 20), cx = 10, cy = 10;
      for (var k = 0; k < 8; k++) {
        var a = k * Math.PI / 4 + f * Math.PI / 8;
        P.poly([
          [cx + Math.cos(a) * 9.8, cy + Math.sin(a) * 9.8],
          [cx + Math.cos(a + 0.42) * 5.5, cy + Math.sin(a + 0.42) * 5.5],
          [cx + Math.cos(a - 0.42) * 5.5, cy + Math.sin(a - 0.42) * 5.5]
        ], 'w');
      }
      P.ellipse(cx, cy, 6.2, 6.2, 'N', 'K');
      P.outline('K');
      P.rows(8, 7, ['w.w', 'w.w']);
      P.rows(11, 7, ['w', 'w']);
      P.set(12, 7, 'w'); P.set(12, 8, 'w');
      add('spiky' + f, P);
    });
  }

  function objects() {
    var P = new Pix(12, 12);
    P.ellipse(6, 7, 5.2, 4.7, 'r', 'd', 'l');
    P.rect(6, 0, 1, 3, 'B');
    P.rows(7, 0, ['gg', '.g']);
    P.outline('K');
    add('apple', P);

    P = new Pix(14, 12);
    P.ellipse(5, 6.5, 4.5, 4, 'w', 'S');
    P.ellipse(9.5, 5.5, 4, 4.2, 'w', 'S');
    P.outline('n');
    add('bosspuff', P);

    P = new Pix(10, 10);
    P.ellipse(4, 5, 3.6, 3.2, 'w', 'S');
    P.ellipse(6.5, 4.5, 3, 3, 'w', 'S');
    P.outline('S');
    add('airpuff', P);

    [12, 16].forEach(function (size) {
      for (var f = 0; f < 4; f++) {
        var Q = new Pix(size, size), c = size / 2, rot = f * Math.PI / 10;
        Q.poly(starPoints(c, c + 0.4, c - 0.5, c * 0.45, rot), 'o');
        Q.poly(starPoints(c, c + 0.4, c - 2, c * 0.32, rot), 'y');
        Q.set(c - 1, c - 1, 'w'); Q.set(c, c - 1, 'w');
        Q.outline('K');
        add('spit' + size + '_' + f, Q);
      }
    });

    [1, 0.6, 0.2, 0.6].forEach(function (sx, f) {
      var Q = new Pix(10, 10);
      var pts = starPoints(5, 5.4, 4.6, 2, 0).map(function (p) { return [5 + (p[0] - 5) * sx, p[1]]; });
      Q.poly(pts, 'y');
      if (sx > 0.5) Q.set(4, 4, 'w');
      Q.outline('o');
      add('pointstar' + f, Q);
    });

    P = new Pix(12, 12);
    P.ellipse(6, 7, 5.4, 4.8, 'r', 'd');
    P.rows(3, 1, ['g.g.g', '.ggg.']);
    P.set(3, 5, 'w'); P.set(3, 6, 'w'); P.set(4, 5, 'w');
    P.outline('K');
    add('food', P);

    P = new Pix(12, 12);
    P.ellipse(6, 6.5, 5, 4.6, 'p', 'd', 'l');
    P.outline('K');
    P.rows(5, 4, ['K.K', 'K.K']);
    P.set(3, 7, 'r'); P.set(9, 7, 'r');
    P.rows(0, 0, ['y']); P.rows(11, 1, ['y']);
    add('oneup', P);

    P = new Pix(16, 16);
    P.rect(7, 8, 2, 8, 'B');
    P.rect(1, 1, 14, 8, 'b');
    P.rect(2, 2, 12, 1, 't');
    P.rect(3, 4, 7, 1, 'B'); P.rect(3, 6, 9, 1, 'B');
    P.outline('K');
    add('sign', P);
  }

  function markers() {
    ['off', 'on0', 'on1'].forEach(function (name, f) {
      var P = new Pix(14, 26);
      P.rect(2, 2, 2, 24, 'N');
      P.rect(2, 2, 1, 24, 'n');
      var col = f === 0 ? 'n' : 'y', shade = f === 0 ? 'N' : 'o';
      var wave = f === 2 ? 1 : 0;
      P.poly([[4, 3], [13, 5 + wave], [13, 10 + wave], [4, 11]], col);
      P.rect(4, 10, 9, 1, shade);
      if (f > 0) P.poly(starPoints(8.5, 7.3 + wave * 0.5, 2.6, 1.1, 0), 'w');
      P.ellipse(3, 2, 2, 2, 'y', 'o');
      P.outline('K');
      add('checkpoint_' + name, P);
    });

    [0, 1].forEach(function (f) {
      var P = new Pix(28, 28);
      P.poly(starPoints(14, 15, 13 - f * 0.5, 6, f * 0.06), 'o');
      P.poly(starPoints(14, 15, 11 - f * 0.5, 5, f * 0.06), 'y');
      P.ellipse(10, 11, 2, 1.5, 'w');
      P.outline('K');
      P.rows(12, 13, ['K..K', 'K..K']);
      P.rows(13, 16, ['rr']);
      add('warp' + f, P);
    });
  }

  function boss() {
    ['idle', 'blow', 'hurt', 'dead'].forEach(function (mode) {
      var P = new Pix(80, 120);
      // Canopy
      P.ellipse(40, 34, 38, 26, 'g', 'G');
      P.ellipse(16, 46, 15, 12, 'g', 'G');
      P.ellipse(64, 46, 15, 12, 'g', 'G');
      P.ellipse(40, 12, 22, 11, 'g', 'G');
      for (var i = 0; i < 40; i++) {
        var lx = Math.floor(hash(i, 7) * 76) + 2, ly = Math.floor(hash(i, 9) * 56) + 4;
        if (P.get(lx, ly) === 'g') P.set(lx, ly, 'G');
      }
      // Trunk with flared roots
      P.rect(21, 52, 38, 68, 'b');
      P.poly([[21, 104], [8, 120], [24, 120]], 'b');
      P.poly([[59, 104], [72, 120], [56, 120]], 'b');
      for (var b = 0; b < 9; b++) {
        var bx = 23 + Math.floor(hash(b, 3) * 34), by = 56 + Math.floor(hash(b, 5) * 50), len = 4 + Math.floor(hash(b, 11) * 8);
        P.rect(bx, by, 1, len, 'B');
      }
      P.rect(21, 52, 2, 68, 'B');
      P.rect(55, 52, 4, 68, 'B');
      P.outline('K');
      // Face
      if (mode === 'dead') {
        P.rows(30, 74, ['K...K', '.K.K.', '..K..', '.K.K.', 'K...K']);
        P.rows(45, 74, ['K...K', '.K.K.', '..K..', '.K.K.', 'K...K']);
      } else if (mode === 'hurt') {
        P.rows(29, 76, ['KKK...', '...KKK']);
        P.rows(45, 76, ['...KKK', 'KKK...']);
      } else {
        P.rows(28, 70, ['KKKK....', '....KKKK']);
        P.rows(44, 70, ['....KKKK', 'KKKK....']);
        P.ellipse(32, 79, 2.6, 4, 'K'); P.ellipse(48, 79, 2.6, 4, 'K');
        P.set(31, 77, 'w'); P.set(47, 77, 'w');
      }
      if (mode === 'blow') { P.ellipse(40, 97, 5, 6, 'K'); P.ellipse(40, 99, 3, 3, 'B'); }
      else if (mode === 'hurt' || mode === 'dead') P.rows(33, 95, ['K.K.K.K.K.K.K.', '.K.K.K.K.K.K.K']);
      else P.rows(33, 96, ['.KKKKKKKKKKKK.', 'K............K']);
      // Apples hanging in the canopy
      [[14, 40], [62, 38], [30, 18], [52, 22]].forEach(function (a) {
        P.ellipse(a[0], a[1], 3, 3, 'r', 'd');
        P.set(a[0] - 1, a[1] - 1, 'l');
      });
      add('boss_' + mode, P);
    });
  }

  function background() {
    var P = new Pix(256, 72);
    for (var x = 0; x < 256; x++) {
      var hgt = 40 + Math.sin(x / 256 * Math.PI * 4) * 14 + Math.sin(x / 256 * Math.PI * 10) * 6;
      for (var y = Math.floor(72 - hgt); y < 72; y++) P.set(x, y, 'S');
    }
    add('bg_far', P);

    P = new Pix(256, 56);
    for (var x2 = 0; x2 < 256; x2++) {
      var h2 = 30 + Math.sin(x2 / 256 * Math.PI * 6 + 1) * 12 + Math.sin(x2 / 256 * Math.PI * 2) * 6;
      for (var y2 = Math.floor(56 - h2); y2 < 56; y2++) P.set(x2, y2, y2 < 56 - h2 + 2 ? 'G' : 'g');
    }
    for (var t = 0; t < 7; t++) {
      var tx = 18 + t * 37, base = 56 - (30 + Math.sin(tx / 256 * Math.PI * 6 + 1) * 12 + Math.sin(tx / 256 * Math.PI * 2) * 6);
      P.rect(tx, base - 6, 2, 8, 'B');
      P.ellipse(tx + 1, base - 9, 5, 5, 'G');
    }
    add('bg_hills', P);

    P = new Pix(48, 20);
    P.ellipse(14, 12, 12, 7, 'w', 'S');
    P.ellipse(28, 9, 13, 9, 'w', 'S');
    P.ellipse(38, 13, 9, 6, 'w', 'S');
    add('bg_cloud', P);

    P = new Pix(12, 3);
    P.rect(0, 1, 12, 1, 'w'); P.rect(3, 0, 5, 1, 'S'); P.rect(6, 2, 4, 1, 'S');
    add('wind_streak', P);
  }

  Sprites.register(tiles);
  Sprites.register(walker);
  Sprites.register(flyer);
  Sprites.register(hopper);
  Sprites.register(spiky);
  Sprites.register(objects);
  Sprites.register(markers);
  Sprites.register(boss);
  Sprites.register(background);
})();

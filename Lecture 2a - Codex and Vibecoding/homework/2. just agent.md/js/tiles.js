// Tile, decoration, HUD icon and background art, drawn in code.
var KB = (typeof KB !== 'undefined') ? KB : {};

KB.Tiles = (function () {
  const PAL = KB.PAL;

  // Deterministic "random" so the art is the same every time.
  function hash(x, y) {
    let h = (x * 374761393 + y * 668265263) | 0;
    h = (h ^ (h >>> 13)) * 1274126177 | 0;
    return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
  }

  function dirt(g, yFrom) {
    for (let y = yFrom; y < 16; y++) {
      for (let x = 0; x < 16; x++) {
        const r = hash(x, y);
        g.set(x, y, r < 0.08 ? PAL.brownDark : r > 0.94 ? PAL.brownLight : PAL.brown, 'dirt');
      }
    }
    // a couple of pebbles
    [[3, yFrom + 4], [11, yFrom + 7]].forEach(([x, y]) => {
      if (y < 15) { g.set(x, y, PAL.brownLight); g.set(x + 1, y, PAL.brownLight); g.set(x, y + 1, PAL.brownDark); g.set(x + 1, y + 1, PAL.brownDark); }
    });
  }

  function groundTop(Grid) {
    const g = new Grid(16, 16);
    dirt(g, 0);
    for (let x = 0; x < 16; x++) {
      const depth = 4 + (hash(x, 99) < 0.4 ? 1 : 0) + (x % 5 === 2 ? 1 : 0);
      for (let y = 0; y < depth; y++) g.set(x, y, y === 0 ? PAL.greenLight : y === depth - 1 ? PAL.greenDark : PAL.green);
    }
    return g.toCanvas(false);
  }
  function ground(Grid) {
    const g = new Grid(16, 16);
    dirt(g, 0);
    return g.toCanvas(false);
  }
  function brick(Grid) {
    const g = new Grid(16, 16);
    for (let y = 0; y < 16; y++) {
      for (let x = 0; x < 16; x++) {
        const row = y < 8 ? 0 : 1;
        const bx = (x + (row ? 8 : 0)) % 16;
        let col = PAL.stone;
        if (y % 8 === 7 || bx === 15) col = PAL.stoneDark;
        else if (y % 8 === 0 || bx === 0) col = PAL.stoneLight;
        else if (hash(x, y) < 0.06) col = PAL.stoneDark;
        g.set(x, y, col);
      }
    }
    return g.toCanvas(false);
  }
  function starBlock(Grid) {
    const g = new Grid(16, 16);
    g.rect(0, 0, 16, 16, PAL.orangeLight);
    g.rect(1, 1, 14, 1, PAL.peach); g.rect(1, 1, 1, 14, PAL.peach);
    g.rect(1, 14, 14, 1, PAL.orange); g.rect(14, 1, 1, 14, PAL.orange);
    g.art(['...k...', '..kyk..', 'kkkykkk', 'kyyYyyk', '.kyyyk.', '.kykyk.', 'kk...kk'], 4, 4,
      { k: PAL.orangeDark, y: PAL.yellow, Y: PAL.yellowLight });
    for (let i = 0; i < 16; i++) { g.set(i, 0, PAL.ink); g.set(i, 15, PAL.ink); g.set(0, i, PAL.ink); g.set(15, i, PAL.ink); }
    return g.toCanvas(false);
  }
  function cloud(Grid, shade) {
    const g = new Grid(16, 16);
    g.ellipse(4, 6, 5, 4, PAL.white, 'c');
    g.ellipse(11, 5, 6, 4.5, PAL.white, 'c');
    g.rect(0, 6, 16, 4, PAL.white, 'c');
    for (let x = 0; x < 16; x++) for (let y = 8; y < 10; y++) g.set(x, y, PAL.skyLight, 'c');
    g.outline(PAL.stoneDark);
    // seamless sides: undo outline where the cloud continues into the next tile
    for (let y = 6; y < 9; y++) { g.set(0, y, y === 8 ? PAL.skyLight : PAL.white, 'c'); g.set(15, y, y === 8 ? PAL.skyLight : PAL.white, 'c'); }
    return g.toCanvas(false);
  }

  function flower(Grid, petal) {
    const g = new Grid(5, 7);
    g.art(['.p.', 'pyp', '.p.'], 1, 0, { p: petal, y: PAL.yellow });
    g.rect(2, 3, 1, 4, PAL.greenDark);
    g.set(1, 5, PAL.green); g.set(3, 4, PAL.green);
    return g.toCanvas(false);
  }
  function bush(Grid, shade) {
    const g = new Grid(28, 12);
    const paint = shade(PAL.greenLight, PAL.green, PAL.greenDark);
    g.ellipse(7, 8, 7, 5, paint, 'b'); g.ellipse(15, 6, 8, 6, paint, 'b'); g.ellipse(22, 8, 6, 4.5, paint, 'b');
    g.rect(1, 10, 26, 2, PAL.green, 'b');
    g.outline(PAL.greenDark);
    return g.toCanvas(false);
  }
  function flag(Grid, raised) {
    const g = new Grid(12, 30);
    g.rect(1, 2, 2, 28, PAL.stoneLight); g.rect(2, 2, 1, 28, PAL.stoneDark);
    g.rect(0, 0, 4, 3, PAL.yellow); g.set(1, 0, PAL.yellowLight);
    const y = raised ? 3 : 20;
    g.art(['ffffffff', 'ffffffff.', 'fffffff', 'ffffff', 'fffff'], 3, y, { f: raised ? PAL.yellow : PAL.red });
    if (raised) g.art(['.s.', 'sss', '.s.'], 6, y + 1, { s: PAL.white });
    return g.toCanvas(false);
  }
  function pip(Grid, full) {
    const g = new Grid(7, 7);
    g.ellipse(3.5, 3.5, 3.5, 3.5, full ? PAL.pink : PAL.stoneDark, 'p');
    g.outline(PAL.ink);
    if (full) g.set(2, 2, PAL.pinkLight);
    return g.toCanvas(false);
  }
  function lifeIcon(Grid) {
    const g = new Grid(10, 9);
    g.ellipse(5, 4.5, 5, 4.5, PAL.pink, 'b');
    g.outline(PAL.ink);
    g.rect(4, 2, 1, 2, PAL.ink); g.rect(6, 2, 1, 2, PAL.ink);
    g.set(3, 5, PAL.blush); g.set(7, 5, PAL.blush);
    return g.toCanvas(false);
  }

  // Wide, horizontally tileable background strips.
  function hills(width, height, base, waves, fill, top, dots) {
    const cv = document.createElement('canvas');
    cv.width = width; cv.height = height;
    const ctx = cv.getContext('2d');
    for (let x = 0; x < width; x++) {
      let h = base;
      waves.forEach(([amp, cycles, phase]) => { h += amp * Math.sin(2 * Math.PI * x * cycles / width + phase); });
      const y0 = Math.round(height - h);
      ctx.fillStyle = fill; ctx.fillRect(x, y0, 1, height - y0);
      ctx.fillStyle = top; ctx.fillRect(x, y0, 1, 1);
      if (dots && hash(x, 7) < 0.05) { ctx.fillStyle = dots; ctx.fillRect(x, y0 + 4 + Math.floor(hash(x, 3) * 10), 2, 2); }
    }
    return cv;
  }
  function skyCloud(Grid, shade) {
    const g = new Grid(44, 18);
    const paint = shade(PAL.white, PAL.white, PAL.skyLight);
    g.ellipse(12, 11, 10, 6, paint, 'c'); g.ellipse(24, 8, 12, 8, paint, 'c'); g.ellipse(34, 12, 9, 5.5, paint, 'c');
    g.outline(PAL.skyLight);
    return g.toCanvas(false);
  }

  function build(Grid, shade) {
    return {
      tile: {
        groundTop: groundTop(Grid), ground: ground(Grid), brick: brick(Grid),
        starBlock: starBlock(Grid), cloud: cloud(Grid, shade),
      },
      flowers: [flower(Grid, PAL.white), flower(Grid, PAL.red), flower(Grid, PAL.purpleLight)],
      bush: bush(Grid, shade),
      flag: [flag(Grid, false), flag(Grid, true)],
      pip: [pip(Grid, false), pip(Grid, true)],
      lifeIcon: lifeIcon(Grid),
      bgFar: hills(320, 90, 46, [[10, 2, 0.4], [6, 5, 1.3]], PAL.hillFar, PAL.white),
      bgNear: hills(256, 70, 30, [[12, 2, 2.1], [5, 6, 0.2]], PAL.hill, PAL.greenLight, PAL.hillDark),
      skyCloud: skyCloud(Grid, shade),
    };
  }

  return { build, hash };
})();

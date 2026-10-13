// Level data and parsing. Pure data: no DOM, no canvas.
var KB = (typeof KB !== 'undefined') ? KB : {};
if (typeof module !== 'undefined') Object.assign(KB, require('./logic/constants.js'));

KB.Level = (function () {
  const C = KB.C;
  const T = C.T;
  const ROWS = 12;

  // Legend:  . empty   # ground   B brick   S star block (inhalable)   = cloud (jump through from below)
  //          P start   W walker   F flyer   H hopper   G gordo (spiky, can't be inhaled)
  //          * point star   T tomato (heals)   C checkpoint   E warp star goal   1-9 tutorial sign
  const TILE_CHARS = { '#': T.GROUND, 'B': T.BRICK, 'S': T.STAR_BLOCK, '=': T.CLOUD };
  const ENEMY_CHARS = { 'W': 'walker', 'F': 'flyer', 'H': 'hopper', 'G': 'gordo' };
  const PICKUP_CHARS = { '*': 'star', 'T': 'tomato' };

  const SIGNS = [
    'ARROWS / A D: MOVE|SPACE: JUMP',
    'HOLD ENTER: INHALE|ENTER AGAIN: SPIT A STAR',
    'TAP SPACE IN THE AIR|TO FLY!',
    'STAR BLOCKS IN THE WAY?|INHALE THEM!',
    'SPIKY GORDO CAN\'T BE|INHALED. FLY OVER IT!',
    'THE WARP STAR!|TOUCH IT TO WIN',
  ];

  // A section is a width plus the rows that are not empty. 'G' means a full row of ground.
  function section(width, rows) {
    const out = [];
    for (let r = 0; r < ROWS; r++) {
      let s = rows[r] || '';
      if (s === 'G') s = '#'.repeat(width);
      if (s.length > width) throw new Error('Section row ' + r + ' is wider than ' + width + ': ' + s);
      out.push(s + '.'.repeat(width - s.length));
    }
    return out;
  }
  function gap(width, rows) { return section(width, rows || {}); }
  function fillRows(width, from, to, ch, offset, len) {
    const rows = {};
    for (let r = from; r <= to; r++) rows[r] = '.'.repeat(offset) + ch.repeat(len);
    return rows;
  }

  const SECTIONS = [
    // Meadow start
    section(30, {
      5: '..............***',
      7: '.............=====',
      9: '..P.1.....*.*.*....2....W',
      10: 'G', 11: 'G',
    }),
    gap(2),
    // Brick step and first hopper
    section(26, {
      6: '.........***',
      8: '........BBBB......*.*',
      9: '....W...BBBB.......H',
      10: 'G', 11: 'G',
    }),
    gap(3),
    // Flyer and the flying tutorial
    section(24, {
      4: '............F',
      7: '....***',
      9: '.................3....W',
      10: 'G', 11: 'G',
    }),
    // Wide pit: must fly
    gap(9, { 3: '..*.*.*..', 6: '....F' }),
    // Checkpoint and the star block corridor
    section(30, Object.assign(fillRows(30, 0, 7, 'B', 10, 14), {
      8: '..........SS..S',
      9: '..C...4...SS..S.....W',
      10: 'G', 11: 'G',
    })),
    // Terraces with hoppers
    section(34, {
      4: '....................***',
      6: '..................=====',
      7: '..........................BBB',
      8: '.............H............BBB',
      9: '.....W...BBBBBBB.....H....BBB.5',
      10: 'G', 11: 'G',
    }),
    // Gordo pit
    gap(8, { 2: '.*....*.', 7: '...G' }),
    // Second checkpoint, tomato on a cloud
    section(22, {
      3: '..............F',
      6: '........T',
      7: '.......===',
      9: '..C.........W.....W',
      10: 'G', 11: 'G',
    }),
    // Cloud hop pit
    gap(14, { 3: '..........F', 5: '.......F', 7: '...*.......*', 8: '..===.....===' }),
    // Stairs up to the warp star
    section(30, {
      2: '.......................*.*',
      5: '......................E',
      6: '.....................#########',
      7: '..................############',
      8: '...............###############',
      9: '.....W..6...##################',
      10: 'G', 11: 'G',
    }),
  ];

  function joinSections(sections) {
    const rows = [];
    for (let r = 0; r < ROWS; r++) rows.push(sections.map(s => s[r]).join(''));
    return rows;
  }

  const DEFAULT_ROWS = joinSections(SECTIONS);

  // Turn an array of equal-length strings into a level description.
  function parse(rows) {
    const h = rows.length;
    const w = rows[0].length;
    const S = C.TILE;
    const level = {
      w, h, tiles: new Array(w * h).fill(T.EMPTY),
      start: null, goal: null, enemies: [], pickups: [], checkpoints: [], signs: [],
    };
    rows.forEach((row, ty) => {
      if (row.length !== w) throw new Error('Row ' + ty + ' has length ' + row.length + ', expected ' + w);
      for (let tx = 0; tx < w; tx++) {
        const ch = row[tx];
        const px = tx * S, py = ty * S;
        if (TILE_CHARS[ch] !== undefined) level.tiles[ty * w + tx] = TILE_CHARS[ch];
        else if (ch === 'P') level.start = { x: px + (S - C.PLAYER_W) / 2, y: py + S - C.PLAYER_H };
        else if (ENEMY_CHARS[ch]) level.enemies.push({ kind: ENEMY_CHARS[ch], tx, ty });
        else if (PICKUP_CHARS[ch]) level.pickups.push({ kind: PICKUP_CHARS[ch], tx, ty });
        else if (ch === 'C') level.checkpoints.push({ tx, ty, x: px + (S - C.PLAYER_W) / 2, y: py + S - C.PLAYER_H });
        else if (ch === 'E') level.goal = { tx, ty, x: px - 2, y: py - 2, w: S + 4, h: S + 4 };
        else if (ch >= '1' && ch <= '9') level.signs.push({ tx, ty, text: SIGNS[ch.charCodeAt(0) - 49] || '' });
        else if (ch !== '.') throw new Error('Unknown level character "' + ch + '" at ' + tx + ',' + ty);
      }
    });
    if (!level.start) throw new Error('Level has no start (P)');
    return level;
  }

  // Column ranges with no floor at the bottom row: the pits Kirby has to cross.
  function findGaps(level) {
    const gaps = [];
    let start = -1;
    for (let tx = 0; tx <= level.w; tx++) {
      const empty = tx < level.w && level.tiles[(level.h - 1) * level.w + tx] === T.EMPTY;
      if (empty && start < 0) start = tx;
      if (!empty && start >= 0) { gaps.push({ from: start, to: tx - 1 }); start = -1; }
    }
    return gaps;
  }

  function load() { return parse(DEFAULT_ROWS); }

  return { ROWS, DEFAULT_ROWS, SIGNS, parse, load, findGaps };
})();

if (typeof module !== 'undefined') module.exports = { Level: KB.Level };

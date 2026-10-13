// Project rules from CLAUDE.md that can be checked mechanically, plus a sanity check of the level.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { World } = require('../js/logic/world.js');
const { LEVEL_1 } = require('../js/level.js');

const root = path.join(__dirname, '..');
const jsFiles = (dir) => fs.readdirSync(path.join(root, dir)).filter((f) => f.endsWith('.js')).map((f) => path.join(dir, f));
const sources = [...jsFiles('js'), ...jsFiles('js/logic')];

test('every source file stays under 400 lines', () => {
  for (const f of sources) {
    const lines = fs.readFileSync(path.join(root, f), 'utf8').split('\n').length;
    assert.ok(lines < 400, `${f} has ${lines} lines`);
  }
});

test('logic files never touch the DOM or canvas and export for Node', () => {
  for (const f of jsFiles('js/logic')) {
    const src = fs.readFileSync(path.join(root, f), 'utf8');
    const code = src.replace(/\/\/.*$/gm, '');
    assert.doesNotMatch(code, /\b(document|window|canvas|getContext|requestAnimationFrame|localStorage)\b/, f);
    assert.match(src.trim().split('\n').pop(), /^if \(typeof module !== 'undefined'\) module\.exports = \{.*\};$/, f);
  }
});

test('index.html loads every script as a classic local script (works over file://)', () => {
  const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  assert.doesNotMatch(html, /type=["']module["']/);
  assert.doesNotMatch(html, /(src|href)=["']https?:/, 'no external assets');
  const scripts = [...html.matchAll(/<script src="([^"]+)"/g)].map((m) => m[1]);
  assert.ok(scripts.length >= 10);
  for (const s of scripts) assert.ok(fs.existsSync(path.join(root, s)), s + ' is missing');
  for (const f of sources) assert.ok(scripts.includes(f.replace(/\\/g, '/')), f + ' is not loaded by index.html');
});

test('no image or audio files: all art and sound is made in code', () => {
  const walk = (dir) => fs.readdirSync(dir, { withFileTypes: true }).flatMap((d) =>
    d.name.startsWith('.') ? [] : d.isDirectory() ? walk(path.join(dir, d.name)) : [d.name]);
  const assets = walk(root).filter((n) => /\.(png|jpe?g|gif|bmp|webp|mp3|wav|ogg)$/i.test(n));
  assert.deepEqual(assets, []);
});

test('the level has every required ingredient', () => {
  const w = World.build(LEVEL_1);
  const types = new Set(w.spawns.map((s) => s.type));
  for (const t of ['walker', 'flyer', 'hopper', 'spiky']) assert.ok(types.has(t), 'missing ' + t);
  assert.ok(w.bossSpawn, 'boss');
  assert.ok(w.warp, 'warp star goal');
  assert.ok(w.gateCol > 0, 'arena gate');
  assert.ok(w.gaps.length >= 8, 'plenty of gaps');
  assert.ok(w.checkpoints.length >= 6, 'a checkpoint roughly every stretch');
  assert.ok(w.sections.length >= 7, 'six stretches plus the arena');
  assert.ok(w.items.some((i) => i.kind === 'food') && w.items.some((i) => i.kind === 'oneup'));
  assert.ok(w.winds.length >= 1, 'windy section');
  assert.ok(w.tiles.includes(4), 'star blocks');
  assert.ok(w.tiles.includes(5), 'spikes');
});

// Browser smoke test: opens index.html over file:// in headless Chrome (DevTools protocol,
// no dependencies), plays with real key events, then lets the test bot drive the real page's
// input to the boss and the win screen. Fails on any console error. Screenshots go to .tmp/.
// Run: node tests/smoke.mjs
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { launch, close, key, sleep } from './cdp.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const tmp = path.join(root, '.tmp');
const shots = path.join(tmp, 'screenshots');
fs.mkdirSync(shots, { recursive: true });

const errors = [];
let browser = null;
let failed = false;

async function hold(c, code, ms) {
  await key(c, code, 'keyDown');
  await sleep(ms);
  await key(c, code, 'keyUp');
}

async function step(name, fn) {
  try {
    await fn();
    console.log('ok   ' + name);
  } catch (err) {
    failed = true;
    console.log('FAIL ' + name + '\n     ' + err.message);
    throw err;
  }
}

try {
  browser = await launch(path.join(tmp, 'chrome-profile-' + process.pid));
  const c = browser.client;
  c.on((m) => {
    if (m.method === 'Runtime.exceptionThrown') {
      const d = m.params.exceptionDetails;
      errors.push('exception: ' + (d.exception?.description || d.text));
    }
    if (m.method === 'Runtime.consoleAPICalled' && (m.params.type === 'error' || m.params.type === 'assert')) {
      errors.push('console.' + m.params.type + ': ' + m.params.args.map((a) => a.value ?? a.description).join(' '));
    }
    if (m.method === 'Log.entryAdded' && m.params.entry.level === 'error') {
      errors.push('log: ' + m.params.entry.text + ' ' + (m.params.entry.url || ''));
    }
  });
  await c.send('Runtime.enable');
  await c.send('Log.enable');
  await c.send('Page.enable');
  await c.send('Emulation.setDeviceMetricsOverride', { width: 800, height: 720, deviceScaleFactor: 1, mobile: false });
  const state = (expr) => c.evaluate(`(function(){ var s = KirbyDebug.state(); return ${expr}; })()`);

  await step('page loads over file:// with no errors', async () => {
    await c.send('Page.navigate', { url: pathToFileURL(path.join(root, 'index.html')).href });
    await sleep(1500);
    assert.equal(await c.evaluate('typeof KirbyDebug'), 'object', 'game did not boot');
    assert.equal(await state('s.mode'), 'title');
    const colors = await c.evaluate(`(function(){
      var cv = document.getElementById('game'), d = cv.getContext('2d').getImageData(0, 0, cv.width, cv.height).data, seen = {};
      for (var i = 0; i < d.length; i += 4) seen[d[i] + ',' + d[i + 1] + ',' + d[i + 2]] = 1;
      return Object.keys(seen).length; })()`);
    assert.ok(colors > 8, 'canvas looks blank (' + colors + ' colours)');
    await c.screenshot(path.join(shots, '01-title.png'));
  });

  await step('Space starts the game', async () => {
    await hold(c, 'Space', 80);
    await sleep(600);
    assert.equal(await state('s.mode'), 'playing');
  });

  await step('arrow keys move Kirby right', async () => {
    const x0 = await state('s.player.x');
    await hold(c, 'ArrowRight', 900);
    const x1 = await state('s.player.x');
    assert.ok(x1 > x0 + 20, `x only went ${x0} -> ${x1}`);
    await c.screenshot(path.join(shots, '02-run.png'));
  });

  await step('holding Enter inhales', async () => {
    await key(c, 'Enter', 'keyDown');
    await sleep(300);
    assert.equal(await state('s.player.inhaling'), true);
    await c.screenshot(path.join(shots, '03-inhale.png'));
    await key(c, 'Enter', 'keyUp');
    await sleep(100);
  });

  await step('Space in the air flies', async () => {
    await hold(c, 'Space', 250);
    await sleep(100);
    await hold(c, 'Space', 60);
    await sleep(80);
    await hold(c, 'Space', 60);
    await sleep(120);
    assert.equal(await state('s.player.flying || !!s.player.mouth'), true, 'Kirby should be flying (or have a full mouth)');
    await c.screenshot(path.join(shots, '04-fly.png'));
    await sleep(1200);
  });

  await step('P pauses and resumes', async () => {
    await hold(c, 'KeyP', 60);
    await sleep(150);
    assert.equal(await state('s.mode'), 'paused');
    await c.screenshot(path.join(shots, '05-pause.png'));
    await hold(c, 'KeyP', 60);
    await sleep(150);
    assert.equal(await state('s.mode'), 'playing');
  });

  // Fast-forward with the test bot: it presses keys on the page's real input tracker.
  await c.evaluate(fs.readFileSync(path.join(root, 'tests', 'bot.js'), 'utf8'));
  const runBot = (until, maxTicks) => c.evaluate(`(function(){
    var bot = window.__bot || (window.__bot = KirbyBot.create());
    var s = KirbyDebug.state(), n = 0;
    while (n < ${maxTicks} && !(${until})) { bot.apply(s, KirbyDebug.input); KirbyDebug.tick(); n++; }
    bot.releaseAll(KirbyDebug.input);
    KirbyDebug.draw();
    return { ticks: n, mode: s.mode, x: s.player.x, boss: s.boss && s.boss.state };
  })()`);

  await step('bot reaches the boss arena using key presses', async () => {
    const r = await runBot(`s.arenaLocked && s.boss.state === 'blow' && s.boss.timer > 30`, 60 * 60 * 15);
    assert.ok(r.boss === 'blow', 'did not reach the boss: ' + JSON.stringify(r));
    await c.screenshot(path.join(shots, '06-boss.png'));
  });

  await step('bot beats the boss and wins', async () => {
    const r = await runBot(`s.mode === 'win' && s.screenTimer === 0`, 60 * 60 * 15);
    assert.equal(r.mode, 'win', 'did not win: ' + JSON.stringify(r));
    await sleep(100);
    await c.screenshot(path.join(shots, '07-win.png'));
  });

  await step('no console errors', async () => {
    assert.deepEqual(errors, []);
  });
} catch (err) {
  failed = true;
  if (!String(err.message).includes('FAIL')) console.error(err);
} finally {
  await close(browser);
  if (errors.length) console.log('console errors:\n  ' + errors.join('\n  '));
  console.log(failed ? '\nSMOKE TEST FAILED' : '\nSMOKE TEST PASSED (screenshots in .tmp/screenshots)');
  process.exitCode = failed ? 1 : 0;
}

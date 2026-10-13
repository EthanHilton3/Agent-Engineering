// Browser smoke test: opens index.html in headless Chrome over the DevTools protocol, plays a little
// with real key events, saves screenshots to .tmp/, and fails on any console error.
// Run: node tests/smoke.mjs        (set CHROME_PATH if Chrome is not in a standard place)
import { spawn, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const outDir = path.join(root, '.tmp');
fs.mkdirSync(outDir, { recursive: true });

function findChrome() {
  const candidates = [
    process.env.CHROME_PATH,
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
    process.env.LOCALAPPDATA && path.join(process.env.LOCALAPPDATA, 'Google/Chrome/Application/chrome.exe'),
    'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser',
  ].filter(Boolean);
  const found = candidates.find(p => fs.existsSync(p));
  if (!found) throw new Error('Chrome not found. Set CHROME_PATH.');
  return found;
}

const sleep = ms => new Promise(r => setTimeout(r, ms));
const errors = [];
let chrome = null;
let profile = null;
let ws = null;

function stopChrome() {
  if (!chrome || chrome.exitCode !== null) return Promise.resolve();
  const exited = new Promise(r => chrome.once('exit', r));
  if (process.platform === 'win32') spawnSync('taskkill', ['/pid', String(chrome.pid), '/T', '/F'], { stdio: 'ignore' });
  else chrome.kill('SIGKILL');
  return Promise.race([exited, sleep(5000)]);
}

async function removeProfile() {
  if (!profile) return;
  for (let i = 0; i < 10; i++) {
    try { fs.rmSync(profile, { recursive: true, force: true }); return; } catch (e) { await sleep(300); }
  }
  console.warn('Could not delete profile folder', profile);
}

async function launch() {
  profile = fs.mkdtempSync(path.join(outDir, 'chrome-profile-'));
  chrome = spawn(findChrome(), [
    '--headless=new', '--remote-debugging-port=0', `--user-data-dir=${profile}`,
    '--no-first-run', '--no-default-browser-check', '--disable-extensions', '--mute-audio',
    '--window-size=1280,900', 'about:blank',
  ], { stdio: ['ignore', 'ignore', 'pipe'] });
  const wsUrl = await new Promise((resolve, reject) => {
    let buf = '';
    const timer = setTimeout(() => reject(new Error('Chrome did not start')), 15000);
    chrome.stderr.on('data', d => {
      buf += d;
      const m = buf.match(/DevTools listening on (ws:\/\/[^\s]+)/);
      if (m) { clearTimeout(timer); resolve(m[1]); }
    });
    chrome.once('exit', () => reject(new Error('Chrome exited early')));
  });
  const port = new URL(wsUrl).port;
  const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  const page = targets.find(t => t.type === 'page');
  return page.webSocketDebuggerUrl;
}

function connect(url) {
  let nextId = 0;
  const pending = new Map();
  const listeners = new Map();
  ws = new WebSocket(url);
  ws.onmessage = ev => {
    const msg = JSON.parse(ev.data);
    if (msg.id && pending.has(msg.id)) {
      const { resolve, reject, method } = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) reject(new Error(method + ': ' + msg.error.message)); else resolve(msg.result);
    } else if (msg.method && listeners.has(msg.method)) {
      listeners.get(msg.method).forEach(fn => fn(msg.params));
    }
  };
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++nextId;
    pending.set(id, { resolve, reject, method });
    ws.send(JSON.stringify({ id, method, params }));
  });
  const on = (method, fn) => { if (!listeners.has(method)) listeners.set(method, []); listeners.get(method).push(fn); };
  return new Promise((resolve, reject) => {
    ws.onopen = () => resolve({ send, on });
    ws.onerror = () => reject(new Error('WebSocket failed'));
  });
}

const KEYS = {
  Enter: { key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 },
  Space: { key: ' ', code: 'Space', windowsVirtualKeyCode: 32 },
  ArrowRight: { key: 'ArrowRight', code: 'ArrowRight', windowsVirtualKeyCode: 39 },
  KeyP: { key: 'p', code: 'KeyP', windowsVirtualKeyCode: 80 },
  KeyR: { key: 'r', code: 'KeyR', windowsVirtualKeyCode: 82 },
};

async function main() {
  const { send, on } = await connect(await launch());
  on('Runtime.consoleAPICalled', p => {
    if (p.type === 'error' || p.type === 'assert') errors.push('console.' + p.type + ': ' + p.args.map(a => a.value ?? a.description).join(' '));
  });
  on('Runtime.exceptionThrown', p => errors.push('exception: ' + (p.exceptionDetails.exception?.description || p.exceptionDetails.text)));
  on('Log.entryAdded', p => { if (p.entry.level === 'error') errors.push('log: ' + p.entry.text + ' ' + (p.entry.url || '')); });
  await send('Runtime.enable');
  await send('Log.enable');
  await send('Page.enable');

  const loaded = new Promise(r => on('Page.loadEventFired', r));
  await send('Page.navigate', { url: pathToFileURL(path.join(root, 'index.html')).href });
  await loaded;
  await sleep(600);

  const evaluate = async expr => (await send('Runtime.evaluate', { expression: expr, returnByValue: true })).result.value;
  const state = () => evaluate('(() => { const g = KirbyGame.state; return { mode: g.mode, x: g.player.x, y: g.player.y, pmode: g.player.mode, onGround: g.player.onGround, score: g.score, lives: g.lives }; })()');
  const shot = async name => {
    const { data } = await send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(outDir, name + '.png'), Buffer.from(data, 'base64'));
  };
  const key = (name, type) => send('Input.dispatchKeyEvent', Object.assign({ type }, KEYS[name]));
  const tap = async (name, ms = 60) => { await key(name, 'keyDown'); await sleep(ms); await key(name, 'keyUp'); };
  const check = (cond, msg) => { if (!cond) throw new Error('Check failed: ' + msg); };

  let s = await state();
  check(s.mode === 'title', 'starts on the title screen, got ' + s.mode);
  await shot('1-title');

  await tap('Enter');
  await sleep(200);
  s = await state();
  check(s.mode === 'playing', 'Enter starts the game');
  const startX = s.x;

  await key('ArrowRight', 'keyDown');
  await sleep(1200);
  await shot('2-running');
  s = await state();
  check(s.x > startX + 40, 'holding Right moves Kirby right (' + startX + ' -> ' + s.x + ')');

  await tap('Space', 120);
  await sleep(250);
  let flew = false;
  for (let i = 0; i < 4; i++) {
    await tap('Space', 50);
    await sleep(140);
    if ((await state()).pmode === 'fly') flew = true;
  }
  await shot('3-flying');
  check(flew, 'tapping Space in the air makes Kirby fly');
  await key('ArrowRight', 'keyUp');

  // Let the air out and land, then inhale.
  await tap('Enter');
  for (let i = 0; i < 40 && !(await state()).onGround; i++) await sleep(100);
  await key('Enter', 'keyDown');
  await sleep(400);
  s = await state();
  check(s.pmode === 'inhale' || s.pmode === 'full', 'holding Enter inhales, got ' + s.pmode);
  await shot('4-inhaling');
  await key('Enter', 'keyUp');

  await tap('KeyP');
  await sleep(150);
  check((await state()).mode === 'paused', 'P pauses');
  await shot('5-paused');
  await tap('KeyP');
  await sleep(150);
  check((await state()).mode === 'playing', 'P resumes');

  await tap('KeyR');
  await sleep(200);
  s = await state();
  check(s.mode === 'playing' && Math.abs(s.x - startX) < 1, 'R restarts at the start');

  // A sprite sheet of every sprite, scaled up, for eyeballing the art.
  await evaluate(`(() => {
    const sp = KB.Sprites.build();
    const list = [];
    const add = c => list.push(c.r || c);
    const walk = v => { if (!v) return; if (v.getContext) add(v); else if (v.r) add(v.r); else if (Array.isArray(v)) v.forEach(walk); else Object.values(v).forEach(walk); };
    walk(sp.kirby); ['walker','flyer','hopper','gordo','star','warpStar','pickup','puff'].forEach(k => walk(sp[k]));
    add(sp.tomato); walk(sp.tile); walk(sp.flowers); walk(sp.flag); walk(sp.pip); add(sp.lifeIcon);
    const sheet = document.createElement('canvas'); sheet.width = 1280; sheet.height = 900;
    const c = sheet.getContext('2d'); c.imageSmoothingEnabled = false; c.fillStyle = '#7fb8e0'; c.fillRect(0, 0, 1280, 900);
    let x = 4, y = 4, rowH = 0;
    for (const s of list) { const w = s.width * 5, h = s.height * 5; if (x + w > 1276) { x = 4; y += rowH + 6; rowH = 0; }
      c.drawImage(s, x, y, w, h); x += w + 6; rowH = Math.max(rowH, h); }
    sheet.style.cssText = 'position:fixed;left:0;top:0;z-index:9'; document.body.appendChild(sheet);
  })()`);
  await sleep(100);
  await shot('6-sprites');

  if (errors.length) throw new Error('Console errors:\n' + errors.join('\n'));
  console.log('smoke test passed; screenshots in .tmp/');
}

let failed = false;
try {
  await main();
} catch (e) {
  failed = true;
  console.error(e.message);
  if (errors.length) console.error(errors.join('\n'));
} finally {
  try { ws && ws.close(); } catch (e) { /* already closed */ }
  await stopChrome();
  await removeProfile();
}
process.exit(failed ? 1 : 0);

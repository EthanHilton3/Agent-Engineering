// Minimal headless-Chrome driver over the DevTools protocol. No dependencies:
// uses child_process, fetch and Node's built-in WebSocket (Node 22+).
import { spawn, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export function findChrome() {
  const local = process.env.LOCALAPPDATA || '';
  const candidates = [
    process.env.CHROME_PATH,
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
    local && path.join(local, 'Google/Chrome/Application/chrome.exe'),
    'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
    'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser'
  ];
  return candidates.find((p) => p && fs.existsSync(p));
}

class Client {
  constructor(ws) {
    this.ws = ws;
    this.nextId = 0;
    this.pending = new Map();
    this.listeners = [];
    ws.addEventListener('message', (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject } = this.pending.get(msg.id);
        this.pending.delete(msg.id);
        if (msg.error) reject(new Error(msg.error.message)); else resolve(msg.result);
      } else if (msg.method) {
        this.listeners.forEach((fn) => fn(msg));
      }
    });
  }
  send(method, params = {}) {
    const id = ++this.nextId;
    this.ws.send(JSON.stringify({ id, method, params }));
    return new Promise((resolve, reject) => this.pending.set(id, { resolve, reject }));
  }
  on(fn) { this.listeners.push(fn); }
  async evaluate(expression) {
    const r = await this.send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    if (r.exceptionDetails) throw new Error('Page evaluate failed: ' + (r.exceptionDetails.exception?.description || r.exceptionDetails.text));
    return r.result.value;
  }
  async screenshot(file) {
    const r = await this.send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(file, Buffer.from(r.data, 'base64'));
  }
}

const KEYS = {
  Space: { key: ' ', vk: 32 }, Enter: { key: 'Enter', vk: 13 }, ArrowLeft: { key: 'ArrowLeft', vk: 37 },
  ArrowRight: { key: 'ArrowRight', vk: 39 }, KeyP: { key: 'p', vk: 80 }, KeyM: { key: 'm', vk: 77 },
  KeyR: { key: 'r', vk: 82 }, Escape: { key: 'Escape', vk: 27 }
};

export async function key(client, code, type) {
  const k = KEYS[code];
  await client.send('Input.dispatchKeyEvent', {
    type, code, key: k.key, windowsVirtualKeyCode: k.vk, nativeVirtualKeyCode: k.vk,
    text: type === 'keyDown' && k.key === ' ' ? ' ' : undefined
  });
}

// Launches headless Chrome with a throwaway profile and returns a connected page client.
export async function launch(profileDir, { width = 900, height = 760 } = {}) {
  const exe = findChrome();
  if (!exe) throw new Error('Chrome/Edge not found. Set CHROME_PATH.');
  fs.rmSync(profileDir, { recursive: true, force: true });
  fs.mkdirSync(profileDir, { recursive: true });
  const proc = spawn(exe, [
    '--headless=new', '--remote-debugging-port=0', `--user-data-dir=${profileDir}`,
    '--no-first-run', '--no-default-browser-check', '--disable-extensions', '--disable-sync',
    '--disable-background-networking', '--mute-audio', '--autoplay-policy=no-user-gesture-required',
    `--window-size=${width},${height}`, 'about:blank'
  ], { stdio: 'ignore' });
  const browser = { proc, profileDir, client: null };
  try {
    const portFile = path.join(profileDir, 'DevToolsActivePort');
    let port = 0;
    for (let i = 0; i < 200 && !port; i++) {
      if (fs.existsSync(portFile)) port = Number(fs.readFileSync(portFile, 'utf8').split('\n')[0]) || 0;
      if (!port) await sleep(100);
    }
    if (!port) throw new Error('Chrome did not open a DevTools port');
    let page = null;
    for (let i = 0; i < 50 && !page; i++) {
      const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
      page = list.find((t) => t.type === 'page');
      if (!page) await sleep(100);
    }
    const ws = new WebSocket(page.webSocketDebuggerUrl);
    await new Promise((res, rej) => { ws.addEventListener('open', res, { once: true }); ws.addEventListener('error', rej, { once: true }); });
    browser.client = new Client(ws);
    return browser;
  } catch (err) {
    await close(browser);
    throw err;
  }
}

// Always stops Chrome (and its child processes) and deletes the throwaway profile.
export async function close(browser) {
  if (!browser) return;
  try { if (browser.client) { await Promise.race([browser.client.send('Browser.close'), sleep(1500)]); browser.client.ws.close(); } } catch { /* already gone */ }
  const { proc } = browser;
  if (proc && proc.exitCode === null) {
    if (process.platform === 'win32') spawnSync('taskkill', ['/pid', String(proc.pid), '/T', '/F'], { stdio: 'ignore' });
    else proc.kill('SIGKILL');
  }
  for (let i = 0; i < 30; i++) {
    try { fs.rmSync(browser.profileDir, { recursive: true, force: true }); return; } catch { await sleep(200); }
  }
}

export { sleep };

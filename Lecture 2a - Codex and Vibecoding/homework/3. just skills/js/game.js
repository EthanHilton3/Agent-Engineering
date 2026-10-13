'use strict';
// Game flow: states, spawning, camera, HUD, screens and the main loop.

const G = {
  state: 'title', stateT: 0, frame: 0,
  level: null, kirby: null, boss: null, ents: [], parts: [], pops: [],
  camX: 0, shake: 0, fade: 0, banner: null,
  score: 0, lives: 3, checkpoint: 0, inArena: false, flagAnim: 0, winBonus: 0, warp: null,
  addScore(n, x, y) { G.score += n; if (x !== undefined) G.pops.push({ x, y, text: String(n), t: 0 }); },
  showBanner(text) { G.banner = { text, t: 0 }; },
};

const CHECKPOINTS = [2 * TILE + 2, FLAG_TX * TILE + 24, 186 * TILE];

function spawnEntities() {
  G.ents = [];
  for (const s of G.level.spawns) {
    let e;
    switch (s.kind) {
      case 'walker': e = new Walker(); break;
      case 'flyer': e = new Flyer(); break;
      case 'shooter': e = new Shooter(); break;
      case 'hothead': e = new HotHead(); break;
      case 'spiky': e = new Spiky(s.opts); break;
      case 'boulder': G.ents.push(new Boulder(s.tx, s.ty)); continue;
      case 'food': case 'tomato': e = new Food(0, 0, s.kind); break;
    }
    G.ents.push(e.onCell(s.tx, s.ty));
  }
}

// (Re)builds the level and puts Kirby at the current checkpoint. Enemies and blocks reset; score doesn't.
function loadAttempt() {
  G.level = new Level();
  spawnEntities();
  G.parts = []; G.pops = []; G.banner = null; G.shake = 0;
  G.boss = new Boss();
  G.kirby = new Kirby(CHECKPOINTS[G.checkpoint], 10 * TILE - 13);
  G.inArena = false;
  if (G.checkpoint === 2) enterArena();
  G.camX = cameraTarget();
  G.state = 'playing'; G.stateT = 0; G.fade = 1;
}

function startGame() {
  G.score = 0; G.lives = 3; G.checkpoint = 0; G.flagAnim = 0;
  loadAttempt();
  Sound.start();
}

function enterArena() {
  const k = G.kirby;
  G.inArena = true; G.checkpoint = 2;
  k.x = 186 * TILE; k.y = 10 * TILE - k.h; k.vx = 0; k.vy = 0; k.facing = 1;
  k.puffed = false; k.inhaling = false; k.firing = false; k.straining = false;
  G.ents = G.ents.filter((e) => e.x < 183 * TILE);
  G.boss = new Boss();
  G.boss.start();
  G.showBanner('WHISPY WOODS');
}

function cameraTarget() {
  if (G.inArena) return ARENA.camX;
  const k = G.kirby;
  return clamp(k.cx - VIEW_W / 2 + k.facing * 20, 0, CAM_MAX);
}

// ---------- Update ----------
function update() {
  G.frame++; G.stateT++;
  if (Input.hit('mute')) G.showBanner(Sound.toggleMute() ? 'SOUND OFF' : 'SOUND ON');
  if (G.fade > 0 && G.state === 'playing') G.fade = Math.max(0, G.fade - 0.06);

  switch (G.state) {
    case 'title':
      if (Input.hit('action') || Input.hit('jump')) startGame();
      break;
    case 'playing': updatePlaying(); break;
    case 'paused':
      if (Input.hit('pause')) { G.state = 'playing'; Sound.pause(); }
      break;
    case 'door':
      updateFx();
      G.fade = G.stateT < 24 ? G.stateT / 24 : Math.max(0, 1 - (G.stateT - 24) / 24);
      if (G.stateT === 24) { enterArena(); G.camX = ARENA.camX; }
      if (G.stateT >= 48) { G.state = 'playing'; G.fade = 0; }
      break;
    case 'dying':
      G.kirby.update();
      updateFx();
      if (G.stateT >= 110) {
        G.lives--;
        if (G.lives > 0) loadAttempt();
        else { G.state = 'gameover'; G.stateT = 0; Sound.gameOver(); }
      }
      break;
    case 'winning': {
      const w = G.warp, k = G.kirby;
      w.t++;
      if (G.stateT > 30) { w.x += 0.5 + (G.stateT - 30) * 0.05; w.y -= 0.6 + (G.stateT - 30) * 0.035; }
      else w.y = w.baseY + Math.sin(w.t * 0.3) * 2;
      k.x = w.cx - k.w / 2; k.y = w.y - k.h + 6; k.t++;
      if (G.stateT % 2 === 0) addPart({ x: w.x + rand(0, 8), y: w.cy + rand(-4, 6), vx: -1, life: 24, col: pick([PAL.yellow, PAL.white, PAL.pink]), size: 2 });
      updateFx();
      if (G.stateT === 150) {
        G.winBonus = G.lives * 5000;
        G.score += G.winBonus;
        G.state = 'win'; G.stateT = 0;
        Sound.win();
      }
      break;
    }
    case 'gameover':
    case 'win':
      if (G.stateT > 40 && Input.hit('action')) startGame();
      break;
  }
}

function updateFx() {
  for (const p of G.parts) {
    p.t++; p.vy += p.g; p.x += p.vx; p.y += p.vy;
    if (p.drag !== 1) { p.vx *= p.drag; p.vy *= p.drag; }
  }
  G.parts = G.parts.filter((p) => p.t < p.life);
  for (const p of G.pops) { p.t++; p.y -= 0.5; }
  G.pops = G.pops.filter((p) => p.t < 45);
  if (G.banner && ++G.banner.t > 110) G.banner = null;
  if (G.shake > 0) G.shake--;
}

function updatePlaying() {
  if (Input.hit('pause')) { G.state = 'paused'; Sound.stopLoops(); Sound.pause(); return; }
  const k = G.kirby;
  k.update();
  if (G.state !== 'playing') { updateFx(); return; } // Kirby died this step

  for (let i = 0, n = G.ents.length; i < n; i++) {
    const e = G.ents[i];
    if (e.dead) continue;
    if (e.caughtTimer > 0) {
      e.caughtTimer--; e.t++;
      if (e.caughtTimer === 0) { e.pullT = 0; e.onRelease(); }
      continue;
    }
    e.update();
    if (e.y > LH * TILE + 40) e.dead = true;
  }
  G.ents = G.ents.filter((e) => !e.dead);
  if (G.inArena) G.boss.update();

  // Kirby vs the world
  const hb = { x: k.x + 1, y: k.y + 2, w: k.w - 2, h: k.h - 2 };
  for (const e of G.ents) {
    if (e.dead || k.dead) continue;
    if (e instanceof Food) { if (overlap(k, e)) e.collect(k); }
    else if (e instanceof WarpStar) {
      if (e.arrived && overlap(k, e)) {
        G.state = 'winning'; G.stateT = 0; G.warp = e;
        k.riding = true; k.facing = 1; k.puffed = false; k.held = null;
        Sound.stopLoops(); Sound.star();
        return;
      }
    } else if (e.harmful && e.caughtTimer === 0 && overlap(hb, e)) k.damage(e.cx);
  }
  if (G.state !== 'playing') { updateFx(); return; }

  // checkpoint flag
  if (G.checkpoint < 1 && k.x > FLAG_TX * TILE) {
    G.checkpoint = 1;
    Sound.checkpoint();
    G.showBanner('CHECKPOINT!');
  }
  if (G.checkpoint >= 1) G.flagAnim = Math.min(1, G.flagAnim + 0.04);

  // boss door
  if (!G.inArena && k.onGround && overlap(k, { x: DOOR.x + 4, y: DOOR.y, w: 8, h: DOOR.h })) {
    G.state = 'door'; G.stateT = 0;
    k.inhaling = false; k.firing = false; Sound.stopLoops();
    Sound.door();
  }

  // camera
  if (G.inArena) G.camX = ARENA.camX;
  else G.camX += (cameraTarget() - G.camX) * 0.15;

  updateFx();
}

// ---------- Rendering ----------
const canvas = document.getElementById('game');
const ctx = canvas.getContext('2d');
ctx.imageSmoothingEnabled = false;

function drawWorld(camX) {
  const cam = Math.round(camX);
  let sx = 0, sy = 0;
  if (G.shake > 0) { const m = Math.min(3, Math.ceil(G.shake / 3)); sx = Math.round(rand(-m, m)); sy = Math.round(rand(-m, m)); }
  ctx.save();
  ctx.beginPath(); ctx.rect(0, 0, VIEW_W, VIEW_H); ctx.clip();
  BG.draw(ctx, cam, G.frame);
  ctx.translate(-cam + sx, sy);
  const lv = G.level, x0 = Math.max(0, cam - 8);
  ctx.drawImage(lv.canvas, x0, 0, VIEW_W + 16, VIEW_H, x0, 0, VIEW_W + 16, VIEW_H);

  for (const s of lv.signs) if (s.x < cam + VIEW_W && s.x + 200 > cam) drawText(ctx, s.text, s.x, s.y, PAL.white, { shadow: PAL.ink });

  // checkpoint flag
  const fx = FLAG_TX * TILE + 4, top = 10 * TILE - 46;
  ctx.fillStyle = PAL.ink; ctx.fillRect(fx - 1, top, 4, 46);
  ctx.fillStyle = PAL.white; ctx.fillRect(fx, top, 2, 46);
  blit(ctx, SPR.tinyStar, fx - 2, top - 5);
  blit(ctx, G.checkpoint >= 1 ? SPR.flagOn : SPR.flagOff, fx + 2, Math.round(top + 30 - G.flagAnim * 28));

  // boss door
  blit(ctx, SPR.door, DOOR.x - 2, DOOR.y - 2);
  blit(ctx, SPR.star[(G.frame >> 3) % 4], DOOR.x + 2, DOOR.y - 16);

  if (cam + VIEW_W > ARENA.camX) G.boss.draw(ctx);
  for (const e of G.ents) e.draw(ctx);
  G.kirby.draw(ctx);
  drawParts();
  if (cam + VIEW_W > ARENA.camX - 20) blit(ctx, SPR.canopy, ARENA.camX - 14, -22);
  for (const p of G.pops) drawText(ctx, p.text, p.x, p.y, p.t % 8 < 4 ? PAL.white : PAL.yellow, { align: 'center', shadow: PAL.ink });
  ctx.restore();

  if (G.banner && !(G.banner.t > 90 && (G.banner.t >> 2) & 1)) {
    drawText(ctx, G.banner.text, VIEW_W / 2, 40, PAL.yellow, { scale: 2, align: 'center', outline: PAL.ink });
  }
}

function drawParts() {
  for (const p of G.parts) {
    const k = p.t / p.life, x = Math.round(p.x), y = Math.round(p.y);
    switch (p.type) {
      case 'dot': ctx.fillStyle = p.col; ctx.fillRect(x, y, p.size, p.size); break;
      case 'wind': ctx.fillStyle = p.col; ctx.fillRect(x, y, 3, 1); break;
      case 'leaf': ctx.fillStyle = p.col; ctx.fillRect(x + Math.round(Math.sin(p.t * 0.2) * 2), y, 2, 2); break;
      case 'star': blit(ctx, SPR.tinyStar, x, y); break;
      case 'cloud': blit(ctx, SPR.puff[k < 0.5 ? 0 : 1], x, y); break;
      case 'flame': {
        ctx.fillStyle = k < 0.3 ? PAL.yellow : k < 0.6 ? PAL.orange : k < 0.85 ? PAL.red : PAL.redD;
        const s = Math.max(1, Math.round(p.size * (1 - k * 0.6)));
        ctx.fillRect(x - (s >> 1), y - (s >> 1), s, s);
        break;
      }
    }
  }
}

function drawHUD() {
  const k = G.kirby, y1 = 197, y2 = 211;
  ctx.fillStyle = PAL.navy; ctx.fillRect(0, VIEW_H, VIEW_W, SCREEN_H - VIEW_H);
  ctx.fillStyle = PAL.ink; ctx.fillRect(0, VIEW_H, VIEW_W, 1);
  ctx.fillStyle = PAL.pinkD; ctx.fillRect(0, VIEW_H + 1, VIEW_W, 1);
  const sh = { shadow: PAL.ink };
  drawText(ctx, 'KIRBY', 6, y1, PAL.pink, sh);
  for (let i = 0; i < k.maxHp; i++) {
    const full = i < k.hp, low = k.hp <= 2 && (G.frame >> 3) & 1;
    blit(ctx, full ? (low ? SPR.pipLow : SPR.pip) : SPR.pipEmpty, 40 + i * 8, y1 - 1);
  }
  drawText(ctx, 'SCORE', 144, y1, PAL.white, sh);
  drawText(ctx, String(G.score).padStart(7, '0'), 250, y1, PAL.yellow, { align: 'right', shadow: PAL.ink });

  blit(ctx, SPR.face, 5, y2 - 2);
  drawText(ctx, 'X' + Math.max(0, G.lives), 17, y2, PAL.white, sh);
  const fire = k.ability === 'fire';
  blit(ctx, fire ? SPR.fireIcon : SPR.normalIcon, 40, y2 - 2);
  drawText(ctx, fire ? 'FIRE' : 'NORMAL', 52, y2, fire ? PAL.orange : PAL.gray, sh);

  const b = G.boss;
  if (G.inArena && b && b.state !== 'sleep' && b.state !== 'dead') {
    drawText(ctx, 'WHISPY', 100, y2, PAL.green, sh);
    const bx = 142, bw = 108;
    ctx.fillStyle = PAL.ink; ctx.fillRect(bx - 1, y2 - 1, bw + 2, 9);
    ctx.fillStyle = PAL.purpleD; ctx.fillRect(bx, y2, bw, 7);
    const w = Math.round(bw * (b.hp / b.maxHp) * b.bar);
    ctx.fillStyle = b.flash > 0 && (b.flash >> 1) & 1 ? PAL.white : PAL.red; ctx.fillRect(bx, y2, w, 7);
    ctx.fillStyle = PAL.orange; ctx.fillRect(bx, y2, w, 2);
  } else {
    let hint = '';
    if (k.held) hint = 'ENTER SPIT  DOWN SWALLOW';
    else if (k.puffed) hint = 'ENTER: EXHALE';
    else if (fire) hint = 'ENTER FIRE  SHIFT DROP';
    drawText(ctx, hint, 250, y2, PAL.gray, { align: 'right' });
  }
}

function drawControlsPanel(y) {
  ctx.fillStyle = PAL.navy; ctx.fillRect(10, y, VIEW_W - 20, 66);
  ctx.fillStyle = PAL.pinkD; ctx.fillRect(10, y, VIEW_W - 20, 1); ctx.fillRect(10, y + 65, VIEW_W - 20, 1);
  const rows = [
    ['MOVE', 'ARROWS OR A / D'],
    ['JUMP / FLY', 'SPACE (TAP IN AIR)'],
    ['INHALE', 'HOLD ENTER'],
    ['SPIT / EXHALE', 'ENTER     SWALLOW: DOWN'],
    ['DROP ABILITY', 'SHIFT  PAUSE P  MUTE M'],
  ];
  rows.forEach(([a, b], i) => {
    drawText(ctx, a, 18, y + 5 + i * 12, PAL.pink);
    drawText(ctx, b, 100, y + 5 + i * 12, PAL.white);
  });
}

function drawTitle() {
  const cam = Math.round(300 + Math.sin(G.frame * 0.003) * 300);
  ctx.save();
  BG.draw(ctx, cam, G.frame);
  ctx.translate(-cam, 32);
  ctx.drawImage(G.level.canvas, cam, 0, VIEW_W, VIEW_H, cam, 0, VIEW_W, VIEW_H);
  ctx.restore();
  drawText(ctx, 'KIRBY', VIEW_W / 2, 14, PAL.pink, { scale: 4, align: 'center', outline: PAL.ink, ow: 2, shadow: PAL.purpleD });
  drawText(ctx, 'PIXEL QUEST', VIEW_W / 2, 50, PAL.yellow, { scale: 2, align: 'center', outline: PAL.ink });
  const K = SPR.kirby, f = (G.frame >> 3) & 1 ? K.fly0 : K.fly1;
  blit(ctx, f.c, VIEW_W / 2 - 12, 74 + Math.round(Math.sin(G.frame * 0.06) * 4));
  if ((G.frame >> 5) & 1) drawText(ctx, 'PRESS ENTER TO START', VIEW_W / 2, 104, PAL.white, { align: 'center', outline: PAL.ink });
  drawControlsPanel(120);
  drawText(ctx, 'SOUND: ' + (Sound.muted ? 'OFF' : 'ON') + ' (M)', VIEW_W / 2, 194, PAL.white, { align: 'center', outline: PAL.ink });
}

function dim(a) { ctx.globalAlpha = a; ctx.fillStyle = PAL.ink; ctx.fillRect(0, 0, VIEW_W, SCREEN_H); ctx.globalAlpha = 1; }

function render() {
  ctx.fillStyle = PAL.ink;
  ctx.fillRect(0, 0, VIEW_W, SCREEN_H);
  if (G.state === 'title') { drawTitle(); return; }
  drawWorld(G.camX);
  drawHUD();
  if (G.fade > 0) { ctx.globalAlpha = G.fade; ctx.fillStyle = PAL.ink; ctx.fillRect(0, 0, VIEW_W, VIEW_H); ctx.globalAlpha = 1; }

  if (G.state === 'paused') {
    dim(0.65);
    drawText(ctx, 'PAUSED', VIEW_W / 2, 30, PAL.yellow, { scale: 3, align: 'center', outline: PAL.ink });
    drawControlsPanel(70);
    drawText(ctx, 'PRESS P TO RESUME', VIEW_W / 2, 150, PAL.white, { align: 'center' });
  } else if (G.state === 'gameover') {
    dim(Math.min(0.8, G.stateT / 40));
    drawText(ctx, 'GAME OVER', VIEW_W / 2, 60, PAL.red, { scale: 3, align: 'center', outline: PAL.ink });
    drawText(ctx, 'SCORE ' + G.score, VIEW_W / 2, 100, PAL.white, { align: 'center' });
    blit(ctx, SPR.kirby.hurt.c, VIEW_W / 2 - 12, 112);
    if (G.stateT > 40 && (G.frame >> 5) & 1) drawText(ctx, 'PRESS ENTER TO TRY AGAIN', VIEW_W / 2, 150, PAL.yellow, { align: 'center' });
  } else if (G.state === 'win') {
    dim(Math.min(0.75, G.stateT / 40));
    drawText(ctx, 'YOU WIN!', VIEW_W / 2, 30, PAL.yellow, { scale: 3, align: 'center', outline: PAL.ink });
    const K = SPR.kirby, f = (G.frame >> 4) & 1 ? K.swallow : K.jump;
    blit(ctx, f.c, VIEW_W / 2 - 12, 62 - ((G.frame >> 4) & 1 ? 0 : 4));
    drawText(ctx, 'LIFE BONUS  ' + G.lives + ' X 5000 = ' + G.winBonus, VIEW_W / 2, 98, PAL.white, { align: 'center' });
    drawText(ctx, 'FINAL SCORE  ' + G.score, VIEW_W / 2, 114, PAL.pink, { scale: 1, align: 'center' });
    if (G.stateT > 40 && (G.frame >> 5) & 1) drawText(ctx, 'PRESS ENTER TO PLAY AGAIN', VIEW_W / 2, 150, PAL.yellow, { align: 'center' });
  }
}

// ---------- Boot & loop ----------
function resize() {
  const strip = document.getElementById('controls').offsetHeight + 40;
  const s = Math.max(1, Math.floor(Math.min((innerWidth - 24) / VIEW_W, (innerHeight - strip) / SCREEN_H)));
  canvas.style.width = VIEW_W * s + 'px';
  canvas.style.height = SCREEN_H * s + 'px';
}

buildSprites();
BG.build();
G.level = new Level();
addEventListener('resize', resize);
resize();

const STEP = 1000 / 60;
let last = performance.now(), acc = 0;
function loop(now) {
  acc += Math.min(now - last, 250);
  last = now;
  let n = 0;
  while (acc >= STEP && n < 5) { update(); Input.endStep(); acc -= STEP; n++; }
  if (n === 5) acc = 0;
  render();
  requestAnimationFrame(loop);
}
requestAnimationFrame(loop);

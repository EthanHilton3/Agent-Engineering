// Wires everything together: fixed 60 Hz updates, drawing on every animation frame.
(function () {
  const C = KB.C;
  const canvas = document.getElementById('game');
  const ctx = canvas.getContext('2d');
  canvas.width = C.VIEW_W;
  canvas.height = C.VIEW_H;

  const sprites = KB.Sprites.build();
  const renderer = KB.Render.create(ctx, sprites);
  const input = KB.Input.create();
  const game = KB.Game.create();
  renderer.snapCamera(game);

  const HI_KEY = 'kirby-dream-dash-hiscore';
  try { renderer.hiScore = Number(localStorage.getItem(HI_KEY)) || 0; } catch (e) { renderer.hiScore = 0; }
  function saveHiScore() {
    if (game.score <= renderer.hiScore) return;
    renderer.hiScore = game.score;
    try { localStorage.setItem(HI_KEY, String(game.score)); } catch (e) { /* storage blocked: keep it in memory */ }
  }

  KB.Input.attach(window, input, () => KB.Audio.unlock());

  // Integer scaling keeps every pixel square and sharp.
  function fit() {
    const reserved = document.getElementById('help').offsetHeight + 24;
    const scale = Math.max(1, Math.floor(Math.min(window.innerWidth / C.VIEW_W, (window.innerHeight - reserved) / C.VIEW_H)));
    canvas.style.width = C.VIEW_W * scale + 'px';
    canvas.style.height = C.VIEW_H * scale + 'px';
  }
  window.addEventListener('resize', fit);
  fit();

  const MAX_FRAME = 0.25;  // after a long stall, don't try to catch up more than this
  let acc = 0;
  let last = performance.now();

  function frame(now) {
    acc += Math.min(MAX_FRAME, (now - last) / 1000);
    last = now;
    while (acc >= C.DT) {
      const snap = KB.Input.snapshot(input);
      if (snap.mutePressed) renderer.muted = KB.Audio.toggleMute();
      KB.Game.update(game, snap);
      renderer.onEvents(game.events);
      KB.Audio.onEvents(game.events);
      if (game.mode !== 'paused') renderer.step(game);
      if (game.events.some(e => e.type === 'win' || e.type === 'gameover')) saveHiScore();
      acc -= C.DT;
    }
    KB.Audio.setInhale(game.mode === 'playing' && game.player.mode === 'inhale');
    renderer.draw(game);
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);

  // Read-only handle for the browser smoke test and for poking around in the console.
  window.KirbyGame = { get state() { return game; } };
})();

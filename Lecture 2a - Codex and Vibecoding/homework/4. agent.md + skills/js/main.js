// Boots the game: fixed 60 Hz logic updates, rendering on requestAnimationFrame.
(function () {
  'use strict';
  var C = CONST;
  var STEP_MS = 1000 / C.TICKS_PER_SECOND;
  var BEST_KEY = 'kirby-dream-meadows-best';

  function loadBest() {
    try { return Number(localStorage.getItem(BEST_KEY)) || 0; } catch (e) { return 0; }
  }
  function saveBest(v) {
    try { localStorage.setItem(BEST_KEY, String(v)); } catch (e) { /* storage blocked: best score is per session */ }
  }

  var canvas = document.getElementById('game');
  canvas.width = C.VIEW_W;
  canvas.height = C.VIEW_H;
  var ctx = canvas.getContext('2d');
  ctx.imageSmoothingEnabled = false;

  Sprites.init();
  Renderer.init(ctx);

  var input = KirbyInput.create();
  KirbyInput.attach(input, window, GameAudio.unlock);
  var state = Game.create(LEVEL_1, { best: loadBest() });
  Renderer.snapCamera(state);

  function musicFor(s) {
    if (s.mode === 'dying' || s.mode === 'gameover' || s.mode === 'win') return null;
    var b = s.boss;
    if (s.arenaLocked && b && b.state !== 'dead' && b.state !== 'dying') return 'boss';
    return 'level';
  }

  function tick() {
    var snap = input.poll();
    if (snap.mutePressed) GameAudio.toggleMute();
    Game.update(state, snap);
    for (var i = 0; i < state.events.length; i++) {
      var ev = state.events[i];
      GameAudio.play(ev);
      Renderer.onEvent(ev, state);
      if (ev.type === 'win' || ev.type === 'gameOver') saveBest(state.best);
    }
    GameAudio.setMusic(musicFor(state));
    GameAudio.setDucked(state.mode === 'paused' || state.mode === 'confirm' || state.mode === 'title');
    Renderer.tick(state);
  }

  var acc = 0, last = performance.now();
  function frame(now) {
    acc += Math.min(now - last, 250);
    last = now;
    var steps = 0;
    while (acc >= STEP_MS && steps < C.MAX_STEPS_PER_FRAME) {
      tick();
      acc -= STEP_MS;
      steps++;
    }
    if (steps === C.MAX_STEPS_PER_FRAME) acc = 0;
    Renderer.draw(state, { muted: GameAudio.isMuted() });
    requestAnimationFrame(frame);
  }

  function resize() {
    var scale = Math.max(1, Math.floor(Math.min(window.innerWidth / C.VIEW_W, (window.innerHeight - 32) / C.VIEW_H)));
    canvas.style.width = C.VIEW_W * scale + 'px';
    canvas.style.height = C.VIEW_H * scale + 'px';
  }
  window.addEventListener('resize', resize);
  resize();

  // Pause automatically when the window loses focus.
  window.addEventListener('blur', function () { Game.pause(state); });

  // Hook used by the browser smoke test to step the real game with simulated keys.
  window.KirbyDebug = {
    state: function () { return state; },
    input: input,
    tick: tick,
    draw: function () { Renderer.draw(state, { muted: GameAudio.isMuted() }); }
  };

  requestAnimationFrame(frame);
})();

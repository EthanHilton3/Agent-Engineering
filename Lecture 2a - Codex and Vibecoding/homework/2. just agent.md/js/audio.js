// Little chiptune sound effects and a music loop, synthesised with Web Audio. No sound files.
var KB = (typeof KB !== 'undefined') ? KB : {};

KB.Audio = (function () {
  let ac = null, master = null, sfxBus = null, musicBus = null;
  let muted = false, inhaleSrc = null, musicTimer = null, nextNote = 0, step = 0;

  function unlock() {
    if (!ac) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return;
      ac = new AC();
      master = ac.createGain(); master.gain.value = muted ? 0 : 0.5; master.connect(ac.destination);
      sfxBus = ac.createGain(); sfxBus.gain.value = 0.5; sfxBus.connect(master);
      musicBus = ac.createGain(); musicBus.gain.value = 0.16; musicBus.connect(master);
      startMusic();
    }
    if (ac.state === 'suspended') ac.resume();
  }

  function tone(freq, dur, type, vol, slideTo, delay, bus) {
    if (!ac) return;
    const t = ac.currentTime + (delay || 0);
    const o = ac.createOscillator(), g = ac.createGain();
    o.type = type || 'square';
    o.frequency.setValueAtTime(freq, t);
    if (slideTo) o.frequency.exponentialRampToValueAtTime(slideTo, t + dur);
    g.gain.setValueAtTime(vol || 0.3, t);
    g.gain.exponentialRampToValueAtTime(0.001, t + dur);
    o.connect(g); g.connect(bus || sfxBus);
    o.start(t); o.stop(t + dur + 0.02);
  }

  function noiseBuffer(seconds) {
    const buf = ac.createBuffer(1, Math.floor(ac.sampleRate * seconds), ac.sampleRate);
    const d = buf.getChannelData(0);
    for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    return buf;
  }
  function noise(dur, vol, freq) {
    if (!ac) return;
    const src = ac.createBufferSource(); src.buffer = noiseBuffer(dur);
    const f = ac.createBiquadFilter(); f.type = 'bandpass'; f.frequency.value = freq || 1200;
    const g = ac.createGain(); const t = ac.currentTime;
    g.gain.setValueAtTime(vol, t); g.gain.exponentialRampToValueAtTime(0.001, t + dur);
    src.connect(f); f.connect(g); g.connect(sfxBus); src.start();
  }
  function arpeggio(notes, len, type, vol) { notes.forEach((n, i) => tone(n, len * 1.6, type, vol, null, i * len)); }

  const SFX = {
    jump: () => tone(330, 0.14, 'square', 0.18, 660),
    flap: () => tone(520, 0.08, 'triangle', 0.3, 700),
    tired: () => tone(200, 0.1, 'triangle', 0.2, 150),
    exhale: () => noise(0.18, 0.35, 900),
    swallow: () => { tone(500, 0.08, 'square', 0.2, 200); tone(250, 0.12, 'triangle', 0.3, 120, 0.06); },
    spit: () => { noise(0.08, 0.3, 2000); tone(900, 0.15, 'square', 0.18, 1400); },
    defeat: () => arpeggio([784, 1047, 1319], 0.05, 'square', 0.15),
    blockBreak: () => noise(0.15, 0.4, 500),
    blockPop: () => noise(0.12, 0.3, 500),
    clink: () => tone(1800, 0.06, 'square', 0.15),
    hurt: () => tone(400, 0.25, 'sawtooth', 0.2, 120),
    die: () => arpeggio([660, 523, 440, 330, 262], 0.12, 'square', 0.2),
    pickup: () => arpeggio([1319, 1568], 0.05, 'square', 0.12),
    heal: () => arpeggio([523, 659, 784, 1047], 0.06, 'triangle', 0.3),
    checkpoint: () => arpeggio([523, 784, 1047], 0.08, 'square', 0.15),
    hop: () => tone(260, 0.08, 'triangle', 0.15, 420),
    win: () => arpeggio([523, 659, 784, 1047, 784, 1047, 1319], 0.11, 'square', 0.2),
    gameover: () => arpeggio([392, 330, 262, 196], 0.22, 'triangle', 0.3),
    start: () => arpeggio([523, 784], 0.08, 'square', 0.15),
  };

  function onEvents(events) {
    if (!ac) return;
    for (const ev of events) if (SFX[ev.type]) SFX[ev.type](ev);
  }

  // Looping rushing-air sound while Kirby inhales.
  function setInhale(on) {
    if (!ac) return;
    if (on && !inhaleSrc) {
      const src = ac.createBufferSource(); src.buffer = noiseBuffer(1); src.loop = true;
      const f = ac.createBiquadFilter(); f.type = 'bandpass'; f.frequency.value = 700; f.Q.value = 0.8;
      const lfo = ac.createOscillator(); lfo.frequency.value = 6;
      const lfoGain = ac.createGain(); lfoGain.gain.value = 250;
      lfo.connect(lfoGain); lfoGain.connect(f.frequency);
      const g = ac.createGain(); g.gain.value = 0.25;
      src.connect(f); f.connect(g); g.connect(sfxBus);
      src.start(); lfo.start();
      inhaleSrc = { src, lfo };
    } else if (!on && inhaleSrc) {
      inhaleSrc.src.stop(); inhaleSrc.lfo.stop();
      inhaleSrc = null;
    }
  }

  // A cheerful 2-bar loop: melody over a bouncing bass. Scheduled a little ahead of time.
  const MELODY = [72, 0, 76, 79, 77, 76, 74, 0, 72, 74, 76, 0, 79, 0, 76, 0, 77, 0, 74, 77, 76, 74, 72, 0, 74, 76, 74, 71, 72, 0, 0, 0];
  const BASS = [48, 55, 48, 55, 43, 50, 43, 50, 45, 52, 45, 52, 43, 50, 43, 47];
  const STEP = 0.14;
  const midi = n => 440 * Math.pow(2, (n - 69) / 12);
  function startMusic() {
    nextNote = ac.currentTime + 0.1;
    musicTimer = setInterval(() => {
      while (nextNote < ac.currentTime + 0.3) {
        const m = MELODY[step % MELODY.length];
        const delay = nextNote - ac.currentTime;
        if (m) tone(midi(m), STEP * 0.9, 'square', 0.25, null, delay, musicBus);
        if (step % 2 === 0) tone(midi(BASS[(step / 2) % BASS.length]), STEP * 1.6, 'triangle', 0.5, null, delay, musicBus);
        nextNote += STEP;
        step++;
      }
    }, 50);
  }

  function toggleMute() {
    muted = !muted;
    if (master) master.gain.value = muted ? 0 : 0.5;
    return muted;
  }

  function stop() { if (musicTimer) clearInterval(musicTimer); setInhale(false); }

  return { unlock, onEvents, setInhale, toggleMute, stop, isMuted: () => muted };
})();

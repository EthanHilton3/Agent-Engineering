// Chiptune sound effects and music, synthesised with Web Audio. No audio files.
// The browser only allows sound after a key press, so unlock() runs on the first key.
var GameAudio = (function () {
  'use strict';
  var VOL = { MASTER: 0.5, SFX: 0.55, MUSIC: 0.2, DUCK: 0.35 };
  var LOOKAHEAD = 0.12, SCHEDULE_MS = 25;

  var ac = null, master = null, sfxBus = null, musicBus = null, noiseBuf = null;
  var muted = false, ducked = false;
  var inhale = null;
  var music = { name: null, song: null, step: 0, next: 0, timer: null };

  // Original tunes. One token per eighth note: note name, '-' holds the previous note, '.' rests.
  var SONGS = {
    level: {
      bpm: 140,
      lead: 'E5 - G5 - C6 - G5 - A5 G5 E5 - D5 - . . F5 - A5 - D6 - A5 - B5 A5 G5 - - - . . ' +
        'E5 - G5 - C6 - E6 - D6 C6 A5 - G5 - E5 - F5 - D5 - G5 - B4 - C5 - - - . . G4 .',
      bass: 'C3 . G3 . C3 . G3 . A2 . E3 . A2 . E3 . D3 . A3 . D3 . A3 . G2 . D3 . G2 . B2 . ' +
        'C3 . G3 . C3 . G3 . F2 . C3 . F2 . C3 . D3 . A2 . G2 . G3 . C3 . G2 . C3 . . .',
      drums: 'k.h.s.h.'
    },
    boss: {
      bpm: 170,
      lead: 'A4 . C5 A4 E5 . D5 C5 B4 . G4 B4 D5 . C5 B4 A4 . C5 A4 E5 . G5 F5 E5 - - D#5 E5 - . .',
      bass: 'A2 A3 A2 A3 A2 A3 A2 A3 G2 G3 G2 G3 G2 G3 G2 G3 F2 F3 F2 F3 F2 F3 F2 F3 E2 E3 E2 E3 E2 E3 B2 E3',
      drums: 'k.hsk.hs'
    }
  };
  var NOTE = { C: 0, 'C#': 1, D: 2, 'D#': 3, E: 4, F: 5, 'F#': 6, G: 7, 'G#': 8, A: 9, 'A#': 10, B: 11 };

  function freq(name) {
    var m = /^([A-G]#?)(\d)$/.exec(name);
    return 440 * Math.pow(2, (NOTE[m[1]] + (Number(m[2]) + 1) * 12 - 69) / 12);
  }

  function parse(song) {
    return {
      bpm: song.bpm,
      lead: song.lead.trim().split(/\s+/),
      bass: song.bass.trim().split(/\s+/),
      drums: song.drums
    };
  }

  function unlock() {
    if (!ac) {
      var Ctor = window.AudioContext || window.webkitAudioContext;
      if (!Ctor) return;
      ac = new Ctor();
      master = ac.createGain();
      master.gain.value = muted ? 0 : VOL.MASTER;
      master.connect(ac.destination);
      sfxBus = ac.createGain(); sfxBus.gain.value = VOL.SFX; sfxBus.connect(master);
      musicBus = ac.createGain(); musicBus.gain.value = VOL.MUSIC; musicBus.connect(master);
      noiseBuf = ac.createBuffer(1, ac.sampleRate, ac.sampleRate);
      var d = noiseBuf.getChannelData(0);
      for (var i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    }
    if (ac.state === 'suspended') ac.resume();
  }

  function env(g, t, vol, dur) {
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(vol, t + 0.005);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  }

  function tone(type, f0, f1, dur, vol, delay, bus, at) {
    if (!ac) return;
    var t = (at || ac.currentTime) + (delay || 0);
    var o = ac.createOscillator(), g = ac.createGain();
    o.type = type;
    o.frequency.setValueAtTime(f0, t);
    if (f1 && f1 !== f0) o.frequency.exponentialRampToValueAtTime(f1, t + dur);
    env(g, t, vol, dur);
    o.connect(g); g.connect(bus || sfxBus);
    o.start(t); o.stop(t + dur + 0.02);
  }

  function noise(dur, vol, f0, f1, delay, bus, at) {
    if (!ac) return;
    var t = (at || ac.currentTime) + (delay || 0);
    var src = ac.createBufferSource(), flt = ac.createBiquadFilter(), g = ac.createGain();
    src.buffer = noiseBuf;
    flt.type = 'bandpass';
    flt.frequency.setValueAtTime(f0, t);
    if (f1) flt.frequency.exponentialRampToValueAtTime(f1, t + dur);
    env(g, t, vol, dur);
    src.connect(flt); flt.connect(g); g.connect(bus || sfxBus);
    src.start(t); src.stop(t + dur + 0.02);
  }

  function arp(notes, step, type, vol) {
    notes.forEach(function (n, i) { tone(type || 'square', freq(n), 0, step * 1.4, vol || 0.12, i * step); });
  }

  function startInhale() {
    if (!ac || inhale) return;
    var src = ac.createBufferSource(), flt = ac.createBiquadFilter(), g = ac.createGain();
    src.buffer = noiseBuf; src.loop = true;
    flt.type = 'bandpass'; flt.Q.value = 2;
    flt.frequency.setValueAtTime(400, ac.currentTime);
    flt.frequency.exponentialRampToValueAtTime(2400, ac.currentTime + 0.6);
    g.gain.setValueAtTime(0.0001, ac.currentTime);
    g.gain.exponentialRampToValueAtTime(0.22, ac.currentTime + 0.08);
    src.connect(flt); flt.connect(g); g.connect(sfxBus);
    src.start();
    inhale = { src: src, g: g };
  }

  function stopInhale() {
    if (!inhale) return;
    var t = ac.currentTime;
    inhale.g.gain.cancelScheduledValues(t);
    inhale.g.gain.setValueAtTime(inhale.g.gain.value, t);
    inhale.g.gain.exponentialRampToValueAtTime(0.0001, t + 0.08);
    inhale.src.stop(t + 0.1);
    inhale = null;
  }

  var SFX = {
    jump: function () { tone('square', 320, 640, 0.12, 0.12); },
    flap: function () { tone('triangle', 520, 820, 0.08, 0.16); noise(0.05, 0.05, 2000); },
    inhaleStart: startInhale,
    inhaleStop: stopInhale,
    swallow: function () { stopInhale(); tone('square', 520, 110, 0.18, 0.16); },
    spit: function (e) { tone('square', e.big ? 700 : 950, 240, 0.15, 0.15); noise(0.08, 0.1, 3000); },
    exhale: function () { noise(0.18, 0.14, 1400, 500); },
    deflate: function () { noise(0.12, 0.08, 1000, 400); },
    defeat: function () { arp(['E6', 'G6', 'C7'], 0.04, 'square', 0.09); },
    blockGrab: function () { tone('triangle', 300, 600, 0.06, 0.1); },
    blockBreak: function () { noise(0.14, 0.22, 900, 200); tone('square', 220, 70, 0.12, 0.08); },
    hurt: function () { tone('sawtooth', 400, 90, 0.3, 0.16); },
    drop: function () { tone('triangle', 600, 300, 0.15, 0.1); },
    death: function () { arp(['C5', 'G4', 'E4', 'C4'], 0.12, 'square', 0.12); },
    pickup: function (e) {
      if (e.kind === 'star') arp(['E6', 'B6'], 0.05, 'square', 0.08);
      else arp(['C5', 'E5', 'G5', 'C6', 'E6'], 0.06, 'square', 0.1);
    },
    oneUp: function () { arp(['E5', 'G5', 'E6', 'C6', 'D6', 'G6'], 0.07, 'square', 0.1); },
    checkpoint: function () { arp(['G5', 'C6', 'E6'], 0.08, 'triangle', 0.16); },
    clink: function () { tone('square', 2100, 1800, 0.05, 0.07); },
    noFly: function () { tone('square', 180, 150, 0.08, 0.08); },
    starPoof: function () { noise(0.06, 0.05, 2500); },
    pause: function () { tone('triangle', 880, 0, 0.06, 0.12); },
    resume: function () { tone('triangle', 660, 0, 0.06, 0.12); },
    arenaLock: function () { noise(0.5, 0.3, 200, 80); tone('square', 110, 55, 0.5, 0.12); },
    bossWake: function () { tone('sawtooth', 90, 60, 0.8, 0.1); },
    appleDrop: function () { tone('triangle', 900, 300, 0.25, 0.07); },
    bossBlow: function () { noise(0.35, 0.13, 700, 250); },
    bossHit: function () { noise(0.2, 0.3, 500, 150); tone('square', 160, 60, 0.25, 0.16); },
    bossBoom: function () { noise(0.3, 0.22, 300, 80); },
    bossDefeated: function () { arp(['C5', 'E5', 'G5', 'C6', 'G5', 'C6', 'E6'], 0.09, 'square', 0.12); },
    win: function () { arp(['G4', 'C5', 'E5', 'G5', 'E5', 'G5', 'C6', 'C6', 'D6', 'E6'], 0.11, 'square', 0.12); },
    gameOver: function () { arp(['G4', 'F#4', 'F4', 'E4', 'D#4', 'C4'], 0.18, 'triangle', 0.18); }
  };

  function play(ev) {
    if (!ac || !SFX[ev.type]) return;
    SFX[ev.type](ev);
  }

  function scheduleStep(song, i, t) {
    var dur = 60 / song.bpm / 2;
    var n = song.lead[i % song.lead.length];
    if (n !== '.' && n !== '-') {
      var hold = 1;
      while (song.lead[(i + hold) % song.lead.length] === '-') hold++;
      tone('square', freq(n), 0, dur * hold * 0.9, 0.12, 0, musicBus, t);
    }
    var b = song.bass[i % song.bass.length];
    if (b !== '.' && b !== '-') tone('triangle', freq(b), 0, dur * 0.9, 0.3, 0, musicBus, t);
    var d = song.drums[i % song.drums.length];
    if (d === 'k') tone('sine', 150, 45, 0.12, 0.35, 0, musicBus, t);
    else if (d === 'h') noise(0.03, 0.08, 7000, 0, 0, musicBus, t);
    else if (d === 's') noise(0.09, 0.14, 1800, 0, 0, musicBus, t);
  }

  function pump() {
    if (!ac || !music.song) return;
    var song = music.song, dur = 60 / song.bpm / 2;
    if (music.next < ac.currentTime) music.next = ac.currentTime + 0.02;
    while (music.next < ac.currentTime + LOOKAHEAD) {
      scheduleStep(song, music.step, music.next);
      music.step = (music.step + 1) % song.lead.length;
      music.next += dur;
    }
  }

  function setMusic(name) {
    if (name === music.name) return;
    music.name = name;
    music.song = name ? parse(SONGS[name]) : null;
    music.step = 0;
    music.next = 0;
    if (music.song && !music.timer) music.timer = setInterval(pump, SCHEDULE_MS);
    if (!music.song && music.timer) { clearInterval(music.timer); music.timer = null; }
  }

  function setDucked(on) {
    if (on === ducked) return;
    ducked = on;
    if (musicBus) musicBus.gain.setTargetAtTime(on ? VOL.MUSIC * VOL.DUCK : VOL.MUSIC, ac.currentTime, 0.05);
    if (on) stopInhale();
  }

  function toggleMute() {
    muted = !muted;
    if (master) master.gain.setTargetAtTime(muted ? 0 : VOL.MASTER, ac.currentTime, 0.02);
    return muted;
  }

  return {
    unlock: unlock, play: play, setMusic: setMusic, setDucked: setDucked, toggleMute: toggleMute,
    isMuted: function () { return muted; }
  };
})();

#!/usr/bin/env node
// Compute common game-feel numbers from a recorded trajectory.
//
// Input: a JSON file (or stdin) with
//   { "tickRate": 60, "tile": 16, "yDown": true,
//     "samples": [ { "x": 0, "y": 100, "vx": 0, "vy": 0, "onGround": true }, ... ] }
// One sample per game tick, starting on the tick the input was applied.
// x and y are in pixels; vx and vy are in pixels per second. yDown is true when y grows downward (most canvas games).
//
// Output: JSON with apex height, time to apex, airtime, horizontal distance,
// peak speed and time to reach 90 percent of peak speed, in tiles and seconds.
//
// Usage: node trajectory_stats.js samples.json
//        node trajectory_stats.js < samples.json

const fs = require('fs');

function stats(data) {
  const { tickRate = 60, tile = 16, yDown = true, samples } = data;
  if (!Array.isArray(samples) || samples.length < 2) {
    throw new Error('need at least 2 samples');
  }
  const dt = 1 / tickRate;
  const up = (y0, y) => (yDown ? y0 - y : y - y0);   // positive = higher than start
  const s0 = samples[0];

  let apex = 0, apexTick = 0;
  samples.forEach((s, i) => {
    const h = up(s0.y, s.y);
    if (h > apex) { apex = h; apexTick = i; }
  });

  // Airtime: ticks from leaving the ground until first landing after that.
  let leave = -1, land = -1;
  for (let i = 1; i < samples.length; i++) {
    if (leave < 0 && samples[i - 1].onGround && !samples[i].onGround) leave = i;
    else if (leave >= 0 && samples[i].onGround) { land = i; break; }
  }

  const speeds = samples.map(s => Math.abs(s.vx || 0));
  const peak = Math.max(...speeds);
  const t90 = peak > 0 ? speeds.findIndex(v => v >= 0.9 * peak) : -1;

  const last = samples[samples.length - 1];
  const r = (n) => Math.round(n * 1000) / 1000;
  return {
    apexTiles: r(apex / tile),
    timeToApexSec: r(apexTick * dt),
    airtimeSec: leave >= 0 && land >= 0 ? r((land - leave) * dt) : null,
    // Horizontal distance covered while airborne (whole recording if it never lands).
    horizontalTiles: r(Math.abs((land >= 0 ? samples[land].x : last.x) - (leave >= 0 ? samples[leave - 1].x : s0.x)) / tile),
    peakSpeedTilesPerSec: r(peak / tile),
    timeToNinetyPercentSpeedSec: t90 >= 0 ? r(t90 * dt) : null,
    samples: samples.length,
  };
}

if (require.main === module) {
  const src = process.argv[2] ? fs.readFileSync(process.argv[2], 'utf8') : fs.readFileSync(0, 'utf8');
  console.log(JSON.stringify(stats(JSON.parse(src)), null, 2));
}

module.exports = { stats };

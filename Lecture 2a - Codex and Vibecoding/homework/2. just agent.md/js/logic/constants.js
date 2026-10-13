// Every tunable number for the game lives here. Units: pixels, seconds, ticks (1/60 s).
var KB = (typeof KB !== 'undefined') ? KB : {};

KB.C = Object.freeze({
  // World
  TILE: 16,
  VIEW_W: 320,
  VIEW_H: 192,
  TICKS_PER_SEC: 60,
  DT: 1 / 60,
  MAX_SUBSTEP: 4,            // largest move per collision sub-step (px); smaller than a tile, so nothing tunnels
  ACTIVATE_DIST: 260,        // enemies farther than this from Kirby stay frozen

  // Tile ids
  T: Object.freeze({ EMPTY: 0, GROUND: 1, BRICK: 2, STAR_BLOCK: 3, CLOUD: 4 }),

  // Kirby body and running
  PLAYER_W: 12,
  PLAYER_H: 14,
  RUN_SPEED: 96,
  GROUND_ACCEL: 900,
  GROUND_DECEL: 1100,
  AIR_ACCEL: 700,
  FULL_SPEED_FACTOR: 0.85,   // mouthful Kirby is a little slower

  // Jumping
  GRAVITY: 950,              // while rising
  FALL_GRAVITY: 1250,        // while falling (snappier landings)
  MAX_FALL_SPEED: 320,
  JUMP_SPEED: 335,
  JUMP_CUT_SPEED: 120,       // releasing Space early caps upward speed to this
  COYOTE_TICKS: 6,
  JUMP_BUFFER_TICKS: 6,

  // Flying (tap Space in the air)
  FLY_FLAP_SPEED: 165,
  FLY_GRAVITY: 420,
  FLY_MAX_FALL: 55,
  FLY_SPEED_X: 72,
  FLY_ACCEL: 500,
  FLY_MAX_FLAPS: 8,          // flaps allowed before Kirby has to land again
  FLY_CEILING: 20,           // Kirby cannot rise above this y (keeps him below the HUD bar)

  // Inhale cone (measured from Kirby's mouth)
  INHALE_RANGE: 64,
  INHALE_HALF_HEIGHT: 10,    // half-height of the cone at the mouth
  INHALE_SPREAD: 0.45,       // extra half-height per pixel of distance
  INHALE_BEHIND: 4,          // things this far behind the mouth still count
  INHALE_PULL_SPEED: 70,     // pull speed at the edge of the cone (px/s)
  INHALE_PULL_BOOST: 260,    // added pull speed as things get close
  INHALE_SWALLOW_DIST: 10,
  INHALE_MOVE_FACTOR: 0,     // Kirby plants his feet while inhaling
  INHALE_AIR_MAX_FALL: 60,   // inhaling in mid-air slows the fall
  MOUTH_Y_RATIO: 0.55,       // mouth height as a fraction of Kirby's body, from the top

  // Projectiles
  STAR_SPEED: 260,
  STAR_LIFE_TICKS: 70,
  STAR_SIZE: 12,
  PUFF_SPEED: 200,
  PUFF_LIFE_TICKS: 14,
  PUFF_SIZE: 10,
  SPIT_ANIM_TICKS: 12,
  LAND_SQUASH_TICKS: 6,

  // Enemies
  WALKER_SPEED: 28,
  FLYER_SPEED: 36,
  FLYER_RANGE: 56,           // patrol distance either side of spawn
  FLYER_AMP: 12,
  FLYER_FREQ: 3,             // radians per second of the bob
  FLYER_EASE: 0.2,           // how fast a flyer drifts back onto its path
  HOPPER_WAIT_TICKS: 70,
  HOPPER_STAGGER: 7,         // spreads out hoppers' first jumps by spawn column
  HOPPER_JUMP_SPEED: 250,
  HOPPER_SPEED_X: 55,
  GORDO_AMP: 36,
  GORDO_FREQ: 1.8,
  ENEMY_SIZE: 12,
  GORDO_SIZE: 14,
  PICKUP_SIZE: 8,
  TOMATO_SIZE: 12,

  // Health, lives, timers
  MAX_HP: 3,
  START_LIVES: 3,
  INVULN_TICKS: 90,
  KNOCKBACK_X: 110,
  KNOCKBACK_Y: 170,
  DEATH_TICKS: 110,
  DEATH_POP_SPEED: 260,
  DEATH_HANG_TICKS: 28,       // Kirby freezes this long before falling off the screen
  CONTACT_INSET: 1,          // enemy touches use a hitbox this much smaller than Kirby's
  WIN_SCREEN_TICKS: 120,
  END_INPUT_DELAY_TICKS: 40, // ignore keys this long after game over / win so mashing doesn't skip it

  // Score
  SCORE_STAR_HIT: 200,       // doubles for each extra enemy one star pierces
  SCORE_PUFF_HIT: 100,
  SCORE_SWALLOW: 100,
  SCORE_BUMP: 50,
  SCORE_PICKUP: 50,
  SCORE_TOMATO: 100,
  SCORE_GOAL: 1000,
  SCORE_LIFE_BONUS: 500,
});

if (typeof module !== 'undefined') module.exports = { C: KB.C };

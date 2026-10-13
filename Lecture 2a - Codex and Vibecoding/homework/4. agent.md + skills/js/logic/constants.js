// Every tunable number in the game lives in this one block.
// Units: pixels for distance, ticks (1/60 s) for time, pixels per tick for speed.
var CONST = {
  // World and screen
  TILE: 16,
  VIEW_W: 256,
  VIEW_H: 224,
  TICKS_PER_SECOND: 60,
  MAX_SUBSTEP: 4,          // max px moved per collision sub-step (smaller than any body, so nothing tunnels)
  MAX_STEPS_PER_FRAME: 5,  // fixed-step catch-up cap so a slow frame cannot spiral

  // Player body and running
  PLAYER_W: 12,
  PLAYER_H: 12,
  RUN_MAX: 1.7,
  RUN_ACCEL: 0.16,
  RUN_DECEL: 0.22,
  RUN_TURN_BOOST: 0.12,
  AIR_ACCEL: 0.11,
  AIR_DECEL: 0.04,
  GRAVITY: 0.26,
  MAX_FALL: 4.8,
  JUMP_VY: -4.9,
  JUMP_CUT_VY: -1.8,       // releasing Space early clamps upward speed to this
  COYOTE_TICKS: 6,
  LAND_DUST_VY: 2.5,

  // Flying (unlimited flaps; the limits are the ceiling, the flap speed and the full-mouth lockout)
  FLAP_VY: -2.3,
  FLY_GRAVITY: 0.11,
  FLY_MAX_FALL: 1.1,
  FLY_MAX_SPEED: 1.25,
  FLY_ACCEL: 0.08,
  FLY_CEILING: 8,          // y in px that Kirby can never rise above
  FLAP_ANIM_TICKS: 10,

  // Mouth full
  FULL_MAX_SPEED: 1.2,
  FULL_JUMP_VY: -4.0,

  // Inhale
  INHALE_RANGE: 60,
  INHALE_HALF_HEIGHT: 10,  // cone half-height at the mouth
  INHALE_SPREAD: 0.35,     // extra half-height per px of distance
  INHALE_BEHIND: 4,        // how far behind the mouth still counts
  INHALE_HOLD_FACTOR: 1.3, // caught things stay caught out to range * this
  INHALE_PULL: 0.4,
  INHALE_MAX_PULL: 5,
  SWALLOW_RADIUS: 8,
  SWALLOW_LOCK_TICKS: 12,
  LOS_STEP: 6,             // px between line-of-sight samples

  // Spit star and exhaled air
  SPIT_SPEED: 4.5,
  SPIT_LIFE: 70,
  SPIT_SIZE: 12,
  BIG_SPIT_SIZE: 16,
  SPIT_RECOIL: 1.2,
  SPIT_ANIM_TICKS: 12,
  AIR_PUFF_SPEED: 3.2,
  AIR_PUFF_DRAG: 0.92,
  AIR_PUFF_LIFE: 18,
  AIR_PUFF_SIZE: 10,

  // Health and lives
  MAX_HEALTH: 6,
  START_LIVES: 3,
  INVULN_TICKS: 90,
  RESPAWN_INVULN_TICKS: 90,
  HURT_STUN_TICKS: 18,
  KNOCKBACK_VX: 2.2,
  KNOCKBACK_VY: -2.6,
  DEATH_TICKS: 120,
  PIT_MARGIN: 32,

  // Enemies
  ACTIVATION_RANGE: 300,
  STUN_TICKS: 30,
  WALKER_SPEED: 0.45,
  FLYER_SPEED: 0.55,
  FLYER_SENSE: 170,
  FLYER_AMP: 10,
  FLYER_FREQ: 0.05,
  FLYER_HOMING: 0.12,
  FLYER_LEASH: 48,
  FLYER_PATROL: 48,
  FLYER_PATROL_SPEED: 0.3,
  HOPPER_WAIT: 50,
  HOPPER_SENSE: 150,
  HOPPER_JUMP_VY: -4.2,
  HOPPER_HOP_VX: 1.3,
  SPIKY_AMP: 18,
  SPIKY_FREQ: 0.035,
  SPIKY_PATROL: 36,
  LOOSE_LIFE: 300,
  LOOSE_BOUNCE: -2.2,
  LOOSE_TOSS_VX: 1.5,
  LOOSE_FRICTION: 0.9,
  LOOSE_BOUNCE_DECAY: 0.6,
  LOOSE_MIN_BOUNCE: -0.8,
  ENEMY_SIZE: 12,          // walker, hopper, flyer width; loose objects
  FLYER_H: 10,
  SPIKY_SIZE: 14,

  // Wind
  WIND_GUST_PERIOD: 150,
  WIND_GUST_MIN: 0.4,      // gusts vary between this fraction and 1.0 of full strength

  // Boss
  BOSS_HP: 6,
  BOSS_W: 40,
  BOSS_H: 56,
  BOSS_INTRO_TICKS: 90,
  BOSS_APPLE_WAIT: 130,
  BOSS_BLOW_WAIT: 150,
  BOSS_APPLES: 2,
  BOSS_RAGE_APPLES: 3,
  BOSS_PUFFS: 3,
  BOSS_PUFF_GAP: 40,
  BOSS_PUFF_SPEED: 1.5,
  BOSS_PUFF_LOW: 14,       // puff centre height above the floor (must jump)
  BOSS_PUFF_HIGH: 40,      // puff centre height above the floor (walk under)
  BOSS_PUFF_SIZE: 12,
  BOSS_PUFF_WOBBLE: 2,
  BOSS_PUFF_WOBBLE_FREQ: 0.25,
  BOSS_HIT_INVULN: 45,
  BOSS_DEATH_TICKS: 150,
  BOSS_BOOM_EVERY: 12,
  BOSS_RAGE_HP: 3,
  BOSS_RAGE_SPEEDUP: 0.7,
  BOSS_APPLE_MARGIN: 32,   // apples never drop closer than this to the arena gate or the trunk
  APPLE_SIZE: 12,
  APPLE_ROLL_SPEED: 0.8,
  APPLE_LIFE: 420,
  ARENA_LOCK_OFFSET: 40,   // px past the gate before it slams shut

  // Score
  SCORE: { walker: 200, flyer: 300, hopper: 300, apple: 50, block: 50, star: 100, food: 500, boss: 5000 },
  TIME_BONUS_MAX: 10000,
  TIME_BONUS_PER_SECOND: 20,
  EXTRA_LIFE_SCORE: 15000,

  // Screens
  SCREEN_INPUT_DELAY: 45,  // ticks before title/game-over/win screens accept input
  BANNER_TICKS: 150
};

if (typeof module !== 'undefined') module.exports = { CONST };

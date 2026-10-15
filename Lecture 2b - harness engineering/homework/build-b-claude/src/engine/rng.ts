// Seeded PRNG (mulberry32). The state is a plain uint32 so it can live inside
// GameState and be cloned; every call returns the advanced state.

/** Returns a uniform integer in [0, maxExclusive) and the advanced RNG state. */
export function randomInt(rngState: number, maxExclusive: number): { value: number; rngState: number } {
  const next = advance(rngState);
  return { value: Math.floor(outputOf(next) * maxExclusive), rngState: next };
}

/** Returns a Fisher-Yates shuffled copy of `items` and the advanced RNG state. */
export function shuffle<T>(items: T[], rngState: number): { items: T[]; rngState: number } {
  const result = [...items];
  let state = rngState;
  for (let i = result.length - 1; i > 0; i--) {
    const pick = randomInt(state, i + 1);
    state = pick.rngState;
    [result[i], result[pick.value]] = [result[pick.value], result[i]];
  }
  return { items: result, rngState: state };
}

function advance(rngState: number): number {
  return (rngState + 0x6d2b79f5) >>> 0;
}

/** The mulberry32 output function: maps a state to a float in [0, 1). */
function outputOf(state: number): number {
  let t = state;
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}

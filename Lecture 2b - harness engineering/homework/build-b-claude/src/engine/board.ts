import { shuffle } from './rng';
import { TOPOLOGY } from './topology';
import type { Board, Hex, HexId, Terrain } from './types';

const TERRAINS: Terrain[] = [
  ...repeat<Terrain>('forest', 4),
  ...repeat<Terrain>('pasture', 4),
  ...repeat<Terrain>('fields', 4),
  ...repeat<Terrain>('hills', 3),
  ...repeat<Terrain>('mountains', 3),
  'desert',
];

const NUMBER_TOKENS: number[] = [2, 3, 3, 4, 4, 5, 5, 6, 6, 8, 8, 9, 9, 10, 10, 11, 11, 12];

/** Generates the board for a seed: the same seed always yields the same terrain and numbers. */
export function generateBoard(seed: number): Board {
  const terrainShuffle = shuffle(TERRAINS, seed >>> 0);
  const terrains = terrainShuffle.items;
  let rngState = terrainShuffle.rngState;
  // Reshuffling on the same RNG stream keeps the result a pure function of the seed.
  for (;;) {
    const numberShuffle = shuffle(NUMBER_TOKENS, rngState);
    rngState = numberShuffle.rngState;
    const board: Board = { seed, hexes: assignNumbers(terrains, numberShuffle.items) };
    if (!hasAdjacentRedNumbers(board)) return board;
  }
}

/** True if any hex numbered 6 or 8 is adjacent to another hex numbered 6 or 8. */
export function hasAdjacentRedNumbers(board: Board): boolean {
  return board.hexes.some(
    (hex) => isRedNumber(hex) && TOPOLOGY.hexNeighbors[hex.id].some((n) => isRedNumber(board.hexes[n])),
  );
}

/** The ID of the board's desert hex, where the robber starts. */
export function desertHex(board: Board): HexId {
  const desert = board.hexes.find((hex) => hex.terrain === 'desert');
  if (!desert) throw new Error('Board has no desert');
  return desert.id;
}

/** Pairs terrains with numbers in hex order, skipping the desert. */
function assignNumbers(terrains: Terrain[], numbers: number[]): Hex[] {
  const remaining = [...numbers];
  return terrains.map((terrain, id) => ({
    id,
    terrain,
    number: terrain === 'desert' ? null : (remaining.shift() ?? null),
  }));
}

function isRedNumber(hex: Hex): boolean {
  return hex.number === 6 || hex.number === 8;
}

function repeat<T>(item: T, count: number): T[] {
  return Array.from({ length: count }, () => item);
}

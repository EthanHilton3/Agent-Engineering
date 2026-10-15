import { GEO } from './geometry';
import { Rng } from './rng';
import type { Board, HexTile, Terrain } from './types';

const TERRAINS: Terrain[] = [
  ...Array<Terrain>(4).fill('forest'),
  ...Array<Terrain>(4).fill('pasture'),
  ...Array<Terrain>(4).fill('fields'),
  ...Array<Terrain>(3).fill('hills'),
  ...Array<Terrain>(3).fill('mountains'),
  'desert',
];

const NUMBERS = [2, 3, 3, 4, 4, 5, 5, 6, 6, 8, 8, 9, 9, 10, 10, 11, 11, 12];

export const isRedNumber = (n: number | null) => n === 6 || n === 8;

/** True if no 6 or 8 sits on a hex adjacent to another 6 or 8. */
export function redNumbersSeparated(tiles: HexTile[]): boolean {
  return GEO.hexes.every(
    (hex) =>
      !isRedNumber(tiles[hex.id].number) ||
      hex.neighbors.every((n) => !isRedNumber(tiles[n].number)),
  );
}

/**
 * Generate a board deterministically from a seed. Layouts that put red numbers
 * next to each other are rejected and re-drawn from the same RNG stream, so the
 * result is still a pure function of the seed.
 */
export function generateBoard(seed: string): Board {
  const rng = Rng.fromSeed(`board:${seed}`);
  for (;;) {
    const terrains = rng.shuffle(TERRAINS);
    const numbers = rng.shuffle(NUMBERS);
    let n = 0;
    const tiles: HexTile[] = terrains.map((terrain) => ({
      terrain,
      number: terrain === 'desert' ? null : numbers[n++],
    }));
    if (redNumbersSeparated(tiles)) {
      return { seed, tiles, desertHex: terrains.indexOf('desert') };
    }
  }
}

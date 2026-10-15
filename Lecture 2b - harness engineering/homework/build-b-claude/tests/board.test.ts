import { describe, expect, it } from 'vitest';
import { desertHex, generateBoard, hasAdjacentRedNumbers } from '../src/engine/board';
import { TOPOLOGY } from '../src/engine/topology';
import type { Board, Terrain } from '../src/engine/types';

const SEEDS = Array.from({ length: 100 }, (_, i) => i * 7919 + 1);

describe('board generation', () => {
  it('Scenario 1: same seed gives identical terrain and numbers', () => {
    for (const seed of [0, 42, 123456789, 4294967295]) {
      expect(generateBoard(seed)).toEqual(generateBoard(seed));
    }
  });

  it('Scenario 2: no adjacent 6/8 across 100 seeds', () => {
    for (const seed of SEEDS) {
      const board = generateBoard(seed);
      for (const hex of board.hexes) {
        if (hex.number !== 6 && hex.number !== 8) continue;
        const neighborNumbers = TOPOLOGY.hexNeighbors[hex.id].map((n) => board.hexes[n].number);
        expect(neighborNumbers).not.toContain(6);
        expect(neighborNumbers).not.toContain(8);
      }
    }
  });

  it('places the correct multiset of terrains', () => {
    for (const seed of SEEDS.slice(0, 10)) {
      const counts = countBy(generateBoard(seed).hexes.map((h) => h.terrain));
      const expected: Record<Terrain, number> = { forest: 4, pasture: 4, fields: 4, hills: 3, mountains: 3, desert: 1 };
      expect(counts).toEqual(expected);
    }
  });

  it('places the correct multiset of numbers, with none on the desert', () => {
    for (const seed of SEEDS.slice(0, 10)) {
      const board = generateBoard(seed);
      const numbers = board.hexes.flatMap((h) => (h.number === null ? [] : [h.number]));
      expect(numbers.sort((a, b) => a - b)).toEqual([2, 3, 3, 4, 4, 5, 5, 6, 6, 8, 8, 9, 9, 10, 10, 11, 11, 12]);
      expect(board.hexes[desertHex(board)].number).toBeNull();
    }
  });

  it('indexes hexes by ID and records the seed', () => {
    const board = generateBoard(99);
    expect(board.seed).toBe(99);
    expect(board.hexes).toHaveLength(19);
    board.hexes.forEach((hex, i) => expect(hex.id).toBe(i));
  });

  it('desertHex finds the desert', () => {
    const board = generateBoard(7);
    expect(board.hexes[desertHex(board)].terrain).toBe('desert');
  });

  it('different seeds usually give different boards', () => {
    const layouts = new Set(SEEDS.slice(0, 20).map((seed) => JSON.stringify(generateBoard(seed).hexes)));
    expect(layouts.size).toBeGreaterThan(15);
  });
});

describe('hasAdjacentRedNumbers', () => {
  it('detects a 6 next to an 8', () => {
    const board = generateBoard(5);
    const [a, b] = adjacentPair();
    expect(hasAdjacentRedNumbers(withNumbers(board, { [a]: 6, [b]: 8 }))).toBe(true);
  });

  it('allows a 6 and 8 that are not adjacent', () => {
    const board = generateBoard(5);
    expect(hasAdjacentRedNumbers(board)).toBe(false);
    const [a, far] = nonAdjacentPair();
    expect(hasAdjacentRedNumbers(withNumbers(board, { [a]: 6, [far]: 8 }))).toBe(false);
  });
});

function countBy<T extends string>(items: T[]): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const item of items) counts[item] = (counts[item] ?? 0) + 1;
  return counts;
}

function adjacentPair(): [number, number] {
  return [9, TOPOLOGY.hexNeighbors[9][0]];
}

function nonAdjacentPair(): [number, number] {
  // Hexes 0 and 18 are opposite ends of the board.
  return [0, 18];
}

/** A copy of `board` with every 6/8 cleared and the given hexes renumbered. */
function withNumbers(board: Board, numbers: Record<number, number>): Board {
  return {
    ...board,
    hexes: board.hexes.map((hex) => {
      const cleared = hex.number === 6 || hex.number === 8 ? 5 : hex.number;
      return { ...hex, number: numbers[hex.id] ?? cleared };
    }),
  };
}

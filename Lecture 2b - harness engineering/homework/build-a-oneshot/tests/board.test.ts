import { describe, expect, it } from 'vitest';
import { generateBoard, isRedNumber } from '../src/game/board';
import { GEO } from '../src/game/geometry';
import { newGame } from './helpers';

describe('board geometry', () => {
  it('has 19 hexes in a 3-4-5-4-3 layout, 54 corners and 72 edges', () => {
    expect(GEO.hexes).toHaveLength(19);
    const rows = [-2, -1, 0, 1, 2].map((r) => GEO.hexes.filter((h) => h.r === r).length);
    expect(rows).toEqual([3, 4, 5, 4, 3]);
    expect(GEO.corners).toHaveLength(54);
    expect(GEO.edges).toHaveLength(72);
  });

  it('shares corners between up to 3 hexes and edges between up to 2', () => {
    expect(Math.max(...GEO.corners.map((c) => c.hexes.length))).toBe(3);
    expect(Math.max(...GEO.edges.map((e) => e.hexes.length))).toBe(2);
    for (const h of GEO.hexes) {
      expect(new Set(h.corners).size).toBe(6);
      expect(new Set(h.edges).size).toBe(6);
    }
  });
});

describe('board generation', () => {
  it('uses the standard terrain and number distribution', () => {
    const b = generateBoard('abc');
    const count = (t: string) => b.tiles.filter((x) => x.terrain === t).length;
    expect([count('forest'), count('pasture'), count('fields'), count('hills'), count('mountains'), count('desert')])
      .toEqual([4, 4, 4, 3, 3, 1]);
    const nums = b.tiles.map((t) => t.number).filter((n) => n !== null).sort((a, z) => a! - z!);
    expect(nums).toEqual([2, 3, 3, 4, 4, 5, 5, 6, 6, 8, 8, 9, 9, 10, 10, 11, 11, 12]);
    expect(b.tiles[b.desertHex]).toEqual({ terrain: 'desert', number: null });
  });

  it('robber starts on the desert', () => {
    const g = newGame(2, 'robber-start');
    expect(g.state.robberHex).toBe(g.state.board.desertHex);
  });

  // Scenario 1
  it('is deterministic: the same seed yields the same board', () => {
    expect(generateBoard('same-seed')).toEqual(generateBoard('same-seed'));
    expect(newGame(3, 'xyz').state.board).toEqual(newGame(3, 'xyz').state.board);
    expect(generateBoard('seed-a')).not.toEqual(generateBoard('seed-b'));
  });

  // Scenario 2
  it('never places a 6 or 8 next to another 6 or 8 (100 boards)', () => {
    for (let i = 0; i < 100; i++) {
      const b = generateBoard(`many-${i}`);
      for (const hex of GEO.hexes) {
        if (!isRedNumber(b.tiles[hex.id].number)) continue;
        for (const n of hex.neighbors) expect(isRedNumber(b.tiles[n].number)).toBe(false);
      }
    }
  });
});

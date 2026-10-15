import { describe, expect, it } from 'vitest';
import {
  COSTS,
  addCounts,
  countsOf,
  hasAtLeast,
  subtractCounts,
  terrainResource,
  totalCards,
} from '../src/engine/resources';
import { randomInt, shuffle } from '../src/engine/rng';

describe('resources', () => {
  it('matches the spec costs', () => {
    expect(totalCards(COSTS.road)).toBe(2);
    expect(COSTS.settlement).toEqual(countsOf({ brick: 1, wood: 1, wheat: 1, sheep: 1 }));
    expect(COSTS.city).toEqual(countsOf({ ore: 3, wheat: 2 }));
  });

  it('checks affordability on both sides', () => {
    expect(hasAtLeast(countsOf({ wood: 1, brick: 1, ore: 2 }), COSTS.road)).toBe(true);
    expect(hasAtLeast(countsOf({ wood: 1 }), COSTS.road)).toBe(false);
  });

  it('adds and subtracts counts per resource', () => {
    const hand = countsOf({ wood: 2, ore: 1 });
    expect(addCounts(hand, COSTS.road)).toEqual(countsOf({ wood: 3, brick: 1, ore: 1 }));
    expect(subtractCounts(addCounts(hand, COSTS.road), COSTS.road)).toEqual(hand);
  });

  it('maps terrain to resources, with no resource for the desert', () => {
    expect(terrainResource('forest')).toBe('wood');
    expect(terrainResource('mountains')).toBe('ore');
    expect(terrainResource('desert')).toBeNull();
  });
});

describe('rng', () => {
  it('is deterministic for a given state and stays in range', () => {
    expect(randomInt(42, 6)).toEqual(randomInt(42, 6));
    let state = 7;
    for (let i = 0; i < 200; i++) {
      const roll = randomInt(state, 6);
      expect(roll.value).toBeGreaterThanOrEqual(0);
      expect(roll.value).toBeLessThan(6);
      state = roll.rngState;
    }
  });

  it('shuffles to a deterministic permutation without mutating the input', () => {
    const items = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
    const first = shuffle(items, 123);
    expect(shuffle(items, 123)).toEqual(first);
    expect([...first.items].sort((a, b) => a - b)).toEqual(items);
    expect(items).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
  });
});

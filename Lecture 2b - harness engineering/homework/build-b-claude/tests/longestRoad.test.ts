import { describe, expect, it } from 'vitest';
import { roadLength } from '../src/engine/longestRoad';
import { victoryPoints } from '../src/engine/scoring';
import { TOPOLOGY } from '../src/engine/topology';
import type { CornerId, GameState } from '../src/engine/types';
import {
  buildPaid,
  buildRoadsAlong,
  findPath,
  newGame,
  runSetup,
  setupWithNetworks,
  sideApproach,
  startTurnOf,
  withNeighbours,
} from './helpers';

function lengths(state: GameState): number[] {
  return state.players.map((player) => roadLength(state, player.id));
}

/** A one-road network for a player who should stay out of the way of `corners`. */
function bystander(corners: CornerId[]): CornerId[] {
  return findPath({ length: 1, avoid: withNeighbours(corners) });
}

/** A neighbour of `corner` that is not on `path`, if any. */
function sideCorner(path: CornerId[], corner: CornerId): CornerId | undefined {
  return TOPOLOGY.cornerNeighbors[corner].find((c) => !path.includes(c));
}

/**
 * Player 1 holds Longest Road with a chain of `holderLength` roads. Player 2, on their own turn,
 * has `breakerLength` roads running from their settlement to the chain's corner `breakAt`, where
 * they can now settle. Their roads reach that corner from the side, not along the chain.
 */
function readyToBreak(holderLength: number, breakAt: number, breakerLength: number) {
  const chain = findPath({
    length: holderLength,
    accept: (path) => sideApproach(path, breakAt, breakerLength) !== null,
  });
  const approach = sideApproach(chain, breakAt, breakerLength)!;

  let state = startTurnOf(setupWithNetworks([chain, approach]), 0);
  state = buildRoadsAlong(state, chain);
  state = startTurnOf(state, 1);
  state = buildRoadsAlong(state, approach);
  return { state, target: chain[breakAt] };
}

describe('road length', () => {
  it('Scenario 16: Y-shaped 3+3+1 network has length 6', () => {
    const trunk = findPath({ length: 6, accept: (path) => sideCorner(path, path[3]) !== undefined });
    const spur = [trunk[3], sideCorner(trunk, trunk[3])!];
    let state = startTurnOf(setupWithNetworks([trunk, bystander([...trunk, ...spur])]), 0);

    state = buildRoadsAlong(state, trunk);
    expect(roadLength(state, 0)).toBe(6);
    state = buildRoadsAlong(state, spur);
    expect(state.roads.filter((owner) => owner === 0)).toHaveLength(8); // 7 in the Y + the second setup road
    expect(roadLength(state, 0)).toBe(6);
  });

  it('counts every road of a loop once, and a trail may pass a corner twice', () => {
    const hexCorners = TOPOLOGY.hexCorners[9]; // the centre hex: every corner has a third neighbour
    const ring = [...hexCorners, hexCorners[0]];
    const tail = [hexCorners[0], sideCorner(ring, hexCorners[0])!];
    let state = startTurnOf(setupWithNetworks([ring, bystander([...ring, ...tail])]), 0);

    state = buildRoadsAlong(state, ring);
    expect(roadLength(state, 0)).toBe(6);
    state = buildRoadsAlong(state, tail);
    expect(roadLength(state, 0)).toBe(7);
  });

  it("an opponent's settlement breaks the road but the player's own does not", () => {
    const chain = findPath({ length: 7 });
    let state = startTurnOf(setupWithNetworks([chain, bystander(chain)]), 0);
    state = buildRoadsAlong(state, chain);
    state = buildPaid(state, { type: 'placeSettlement', corner: chain[3] });
    expect(roadLength(state, 0)).toBe(7);

    const broken = readyToBreak(7, 3, 2);
    expect(lengths(broken.state)).toEqual([7, 2]);
    const after = buildPaid(broken.state, { type: 'placeSettlement', corner: broken.target });
    expect(lengths(after)).toEqual([4, 2]);
  });

  it('is 1 per player after setup, with no holder', () => {
    const state = runSetup(newGame(3));
    expect(lengths(state)).toEqual([1, 1, 1]);
    expect(state.longestRoadHolder).toBeNull();
  });
});

describe('Longest Road card', () => {
  it('Scenario 14: 4 roads give no card, the 5th grants it (+2 VP)', () => {
    const chain = findPath({ length: 5 });
    let state = startTurnOf(setupWithNetworks([chain, bystander(chain)]), 0);
    const pointsBefore = victoryPoints(state, 0);

    state = buildRoadsAlong(state, chain.slice(0, 5));
    expect(roadLength(state, 0)).toBe(4);
    expect(state.longestRoadHolder).toBeNull();
    expect(victoryPoints(state, 0)).toBe(pointsBefore);

    state = buildRoadsAlong(state, chain);
    expect(roadLength(state, 0)).toBe(5);
    expect(state.longestRoadHolder).toBe(0);
    expect(victoryPoints(state, 0)).toBe(pointsBefore + 2);
    expect(state.log).toContain('Player 1 takes Longest Road with a road of length 5');
  });

  it('Scenario 15: tying the holder does not take the card; exceeding does', () => {
    const first = findPath({ length: 5 });
    const second = findPath({ length: 6, avoid: withNeighbours(first) });
    let state = startTurnOf(setupWithNetworks([first, second]), 0);
    state = buildRoadsAlong(state, first);
    expect(state.longestRoadHolder).toBe(0);

    state = startTurnOf(state, 1);
    state = buildRoadsAlong(state, second.slice(0, 6));
    expect(lengths(state)).toEqual([5, 5]);
    expect(state.longestRoadHolder).toBe(0);

    const points = [victoryPoints(state, 0), victoryPoints(state, 1)];
    state = buildRoadsAlong(state, second);
    expect(lengths(state)).toEqual([5, 6]);
    expect(state.longestRoadHolder).toBe(1);
    expect([victoryPoints(state, 0), victoryPoints(state, 1)]).toEqual([points[0] - 2, points[1] + 2]);
    expect(state.log.at(-1)).toBe('Player 2 takes Longest Road with a road of length 6');
  });

  it('Scenario 17: opponent settlement splits a 6-chain; card reassigned to the unique leader', () => {
    const { state, target } = readyToBreak(6, 3, 5);
    expect(lengths(state)).toEqual([6, 5]);
    expect(state.longestRoadHolder).toBe(0);

    const after = buildPaid(state, { type: 'placeSettlement', corner: target });
    expect(lengths(after)).toEqual([3, 5]);
    expect(after.longestRoadHolder).toBe(1);
    expect(after.log.at(-1)).toBe('Player 2 takes Longest Road with a road of length 5');
  });

  it('Scenario 17: opponent settlement splits a 6-chain; card set aside when nobody has 5', () => {
    const { state, target } = readyToBreak(6, 3, 2);
    expect(state.longestRoadHolder).toBe(0);

    const after = buildPaid(state, { type: 'placeSettlement', corner: target });
    expect(lengths(after)).toEqual([3, 2]);
    expect(after.longestRoadHolder).toBeNull();
    expect(victoryPoints(after, 0)).toBe(victoryPoints(state, 0) - 2);
    expect(after.log.at(-1)).toBe('Player 1 loses Longest Road; the card is set aside');
  });

  it('the holder keeps the card when still tied for longest at 5 or more after a break', () => {
    const { state, target } = readyToBreak(7, 5, 5);
    expect(lengths(state)).toEqual([7, 5]);

    const after = buildPaid(state, { type: 'placeSettlement', corner: target });
    expect(lengths(after)).toEqual([5, 5]);
    expect(after.longestRoadHolder).toBe(0);
  });

  it('the card is set aside when the holder is tied for longest at 4 after a break (Decision 10)', () => {
    const { state, target } = readyToBreak(6, 4, 4);
    expect(state.longestRoadHolder).toBe(0);

    const after = buildPaid(state, { type: 'placeSettlement', corner: target });
    expect(lengths(after)).toEqual([4, 4]);
    expect(after.longestRoadHolder).toBeNull();
  });
});

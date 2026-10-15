import { describe, expect, it } from 'vitest';
import { desertHex } from '../src/engine/board';
import { applyAction, createGame } from '../src/engine/game';
import {
  buildError,
  legalCityCorners,
  legalRoadEdges,
  legalSettlementCorners,
  roadError,
  settlementError,
} from '../src/engine/placement';
import { emptyCounts, terrainResource, totalCards } from '../src/engine/resources';
import { setupOrder } from '../src/engine/setupPhase';
import { TOPOLOGY } from '../src/engine/topology';
import type { CornerId, GameState, ResourceCounts } from '../src/engine/types';
import { act, newGame, runSetup } from './helpers';

/** Places a setup settlement at `corner` and a road on its first legal edge. */
function placeSetupPair(state: GameState, corner: CornerId): GameState {
  const placed = act(state, { type: 'placeSettlement', corner });
  return act(placed, { type: 'placeRoad', edge: legalRoadEdges(placed)[0] });
}

/** Greedily picks corners that are pairwise at least two edges apart, starting with `first`. */
function spreadCorners(first: CornerId, count: number): CornerId[] {
  const picked = [first];
  for (let c = 0; c < TOPOLOGY.cornerHexes.length && picked.length < count; c++) {
    if (picked.every((p) => p !== c && !TOPOLOGY.cornerNeighbors[p].includes(c))) picked.push(c);
  }
  return picked;
}

/** The cards a second setup settlement on `corner` should pay: one per adjacent non-desert hex. */
function expectedSetupCards(state: GameState, corner: CornerId): ResourceCounts {
  const expected = emptyCounts();
  for (const hex of TOPOLOGY.cornerHexes[corner]) {
    const resource = terrainResource(state.board.hexes[hex].terrain);
    if (resource) expected[resource]++;
  }
  return expected;
}

function threeHexCornerOf(hex: number): CornerId {
  const corner = TOPOLOGY.hexCorners[hex].find((c) => TOPOLOGY.cornerHexes[c].length === 3);
  if (corner === undefined) throw new Error(`Hex ${hex} has no three-hex corner`);
  return corner;
}

describe('game creation', () => {
  it('starts in setup with player 1 placing a settlement and the robber on the desert', () => {
    const state = newGame(3, 42);
    expect(state.phase).toEqual({ kind: 'setup', turnIndex: 0, step: 'settlement', lastSettlement: null });
    expect(state.currentPlayer).toBe(0);
    expect(state.robberHex).toBe(desertHex(state.board));
    expect(state.board.hexes[state.robberHex].terrain).toBe('desert');
    expect(state.bank).toEqual({ wood: 19, brick: 19, sheep: 19, wheat: 19, ore: 19 });
    expect(state.buildings).toHaveLength(54);
    expect(state.roads).toHaveLength(72);
    for (const player of state.players) {
      expect(totalCards(player.hand)).toBe(0);
      expect(player.pieces).toEqual({ road: 15, settlement: 5, city: 4 });
    }
    expect(state.players.map((p) => p.name)).toEqual(['Player 1', 'Player 2', 'Player 3']);
  });

  it('accepts 2 to 4 players and rejects other counts', () => {
    expect(newGame(2).players).toHaveLength(2);
    expect(newGame(4).players).toHaveLength(4);
    expect(() => createGame({ seed: 1, playerNames: ['Solo'] })).toThrow();
    expect(() => createGame({ seed: 1, playerNames: ['A', 'B', 'C', 'D', 'E'] })).toThrow();
  });

  it('uses the same board for the same seed', () => {
    expect(newGame(2, 99).board).toEqual(newGame(2, 99).board);
  });
});

describe('setup phase', () => {
  it('Scenario 3: corners next to a setup settlement are not legal', () => {
    const corner = threeHexCornerOf(9);
    const before = newGame(3);
    expect(legalSettlementCorners(before)).toContain(corner);
    for (const neighbor of TOPOLOGY.cornerNeighbors[corner]) {
      expect(legalSettlementCorners(before)).toContain(neighbor);
    }

    const state = placeSetupPair(before, corner);
    const legal = legalSettlementCorners(state);
    expect(legal).not.toContain(corner);
    for (const neighbor of TOPOLOGY.cornerNeighbors[corner]) {
      expect(legal).not.toContain(neighbor);
      expect(applyAction(state, { type: 'placeSettlement', corner: neighbor })).toEqual({
        ok: false,
        error: 'Too close to another settlement or city',
      });
    }
    // A corner two edges away is still allowed.
    const twoAway = TOPOLOGY.cornerNeighbors[TOPOLOGY.cornerNeighbors[corner][0]].find((c) => c !== corner)!;
    expect(legal).toContain(twoAway);
    expect(legal).toHaveLength(54 - 1 - TOPOLOGY.cornerNeighbors[corner].length);
  });

  it('Scenario 4: only the second setup settlement grants resources', () => {
    const start = newGame(2, 7);
    const desert = desertHex(start.board);
    const desertCorner = threeHexCornerOf(desert);
    // Snake order for 2 players is P1, P2, P2, P1; P2's second settlement touches the desert.
    const [p2Second, p1First, p2First, p1Second] = spreadCorners(desertCorner, 4);

    let state = placeSetupPair(start, p1First);
    state = placeSetupPair(state, p2First);
    expect(state.players.map((p) => totalCards(p.hand))).toEqual([0, 0]);

    state = placeSetupPair(state, p2Second);
    const p2Expected = expectedSetupCards(state, p2Second);
    expect(totalCards(p2Expected)).toBe(2); // three hexes, one of them the desert
    expect(state.players[1].hand).toEqual(p2Expected);
    expect(totalCards(state.players[0].hand)).toBe(0);

    state = placeSetupPair(state, p1Second);
    const p1Expected = expectedSetupCards(state, p1Second);
    expect(state.players[0].hand).toEqual(p1Expected);
    expect(totalCards(state.bank)).toBe(95 - totalCards(p1Expected) - totalCards(p2Expected));
  });

  it('Scenario 5: 3-player snake order is 1,2,3,3,2,1', () => {
    expect(setupOrder(3)).toEqual([0, 1, 2, 2, 1, 0]);
    let state = newGame(3);
    const settlementTurns: number[] = [];
    while (state.phase.kind === 'setup') {
      settlementTurns.push(state.currentPlayer);
      state = act(state, { type: 'placeSettlement', corner: legalSettlementCorners(state)[0] });
      expect(state.currentPlayer).toBe(settlementTurns.at(-1)); // the same player places the road
      state = act(state, { type: 'placeRoad', edge: legalRoadEdges(state)[0] });
    }
    expect(settlementTurns.map((p) => p + 1)).toEqual([1, 2, 3, 3, 2, 1]);
  });

  it('snake order for 4 players is 1,2,3,4,4,3,2,1', () => {
    expect(setupOrder(4)).toEqual([0, 1, 2, 3, 3, 2, 1, 0]);
    expect(setupOrder(2)).toEqual([0, 1, 1, 0]);
  });

  it('a setup road must touch the settlement just placed', () => {
    const corner = threeHexCornerOf(9);
    const state = act(newGame(2), { type: 'placeSettlement', corner });
    expect([...legalRoadEdges(state)].sort((a, b) => a - b)).toEqual(
      [...TOPOLOGY.cornerEdges[corner]].sort((a, b) => a - b),
    );
    const farEdge = TOPOLOGY.edgeCorners.findIndex((pair) => !pair.includes(corner));
    expect(applyAction(state, { type: 'placeRoad', edge: farEdge })).toEqual({
      ok: false,
      error: 'Your setup road must touch the settlement you just placed',
    });
    expect(applyAction(state, { type: 'placeRoad', edge: TOPOLOGY.cornerEdges[corner][0] }).ok).toBe(true);
  });

  it('a second-round setup road may not hang off the first settlement instead', () => {
    // 2 players: P1, P2, P2, P1. Run P1's and P2's first and P2's second placements.
    const [p1First, p2First, p2Second, p1Second] = spreadCorners(threeHexCornerOf(9), 4);
    let state = placeSetupPair(newGame(2), p1First);
    state = placeSetupPair(state, p2First);
    state = placeSetupPair(state, p2Second);
    state = act(state, { type: 'placeSettlement', corner: p1Second });
    const freeEdgeAtFirst = TOPOLOGY.cornerEdges[p1First].find((e) => state.roads[e] === null)!;
    expect(roadError(state, 0, freeEdgeAtFirst)).toBe('Your setup road must touch the settlement you just placed');
    expect(legalRoadEdges(state)).not.toContain(freeEdgeAtFirst);
  });

  it('rejects a road before a settlement and a second settlement before the road', () => {
    const start = newGame(2);
    expect(applyAction(start, { type: 'placeRoad', edge: 0 })).toEqual({ ok: false, error: 'Place a settlement first' });
    expect(legalRoadEdges(start)).toEqual([]);

    const placed = act(start, { type: 'placeSettlement', corner: 0 });
    const farCorner = spreadCorners(0, 2)[1];
    expect(applyAction(placed, { type: 'placeSettlement', corner: farCorner })).toEqual({
      ok: false,
      error: 'Place a road next to your settlement first',
    });
    expect(legalSettlementCorners(placed)).toEqual([]);
  });

  it('rejects occupied corners, occupied edges and unknown IDs', () => {
    const state = placeSetupPair(newGame(2), 0);
    expect(applyAction(state, { type: 'placeSettlement', corner: 0 })).toEqual({
      ok: false,
      error: 'That corner is already occupied',
    });
    expect(applyAction(state, { type: 'placeSettlement', corner: 54 })).toEqual({ ok: false, error: 'No such corner' });
    const usedEdge = state.roads.findIndex((owner) => owner === 0);
    const next = act(state, { type: 'placeSettlement', corner: spreadCorners(0, 2)[1] });
    expect(roadError(next, 1, usedEdge)).toBe('That edge already has a road');
    expect(roadError(next, 1, 72)).toBe('No such edge');
  });

  it('rejects actions from other phases during setup', () => {
    const state = newGame(2);
    for (const action of [{ type: 'roll' }, { type: 'endTurn' }, { type: 'placeCity', corner: 0 }] as const) {
      expect(applyAction(state, action)).toEqual({ ok: false, error: 'Finish setup first' });
    }
  });

  it('never modifies the input state', () => {
    const state = newGame(2);
    const snapshot = structuredClone(state);
    act(state, { type: 'placeSettlement', corner: 0 });
    applyAction(state, { type: 'placeRoad', edge: 0 });
    expect(state).toEqual(snapshot);
  });

  it('after setup: player 1 rolls, each player has 3 settlements and 13 roads left', () => {
    for (const players of [2, 3, 4]) {
      const state = runSetup(newGame(players, 5));
      expect(state.phase).toEqual({ kind: 'roll' });
      expect(state.currentPlayer).toBe(0);
      for (const player of state.players) {
        expect(player.pieces).toEqual({ road: 13, settlement: 3, city: 4 });
      }
      expect(state.buildings.filter((b) => b !== null)).toHaveLength(players * 2);
      expect(state.roads.filter((r) => r !== null)).toHaveLength(players * 2);
      expect(applyAction(state, { type: 'placeSettlement', corner: 0 })).toEqual({
        ok: false,
        error: 'Roll the dice first',
      });
    }
  });

  it('runSetup uses the given picks in snake order', () => {
    const [a, b, c, d] = spreadCorners(threeHexCornerOf(9), 4);
    const state = runSetup(newGame(2), [{ corner: a }, { corner: b }, { corner: c }, { corner: d }]);
    expect([a, b, c, d].map((corner) => state.buildings[corner]?.owner)).toEqual([0, 1, 1, 0]);
  });
});

describe('placement queries', () => {
  it('buildError is null during setup, since setup pieces are free', () => {
    const state = newGame(2);
    expect(buildError(state, 'road')).toBeNull();
    expect(buildError(state, 'settlement')).toBeNull();
  });

  it('buildError reports a city the player cannot pay for after setup', () => {
    const state = runSetup(newGame(2));
    expect(buildError(state, 'city')).toBe('Not enough resources'); // at most 3 cards from setup
  });

  it('offers no build spots outside setup and the main phase', () => {
    const state = runSetup(newGame(2));
    expect(legalSettlementCorners(state)).toEqual([]);
    expect(legalRoadEdges(state)).toEqual([]);
    expect(legalCityCorners(state)).toEqual([]);
  });

  it('in normal play a settlement needs its own road and a road must connect to the network', () => {
    const corner = threeHexCornerOf(9);
    const state = runSetup(newGame(2), [{ corner }]);
    const ownRoad = TOPOLOGY.cornerEdges[corner].find((e) => state.roads[e] === 0)!;
    const roadEnd = TOPOLOGY.edgeCorners[ownRoad].find((c) => c !== corner)!;

    // An edge continuing from the road's far end connects; one far from P1's pieces does not.
    const continuing = TOPOLOGY.cornerEdges[roadEnd].find((e) => e !== ownRoad && state.roads[e] === null)!;
    expect(roadError(state, 0, continuing)).toBeNull();
    const isolated = TOPOLOGY.edgeCorners.findIndex((pair, e) =>
      pair.every((c) => state.buildings[c] === null && TOPOLOGY.cornerEdges[c].every((x) => state.roads[x] === null)) &&
      state.roads[e] === null,
    );
    expect(roadError(state, 0, isolated)).toBe('A road must connect to your own road, settlement, or city');

    // A corner that passes the distance rule but touches none of P1's roads.
    const roadless = TOPOLOGY.cornerNeighbors.findIndex(
      (neighbors, c) =>
        [c, ...neighbors].every((x) => state.buildings[x] === null) &&
        TOPOLOGY.cornerEdges[c].every((e) => state.roads[e] !== 0),
    );
    expect(settlementError(state, 0, roadless)).toBe('A settlement must touch one of your roads');
    expect(settlementError(state, 0, roadEnd)).toBe('Too close to another settlement or city');
  });
});

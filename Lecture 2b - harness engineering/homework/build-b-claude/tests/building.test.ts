import { describe, expect, it } from 'vitest';
import { applyAction } from '../src/engine/game';
import { buildError, legalCityCorners, legalRoadEdges, legalSettlementCorners } from '../src/engine/placement';
import { COSTS, addCounts, countsOf, emptyCounts, subtractCounts, terrainResource } from '../src/engine/resources';
import { victoryPoints } from '../src/engine/scoring';
import { TOPOLOGY, edgeBetween } from '../src/engine/topology';
import type { CornerId, EdgeId, GameState, HexId, Resource } from '../src/engine/types';
import {
  act,
  buildPaid,
  giveCards,
  handDelta,
  newGame,
  roadsToOpenCorner,
  runSetup,
  settleNearby,
  toMainPhase,
} from './helpers';

const SEED = 3;

function edge(a: CornerId, b: CornerId): EdgeId {
  const id = edgeBetween(a, b);
  if (id === null) throw new Error(`Corners ${a} and ${b} are not adjacent`);
  return id;
}

/** Hexes producing any of `resources`. */
function hexesProducing(state: GameState, resources: Resource[]): HexId[] {
  return state.board.hexes.filter((h) => {
    const resource = terrainResource(h.terrain);
    return resource !== null && resources.includes(resource);
  }).map((h) => h.id);
}

/** A 2-player game in player id 0's main phase, where setup gave nobody wood or brick. */
function mainPhaseWithoutRoadCards(): GameState {
  const base = newGame(2, SEED);
  const state = toMainPhase(runSetup(base, [], { avoidHexes: hexesProducing(base, ['wood', 'brick']) }));
  expect(state.players[0].hand.wood + state.players[0].hand.brick).toBe(0);
  return state;
}

/** Sets the current player's count of `resource` to exactly `count` (count must be at least what they hold). */
function holdExactly(state: GameState, resource: Resource, count: number): GameState {
  const held = state.players[state.currentPlayer].hand[resource];
  if (held > count) throw new Error(`Player already holds ${held} ${resource}`);
  return giveCards(state, state.currentPlayer, { [resource]: count - held });
}

/**
 * Player id 0's setup settlement S with road S-A, and an interior corner X one edge past A whose
 * other edges lead to Y and Z.
 */
function roadThroughCorner() {
  const x = TOPOLOGY.hexCorners[9][0];
  const a = TOPOLOGY.cornerNeighbors[x][0];
  const s = TOPOLOGY.cornerNeighbors[a].find((c) => c !== x)!;
  const [y, z] = TOPOLOGY.cornerNeighbors[x].filter((c) => c !== a);
  return { s, a, x, y, z, avoidHexes: TOPOLOGY.cornerHexes[x] };
}

describe('building', () => {
  it('Scenario 12: road cannot pass through an opponent\'s settlement', () => {
    const { s, a, x, y, z, avoidHexes } = roadThroughCorner();
    const picks = [{ corner: s, edge: edge(s, a) }, { corner: x, edge: edge(x, z) }];
    let state = toMainPhase(runSetup(newGame(2, SEED), picks, { avoidHexes }));
    expect(state.buildings[x]).toEqual({ owner: 1, kind: 'settlement' });

    // Player id 0 extends their road up to the opponent's settlement at X...
    state = buildPaid(state, { type: 'placeRoad', edge: edge(a, x) });
    expect(state.roads[edge(a, x)]).toBe(0);

    // ...but cannot continue through X.
    const paid = giveCards(state, 0, COSTS.road);
    expect(legalRoadEdges(paid)).not.toContain(edge(x, y));
    expect(applyAction(paid, { type: 'placeRoad', edge: edge(x, y) })).toEqual({
      ok: false,
      error: 'A road must connect to your own road, settlement, or city',
    });
  });

  it('Scenario 12 (other side): the same road is legal when the corner is empty', () => {
    const { s, a, x, y, avoidHexes } = roadThroughCorner();
    let state = toMainPhase(runSetup(newGame(2, SEED), [{ corner: s, edge: edge(s, a) }], { avoidHexes }));
    expect(state.buildings[x]).toBeNull();

    state = buildPaid(state, { type: 'placeRoad', edge: edge(a, x) });
    expect(legalRoadEdges(giveCards(state, 0, COSTS.road))).toContain(edge(x, y));
    state = buildPaid(state, { type: 'placeRoad', edge: edge(x, y) });
    expect(state.roads[edge(x, y)]).toBe(0);
  });

  it('Scenario 13: building and trading before rolling are rejected', () => {
    let state = runSetup(newGame(2, SEED));
    const ownSettlement = state.buildings.findIndex((b) => b?.owner === 0);
    state = giveCards(state, 0, addCounts(addCounts(COSTS.road, COSTS.settlement), countsOf({ ore: 3, wheat: 2, sheep: 4 })));
    const road = TOPOLOGY.cornerEdges[ownSettlement].find((e) => state.roads[e] === null)!;
    const attempts = [
      { type: 'placeRoad', edge: road },
      { type: 'placeSettlement', corner: 0 },
      { type: 'placeCity', corner: ownSettlement },
      { type: 'bankTrade', give: 'sheep', get: 'ore' },
    ] as const;

    expect(state.phase).toEqual({ kind: 'roll' });
    for (const action of attempts) {
      expect(applyAction(state, action)).toEqual({ ok: false, error: 'Roll the dice first' });
    }
    expect(legalRoadEdges(state)).toEqual([]);
    expect(legalCityCorners(state)).toEqual([]);

    // After rolling, the same road, city, and trade succeed.
    const rolled = toMainPhase(state);
    for (const action of [attempts[0], attempts[2], attempts[3]]) {
      expect(applyAction(rolled, action).ok).toBe(true);
    }
  });

  it('Scenario 18: 6th settlement rejected until a city upgrade frees one', () => {
    let state = toMainPhase(runSetup(newGame(2, SEED)));
    expect(state.players[0].pieces.settlement).toBe(3);
    for (let i = 0; i < 3; i++) state = settleNearby(state).state;
    expect(state.buildings.filter((b) => b?.owner === 0)).toHaveLength(5);
    expect(state.players[0].pieces.settlement).toBe(0);

    // A sixth spot is reachable and the player can pay, but has no settlement left.
    const { state: withRoads, corner } = roadsToOpenCorner(state);
    const paid = giveCards(withRoads, 0, COSTS.settlement);
    expect(buildError(paid, 'settlement')).toBe('No settlements left');
    expect(legalSettlementCorners(paid)).toEqual([]);
    expect(applyAction(paid, { type: 'placeSettlement', corner })).toEqual({ ok: false, error: 'No settlements left' });

    // Upgrading a settlement returns its piece, and the sixth settlement can then be built.
    const upgradeAt = paid.buildings.findIndex((b) => b?.owner === 0);
    const upgraded = buildPaid(paid, { type: 'placeCity', corner: upgradeAt });
    expect(upgraded.players[0].pieces.settlement).toBe(1);
    expect(legalSettlementCorners(upgraded)).toContain(corner);
    const built = act(upgraded, { type: 'placeSettlement', corner });
    expect(built.buildings[corner]).toEqual({ owner: 0, kind: 'settlement' });
    expect(built.players[0].pieces.settlement).toBe(0);
  });

  it('a build deducts its cost and returns it to the bank', () => {
    const state = giveCards(mainPhaseWithoutRoadCards(), 0, COSTS.road);
    const road = legalRoadEdges(state)[0];
    const built = act(state, { type: 'placeRoad', edge: road });
    expect(handDelta(state, built, 0)).toEqual(subtractCounts(emptyCounts(), COSTS.road));
    expect(built.bank).toEqual(addCounts(state.bank, COSTS.road));
    expect(built.roads[road]).toBe(0);
    expect(built.players[0].pieces.road).toBe(state.players[0].pieces.road - 1);
  });

  it('a player who cannot pay gets a buildError and no legal spots; after receiving the cards both allow the build', () => {
    const state = mainPhaseWithoutRoadCards();
    expect(buildError(state, 'road')).toBe('Not enough resources');
    expect(legalRoadEdges(state)).toEqual([]);
    const ownSettlement = state.buildings.findIndex((b) => b?.owner === 0);
    const road = TOPOLOGY.cornerEdges[ownSettlement].find((e) => state.roads[e] === null)!;
    expect(applyAction(state, { type: 'placeRoad', edge: road })).toEqual({ ok: false, error: 'Not enough resources' });

    const paid = giveCards(state, 0, COSTS.road);
    expect(buildError(paid, 'road')).toBeNull();
    expect(legalRoadEdges(paid)).toContain(road);
    expect(act(paid, { type: 'placeRoad', edge: road }).roads[road]).toBe(0);
  });

  it('a city replaces your own settlement, returns the settlement piece, and is worth 2', () => {
    const state = toMainPhase(runSetup(newGame(2, SEED)));
    const own = state.buildings.findIndex((b) => b?.owner === 0);
    const opponents = state.buildings.findIndex((b) => b?.owner === 1);
    const paid = giveCards(state, 0, COSTS.city);
    expect(legalCityCorners(paid).sort()).toEqual(
      state.buildings.flatMap((b, c) => (b?.owner === 0 ? [c] : [])).sort(),
    );
    expect(applyAction(paid, { type: 'placeCity', corner: opponents })).toEqual({
      ok: false,
      error: 'A city must replace one of your settlements',
    });

    const built = act(paid, { type: 'placeCity', corner: own });
    expect(built.buildings[own]).toEqual({ owner: 0, kind: 'city' });
    expect(built.players[0].pieces).toMatchObject({ settlement: 4, city: 3 });
    expect(victoryPoints(built, 0)).toBe(victoryPoints(state, 0) + 1);
    expect(applyAction(giveCards(built, 0, COSTS.city), { type: 'placeCity', corner: own })).toMatchObject({ ok: false });
  });

  it('a normal settlement needs its own road', () => {
    const state = giveCards(toMainPhase(runSetup(newGame(2, SEED))), 0, COSTS.settlement);
    const roadless = TOPOLOGY.cornerNeighbors.findIndex(
      (neighbors, c) =>
        [c, ...neighbors].every((x) => state.buildings[x] === null) &&
        TOPOLOGY.cornerEdges[c].every((e) => state.roads[e] !== 0),
    );
    expect(applyAction(state, { type: 'placeSettlement', corner: roadless })).toEqual({
      ok: false,
      error: 'A settlement must touch one of your roads',
    });
    const { state: withRoads, corner } = roadsToOpenCorner(state);
    expect(act(withRoads, { type: 'placeSettlement', corner }).buildings[corner]).toEqual({ owner: 0, kind: 'settlement' });
  });

  it('the 15-road limit is enforced', () => {
    let state = toMainPhase(runSetup(newGame(2, SEED)));
    for (let i = 0; i < 13; i++) {
      state = buildPaid(state, { type: 'placeRoad', edge: legalRoadEdges(giveCards(state, 0, COSTS.road))[0] });
    }
    expect(state.roads.filter((r) => r === 0)).toHaveLength(15);
    const paid = giveCards(state, 0, COSTS.road);
    expect(buildError(paid, 'road')).toBe('No roads left');
    expect(legalRoadEdges(paid)).toEqual([]);
    const free = TOPOLOGY.edgeCorners.findIndex((_, e) => state.roads[e] === null);
    expect(applyAction(paid, { type: 'placeRoad', edge: free })).toEqual({ ok: false, error: 'No roads left' });
  });

  it('the 4-city limit is enforced', () => {
    let state = toMainPhase(runSetup(newGame(2, SEED)));
    for (let i = 0; i < 2; i++) state = settleNearby(state).state;
    for (const corner of state.buildings.flatMap((b, c) => (b?.owner === 0 ? [c] : []))) {
      state = buildPaid(state, { type: 'placeCity', corner });
    }
    expect(state.players[0].pieces.city).toBe(0);
    expect(victoryPoints(state, 0)).toBe(8);

    const { state: settled, corner } = settleNearby(state);
    const paid = giveCards(settled, 0, COSTS.city);
    expect(buildError(paid, 'city')).toBe('No cities left');
    expect(legalCityCorners(paid)).toEqual([]);
    expect(applyAction(paid, { type: 'placeCity', corner })).toEqual({ ok: false, error: 'No cities left' });
  });
});

describe('bank trade', () => {
  it('Scenario 19: 4 wood trades for 1 chosen resource; 3 wood is rejected', () => {
    const state = toMainPhase(runSetup(newGame(2, SEED)));

    const four = holdExactly(state, 'wood', 4);
    const traded = act(four, { type: 'bankTrade', give: 'wood', get: 'ore' });
    expect(handDelta(four, traded, 0)).toEqual(countsOf({ wood: -4, ore: 1 }));
    expect(traded.bank.wood).toBe(four.bank.wood + 4);
    expect(traded.bank.ore).toBe(four.bank.ore - 1);

    const three = holdExactly(state, 'wood', 3);
    expect(applyAction(three, { type: 'bankTrade', give: 'wood', get: 'ore' })).toEqual({
      ok: false,
      error: 'You need 4 wood to trade',
    });
  });

  it('fails when the bank is out of the requested resource', () => {
    let state = holdExactly(toMainPhase(runSetup(newGame(2, SEED))), 'wood', 4);
    state = giveCards(state, 1, { ore: state.bank.ore });
    expect(state.bank.ore).toBe(0);
    expect(applyAction(state, { type: 'bankTrade', give: 'wood', get: 'ore' })).toEqual({
      ok: false,
      error: 'The bank has no ore left',
    });
    expect(applyAction(state, { type: 'bankTrade', give: 'wood', get: 'wheat' }).ok).toBe(true);
  });

  it('fails when giving and getting the same resource', () => {
    const state = holdExactly(toMainPhase(runSetup(newGame(2, SEED))), 'wood', 4);
    expect(applyAction(state, { type: 'bankTrade', give: 'wood', get: 'wood' })).toEqual({
      ok: false,
      error: 'Choose a different resource to receive',
    });
  });
});

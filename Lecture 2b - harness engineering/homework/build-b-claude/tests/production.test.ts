import { describe, expect, it } from 'vitest';
import { applyAction } from '../src/engine/game';
import { computeProduction } from '../src/engine/production';
import { addCounts, countsOf, emptyCounts, terrainResource, totalCards } from '../src/engine/resources';
import { TOPOLOGY } from '../src/engine/topology';
import type { CornerId, GameState, HexId, Resource, ResourceCounts } from '../src/engine/types';
import { act, buildPaid, forceRoll, giveCards, handDelta, newGame, runSetup, toMainPhase } from './helpers';

const SEED = 7;

/** All hexes whose number token is one of `numbers`. */
function hexesNumbered(state: GameState, numbers: number[]): HexId[] {
  return state.board.hexes.filter((h) => h.number !== null && numbers.includes(h.number)).map((h) => h.id);
}

/** Corners of `hex` where no other touching hex carries the same number, so a roll pays only from `hex`. */
function cornersProducingOnlyFrom(state: GameState, hex: HexId): CornerId[] {
  const number = state.board.hexes[hex].number;
  return TOPOLOGY.hexCorners[hex].filter((c) =>
    TOPOLOGY.cornerHexes[c].every((h) => h === hex || state.board.hexes[h].number !== number),
  );
}

function resourceOf(state: GameState, hex: HexId): Resource {
  const resource = terrainResource(state.board.hexes[hex].terrain);
  if (resource === null) throw new Error(`Hex ${hex} is the desert`);
  return resource;
}

/** One card of each listed hex's resource. */
function resourcesOf(state: GameState, hexes: HexId[]): ResourceCounts {
  const counts = emptyCounts();
  for (const h of hexes) counts[resourceOf(state, h)]++;
  return counts;
}

function isFarFrom(corner: CornerId, others: CornerId[]): boolean {
  return others.every((o) => o !== corner && !TOPOLOGY.cornerNeighbors[o].includes(corner));
}

/** Drains the bank's `resource` down to `left` by giving the rest to `player`. */
function drainBank(state: GameState, resource: Resource, left: number, player = 1): GameState {
  return giveCards(state, player, { [resource]: state.bank[resource] - left });
}

interface ShortageSetup {
  state: GameState;
  number: number;
  shared: Resource;
  solo: Resource;
}

/**
 * A 2-player game after setup where rolling `number` owes player id 0 one `shared` card (hex A)
 * and one `solo` card (hex B), owes player id 1 one `shared` card (hex A), and owes nothing else.
 */
function shortageSetup(): ShortageSetup {
  const base = newGame(2, SEED);
  for (let number = 2; number <= 12; number++) {
    const hexes = hexesNumbered(base, [number]);
    for (const a of hexes) {
      for (const b of hexes) {
        if (a === b || resourceOf(base, a) === resourceOf(base, b)) continue;
        const onA = cornersProducingOnlyFrom(base, a);
        const p1A = onA[0];
        const p2A = onA.find((c) => isFarFrom(c, [p1A]));
        if (p1A === undefined || p2A === undefined) continue;
        const p1B = cornersProducingOnlyFrom(base, b).find((c) => isFarFrom(c, [p1A, p2A]));
        if (p1B === undefined) continue;
        // Snake order for 2 players is 1, 2, 2, 1.
        const picks = [{ corner: p1A }, { corner: p2A }, undefined, { corner: p1B }];
        const state = runSetup(base, picks, { avoidHexes: hexes });
        return { state, number, shared: resourceOf(base, a), solo: resourceOf(base, b) };
      }
    }
  }
  throw new Error(`Seed ${SEED} has no number on two hexes with different resources`);
}

describe('production', () => {
  it('Scenario 6: shared-corner settlement produces from all three hexes', () => {
    const base = newGame(2, SEED);
    const corner = TOPOLOGY.cornerHexes.findIndex(
      (hexes) => hexes.length === 3 && hexes.every((h) => base.board.hexes[h].number !== null),
    );
    const hexes = TOPOLOGY.cornerHexes[corner];
    const numbers = hexes.map((h) => base.board.hexes[h].number as number);
    const state = runSetup(base, [{ corner }], { avoidHexes: hexesNumbered(base, numbers) });

    let received = emptyCounts();
    for (const number of new Set(numbers)) {
      const rolled = toMainPhase(state, number);
      const expected = resourcesOf(base, hexes.filter((h) => base.board.hexes[h].number === number));
      expect(handDelta(state, rolled, 0)).toEqual(expected);
      expect(handDelta(state, rolled, 1)).toEqual(emptyCounts());
      received = addCounts(received, expected);
    }
    // Across the rolls, the corner earned one card from each of its three hexes.
    expect(received).toEqual(resourcesOf(base, hexes));
    expect(totalCards(received)).toBe(3);
  });

  it('Scenario 8: robber hex produces nothing', () => {
    const base = newGame(2, SEED);
    const hex = base.board.hexes.find((h) => h.number !== null && cornersProducingOnlyFrom(base, h.id).length > 0)!.id;
    const number = base.board.hexes[hex].number as number;
    const corner = cornersProducingOnlyFrom(base, hex)[0];
    const state = runSetup(base, [{ corner }], { avoidHexes: hexesNumbered(base, [number]) });

    // Without the robber, the hex pays player id 0.
    const unblocked = toMainPhase(state, number);
    expect(handDelta(state, unblocked, 0)).toEqual(countsOf({ [resourceOf(base, hex)]: 1 }));

    // Player id 0 is the only builder on the hex, so moving the robber there steals nothing.
    let blocked = forceRoll(state, 7);
    blocked = act(blocked, { type: 'moveRobber', hex });
    expect(blocked.phase).toEqual({ kind: 'main' });
    blocked = act(blocked, { type: 'endTurn' });

    const rolled = forceRoll(blocked, number);
    expect(rolled.players.map((p) => p.hand)).toEqual(blocked.players.map((p) => p.hand));
    expect(rolled.bank).toEqual(blocked.bank);
  });

  describe('bank shortage (settlements only)', () => {
    it('pays everyone when the bank holds exactly what is owed', () => {
      const { state, number, shared, solo } = shortageSetup();
      const drained = drainBank(state, shared, 2);
      const rolled = toMainPhase(drained, number);
      expect(handDelta(drained, rolled, 0)).toEqual(countsOf({ [shared]: 1, [solo]: 1 }));
      expect(handDelta(drained, rolled, 1)).toEqual(countsOf({ [shared]: 1 }));
      expect(rolled.bank[shared]).toBe(0);
    });

    it('pays neither of two owed players when the bank is short, but still pays other resources', () => {
      const { state, number, shared, solo } = shortageSetup();
      const drained = drainBank(state, shared, 1);
      const rolled = toMainPhase(drained, number);
      expect(handDelta(drained, rolled, 0)).toEqual(countsOf({ [solo]: 1 }));
      expect(handDelta(drained, rolled, 1)).toEqual(emptyCounts());
      expect(rolled.bank[shared]).toBe(1);
    });

    it('pays a single owed player nothing when the bank is empty', () => {
      const { state, number, shared, solo } = shortageSetup();
      const drained = drainBank(state, solo, 0);
      const rolled = toMainPhase(drained, number);
      expect(handDelta(drained, rolled, 0)).toEqual(countsOf({ [shared]: 1 }));
      expect(handDelta(drained, rolled, 1)).toEqual(countsOf({ [shared]: 1 }));
      expect(rolled.bank[solo]).toBe(0);
    });

    it('computeProduction reports the shortage-adjusted payout without changing state', () => {
      const { state, number, shared, solo } = shortageSetup();
      const drained = drainBank(state, shared, 1);
      expect(computeProduction(drained, number)).toEqual([countsOf({ [solo]: 1 }), emptyCounts()]);
    });
  });
});

/** A non-7 total other than `number`, for rolls that should not matter. */
function otherTotal(number: number): number {
  return number === 2 ? 3 : 2;
}

interface FieldsHex {
  base: GameState;
  number: number;
  /** Two corners of the fields hex, not adjacent, that produce only from it on its number. */
  corners: [CornerId, CornerId];
}

/** Finds a seed whose board has a fields hex with two separate corners that only it pays on its number. */
function fieldsHexWithTwoSpots(): FieldsHex {
  for (let seed = SEED; seed < SEED + 50; seed++) {
    const base = newGame(2, seed);
    for (const hex of base.board.hexes) {
      if (hex.terrain !== 'fields') continue;
      const spots = cornersProducingOnlyFrom(base, hex.id);
      const second = spots.find((c) => isFarFrom(c, [spots[0]]));
      if (second !== undefined) return { base, number: hex.number as number, corners: [spots[0], second] };
    }
  }
  throw new Error('No suitable fields hex found');
}

describe('production with cities', () => {
  it('Scenario 7: city produces 2 per roll', () => {
    const base = newGame(2, SEED);
    const hex = base.board.hexes.find((h) => h.number !== null && cornersProducingOnlyFrom(base, h.id).length > 0)!.id;
    const number = base.board.hexes[hex].number as number;
    const corner = cornersProducingOnlyFrom(base, hex)[0];
    const resource = resourceOf(base, hex);
    const state = toMainPhase(runSetup(base, [{ corner }], { avoidHexes: hexesNumbered(base, [number]) }), otherTotal(number));

    // As a settlement the corner earns 1; after upgrading to a city it earns 2.
    const settlementTurn = act(state, { type: 'endTurn' });
    expect(handDelta(settlementTurn, forceRoll(settlementTurn, number), 0)).toEqual(countsOf({ [resource]: 1 }));

    const cityTurn = act(buildPaid(state, { type: 'placeCity', corner }), { type: 'endTurn' });
    const rolled = forceRoll(cityTurn, number);
    expect(handDelta(cityTurn, rolled, 0)).toEqual(countsOf({ [resource]: 2 }));
    expect(handDelta(cityTurn, rolled, 1)).toEqual(emptyCounts());
    expect(rolled.bank[resource]).toBe(cityTurn.bank[resource] - 2);
  });

  it('Scenario 11: bank shortage pays nobody when two players are each owed 2 wheat and the bank has 2', () => {
    const { base, number, corners } = fieldsHexWithTwoSpots();
    const [mine, theirs] = corners;
    const other = otherTotal(number);
    let state = runSetup(base, [{ corner: mine }, { corner: theirs }], { avoidHexes: hexesNumbered(base, [number]) });
    state = act(buildPaid(toMainPhase(state, other), { type: 'placeCity', corner: mine }), { type: 'endTurn' });
    state = act(buildPaid(toMainPhase(state, other), { type: 'placeCity', corner: theirs }), { type: 'endTurn' });
    expect(computeProduction(state, number)).toEqual([countsOf({ wheat: 2 }), countsOf({ wheat: 2 })]);

    const drained = drainBank(state, 'wheat', 2);
    const rolled = forceRoll(drained, number);
    expect(handDelta(drained, rolled, 0)).toEqual(emptyCounts());
    expect(handDelta(drained, rolled, 1)).toEqual(emptyCounts());
    expect(rolled.bank.wheat).toBe(2);
  });

  it('Scenario 11: a single player owed 3 wheat receives the 2 the bank has left', () => {
    const { base, number, corners } = fieldsHexWithTwoSpots();
    const [city, settlement] = corners;
    // Snake order 1, 2, 2, 1: player id 0 places both settlements on the fields hex.
    const picks = [{ corner: city }, undefined, undefined, { corner: settlement }];
    let state = runSetup(base, picks, { avoidHexes: hexesNumbered(base, [number]) });
    state = act(buildPaid(toMainPhase(state, otherTotal(number)), { type: 'placeCity', corner: city }), { type: 'endTurn' });
    expect(computeProduction(state, number)).toEqual([countsOf({ wheat: 3 }), emptyCounts()]);

    const drained = drainBank(state, 'wheat', 2);
    const rolled = forceRoll(drained, number);
    expect(handDelta(drained, rolled, 0)).toEqual(countsOf({ wheat: 2 }));
    expect(handDelta(drained, rolled, 1)).toEqual(emptyCounts());
    expect(rolled.bank.wheat).toBe(0);
  });
});

describe('rolling and turns', () => {
  it('a forced roll is used once and shown as two dice', () => {
    const state = runSetup(newGame(2, SEED));
    const rolled = forceRoll(state, 8);
    expect(rolled.lastRoll).toEqual([6, 2]);
    expect(rolled.forcedRoll).toBeNull();
    expect(forceRoll(state, 2).lastRoll).toEqual([1, 1]);
    expect(forceRoll(state, 12).lastRoll).toEqual([6, 6]);
  });

  it('forced rolls outside 2..12 are rejected', () => {
    const state = runSetup(newGame(2, SEED));
    for (const total of [1, 13, 7.5]) {
      expect(applyAction(state, { type: 'debugForceRoll', total })).toMatchObject({ ok: false });
    }
  });

  it('random rolls are two dice from 1 to 6 and reproducible from the seed', () => {
    const first = act(runSetup(newGame(2, SEED)), { type: 'roll' });
    const second = act(runSetup(newGame(2, SEED)), { type: 'roll' });
    expect(first.lastRoll).toEqual(second.lastRoll);
    for (const die of first.lastRoll!) {
      expect(die).toBeGreaterThanOrEqual(1);
      expect(die).toBeLessThanOrEqual(6);
    }
  });

  it('a player cannot roll twice or end the turn before rolling', () => {
    const state = runSetup(newGame(2, SEED));
    expect(applyAction(state, { type: 'endTurn' })).toEqual({ ok: false, error: 'Roll the dice first' });
    const rolled = toMainPhase(state);
    expect(applyAction(rolled, { type: 'roll' })).toEqual({ ok: false, error: 'You have already rolled this turn' });
  });

  it('ending the turn passes play to the next player, wrapping after the last', () => {
    let state = runSetup(newGame(3, SEED));
    for (const expected of [1, 2, 0]) {
      state = act(toMainPhase(state), { type: 'endTurn' });
      expect(state.currentPlayer).toBe(expected);
      expect(state.phase).toEqual({ kind: 'roll' });
    }
  });

  it('debug give moves cards from the bank and fails if the bank has too few', () => {
    const state = runSetup(newGame(2, SEED));
    const given = giveCards(state, 1, { ore: 3 });
    expect(handDelta(state, given, 1)).toEqual(countsOf({ ore: 3 }));
    expect(given.bank.ore).toBe(state.bank.ore - 3);
    const tooMany = applyAction(state, { type: 'debugGiveResource', player: 1, resource: 'ore', amount: state.bank.ore + 1 });
    expect(tooMany).toMatchObject({ ok: false });
    expect(applyAction(state, { type: 'debugGiveResource', player: 5, resource: 'ore', amount: 1 })).toMatchObject({ ok: false });
  });
});

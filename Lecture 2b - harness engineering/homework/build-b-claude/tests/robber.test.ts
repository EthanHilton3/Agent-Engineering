import { describe, expect, it } from 'vitest';
import { desertHex } from '../src/engine/board';
import { applyAction } from '../src/engine/game';
import { legalRobberHexes } from '../src/engine/placement';
import { discardAmount } from '../src/engine/production';
import { RESOURCES, addCounts, emptyCounts, subtractCounts, totalCards } from '../src/engine/resources';
import { TOPOLOGY } from '../src/engine/topology';
import type { GameState, HexId, PlayerId, ResourceCounts } from '../src/engine/types';
import { act, forceRoll, giveCards, handDelta, newGame, runSetup, toMainPhase } from './helpers';

const SEED = 11;

/** Gives `player` wood until they hold exactly `total` cards. */
function topUpTo(state: GameState, player: PlayerId, total: number): GameState {
  const missing = total - totalCards(state.players[player].hand);
  if (missing < 0) throw new Error(`Player ${player} already holds more than ${total} cards`);
  return giveCards(state, player, { wood: missing });
}

/** Some `count` cards from `hand`, taken resource by resource. */
function someCards(hand: ResourceCounts, count: number): ResourceCounts {
  const cards = emptyCounts();
  let left = count;
  for (const r of RESOURCES) {
    cards[r] = Math.min(hand[r], left);
    left -= cards[r];
  }
  return cards;
}

/** Returns all of `player`'s cards to the bank. No public action can do this, so the state is edited directly. */
function withEmptyHand(state: GameState, player: PlayerId): GameState {
  const copy = structuredClone(state);
  copy.bank = addCounts(copy.bank, copy.players[player].hand);
  copy.players[player].hand = emptyCounts();
  return copy;
}

function firstNonDesertHex(state: GameState): HexId {
  return state.board.hexes.findIndex((h) => h.terrain !== 'desert');
}

/**
 * Setup where the first `owners.length` placements (in snake order) put settlements on alternating
 * corners of the returned robber target hex, and no other settlement touches it.
 */
function setupAroundHex(players: number, owners: number): { state: GameState; target: HexId } {
  const base = newGame(players, SEED);
  const target = firstNonDesertHex(base);
  const corners = TOPOLOGY.hexCorners[target];
  const picks = [corners[0], corners[2], corners[4]].slice(0, owners).map((corner) => ({ corner }));
  return { state: runSetup(base, picks, { avoidHexes: [target] }), target };
}

describe('discarding on a 7', () => {
  it('Scenario 9: 9 cards discards 4, 7 cards discards nothing', () => {
    let state = runSetup(newGame(3, SEED));
    state = topUpTo(state, 0, 9);
    state = topUpTo(state, 1, 7);
    expect(totalCards(state.players[2].hand)).toBeLessThanOrEqual(7);

    const rolled = forceRoll(state, 7);
    expect(rolled.phase).toEqual({ kind: 'discard', pending: [{ player: 0, amount: 4 }] });

    const discarded = act(rolled, { type: 'discard', cards: someCards(rolled.players[0].hand, 4) });
    expect(totalCards(discarded.players[0].hand)).toBe(5);
    expect(totalCards(discarded.players[1].hand)).toBe(7);
    expect(discarded.phase).toEqual({ kind: 'moveRobber' });
  });

  it('discard amount is half rounded down, only above 7 cards', () => {
    expect([0, 7, 8, 9, 10, 15].map(discardAmount)).toEqual([0, 0, 4, 4, 5, 7]);
  });

  it('discarded cards go back to the bank', () => {
    const rolled = forceRoll(topUpTo(runSetup(newGame(2, SEED)), 0, 8), 7);
    const cards = someCards(rolled.players[0].hand, 4);
    const discarded = act(rolled, { type: 'discard', cards });
    expect(discarded.bank).toEqual(addCounts(rolled.bank, cards));
    expect(handDelta(rolled, discarded, 0)).toEqual(subtractCounts(emptyCounts(), cards));
  });

  it('rejects a discard of the wrong total, of cards not held, or of negative counts', () => {
    const rolled = forceRoll(topUpTo(runSetup(newGame(2, SEED)), 0, 9), 7);
    const hand = rolled.players[0].hand;
    const tryDiscard = (cards: Partial<ResourceCounts>) => applyAction(rolled, { type: 'discard', cards });

    expect(tryDiscard(someCards(hand, 3))).toEqual({ ok: false, error: 'Discard exactly 4 cards' });
    expect(tryDiscard(someCards(hand, 5))).toEqual({ ok: false, error: 'Discard exactly 4 cards' });
    const scarce = RESOURCES.find((r) => hand[r] < 4)!;
    expect(tryDiscard({ [scarce]: 4 })).toEqual({ ok: false, error: "You don't have those cards" });
    expect(tryDiscard({ wood: 5, brick: -1 })).toMatchObject({ ok: false });
  });

  it('prompts discards in turn order starting with the roller, before the robber moves', () => {
    // Player id 1 rolls; ids 1, 2 and 0 all hold 8 cards.
    let state = act(toMainPhase(runSetup(newGame(3, SEED))), { type: 'endTurn' });
    for (const player of [0, 1, 2]) state = topUpTo(state, player, 8);
    let rolled = forceRoll(state, 7);
    expect(rolled.phase).toEqual({
      kind: 'discard',
      pending: [
        { player: 1, amount: 4 },
        { player: 2, amount: 4 },
        { player: 0, amount: 4 },
      ],
    });
    expect(applyAction(rolled, { type: 'moveRobber', hex: firstNonDesertHex(rolled) })).toEqual({
      ok: false,
      error: 'Discard cards first',
    });

    for (const player of [1, 2, 0]) {
      rolled = act(rolled, { type: 'discard', cards: someCards(rolled.players[player].hand, 4) });
      expect(totalCards(rolled.players[player].hand)).toBe(4);
    }
    expect(rolled.phase).toEqual({ kind: 'moveRobber' });
  });

  it('no production happens on a 7', () => {
    const state = runSetup(newGame(3, SEED));
    const rolled = forceRoll(state, 7);
    expect(rolled.phase).toEqual({ kind: 'moveRobber' });
    expect(rolled.players.map((p) => p.hand)).toEqual(state.players.map((p) => p.hand));
    expect(rolled.bank).toEqual(state.bank);
  });
});

describe('moving the robber and stealing', () => {
  it('Scenario 10: only adjacent opponents can be robbed, never the roller', () => {
    // Ids 0, 1 and 2 build on the target hex; id 3 does not.
    const { state, target } = setupAroundHex(4, 3);
    const moved = act(forceRoll(state, 7), { type: 'moveRobber', hex: target });
    expect(moved.phase).toEqual({ kind: 'steal', candidates: [1, 2] });

    expect(applyAction(moved, { type: 'steal', victim: 0 })).toEqual({
      ok: false,
      error: 'You cannot steal from yourself',
    });
    expect(applyAction(moved, { type: 'steal', victim: 3 })).toEqual({
      ok: false,
      error: 'You can only steal from a player with a building on the robber hex',
    });

    expect(totalCards(moved.players[1].hand)).toBeGreaterThan(0);
    const robbed = act(moved, { type: 'steal', victim: 1 });
    const lost = handDelta(moved, robbed, 1);
    expect(totalCards(lost)).toBe(-1);
    expect(handDelta(moved, robbed, 0)).toEqual(subtractCounts(emptyCounts(), lost));
    expect(handDelta(moved, robbed, 2)).toEqual(emptyCounts());
    expect(handDelta(moved, robbed, 3)).toEqual(emptyCounts());
    expect(robbed.phase).toEqual({ kind: 'main' });
  });

  it('steals automatically from a single adjacent opponent, conserving the card', () => {
    const { state, target } = setupAroundHex(3, 2);
    const rolled = forceRoll(state, 7);
    expect(totalCards(rolled.players[1].hand)).toBeGreaterThan(0);

    const robbed = act(rolled, { type: 'moveRobber', hex: target });
    expect(robbed.phase).toEqual({ kind: 'main' });
    const lost = handDelta(rolled, robbed, 1);
    expect(totalCards(lost)).toBe(-1);
    expect(handDelta(rolled, robbed, 0)).toEqual(subtractCounts(emptyCounts(), lost));
    expect(handDelta(rolled, robbed, 2)).toEqual(emptyCounts());
    expect(robbed.bank).toEqual(rolled.bank);
  });

  it('steals nothing when only the roller builds on the robber hex', () => {
    const { state, target } = setupAroundHex(3, 1);
    const rolled = forceRoll(state, 7);
    const moved = act(rolled, { type: 'moveRobber', hex: target });
    expect(moved.phase).toEqual({ kind: 'main' });
    expect(moved.players.map((p) => p.hand)).toEqual(rolled.players.map((p) => p.hand));
  });

  it('a victim with no cards loses nothing', () => {
    const { state, target } = setupAroundHex(3, 2);
    const rolled = forceRoll(withEmptyHand(state, 1), 7);
    const moved = act(rolled, { type: 'moveRobber', hex: target });
    expect(moved.phase).toEqual({ kind: 'main' });
    expect(moved.players.map((p) => p.hand)).toEqual(rolled.players.map((p) => p.hand));
  });

  it('the robber must move to a different hex; the desert is allowed', () => {
    const { state, target } = setupAroundHex(2, 1);
    const rolled = forceRoll(state, 7);
    expect(legalRobberHexes(rolled)).toHaveLength(18);
    expect(legalRobberHexes(rolled)).not.toContain(rolled.robberHex);
    expect(applyAction(rolled, { type: 'moveRobber', hex: rolled.robberHex })).toEqual({
      ok: false,
      error: 'The robber must move to a different hex',
    });
    expect(applyAction(rolled, { type: 'moveRobber', hex: 19 })).toEqual({ ok: false, error: 'No such hex' });

    // Move it off the desert, then (on the next player's 7) back onto it.
    let later = act(act(rolled, { type: 'moveRobber', hex: target }), { type: 'endTurn' });
    later = act(forceRoll(later, 7), { type: 'moveRobber', hex: desertHex(later.board) });
    expect(later.robberHex).toBe(desertHex(later.board));
  });

  it('a full 7 runs discard, move robber, steal, then trade and build', () => {
    let { state, target } = setupAroundHex(4, 3);
    state = topUpTo(state, 2, 8);

    let current = forceRoll(state, 7);
    expect(current.phase).toEqual({ kind: 'discard', pending: [{ player: 2, amount: 4 }] });
    current = act(current, { type: 'discard', cards: someCards(current.players[2].hand, 4) });
    expect(current.phase).toEqual({ kind: 'moveRobber' });
    current = act(current, { type: 'moveRobber', hex: target });
    expect(current.phase).toEqual({ kind: 'steal', candidates: [1, 2] });
    current = act(current, { type: 'steal', victim: 2 });
    expect(current.phase).toEqual({ kind: 'main' });
    expect(totalCards(current.players[2].hand)).toBe(3);
    expect(act(current, { type: 'endTurn' }).currentPlayer).toBe(1);
  });
});

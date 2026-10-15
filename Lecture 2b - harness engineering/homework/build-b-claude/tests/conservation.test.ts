import { describe, expect, it } from 'vitest';
import { legalRobberHexes, legalRoadEdges } from '../src/engine/placement';
import { COSTS, RESOURCES } from '../src/engine/resources';
import type { GameState, ResourceCounts } from '../src/engine/types';
import { act, buildPaid, forceRoll, giveCards, newGame, runSetup, settleNearby } from './helpers';

const CARDS_PER_RESOURCE = 19;

function expectCardsConserved(state: GameState): void {
  for (const resource of RESOURCES) {
    const inHands = state.players.reduce((sum, p) => sum + p.hand[resource], 0);
    expect(state.bank[resource] + inHands, resource).toBe(CARDS_PER_RESOURCE);
  }
}

/** Discards the first cards of each pending player's hand, moves the robber, and steals if asked. */
function resolveSeven(state: GameState): GameState {
  let current = state;
  while (current.phase.kind === 'discard') {
    const { player, amount } = current.phase.pending[0];
    current = act(current, { type: 'discard', cards: firstCards(current.players[player].hand, amount) });
    expectCardsConserved(current);
  }
  current = act(current, { type: 'moveRobber', hex: legalRobberHexes(current)[0] });
  if (current.phase.kind === 'steal') current = act(current, { type: 'steal', victim: current.phase.candidates[0] });
  return current;
}

function firstCards(hand: ResourceCounts, amount: number): Partial<ResourceCounts> {
  const cards: Partial<ResourceCounts> = {};
  let left = amount;
  for (const resource of RESOURCES) {
    const take = Math.min(left, hand[resource]);
    if (take > 0) cards[resource] = take;
    left -= take;
  }
  return cards;
}

describe('card conservation', () => {
  it('bank plus all hands stays at 19 per resource through a scripted game', () => {
    let state = runSetup(newGame(3, 11));
    expectCardsConserved(state);

    // Player 1: production, a road, a settlement, and a bank trade.
    state = forceRoll(state, 8);
    state = buildPaid(state, { type: 'placeRoad', edge: legalRoadEdges(giveCards(state, 0, COSTS.road))[0] });
    state = settleNearby(state).state;
    state = act(giveCards(state, 0, { sheep: 4 }), { type: 'bankTrade', give: 'sheep', get: 'brick' });
    expectCardsConserved(state);
    state = act(state, { type: 'endTurn' });

    // Player 2: a 7 with discards and a robber move, then a city.
    state = giveCards(state, 1, { wood: 5, ore: 4 });
    state = giveCards(state, 2, { wheat: 8 });
    state = resolveSeven(forceRoll(state, 7));
    expectCardsConserved(state);
    const city = state.buildings.findIndex((b) => b?.owner === 1);
    state = act(buildPaid(state, { type: 'placeCity', corner: city }), { type: 'endTurn' });
    expectCardsConserved(state);

    // A few random turns, resolving any 7.
    for (let turn = 0; turn < 9; turn++) {
      state = act(state, { type: 'roll' });
      if (state.phase.kind !== 'main') state = resolveSeven(state);
      expectCardsConserved(state);
      state = act(state, { type: 'endTurn' });
    }
  });
});

import { describe, expect, it } from 'vitest';
import { applyAction, currentPhaseLabel } from '../src/engine/game';
import { victoryPoints } from '../src/engine/scoring';
import type { Action, GameState } from '../src/engine/types';
import {
  act,
  buildPaid,
  buildRoadsAlong,
  findPath,
  newGame,
  runSetup,
  settleNearby,
  setupWithNetworks,
  sideApproach,
  startTurnOf,
  toMainPhase,
  withNeighbours,
} from './helpers';

const SEED = 3;

/** Player id 0, on their own main phase, with 4 cities and 1 settlement (9 VP). */
function oneSettlementFromWinning(): GameState {
  let state = toMainPhase(runSetup(newGame(2, SEED)));
  for (let i = 0; i < 2; i++) state = settleNearby(state).state;
  for (const corner of state.buildings.flatMap((b, c) => (b?.owner === 0 ? [c] : []))) {
    state = buildPaid(state, { type: 'placeCity', corner });
  }
  return settleNearby(state).state;
}

describe('victory', () => {
  it('counts 1 per settlement and 2 per city', () => {
    const state = toMainPhase(runSetup(newGame(3, SEED)));
    expect([0, 1, 2].map((p) => victoryPoints(state, p))).toEqual([2, 2, 2]);
    const corner = state.buildings.findIndex((b) => b?.owner === 0);
    expect(victoryPoints(buildPaid(state, { type: 'placeCity', corner }), 0)).toBe(3);
  });

  it('9 VP does not end the game', () => {
    const state = oneSettlementFromWinning();
    expect(victoryPoints(state, 0)).toBe(9);
    expect(state.phase).toEqual({ kind: 'main' });
  });

  it('Scenario 20: reaching 10 VP on own turn ends the game; later actions rejected', () => {
    const state = settleNearby(oneSettlementFromWinning()).state;
    expect(victoryPoints(state, 0)).toBe(10);
    expect(state.phase).toEqual({ kind: 'gameOver', winner: 0 });
    expect(state.log.at(-1)).toBe('Player 1 wins with 10 victory points!');
    expect(currentPhaseLabel(state)).toBe('Game over: Player 1 wins');

    const later: Action[] = [
      { type: 'endTurn' },
      { type: 'roll' },
      { type: 'placeRoad', edge: 0 },
      { type: 'placeSettlement', corner: 0 },
      { type: 'placeCity', corner: 0 },
      { type: 'bankTrade', give: 'wood', get: 'ore' },
      { type: 'discard', cards: {} },
      { type: 'moveRobber', hex: 0 },
      { type: 'steal', victim: 1 },
      { type: 'debugForceRoll', total: 6 },
      { type: 'debugGiveResource', player: 0, resource: 'wood', amount: 1 },
    ];
    for (const action of later) {
      expect(applyAction(state, action)).toEqual({ ok: false, error: 'The game is over' });
    }
  });

  it("a player who reaches 10 VP on another player's turn wins when their own turn starts", () => {
    // Player 1 holds Longest Road (6). Player 2 has 8 VP in cities and a 5-road chain.
    // On player 3's turn, player 3 settles in the middle of player 1's chain, so player 2 takes the card.
    const holderChain = findPath({ length: 6, accept: (path) => sideApproach(path, 3, 2) !== null });
    const breakerRoads = sideApproach(holderChain, 3, 2)!;
    const winnerChain = findPath({ length: 5, avoid: withNeighbours([...holderChain, ...breakerRoads]) });

    let state = startTurnOf(setupWithNetworks([holderChain, winnerChain, breakerRoads]), 0);
    state = buildRoadsAlong(state, holderChain);
    state = startTurnOf(state, 1);
    state = buildRoadsAlong(state, winnerChain);
    for (const corner of [winnerChain[2], winnerChain[4]]) state = buildPaid(state, { type: 'placeSettlement', corner });
    for (const corner of state.buildings.flatMap((b, c) => (b?.owner === 1 ? [c] : []))) {
      state = buildPaid(state, { type: 'placeCity', corner });
    }
    expect(state.longestRoadHolder).toBe(0);
    expect(victoryPoints(state, 1)).toBe(8);

    state = startTurnOf(state, 2);
    state = buildRoadsAlong(state, breakerRoads);
    state = buildPaid(state, { type: 'placeSettlement', corner: holderChain[3] });
    expect(state.longestRoadHolder).toBe(1);
    expect(victoryPoints(state, 1)).toBe(10);
    expect(state.phase).toEqual({ kind: 'main' });

    state = act(state, { type: 'endTurn' });
    expect(state.currentPlayer).toBe(0);
    expect(state.phase).toEqual({ kind: 'roll' });

    state = act(toMainPhase(state), { type: 'endTurn' });
    expect(state.currentPlayer).toBe(1);
    expect(state.phase).toEqual({ kind: 'gameOver', winner: 1 });
    expect(state.log.at(-1)).toBe('Player 2 wins with 10 victory points!');
  });
});

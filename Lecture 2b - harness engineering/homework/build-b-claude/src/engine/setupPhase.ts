import { updateLongestRoad } from './longestRoad';
import { roadError, settlementError } from './placement';
import { describeCounts, emptyCounts, terrainResource } from './resources';
import { TOPOLOGY } from './topology';
import type { CornerId, EdgeId, GameState, PlayerId, ResourceCounts } from './types';

/** The snake order of setup placements: players 0..n-1, then n-1..0. */
export function setupOrder(playerCount: number): PlayerId[] {
  const forward = Array.from({ length: playerCount }, (_, i) => i);
  return [...forward, ...[...forward].reverse()];
}

/** Places the current player's setup settlement; the second one also pays out its adjacent resources. */
export function placeSetupSettlement(draft: GameState, corner: CornerId): string | null {
  const phase = draft.phase;
  if (phase.kind !== 'setup') return 'Setup is over';
  if (phase.step !== 'settlement') return 'Place a road next to your settlement first';
  const player = draft.currentPlayer;
  const error = settlementError(draft, player, corner);
  if (error) return error;

  draft.buildings[corner] = { owner: player, kind: 'settlement' };
  draft.players[player].pieces.settlement--;
  draft.log.push(`${playerName(draft, player)} placed a settlement`);
  updateLongestRoad(draft);
  if (isSecondSettlement(draft, phase.turnIndex)) grantSetupResources(draft, player, corner);
  draft.phase = { ...phase, step: 'road', lastSettlement: corner };
  return null;
}

/** Places the current player's setup road next to their new settlement and passes setup to the next player. */
export function placeSetupRoad(draft: GameState, edge: EdgeId): string | null {
  const phase = draft.phase;
  if (phase.kind !== 'setup') return 'Setup is over';
  if (phase.step !== 'road') return 'Place a settlement first';
  const player = draft.currentPlayer;
  const error = roadError(draft, player, edge);
  if (error) return error;

  draft.roads[edge] = player;
  draft.players[player].pieces.road--;
  draft.log.push(`${playerName(draft, player)} placed a road`);
  updateLongestRoad(draft);
  advanceSetup(draft, phase.turnIndex + 1);
  return null;
}

/** Moves setup to placement `turnIndex`, or starts normal play once every player has placed twice. */
function advanceSetup(draft: GameState, turnIndex: number): void {
  const order = setupOrder(draft.players.length);
  if (turnIndex >= order.length) {
    draft.currentPlayer = 0;
    draft.phase = { kind: 'roll' };
    draft.log.push(`Setup complete. ${playerName(draft, 0)} takes the first turn`);
    return;
  }
  draft.currentPlayer = order[turnIndex];
  draft.phase = { kind: 'setup', turnIndex, step: 'settlement', lastSettlement: null };
}

function isSecondSettlement(state: GameState, turnIndex: number): boolean {
  return turnIndex >= state.players.length;
}

/** Moves one card per adjacent non-desert hex from the bank to the player. */
function grantSetupResources(draft: GameState, player: PlayerId, corner: CornerId): void {
  const received: ResourceCounts = emptyCounts();
  for (const hex of TOPOLOGY.cornerHexes[corner]) {
    const resource = terrainResource(draft.board.hexes[hex].terrain);
    if (resource === null || draft.bank[resource] === 0) continue;
    draft.bank[resource]--;
    draft.players[player].hand[resource]++;
    received[resource]++;
  }
  draft.log.push(`${playerName(draft, player)} received ${describeCounts(received)}`);
}

function playerName(state: GameState, player: PlayerId): string {
  return state.players[player].name;
}

import { updateLongestRoad } from './longestRoad';
import { buildError, cityError, roadError, settlementError, type BuildKind } from './placement';
import { COSTS, RESOURCES, addCounts, subtractCounts } from './resources';
import type { CornerId, EdgeId, GameState, PlayerId, Resource } from './types';

/** Number of identical cards the bank takes for one card of the player's choice. */
export const BANK_TRADE_RATE = 4;

/** Builds a road for the current player on `edge`, paying its cost. */
export function buildRoad(draft: GameState, edge: EdgeId): string | null {
  const player = draft.currentPlayer;
  const error = mainPhaseError(draft) ?? buildError(draft, 'road') ?? roadError(draft, player, edge);
  if (error) return error;

  payFor(draft, player, 'road');
  draft.roads[edge] = player;
  draft.players[player].pieces.road--;
  draft.log.push(`${nameOf(draft, player)} built a road`);
  updateLongestRoad(draft);
  return null;
}

/** Builds a settlement for the current player on `corner`, paying its cost. */
export function buildSettlement(draft: GameState, corner: CornerId): string | null {
  const player = draft.currentPlayer;
  const error = mainPhaseError(draft) ?? buildError(draft, 'settlement') ?? settlementError(draft, player, corner);
  if (error) return error;

  payFor(draft, player, 'settlement');
  draft.buildings[corner] = { owner: player, kind: 'settlement' };
  draft.players[player].pieces.settlement--;
  draft.log.push(`${nameOf(draft, player)} built a settlement`);
  updateLongestRoad(draft);
  return null;
}

/** Upgrades the current player's settlement on `corner` to a city, paying its cost and returning the settlement piece. */
export function buildCity(draft: GameState, corner: CornerId): string | null {
  const player = draft.currentPlayer;
  const error = mainPhaseError(draft) ?? buildError(draft, 'city') ?? cityError(draft, player, corner);
  if (error) return error;

  payFor(draft, player, 'city');
  draft.buildings[corner] = { owner: player, kind: 'city' };
  draft.players[player].pieces.city--;
  draft.players[player].pieces.settlement++;
  draft.log.push(`${nameOf(draft, player)} upgraded a settlement to a city`);
  return null;
}

/** Trades 4 of the current player's `give` cards to the bank for 1 `get` card. */
export function bankTrade(draft: GameState, give: Resource, get: Resource): string | null {
  const player = draft.currentPlayer;
  const error = mainPhaseError(draft) ?? bankTradeError(draft, player, give, get);
  if (error) return error;

  const hand = draft.players[player].hand;
  hand[give] -= BANK_TRADE_RATE;
  draft.bank[give] += BANK_TRADE_RATE;
  draft.bank[get]--;
  hand[get]++;
  draft.log.push(`${nameOf(draft, player)} traded ${BANK_TRADE_RATE} ${give} to the bank for 1 ${get}`);
  return null;
}

function mainPhaseError(state: GameState): string | null {
  return state.phase.kind === 'main' ? null : 'You can only trade and build after rolling';
}

function bankTradeError(state: GameState, player: PlayerId, give: Resource, get: Resource): string | null {
  if (!RESOURCES.includes(give) || !RESOURCES.includes(get)) return 'No such resource';
  if (give === get) return 'Choose a different resource to receive';
  if (state.players[player].hand[give] < BANK_TRADE_RATE) return `You need ${BANK_TRADE_RATE} ${give} to trade`;
  if (state.bank[get] === 0) return `The bank has no ${get} left`;
  return null;
}

/** Moves the cost of `kind` from the player's hand to the bank. */
function payFor(draft: GameState, player: PlayerId, kind: BuildKind): void {
  draft.players[player].hand = subtractCounts(draft.players[player].hand, COSTS[kind]);
  draft.bank = addCounts(draft.bank, COSTS[kind]);
}

function nameOf(state: GameState, player: PlayerId): string {
  return state.players[player].name;
}

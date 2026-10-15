import { legalRobberHexes } from './placement';
import { computeProduction, discardAmount } from './production';
import {
  RESOURCES,
  addCounts,
  countsOf,
  describeCounts,
  hasAtLeast,
  subtractCounts,
  totalCards,
} from './resources';
import { randomInt } from './rng';
import { TOPOLOGY } from './topology';
import type { GameState, HexId, PlayerId, Resource, ResourceCounts } from './types';

/** Rolls the dice (or uses the forced total). A 7 starts the robber sequence; any other total pays production. */
export function roll(draft: GameState): string | null {
  if (draft.phase.kind !== 'roll') return 'You have already rolled this turn';
  const dice = rollDice(draft);
  const total = dice[0] + dice[1];
  draft.lastRoll = dice;
  draft.log.push(`${nameOf(draft, draft.currentPlayer)} rolled ${total} (${dice[0]} + ${dice[1]})`);
  if (total === ROBBER_ROLL) {
    startRobberSequence(draft);
  } else {
    payProduction(draft, total);
    draft.phase = { kind: 'main' };
  }
  return null;
}

/** Discards `cards` for the first player who still owes a discard after a 7. */
export function discard(draft: GameState, cards: Partial<ResourceCounts>): string | null {
  const phase = draft.phase;
  if (phase.kind !== 'discard') return 'Nobody needs to discard now';
  const { player, amount } = phase.pending[0];
  const counts = countsOf(cards);
  const error = discardError(draft.players[player].hand, counts, amount);
  if (error) return error;

  moveCards(draft, counts, player, BANK);
  draft.log.push(`${nameOf(draft, player)} discarded ${describeCounts(counts)}`);
  const remaining = phase.pending.slice(1);
  draft.phase = remaining.length > 0 ? { kind: 'discard', pending: remaining } : { kind: 'moveRobber' };
  return null;
}

/** Moves the robber to `hex`, then steals automatically, asks the roller to choose a victim, or skips the steal. */
export function moveRobber(draft: GameState, hex: HexId): string | null {
  if (draft.phase.kind !== 'moveRobber') return 'You cannot move the robber now';
  if (hex === draft.robberHex) return 'The robber must move to a different hex';
  if (!legalRobberHexes(draft).includes(hex)) return 'No such hex';

  draft.robberHex = hex;
  draft.log.push(`${nameOf(draft, draft.currentPlayer)} moved the robber to ${describeHex(draft, hex)}`);
  const candidates = stealCandidates(draft);
  if (candidates.length === 0) {
    draft.log.push('Nobody to steal from');
    draft.phase = { kind: 'main' };
  } else if (candidates.length === 1) {
    stealRandomCard(draft, candidates[0]);
    draft.phase = { kind: 'main' };
  } else {
    draft.phase = { kind: 'steal', candidates };
  }
  return null;
}

/** Steals a random card from the chosen opponent touching the robber hex. */
export function steal(draft: GameState, victim: PlayerId): string | null {
  const phase = draft.phase;
  if (phase.kind !== 'steal') return 'You cannot steal now';
  if (victim === draft.currentPlayer) return 'You cannot steal from yourself';
  if (!phase.candidates.includes(victim)) return 'You can only steal from a player with a building on the robber hex';

  stealRandomCard(draft, victim);
  draft.phase = { kind: 'main' };
  return null;
}

/** Passes the turn to the next player in order, who must roll. */
export function endTurn(draft: GameState): string | null {
  if (draft.phase.kind !== 'main') return 'You cannot end your turn now';
  draft.currentPlayer = (draft.currentPlayer + 1) % draft.players.length;
  draft.phase = { kind: 'roll' };
  draft.lastRoll = null;
  draft.log.push(`${nameOf(draft, draft.currentPlayer)}'s turn`);
  return null;
}

/** The dice shown for a forced total (Decision 5): the first die as high as possible. */
function forcedDice(total: number): [number, number] {
  const first = Math.min(6, total - 1);
  return [first, total - first];
}

const ROBBER_ROLL = 7;
const BANK = 'bank';
type CardHolder = PlayerId | typeof BANK;

function rollDice(draft: GameState): [number, number] {
  if (draft.forcedRoll !== null) {
    const dice = forcedDice(draft.forcedRoll);
    draft.forcedRoll = null;
    return dice;
  }
  return [rollDie(draft), rollDie(draft)];
}

function rollDie(draft: GameState): number {
  const { value, rngState } = randomInt(draft.rngState, 6);
  draft.rngState = rngState;
  return value + 1;
}

function payProduction(draft: GameState, total: number): void {
  const paid = computeProduction(draft, total);
  paid.forEach((cards, player) => {
    if (totalCards(cards) === 0) return;
    moveCards(draft, cards, BANK, player);
    draft.log.push(`${nameOf(draft, player)} received ${describeCounts(cards)}`);
  });
  if (paid.every((cards) => totalCards(cards) === 0)) draft.log.push('Nobody received anything');
}

/** After a 7: players over the limit discard first (roller first, then turn order), then the robber moves. */
function startRobberSequence(draft: GameState): void {
  const pending = turnOrderFrom(draft, draft.currentPlayer)
    .map((player) => ({ player, amount: discardAmount(totalCards(draft.players[player].hand)) }))
    .filter((entry) => entry.amount > 0);
  draft.phase = pending.length > 0 ? { kind: 'discard', pending } : { kind: 'moveRobber' };
}

function turnOrderFrom(state: GameState, first: PlayerId): PlayerId[] {
  const count = state.players.length;
  return Array.from({ length: count }, (_, i) => (first + i) % count);
}

function discardError(hand: ResourceCounts, cards: ResourceCounts, amount: number): string | null {
  if (!RESOURCES.every((r) => Number.isInteger(cards[r]) && cards[r] >= 0)) {
    return 'Card counts must be whole numbers';
  }
  if (totalCards(cards) !== amount) return `Discard exactly ${amount} cards`;
  if (!hasAtLeast(hand, cards)) return "You don't have those cards";
  return null;
}

/** Opponents of the roller with a settlement or city touching the robber hex, in player order. */
function stealCandidates(state: GameState): PlayerId[] {
  const owners = new Set<PlayerId>();
  for (const corner of TOPOLOGY.hexCorners[state.robberHex]) {
    const building = state.buildings[corner];
    if (building && building.owner !== state.currentPlayer) owners.add(building.owner);
  }
  return [...owners].sort((a, b) => a - b);
}

/** Moves one card, chosen uniformly from the victim's individual cards, to the current player. */
function stealRandomCard(draft: GameState, victim: PlayerId): void {
  const thief = draft.currentPlayer;
  const hand = draft.players[victim].hand;
  const handSize = totalCards(hand);
  if (handSize === 0) {
    draft.log.push(`${nameOf(draft, thief)} tried to steal from ${nameOf(draft, victim)}, who has no cards`);
    return;
  }
  const pick = randomInt(draft.rngState, handSize);
  draft.rngState = pick.rngState;
  moveCards(draft, countsOf({ [nthCard(hand, pick.value)]: 1 }), victim, thief);
  draft.log.push(`${nameOf(draft, thief)} stole a card from ${nameOf(draft, victim)}`);
}

/** The resource of the `index`-th card when the hand is laid out resource by resource. */
function nthCard(hand: ResourceCounts, index: number): Resource {
  let remaining = index;
  for (const resource of RESOURCES) {
    if (remaining < hand[resource]) return resource;
    remaining -= hand[resource];
  }
  throw new Error(`Card index ${index} is outside a hand of ${totalCards(hand)}`);
}

function moveCards(draft: GameState, cards: ResourceCounts, from: CardHolder, to: CardHolder): void {
  if (from === BANK) draft.bank = subtractCounts(draft.bank, cards);
  else draft.players[from].hand = subtractCounts(draft.players[from].hand, cards);
  if (to === BANK) draft.bank = addCounts(draft.bank, cards);
  else draft.players[to].hand = addCounts(draft.players[to].hand, cards);
}

function describeHex(state: GameState, hex: HexId): string {
  const { terrain, number } = state.board.hexes[hex];
  return number === null ? `the ${terrain}` : `the ${terrain} (${number})`;
}

function nameOf(state: GameState, player: PlayerId): string {
  return state.players[player].name;
}

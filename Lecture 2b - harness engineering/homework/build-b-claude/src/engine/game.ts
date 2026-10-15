import { desertHex, generateBoard } from './board';
import { bankTrade, buildCity, buildRoad, buildSettlement } from './building';
import { RESOURCES, countsOf, emptyCounts } from './resources';
import { checkWinner } from './scoring';
import { placeSetupRoad, placeSetupSettlement } from './setupPhase';
import { TOPOLOGY } from './topology';
import { discard, endTurn, moveRobber, roll, steal } from './turn';
import type { Action, ActionResult, GameState, Phase, Player, PlayerId, Resource } from './types';

export const MIN_PLAYERS = 2;
export const MAX_PLAYERS = 4;

/** Creates a new game in setup, with player 1 to place the first settlement. */
export function createGame(opts: { seed: number; playerNames: string[] }): GameState {
  const count = opts.playerNames.length;
  if (count < MIN_PLAYERS || count > MAX_PLAYERS) {
    throw new Error(`A game needs ${MIN_PLAYERS} to ${MAX_PLAYERS} players`);
  }
  const seed = opts.seed >>> 0;
  const board = generateBoard(seed);
  return {
    board,
    players: opts.playerNames.map(newPlayer),
    currentPlayer: 0,
    phase: { kind: 'setup', turnIndex: 0, step: 'settlement', lastSettlement: null },
    buildings: TOPOLOGY.cornerHexes.map(() => null),
    roads: TOPOLOGY.edgeCorners.map(() => null),
    bank: countsOf({ wood: BANK_SIZE, brick: BANK_SIZE, sheep: BANK_SIZE, wheat: BANK_SIZE, ore: BANK_SIZE }),
    robberHex: desertHex(board),
    longestRoadHolder: null,
    lastRoll: null,
    forcedRoll: null,
    // Mixed so the dice stream doesn't replay the board's shuffle sequence.
    rngState: (seed ^ DICE_SEED_MIX) >>> 0,
    log: [`New game with seed ${seed}`],
  };
}

/** Applies an action, returning the new state or an error; the input state is never modified. */
export function applyAction(state: GameState, action: Action): ActionResult {
  const blocked = phaseError(state, action);
  if (blocked) return { ok: false, error: blocked };
  // Handlers mutate this copy; on error it is discarded, so partial changes never leak.
  const draft = structuredClone(state);
  const error = runHandler(draft, action);
  if (error) return { ok: false, error };
  // After endTurn the current player is the incoming one, so this also covers a win reached on another turn (Decision 11).
  if (!isDebugAction(action)) checkWinner(draft, draft.currentPlayer);
  return { ok: true, state: draft };
}

/** A short description of what the current player must do now. */
export function currentPhaseLabel(state: GameState): string {
  const name = state.players[state.currentPlayer].name;
  const phase = state.phase;
  switch (phase.kind) {
    case 'setup':
      return `Setup: ${name}, place a ${phase.step}`;
    case 'roll':
      return `${name}: roll the dice`;
    case 'discard':
      return `${state.players[phase.pending[0].player].name}: discard ${phase.pending[0].amount} cards`;
    case 'moveRobber':
      return `${name}: move the robber`;
    case 'steal':
      return `${name}: choose a player to steal from`;
    case 'main':
      return `${name}: trade and build`;
    case 'gameOver':
      return `Game over: ${state.players[phase.winner].name} wins`;
  }
}

const BANK_SIZE = 19;
const DICE_SEED_MIX = 0x9e3779b9;
const MIN_ROLL = 2;
const MAX_ROLL = 12;
const DEFAULT_COLORS = ['red', 'blue', 'orange', 'green'];

const ALLOWED_ACTIONS: Record<Phase['kind'], Action['type'][]> = {
  setup: ['placeSettlement', 'placeRoad'],
  roll: ['roll'],
  discard: ['discard'],
  moveRobber: ['moveRobber'],
  steal: ['steal'],
  main: ['placeSettlement', 'placeRoad', 'placeCity', 'bankTrade', 'endTurn'],
  gameOver: [],
};

const BLOCKED_MESSAGE: Record<Phase['kind'], string> = {
  setup: 'Finish setup first',
  roll: 'Roll the dice first',
  discard: 'Discard cards first',
  moveRobber: 'Move the robber first',
  steal: 'Choose a player to steal from first',
  main: 'You have already rolled this turn',
  gameOver: 'The game is over',
};

/** Why the action is not allowed in the current phase, or null if it is. Debug actions work until the game ends. */
function phaseError(state: GameState, action: Action): string | null {
  const phase = state.phase.kind;
  if (phase === 'gameOver') return BLOCKED_MESSAGE.gameOver;
  if (isDebugAction(action)) return null;
  return ALLOWED_ACTIONS[phase].includes(action.type) ? null : BLOCKED_MESSAGE[phase];
}

function runHandler(draft: GameState, action: Action): string | null {
  const inSetup = draft.phase.kind === 'setup';
  switch (action.type) {
    case 'placeSettlement':
      return inSetup ? placeSetupSettlement(draft, action.corner) : buildSettlement(draft, action.corner);
    case 'placeRoad':
      return inSetup ? placeSetupRoad(draft, action.edge) : buildRoad(draft, action.edge);
    case 'placeCity':
      return buildCity(draft, action.corner);
    case 'bankTrade':
      return bankTrade(draft, action.give, action.get);
    case 'roll':
      return roll(draft);
    case 'discard':
      return discard(draft, action.cards);
    case 'moveRobber':
      return moveRobber(draft, action.hex);
    case 'steal':
      return steal(draft, action.victim);
    case 'endTurn':
      return endTurn(draft);
    case 'debugForceRoll':
      return debugForceRoll(draft, action.total);
    case 'debugGiveResource':
      return debugGiveResource(draft, action.player, action.resource, action.amount);
  }
}

/** Debug: makes the next roll come up `total`. */
function debugForceRoll(draft: GameState, total: number): string | null {
  if (!Number.isInteger(total) || total < MIN_ROLL || total > MAX_ROLL) {
    return `A forced roll must be a whole number from ${MIN_ROLL} to ${MAX_ROLL}`;
  }
  draft.forcedRoll = total;
  draft.log.push(`Debug: the next roll will be ${total}`);
  return null;
}

/** Debug: moves cards from the bank to a player, so the 19-per-resource total is preserved (Decision 6). */
function debugGiveResource(draft: GameState, player: PlayerId, resource: Resource, amount: number): string | null {
  if (!Number.isInteger(player) || player < 0 || player >= draft.players.length) return 'No such player';
  if (!RESOURCES.includes(resource)) return 'No such resource';
  if (!Number.isInteger(amount) || amount < 1) return 'Give at least 1 card';
  if (draft.bank[resource] < amount) return `The bank has only ${draft.bank[resource]} ${resource}`;

  draft.bank[resource] -= amount;
  draft.players[player].hand[resource] += amount;
  draft.log.push(`Debug: ${draft.players[player].name} was given ${amount} ${resource}`);
  return null;
}

function isDebugAction(action: Action): boolean {
  return action.type === 'debugForceRoll' || action.type === 'debugGiveResource';
}

function newPlayer(name: string, id: number): Player {
  return {
    id,
    name: name.trim() || `Player ${id + 1}`,
    color: DEFAULT_COLORS[id],
    hand: emptyCounts(),
    pieces: { road: 15, settlement: 5, city: 4 },
  };
}

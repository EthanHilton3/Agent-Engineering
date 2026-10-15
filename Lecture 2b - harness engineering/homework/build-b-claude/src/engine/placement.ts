import { COSTS, hasAtLeast } from './resources';
import { TOPOLOGY } from './topology';
import type { CornerId, EdgeId, GameState, HexId, PlayerId } from './types';

export type BuildKind = 'road' | 'settlement' | 'city';

/** Why the current player cannot build a piece of this kind right now (cost or supply), or null if they can. */
export function buildError(state: GameState, kind: BuildKind): string | null {
  if (state.phase.kind === 'setup') return null; // setup pieces are free
  const player = state.players[state.currentPlayer];
  if (player.pieces[kind] === 0) return NO_PIECES_LEFT[kind];
  if (!hasAtLeast(player.hand, COSTS[kind])) return 'Not enough resources';
  return null;
}

/** Why `player` may not put a settlement on `corner` (location rules only), or null if they may. */
export function settlementError(state: GameState, player: PlayerId, corner: CornerId): string | null {
  if (!isValidId(corner, CORNER_COUNT)) return 'No such corner';
  if (state.buildings[corner] !== null) return 'That corner is already occupied';
  if (violatesDistanceRule(state, corner)) return 'Too close to another settlement or city';
  if (state.phase.kind !== 'setup' && !touchesOwnRoad(state, player, corner)) {
    return 'A settlement must touch one of your roads';
  }
  return null;
}

/** Why `player` may not put a road on `edge` (location rules only), or null if they may. */
export function roadError(state: GameState, player: PlayerId, edge: EdgeId): string | null {
  if (!isValidId(edge, EDGE_COUNT)) return 'No such edge';
  if (state.roads[edge] !== null) return 'That edge already has a road';
  if (state.phase.kind === 'setup') {
    const anchor = state.phase.lastSettlement;
    if (anchor === null || !TOPOLOGY.edgeCorners[edge].includes(anchor)) {
      return 'Your setup road must touch the settlement you just placed';
    }
    return null;
  }
  if (!connectsToNetwork(state, player, edge)) return 'A road must connect to your own road, settlement, or city';
  return null;
}

/** Why `player` may not upgrade `corner` to a city (location rules only), or null if they may. */
export function cityError(state: GameState, player: PlayerId, corner: CornerId): string | null {
  if (!isValidId(corner, CORNER_COUNT)) return 'No such corner';
  const building = state.buildings[corner];
  if (building?.owner !== player || building.kind !== 'settlement') {
    return 'A city must replace one of your settlements';
  }
  return null;
}

/** Corners where the current player may place a settlement now. */
export function legalSettlementCorners(state: GameState): CornerId[] {
  if (!canPlaceNow(state, 'settlement')) return [];
  return allIds(CORNER_COUNT).filter((c) => settlementError(state, state.currentPlayer, c) === null);
}

/** Edges where the current player may place a road now. */
export function legalRoadEdges(state: GameState): EdgeId[] {
  if (!canPlaceNow(state, 'road')) return [];
  return allIds(EDGE_COUNT).filter((e) => roadError(state, state.currentPlayer, e) === null);
}

/** Corners where the current player may build a city now. */
export function legalCityCorners(state: GameState): CornerId[] {
  if (!canPlaceNow(state, 'city')) return [];
  return allIds(CORNER_COUNT).filter((c) => cityError(state, state.currentPlayer, c) === null);
}

/** Hexes the robber may move to now: every hex except its current one, during the robber step. */
export function legalRobberHexes(state: GameState): HexId[] {
  if (state.phase.kind !== 'moveRobber') return [];
  return allIds(HEX_COUNT).filter((h) => h !== state.robberHex);
}

const CORNER_COUNT = TOPOLOGY.cornerHexes.length;
const EDGE_COUNT = TOPOLOGY.edgeCorners.length;
const HEX_COUNT = TOPOLOGY.hexCoords.length;

const NO_PIECES_LEFT: Record<BuildKind, string> = {
  road: 'No roads left',
  settlement: 'No settlements left',
  city: 'No cities left',
};

/** True if the phase (and, in normal play, cost and supply) lets the current player place this kind. */
function canPlaceNow(state: GameState, kind: BuildKind): boolean {
  const phase = state.phase;
  if (phase.kind === 'setup') return phase.step === kind;
  return phase.kind === 'main' && buildError(state, kind) === null;
}

function violatesDistanceRule(state: GameState, corner: CornerId): boolean {
  return TOPOLOGY.cornerNeighbors[corner].some((n) => state.buildings[n] !== null);
}

function touchesOwnRoad(state: GameState, player: PlayerId, corner: CornerId): boolean {
  return TOPOLOGY.cornerEdges[corner].some((e) => state.roads[e] === player);
}

/** True if some endpoint of `edge` links it to the player's network without passing an opponent's building. */
function connectsToNetwork(state: GameState, player: PlayerId, edge: EdgeId): boolean {
  return TOPOLOGY.edgeCorners[edge].some((corner) => {
    const building = state.buildings[corner];
    if (building) return building.owner === player;
    return TOPOLOGY.cornerEdges[corner].some((other) => other !== edge && state.roads[other] === player);
  });
}

function isValidId(id: number, count: number): boolean {
  return Number.isInteger(id) && id >= 0 && id < count;
}

function allIds(count: number): number[] {
  return Array.from({ length: count }, (_, i) => i);
}

import { applyAction, createGame } from '../src/engine/game';
import { legalRoadEdges, legalSettlementCorners } from '../src/engine/placement';
import { COSTS, RESOURCES, subtractCounts } from '../src/engine/resources';
import { setupOrder } from '../src/engine/setupPhase';
import { TOPOLOGY, edgeBetween } from '../src/engine/topology';
import type { Action, CornerId, EdgeId, GameState, HexId, PlayerId, ResourceCounts } from '../src/engine/types';

/** A setup placement: the settlement corner and, optionally, the road edge (default: first legal edge). */
export interface SetupPick {
  corner: CornerId;
  edge?: EdgeId;
}

/** Options for `runSetup`'s default picks. */
export interface SetupOptions {
  /** Default settlement picks never touch these hexes. */
  avoidHexes?: HexId[];
}

/** Starts a game with `players` default-named players. */
export function newGame(players: number, seed = 1): GameState {
  const playerNames = Array.from({ length: players }, (_, i) => `Player ${i + 1}`);
  return createGame({ seed, playerNames });
}

/** Applies an action that the test expects to succeed; throws with the engine's error otherwise. */
export function act(state: GameState, action: Action): GameState {
  const result = applyAction(state, action);
  if (!result.ok) throw new Error(`${action.type} failed: ${result.error}`);
  return result.state;
}

/**
 * Plays out the remaining setup placements in snake order. `picks[i]` is used for the i-th
 * remaining placement; missing picks take the first legal corner (that touches no avoided hex and
 * leaves every explicit pick placeable) and the first legal edge.
 */
export function runSetup(
  state: GameState,
  picks: (SetupPick | undefined)[] = [],
  options: SetupOptions = {},
): GameState {
  const reserved = picks.flatMap((pick) => (pick ? [pick.corner] : []));
  const avoid = options.avoidHexes ?? [];
  let current = state;
  for (let i = 0; current.phase.kind === 'setup'; i++) {
    const pick = picks[i];
    const corner = pick?.corner ?? firstOf(defaultCorners(current, reserved, avoid));
    current = act(current, { type: 'placeSettlement', corner });
    current = act(current, { type: 'placeRoad', edge: pick?.edge ?? firstOf(legalRoadEdges(current)) });
  }
  return current;
}

/** Moves cards from the bank to `player` with the debug action. */
export function giveCards(state: GameState, player: PlayerId, cards: Partial<ResourceCounts>): GameState {
  let current = state;
  for (const resource of RESOURCES) {
    const amount = cards[resource] ?? 0;
    if (amount > 0) current = act(current, { type: 'debugGiveResource', player, resource, amount });
  }
  return current;
}

/** Forces the next roll to `total` and rolls it. */
export function forceRoll(state: GameState, total: number): GameState {
  return act(act(state, { type: 'debugForceRoll', total }), { type: 'roll' });
}

/** From the roll phase, rolls a forced non-7 `total` so the current player is in the trade-and-build phase. */
export function toMainPhase(state: GameState, total = 2): GameState {
  if (total === 7) throw new Error('toMainPhase needs a total other than 7');
  return forceRoll(state, total);
}

/** How `player`'s hand changed between two states (negative counts are losses). */
export function handDelta(before: GameState, after: GameState, player: PlayerId): ResourceCounts {
  return subtractCounts(after.players[player].hand, before.players[player].hand);
}

/** A build action for the current player. */
export type BuildAction = Extract<Action, { type: 'placeRoad' | 'placeSettlement' | 'placeCity' }>;

/** Gives the current player the cost of the piece, then builds it (main phase). */
export function buildPaid(state: GameState, action: BuildAction): GameState {
  return act(giveCards(state, state.currentPlayer, COSTS[BUILD_KIND[action.type]]), action);
}

/**
 * Builds (paid) roads along a shortest path from the current player's network to the nearest
 * corner where they could then settle, and returns that corner.
 */
export function roadsToOpenCorner(state: GameState): { state: GameState; corner: CornerId } {
  const path = pathToOpenCorner(state, state.currentPlayer);
  let current = state;
  for (const edge of path.edges) current = buildPaid(current, { type: 'placeRoad', edge });
  return { state: current, corner: path.corner };
}

/** Builds (paid) roads to the nearest open corner and a settlement there; returns that corner. */
export function settleNearby(state: GameState): { state: GameState; corner: CornerId } {
  const { state: withRoads, corner } = roadsToOpenCorner(state);
  return { state: buildPaid(withRoads, { type: 'placeSettlement', corner }), corner };
}

/** What `findPath` looks for: a simple path of `length` edges. */
export interface PathSearch {
  length: number;
  /** Start corner; by default every corner not in `avoid` is tried, in ID order. */
  from?: CornerId;
  /** Corners the path may not use (the `from` corner excepted). */
  avoid?: CornerId[];
  /** Extra condition the whole path must meet. */
  accept?: (path: CornerId[]) => boolean;
}

/** The first simple path of corners (length + 1 of them) meeting the search, or null. Pure topology. */
export function tryFindPath(search: PathSearch): CornerId[] | null {
  const avoid = new Set(search.avoid ?? []);
  const accept = search.accept ?? (() => true);
  const starts =
    search.from !== undefined ? [search.from] : TOPOLOGY.cornerNeighbors.map((_, c) => c).filter((c) => !avoid.has(c));
  for (const start of starts) {
    const path = extendPath([start], search.length, avoid, accept);
    if (path) return path;
  }
  return null;
}

/** Like `tryFindPath`, but throws when no path exists. */
export function findPath(search: PathSearch): CornerId[] {
  const path = tryFindPath(search);
  if (!path) throw new Error(`No path of length ${search.length} found`);
  return path;
}

/**
 * A path of `length` edges that ends at `chain[at]`, reaching it from off the chain and starting
 * far enough from `chain[0]` (the chain's settlement) for a settlement of its own; or null.
 */
export function sideApproach(chain: CornerId[], at: number, length: number): CornerId[] | null {
  const path = tryFindPath({ length, from: chain[at], avoid: [...chain, ...withNeighbours([chain[0]])] });
  return path ? path.reverse() : null;
}

/** The edges between consecutive corners of a path. */
export function pathEdges(path: CornerId[]): EdgeId[] {
  return path.slice(1).map((corner, i) => {
    const edge = edgeBetween(path[i], corner);
    if (edge === null) throw new Error(`Corners ${path[i]} and ${corner} are not adjacent`);
    return edge;
  });
}

/** The corners plus all their neighbours. */
export function withNeighbours(corners: CornerId[]): CornerId[] {
  return [...new Set(corners.flatMap((c) => [c, ...TOPOLOGY.cornerNeighbors[c]]))];
}

/**
 * Starts a game and plays setup so player i's first settlement is on `networks[i][0]` with its
 * road along the path's first edge. Second settlements and roads go where they touch nothing
 * else, so they never join or block the given networks.
 */
export function setupWithNetworks(networks: CornerId[][], seed = 1): GameState {
  const players = networks.length;
  const taken = withNeighbours(networks.flat());
  const seconds = networks.map(() => {
    const second = findPath({ length: 1, avoid: taken });
    taken.push(...withNeighbours(second));
    return second;
  });
  const picks = setupOrder(players).map((player, turnIndex) => {
    const path = turnIndex < players ? networks[player] : seconds[player];
    return { corner: path[0], edge: pathEdges(path.slice(0, 2))[0] };
  });
  return runSetup(newGame(players, seed), picks);
}

/** Passes turns (each roll forced to a non-7) until `player` is in their trade-and-build phase. */
export function startTurnOf(state: GameState, player: PlayerId): GameState {
  let current = state;
  while (current.currentPlayer !== player || current.phase.kind !== 'main') {
    current = current.phase.kind === 'main' ? act(current, { type: 'endTurn' }) : toMainPhase(current);
  }
  return current;
}

/** Builds (paid) every road along the path that isn't built yet, in path order. */
export function buildRoadsAlong(state: GameState, path: CornerId[]): GameState {
  let current = state;
  for (const edge of pathEdges(path)) {
    if (current.roads[edge] === null) current = buildPaid(current, { type: 'placeRoad', edge });
  }
  return current;
}

const BUILD_KIND = { placeRoad: 'road', placeSettlement: 'settlement', placeCity: 'city' } as const;

/** Breadth-first search over empty edges, never passing a building, to a corner that is free under the distance rule. */
function pathToOpenCorner(state: GameState, player: PlayerId): { edges: EdgeId[]; corner: CornerId } {
  const queue = networkCorners(state, player).map((corner) => ({ corner, edges: [] as EdgeId[] }));
  const visited = new Set(queue.map((step) => step.corner));
  for (let step = queue.shift(); step; step = queue.shift()) {
    if (isOpenCorner(state, step.corner)) return step;
    for (const edge of TOPOLOGY.cornerEdges[step.corner]) {
      const next = TOPOLOGY.edgeCorners[edge].find((c) => c !== step.corner)!;
      if (state.roads[edge] !== null || visited.has(next) || state.buildings[next] !== null) continue;
      visited.add(next);
      queue.push({ corner: next, edges: [...step.edges, edge] });
    }
  }
  throw new Error('No open corner reachable');
}

/** Corners the player's roads can extend from: their buildings and their road ends without a building. */
function networkCorners(state: GameState, player: PlayerId): CornerId[] {
  return TOPOLOGY.cornerEdges.flatMap((edges, c) => {
    const building = state.buildings[c];
    const ownBuilding = building?.owner === player;
    const ownRoadEnd = building === null && edges.some((e) => state.roads[e] === player);
    return ownBuilding || ownRoadEnd ? [c] : [];
  });
}

/** True if the corner and all its neighbours are empty, so the distance rule allows a settlement there. */
function isOpenCorner(state: GameState, corner: CornerId): boolean {
  return [corner, ...TOPOLOGY.cornerNeighbors[corner]].every((c) => state.buildings[c] === null);
}

/** Legal setup corners that touch no avoided hex and are not on or next to a reserved corner. */
function defaultCorners(state: GameState, reserved: CornerId[], avoidHexes: HexId[]): CornerId[] {
  return legalSettlementCorners(state).filter(
    (c) =>
      !TOPOLOGY.cornerHexes[c].some((h) => avoidHexes.includes(h)) &&
      !reserved.some((r) => r === c || TOPOLOGY.cornerNeighbors[r].includes(c)),
  );
}

/** Depth-first extension of a simple path until it has `length` edges and is accepted. */
function extendPath(
  path: CornerId[],
  length: number,
  avoid: Set<CornerId>,
  accept: (path: CornerId[]) => boolean,
): CornerId[] | null {
  if (path.length === length + 1) return accept(path) ? path : null;
  for (const next of TOPOLOGY.cornerNeighbors[path[path.length - 1]]) {
    if (avoid.has(next) || path.includes(next)) continue;
    const found = extendPath([...path, next], length, avoid, accept);
    if (found) return found;
  }
  return null;
}

function firstOf(ids: number[]): number {
  if (ids.length === 0) throw new Error('No legal placement available');
  return ids[0];
}

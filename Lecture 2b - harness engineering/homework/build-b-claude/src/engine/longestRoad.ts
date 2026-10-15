import { TOPOLOGY } from './topology';
import type { CornerId, EdgeId, GameState, PlayerId } from './types';

/** Road length needed to take the Longest Road card. */
export const LONGEST_ROAD_MIN_LENGTH = 5;

/** The player's longest trail of their own roads (each road used once), broken at opponents' buildings. */
export function roadLength(state: GameState, player: PlayerId): number {
  let best = 0;
  for (const corner of cornersTouchingRoads(state, player)) {
    best = Math.max(best, longestTrailFrom(state, player, corner, new Set()));
  }
  return best;
}

/** Re-evaluates who holds the Longest Road card after a road or settlement placement, logging any change. */
export function updateLongestRoad(draft: GameState): void {
  const lengths = draft.players.map((player) => roadLength(draft, player.id));
  const previous = draft.longestRoadHolder;
  const holder = nextHolder(previous, lengths);
  if (holder === previous) return;

  draft.longestRoadHolder = holder;
  if (holder !== null) {
    draft.log.push(`${draft.players[holder].name} takes Longest Road with a road of length ${lengths[holder]}`);
  } else if (previous !== null) {
    draft.log.push(`${draft.players[previous].name} loses Longest Road; the card is set aside`);
  }
}

/**
 * The holder keeps the card while at least 5 long and tied for longest (Decision 10). Otherwise it
 * goes to a unique longest player of at least 5, or nobody. Since one placement changes at most one
 * player's length upward, "exceed to take, ties don't take" follows from this.
 */
function nextHolder(holder: PlayerId | null, lengths: number[]): PlayerId | null {
  const longest = Math.max(...lengths);
  if (holder !== null && lengths[holder] >= LONGEST_ROAD_MIN_LENGTH && lengths[holder] === longest) return holder;

  const leaders = lengths.flatMap((length, player) => (length === longest ? [player] : []));
  return leaders.length === 1 && longest >= LONGEST_ROAD_MIN_LENGTH ? leaders[0] : null;
}

/** Depth-first search for the longest trail starting at `corner` that avoids the roads in `used`. */
function longestTrailFrom(state: GameState, player: PlayerId, corner: CornerId, used: Set<EdgeId>): number {
  let best = 0;
  for (const edge of TOPOLOGY.cornerEdges[corner]) {
    if (state.roads[edge] !== player || used.has(edge)) continue;
    const next = otherEnd(edge, corner);
    used.add(edge);
    const onward = isBlockedFor(state, player, next) ? 0 : longestTrailFrom(state, player, next, used);
    used.delete(edge);
    best = Math.max(best, 1 + onward);
  }
  return best;
}

function cornersTouchingRoads(state: GameState, player: PlayerId): CornerId[] {
  const corners = new Set<CornerId>();
  state.roads.forEach((owner, edge) => {
    if (owner === player) TOPOLOGY.edgeCorners[edge].forEach((corner) => corners.add(corner));
  });
  return [...corners];
}

/** A trail may end at an opponent's building but cannot pass through it. */
function isBlockedFor(state: GameState, player: PlayerId, corner: CornerId): boolean {
  const building = state.buildings[corner];
  return building !== null && building.owner !== player;
}

function otherEnd(edge: EdgeId, corner: CornerId): CornerId {
  const [a, b] = TOPOLOGY.edgeCorners[edge];
  return a === corner ? b : a;
}

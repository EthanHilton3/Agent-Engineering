import { GEO, otherCorner } from './geometry';
import { LONGEST_ROAD_MIN, type Building } from './types';

/**
 * Length of a player's longest continuous road: the longest trail (each edge
 * used at most once, corners may repeat) through their road network. A corner
 * holding an opponent's building ends the trail — it can be an endpoint but
 * cannot be passed through.
 */
export function longestRoadLength(
  roads: (number | null)[],
  buildings: (Building | null)[],
  player: number,
): number {
  const blocked = (c: number) => {
    const b = buildings[c];
    return b !== null && b.owner !== player;
  };
  const used = new Set<number>();

  const walk = (corner: number): number => {
    if (used.size > 0 && blocked(corner)) return 0;
    let best = 0;
    for (const e of GEO.corners[corner].edges) {
      if (roads[e] !== player || used.has(e)) continue;
      used.add(e);
      best = Math.max(best, 1 + walk(otherCorner(e, corner)));
      used.delete(e);
    }
    return best;
  };

  let best = 0;
  const starts = new Set<number>();
  roads.forEach((owner, e) => {
    if (owner === player) GEO.edges[e].corners.forEach((c) => starts.add(c));
  });
  for (const c of starts) best = Math.max(best, walk(c));
  return best;
}

/**
 * Decide who holds the Longest Road card given everyone's current lengths.
 *
 * - The holder keeps it while they are still (possibly tied for) longest and
 *   still have at least 5.
 * - Otherwise the card goes to whoever is uniquely longest with at least 5;
 *   if there is a tie for longest or nobody has 5, it is set aside (null).
 *
 * When nobody holds it, the unique longest player with at least 5 takes it.
 * Because only one player's length grows per placement, a challenger can only
 * take the card from a holder by strictly exceeding them.
 */
export function resolveLongestRoad(lengths: number[], holder: number | null): number | null {
  const max = Math.max(...lengths);
  if (holder !== null && lengths[holder] === max && max >= LONGEST_ROAD_MIN) return holder;
  if (max < LONGEST_ROAD_MIN) return null;
  const leaders = lengths.flatMap((len, p) => (len === max ? [p] : []));
  return leaders.length === 1 ? leaders[0] : null;
}

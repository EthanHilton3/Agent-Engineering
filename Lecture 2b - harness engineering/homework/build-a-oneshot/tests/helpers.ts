import { expect } from 'vitest';
import { Game } from '../src/game/game';
import { GEO, edgeBetween } from '../src/game/geometry';
import { RESOURCES, type Building, type ResourceMap, type Result } from '../src/game/types';

export function newGame(players = 2, seed = 'test-seed'): Game {
  return new Game({ seed, playerNames: Array.from({ length: players }, (_, i) => `P${i + 1}`) });
}

export function expectOk(r: Result) {
  expect(r, r.ok ? '' : r.error).toEqual({ ok: true });
}

export function expectFail(r: Result, match?: RegExp) {
  expect(r.ok).toBe(false);
  if (!r.ok && match) expect(r.error).toMatch(match);
}

/** Jump straight to player 1's first normal turn with an empty board. */
export function skipSetup(g: Game) {
  const s = g.state;
  s.setupStep = s.setupOrder.length;
  s.setupSettlement = null;
  s.currentPlayer = 0;
  s.phase = 'roll';
}

/** Place a building without any rule checks (test preconditions only). */
export function rawBuild(g: Game, corner: number, owner: number, kind: Building['kind'] = 'settlement') {
  g.state.buildings[corner] = { owner, kind };
  const p = g.state.players[owner];
  if (kind === 'settlement') p.settlementsLeft--;
  else p.citiesLeft--;
  g.updateLongestRoad();
}

/** Place roads without any rule checks (test preconditions only). */
export function rawRoads(g: Game, edges: number[], owner: number) {
  for (const e of edges) {
    g.state.roads[e] = owner;
    g.state.players[owner].roadsLeft--;
  }
  g.updateLongestRoad();
}

export function give(g: Game, p: number, res: Partial<ResourceMap>) {
  for (const r of RESOURCES) if (res[r]) expectOk(g.debugGive(p, r, res[r]!));
}

/** Roll a forced (non-7) value so the current player reaches the build phase. */
export function rollTo(g: Game, total = 12) {
  expectOk(g.debugForceRoll(total));
  expectOk(g.roll());
}

export function pathEdges(corners: number[]): number[] {
  return corners.slice(1).map((c, i) => edgeBetween(corners[i], c)!);
}

/**
 * First simple path of `len` edges (as a corner list) found by DFS, avoiding
 * the given corners and satisfying `accept`.
 */
export function findPath(
  len: number,
  avoid: Set<number> = new Set(),
  accept: (path: number[]) => boolean = () => true,
): number[] {
  const dfs = (path: number[]): number[] | null => {
    if (path.length === len + 1) return accept(path) ? path : null;
    for (const n of GEO.corners[path[path.length - 1]].neighbors) {
      if (path.includes(n) || avoid.has(n)) continue;
      const found = dfs([...path, n]);
      if (found) return found;
    }
    return null;
  };
  for (const c of GEO.corners) {
    if (avoid.has(c.id)) continue;
    const found = dfs([c.id]);
    if (found) return found;
  }
  throw new Error(`no path of length ${len}`);
}

/** The corners plus every corner adjacent to them. */
export function withNeighbors(corners: Iterable<number>): Set<number> {
  const out = new Set<number>();
  for (const c of corners) {
    out.add(c);
    GEO.corners[c].neighbors.forEach((n) => out.add(n));
  }
  return out;
}

/** Corners that satisfy the distance rule among themselves and avoid `avoid`. */
export function spreadCorners(count: number, avoid: Set<number> = new Set()): number[] {
  const picked: number[] = [];
  const blocked = new Set(avoid);
  for (const c of GEO.corners) {
    if (picked.length === count) break;
    if (blocked.has(c.id) || c.neighbors.some((n) => picked.includes(n))) continue;
    picked.push(c.id);
    blocked.add(c.id);
  }
  if (picked.length < count) throw new Error('not enough free corners');
  return picked;
}

/**
 * A simple path of `len` edges whose corner at `breakAt` has a third neighbour
 * `x` off the path — so an opponent can run a road x→path[breakAt] and settle there.
 */
export function breakableChain(len: number, breakAt: number, avoid = new Set<number>()) {
  const thirdNeighbor = (path: number[]) =>
    GEO.corners[path[breakAt]].neighbors.find((n) => !path.includes(n) && !avoid.has(n));
  const path = findPath(len, avoid, (p) => thirdNeighbor(p) !== undefined);
  return { path, x: thirdNeighbor(path)! };
}

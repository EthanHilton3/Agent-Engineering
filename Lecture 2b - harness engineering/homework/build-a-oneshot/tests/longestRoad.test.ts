import { describe, expect, it } from 'vitest';
import { GEO, edgeBetween } from '../src/game/geometry';
import { longestRoadLength, resolveLongestRoad } from '../src/game/longestRoad';
import type { Game } from '../src/game/game';
import {
  breakableChain, expectOk, findPath, give, newGame, pathEdges, rawBuild, rawRoads, rollTo, skipSetup, withNeighbors,
} from './helpers';

const SETTLEMENT = { wood: 1, brick: 1, wheat: 1, sheep: 1 };

/** Advance to `player`'s build phase. */
function turnOf(g: Game, player: number) {
  if (g.state.phase === 'roll') rollTo(g);
  while (g.state.currentPlayer !== player) {
    expectOk(g.endTurn());
    rollTo(g);
  }
}

describe('longest road length', () => {
  // Scenario 16
  it('a Y of 3 + 3 + 1 roads has length 6, not 7', () => {
    const g = newGame(2);
    const { path, x } = breakableChain(6, 3);
    rawRoads(g, [...pathEdges(path), edgeBetween(path[3], x)!], 0);
    expect(longestRoadLength(g.state.roads, g.state.buildings, 0)).toBe(6);
    expect(g.state.roadLengths[0]).toBe(6);
  });

  it('loops count: a hex ring of 6 plus a tail of 1 has length 7', () => {
    const g = newGame(2);
    const hex = GEO.hexes.find((h) => h.q === 0 && h.r === 0)!;
    const tail = GEO.corners[hex.corners[0]].edges.find((e) => !hex.edges.includes(e))!;
    rawRoads(g, [...hex.edges, tail], 0);
    expect(g.state.roadLengths[0]).toBe(7);
  });

  it("an opponent's building splits the path; your own does not", () => {
    const g = newGame(2);
    const path = findPath(6);
    rawRoads(g, pathEdges(path), 0);
    rawBuild(g, path[2], 0);
    expect(g.state.roadLengths[0]).toBe(6);
    rawBuild(g, path[4], 1);
    expect(g.state.roadLengths[0]).toBe(4);
  });
});

describe('Longest Road card', () => {
  // Scenario 14
  it('4 connected roads give nothing; the 5th grants Longest Road (+2 VP)', () => {
    const g = newGame(2);
    skipSetup(g);
    const path = findPath(5);
    rawBuild(g, path[0], 0);
    rollTo(g);
    give(g, 0, { wood: 5, brick: 5 });
    const edges = pathEdges(path);
    for (const e of edges.slice(0, 4)) expectOk(g.placeRoad(e));
    expect(g.state.roadLengths[0]).toBe(4);
    expect(g.state.longestRoadHolder).toBeNull();
    expect(g.victoryPoints(0)).toBe(1);
    expectOk(g.placeRoad(edges[4]));
    expect(g.state.longestRoadHolder).toBe(0);
    expect(g.victoryPoints(0)).toBe(3);
    expect(g.state.log.at(-1)).toMatch(/P1 takes Longest Road \(length 5\)/);
  });

  // Scenario 15
  it('tying the holder does not take the card; exceeding does', () => {
    const g = newGame(2);
    skipSetup(g);
    const a = findPath(5);
    const b = findPath(6, withNeighbors(a));
    rawBuild(g, a[0], 0);
    rawRoads(g, pathEdges(a), 0);
    expect(g.state.longestRoadHolder).toBe(0);

    rawBuild(g, b[0], 1);
    const bEdges = pathEdges(b);
    rawRoads(g, bEdges.slice(0, 4), 1);
    turnOf(g, 1);
    give(g, 1, { wood: 2, brick: 2 });
    expectOk(g.placeRoad(bEdges[4]));
    expect(g.state.roadLengths).toEqual([5, 5]);
    expect(g.state.longestRoadHolder).toBe(0);
    expectOk(g.placeRoad(bEdges[5]));
    expect(g.state.longestRoadHolder).toBe(1);
    expect(g.victoryPoints(0)).toBe(1);
    expect(g.victoryPoints(1)).toBe(3);
  });

  // Scenario 17
  describe('broken road', () => {
    /** P1 holds Longest Road with a 6-chain; P2 can settle on its middle corner. */
    function brokenSetup(players: number, chainLen = 6, breakAt = 3) {
      const g = newGame(players);
      skipSetup(g);
      const { path, x } = breakableChain(chainLen, breakAt);
      rawRoads(g, pathEdges(path), 0);
      rawRoads(g, [edgeBetween(x, path[breakAt])!], 1);
      expect(g.state.longestRoadHolder).toBe(0);
      const used = withNeighbors([...path, x]);
      return { g, path, used, breakCorner: path[breakAt] };
    }

    function breakIt(g: Game, corner: number) {
      turnOf(g, 1);
      give(g, 1, SETTLEMENT);
      expectOk(g.placeSettlement(corner));
    }

    it('sets the card aside when nobody else has 5', () => {
      const { g, breakCorner } = brokenSetup(2);
      breakIt(g, breakCorner);
      expect(g.state.roadLengths[0]).toBe(3);
      expect(g.state.longestRoadHolder).toBeNull();
      expect(g.victoryPoints(0)).toBe(0);
      expect(g.state.log.some((l) => /Longest Road is set aside/.test(l))).toBe(true);
    });

    it('gives the card to the one player who is now uniquely longest', () => {
      const { g, used, breakCorner } = brokenSetup(2);
      rawRoads(g, pathEdges(findPath(5, used)), 1);
      expect(g.state.longestRoadHolder).toBe(0);
      breakIt(g, breakCorner);
      expect(g.state.roadLengths).toEqual([3, 5]);
      expect(g.state.longestRoadHolder).toBe(1);
    });

    it('sets the card aside when several players tie for longest', () => {
      const { g, used, breakCorner } = brokenSetup(3);
      const p2Chain = findPath(5, used);
      rawRoads(g, pathEdges(p2Chain), 1);
      rawRoads(g, pathEdges(findPath(5, new Set([...used, ...withNeighbors(p2Chain)]))), 2);
      breakIt(g, breakCorner);
      expect(g.state.roadLengths).toEqual([3, 5, 5]);
      expect(g.state.longestRoadHolder).toBeNull();
    });

    it('the holder keeps the card if still tied for longest', () => {
      const { g, used, breakCorner } = brokenSetup(2, 7, 2);
      rawRoads(g, pathEdges(findPath(5, used)), 1);
      breakIt(g, breakCorner);
      expect(g.state.roadLengths).toEqual([5, 5]);
      expect(g.state.longestRoadHolder).toBe(0);
    });
  });

  it('resolveLongestRoad follows the rules table', () => {
    expect(resolveLongestRoad([4, 3], null)).toBeNull();
    expect(resolveLongestRoad([5, 3], null)).toBe(0);
    expect(resolveLongestRoad([5, 5], null)).toBeNull();
    expect(resolveLongestRoad([5, 5], 0)).toBe(0);
    expect(resolveLongestRoad([5, 6], 0)).toBe(1);
    expect(resolveLongestRoad([3, 6, 6], 0)).toBeNull();
    expect(resolveLongestRoad([4, 4], 0)).toBeNull();
  });
});

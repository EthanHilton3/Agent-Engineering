import { describe, expect, it } from 'vitest';
import { edgeBetween } from '../src/game/geometry';
import {
  breakableChain, expectFail, expectOk, findPath, give, newGame, pathEdges, rawBuild, rawRoads, rollTo, skipSetup,
  spreadCorners, withNeighbors,
} from './helpers';

describe('victory', () => {
  // Scenario 20
  it('reaching 10 VP on your own turn ends the game', () => {
    const g = newGame(2);
    skipSetup(g);
    const path = findPath(2);
    rawBuild(g, path[0], 0);
    rawRoads(g, pathEdges(path), 0);
    spreadCorners(4, withNeighbors(path)).forEach((c) => rawBuild(g, c, 0, 'city'));
    expect(g.victoryPoints(0)).toBe(9);
    rollTo(g);
    expect(g.state.winner).toBeNull();
    give(g, 0, { wood: 2, brick: 2, wheat: 1, sheep: 1 });
    expectOk(g.placeSettlement(path[2]));
    expect(g.victoryPoints(0)).toBe(10);
    expect(g.state.winner).toBe(0);
    expect(g.state.phase).toBe('game-over');
    expect(g.state.log.at(-1)).toMatch(/P1 wins/);
    expectFail(g.endTurn(), /game is over/);
    expectFail(g.roll(), /game is over/);
    expectFail(g.bankTrade('wood', 'ore'), /game is over/);
    expectFail(g.placeRoad(pathEdges(path)[0]), /game is over/);
  });

  it('10 VP reached on another player’s turn wins at the start of your next turn', () => {
    const g = newGame(3);
    skipSetup(g);
    // P3 holds Longest Road with a 6-chain that P1 can break.
    const { path, x } = breakableChain(6, 3);
    rawRoads(g, pathEdges(path), 2);
    rawRoads(g, [edgeBetween(x, path[3])!], 0);
    // P2 has a 5-chain and 4 cities (8 VP).
    const used = withNeighbors([...path, x]);
    const p2Chain = findPath(5, used);
    rawRoads(g, pathEdges(p2Chain), 1);
    [p2Chain[0], p2Chain[2], p2Chain[4]].forEach((c) => rawBuild(g, c, 1, 'city'));
    rawBuild(g, spreadCorners(1, new Set([...used, ...withNeighbors(p2Chain)]))[0], 1, 'city');
    expect(g.state.longestRoadHolder).toBe(2);
    expect(g.victoryPoints(1)).toBe(8);

    rollTo(g);
    give(g, 0, { wood: 1, brick: 1, wheat: 1, sheep: 1 });
    expectOk(g.placeSettlement(path[3]));
    expect(g.state.longestRoadHolder).toBe(1);
    expect(g.victoryPoints(1)).toBe(10);
    expect(g.state.winner).toBeNull(); // not P2's turn
    expect(g.state.phase).toBe('main');

    expectOk(g.endTurn());
    expect(g.state.winner).toBe(1);
    expect(g.state.phase).toBe('game-over');
  });
});

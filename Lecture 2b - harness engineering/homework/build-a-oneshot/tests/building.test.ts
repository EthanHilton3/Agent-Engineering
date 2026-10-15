import { describe, expect, it } from 'vitest';
import { GEO, edgeBetween } from '../src/game/geometry';
import {
  expectFail, expectOk, findPath, give, newGame, pathEdges, rawBuild, rawRoads, rollTo, skipSetup,
  spreadCorners, withNeighbors,
} from './helpers';

const ROAD = { wood: 1, brick: 1 };
const SETTLEMENT = { wood: 1, brick: 1, wheat: 1, sheep: 1 };
const CITY = { ore: 3, wheat: 2 };

describe('building', () => {
  // Scenario 13
  it('nothing can be built or traded before rolling', () => {
    const g = newGame(2);
    skipSetup(g);
    const corner = 10;
    rawBuild(g, corner, 0);
    give(g, 0, { wood: 6, brick: 2, wheat: 3, sheep: 1, ore: 3 });
    expect(g.state.phase).toBe('roll');
    expectFail(g.placeRoad(GEO.corners[corner].edges[0]), /Roll the dice first/);
    expectFail(g.placeCity(corner), /Roll the dice first/);
    expectFail(g.placeSettlement(30), /Roll the dice first/);
    expectFail(g.bankTrade('wood', 'ore'), /Roll the dice first/);
    expectFail(g.endTurn(), /Roll the dice first/);
    rollTo(g);
    expectFail(g.roll(), /already rolled/);
    expectOk(g.placeRoad(GEO.corners[corner].edges[0]));
    expectOk(g.placeCity(corner));
    expectOk(g.bankTrade('wood', 'ore'));
  });

  it('building costs resources, which return to the bank', () => {
    const g = newGame(2);
    skipSetup(g);
    rawBuild(g, 10, 0);
    rollTo(g);
    expectFail(g.placeRoad(GEO.corners[10].edges[0]), /Not enough resources/);
    give(g, 0, ROAD);
    expect(g.state.bank.wood).toBe(18);
    expectOk(g.placeRoad(GEO.corners[10].edges[0]));
    expect(g.state.bank.wood).toBe(19);
    expect(g.state.players[0].roadsLeft).toBe(14);
  });

  it('settlements must touch your own road and obey the distance rule', () => {
    const g = newGame(2);
    skipSetup(g);
    const path = findPath(2);
    rawBuild(g, path[0], 0);
    rollTo(g);
    give(g, 0, { ...ROAD, ...SETTLEMENT });
    give(g, 0, SETTLEMENT);
    const lonely = GEO.corners.find((c) => !withNeighbors(path).has(c.id))!.id;
    expectFail(g.placeSettlement(lonely), /touch one of your roads/);
    expectOk(g.placeRoad(edgeBetween(path[0], path[1])!));
    expectFail(g.placeSettlement(path[1]), /distance rule/);
    give(g, 0, ROAD);
    expectOk(g.placeRoad(edgeBetween(path[1], path[2])!));
    expectOk(g.placeSettlement(path[2]));
    expect(g.victoryPoints(0)).toBe(2);
  });

  // Scenario 12
  it("a road cannot extend through an opponent's settlement", () => {
    const g = newGame(2);
    skipSetup(g);
    const path = findPath(3, new Set(), (p) =>
      GEO.corners[p[1]].neighbors.length === 3 && GEO.corners[p[2]].neighbors.length === 3);
    const [start, a, b, c] = path;
    rawBuild(g, start, 0);
    rawRoads(g, pathEdges([start, a, b]), 0);
    rawBuild(g, b, 1); // opponent settles on the end of P1's road
    rollTo(g);
    give(g, 0, ROAD);
    const through = edgeBetween(b, c)!;
    expect(g.legalRoadEdges()).not.toContain(through);
    expectFail(g.placeRoad(through), /opponent's building/);
    // Every edge leaving the blocked corner is illegal for P1.
    for (const e of GEO.corners[b].edges) expect(g.legalRoadEdges()).not.toContain(e);
    // But extending from P1's own corner is fine.
    const branch = GEO.corners[a].edges.find((e) => g.state.roads[e] === null)!;
    expectOk(g.placeRoad(branch));
  });

  it('a city must replace your own settlement and returns the settlement piece', () => {
    const g = newGame(2);
    skipSetup(g);
    rawBuild(g, 10, 0);
    rawBuild(g, 30, 1);
    rollTo(g);
    give(g, 0, CITY);
    give(g, 0, CITY);
    expectFail(g.placeCity(30), /your own settlements/);
    expectFail(g.placeCity(20), /your own settlements/);
    expect(g.state.players[0].settlementsLeft).toBe(4);
    expectOk(g.placeCity(10));
    expect(g.state.players[0].settlementsLeft).toBe(5);
    expect(g.state.players[0].citiesLeft).toBe(3);
    expect(g.victoryPoints(0)).toBe(2);
    expectFail(g.placeCity(10), /your own settlements/);
  });

  // Scenario 18
  it('with all 5 settlements placed, another needs a city upgrade first', () => {
    const g = newGame(2);
    skipSetup(g);
    const path = findPath(2);
    const others = spreadCorners(4, withNeighbors(path));
    rawBuild(g, path[0], 0);
    others.forEach((c) => rawBuild(g, c, 0));
    rawRoads(g, pathEdges(path), 0);
    expect(g.state.players[0].settlementsLeft).toBe(0);
    rollTo(g);
    give(g, 0, { ...SETTLEMENT, ...CITY, wheat: 3 });
    expect(g.legalSettlementCorners()).toContain(path[2]);
    expectFail(g.placeSettlement(path[2]), /no settlements left/);
    expectOk(g.placeCity(others[0]));
    expectOk(g.placeSettlement(path[2]));
    expect(g.state.players[0].settlementsLeft).toBe(0);
  });

  it('enforces the road and city piece limits', () => {
    const g = newGame(2);
    skipSetup(g);
    rawBuild(g, 10, 0);
    g.state.players[0].roadsLeft = 0;
    g.state.players[0].citiesLeft = 0;
    rollTo(g);
    give(g, 0, { ...ROAD, ...CITY });
    expectFail(g.placeRoad(GEO.corners[10].edges[0]), /no roads left/);
    expectFail(g.placeCity(10), /no cities left/);
  });
});

describe('bank trade', () => {
  // Scenario 19
  it('4 identical resources buy 1 of your choice; 3 is not enough', () => {
    const g = newGame(2);
    skipSetup(g);
    rollTo(g);
    give(g, 0, { wood: 3 });
    expectFail(g.bankTrade('wood', 'ore'), /need 4 wood/);
    give(g, 0, { wood: 1 });
    expectFail(g.bankTrade('wood', 'wood'), /different/);
    expectOk(g.bankTrade('wood', 'ore'));
    expect(g.state.players[0].resources).toMatchObject({ wood: 0, ore: 1 });
    expect(g.state.bank).toMatchObject({ wood: 19, ore: 18 });
  });

  it('cannot buy a resource the bank has run out of', () => {
    const g = newGame(2);
    skipSetup(g);
    rollTo(g);
    give(g, 1, { ore: 19 });
    give(g, 0, { wood: 4 });
    expectFail(g.bankTrade('wood', 'ore'), /no ore left/);
  });
});

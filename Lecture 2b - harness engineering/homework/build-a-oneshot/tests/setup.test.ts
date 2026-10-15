import { describe, expect, it } from 'vitest';
import { GEO } from '../src/game/geometry';
import { TERRAIN_RESOURCE, totalCards } from '../src/game/types';
import { expectFail, expectOk, newGame, withNeighbors } from './helpers';
import type { Game } from '../src/game/game';

/** Place a settlement plus its first legal road for the current setup player. */
function setupPlace(g: Game, corner: number) {
  expectOk(g.placeSettlement(corner));
  expectOk(g.placeRoad(g.legalRoadEdges()[0]));
}

describe('setup phase', () => {
  // Scenario 5
  it('uses snake order 1, 2, 3, 3, 2, 1 with 3 players', () => {
    const g = newGame(3);
    const order: number[] = [];
    while (g.isSetup) {
      expect(g.state.phase).toBe('setup-settlement');
      order.push(g.state.currentPlayer + 1);
      setupPlace(g, g.legalSettlementCorners()[0]);
    }
    expect(order).toEqual([1, 2, 3, 3, 2, 1]);
    expect(g.state.phase).toBe('roll');
    expect(g.state.currentPlayer).toBe(0);
  });

  // Scenario 3
  it('does not offer corners one edge from an existing settlement', () => {
    const g = newGame(2);
    const corner = GEO.corners.find((c) => c.neighbors.length === 3)!.id;
    setupPlace(g, corner);
    const legal = g.legalSettlementCorners();
    for (const n of GEO.corners[corner].neighbors) {
      expect(legal).not.toContain(n);
      expectFail(g.placeSettlement(n), /distance rule/);
    }
    expect(legal).not.toContain(corner);
    // Two edges away is fine.
    const twoAway = GEO.corners[GEO.corners[corner].neighbors[0]].neighbors.find((c) => c !== corner)!;
    expect(legal).toContain(twoAway);
  });

  it('requires the setup road to touch the settlement just placed', () => {
    const g = newGame(2);
    const corner = GEO.corners[20].id;
    expectOk(g.placeSettlement(corner));
    const legal = g.legalRoadEdges();
    expect(legal.sort()).toEqual([...GEO.corners[corner].edges].sort());
    const far = GEO.edges.find((e) => !e.corners.includes(corner))!.id;
    expectFail(g.placeRoad(far), /must touch/);
    expectFail(g.placeSettlement(GEO.corners[40].id), /road now/);
  });

  // Scenario 4
  it('grants resources only for the second settlement, one per non-desert hex', () => {
    const g = newGame(2, 'setup-res');
    const desert = g.state.board.desertHex;
    const nextToDesert = GEO.corners.find((c) => c.hexes.length === 3 && c.hexes.includes(desert))!.id;
    const reserved = withNeighbors([nextToDesert]);
    const pickThreeHex = () =>
      g.legalSettlementCorners().find(
        (c) => !reserved.has(c) && GEO.corners[c].hexes.length === 3 && !GEO.corners[c].hexes.includes(desert),
      )!;

    // P1 first settlement: nothing.
    setupPlace(g, pickThreeHex());
    expect(totalCards(g.state.players[0].resources)).toBe(0);

    // P2 first settlement: nothing; P2 second settlement touches 3 non-desert hexes.
    setupPlace(g, pickThreeHex());
    expect(totalCards(g.state.players[1].resources)).toBe(0);
    const p2Second = pickThreeHex();
    setupPlace(g, p2Second);
    expect(totalCards(g.state.players[1].resources)).toBe(3);
    for (const h of GEO.corners[p2Second].hexes) {
      const r = TERRAIN_RESOURCE[g.state.board.tiles[h].terrain]!;
      expect(g.state.players[1].resources[r]).toBeGreaterThan(0);
    }

    // P1 second settlement next to the desert: only 2 resources.
    expect(g.legalSettlementCorners()).toContain(nextToDesert);
    setupPlace(g, nextToDesert);
    expect(totalCards(g.state.players[0].resources)).toBe(2);
    expect(g.state.bank.wood + g.state.bank.brick + g.state.bank.sheep + g.state.bank.wheat + g.state.bank.ore)
      .toBe(19 * 5 - 5);
  });
});

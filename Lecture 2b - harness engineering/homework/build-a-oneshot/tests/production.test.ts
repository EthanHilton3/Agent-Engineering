import { describe, expect, it } from 'vitest';
import { GEO } from '../src/game/geometry';
import { TERRAIN_RESOURCE, totalCards, type Resource } from '../src/game/types';
import type { Game } from '../src/game/game';
import { expectOk, give, newGame, rawBuild, rollTo, skipSetup } from './helpers';

/** A corner touching three non-desert hexes whose numbers are all distinct. */
function threeHexCorner(g: Game): number {
  const tiles = g.state.board.tiles;
  return GEO.corners.find(
    (c) =>
      c.hexes.length === 3 &&
      c.hexes.every((h) => tiles[h].number !== null) &&
      new Set(c.hexes.map((h) => tiles[h].number)).size === 3,
  )!.id;
}

function resourceOf(g: Game, hex: number): Resource {
  return TERRAIN_RESOURCE[g.state.board.tiles[hex].terrain]!;
}

/** Roll `total` on the current player's turn, then pass the turn back to roll again. */
function rollAndEnd(g: Game, total: number) {
  rollTo(g, total);
  expectOk(g.endTurn());
}

describe('dice production', () => {
  // Scenario 6
  it('a settlement on a three-hex corner produces from each hex', () => {
    const g = newGame(2, 'prod');
    skipSetup(g);
    const corner = threeHexCorner(g);
    rawBuild(g, corner, 0);
    for (const h of GEO.corners[corner].hexes) {
      const r = resourceOf(g, h);
      const before = g.state.players[0].resources[r];
      const beforeTotal = totalCards(g.state.players[0].resources);
      rollAndEnd(g, g.state.board.tiles[h].number!);
      expect(g.state.players[0].resources[r]).toBe(before + 1);
      expect(totalCards(g.state.players[0].resources)).toBe(beforeTotal + 1);
      rollAndEnd(g, 12 === g.state.board.tiles[h].number ? 2 : 12); // back to P1
    }
  });

  // Scenario 7
  it('a city produces 2 resources per roll', () => {
    const g = newGame(2, 'prod');
    skipSetup(g);
    const corner = threeHexCorner(g);
    rawBuild(g, corner, 0, 'city');
    const h = GEO.corners[corner].hexes[0];
    const r = resourceOf(g, h);
    rollTo(g, g.state.board.tiles[h].number!);
    expect(g.state.players[0].resources[r]).toBe(2);
    expect(totalCards(g.state.players[0].resources)).toBe(2);
    expect(g.state.bank[r]).toBe(17);
  });

  // Scenario 8
  it('the robber blocks production on its hex', () => {
    const g = newGame(2, 'prod');
    skipSetup(g);
    const corner = threeHexCorner(g);
    rawBuild(g, corner, 0);
    const [blocked, other] = GEO.corners[corner].hexes;

    rollTo(g, 7);
    expectOk(g.moveRobber(blocked));
    expect(g.state.phase).toBe('main');
    expectOk(g.endTurn());

    rollTo(g, g.state.board.tiles[blocked].number!);
    expect(totalCards(g.state.players[0].resources)).toBe(0);
    expectOk(g.endTurn());

    // An unblocked neighbour still produces.
    rollTo(g, g.state.board.tiles[other].number!);
    expect(g.state.players[0].resources[resourceOf(g, other)]).toBe(1);
  });

  // Scenario 11
  describe('bank shortage', () => {
    /** A fields hex and two of its corners, 3 apart, whose other hexes don't share its number. */
    function wheatSetup(g: Game) {
      const tiles = g.state.board.tiles;
      for (const hex of GEO.hexes) {
        if (tiles[hex.id].terrain !== 'fields') continue;
        const n = tiles[hex.id].number;
        const clean = (c: number) =>
          GEO.corners[c].hexes.every((h) => h === hex.id || tiles[h].number !== n);
        for (let i = 0; i < 3; i++) {
          const a = hex.corners[i];
          const b = hex.corners[i + 3];
          if (clean(a) && clean(b)) return { hex: hex.id, number: n!, a, b };
        }
      }
      throw new Error('no suitable fields hex');
    }

    it('nobody gets wheat when the bank cannot pay every player owed it', () => {
      const g = newGame(3, 'shortage');
      skipSetup(g);
      const { number, a, b } = wheatSetup(g);
      rawBuild(g, a, 0, 'city');
      rawBuild(g, b, 1, 'city');
      give(g, 2, { wheat: 17 });
      expect(g.state.bank.wheat).toBe(2);
      rollTo(g, number);
      expect(g.state.players[0].resources.wheat).toBe(0);
      expect(g.state.players[1].resources.wheat).toBe(0);
      expect(g.state.bank.wheat).toBe(2);
      expect(g.state.log.some((l) => /nobody receives wheat/.test(l))).toBe(true);
    });

    it('a single player owed more than the bank has gets what is left', () => {
      const g = newGame(3, 'shortage');
      skipSetup(g);
      const { number, a, b } = wheatSetup(g);
      rawBuild(g, a, 0, 'city');
      rawBuild(g, b, 0, 'settlement');
      give(g, 2, { wheat: 17 });
      rollTo(g, number);
      expect(g.state.players[0].resources.wheat).toBe(2);
      expect(g.state.bank.wheat).toBe(0);
    });

    it('other resources from the same roll are still paid', () => {
      const g = newGame(3, 'shortage');
      skipSetup(g);
      const { hex, number, a, b } = wheatSetup(g);
      rawBuild(g, a, 0, 'city');
      rawBuild(g, b, 1, 'city');
      // Another hex with the same number but a different resource.
      const tiles = g.state.board.tiles;
      const twin = GEO.hexes.find(
        (h) => h.id !== hex && tiles[h.id].number === number && tiles[h.id].terrain !== 'fields',
      )!;
      const twinRes = TERRAIN_RESOURCE[tiles[twin.id].terrain]!;
      const twinCorner = twin.corners.find(
        (c) => !g.state.buildings[c] && GEO.corners[c].neighbors.every((x) => !g.state.buildings[x]),
      )!;
      rawBuild(g, twinCorner, 2);
      give(g, 2, { wheat: 17 });
      const before = g.state.players[2].resources[twinRes];
      rollTo(g, number);
      expect(g.state.players[2].resources[twinRes]).toBeGreaterThan(before);
    });
  });
});

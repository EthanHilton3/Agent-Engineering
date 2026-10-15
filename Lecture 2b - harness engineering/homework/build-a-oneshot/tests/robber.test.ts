import { describe, expect, it } from 'vitest';
import { GEO } from '../src/game/geometry';
import { totalCards } from '../src/game/types';
import { expectFail, expectOk, give, newGame, rawBuild, rollTo, skipSetup } from './helpers';

describe('rolling a 7', () => {
  // Scenario 9
  it('a player with 9 cards discards 4; a player with 7 discards nothing', () => {
    const g = newGame(3, 'seven');
    skipSetup(g);
    give(g, 0, { wood: 5, ore: 4 });
    give(g, 1, { wheat: 7 });
    give(g, 2, { sheep: 8 });
    rollTo(g, 7);
    expect(g.state.phase).toBe('discard');
    expect(g.state.pendingDiscards).toEqual([
      { player: 0, amount: 4 },
      { player: 2, amount: 4 },
    ]);

    expectFail(g.discard(2, { sheep: 4 }), /P1's turn to discard/);
    expectFail(g.discard(0, { wood: 3 }), /exactly 4/);
    expectFail(g.discard(0, { ore: 5 }), /only have 4 ore/);
    expectFail(g.moveRobber(5), /can't move the robber/);
    expectOk(g.discard(0, { wood: 2, ore: 2 }));
    expect(totalCards(g.state.players[0].resources)).toBe(5);
    expect(g.state.bank.wood).toBe(19 - 3);

    expectOk(g.discard(2, { sheep: 4 }));
    expect(totalCards(g.state.players[1].resources)).toBe(7);
    expect(g.state.phase).toBe('move-robber');
  });

  it('no production happens on a 7 and the robber must move to a new hex', () => {
    const g = newGame(2, 'seven');
    skipSetup(g);
    rollTo(g, 7);
    expect(g.state.phase).toBe('move-robber');
    expectFail(g.moveRobber(g.state.robberHex), /different hex/);
    expectFail(g.placeRoad(0), /Finish the current step/);
    expectOk(g.moveRobber((g.state.robberHex + 1) % 19));
    expect(g.state.phase).toBe('main');
  });

  // Scenario 10
  it('only opponents touching the robber hex can be robbed, never the roller', () => {
    const g = newGame(3, 'steal');
    skipSetup(g);
    const hex = GEO.hexes.find((h) => h.id !== g.state.robberHex && h.corners.length === 6)!;
    const [c0, , c2, , c4] = hex.corners;
    rawBuild(g, c0, 0); // roller's own building on the hex
    rawBuild(g, c2, 1);
    const far = GEO.corners.find(
      (c) => !c.hexes.includes(hex.id) && c.neighbors.every((n) => !hex.corners.includes(n)),
    )!.id;
    rawBuild(g, far, 2);
    give(g, 1, { brick: 2 });
    give(g, 2, { ore: 2 });

    rollTo(g, 7);
    expect(g.robbableAt(hex.id)).toEqual([1]);
    expectOk(g.moveRobber(hex.id));
    // Single candidate: stolen automatically.
    expect(g.state.phase).toBe('main');
    expect(g.state.players[0].resources.brick).toBe(1);
    expect(g.state.players[1].resources.brick).toBe(1);
    expect(g.state.players[2].resources.ore).toBe(2);

    // Now P3 also borders the hex: P1 must choose, and can't pick themselves.
    rawBuild(g, c4, 2);
    g.state.robberHex = g.state.board.desertHex;
    expectOk(g.endTurn());
    rollTo(g, 2); // P2
    expectOk(g.endTurn());
    rollTo(g, 2); // P3
    expectOk(g.endTurn());
    rollTo(g, 7); // P1 again
    expectOk(g.moveRobber(hex.id));
    expect(g.state.phase).toBe('steal');
    expect(g.state.stealCandidates).toEqual([1, 2]);
    expectFail(g.steal(0), /no building/);
    expectFail(g.endTurn(), /Finish the current step/);
    const before = totalCards(g.state.players[0].resources);
    expectOk(g.steal(2));
    expect(totalCards(g.state.players[0].resources)).toBe(before + 1);
    expect(g.state.phase).toBe('main');
  });

  it('robbing an opponent with no cards steals nothing', () => {
    const g = newGame(2, 'steal-empty');
    skipSetup(g);
    const hex = GEO.hexes.find((h) => h.id !== g.state.robberHex)!;
    rawBuild(g, hex.corners[0], 1);
    rollTo(g, 7);
    expectOk(g.moveRobber(hex.id));
    expect(totalCards(g.state.players[0].resources)).toBe(0);
    expect(g.state.phase).toBe('main');
  });
});

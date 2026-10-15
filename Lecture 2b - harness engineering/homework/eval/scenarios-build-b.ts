/**
 * Independent acceptance check for build B (Claude Code + native harness) against spec.md's 20 scenarios.
 * Same checks as scenarios-build-a.ts, ported to build B's API (pure `applyAction(state, action)`).
 *
 * Run from build-b-claude/:  npx vite-node ../eval/scenarios-build-b.ts
 */
import { applyAction, createGame } from '../build-b-claude/src/engine/game';
import { generateBoard } from '../build-b-claude/src/engine/board';
import { TOPOLOGY, edgeBetween } from '../build-b-claude/src/engine/topology';
import { legalRoadEdges, legalSettlementCorners } from '../build-b-claude/src/engine/placement';
import { roadLength, updateLongestRoad } from '../build-b-claude/src/engine/longestRoad';
import { victoryPoints } from '../build-b-claude/src/engine/scoring';
import { terrainResource, totalCards } from '../build-b-claude/src/engine/resources';
import type { Action, GameState, Resource } from '../build-b-claude/src/engine/types';

type Outcome = { id: number; name: string; pass: boolean; notes: string[] };
const results: Outcome[] = [];

function scenario(id: number, name: string, fn: (check: (cond: boolean, note: string) => void) => void) {
  const notes: string[] = [];
  let pass = true;
  const check = (cond: boolean, note: string) => {
    if (!cond) pass = false;
    notes.push(`${cond ? 'ok  ' : 'FAIL'} ${note}`);
  };
  try {
    fn(check);
  } catch (e) {
    pass = false;
    notes.push(`FAIL threw: ${(e as Error).message}`);
  }
  results.push({ id, name, pass, notes });
}

// ------------------------------------------------------------------ helpers

const CORNERS = TOPOLOGY.cornerHexes.length;
const neighbors = (c: number) => TOPOLOGY.cornerNeighbors[c];
const cornerEdges = (c: number) => TOPOLOGY.cornerEdges[c];
const hexCorners = (h: number) => TOPOLOGY.hexCorners[h];
const between = (a: number, b: number) => edgeBetween(a, b)!;

/** Mutable wrapper so scenarios read like build A's: g.s is the current state; act() advances it. */
class G {
  s: GameState;
  lastError = '';
  constructor(players = 3, seed = 12345) {
    this.s = createGame({ seed, playerNames: Array.from({ length: players }, (_, i) => `P${i}`) });
  }
  act(action: Action): boolean {
    const r = applyAction(this.s, action);
    if (r.ok) this.s = r.state;
    else this.lastError = r.error;
    return r.ok;
  }
  /** Skip setup and drop into `kind` for `player` on an empty board. */
  inPhase(player: number, kind: 'roll' | 'main') {
    this.s.currentPlayer = player;
    this.s.phase = { kind };
  }
  give(p: number, r: Resource, n: number) {
    this.s.players[p].hand[r] += n;
    this.s.bank[r] -= n;
  }
  setRoads(edges: number[], owner: number) {
    for (const e of edges) this.s.roads[e] = owner;
    updateLongestRoad(this.s);
  }
  forceRoll(total: number) {
    this.act({ type: 'debugForceRoll', total });
    this.act({ type: 'roll' });
  }
  tile(h: number) {
    return this.s.board.hexes[h];
  }
}

function hexesAdjacent(a: number, b: number) {
  return hexCorners(a).filter((c) => hexCorners(b).includes(c)).length === 2;
}

function findPath(len: number, avoid = new Set<number>(), accept: (path: number[]) => boolean = () => true): number[] {
  const dfs = (path: number[]): number[] | null => {
    if (path.length === len + 1) return accept(path) ? path : null;
    for (const n of neighbors(path[path.length - 1])) {
      if (path.includes(n) || avoid.has(n)) continue;
      const found = dfs([...path, n]);
      if (found) return found;
    }
    return null;
  };
  for (let c = 0; c < CORNERS; c++) {
    if (avoid.has(c)) continue;
    const p = dfs([c]);
    if (p) return p;
  }
  throw new Error(`no path of length ${len}`);
}

const pathEdges = (path: number[]) => path.slice(1).map((c, i) => between(path[i], c));
const farHex = (corners: number[]) => TOPOLOGY.hexCorners.findIndex((cs) => !cs.some((c) => corners.includes(c)));

function playSetup(g: G, onSettlement?: (p: number, corner: number, before: number) => void) {
  const order: number[] = [];
  while (g.s.phase.kind === 'setup') {
    const p = g.s.currentPlayer;
    order.push(p);
    const corner = legalSettlementCorners(g.s)[0];
    const before = totalCards(g.s.players[p].hand);
    if (!g.act({ type: 'placeSettlement', corner })) throw new Error(g.lastError);
    onSettlement?.(p, corner, before);
    if (!g.act({ type: 'placeRoad', edge: legalRoadEdges(g.s)[0] })) throw new Error(g.lastError);
  }
  return order;
}

// ---------------------------------------------------------------- scenarios

scenario(1, 'Deterministic board', (check) => {
  const a = generateBoard(777);
  const b = generateBoard(777);
  check(JSON.stringify(a.hexes) === JSON.stringify(b.hexes), 'same seed → identical hexes');
  check(JSON.stringify(a.hexes) !== JSON.stringify(generateBoard(778).hexes), 'different seed → different hexes');
  check(TOPOLOGY.hexCorners.length === 19 && CORNERS === 54 && TOPOLOGY.edgeCorners.length === 72,
    `topology 19/54/72 (got ${TOPOLOGY.hexCorners.length}/${CORNERS}/${TOPOLOGY.edgeCorners.length})`);
  const terr = a.hexes.map((t) => t.terrain).sort().join(',');
  check(terr === 'desert,fields,fields,fields,fields,forest,forest,forest,forest,hills,hills,hills,mountains,mountains,mountains,pasture,pasture,pasture,pasture',
    'terrain counts match spec');
  const nums = a.hexes.map((t) => t.number).filter((n) => n !== null).sort((x, y) => x! - y!).join(',');
  check(nums === '2,3,3,4,4,5,5,6,6,8,8,9,9,10,10,11,11,12', 'number tokens match spec');
  check(a.hexes.find((h) => h.terrain === 'desert')!.number === null, 'desert has no number');
  const g = new G(2, 777);
  check(g.tile(g.s.robberHex).terrain === 'desert', 'robber starts on desert');
});

scenario(2, 'No adjacent 6/8 across 1000 boards', (check) => {
  let bad = 0;
  const red = (n: number | null) => n === 6 || n === 8;
  for (let i = 0; i < 1000; i++) {
    const hexes = generateBoard(i * 7919 + 1).hexes;
    for (let a = 0; a < 19; a++)
      for (let b = a + 1; b < 19; b++)
        if (red(hexes[a].number) && red(hexes[b].number) && hexesAdjacent(a, b)) bad++;
  }
  check(bad === 0, `adjacent red pairs found: ${bad} (checked with independent adjacency)`);
});

scenario(3, 'Distance rule in setup', (check) => {
  const g = new G();
  const c = [...Array(CORNERS).keys()].find((x) => neighbors(x).length === 3)!;
  check(g.act({ type: 'placeSettlement', corner: c }), 'P0 places settlement');
  check(g.act({ type: 'placeRoad', edge: cornerEdges(c)[0] }), 'P0 places road');
  const legal = legalSettlementCorners(g.s);
  check(neighbors(c).every((n) => !legal.includes(n)), 'neighbors not offered as legal');
  check(!legal.includes(c), 'occupied corner not offered');
  check(!g.act({ type: 'placeSettlement', corner: neighbors(c)[0] }), 'placing on a neighbor is rejected');
  const twoAway = neighbors(neighbors(c)[0]).find((x) => x !== c && !neighbors(c).includes(x))!;
  check(legal.includes(twoAway), 'corner two edges away is legal');
});

scenario(4, 'Only second setup settlement grants resources', (check) => {
  const g = new G(3);
  let count = 0;
  playSetup(g, (p, corner, before) => {
    count++;
    const after = totalCards(g.s.players[p].hand);
    const expected = TOPOLOGY.cornerHexes[corner].filter((h) => g.tile(h).terrain !== 'desert').length;
    if (count <= 3) check(after === before, `first settlement P${p}: +${after - before} (expect 0)`);
    else check(after - before === expected, `second settlement P${p}: +${after - before} (expect ${expected})`);
  });
  const total = totalCards(g.s.bank) + g.s.players.reduce((s, p) => s + totalCards(p.hand), 0);
  check(total === 95, `card conservation: bank + hands = ${total} (expect 95)`);
});

scenario(5, 'Snake order 1,2,3,3,2,1', (check) => {
  const g = new G(3);
  const order = playSetup(g);
  check(order.join(',') === '0,1,2,2,1,0', `order was ${order.join(',')}`);
  check(g.s.phase.kind === 'roll' && g.s.currentPlayer === 0, 'player 1 takes first normal turn');
  check(playSetup(new G(4)).join(',') === '0,1,2,3,3,2,1,0', '4-player order correct');
});

scenario(6, 'Shared-corner production from all 3 hexes', (check) => {
  const g = new G();
  g.inPhase(0, 'roll');
  const corner = [...Array(CORNERS).keys()].find((c) => TOPOLOGY.cornerHexes[c].length === 3 &&
    TOPOLOGY.cornerHexes[c].every((h) => g.tile(h).terrain !== 'desert'))!;
  const hexes = TOPOLOGY.cornerHexes[corner];
  g.s.buildings[corner] = { owner: 0, kind: 'settlement' };
  const nums = [3, 4, 5];
  g.s.board.hexes.forEach((t) => { if (t.number !== null && nums.includes(t.number)) t.number = 12; });
  hexes.forEach((h, i) => (g.tile(h).number = nums[i]));
  g.s.robberHex = farHex([corner]);
  hexes.forEach((h, i) => {
    const r = terrainResource(g.tile(h).terrain)!;
    const before = g.s.players[0].hand[r];
    g.s.phase = { kind: 'roll' };
    g.forceRoll(nums[i]);
    check(g.s.players[0].hand[r] === before + 1, `roll ${nums[i]} → +1 ${r}`);
  });
});

scenario(7, 'City produces 2', (check) => {
  const g = new G();
  g.inPhase(0, 'roll');
  const hex = TOPOLOGY.hexCorners.findIndex((_, h) => g.tile(h).number !== null && h !== g.s.robberHex);
  const num = g.tile(hex).number!;
  const r = terrainResource(g.tile(hex).terrain)!;
  const corner = hexCorners(hex)[0];
  g.s.buildings[corner] = { owner: 0, kind: 'city' };
  g.forceRoll(num);
  const expected = TOPOLOGY.cornerHexes[corner]
    .filter((h) => g.tile(h).number === num && terrainResource(g.tile(h).terrain) === r && h !== g.s.robberHex).length * 2;
  check(g.s.players[0].hand[r] === expected, `city got ${g.s.players[0].hand[r]} ${r} (expect ${expected})`);
});

scenario(8, 'Robber blocks production', (check) => {
  const g = new G();
  g.inPhase(0, 'roll');
  const hex = TOPOLOGY.hexCorners.findIndex((_, h) => g.tile(h).number !== null);
  const num = g.tile(hex).number!;
  const corner = hexCorners(hex).find((c) => TOPOLOGY.cornerHexes[c].every((h) => h === hex || g.tile(h).number !== num))!;
  g.s.buildings[corner] = { owner: 0, kind: 'settlement' };
  g.s.robberHex = hex;
  g.forceRoll(num);
  check(totalCards(g.s.players[0].hand) === 0, `blocked hex produced ${totalCards(g.s.players[0].hand)} cards`);
});

scenario(9, 'Discard on 7: 9 cards → 4, 7 cards → 0', (check) => {
  const g = new G(3);
  g.inPhase(0, 'roll');
  g.give(1, 'wood', 5); g.give(1, 'ore', 4);
  g.give(2, 'sheep', 7);
  g.forceRoll(7);
  const phase = g.s.phase;
  check(phase.kind === 'discard', `phase is ${phase.kind}`);
  const pend = phase.kind === 'discard' ? phase.pending : [];
  check(pend.length === 1 && pend[0].player === 1 && pend[0].amount === 4, `pending: ${JSON.stringify(pend)}`);
  check(!g.act({ type: 'discard', cards: { wood: 3 } }), 'discarding 3 instead of 4 is rejected');
  check(g.act({ type: 'discard', cards: { wood: 2, ore: 2 } }), 'P1 discards 4 of their choice');
  check(totalCards(g.s.players[1].hand) === 5 && g.s.phase.kind === 'moveRobber', 'P1 left with 5, move to robber');
  check(totalCards(g.s.players[2].hand) === 7, 'P2 (7 cards) untouched');
  check(!g.act({ type: 'placeRoad', edge: 0 }) && !g.act({ type: 'endTurn' }), 'cannot build or end turn before robber is resolved');
});

scenario(10, 'Steal targeting', (check) => {
  const g = new G(4);
  g.inPhase(0, 'main');
  const hex = TOPOLOGY.hexCorners.findIndex((_, h) => h !== g.s.robberHex);
  const [c0, , c2, , c4] = hexCorners(hex);
  g.s.buildings[c0] = { owner: 0, kind: 'settlement' };
  g.s.buildings[c2] = { owner: 1, kind: 'settlement' };
  g.s.buildings[c4] = { owner: 2, kind: 'settlement' };
  const far = farHex(hexCorners(hex));
  g.s.buildings[hexCorners(far)[0]] = { owner: 3, kind: 'settlement' };  // not adjacent: never robbable
  g.give(1, 'ore', 2); g.give(2, 'wheat', 2); g.give(3, 'sheep', 2);
  g.s.phase = { kind: 'moveRobber' };
  check(!g.act({ type: 'moveRobber', hex: g.s.robberHex }), 'robber must move to a different hex');
  check(g.act({ type: 'moveRobber', hex }) && g.s.phase.kind === 'steal', 'two victims → roller chooses');
  const cands = g.s.phase.kind === 'steal' ? g.s.phase.candidates : [];
  check(JSON.stringify([...cands].sort()) === '[1,2]', `candidates = ${JSON.stringify(cands)} (roller and far P3 excluded)`);
  check(!g.act({ type: 'steal', victim: 0 }), 'roller cannot rob themselves');
  check(!g.act({ type: 'steal', victim: 3 }), 'non-adjacent player cannot be robbed');
  check(g.act({ type: 'steal', victim: 2 }) && totalCards(g.s.players[2].hand) === 1 && totalCards(g.s.players[0].hand) === 1,
    'steal moves exactly 1 card');
});

scenario(11, 'Bank shortage', (check) => {
  const setup = (owners: [number, 'city' | 'settlement'][]) => {
    const g = new G(3);
    g.inPhase(0, 'roll');
    const fields = TOPOLOGY.hexCorners.findIndex((_, h) => g.tile(h).terrain === 'fields' && g.tile(h).number !== 12);
    const num = g.tile(fields).number!;
    g.s.board.hexes.forEach((t, i) => { if (i !== fields && t.number === num) t.number = 12; });
    g.s.robberHex = farHex(hexCorners(fields));
    owners.forEach(([p, kind], i) => (g.s.buildings[hexCorners(fields)[i * 3]] = { owner: p, kind }));
    g.s.bank.wheat = 2;
    g.forceRoll(num);
    return g;
  };
  const g = setup([[1, 'city'], [2, 'city']]);
  check(g.s.players[1].hand.wheat === 0 && g.s.players[2].hand.wheat === 0, 'two players owed → neither receives');
  check(g.s.bank.wheat === 2, 'bank unchanged');
  const h = setup([[1, 'city'], [1, 'settlement']]);
  check(h.s.players[1].hand.wheat === 2 && h.s.bank.wheat === 0, `single player owed 3 got ${h.s.players[1].hand.wheat}`);
});

scenario(12, 'Road cannot pass through opponent settlement', (check) => {
  const g = new G();
  g.inPhase(0, 'main');
  const [a, x, b] = findPath(2, new Set(), (p) => neighbors(p[1]).length === 3);
  g.s.buildings[a] = { owner: 0, kind: 'settlement' };
  g.setRoads([between(a, x)], 0);
  g.s.buildings[x] = { owner: 1, kind: 'settlement' };
  g.give(0, 'wood', 1); g.give(0, 'brick', 1);
  check(!g.act({ type: 'placeRoad', edge: between(x, b) }), 'extending through opponent settlement rejected');
  const third = neighbors(x).find((n) => n !== a && n !== b)!;
  check(!legalRoadEdges(g.s).includes(between(x, third)), 'other edge through that corner not offered either');
  const disconnected = TOPOLOGY.edgeCorners.findIndex((cs) => !cs.some((c) => [a, x, b].includes(c) || neighbors(c).some((n) => [a, x, b].includes(n))));
  check(!g.act({ type: 'placeRoad', edge: disconnected }), 'disconnected road rejected');
});

scenario(13, 'Phase enforcement', (check) => {
  const g = new G();
  g.inPhase(0, 'roll');
  (['wood', 'brick', 'wheat', 'sheep'] as Resource[]).forEach((r) => g.give(0, r, 5));
  g.s.buildings[0] = { owner: 0, kind: 'settlement' };
  check(!g.act({ type: 'placeRoad', edge: cornerEdges(0)[0] }), 'road before roll rejected');
  check(!g.act({ type: 'bankTrade', give: 'wood', get: 'ore' }), 'trade before roll rejected');
  check(!g.act({ type: 'placeCity', corner: 0 }), 'city before roll rejected');
  check(!g.act({ type: 'endTurn' }), 'end turn before roll rejected');
  g.act({ type: 'debugForceRoll', total: 4 });
  check(g.act({ type: 'roll' }) && !g.act({ type: 'roll' }), 'cannot roll twice');
  check(g.act({ type: 'placeRoad', edge: cornerEdges(0)[0] }), 'road after roll accepted');
  check(g.act({ type: 'endTurn' }) && g.s.currentPlayer === 1 && g.s.phase.kind === 'roll', 'end turn passes to next player');
});

const chain = findPath(6, new Set(), (p) => neighbors(p[3]).length === 3);
const chainEdges = pathEdges(chain);
const roadCost = (g: G, p: number) => { g.give(p, 'wood', 1); g.give(p, 'brick', 1); };
const settlementCost = (g: G, p: number) => (['wood', 'brick', 'wheat', 'sheep'] as Resource[]).forEach((r) => g.give(p, r, 1));
const awayFromChain = () => {
  const avoid = new Set<number>();
  chain.forEach((c) => { avoid.add(c); neighbors(c).forEach((n) => avoid.add(n)); });
  return avoid;
};

scenario(14, 'Longest Road threshold at 5', (check) => {
  const g = new G();
  g.inPhase(0, 'main');
  g.s.buildings[chain[0]] = { owner: 0, kind: 'settlement' };
  g.setRoads(chainEdges.slice(0, 4), 0);
  check(g.s.longestRoadHolder === null, `4 roads → holder ${g.s.longestRoadHolder}`);
  const vp = victoryPoints(g.s, 0);
  roadCost(g, 0);
  check(g.act({ type: 'placeRoad', edge: chainEdges[4] }), 'build 5th road');
  check(g.s.longestRoadHolder === 0 && victoryPoints(g.s, 0) === vp + 2, `holder ${g.s.longestRoadHolder}, VP ${vp} → ${victoryPoints(g.s, 0)}`);
});

scenario(15, 'Longest Road: tie does not take, exceeding does', (check) => {
  const g = new G();
  g.inPhase(0, 'main');
  g.setRoads(chainEdges.slice(0, 5), 0);
  check(g.s.longestRoadHolder === 0, 'P0 holds with 5');
  const p1Edges = pathEdges(findPath(6, awayFromChain()));
  g.setRoads(p1Edges.slice(0, 4), 1);
  g.s.currentPlayer = 1;
  roadCost(g, 1);
  check(g.act({ type: 'placeRoad', edge: p1Edges[4] }) && g.s.longestRoadHolder === 0, `P1 ties at 5 → holder ${g.s.longestRoadHolder}`);
  roadCost(g, 1);
  check(g.act({ type: 'placeRoad', edge: p1Edges[5] }) && g.s.longestRoadHolder === 1, `P1 reaches 6 → holder ${g.s.longestRoadHolder}`);
});

scenario(16, 'Y-shaped 3+3+1 network has length 6', (check) => {
  const g = new G();
  let found = false;
  for (let center = 0; center < CORNERS && !found; center++) {
    if (neighbors(center).length !== 3) continue;
    const [n1, n2, n3] = neighbors(center);
    const arm = (start: number, len: number, avoid: Set<number>) => {
      const dfs = (p: number[]): number[] | null => {
        if (p.length === len) return p;
        for (const n of neighbors(p[p.length - 1])) if (!avoid.has(n) && !p.includes(n)) { const r = dfs([...p, n]); if (r) return r; }
        return null;
      };
      return dfs([start]);
    };
    const a1 = arm(n1, 3, new Set([center, n2, n3]));
    if (!a1) continue;
    const a2 = arm(n2, 3, new Set([center, n3, ...a1]));
    if (!a2) continue;
    const edges = [...pathEdges([center, ...a1]), ...pathEdges([center, ...a2]), between(center, n3)];
    g.setRoads(edges, 0);
    check(edges.length === 7, '7 road segments placed');
    check(roadLength(g.s, 0) === 6, `measured length ${roadLength(g.s, 0)} (expect 6)`);
    found = true;
  }
  check(found, 'built a Y shape');
  const h = new G();
  h.setRoads(TOPOLOGY.hexCorners[9].map((c, i, cs) => between(c, cs[(i + 1) % 6])), 0);
  check(roadLength(h.s, 0) === 6, `hex ring length ${roadLength(h.s, 0)} (expect 6)`);
});

scenario(17, 'Opponent settlement breaks a 6-road chain', (check) => {
  const mid = chain[3];
  const spur = neighbors(mid).find((n) => !chain.includes(n))!;
  const g = new G(3);
  g.inPhase(1, 'main');
  g.setRoads(chainEdges, 0);
  check(g.s.longestRoadHolder === 0, 'P0 holds with 6');
  g.s.roads[between(mid, spur)] = 1;
  settlementCost(g, 1);
  check(g.act({ type: 'placeSettlement', corner: mid }), 'P1 builds settlement mid-chain');
  check(roadLength(g.s, 0) === 3, `P0 length now ${roadLength(g.s, 0)} (expect 3)`);
  check(g.s.longestRoadHolder === null, `card set aside (holder ${g.s.longestRoadHolder})`);

  const h = new G(3);
  h.inPhase(1, 'main');
  h.setRoads(chainEdges, 0);
  h.setRoads(pathEdges(findPath(5, awayFromChain())), 2);
  check(h.s.longestRoadHolder === 0, 'P0 still holds (6 > 5)');
  h.s.roads[between(mid, spur)] = 1;
  settlementCost(h, 1);
  h.act({ type: 'placeSettlement', corner: mid });
  check(h.s.longestRoadHolder === 2, `P2 uniquely longest takes card (holder ${h.s.longestRoadHolder})`);
});

scenario(18, 'Piece limits', (check) => {
  const g = new G();
  g.inPhase(0, 'main');
  g.s.players[0].pieces.settlement = 0;
  const [p0, p1] = findPath(1);
  g.s.roads[between(p0, p1)] = 0;
  settlementCost(g, 0);
  check(!g.act({ type: 'placeSettlement', corner: p0 }), 'no settlements left → rejected');
  const far = [...Array(CORNERS).keys()].find((c) => c !== p0 && c !== p1 && !neighbors(c).some((n) => n === p0 || n === p1))!;
  g.s.buildings[far] = { owner: 0, kind: 'settlement' };
  g.give(0, 'ore', 3); g.give(0, 'wheat', 2);
  check(g.act({ type: 'placeCity', corner: far }) && g.s.players[0].pieces.settlement === 1, 'city returns settlement to supply');
  check(g.act({ type: 'placeSettlement', corner: p0 }), 'can build settlement again');
  g.s.players[0].pieces.road = 0;
  roadCost(g, 0);
  check(!g.act({ type: 'placeRoad', edge: cornerEdges(p0).find((e) => g.s.roads[e] === null)! }), 'no roads left → rejected');
});

scenario(19, 'Bank trade 4:1', (check) => {
  const g = new G();
  g.inPhase(0, 'main');
  g.give(0, 'wood', 3);
  check(!g.act({ type: 'bankTrade', give: 'wood', get: 'ore' }), '3 wood rejected');
  g.give(0, 'wood', 1);
  check(g.act({ type: 'bankTrade', give: 'wood', get: 'ore' }), '4 wood accepted');
  const h = g.s.players[0].hand;
  check(h.wood === 0 && h.ore === 1, `hand after: wood ${h.wood}, ore ${h.ore}`);
  g.give(0, 'wood', 4);
  g.s.bank.ore = 0;
  check(!g.act({ type: 'bankTrade', give: 'wood', get: 'ore' }), 'bank out of ore → rejected');
});

scenario(20, 'Win at 10 VP on own turn', (check) => {
  const spots: number[] = [];
  for (let c = 0; c < CORNERS && spots.length < 6; c++) if (spots.every((s) => !neighbors(s).includes(c))) spots.push(c);
  const g = new G(2);
  g.inPhase(0, 'main');
  spots.slice(0, 4).forEach((c) => (g.s.buildings[c] = { owner: 0, kind: 'city' }));
  g.s.buildings[spots[4]] = { owner: 0, kind: 'settlement' };
  check(victoryPoints(g.s, 0) === 9, `VP ${victoryPoints(g.s, 0)}`);
  g.s.roads[cornerEdges(spots[5])[0]] = 0;
  settlementCost(g, 0);
  check(g.act({ type: 'placeSettlement', corner: spots[5] }), 'build 10th VP');
  const ph = g.s.phase;
  check(ph.kind === 'gameOver' && ph.winner === 0, `phase ${ph.kind}`);
  check(!g.act({ type: 'endTurn' }) && !g.act({ type: 'roll' }), 'no actions after game over');

  const h = new G(2);
  h.inPhase(1, 'main');
  spots.slice(0, 4).forEach((c) => (h.s.buildings[c] = { owner: 0, kind: 'city' }));
  h.s.buildings[spots[4]] = { owner: 0, kind: 'settlement' };
  h.s.buildings[spots[5]] = { owner: 0, kind: 'settlement' };
  check(h.s.phase.kind === 'main', 'P0 has 10 on P1 turn → no win yet');
  h.act({ type: 'endTurn' });
  const hp = h.s.phase;
  check(hp.kind === 'gameOver' && hp.winner === 0, `P0 wins when their turn starts (phase ${hp.kind})`);
});

// ------------------------------------------------------------------- report

let passed = 0;
for (const r of results.sort((a, b) => a.id - b.id)) {
  if (r.pass) passed++;
  console.log(`${r.pass ? 'PASS' : 'FAIL'}  #${r.id} ${r.name}`);
  for (const n of r.notes) if (process.argv.includes('-v') || n.startsWith('FAIL')) console.log(`        ${n}`);
}
console.log(`\n${passed}/${results.length} scenarios passed`);

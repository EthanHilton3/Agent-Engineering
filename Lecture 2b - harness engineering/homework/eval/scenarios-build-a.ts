/**
 * Independent acceptance check for build A (one-shot) against spec.md's 20 scenarios.
 * Written outside the build so it doesn't reuse the build's own test helpers.
 *
 * Run from build-a-oneshot/:  npx vite-node ../eval/scenarios-build-a.ts
 */
import { Game } from '../build-a-oneshot/src/game/game';
import { GEO, edgeBetween } from '../build-a-oneshot/src/game/geometry';
import { generateBoard } from '../build-a-oneshot/src/game/board';
import { RESOURCES, TERRAIN_RESOURCE, totalCards, type Resource } from '../build-a-oneshot/src/game/types';

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

function newGame(players = 3, seed = 'eval') {
  return new Game({ seed, playerNames: Array.from({ length: players }, (_, i) => `P${i}`) });
}

/** Skip setup and drop into `phase` for `player` on an empty board. */
function inPhase(g: Game, player: number, phase: 'roll' | 'main') {
  g.state.setupStep = g.state.setupOrder.length;
  g.state.setupSettlement = null;
  g.state.currentPlayer = player;
  g.state.phase = phase;
}

function give(g: Game, p: number, r: Resource, n: number) {
  g.state.players[p].resources[r] += n;
  g.state.bank[r] -= n;
}

function giveRoadCost(g: Game, p: number) {
  give(g, p, 'wood', 1);
  give(g, p, 'brick', 1);
}

/** Hexes are adjacent iff they share an edge (two corners). Independent of the build's neighbor lists. */
function hexesAdjacent(a: number, b: number) {
  const shared = GEO.hexes[a].corners.filter((c) => GEO.hexes[b].corners.includes(c));
  return shared.length === 2;
}

/** Find a simple corner path with `len` edges, avoiding `avoid` corners. */
function findPath(len: number, avoid = new Set<number>(), accept: (path: number[]) => boolean = () => true): number[] {
  const dfs = (path: number[]): number[] | null => {
    if (path.length === len + 1) return accept(path) ? path : null;
    const last = path[path.length - 1];
    for (const n of GEO.corners[last].neighbors) {
      if (path.includes(n) || avoid.has(n)) continue;
      const found = dfs([...path, n]);
      if (found) return found;
    }
    return null;
  };
  for (const c of GEO.corners) {
    if (avoid.has(c.id)) continue;
    const p = dfs([c.id]);
    if (p) return p;
  }
  throw new Error(`no path of length ${len}`);
}

function pathEdges(path: number[]) {
  return path.slice(1).map((c, i) => edgeBetween(path[i], c)!);
}

function setRoads(g: Game, edges: number[], owner: number) {
  for (const e of edges) g.state.roads[e] = owner;
  g.updateLongestRoad();
}

/** A hex not touching any of the given corners (to park the robber). */
function farHex(corners: number[]) {
  return GEO.hexes.find((h) => !h.corners.some((c) => corners.includes(c)))!.id;
}

/** Play out setup by always choosing the first legal spot. Returns who placed each settlement. */
function playSetup(g: Game, onSecond?: (p: number, corner: number, before: number) => void) {
  const order: number[] = [];
  let placed = 0;
  while (g.state.phase === 'setup-settlement') {
    const p = g.state.currentPlayer;
    order.push(p);
    const corner = g.legalSettlementCorners()[0];
    const before = totalCards(g.state.players[p].resources);
    const r = g.placeSettlement(corner);
    if (!r.ok) throw new Error(r.error);
    placed++;
    onSecond?.(p, corner, before);
    const road = g.legalRoadEdges()[0];
    const rr = g.placeRoad(road);
    if (!rr.ok) throw new Error(rr.error);
  }
  return order;
}

// ---------------------------------------------------------------- scenarios

scenario(1, 'Deterministic board', (check) => {
  const a = generateBoard('same-seed');
  const b = generateBoard('same-seed');
  check(JSON.stringify(a.tiles) === JSON.stringify(b.tiles), 'same seed → identical tiles');
  const c = generateBoard('other-seed');
  check(JSON.stringify(a.tiles) !== JSON.stringify(c.tiles), 'different seed → different tiles');
  check(GEO.hexes.length === 19 && GEO.corners.length === 54 && GEO.edges.length === 72,
    `topology 19 hexes / 54 corners / 72 edges (got ${GEO.hexes.length}/${GEO.corners.length}/${GEO.edges.length})`);
  const terr = a.tiles.map((t) => t.terrain).sort().join(',');
  check(terr === 'desert,fields,fields,fields,fields,forest,forest,forest,forest,hills,hills,hills,mountains,mountains,mountains,pasture,pasture,pasture,pasture',
    'terrain counts match spec');
  const nums = a.tiles.map((t) => t.number).filter((n) => n !== null).sort((x, y) => x! - y!).join(',');
  check(nums === '2,3,3,4,4,5,5,6,6,8,8,9,9,10,10,11,11,12', 'number tokens match spec');
  check(a.tiles[a.desertHex].number === null, 'desert has no number');
  const g = new Game({ seed: 'same-seed', playerNames: ['a', 'b'] });
  check(g.state.robberHex === g.state.board.desertHex, 'robber starts on desert');
});

scenario(2, 'No adjacent 6/8 across 1000 boards', (check) => {
  let bad = 0;
  for (let i = 0; i < 1000; i++) {
    const tiles = generateBoard(`seed-${i}`).tiles;
    const red = (n: number | null) => n === 6 || n === 8;
    for (let a = 0; a < 19; a++)
      for (let b = a + 1; b < 19; b++)
        if (red(tiles[a].number) && red(tiles[b].number) && hexesAdjacent(a, b)) bad++;
  }
  check(bad === 0, `adjacent red pairs found: ${bad} (checked with independent adjacency)`);
});

scenario(3, 'Distance rule in setup', (check) => {
  const g = newGame();
  const c = GEO.corners.find((x) => x.neighbors.length === 3)!.id;
  check(g.placeSettlement(c).ok, 'P0 places settlement');
  check(g.placeRoad(GEO.corners[c].edges[0]).ok, 'P0 places road');
  const legal = g.legalSettlementCorners();
  check(GEO.corners[c].neighbors.every((n) => !legal.includes(n)), 'neighbors not offered as legal');
  check(!legal.includes(c), 'occupied corner not offered');
  check(!g.placeSettlement(GEO.corners[c].neighbors[0]).ok, 'placing on a neighbor is rejected');
  const twoAway = GEO.corners[GEO.corners[c].neighbors[0]].neighbors.find((x) => x !== c && !GEO.corners[c].neighbors.includes(x))!;
  check(legal.includes(twoAway), 'corner two edges away is legal');
});

scenario(4, 'Only second setup settlement grants resources', (check) => {
  const g = newGame(3);
  let count = 0;
  playSetup(g, (p, corner, before) => {
    count++;
    const after = totalCards(g.state.players[p].resources);
    const expected = GEO.corners[corner].hexes.filter((h) => g.state.board.tiles[h].terrain !== 'desert').length;
    if (count <= 3) check(after === before, `first settlement P${p}: +${after - before} (expect 0)`);
    else check(after - before === expected, `second settlement P${p}: +${after - before} (expect ${expected})`);
  });
  const bankTotal = totalCards(g.state.bank) + g.state.players.reduce((s, p) => s + totalCards(p.resources), 0);
  check(bankTotal === 95, `card conservation: bank + hands = ${bankTotal} (expect 95)`);
});

scenario(5, 'Snake order 1,2,3,3,2,1', (check) => {
  const g = newGame(3);
  const order = playSetup(g);
  check(order.join(',') === '0,1,2,2,1,0', `order was ${order.join(',')}`);
  check(g.state.phase === 'roll' && g.state.currentPlayer === 0, 'player 1 takes first normal turn');
  const g4 = newGame(4);
  check(playSetup(g4).join(',') === '0,1,2,3,3,2,1,0', '4-player order correct');
});

scenario(6, 'Shared-corner production from all 3 hexes', (check) => {
  const g = newGame();
  inPhase(g, 0, 'roll');
  const corner = GEO.corners.find((c) => c.hexes.length === 3 && c.hexes.every((h) => g.state.board.tiles[h].terrain !== 'desert'))!;
  g.state.buildings[corner.id] = { owner: 0, kind: 'settlement' };
  // Give the three hexes unique numbers that nothing else uses for this test.
  const nums = [3, 4, 5];
  g.state.board.tiles.forEach((t) => { if (t.number !== null && nums.includes(t.number)) t.number = 12; });
  corner.hexes.forEach((h, i) => (g.state.board.tiles[h].number = nums[i]));
  g.state.robberHex = farHex([corner.id]);
  corner.hexes.forEach((h, i) => {
    const r = TERRAIN_RESOURCE[g.state.board.tiles[h].terrain]!;
    const before = g.state.players[0].resources[r];
    g.state.phase = 'roll';
    g.debugForceRoll(nums[i]);
    g.roll();
    check(g.state.players[0].resources[r] === before + 1, `roll ${nums[i]} → +1 ${r}`);
  });
});

scenario(7, 'City produces 2', (check) => {
  const g = newGame();
  inPhase(g, 0, 'roll');
  const hex = GEO.hexes.find((h) => g.state.board.tiles[h.id].number !== null && h.id !== g.state.robberHex)!;
  const tile = g.state.board.tiles[hex.id];
  const r = TERRAIN_RESOURCE[tile.terrain]!;
  g.state.buildings[hex.corners[0]] = { owner: 0, kind: 'city' };
  g.debugForceRoll(tile.number!);
  g.roll();
  // Other hexes with the same number may touch the same corner, so count expected precisely.
  const expected = GEO.corners[hex.corners[0]].hexes
    .filter((h) => g.state.board.tiles[h].number === tile.number && TERRAIN_RESOURCE[g.state.board.tiles[h].terrain] === r && h !== g.state.robberHex).length * 2;
  check(g.state.players[0].resources[r] === expected, `city got ${g.state.players[0].resources[r]} ${r} (expect ${expected})`);
});

scenario(8, 'Robber blocks production', (check) => {
  const g = newGame();
  inPhase(g, 0, 'roll');
  const hex = GEO.hexes.find((h) => g.state.board.tiles[h.id].number !== null)!;
  const num = g.state.board.tiles[hex.id].number!;
  // Use a corner that only touches this hex's number, so nothing else could pay out.
  const corner = hex.corners.find((c) => GEO.corners[c].hexes.every((h) => h === hex.id || g.state.board.tiles[h].number !== num))!;
  g.state.buildings[corner] = { owner: 0, kind: 'settlement' };
  g.state.robberHex = hex.id;
  g.debugForceRoll(num);
  g.roll();
  check(totalCards(g.state.players[0].resources) === 0, `blocked hex produced ${totalCards(g.state.players[0].resources)} cards`);
});

scenario(9, 'Discard on 7: 9 cards → 4, 7 cards → 0', (check) => {
  const g = newGame(3);
  inPhase(g, 0, 'roll');
  give(g, 1, 'wood', 5); give(g, 1, 'ore', 4);   // 9
  give(g, 2, 'sheep', 7);                         // 7
  g.debugForceRoll(7);
  g.roll();
  check(g.state.phase === 'discard', `phase is ${g.state.phase}`);
  const pend = g.state.pendingDiscards;
  check(pend.length === 1 && pend[0].player === 1 && pend[0].amount === 4, `pending: ${JSON.stringify(pend)}`);
  check(!g.discard(1, { wood: 3 }).ok, 'discarding 3 instead of 4 is rejected');
  check(!g.discard(2, { sheep: 3 }).ok, 'P2 (7 cards) cannot be made to discard');
  check(g.discard(1, { wood: 2, ore: 2 }).ok, 'P1 discards 4 of their choice');
  check(totalCards(g.state.players[1].resources) === 5 && g.state.phase === 'move-robber', 'P1 left with 5, move to robber');
  check(!g.placeRoad(0).ok && !g.endTurn().ok, 'cannot build or end turn before robber is resolved');
});

scenario(10, 'Steal targeting', (check) => {
  const g = newGame(3);
  inPhase(g, 0, 'main');
  const hex = GEO.hexes.find((h) => h.id !== g.state.robberHex)!;
  const [c0, , c2, , c4] = hex.corners;
  g.state.buildings[c0] = { owner: 0, kind: 'settlement' };
  g.state.buildings[c2] = { owner: 1, kind: 'settlement' };
  g.state.buildings[c4] = { owner: 2, kind: 'settlement' };
  give(g, 1, 'ore', 2); give(g, 2, 'wheat', 2);
  check(JSON.stringify(g.robbableAt(hex.id)) === '[1,2]', `robbable = ${JSON.stringify(g.robbableAt(hex.id))} (roller excluded)`);
  g.state.phase = 'move-robber';
  check(!g.moveRobber(g.state.robberHex).ok, 'robber must move to a different hex');
  check(g.moveRobber(hex.id).ok && g.state.phase === 'steal', 'two victims → roller chooses');
  check(!g.steal(0).ok, 'roller cannot rob themselves');
  check(g.steal(2).ok && totalCards(g.state.players[2].resources) === 1 && totalCards(g.state.players[0].resources) === 1, 'steal moves exactly 1 card');
  // Opponent not touching the hex is not robbable.
  const other = GEO.hexes.find((h) => !h.corners.some((c) => [c0, c2, c4].includes(c)) && h.id !== hex.id)!;
  check(g.robbableAt(other.id).length === 0, 'nobody robbable on an empty hex');
});

scenario(11, 'Bank shortage', (check) => {
  // Two players owed 2 wheat each, bank has 2 → nobody gets wheat.
  const g = newGame(3);
  inPhase(g, 0, 'roll');
  const fields = GEO.hexes.find((h) => g.state.board.tiles[h.id].terrain === 'fields')!;
  const num = g.state.board.tiles[fields.id].number!;
  g.state.board.tiles.forEach((t, i) => { if (i !== fields.id && t.number === num) t.number = 12; });
  if (num === 12) throw new Error('pick another seed');
  g.state.robberHex = farHex(fields.corners);
  g.state.buildings[fields.corners[0]] = { owner: 1, kind: 'city' };
  g.state.buildings[fields.corners[3]] = { owner: 2, kind: 'city' };
  g.state.bank.wheat = 2;
  g.debugForceRoll(num);
  g.roll();
  check(g.state.players[1].resources.wheat === 0 && g.state.players[2].resources.wheat === 0, 'two players owed → neither receives');
  check(g.state.bank.wheat === 2, 'bank unchanged');

  // One player owed 3, bank has 2 → receives 2.
  const h = newGame(3);
  inPhase(h, 0, 'roll');
  const f2 = GEO.hexes.find((x) => h.state.board.tiles[x.id].terrain === 'fields')!;
  const n2 = h.state.board.tiles[f2.id].number!;
  h.state.board.tiles.forEach((t, i) => { if (i !== f2.id && t.number === n2) t.number = 12; });
  h.state.robberHex = farHex(f2.corners);
  h.state.buildings[f2.corners[0]] = { owner: 1, kind: 'city' };
  h.state.buildings[f2.corners[3]] = { owner: 1, kind: 'settlement' };
  h.state.bank.wheat = 2;
  h.debugForceRoll(n2);
  h.roll();
  check(h.state.players[1].resources.wheat === 2 && h.state.bank.wheat === 0, `single player owed 3 got ${h.state.players[1].resources.wheat}`);
});

scenario(12, 'Road cannot pass through opponent settlement', (check) => {
  const g = newGame();
  inPhase(g, 0, 'main');
  const path = findPath(2, new Set(), (p) => GEO.corners[p[1]].neighbors.length === 3);
  const [a, x, b] = path;
  g.state.buildings[a] = { owner: 0, kind: 'settlement' };
  setRoads(g, [edgeBetween(a, x)!], 0);
  g.state.buildings[x] = { owner: 1, kind: 'settlement' };
  giveRoadCost(g, 0);
  check(!g.placeRoad(edgeBetween(x, b)!).ok, 'extending through opponent settlement rejected');
  const third = GEO.corners[x].neighbors.find((n) => n !== a && n !== b)!;
  check(!g.legalRoadEdges().includes(edgeBetween(x, third)!), 'other edge through that corner not offered either');
  check(!g.placeRoad(GEO.edges.find((e) => !e.corners.some((c) => [a, x, b].includes(c) || GEO.corners[c].neighbors.some((n) => [a, x, b].includes(n))))!.id).ok,
    'disconnected road rejected');
});

scenario(13, 'Phase enforcement', (check) => {
  const g = newGame();
  inPhase(g, 0, 'roll');
  give(g, 0, 'wood', 5); give(g, 0, 'brick', 5); give(g, 0, 'wheat', 5); give(g, 0, 'sheep', 5);
  g.state.buildings[0] = { owner: 0, kind: 'settlement' };
  check(!g.placeRoad(GEO.corners[0].edges[0]).ok, 'road before roll rejected');
  check(!g.bankTrade('wood', 'ore').ok, 'trade before roll rejected');
  check(!g.placeCity(0).ok, 'city before roll rejected');
  check(!g.endTurn().ok, 'end turn before roll rejected');
  g.debugForceRoll(4);
  check(g.roll().ok && !g.roll().ok, 'cannot roll twice');
  check(g.placeRoad(GEO.corners[0].edges[0]).ok, 'road after roll accepted');
  check(g.endTurn().ok && g.state.currentPlayer === 1 && g.state.phase === 'roll', 'end turn passes to next player');
});

// Longest-road scenarios share a 6-edge chain whose middle corner has a third edge.
const chain = findPath(6, new Set(), (p) => GEO.corners[p[3]].neighbors.length === 3);
const chainEdges = pathEdges(chain);

scenario(14, 'Longest Road threshold at 5', (check) => {
  const g = newGame();
  inPhase(g, 0, 'main');
  g.state.buildings[chain[0]] = { owner: 0, kind: 'settlement' };
  setRoads(g, chainEdges.slice(0, 4), 0);
  check(g.state.longestRoadHolder === null, `4 roads → holder ${g.state.longestRoadHolder}`);
  const vp = g.victoryPoints(0);
  giveRoadCost(g, 0);
  check(g.placeRoad(chainEdges[4]).ok, 'build 5th road');
  check(g.state.longestRoadHolder === 0 && g.victoryPoints(0) === vp + 2, `holder ${g.state.longestRoadHolder}, VP ${vp} → ${g.victoryPoints(0)}`);
});

scenario(15, 'Longest Road: tie does not take, exceeding does', (check) => {
  const g = newGame();
  inPhase(g, 0, 'main');
  setRoads(g, chainEdges.slice(0, 5), 0);
  check(g.state.longestRoadHolder === 0, 'P0 holds with 5');
  const avoid = new Set<number>();
  chain.forEach((c) => { avoid.add(c); GEO.corners[c].neighbors.forEach((n) => avoid.add(n)); });
  const p1 = findPath(6, avoid);
  const p1Edges = pathEdges(p1);
  setRoads(g, p1Edges.slice(0, 4), 1);
  g.state.currentPlayer = 1;
  giveRoadCost(g, 1);
  check(g.placeRoad(p1Edges[4]).ok && g.state.longestRoadHolder === 0, `P1 ties at 5 → holder ${g.state.longestRoadHolder}`);
  giveRoadCost(g, 1);
  check(g.placeRoad(p1Edges[5]).ok && g.state.longestRoadHolder === 1, `P1 reaches 6 → holder ${g.state.longestRoadHolder}`);
});

scenario(16, 'Y-shaped 3+3+1 network has length 6', (check) => {
  const g = newGame();
  // Find center with 3 neighbors and three disjoint arms of length 3, 3, 1.
  let found = false;
  for (const center of GEO.corners.filter((c) => c.neighbors.length === 3)) {
    const [n1, n2, n3] = center.neighbors;
    const arm = (start: number, len: number, avoid: Set<number>) => {
      const dfs = (p: number[]): number[] | null => {
        if (p.length === len) return p;
        for (const n of GEO.corners[p[p.length - 1]].neighbors) if (!avoid.has(n) && !p.includes(n)) { const r = dfs([...p, n]); if (r) return r; }
        return null;
      };
      return dfs([start]);
    };
    const a1 = arm(n1, 3, new Set([center.id, n2, n3]));
    if (!a1) continue;
    const a2 = arm(n2, 3, new Set([center.id, n3, ...a1]));
    if (!a2) continue;
    const edges = [...pathEdges([center.id, ...a1]), ...pathEdges([center.id, ...a2]), edgeBetween(center.id, n3)!];
    setRoads(g, edges, 0);
    check(edges.length === 7, '7 road segments placed');
    check(g.state.roadLengths[0] === 6, `measured length ${g.state.roadLengths[0]} (expect 6)`);
    found = true;
    break;
  }
  check(found, 'built a Y shape');
  // A closed loop (one hex ring = 6 roads) should count 6.
  const h = newGame();
  setRoads(h, GEO.hexes[9].edges, 0);
  check(h.state.roadLengths[0] === 6, `hex ring length ${h.state.roadLengths[0]} (expect 6)`);
});

scenario(17, 'Opponent settlement breaks a 6-road chain', (check) => {
  const g = newGame(3);
  inPhase(g, 1, 'main');
  setRoads(g, chainEdges, 0);
  check(g.state.longestRoadHolder === 0, 'P0 holds with 6');
  const mid = chain[3];
  const spur = GEO.corners[mid].neighbors.find((n) => !chain.includes(n))!;
  g.state.roads[edgeBetween(mid, spur)!] = 1;
  ['wood', 'brick', 'wheat', 'sheep'].forEach((r) => give(g, 1, r as Resource, 1));
  check(g.placeSettlement(mid).ok, 'P1 builds settlement mid-chain');
  check(g.state.roadLengths[0] === 3, `P0 length now ${g.state.roadLengths[0]} (expect 3)`);
  check(g.state.longestRoadHolder === null, `card set aside (holder ${g.state.longestRoadHolder})`);

  // Variant: a third player with 5 roads takes the card when the holder is broken.
  const h = newGame(3);
  inPhase(h, 1, 'main');
  setRoads(h, chainEdges, 0);
  const avoid = new Set<number>();
  chain.forEach((c) => { avoid.add(c); GEO.corners[c].neighbors.forEach((n) => avoid.add(n)); });
  setRoads(h, pathEdges(findPath(5, avoid)), 2);
  check(h.state.longestRoadHolder === 0, 'P0 still holds (6 > 5)');
  h.state.roads[edgeBetween(mid, spur)!] = 1;
  ['wood', 'brick', 'wheat', 'sheep'].forEach((r) => give(h, 1, r as Resource, 1));
  h.placeSettlement(mid);
  check(h.state.longestRoadHolder === 2, `P2 uniquely longest takes card (holder ${h.state.longestRoadHolder})`);
});

scenario(18, 'Piece limits', (check) => {
  const g = newGame();
  inPhase(g, 0, 'main');
  g.state.players[0].settlementsLeft = 0;
  const path = findPath(1);
  g.state.roads[edgeBetween(path[0], path[1])!] = 0;
  ['wood', 'brick', 'wheat', 'sheep'].forEach((r) => give(g, 0, r as Resource, 1));
  check(!g.placeSettlement(path[0]).ok, 'no settlements left → rejected');
  const far = GEO.corners.find((c) => !path.includes(c.id) && !c.neighbors.some((n) => path.includes(n)))!.id;
  g.state.buildings[far] = { owner: 0, kind: 'settlement' };
  give(g, 0, 'ore', 3); give(g, 0, 'wheat', 2);
  check(g.placeCity(far).ok && g.state.players[0].settlementsLeft === 1, 'city returns settlement to supply');
  check(g.placeSettlement(path[0]).ok, 'can build settlement again');
  g.state.players[0].roadsLeft = 0;
  giveRoadCost(g, 0);
  check(!g.placeRoad(GEO.corners[path[0]].edges.find((e) => g.state.roads[e] === null)!).ok, 'no roads left → rejected');
});

scenario(19, 'Bank trade 4:1', (check) => {
  const g = newGame();
  inPhase(g, 0, 'main');
  give(g, 0, 'wood', 3);
  check(!g.bankTrade('wood', 'ore').ok, '3 wood rejected');
  give(g, 0, 'wood', 1);
  check(g.bankTrade('wood', 'ore').ok, '4 wood accepted');
  const r = g.state.players[0].resources;
  check(r.wood === 0 && r.ore === 1, `hand after: wood ${r.wood}, ore ${r.ore}`);
  give(g, 0, 'wood', 4);
  g.state.bank.ore = 0;
  check(!g.bankTrade('wood', 'ore').ok, 'bank out of ore → rejected');
});

scenario(20, 'Win at 10 VP on own turn', (check) => {
  const g = newGame();
  inPhase(g, 0, 'main');
  // 4 cities (8) + 1 settlement (1) = 9 VP, spread out.
  const spots: number[] = [];
  for (const c of GEO.corners) if (spots.length < 6 && spots.every((s) => s !== c.id && !GEO.corners[s].neighbors.includes(c.id))) spots.push(c.id);
  spots.slice(0, 4).forEach((c) => (g.state.buildings[c] = { owner: 0, kind: 'city' }));
  g.state.buildings[spots[4]] = { owner: 0, kind: 'settlement' };
  check(g.victoryPoints(0) === 9, `VP ${g.victoryPoints(0)}`);
  g.state.roads[GEO.corners[spots[5]].edges[0]] = 0;
  ['wood', 'brick', 'wheat', 'sheep'].forEach((r) => give(g, 0, r as Resource, 1));
  check(g.placeSettlement(spots[5]).ok, 'build 10th VP');
  check(g.state.phase === 'game-over' && g.state.winner === 0, `phase ${g.state.phase}, winner ${g.state.winner}`);
  check(!g.endTurn().ok && !g.roll().ok, 'no actions after game over');

  // Reaching 10 on someone else's turn: not a win until your own turn.
  const h = newGame(2);
  inPhase(h, 1, 'main');
  spots.slice(0, 4).forEach((c) => (h.state.buildings[c] = { owner: 0, kind: 'city' }));
  h.state.buildings[spots[4]] = { owner: 0, kind: 'settlement' };
  h.state.buildings[spots[5]] = { owner: 0, kind: 'settlement' };
  check(h.state.phase === 'main' && h.state.winner === null, 'P0 has 10 on P1 turn → no win yet');
  h.endTurn();
  check(h.state.winner === 0, `P0 wins when their turn starts (winner ${h.state.winner})`);
});

// ------------------------------------------------------------------- report

let passed = 0;
for (const r of results.sort((a, b) => a.id - b.id)) {
  if (r.pass) passed++;
  console.log(`${r.pass ? 'PASS' : 'FAIL'}  #${r.id} ${r.name}`);
  for (const n of r.notes) if (process.argv.includes('-v') || n.startsWith('FAIL')) console.log(`        ${n}`);
}
console.log(`\n${passed}/${results.length} scenarios passed`);

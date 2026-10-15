import { generateBoard } from './board';
import { GEO } from './geometry';
import { longestRoadLength, resolveLongestRoad } from './longestRoad';
import { Rng, hashSeed } from './rng';
import {
  BANK_PER_RESOURCE,
  COSTS,
  LONGEST_ROAD_MIN,
  OK,
  PIECE_LIMITS,
  RESOURCES,
  TERRAIN_RESOURCE,
  WINNING_VP,
  emptyResources,
  fail,
  totalCards,
  type BuildKind,
  type GameState,
  type Phase,
  type Resource,
  type ResourceMap,
  type Result,
} from './types';

export const PLAYER_COLORS = ['#d64545', '#3b6fd6', '#e8902a', '#8e4bc4'];

export interface GameOptions {
  seed: string;
  playerNames: string[];
}

export function formatCost(cost: Partial<ResourceMap>): string {
  return RESOURCES.filter((r) => cost[r])
    .map((r) => `${cost[r]} ${r}`)
    .join(', ');
}

export const PHASE_LABELS: Record<Phase, string> = {
  'setup-settlement': 'Setup: place a settlement',
  'setup-road': 'Setup: place a road',
  roll: 'Roll the dice',
  discard: 'Discard cards (rolled 7)',
  'move-robber': 'Move the robber',
  steal: 'Choose a player to rob',
  main: 'Trade and build',
  'game-over': 'Game over',
};

/**
 * The full Catan Lite rules engine. Every action validates the current phase
 * and its own preconditions and returns a Result; failed actions never change
 * state, and the error string is meant to be shown to the player.
 */
export class Game {
  state: GameState;

  constructor(opts: GameOptions) {
    const n = opts.playerNames.length;
    if (n < 2 || n > 4) throw new Error('Catan Lite needs 2–4 players');
    const board = generateBoard(opts.seed);
    const order = [...Array(n).keys()];
    this.state = {
      board,
      players: opts.playerNames.map((name, id) => ({
        id,
        name,
        color: PLAYER_COLORS[id],
        resources: emptyResources(),
        roadsLeft: PIECE_LIMITS.roads,
        settlementsLeft: PIECE_LIMITS.settlements,
        citiesLeft: PIECE_LIMITS.cities,
      })),
      bank: Object.fromEntries(RESOURCES.map((r) => [r, BANK_PER_RESOURCE])) as ResourceMap,
      buildings: GEO.corners.map(() => null),
      roads: GEO.edges.map(() => null),
      robberHex: board.desertHex,
      phase: 'setup-settlement',
      currentPlayer: 0,
      setupStep: 0,
      setupOrder: [...order, ...order.slice().reverse()],
      setupSettlement: null,
      dice: null,
      pendingDiscards: [],
      stealCandidates: [],
      longestRoadHolder: null,
      roadLengths: order.map(() => 0),
      winner: null,
      forcedRoll: null,
      rngState: hashSeed(`play:${opts.seed}`),
      log: [],
    };
    this.log(`New game, seed "${opts.seed}". ${this.name(0)} starts setup.`);
  }

  // ---------------------------------------------------------------- queries

  get current() {
    return this.state.players[this.state.currentPlayer];
  }

  get isSetup(): boolean {
    return this.state.phase === 'setup-settlement' || this.state.phase === 'setup-road';
  }

  name(p: number): string {
    return this.state.players[p].name;
  }

  victoryPoints(p: number): number {
    let vp = 0;
    for (const b of this.state.buildings) {
      if (b?.owner === p) vp += b.kind === 'city' ? 2 : 1;
    }
    if (this.state.longestRoadHolder === p) vp += 2;
    return vp;
  }

  canAfford(p: number, kind: BuildKind): boolean {
    const res = this.state.players[p].resources;
    const cost: Partial<ResourceMap> = COSTS[kind];
    return RESOURCES.every((r) => res[r] >= (cost[r] ?? 0));
  }

  /** Why `p` may not put a settlement on `corner`, ignoring phase and cost. */
  settlementSpotError(p: number, corner: number): string | null {
    const s = this.state;
    if (s.buildings[corner]) return 'That corner is already occupied.';
    if (GEO.corners[corner].neighbors.some((c) => s.buildings[c])) {
      return 'Too close to another settlement or city (distance rule).';
    }
    if (!this.isSetup && !GEO.corners[corner].edges.some((e) => s.roads[e] === p)) {
      return 'A settlement must touch one of your roads.';
    }
    return null;
  }

  /** Why `p` may not put a road on `edge`, ignoring phase and cost. */
  roadSpotError(p: number, edge: number): string | null {
    const s = this.state;
    if (s.roads[edge] !== null) return 'That edge already has a road.';
    const ends = GEO.edges[edge].corners;
    if (this.isSetup) {
      return s.setupSettlement !== null && ends.includes(s.setupSettlement)
        ? null
        : 'Your setup road must touch the settlement you just placed.';
    }
    const connected = ends.some((c) => {
      const b = s.buildings[c];
      if (b) return b.owner === p;
      return GEO.corners[c].edges.some((e) => e !== edge && s.roads[e] === p);
    });
    return connected
      ? null
      : "A road must connect to your own road, settlement or city (and can't pass through an opponent's building).";
  }

  citySpotError(p: number, corner: number): string | null {
    const b = this.state.buildings[corner];
    return b && b.owner === p && b.kind === 'settlement'
      ? null
      : 'A city must replace one of your own settlements.';
  }

  legalSettlementCorners(p = this.state.currentPlayer): number[] {
    return GEO.corners.map((c) => c.id).filter((c) => this.settlementSpotError(p, c) === null);
  }

  legalRoadEdges(p = this.state.currentPlayer): number[] {
    return GEO.edges.map((e) => e.id).filter((e) => this.roadSpotError(p, e) === null);
  }

  legalCityCorners(p = this.state.currentPlayer): number[] {
    return GEO.corners.map((c) => c.id).filter((c) => this.citySpotError(p, c) === null);
  }

  /** Why the current player can't start building `kind` right now, or null. */
  buildError(kind: BuildKind): string | null {
    const s = this.state;
    const p = this.current;
    if (s.phase === 'game-over') return 'The game is over.';
    if (this.isSetup) {
      const want = s.phase === 'setup-settlement' ? 'settlement' : 'road';
      return kind === want ? null : `During setup you must place a ${want} now.`;
    }
    if (s.phase === 'roll') return 'Roll the dice first.';
    if (s.phase !== 'main') return `Finish the current step first: ${PHASE_LABELS[s.phase]}.`;
    const left = { road: p.roadsLeft, settlement: p.settlementsLeft, city: p.citiesLeft }[kind];
    if (left === 0) {
      return kind === 'settlement'
        ? 'You have no settlements left — upgrade one to a city to get it back.'
        : `You have no ${kind === 'city' ? 'cities' : 'roads'} left.`;
    }
    if (!this.canAfford(s.currentPlayer, kind)) {
      return `Not enough resources: a ${kind} costs ${formatCost(COSTS[kind])}.`;
    }
    return null;
  }

  tradeError(give: Resource, get: Resource): string | null {
    const s = this.state;
    if (s.phase === 'game-over') return 'The game is over.';
    if (s.phase === 'roll') return 'Roll the dice first.';
    if (s.phase !== 'main') return `You can't trade right now (${PHASE_LABELS[s.phase]}).`;
    if (give === get) return 'Pick two different resources.';
    if (this.current.resources[give] < 4) return `You need 4 ${give} to trade with the bank.`;
    if (s.bank[get] < 1) return `The bank has no ${get} left.`;
    return null;
  }

  // ---------------------------------------------------------------- actions

  placeSettlement(corner: number): Result {
    const err = this.buildError('settlement') ?? this.settlementSpotError(this.state.currentPlayer, corner);
    if (err) return fail(err);
    const s = this.state;
    const p = s.currentPlayer;
    const player = this.current;

    if (!this.isSetup) this.pay(p, COSTS.settlement);
    s.buildings[corner] = { owner: p, kind: 'settlement' };
    player.settlementsLeft--;
    this.log(`${player.name} built a settlement (corner ${corner}).`);

    if (this.isSetup) {
      if (s.setupStep >= s.players.length) this.grantSetupResources(p, corner);
      s.setupSettlement = corner;
      s.phase = 'setup-road';
    }
    this.updateLongestRoad();
    this.checkWin();
    return OK;
  }

  placeRoad(edge: number): Result {
    const err = this.buildError('road') ?? this.roadSpotError(this.state.currentPlayer, edge);
    if (err) return fail(err);
    const s = this.state;
    const player = this.current;

    if (!this.isSetup) this.pay(s.currentPlayer, COSTS.road);
    s.roads[edge] = s.currentPlayer;
    player.roadsLeft--;
    this.log(`${player.name} built a road (edge ${edge}).`);
    this.updateLongestRoad();

    if (this.isSetup) this.advanceSetup();
    else this.checkWin();
    return OK;
  }

  placeCity(corner: number): Result {
    const err = this.buildError('city') ?? this.citySpotError(this.state.currentPlayer, corner);
    if (err) return fail(err);
    const player = this.current;
    this.pay(player.id, COSTS.city);
    this.state.buildings[corner] = { owner: player.id, kind: 'city' };
    player.citiesLeft--;
    player.settlementsLeft++;
    this.log(`${player.name} upgraded to a city (corner ${corner}).`);
    this.checkWin();
    return OK;
  }

  roll(): Result {
    const s = this.state;
    if (s.phase === 'game-over') return fail('The game is over.');
    if (s.phase !== 'roll') {
      return fail(this.isSetup ? 'Finish setup first.' : 'You have already rolled this turn.');
    }
    let d1: number;
    let d2: number;
    if (s.forcedRoll !== null) {
      d1 = Math.max(1, s.forcedRoll - 6);
      d2 = s.forcedRoll - d1;
      s.forcedRoll = null;
    } else {
      const rng = new Rng(s.rngState);
      d1 = rng.int(6) + 1;
      d2 = rng.int(6) + 1;
      s.rngState = rng.state;
    }
    s.dice = [d1, d2];
    const total = d1 + d2;
    this.log(`${this.current.name} rolled ${total} (${d1} + ${d2}).`);

    if (total === 7) {
      s.pendingDiscards = s.players
        .filter((pl) => totalCards(pl.resources) > 7)
        .map((pl) => ({ player: pl.id, amount: Math.floor(totalCards(pl.resources) / 2) }));
      s.phase = s.pendingDiscards.length > 0 ? 'discard' : 'move-robber';
    } else {
      this.produce(total);
      s.phase = 'main';
    }
    return OK;
  }

  /** The player who must discard next and how many cards, if any. */
  get pendingDiscard() {
    return this.state.phase === 'discard' ? this.state.pendingDiscards[0] : undefined;
  }

  discard(player: number, cards: Partial<ResourceMap>): Result {
    const s = this.state;
    const pending = this.pendingDiscard;
    if (!pending) return fail('Nobody needs to discard right now.');
    if (pending.player !== player) return fail(`It is ${this.name(pending.player)}'s turn to discard.`);
    const res = s.players[player].resources;
    let count = 0;
    for (const r of RESOURCES) {
      const n = cards[r] ?? 0;
      if (n < 0 || !Number.isInteger(n)) return fail('Invalid discard.');
      if (n > res[r]) return fail(`You only have ${res[r]} ${r}.`);
      count += n;
    }
    if (count !== pending.amount) {
      return fail(`You must discard exactly ${pending.amount} cards (selected ${count}).`);
    }
    for (const r of RESOURCES) {
      const n = cards[r] ?? 0;
      res[r] -= n;
      s.bank[r] += n;
    }
    this.log(`${this.name(player)} discarded ${formatCost(cards)}.`);
    s.pendingDiscards.shift();
    if (s.pendingDiscards.length === 0) s.phase = 'move-robber';
    return OK;
  }

  /** Opponents with a building on `hex` (the ones the roller could rob there). */
  robbableAt(hex: number): number[] {
    const owners = new Set<number>();
    for (const c of GEO.hexes[hex].corners) {
      const b = this.state.buildings[c];
      if (b && b.owner !== this.state.currentPlayer) owners.add(b.owner);
    }
    return [...owners].sort();
  }

  moveRobber(hex: number): Result {
    const s = this.state;
    if (s.phase !== 'move-robber') return fail("You can't move the robber now.");
    if (!(hex >= 0 && hex < GEO.hexes.length)) return fail('No such hex.');
    if (hex === s.robberHex) return fail('The robber must move to a different hex.');
    s.robberHex = hex;
    const tile = s.board.tiles[hex];
    this.log(`${this.current.name} moved the robber to hex ${hex} (${tile.terrain}${tile.number ? ' ' + tile.number : ''}).`);

    const candidates = this.robbableAt(hex);
    if (candidates.length === 0) {
      this.log('No one to rob there.');
      s.phase = 'main';
    } else if (candidates.length === 1) {
      this.doSteal(candidates[0]);
      s.phase = 'main';
    } else {
      s.stealCandidates = candidates;
      s.phase = 'steal';
    }
    return OK;
  }

  steal(victim: number): Result {
    const s = this.state;
    if (s.phase !== 'steal') return fail("You can't steal right now.");
    if (!s.stealCandidates.includes(victim)) {
      return fail(`${this.name(victim)} has no building on the robber's hex.`);
    }
    this.doSteal(victim);
    s.stealCandidates = [];
    s.phase = 'main';
    return OK;
  }

  bankTrade(give: Resource, get: Resource): Result {
    const err = this.tradeError(give, get);
    if (err) return fail(err);
    const s = this.state;
    const res = this.current.resources;
    res[give] -= 4;
    s.bank[give] += 4;
    res[get] += 1;
    s.bank[get] -= 1;
    this.log(`${this.current.name} traded 4 ${give} for 1 ${get} with the bank.`);
    return OK;
  }

  endTurn(): Result {
    const s = this.state;
    if (s.phase === 'game-over') return fail('The game is over.');
    if (s.phase === 'roll') return fail('Roll the dice first.');
    if (s.phase !== 'main') return fail(`Finish the current step first: ${PHASE_LABELS[s.phase]}.`);
    s.currentPlayer = (s.currentPlayer + 1) % s.players.length;
    s.phase = 'roll';
    s.dice = null;
    this.log(`— ${this.current.name}'s turn.`);
    this.checkWin();
    return OK;
  }

  // ------------------------------------------------------------------ debug

  debugForceRoll(total: number | null): Result {
    if (total !== null && !(Number.isInteger(total) && total >= 2 && total <= 12)) {
      return fail('Forced roll must be between 2 and 12.');
    }
    this.state.forcedRoll = total;
    return OK;
  }

  /** Move cards from the bank to a player (limited by what the bank holds). */
  debugGive(player: number, resource: Resource, amount = 1): Result {
    const s = this.state;
    if (amount < 1) return fail('Amount must be positive.');
    if (s.bank[resource] < amount) return fail(`The bank only has ${s.bank[resource]} ${resource}.`);
    s.bank[resource] -= amount;
    s.players[player].resources[resource] += amount;
    this.log(`[debug] ${this.name(player)} was given ${amount} ${resource}.`);
    return OK;
  }

  // ---------------------------------------------------------------- helpers

  private log(msg: string) {
    this.state.log.push(msg);
  }

  private pay(p: number, cost: Partial<ResourceMap>) {
    const res = this.state.players[p].resources;
    for (const r of RESOURCES) {
      const n = cost[r] ?? 0;
      res[r] -= n;
      this.state.bank[r] += n;
    }
  }

  private grantSetupResources(p: number, corner: number) {
    const s = this.state;
    const got = emptyResources();
    for (const h of GEO.corners[corner].hexes) {
      const r = TERRAIN_RESOURCE[s.board.tiles[h].terrain];
      if (r && s.bank[r] > 0) {
        s.bank[r]--;
        s.players[p].resources[r]++;
        got[r]++;
      }
    }
    const text = formatCost(got);
    this.log(`${this.name(p)} received ${text || 'nothing'} from their second settlement.`);
  }

  private advanceSetup() {
    const s = this.state;
    s.setupStep++;
    s.setupSettlement = null;
    if (s.setupStep >= s.setupOrder.length) {
      s.currentPlayer = 0;
      s.phase = 'roll';
      this.log(`Setup complete. — ${this.current.name}'s turn.`);
    } else {
      s.currentPlayer = s.setupOrder[s.setupStep];
      s.phase = 'setup-settlement';
    }
  }

  private produce(total: number) {
    const s = this.state;
    const owed = Object.fromEntries(RESOURCES.map((r) => [r, s.players.map(() => 0)])) as Record<Resource, number[]>;
    GEO.hexes.forEach((hex) => {
      const tile = s.board.tiles[hex.id];
      const r = TERRAIN_RESOURCE[tile.terrain];
      if (tile.number !== total || !r) return;
      if (hex.id === s.robberHex) {
        this.log(`The robber blocks hex ${hex.id} (${tile.terrain}).`);
        return;
      }
      for (const c of hex.corners) {
        const b = s.buildings[c];
        if (b) owed[r][b.owner] += b.kind === 'city' ? 2 : 1;
      }
    });

    const received = s.players.map(() => emptyResources());
    for (const r of RESOURCES) {
      const want = owed[r];
      const sum = want.reduce((a, b) => a + b, 0);
      if (sum === 0) continue;
      const owedPlayers = want.flatMap((n, p) => (n > 0 ? [p] : []));
      if (sum <= s.bank[r]) {
        owedPlayers.forEach((p) => (received[p][r] = want[p]));
      } else if (owedPlayers.length === 1) {
        received[owedPlayers[0]][r] = s.bank[r];
        this.log(`Bank shortage: only ${s.bank[r]} ${r} left for ${this.name(owedPlayers[0])}.`);
      } else {
        this.log(`Bank shortage: not enough ${r} for everyone, so nobody receives ${r}.`);
      }
    }

    let anyone = false;
    received.forEach((got, p) => {
      for (const r of RESOURCES) {
        s.bank[r] -= got[r];
        s.players[p].resources[r] += got[r];
      }
      if (totalCards(got) > 0) {
        anyone = true;
        this.log(`${this.name(p)} received ${formatCost(got)}.`);
      }
    });
    if (!anyone) this.log('No one produced anything.');
  }

  private doSteal(victim: number) {
    const s = this.state;
    const res = s.players[victim].resources;
    const deck = RESOURCES.flatMap((r) => Array<Resource>(res[r]).fill(r));
    if (deck.length === 0) {
      this.log(`${this.current.name} tried to rob ${this.name(victim)}, who has no cards.`);
      return;
    }
    const rng = new Rng(s.rngState);
    const card = deck[rng.int(deck.length)];
    s.rngState = rng.state;
    res[card]--;
    this.current.resources[card]++;
    this.log(`${this.current.name} stole a card from ${this.name(victim)}.`);
  }

  /** Recompute road lengths and re-assign the Longest Road card. */
  updateLongestRoad() {
    const s = this.state;
    s.roadLengths = s.players.map((p) => longestRoadLength(s.roads, s.buildings, p.id));
    const before = s.longestRoadHolder;
    const after = resolveLongestRoad(s.roadLengths, before);
    if (after === before) return;
    s.longestRoadHolder = after;
    if (after !== null) {
      this.log(`${this.name(after)} takes Longest Road (length ${s.roadLengths[after]}).`);
    } else {
      this.log(
        `Longest Road is set aside: no one uniquely has the longest road of at least ${LONGEST_ROAD_MIN}.`,
      );
    }
  }

  /** A player wins once they have 10+ VP during their own turn. */
  private checkWin() {
    const s = this.state;
    if (this.isSetup || s.phase === 'game-over') return;
    const p = s.currentPlayer;
    if (this.victoryPoints(p) >= WINNING_VP) {
      s.winner = p;
      s.phase = 'game-over';
      this.log(`🏆 ${this.name(p)} wins with ${this.victoryPoints(p)} victory points!`);
    }
  }
}

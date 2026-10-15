export const RESOURCES = ['wood', 'brick', 'sheep', 'wheat', 'ore'] as const;
export type Resource = (typeof RESOURCES)[number];
export type ResourceMap = Record<Resource, number>;

export type Terrain = 'forest' | 'pasture' | 'fields' | 'hills' | 'mountains' | 'desert';

export const TERRAIN_RESOURCE: Record<Terrain, Resource | null> = {
  forest: 'wood',
  pasture: 'sheep',
  fields: 'wheat',
  hills: 'brick',
  mountains: 'ore',
  desert: null,
};

export interface HexTile {
  terrain: Terrain;
  /** Number token, or null for the desert. */
  number: number | null;
}

export interface Board {
  seed: string;
  /** Indexed by hex id (see geometry.ts). */
  tiles: HexTile[];
  desertHex: number;
}

export interface Building {
  owner: number;
  kind: 'settlement' | 'city';
}

export interface Player {
  id: number;
  name: string;
  color: string;
  resources: ResourceMap;
  /** Pieces still in the player's supply. */
  roadsLeft: number;
  settlementsLeft: number;
  citiesLeft: number;
}

export type Phase =
  | 'setup-settlement'
  | 'setup-road'
  | 'roll'
  | 'discard'
  | 'move-robber'
  | 'steal'
  | 'main'
  | 'game-over';

export interface PendingDiscard {
  player: number;
  amount: number;
}

export interface GameState {
  board: Board;
  players: Player[];
  bank: ResourceMap;
  /** Indexed by corner id. */
  buildings: (Building | null)[];
  /** Indexed by edge id: owning player or null. */
  roads: (number | null)[];
  robberHex: number;
  phase: Phase;
  currentPlayer: number;
  /** Index into setupOrder during the setup phase. */
  setupStep: number;
  setupOrder: number[];
  /** Corner of the settlement just placed in setup (its road must touch it). */
  setupSettlement: number | null;
  dice: [number, number] | null;
  pendingDiscards: PendingDiscard[];
  /** Players the roller may steal from after moving the robber. */
  stealCandidates: number[];
  longestRoadHolder: number | null;
  roadLengths: number[];
  winner: number | null;
  /** Debug: total for the next roll, consumed by roll(). */
  forcedRoll: number | null;
  rngState: number;
  log: string[];
}

export type Result = { ok: true } | { ok: false; error: string };

export const OK: Result = { ok: true };
export function fail(error: string): Result {
  return { ok: false, error };
}

export function emptyResources(): ResourceMap {
  return { wood: 0, brick: 0, sheep: 0, wheat: 0, ore: 0 };
}

export function totalCards(r: ResourceMap): number {
  return RESOURCES.reduce((sum, k) => sum + r[k], 0);
}

export const COSTS = {
  road: { wood: 1, brick: 1 },
  settlement: { wood: 1, brick: 1, wheat: 1, sheep: 1 },
  city: { ore: 3, wheat: 2 },
} satisfies Record<string, Partial<ResourceMap>>;

export type BuildKind = keyof typeof COSTS;

export const PIECE_LIMITS = { roads: 15, settlements: 5, cities: 4 };
export const BANK_PER_RESOURCE = 19;
export const WINNING_VP = 10;
export const LONGEST_ROAD_MIN = 5;

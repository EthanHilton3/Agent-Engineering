export type Resource = 'wood' | 'brick' | 'sheep' | 'wheat' | 'ore';
export type ResourceCounts = Record<Resource, number>;
export type Terrain = 'forest' | 'pasture' | 'fields' | 'hills' | 'mountains' | 'desert';
export type HexId = number; // 0..18
export type CornerId = number; // 0..53
export type EdgeId = number; // 0..71
export type PlayerId = number; // 0..N-1 (displayed as "Player 1".."Player N")

/** Static board geometry, identical for every game. */
export interface Topology {
  hexCoords: { q: number; r: number }[]; // axial, radius 2, rows 3-4-5-4-3
  hexCorners: CornerId[][]; // 6 per hex
  hexNeighbors: HexId[][]; // on-board neighbours only
  cornerHexes: HexId[][]; // 1..3 per corner
  cornerNeighbors: CornerId[][]; // 2..3 per corner
  cornerEdges: EdgeId[][]; // 2..3 per corner
  edgeCorners: [CornerId, CornerId][]; // endpoints
  cornerPositions: { x: number; y: number }[]; // unit hex size, for the UI
}

export interface Hex {
  id: HexId;
  terrain: Terrain;
  number: number | null;
}

export interface Board {
  seed: number;
  hexes: Hex[]; // indexed by HexId
}

export interface Building {
  owner: PlayerId;
  kind: 'settlement' | 'city';
}

export interface PiecesLeft {
  road: number;
  settlement: number;
  city: number;
}

export interface Player {
  id: PlayerId;
  name: string;
  color: string;
  hand: ResourceCounts;
  pieces: PiecesLeft;
}

export type Phase =
  | { kind: 'setup'; turnIndex: number; step: 'settlement' | 'road'; lastSettlement: CornerId | null }
  | { kind: 'roll' }
  | { kind: 'discard'; pending: { player: PlayerId; amount: number }[] }
  | { kind: 'moveRobber' }
  | { kind: 'steal'; candidates: PlayerId[] }
  | { kind: 'main' } // trade and build
  | { kind: 'gameOver'; winner: PlayerId };

export interface GameState {
  board: Board;
  players: Player[];
  currentPlayer: PlayerId;
  phase: Phase;
  buildings: (Building | null)[]; // indexed by CornerId
  roads: (PlayerId | null)[]; // indexed by EdgeId
  bank: ResourceCounts;
  robberHex: HexId;
  longestRoadHolder: PlayerId | null;
  lastRoll: [number, number] | null;
  forcedRoll: number | null; // debug: total for the next roll
  rngState: number; // dice and steals; advanced on use
  log: string[];
}

export type Action =
  | { type: 'placeSettlement'; corner: CornerId } // setup and normal play
  | { type: 'placeRoad'; edge: EdgeId } // setup and normal play
  | { type: 'placeCity'; corner: CornerId }
  | { type: 'roll' }
  | { type: 'discard'; cards: Partial<ResourceCounts> } // for phase.pending[0]
  | { type: 'moveRobber'; hex: HexId }
  | { type: 'steal'; victim: PlayerId }
  | { type: 'bankTrade'; give: Resource; get: Resource }
  | { type: 'endTurn' }
  | { type: 'debugForceRoll'; total: number }
  | { type: 'debugGiveResource'; player: PlayerId; resource: Resource; amount: number };

export type ActionResult = { ok: true; state: GameState } | { ok: false; error: string };

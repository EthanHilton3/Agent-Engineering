import type { CornerId, EdgeId, HexId, Topology } from './types';

// Pointy-top hexes in axial coordinates (q, r), radius 2, so rows of
// r = -2..2 hold 3-4-5-4-3 hexes. Hex IDs run row by row, left to right.
// Corner IDs are assigned in hex order then corner order (clockwise from the
// top-right), deduplicated by rounded position, so IDs are stable across games.

const BOARD_RADIUS = 2;
const SQRT3 = Math.sqrt(3);
const AXIAL_DIRECTIONS: [number, number][] = [
  [1, 0],
  [1, -1],
  [0, -1],
  [-1, 0],
  [-1, 1],
  [0, 1],
];

/** The static board geometry shared by every game. */
export const TOPOLOGY: Topology = buildTopology();

/** The edge joining two corners, or null if they are not adjacent. */
export function edgeBetween(a: CornerId, b: CornerId): EdgeId | null {
  return TOPOLOGY.cornerEdges[a].find((e) => TOPOLOGY.edgeCorners[e].includes(b)) ?? null;
}

function buildTopology(): Topology {
  const hexCoords = axialHexCoords();
  const hexNeighbors = hexCoords.map((coord) => neighborsOf(coord, hexCoords));
  const { hexCorners, cornerPositions } = dedupeCorners(hexCoords);
  const edgeCorners = collectEdges(hexCorners);
  const cornerHexes = invert(hexCorners, cornerPositions.length);
  const cornerEdges = invert(edgeCorners, cornerPositions.length);
  const cornerNeighbors = cornerEdges.map((edges, corner) =>
    edges.map((e) => otherEnd(edgeCorners[e], corner)),
  );
  return { hexCoords, hexCorners, hexNeighbors, cornerHexes, cornerNeighbors, cornerEdges, edgeCorners, cornerPositions };
}

function axialHexCoords(): { q: number; r: number }[] {
  const coords: { q: number; r: number }[] = [];
  for (let r = -BOARD_RADIUS; r <= BOARD_RADIUS; r++) {
    for (let q = -BOARD_RADIUS; q <= BOARD_RADIUS; q++) {
      if (Math.abs(q + r) <= BOARD_RADIUS) coords.push({ q, r });
    }
  }
  return coords;
}

function neighborsOf(coord: { q: number; r: number }, all: { q: number; r: number }[]): HexId[] {
  const neighbors: HexId[] = [];
  for (const [dq, dr] of AXIAL_DIRECTIONS) {
    const id = all.findIndex((c) => c.q === coord.q + dq && c.r === coord.r + dr);
    if (id >= 0) neighbors.push(id);
  }
  return neighbors;
}

function dedupeCorners(hexCoords: { q: number; r: number }[]): {
  hexCorners: CornerId[][];
  cornerPositions: { x: number; y: number }[];
} {
  const idByKey = new Map<string, CornerId>();
  const cornerPositions: { x: number; y: number }[] = [];
  const hexCorners = hexCoords.map((coord) =>
    cornerPointsOf(coord).map((point) => {
      const key = positionKey(point);
      let id = idByKey.get(key);
      if (id === undefined) {
        id = cornerPositions.length;
        idByKey.set(key, id);
        cornerPositions.push(point);
      }
      return id;
    }),
  );
  return { hexCorners, cornerPositions };
}

/** The six corner points of a unit-size pointy-top hex, clockwise from the top-right. */
function cornerPointsOf(coord: { q: number; r: number }): { x: number; y: number }[] {
  const cx = SQRT3 * (coord.q + coord.r / 2);
  const cy = 1.5 * coord.r;
  return [0, 1, 2, 3, 4, 5].map((i) => {
    const angle = (Math.PI / 180) * (60 * i - 30);
    return { x: cx + Math.cos(angle), y: cy + Math.sin(angle) };
  });
}

function positionKey(point: { x: number; y: number }): string {
  // Adding 0 turns -0 into 0 so the same corner always yields the same key.
  const round = (n: number) => (Math.round(n * 1000) / 1000 + 0).toFixed(3);
  return `${round(point.x)},${round(point.y)}`;
}

/** Edges between consecutive corners of each hex, deduplicated by sorted corner pair. */
function collectEdges(hexCorners: CornerId[][]): [CornerId, CornerId][] {
  const seen = new Set<string>();
  const edges: [CornerId, CornerId][] = [];
  for (const corners of hexCorners) {
    corners.forEach((a, i) => {
      const b = corners[(i + 1) % corners.length];
      const pair: [CornerId, CornerId] = a < b ? [a, b] : [b, a];
      const key = pair.join('-');
      if (!seen.has(key)) {
        seen.add(key);
        edges.push(pair);
      }
    });
  }
  return edges;
}

/** Given a list of items each referencing some corners, lists the items touching each corner. */
function invert(itemCorners: readonly CornerId[][], cornerCount: number): number[][] {
  const result: number[][] = Array.from({ length: cornerCount }, () => []);
  itemCorners.forEach((corners, item) => {
    for (const corner of corners) result[corner].push(item);
  });
  return result;
}

function otherEnd(edge: [CornerId, CornerId], corner: CornerId): CornerId {
  return edge[0] === corner ? edge[1] : edge[0];
}

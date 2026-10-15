/**
 * Fixed board topology: 19 pointy-top hexes in a 3-4-5-4-3 layout, plus the
 * 54 corners (intersections) and 72 edges between them. Topology never changes
 * between games; only terrain and numbers do, so it is computed once.
 */

export interface HexGeo {
  id: number;
  q: number;
  r: number;
  /** Center in unit-hex coordinates (hex "size" = 1). */
  x: number;
  y: number;
  /** Corner ids, clockwise starting from the top corner. */
  corners: number[];
  edges: number[];
  /** Ids of neighbouring land hexes. */
  neighbors: number[];
}

export interface CornerGeo {
  id: number;
  x: number;
  y: number;
  hexes: number[];
  edges: number[];
  /** Corners one edge away. */
  neighbors: number[];
}

export interface EdgeGeo {
  id: number;
  corners: [number, number];
  hexes: number[];
}

export interface Geometry {
  hexes: HexGeo[];
  corners: CornerGeo[];
  edges: EdgeGeo[];
}

const SQRT3 = Math.sqrt(3);
const AXIAL_DIRS: [number, number][] = [
  [1, 0], [1, -1], [0, -1], [-1, 0], [-1, 1], [0, 1],
];

function buildGeometry(): Geometry {
  const hexes: HexGeo[] = [];
  for (let r = -2; r <= 2; r++) {
    for (let q = Math.max(-2, -r - 2); q <= Math.min(2, -r + 2); q++) {
      hexes.push({
        id: hexes.length, q, r,
        x: SQRT3 * (q + r / 2),
        y: 1.5 * r,
        corners: [], edges: [], neighbors: [],
      });
    }
  }

  const corners: CornerGeo[] = [];
  const cornerByKey = new Map<string, number>();
  for (const hex of hexes) {
    for (let i = 0; i < 6; i++) {
      const angle = (Math.PI / 180) * (60 * i - 90);
      const x = hex.x + Math.cos(angle);
      const y = hex.y + Math.sin(angle);
      const key = `${Math.round(x * 1000)},${Math.round(y * 1000)}`;
      let id = cornerByKey.get(key);
      if (id === undefined) {
        id = corners.length;
        cornerByKey.set(key, id);
        corners.push({ id, x, y, hexes: [], edges: [], neighbors: [] });
      }
      corners[id].hexes.push(hex.id);
      hex.corners.push(id);
    }
  }

  const edges: EdgeGeo[] = [];
  const edgeByKey = new Map<string, number>();
  for (const hex of hexes) {
    for (let i = 0; i < 6; i++) {
      const a = hex.corners[i];
      const b = hex.corners[(i + 1) % 6];
      const key = a < b ? `${a}-${b}` : `${b}-${a}`;
      let id = edgeByKey.get(key);
      if (id === undefined) {
        id = edges.length;
        edgeByKey.set(key, id);
        edges.push({ id, corners: [Math.min(a, b), Math.max(a, b)], hexes: [] });
        corners[a].edges.push(id);
        corners[b].edges.push(id);
        corners[a].neighbors.push(b);
        corners[b].neighbors.push(a);
      }
      edges[id].hexes.push(hex.id);
      hex.edges.push(id);
    }
  }

  const hexByAxial = new Map(hexes.map((h) => [`${h.q},${h.r}`, h.id]));
  for (const hex of hexes) {
    for (const [dq, dr] of AXIAL_DIRS) {
      const n = hexByAxial.get(`${hex.q + dq},${hex.r + dr}`);
      if (n !== undefined) hex.neighbors.push(n);
    }
  }

  return { hexes, corners, edges };
}

export const GEO: Geometry = buildGeometry();

/** The edge joining two corners, or undefined if they are not adjacent. */
export function edgeBetween(a: number, b: number): number | undefined {
  return GEO.corners[a].edges.find((e) => GEO.edges[e].corners.includes(b));
}

export function otherCorner(edge: number, corner: number): number {
  const [a, b] = GEO.edges[edge].corners;
  return a === corner ? b : a;
}

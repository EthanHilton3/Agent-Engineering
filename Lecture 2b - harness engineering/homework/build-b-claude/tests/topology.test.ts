import { describe, expect, it } from 'vitest';
import { TOPOLOGY, edgeBetween } from '../src/engine/topology';

const { hexCoords, hexCorners, hexNeighbors, cornerHexes, cornerNeighbors, cornerEdges, edgeCorners, cornerPositions } =
  TOPOLOGY;

describe('topology', () => {
  it('has 19 hexes, 54 corners, and 72 edges', () => {
    expect(hexCoords).toHaveLength(19);
    expect(cornerPositions).toHaveLength(54);
    expect(edgeCorners).toHaveLength(72);
  });

  it('lays hexes out in rows of 3-4-5-4-3', () => {
    const rowSizes = [-2, -1, 0, 1, 2].map((r) => hexCoords.filter((c) => c.r === r).length);
    expect(rowSizes).toEqual([3, 4, 5, 4, 3]);
  });

  it('gives every hex 6 distinct corners', () => {
    for (const corners of hexCorners) expect(new Set(corners).size).toBe(6);
  });

  it('gives every corner 1-3 hexes, 2-3 neighbours, and matching edges', () => {
    cornerNeighbors.forEach((neighbors, corner) => {
      expect(neighbors.length).toBeGreaterThanOrEqual(2);
      expect(neighbors.length).toBeLessThanOrEqual(3);
      expect(cornerEdges[corner]).toHaveLength(neighbors.length);
      expect(cornerHexes[corner].length).toBeGreaterThanOrEqual(1);
      expect(cornerHexes[corner].length).toBeLessThanOrEqual(3);
    });
  });

  it('has symmetric corner adjacency', () => {
    cornerNeighbors.forEach((neighbors, corner) => {
      for (const n of neighbors) expect(cornerNeighbors[n]).toContain(corner);
    });
  });

  it('has symmetric hex adjacency with 3-6 neighbours per hex', () => {
    hexNeighbors.forEach((neighbors, hex) => {
      expect(neighbors.length).toBeGreaterThanOrEqual(3);
      expect(neighbors.length).toBeLessThanOrEqual(6);
      for (const n of neighbors) expect(hexNeighbors[n]).toContain(hex);
    });
    expect(hexNeighbors[9]).toHaveLength(6); // centre hex
  });

  it("makes every edge's endpoints corner neighbours", () => {
    edgeCorners.forEach(([a, b], edge) => {
      expect(cornerNeighbors[a]).toContain(b);
      expect(cornerEdges[a]).toContain(edge);
      expect(cornerEdges[b]).toContain(edge);
    });
  });

  it('keeps cornerHexes consistent with hexCorners', () => {
    cornerHexes.forEach((hexes, corner) => {
      for (const hex of hexes) expect(hexCorners[hex]).toContain(corner);
    });
  });

  it('finds the edge between adjacent corners and null otherwise', () => {
    const [a, b] = edgeCorners[10];
    expect(edgeBetween(a, b)).toBe(10);
    expect(edgeBetween(b, a)).toBe(10);
    const notNeighbor = cornerPositions.findIndex((_, c) => c !== a && !cornerNeighbors[a].includes(c));
    expect(edgeBetween(a, notNeighbor)).toBeNull();
  });
});

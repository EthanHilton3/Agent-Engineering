import type { Resource, ResourceCounts, Terrain } from './types';

/** All resources, in display order. */
export const RESOURCES: Resource[] = ['wood', 'brick', 'sheep', 'wheat', 'ore'];

/** Resource cost of each buildable piece. */
export const COSTS: Record<'road' | 'settlement' | 'city', ResourceCounts> = {
  road: countsOf({ brick: 1, wood: 1 }),
  settlement: countsOf({ brick: 1, wood: 1, wheat: 1, sheep: 1 }),
  city: countsOf({ ore: 3, wheat: 2 }),
};

/** Returns a count of zero for every resource. */
export function emptyCounts(): ResourceCounts {
  return { wood: 0, brick: 0, sheep: 0, wheat: 0, ore: 0 };
}

/** Fills in missing resources of a partial count with zero. */
export function countsOf(partial: Partial<ResourceCounts>): ResourceCounts {
  return { ...emptyCounts(), ...partial };
}

/** Total number of cards across all resources. */
export function totalCards(counts: ResourceCounts): number {
  return RESOURCES.reduce((sum, r) => sum + counts[r], 0);
}

/** True if `have` holds at least `need` of every resource. */
export function hasAtLeast(have: ResourceCounts, need: ResourceCounts): boolean {
  return RESOURCES.every((r) => have[r] >= need[r]);
}

/** Per-resource sum of two counts. */
export function addCounts(a: ResourceCounts, b: ResourceCounts): ResourceCounts {
  return combine(a, b, (x, y) => x + y);
}

/** Per-resource difference `a - b` (callers check `hasAtLeast` first). */
export function subtractCounts(a: ResourceCounts, b: ResourceCounts): ResourceCounts {
  return combine(a, b, (x, y) => x - y);
}

/** Human-readable list of the non-zero counts, e.g. "1 wood, 2 ore" (or "nothing"), for the log. */
export function describeCounts(counts: ResourceCounts): string {
  const parts = RESOURCES.filter((r) => counts[r] > 0).map((r) => `${counts[r]} ${r}`);
  return parts.length > 0 ? parts.join(', ') : 'nothing';
}

/** The resource a terrain produces, or null for the desert. */
export function terrainResource(terrain: Terrain): Resource | null {
  return TERRAIN_RESOURCE[terrain];
}

const TERRAIN_RESOURCE: Record<Terrain, Resource | null> = {
  forest: 'wood',
  hills: 'brick',
  pasture: 'sheep',
  fields: 'wheat',
  mountains: 'ore',
  desert: null,
};

function combine(a: ResourceCounts, b: ResourceCounts, op: (x: number, y: number) => number): ResourceCounts {
  const result = emptyCounts();
  for (const r of RESOURCES) result[r] = op(a[r], b[r]);
  return result;
}

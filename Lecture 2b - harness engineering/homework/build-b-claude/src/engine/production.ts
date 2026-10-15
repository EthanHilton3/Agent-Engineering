import { RESOURCES, emptyCounts, terrainResource } from './resources';
import { TOPOLOGY } from './topology';
import type { Building, GameState, Hex, PlayerId, Resource, ResourceCounts } from './types';

/** The cards each player receives for a roll of `total` (indexed by PlayerId), after the robber and bank shortages. */
export function computeProduction(state: GameState, total: number): ResourceCounts[] {
  const owed = owedProduction(state, total);
  return applyBankShortage(owed, state.bank);
}

/** How many cards a player holding `handTotal` cards must discard when a 7 is rolled. */
export function discardAmount(handTotal: number): number {
  return handTotal > DISCARD_LIMIT ? Math.floor(handTotal / 2) : 0;
}

const DISCARD_LIMIT = 7;
const BUILDING_YIELD: Record<Building['kind'], number> = { settlement: 1, city: 2 };

/** What every building on a producing hex earns, before checking the bank. */
function owedProduction(state: GameState, total: number): ResourceCounts[] {
  const owed = state.players.map(() => emptyCounts());
  for (const hex of producingHexes(state, total)) {
    const resource = terrainResource(hex.terrain);
    if (resource === null) continue;
    // A corner shared by several producing hexes is visited once per hex, so it earns from each.
    for (const corner of TOPOLOGY.hexCorners[hex.id]) {
      const building = state.buildings[corner];
      if (building) owed[building.owner][resource] += BUILDING_YIELD[building.kind];
    }
  }
  return owed;
}

function producingHexes(state: GameState, total: number): Hex[] {
  return state.board.hexes.filter((hex) => hex.number === total && hex.id !== state.robberHex);
}

/**
 * Per resource: if the bank can cover everyone owed, all are paid; if not, a sole claimant gets
 * whatever the bank has left and multiple claimants get nothing.
 */
function applyBankShortage(owed: ResourceCounts[], bank: ResourceCounts): ResourceCounts[] {
  const paid = owed.map(() => emptyCounts());
  for (const resource of RESOURCES) {
    const claimants = claimantsOf(owed, resource);
    const totalOwed = claimants.reduce((sum, p) => sum + owed[p][resource], 0);
    if (totalOwed <= bank[resource]) {
      for (const p of claimants) paid[p][resource] = owed[p][resource];
    } else if (claimants.length === 1) {
      paid[claimants[0]][resource] = bank[resource];
    }
  }
  return paid;
}

function claimantsOf(owed: ResourceCounts[], resource: Resource): PlayerId[] {
  return owed.flatMap((counts, player) => (counts[resource] > 0 ? [player] : []));
}

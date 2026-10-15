import type { GameState, PlayerId } from './types';

/** Points needed to win. */
export const WINNING_POINTS = 10;

/** A player's victory points: 1 per settlement, 2 per city, 2 for holding Longest Road. */
export function victoryPoints(state: GameState, player: PlayerId): number {
  const buildingPoints = state.buildings.reduce(
    (sum, building) => (building?.owner === player ? sum + BUILDING_POINTS[building.kind] : sum),
    0,
  );
  const longestRoadPoints = state.longestRoadHolder === player ? LONGEST_ROAD_POINTS : 0;
  return buildingPoints + longestRoadPoints;
}

/** Ends the game with `player` as the winner if they have enough points. */
export function checkWinner(draft: GameState, player: PlayerId): void {
  if (draft.phase.kind === 'gameOver') return;
  const points = victoryPoints(draft, player);
  if (points < WINNING_POINTS) return;
  draft.phase = { kind: 'gameOver', winner: player };
  draft.log.push(`${draft.players[player].name} wins with ${points} victory points!`);
}

const BUILDING_POINTS = { settlement: 1, city: 2 } as const;
const LONGEST_ROAD_POINTS = 2;

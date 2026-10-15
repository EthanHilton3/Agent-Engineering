import { roadLength } from '../engine/longestRoad';
import { RESOURCES, totalCards } from '../engine/resources';
import { victoryPoints } from '../engine/scoring';
import type { GameState, Player } from '../engine/types';
import { html, swatch } from './dom';

/** One panel per player: name and color, VP, card count, pieces left, road length; the current player's hand too. */
export function renderPlayerPanels(state: GameState): HTMLElement {
  return html(
    'section',
    { class: 'player-panels', 'aria-label': 'Players' },
    state.players.map((player) => renderPlayerPanel(state, player)),
  );
}

function renderPlayerPanel(state: GameState, player: Player): HTMLElement {
  const isCurrent = player.id === state.currentPlayer;
  return html('article', { class: isCurrent ? 'player-panel current' : 'player-panel' }, [
    html('h2', {}, [
      swatch(player.color),
      player.name,
      isCurrent && html('span', { class: 'badge' }, ['current']),
      state.longestRoadHolder === player.id && html('span', { class: 'badge longest-road' }, ['Longest Road']),
    ]),
    html('dl', { class: 'player-stats' }, [
      stat('Victory points', String(victoryPoints(state, player.id))),
      stat('Resource cards', String(totalCards(player.hand))),
      stat('Road length', String(roadLength(state, player.id))),
      stat('Pieces left', piecesLeftText(player)),
    ]),
    isCurrent && renderHand(player),
  ]);
}

function renderHand(player: Player): HTMLElement {
  return html(
    'ul',
    { class: 'hand', 'aria-label': `${player.name}'s cards` },
    RESOURCES.map((resource) =>
      html('li', { class: `card resource-${resource}` }, [
        html('span', { class: 'card-count' }, [String(player.hand[resource])]),
        resource,
      ]),
    ),
  );
}

function stat(label: string, value: string): HTMLElement {
  return html('div', { class: 'stat' }, [html('dt', {}, [label]), html('dd', {}, [value])]);
}

function piecesLeftText(player: Player): string {
  const { road, settlement, city } = player.pieces;
  return `${road} roads, ${settlement} settlements, ${city} cities`;
}

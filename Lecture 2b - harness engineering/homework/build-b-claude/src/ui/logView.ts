import type { GameState } from '../engine/types';
import { html } from './dom';

/** The event log, newest entry first so the latest events are visible without scrolling. */
export function renderLog(state: GameState): HTMLElement {
  const newestFirst = state.log.slice().reverse();
  return html('section', { class: 'log', 'aria-label': 'Event log' }, [
    html('h2', {}, ['Event log']),
    html(
      'ol',
      { class: 'log-entries', reversed: '' },
      newestFirst.map((entry) => html('li', {}, [entry])),
    ),
  ]);
}

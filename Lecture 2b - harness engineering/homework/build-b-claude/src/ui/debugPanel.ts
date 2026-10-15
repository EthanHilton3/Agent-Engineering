import { RESOURCES } from '../engine/resources';
import type { Action, GameState, PlayerId, Resource } from '../engine/types';
import { html } from './dom';
import { readSeed } from './screens';

/** A "give resource" choice, kept by the app so the form remembers it between gifts. */
export interface GiveChoice {
  player: PlayerId;
  resource: Resource;
  amount: number;
}

/** What the debug panel needs from the app. */
export interface DebugPanelProps {
  state: GameState;
  showIds: boolean;
  lastGive: GiveChoice;
  dispatch: (action: Action) => void;
  onGive: (choice: GiveChoice) => void;
  onNewGame: (seed: number) => void;
  onShowIdsChange: (show: boolean) => void;
}

/** Debug tools: new game from a seed, force the next roll, give resources, and show board IDs. */
export function renderDebugPanel(props: DebugPanelProps): HTMLElement {
  // The engine rejects every action once the game is over, so only the tools that still work are shown.
  const gameOver = props.state.phase.kind === 'gameOver';
  return html('section', { class: 'debug-panel', 'aria-label': 'Debug' }, [
    html('h2', {}, ['Debug']),
    renderNewGameWithSeed(props.state.board.seed, props.onNewGame),
    !gameOver && renderForceRoll(props.state.forcedRoll, props.dispatch),
    !gameOver && renderGiveResource(props.state, props.lastGive, props.onGive),
    renderShowIdsToggle(props.showIds, props.onShowIdsChange),
  ]);
}

const DEFAULT_FORCED_ROLL = 7;
const ROLL_TOTALS = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];

function renderNewGameWithSeed(currentSeed: number, onNewGame: (seed: number) => void): HTMLFormElement {
  const seedInput = html('input', { id: 'debug-seed', type: 'text', inputmode: 'numeric', placeholder: 'random' });
  seedInput.value = String(currentSeed);
  const error = html('p', { class: 'error', role: 'alert' });
  const form = html('form', { class: 'debug-row' }, [
    html('label', { for: 'debug-seed' }, ['Seed']),
    seedInput,
    html('button', { type: 'submit' }, ['New game with this seed']),
    error,
  ]);
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const seed = readSeed(seedInput.value);
    if (typeof seed === 'string') error.textContent = seed;
    else onNewGame(seed);
  });
  return form;
}

function renderForceRoll(forcedRoll: number | null, dispatch: (action: Action) => void): HTMLFormElement {
  const totalSelect = html(
    'select',
    { id: 'debug-roll' },
    ROLL_TOTALS.map((total) => html('option', { value: total }, [String(total)])),
  );
  totalSelect.value = String(forcedRoll ?? DEFAULT_FORCED_ROLL);
  const form = html('form', { class: 'debug-row' }, [
    html('label', { for: 'debug-roll' }, ['Next roll']),
    totalSelect,
    html('button', { type: 'submit' }, ['Force roll']),
    forcedRoll !== null && html('span', { class: 'hint' }, [`(next roll will be ${forcedRoll})`]),
  ]);
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    dispatch({ type: 'debugForceRoll', total: Number(totalSelect.value) });
  });
  return form;
}

function renderGiveResource(state: GameState, lastGive: GiveChoice, onGive: (choice: GiveChoice) => void): HTMLFormElement {
  const playerSelect = html(
    'select',
    { id: 'debug-give-player' },
    state.players.map((player) => html('option', { value: player.id }, [player.name])),
  );
  playerSelect.value = String(lastGive.player);
  const resourceSelect = html(
    'select',
    { id: 'debug-give-resource' },
    RESOURCES.map((resource) => html('option', { value: resource }, [`${resource} (bank ${state.bank[resource]})`])),
  );
  resourceSelect.value = lastGive.resource;
  const amountInput = html('input', { id: 'debug-give-amount', type: 'number', min: 1, value: lastGive.amount });

  const form = html('form', { class: 'debug-row' }, [
    html('label', { for: 'debug-give-amount' }, ['Give']),
    amountInput,
    html('label', { for: 'debug-give-resource', class: 'visually-hidden' }, ['Resource']),
    resourceSelect,
    html('label', { for: 'debug-give-player' }, ['to']),
    playerSelect,
    html('button', { type: 'submit' }, ['Give']),
  ]);
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    onGive({
      player: Number(playerSelect.value),
      resource: resourceSelect.value as Resource,
      amount: Number(amountInput.value),
    });
  });
  return form;
}

function renderShowIdsToggle(showIds: boolean, onChange: (show: boolean) => void): HTMLElement {
  const checkbox = html('input', { id: 'debug-show-ids', type: 'checkbox' });
  checkbox.checked = showIds;
  checkbox.addEventListener('change', () => onChange(checkbox.checked));
  return html('div', { class: 'debug-row' }, [
    checkbox,
    html('label', { for: 'debug-show-ids' }, ['Show hex, corner, and edge IDs on the board']),
  ]);
}

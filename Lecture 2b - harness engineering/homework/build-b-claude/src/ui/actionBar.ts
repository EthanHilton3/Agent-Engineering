import { BANK_TRADE_RATE } from '../engine/building';
import { currentPhaseLabel } from '../engine/game';
import { buildError, type BuildKind } from '../engine/placement';
import { COSTS, RESOURCES, describeCounts, emptyCounts, totalCards } from '../engine/resources';
import type { Action, GameState, PlayerId, Resource, ResourceCounts } from '../engine/types';
import { html, swatch, type Child } from './dom';

/** What the action bar needs from the app: UI-only state and the ways to act on the game. */
export interface ActionBarProps {
  buildMode: BuildKind | null;
  error: string | null;
  dispatch: (action: Action) => void;
  onBuildModeClick: (kind: BuildKind) => void;
}

/** Phase and current player, dice, the controls for the current phase, and the latest error message. */
export function renderActionBar(state: GameState, ui: ActionBarProps): HTMLElement {
  return html('section', { class: 'action-bar', 'aria-label': 'Actions' }, [
    renderStatus(state),
    renderDice(state),
    html('div', { class: 'phase-controls' }, phaseControls(state, ui)),
    html('p', { class: 'error', role: 'alert' }, [ui.error ?? '']),
  ]);
}

const BUILD_KINDS: BuildKind[] = ['road', 'settlement', 'city'];

function phaseControls(state: GameState, ui: ActionBarProps): Child[] {
  const phase = state.phase;
  switch (phase.kind) {
    case 'setup':
      return [hint(`Click a highlighted ${phase.step === 'road' ? 'edge' : 'corner'} to place your ${phase.step}.`)];
    case 'roll':
      return [button('Roll dice', () => ui.dispatch({ type: 'roll' }), 'primary')];
    case 'discard':
      return [renderDiscardPrompt(state, phase.pending[0], ui.dispatch)];
    case 'moveRobber':
      return [hint('A 7! Click a highlighted hex to move the robber there.')];
    case 'steal':
      return [renderStealChooser(state, phase.candidates, ui.dispatch)];
    case 'main':
      return [
        renderBuildButtons(state, ui),
        renderBankTrade(ui.dispatch),
        button('End turn', () => ui.dispatch({ type: 'endTurn' }), 'primary'),
      ];
    case 'gameOver':
      return [hint('The game is over.')];
  }
}

function renderStatus(state: GameState): HTMLElement {
  const current = state.players[state.currentPlayer];
  return html('div', { class: 'status' }, [
    html('p', { class: 'turn' }, ['Turn: ', swatch(current.color), current.name]),
    html('p', { class: 'phase' }, [currentPhaseLabel(state)]),
  ]);
}

function renderDice(state: GameState): HTMLElement {
  if (!state.lastRoll) return html('p', { class: 'dice' }, ['Dice: not rolled yet this turn']);
  const [first, second] = state.lastRoll;
  return html('p', { class: 'dice' }, [
    'Dice: ',
    html('span', { class: 'die' }, [String(first)]),
    html('span', { class: 'die' }, [String(second)]),
    ` = ${first + second}`,
  ]);
}

/**
 * One button per piece. An unaffordable piece keeps a clickable button so the click can explain why;
 * the reason is the engine's `buildError`, shown as the tooltip here and in the error line by the app.
 */
function renderBuildButtons(state: GameState, ui: ActionBarProps): HTMLElement {
  const buttons = BUILD_KINDS.map((kind) => {
    const reason = buildError(state, kind);
    const selected = ui.buildMode === kind;
    const classes = ['build-button', selected && 'selected', reason && 'unavailable'].filter(Boolean).join(' ');
    const label = `Build ${kind} (${describeCounts(COSTS[kind])})`;
    const element = button(label, () => ui.onBuildModeClick(kind), classes);
    element.title = reason ?? (selected ? 'Click again to stop building' : `Choose where to build a ${kind}`);
    element.setAttribute('aria-pressed', String(selected));
    if (reason) element.setAttribute('aria-disabled', 'true');
    return element;
  });
  return html('div', { class: 'build-buttons' }, [
    ...buttons,
    ui.buildMode && hint(`Click a highlighted ${ui.buildMode === 'road' ? 'edge' : 'corner'} to build a ${ui.buildMode}.`),
  ]);
}

function renderBankTrade(dispatch: (action: Action) => void): HTMLFormElement {
  const give = resourceSelect('trade-give', RESOURCES[0]);
  const get = resourceSelect('trade-get', RESOURCES[1]);
  const form = html('form', { class: 'bank-trade' }, [
    html('label', { for: 'trade-give' }, [`Give ${BANK_TRADE_RATE}`]),
    give,
    html('label', { for: 'trade-get' }, ['for 1']),
    get,
    html('button', { type: 'submit' }, ['Trade with bank']),
  ]);
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    dispatch({ type: 'bankTrade', give: give.value as Resource, get: get.value as Resource });
  });
  return form;
}

/** Lets the player who owes a discard pick exactly which cards to give up; the engine checks the choice. */
function renderDiscardPrompt(
  state: GameState,
  request: { player: PlayerId; amount: number },
  dispatch: (action: Action) => void,
): HTMLFormElement {
  const player = state.players[request.player];
  const inputs = RESOURCES.map((resource) =>
    html('input', { id: `discard-${resource}`, type: 'number', min: 0, max: player.hand[resource], value: 0 }),
  );
  const selected = html('p', { class: 'discard-total' });
  const showSelected = () => {
    selected.textContent = `Selected ${totalCards(readCounts(inputs))} of ${request.amount}`;
  };

  const form = html('form', { class: 'discard-prompt' }, [
    html('h3', {}, [
      swatch(player.color),
      `${player.name}: you have ${totalCards(player.hand)} cards, discard ${request.amount}`,
    ]),
    html(
      'div',
      { class: 'discard-fields' },
      RESOURCES.map((resource, i) =>
        html('label', { for: `discard-${resource}` }, [`${resource} (have ${player.hand[resource]})`, inputs[i]]),
      ),
    ),
    selected,
    html('button', { type: 'submit', class: 'primary' }, ['Discard']),
  ]);
  showSelected();
  form.addEventListener('input', showSelected);
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    dispatch({ type: 'discard', cards: readCounts(inputs) });
  });
  return form;
}

function renderStealChooser(state: GameState, candidates: PlayerId[], dispatch: (action: Action) => void): HTMLElement {
  return html('div', { class: 'steal-chooser' }, [
    hint('Choose a player to steal a random card from:'),
    ...candidates.map((victim) => {
      const player = state.players[victim];
      const label = `${player.name} (${totalCards(player.hand)} cards)`;
      return button(label, () => dispatch({ type: 'steal', victim }));
    }),
  ]);
}

/** Reads one number input per resource (in `RESOURCES` order); blank fields count as 0. */
function readCounts(inputs: HTMLInputElement[]): ResourceCounts {
  const counts = emptyCounts();
  RESOURCES.forEach((resource, i) => {
    counts[resource] = inputs[i].value.trim() === '' ? 0 : Number(inputs[i].value);
  });
  return counts;
}

function resourceSelect(id: string, initial: Resource): HTMLSelectElement {
  const select = html(
    'select',
    { id },
    RESOURCES.map((resource) => html('option', { value: resource }, [resource])),
  );
  select.value = initial;
  return select;
}

function button(label: string, onClick: () => void, className = ''): HTMLButtonElement {
  const element = html('button', { type: 'button', class: className }, [label]);
  element.addEventListener('click', onClick);
  return element;
}

function hint(text: string): HTMLElement {
  return html('p', { class: 'hint' }, [text]);
}

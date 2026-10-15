import { MAX_PLAYERS, MIN_PLAYERS } from '../engine/game';
import { roadLength } from '../engine/longestRoad';
import { victoryPoints } from '../engine/scoring';
import type { GameState, Player } from '../engine/types';
import { html, swatch } from './dom';

/** The choices the new-game form hands to `createGame`. */
export interface NewGameOptions {
  seed: number;
  playerNames: string[];
}

/** The new-game form: player count, player names, and an optional seed (blank means random). */
export function renderNewGameForm(onStart: (opts: NewGameOptions) => void): HTMLElement {
  const countSelect = html('select', { id: 'player-count' }, playerCountOptions());
  countSelect.value = String(DEFAULT_PLAYER_COUNT);
  const nameList = html('div', { class: 'name-list' });
  const seedInput = html('input', { id: 'seed', type: 'text', inputmode: 'numeric', placeholder: 'random' });
  const error = html('p', { class: 'error', role: 'alert' });

  const form = html('form', { class: 'new-game' }, [
    html('h1', {}, ['Catan Lite']),
    html('label', { for: 'player-count' }, ['Players']),
    countSelect,
    nameList,
    html('label', { for: 'seed' }, ['Seed']),
    seedInput,
    error,
    html('button', { type: 'submit' }, ['Start game']),
  ]);

  const showNameInputs = () => nameList.replaceChildren(...nameInputs(Number(countSelect.value), nameList));
  countSelect.addEventListener('change', showNameInputs);
  showNameInputs();

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const seed = readSeed(seedInput.value);
    if (typeof seed === 'string') {
      error.textContent = seed;
      return;
    }
    const playerNames = Array.from(nameList.querySelectorAll('input'), (input) => input.value);
    onStart({ seed, playerNames });
  });
  return form;
}

/** The end-of-game screen: who won, everyone's final score, and a way to start over. */
export function renderWinnerScreen(state: GameState, onNewGame: () => void): HTMLElement {
  if (state.phase.kind !== 'gameOver') throw new Error('The winner screen needs a finished game');
  const winner = state.players[state.phase.winner];
  const byScore = state.players.slice().sort((a, b) => victoryPoints(state, b.id) - victoryPoints(state, a.id));
  const newGame = html('button', { type: 'button', class: 'primary' }, ['New game']);
  newGame.addEventListener('click', onNewGame);

  return html('section', { class: 'winner-screen', role: 'dialog', 'aria-label': 'Game over' }, [
    html('h2', {}, [swatch(winner.color), `${winner.name} wins with ${victoryPoints(state, winner.id)} victory points!`]),
    html('table', { class: 'final-scores' }, [
      html('thead', {}, [html('tr', {}, FINAL_SCORE_COLUMNS.map((label) => html('th', {}, [label])))]),
      html('tbody', {}, byScore.map((player) => finalScoreRow(state, player))),
    ]),
    newGame,
  ]);
}

const FINAL_SCORE_COLUMNS = ['Player', 'Victory points', 'Settlements', 'Cities', 'Longest Road'];

function finalScoreRow(state: GameState, player: Player): HTMLTableRowElement {
  const owned = state.buildings.filter((building) => building?.owner === player.id);
  const cells = [
    String(victoryPoints(state, player.id)),
    String(owned.filter((building) => building?.kind === 'settlement').length),
    String(owned.filter((building) => building?.kind === 'city').length),
    state.longestRoadHolder === player.id ? `Yes (${roadLength(state, player.id)})` : String(roadLength(state, player.id)),
  ];
  return html('tr', {}, [
    html('th', { scope: 'row' }, [swatch(player.color), player.name]),
    ...cells.map((text) => html('td', {}, [text])),
  ]);
}

const DEFAULT_PLAYER_COUNT = 3;
const MAX_SEED = 2 ** 32 - 1;
const MAX_NAME_LENGTH = 20;

function playerCountOptions(): HTMLOptionElement[] {
  const options: HTMLOptionElement[] = [];
  for (let count = MIN_PLAYERS; count <= MAX_PLAYERS; count++) {
    options.push(html('option', { value: count }, [`${count} players`]));
  }
  return options;
}

/** One name field per player, keeping any names already typed into `previous`. */
function nameInputs(count: number, previous: HTMLElement): HTMLElement[] {
  const typed = Array.from(previous.querySelectorAll('input'), (input) => input.value);
  return Array.from({ length: count }, (_, i) => {
    const id = `player-name-${i}`;
    const input = html('input', { id, type: 'text', maxlength: MAX_NAME_LENGTH, placeholder: `Player ${i + 1}` });
    input.value = typed[i] ?? '';
    return html('div', { class: 'name-field' }, [html('label', { for: id }, [`Player ${i + 1} name`]), input]);
  });
}

/** The seed typed by the user, a random one if blank, or an error message (Decision 1: a uint32). */
export function readSeed(text: string): number | string {
  const trimmed = text.trim();
  if (trimmed === '') return Date.now() % 2 ** 32;
  if (!/^\d+$/.test(trimmed) || Number(trimmed) > MAX_SEED) {
    return `The seed must be a whole number from 0 to ${MAX_SEED}`;
  }
  return Number(trimmed);
}

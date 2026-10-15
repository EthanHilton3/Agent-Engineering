import { applyAction, createGame } from '../engine/game';
import {
  buildError,
  legalCityCorners,
  legalRoadEdges,
  legalRobberHexes,
  legalSettlementCorners,
  type BuildKind,
} from '../engine/placement';
import type { Action, CornerId, EdgeId, GameState, HexId } from '../engine/types';
import { renderActionBar } from './actionBar';
import { renderBoard } from './boardView';
import { renderDebugPanel, type GiveChoice } from './debugPanel';
import { html } from './dom';
import { renderLog } from './logView';
import { renderPlayerPanels } from './playerPanels';
import { renderNewGameForm, renderWinnerScreen, type NewGameOptions } from './screens';

/** Mounts the game in `root`, starting at the new-game form. */
export function startApp(root: HTMLElement): void {
  new App(root).render();
}

/** Holds the current game plus UI-only state, and redraws everything after each change. */
class App {
  render(): void {
    const view = this.game ? this.gameView(this.game) : renderNewGameForm((opts) => this.start(opts));
    this.root.replaceChildren(view);
  }

  private start(opts: NewGameOptions): void {
    this.game = createGame(opts);
    this.error = null;
    this.buildMode = null;
    this.lastGive = { ...this.lastGive, player: 0 };
    this.render();
  }

  /** Debug: a fresh game on the given seed with the same players. */
  private restartWithSeed(seed: number): void {
    if (!this.game) return;
    this.start({ seed, playerNames: this.game.players.map((player) => player.name) });
  }

  private debugGive(choice: GiveChoice): void {
    this.lastGive = choice;
    this.dispatch({ type: 'debugGiveResource', ...choice });
  }

  private toggleDebug(): void {
    this.debugOpen = !this.debugOpen;
    this.render();
  }

  private setShowIds(show: boolean): void {
    this.showIds = show;
    this.render();
  }

  private backToNewGameForm(): void {
    this.game = null;
    this.render();
  }

  /** Applies an action through the engine; a rejected action leaves the game unchanged and shows the engine's reason. */
  private dispatch(action: Action): void {
    if (!this.game) return;
    const result = applyAction(this.game, action);
    if (result.ok) {
      this.game = result.state;
      this.error = null;
      this.buildMode = stillUsableBuildMode(result.state, this.buildMode);
    } else {
      this.error = result.error;
    }
    this.render();
  }

  /** Toggles a build mode; if the engine says the piece can't be built, shows its reason instead. */
  private chooseBuildMode(kind: BuildKind): void {
    if (!this.game) return;
    const reason = buildError(this.game, kind);
    const turningOff = this.buildMode === kind;
    this.error = reason;
    this.buildMode = reason !== null || turningOff ? null : kind;
    this.render();
  }

  private gameView(state: GameState): HTMLElement {
    const gameOver = state.phase.kind === 'gameOver';
    return html('div', { class: 'game' }, [
      this.header(state),
      gameOver && renderWinnerScreen(state, () => this.backToNewGameForm()),
      html('div', { class: 'game-layout' }, [
        html('div', { class: 'board-column' }, [this.board(state)]),
        html('div', { class: 'side-column' }, [
          !gameOver &&
            renderActionBar(state, {
              buildMode: this.buildMode,
              error: this.error,
              dispatch: (action) => this.dispatch(action),
              onBuildModeClick: (kind) => this.chooseBuildMode(kind),
            }),
          this.debugOpen &&
            renderDebugPanel({
              state,
              showIds: this.showIds,
              lastGive: this.lastGive,
              dispatch: (action) => this.dispatch(action),
              onGive: (choice) => this.debugGive(choice),
              onNewGame: (seed) => this.restartWithSeed(seed),
              onShowIdsChange: (show) => this.setShowIds(show),
            }),
          renderPlayerPanels(state),
          renderLog(state),
        ]),
      ]),
    ]);
  }

  private header(state: GameState): HTMLElement {
    const debugToggle = html('button', { type: 'button', class: 'debug-toggle', 'aria-pressed': String(this.debugOpen) }, [
      this.debugOpen ? 'Hide debug panel' : 'Show debug panel',
    ]);
    debugToggle.addEventListener('click', () => this.toggleDebug());
    return html('header', { class: 'game-header' }, [
      html('h1', {}, ['Catan Lite']),
      html('p', { class: 'seed' }, [`Seed: ${state.board.seed}`]),
      debugToggle,
    ]);
  }

  private board(state: GameState): SVGSVGElement {
    const targets = boardTargets(state, this.buildMode);
    const cornerAction = this.buildMode === 'city' ? 'placeCity' : 'placeSettlement';
    return renderBoard(state, {
      clickableCorners: targets.corners,
      clickableEdges: targets.edges,
      clickableHexes: targets.hexes,
      showIds: this.debugOpen && this.showIds,
      onCornerClick: (corner) => this.dispatch({ type: cornerAction, corner }),
      onEdgeClick: (edge) => this.dispatch({ type: 'placeRoad', edge }),
      onHexClick: (hex) => this.dispatch({ type: 'moveRobber', hex }),
    });
  }

  private game: GameState | null = null;
  private error: string | null = null;
  private buildMode: BuildKind | null = null;
  private debugOpen = false;
  private showIds = false;
  private lastGive: GiveChoice = { player: 0, resource: 'wood', amount: 1 };

  constructor(private readonly root: HTMLElement) {}
}

interface BoardTargets {
  corners: CornerId[];
  edges: EdgeId[];
  hexes: HexId[];
}

/** The spots the board should offer right now, straight from the engine's legal-spot queries. */
function boardTargets(state: GameState, buildMode: BuildKind | null): BoardTargets {
  switch (state.phase.kind) {
    case 'setup':
      return { ...NO_TARGETS, corners: legalSettlementCorners(state), edges: legalRoadEdges(state) };
    case 'moveRobber':
      return { ...NO_TARGETS, hexes: legalRobberHexes(state) };
    case 'main':
      return buildModeTargets(state, buildMode);
    default:
      return NO_TARGETS;
  }
}

const NO_TARGETS: BoardTargets = { corners: [], edges: [], hexes: [] };

function buildModeTargets(state: GameState, buildMode: BuildKind | null): BoardTargets {
  switch (buildMode) {
    case 'road':
      return { ...NO_TARGETS, edges: legalRoadEdges(state) };
    case 'settlement':
      return { ...NO_TARGETS, corners: legalSettlementCorners(state) };
    case 'city':
      return { ...NO_TARGETS, corners: legalCityCorners(state) };
    case null:
      return NO_TARGETS;
  }
}

/** Keeps the build mode across builds (handy for laying several roads) until the engine says it no longer applies. */
function stillUsableBuildMode(state: GameState, buildMode: BuildKind | null): BuildKind | null {
  if (buildMode === null || state.phase.kind !== 'main') return null;
  return buildError(state, buildMode) === null ? buildMode : null;
}

import { Game, PHASE_LABELS, PLAYER_COLORS, formatCost } from '../game/game';
import { randomSeed } from '../game/rng';
import {
  COSTS, RESOURCES, emptyResources, totalCards,
  type BuildKind, type Resource, type ResourceMap, type Result,
} from '../game/types';
import { renderBoard, type BoardHighlights } from './board';

type BuildMode = BuildKind | null;

const RESOURCE_ICON: Record<Resource, string> = {
  wood: '🌲', brick: '🧱', sheep: '🐑', wheat: '🌾', ore: '⛰️',
};
const DIE_FACES = ['⚀', '⚁', '⚂', '⚃', '⚄', '⚅'];

function esc(s: string): string {
  return s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!);
}

const resourceLabel = (r: Resource) => `${RESOURCE_ICON[r]} ${r}`;

export class App {
  private game: Game | null = null;
  private mode: BuildMode = null;
  private message: { text: string; kind: 'error' | 'info' } | null = null;
  private showIds = false;
  private debugOpen = false;
  private discardPick: ResourceMap = emptyResources();
  private tradeGive: Resource = 'wood';
  private tradeGet: Resource = 'ore';

  // Start screen + debug form fields
  private setupCount = 3;
  private setupNames = ['Player 1', 'Player 2', 'Player 3', 'Player 4'];
  private setupSeed = randomSeed();
  private debugSeed = '';
  private debugRoll = 7;
  private debugPlayer = 0;
  private debugResource: Resource = 'wood';
  private debugAmount = 1;

  constructor(private root: HTMLElement) {
    root.addEventListener('click', (e) => this.onClick(e));
    root.addEventListener('input', (e) => this.onInput(e));
    root.addEventListener('change', (e) => this.onInput(e));
    this.render();
  }

  // ----------------------------------------------------------------- events

  private onInput(e: Event) {
    const el = e.target as HTMLInputElement | HTMLSelectElement;
    const bind = el.dataset.bind;
    if (!bind) return;
    const v = el.value;
    switch (bind) {
      case 'count': this.setupCount = Number(v); this.render(); break;
      case 'name': this.setupNames[Number(el.dataset.index)] = v; break;
      case 'seed': this.setupSeed = v; break;
      case 'trade-give': this.tradeGive = v as Resource; break;
      case 'trade-get': this.tradeGet = v as Resource; break;
      case 'debug-seed': this.debugSeed = v; break;
      case 'debug-roll': this.debugRoll = Number(v); break;
      case 'debug-player': this.debugPlayer = Number(v); break;
      case 'debug-resource': this.debugResource = v as Resource; break;
      case 'debug-amount': this.debugAmount = Number(v); break;
      case 'show-ids': this.showIds = (el as HTMLInputElement).checked; this.render(); break;
    }
  }

  private onClick(e: Event) {
    const el = (e.target as Element).closest<HTMLElement | SVGElement>('[data-action]');
    if (!el) return;
    const d = el.dataset;
    const g = this.game;
    switch (d.action) {
      case 'start': return this.startGame(this.setupSeed.trim() || randomSeed());
      case 'random-seed': this.setupSeed = randomSeed(); return this.render();
      case 'new-game':
        if (g && g.state.phase !== 'game-over' && !confirm('Abandon the current game?')) return;
        this.game = null;
        this.setupSeed = randomSeed();
        return this.render();
      case 'toggle-debug': this.debugOpen = !this.debugOpen; return this.render();
    }
    if (!g) return;
    switch (d.action) {
      case 'roll': return this.apply(g.roll());
      case 'end-turn': return this.apply(g.endTurn(), `${g.name((g.state.currentPlayer + 1) % g.state.players.length)}, it's your turn.`);
      case 'build': return this.enterMode(d.kind as BuildKind);
      case 'cancel': this.mode = null; this.message = null; return this.render();
      case 'corner': {
        const c = Number(d.corner);
        const r = this.mode === 'city' ? g.placeCity(c) : g.placeSettlement(c);
        return this.apply(r);
      }
      case 'edge': return this.apply(g.placeRoad(Number(d.edge)));
      case 'robber': return this.apply(g.moveRobber(Number(d.hex)));
      case 'steal': return this.apply(g.steal(Number(d.player)));
      case 'trade': return this.apply(g.bankTrade(this.tradeGive, this.tradeGet));
      case 'discard-inc':
      case 'discard-dec': {
        const r = d.resource as Resource;
        const pending = g.pendingDiscard!;
        const have = g.state.players[pending.player].resources[r];
        const delta = d.action === 'discard-inc' ? 1 : -1;
        this.discardPick[r] = Math.max(0, Math.min(have, this.discardPick[r] + delta));
        return this.render();
      }
      case 'discard-confirm': {
        const pending = g.pendingDiscard!;
        const r = g.discard(pending.player, this.discardPick);
        if (r.ok) this.discardPick = emptyResources();
        return this.apply(r);
      }
      case 'debug-new': return this.startGame(this.debugSeed.trim() || randomSeed(), this.game!.state.players.map((p) => p.name));
      case 'debug-force': return this.apply(g.debugForceRoll(this.debugRoll), `Next roll will be ${this.debugRoll}.`);
      case 'debug-unforce': return this.apply(g.debugForceRoll(null), 'Next roll will be random.');
      case 'debug-give': return this.apply(g.debugGive(this.debugPlayer, this.debugResource, this.debugAmount));
    }
  }

  private startGame(seed: string, names?: string[]) {
    const playerNames = names ?? this.setupNames.slice(0, this.setupCount).map((n, i) => n.trim() || `Player ${i + 1}`);
    this.game = new Game({ seed, playerNames });
    this.debugSeed = seed;
    this.mode = null;
    this.message = null;
    this.discardPick = emptyResources();
    this.render();
  }

  private apply(r: Result, info?: string) {
    if (r.ok) {
      this.mode = null;
      this.message = info ? { text: info, kind: 'info' } : null;
    } else {
      this.message = { text: r.error, kind: 'error' };
    }
    this.render();
  }

  private enterMode(kind: BuildKind) {
    const g = this.game!;
    const err = g.buildError(kind);
    if (err) {
      this.message = { text: err, kind: 'error' };
    } else {
      const spots =
        kind === 'road' ? g.legalRoadEdges() : kind === 'settlement' ? g.legalSettlementCorners() : g.legalCityCorners();
      if (spots.length === 0) {
        const why = {
          road: 'There is no legal edge for a road (it must connect to your network).',
          settlement: 'There is no legal corner for a settlement (it must touch your road and obey the distance rule).',
          city: 'You have no settlements to upgrade.',
        }[kind];
        this.message = { text: why, kind: 'error' };
      } else {
        this.mode = kind;
        this.message = { text: `Click a highlighted ${kind === 'road' ? 'edge' : 'corner'} to build a ${kind}.`, kind: 'info' };
      }
    }
    this.render();
  }

  // ----------------------------------------------------------------- render

  private render() {
    this.root.innerHTML = this.game ? this.gameView(this.game) : this.startView();
    const log = this.root.querySelector('.log-list');
    if (log) log.scrollTop = log.scrollHeight;
  }

  private startView(): string {
    const names = Array.from({ length: this.setupCount }, (_, i) =>
      `<label class="name-row"><span class="swatch" style="background:${PLAYER_COLORS[i]}"></span>
        <input data-bind="name" data-index="${i}" value="${esc(this.setupNames[i])}" maxlength="16"/></label>`,
    ).join('');
    return `
      <div class="start">
        <h1>Catan Lite</h1>
        <p class="sub">Hot-seat Settlers of Catan for 2–4 players on one computer.</p>
        <div class="card">
          <label>Players
            <select data-bind="count">
              ${[2, 3, 4].map((n) => `<option ${n === this.setupCount ? 'selected' : ''}>${n}</option>`).join('')}
            </select>
          </label>
          <div class="names">${names}</div>
          <label>Board seed
            <div class="row"><input data-bind="seed" value="${esc(this.setupSeed)}"/>
            <button class="ghost" data-action="random-seed" title="New random seed">🎲</button></div>
          </label>
          <button class="primary big" data-action="start">Start game</button>
        </div>
      </div>`;
  }

  private highlights(g: Game): BoardHighlights {
    const s = g.state;
    const hl: BoardHighlights = { corners: [], edges: [], hexes: [], color: g.current.color };
    if (s.phase === 'setup-settlement') hl.corners = g.legalSettlementCorners();
    else if (s.phase === 'setup-road') hl.edges = g.legalRoadEdges();
    else if (s.phase === 'move-robber') hl.hexes = s.board.tiles.map((_, i) => i).filter((h) => h !== s.robberHex);
    else if (s.phase === 'main') {
      if (this.mode === 'road') hl.edges = g.legalRoadEdges();
      if (this.mode === 'settlement') hl.corners = g.legalSettlementCorners();
      if (this.mode === 'city') hl.corners = g.legalCityCorners();
    }
    return hl;
  }

  private gameView(g: Game): string {
    const s = g.state;
    return `
      <header>
        <h1>Catan Lite</h1>
        <div class="seed">Seed: <code>${esc(s.board.seed)}</code></div>
        <div class="spacer"></div>
        <button class="ghost" data-action="toggle-debug">${this.debugOpen ? 'Hide' : 'Show'} debug</button>
        <button class="ghost" data-action="new-game">New game</button>
      </header>
      <main>
        <section class="board-wrap">${renderBoard(g, this.highlights(g), this.showIds)}</section>
        <aside>
          ${this.turnView(g)}
          ${this.debugOpen ? this.debugView(g) : ''}
          <div class="players">${s.players.map((_, p) => this.playerView(g, p)).join('')}</div>
          ${this.bankView(g)}
          <div class="card log"><h3>Event log</h3><ol class="log-list">${s.log.map((l) => `<li>${esc(l)}</li>`).join('')}</ol></div>
        </aside>
      </main>
      ${s.phase === 'discard' ? this.discardModal(g) : ''}
      ${s.phase === 'game-over' ? this.winnerModal(g) : ''}`;
  }

  private turnView(g: Game): string {
    const s = g.state;
    const p = g.current;
    const dice = s.dice
      ? `<div class="dice"><span>${DIE_FACES[s.dice[0] - 1]}</span><span>${DIE_FACES[s.dice[1] - 1]}</span><b>${s.dice[0] + s.dice[1]}</b></div>`
      : `<div class="dice muted">Not rolled yet</div>`;
    const hints: Record<string, string> = {
      'setup-settlement': `Click a highlighted corner to place your ${s.setupStep >= s.players.length ? 'second' : 'first'} settlement.`,
      'setup-road': 'Click a highlighted edge next to the settlement you just placed.',
      roll: 'Roll the dice to start your turn.',
      discard: 'Players with more than 7 cards must discard half.',
      'move-robber': 'Click any other hex to move the robber there.',
      steal: 'Choose which player to rob.',
      main: 'Trade with the bank, build, or end your turn.',
      'game-over': 'The game has ended.',
    };
    const msg = this.message
      ? `<div class="msg ${this.message.kind}">${esc(this.message.text)}</div>`
      : `<div class="msg hint">${hints[s.phase]}</div>`;
    return `
      <div class="card turn" style="--pc:${p.color}">
        <div class="turn-head">
          <span class="swatch big" style="background:${p.color}"></span>
          <div><div class="who">${esc(p.name)}</div><div class="phase">${PHASE_LABELS[s.phase]}</div></div>
          ${dice}
        </div>
        ${msg}
        ${this.actionsView(g)}
      </div>`;
  }

  private actionsView(g: Game): string {
    const s = g.state;
    if (g.isSetup || s.phase === 'game-over' || s.phase === 'discard' || s.phase === 'move-robber') return '';
    if (s.phase === 'steal') {
      return `<div class="actions">${s.stealCandidates
        .map((v) => {
          const pl = s.players[v];
          return `<button data-action="steal" data-player="${v}" style="--pc:${pl.color}" class="player-btn">
            Rob ${esc(pl.name)} (${totalCards(pl.resources)} cards)</button>`;
        })
        .join('')}</div>`;
    }
    const inMain = s.phase === 'main';
    // Buttons that can't be used look dimmed but stay clickable so the player gets an explanation.
    const btn = (action: string, label: string, err: string | null, extra = '') =>
      `<button data-action="${action}" ${extra} class="${err ? 'dim' : ''}${this.mode && extra.includes(`"${this.mode}"`) ? ' active' : ''}"
        title="${esc(err ?? '')}">${label}</button>`;
    const buildBtn = (kind: BuildKind, label: string) =>
      btn('build', `${label}<small>${formatCost(COSTS[kind])}</small>`, g.buildError(kind), `data-kind="${kind}"`);
    const opts = (sel: Resource) => RESOURCES.map((r) => `<option value="${r}" ${r === sel ? 'selected' : ''}>${resourceLabel(r)}</option>`).join('');
    return `
      <div class="actions">
        ${s.phase === 'roll' ? `<button class="primary" data-action="roll">🎲 Roll dice</button>` : ''}
        ${buildBtn('road', 'Road')}
        ${buildBtn('settlement', 'Settlement')}
        ${buildBtn('city', 'City')}
        ${this.mode ? `<button class="ghost" data-action="cancel">Cancel</button>` : ''}
      </div>
      <div class="trade">
        <span>Bank 4:1</span>
        <select data-bind="trade-give">${opts(this.tradeGive)}</select>
        <span>→</span>
        <select data-bind="trade-get">${opts(this.tradeGet)}</select>
        ${btn('trade', 'Trade', inMain ? null : 'Roll the dice first.')}
      </div>
      ${inMain ? `<button class="primary end" data-action="end-turn">End turn</button>` : ''}`;
  }

  private playerView(g: Game, p: number): string {
    const s = g.state;
    const pl = s.players[p];
    const isCurrent = p === s.currentPlayer;
    const cards = isCurrent
      ? `<div class="hand">${RESOURCES.map((r) => `<span class="res ${pl.resources[r] ? '' : 'zero'}" title="${r}">${RESOURCE_ICON[r]} ${pl.resources[r]}</span>`).join('')}</div>`
      : '';
    return `
      <div class="card player ${isCurrent ? 'current' : ''}" style="--pc:${pl.color}">
        <div class="player-head">
          <span class="swatch" style="background:${pl.color}"></span>
          <b>${esc(pl.name)}</b>
          ${s.longestRoadHolder === p ? '<span class="badge" title="Longest Road (+2 VP)">🛣️ Longest Road</span>' : ''}
          <span class="vp">${g.victoryPoints(p)} VP</span>
        </div>
        <div class="stats">
          <span title="Resource cards">🃏 ${totalCards(pl.resources)} cards</span>
          <span title="Longest road length">🛣️ ${s.roadLengths[p]}</span>
          <span title="Pieces left: roads / settlements / cities">Left: ${pl.roadsLeft}R · ${pl.settlementsLeft}S · ${pl.citiesLeft}C</span>
        </div>
        ${cards}
      </div>`;
  }

  private bankView(g: Game): string {
    return `<div class="card bank"><b>Bank</b>${RESOURCES.map((r) => `<span title="${r}">${RESOURCE_ICON[r]} ${g.state.bank[r]}</span>`).join('')}</div>`;
  }

  private debugView(g: Game): string {
    const s = g.state;
    const players = s.players.map((pl, i) => `<option value="${i}" ${i === this.debugPlayer ? 'selected' : ''}>${esc(pl.name)}</option>`).join('');
    const resources = RESOURCES.map((r) => `<option value="${r}" ${r === this.debugResource ? 'selected' : ''}>${resourceLabel(r)}</option>`).join('');
    const rolls = Array.from({ length: 11 }, (_, i) => i + 2)
      .map((n) => `<option ${n === this.debugRoll ? 'selected' : ''}>${n}</option>`).join('');
    return `
      <div class="card debug">
        <h3>Debug</h3>
        <div class="row"><span>Seed</span><input data-bind="debug-seed" value="${esc(this.debugSeed)}"/>
          <button data-action="debug-new">New game</button></div>
        <div class="row"><span>Next roll</span><select data-bind="debug-roll">${rolls}</select>
          <button data-action="debug-force">Force</button>
          <button class="ghost" data-action="debug-unforce">Clear</button>
          <em>${s.forcedRoll !== null ? `forced: ${s.forcedRoll}` : 'random'}</em></div>
        <div class="row"><span>Give</span><select data-bind="debug-player">${players}</select>
          <input type="number" min="1" max="19" data-bind="debug-amount" value="${this.debugAmount}" class="num"/>
          <select data-bind="debug-resource">${resources}</select>
          <button data-action="debug-give">Give</button></div>
        <label class="row"><input type="checkbox" data-bind="show-ids" ${this.showIds ? 'checked' : ''}/> Show hex / corner / edge IDs</label>
      </div>`;
  }

  private discardModal(g: Game): string {
    const pending = g.pendingDiscard!;
    const pl = g.state.players[pending.player];
    const picked = totalCards(this.discardPick);
    const rows = RESOURCES.map((r) => `
      <div class="discard-row">
        <span>${resourceLabel(r)}</span>
        <span class="muted">have ${pl.resources[r]}</span>
        <button data-action="discard-dec" data-resource="${r}" ${this.discardPick[r] === 0 ? 'disabled' : ''}>−</button>
        <b>${this.discardPick[r]}</b>
        <button data-action="discard-inc" data-resource="${r}" ${this.discardPick[r] >= pl.resources[r] || picked >= pending.amount ? 'disabled' : ''}>+</button>
      </div>`).join('');
    const err = this.message?.kind === 'error' ? `<div class="msg error">${esc(this.message.text)}</div>` : '';
    return `
      <div class="overlay">
        <div class="modal" style="--pc:${pl.color}">
          <h2><span class="swatch big" style="background:${pl.color}"></span> ${esc(pl.name)}: discard ${pending.amount}</h2>
          <p>A 7 was rolled and you hold ${totalCards(pl.resources)} cards. Choose ${pending.amount} to return to the bank.</p>
          ${rows}
          ${err}
          <button class="primary" data-action="discard-confirm" ${picked === pending.amount ? '' : 'disabled'}>
            Discard ${picked} / ${pending.amount}</button>
        </div>
      </div>`;
  }

  private winnerModal(g: Game): string {
    const s = g.state;
    const winner = s.players[s.winner!];
    const ranking = s.players
      .map((pl) => ({ pl, vp: g.victoryPoints(pl.id) }))
      .sort((a, b) => b.vp - a.vp);
    return `
      <div class="overlay">
        <div class="modal winner" style="--pc:${winner.color}">
          <div class="trophy">🏆</div>
          <h2>${esc(winner.name)} wins!</h2>
          <table>
            <tr><th>Player</th><th>Settlements</th><th>Cities</th><th>Longest Road</th><th>VP</th></tr>
            ${ranking.map(({ pl, vp }) => {
              const settlements = s.buildings.filter((b) => b?.owner === pl.id && b.kind === 'settlement').length;
              const cities = s.buildings.filter((b) => b?.owner === pl.id && b.kind === 'city').length;
              return `<tr><td><span class="swatch" style="background:${pl.color}"></span> ${esc(pl.name)}</td>
                <td>${settlements}</td><td>${cities}</td><td>${s.longestRoadHolder === pl.id ? '✓' : ''} (${s.roadLengths[pl.id]})</td><td><b>${vp}</b></td></tr>`;
            }).join('')}
          </table>
          <button class="primary big" data-action="new-game">New game</button>
        </div>
      </div>`;
  }
}

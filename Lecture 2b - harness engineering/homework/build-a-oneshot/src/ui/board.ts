import { isRedNumber } from '../game/board';
import type { Game } from '../game/game';
import { GEO } from '../game/geometry';
import type { Terrain } from '../game/types';

const S = 64; // hex radius in px
const PAD = 40;

const TERRAIN_STYLE: Record<Terrain, { fill: string; icon: string; label: string }> = {
  forest: { fill: '#3f8a46', icon: '🌲', label: 'Forest (wood)' },
  pasture: { fill: '#9ccc65', icon: '🐑', label: 'Pasture (sheep)' },
  fields: { fill: '#f0c84b', icon: '🌾', label: 'Fields (wheat)' },
  hills: { fill: '#c46a42', icon: '🧱', label: 'Hills (brick)' },
  mountains: { fill: '#8d939c', icon: '⛰️', label: 'Mountains (ore)' },
  desert: { fill: '#e6d6a8', icon: '🏜️', label: 'Desert' },
};

const PIPS: Record<number, number> = { 2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 8: 5, 9: 4, 10: 3, 11: 2, 12: 1 };

const xs = GEO.corners.map((c) => c.x * S);
const ys = GEO.corners.map((c) => c.y * S);
const minX = Math.min(...xs) - PAD;
const minY = Math.min(...ys) - PAD;
const width = Math.max(...xs) - minX + PAD;
const height = Math.max(...ys) - minY + PAD;

const px = (x: number) => (x * S).toFixed(1);
const py = (y: number) => (y * S).toFixed(1);

export interface BoardHighlights {
  corners: number[];
  edges: number[];
  hexes: number[];
  /** Colour of the player who would build on the highlighted spots. */
  color: string;
}

function settlementShape(x: number, y: number, color: string, label: string): string {
  const pts = [[0, -11], [9, -3], [9, 9], [-9, 9], [-9, -3]]
    .map(([dx, dy]) => `${(x + dx).toFixed(1)},${(y + dy).toFixed(1)}`)
    .join(' ');
  return `<polygon class="piece" points="${pts}" fill="${color}"><title>${label}</title></polygon>`;
}

function cityShape(x: number, y: number, color: string, label: string): string {
  const pts = [[-13, 11], [-13, -4], [-6, -12], [1, -4], [1, -1], [13, -1], [13, 11]]
    .map(([dx, dy]) => `${(x + dx).toFixed(1)},${(y + dy).toFixed(1)}`)
    .join(' ');
  return `<polygon class="piece" points="${pts}" fill="${color}"><title>${label}</title></polygon>`;
}

export function renderBoard(game: Game, hl: BoardHighlights, showIds: boolean): string {
  const s = game.state;
  const parts: string[] = [];

  // Hexes
  for (const hex of GEO.hexes) {
    const tile = s.board.tiles[hex.id];
    const style = TERRAIN_STYLE[tile.terrain];
    const pts = hex.corners.map((c) => `${px(GEO.corners[c].x)},${py(GEO.corners[c].y)}`).join(' ');
    const target = hl.hexes.includes(hex.id);
    parts.push(
      `<polygon class="hex${target ? ' robber-target' : ''}" points="${pts}" fill="${style.fill}"` +
        (target ? ` data-action="robber" data-hex="${hex.id}"` : '') +
        `><title>${style.label}${tile.number ? ` — ${tile.number}` : ''} (hex ${hex.id})</title></polygon>`,
    );
    const cx = hex.x * S;
    const cy = hex.y * S;
    parts.push(`<text class="terrain-icon" x="${cx}" y="${cy - 30}">${style.icon}</text>`);
    if (tile.number !== null) {
      const red = isRedNumber(tile.number);
      const pips = PIPS[tile.number];
      parts.push(
        `<g class="token${red ? ' red' : ''}">` +
          `<circle cx="${cx}" cy="${cy}" r="${red ? 20 : 18}"/>` +
          `<text x="${cx}" y="${cy + 1}">${tile.number}</text>` +
          Array.from({ length: pips }, (_, i) =>
            `<circle class="pip" cx="${cx + (i - (pips - 1) / 2) * 4.5}" cy="${cy + 12}" r="1.6"/>`,
          ).join('') +
          `</g>`,
      );
    }
    if (hex.id === s.robberHex) {
      parts.push(
        `<g class="robber" transform="translate(${cx + 30},${cy + 4})">` +
          `<ellipse cx="0" cy="14" rx="10" ry="4"/><path d="M-8,14 Q-9,-2 0,-4 Q9,-2 8,14 Z"/>` +
          `<circle cx="0" cy="-9" r="6"/><title>Robber</title></g>`,
      );
    }
    if (showIds) {
      parts.push(`<text class="debug-id hex-id" x="${cx}" y="${cy + 34}">H${hex.id}</text>`);
    }
  }

  // Roads
  for (const edge of GEO.edges) {
    const owner = s.roads[edge.id];
    if (owner === null) continue;
    const [a, b] = edge.corners.map((c) => GEO.corners[c]);
    const line = `x1="${px(a.x)}" y1="${py(a.y)}" x2="${px(b.x)}" y2="${py(b.y)}"`;
    parts.push(`<line class="road-outline" ${line}/>`);
    parts.push(
      `<line class="road" ${line} stroke="${s.players[owner].color}"><title>${s.players[owner].name}'s road</title></line>`,
    );
  }

  // Legal edges
  for (const e of hl.edges) {
    const [a, b] = GEO.edges[e].corners.map((c) => GEO.corners[c]);
    parts.push(
      `<line class="legal-edge-halo" x1="${px(a.x)}" y1="${py(a.y)}" x2="${px(b.x)}" y2="${py(b.y)}"/>`,
      `<line class="legal-edge" data-action="edge" data-edge="${e}" stroke="${hl.color}" ` +
        `x1="${px(a.x)}" y1="${py(a.y)}" x2="${px(b.x)}" y2="${py(b.y)}"><title>Edge ${e}</title></line>`,
    );
  }

  // Buildings
  for (const corner of GEO.corners) {
    const b = s.buildings[corner.id];
    if (!b) continue;
    const pl = s.players[b.owner];
    const x = corner.x * S;
    const y = corner.y * S;
    parts.push(
      b.kind === 'city'
        ? cityShape(x, y, pl.color, `${pl.name}'s city`)
        : settlementShape(x, y, pl.color, `${pl.name}'s settlement`),
    );
  }

  // Legal corners (drawn on top so city upgrades are clickable over settlements)
  for (const c of hl.corners) {
    const corner = GEO.corners[c];
    parts.push(
      `<circle class="legal-corner" data-action="corner" data-corner="${c}" cx="${px(corner.x)}" cy="${py(corner.y)}" ` +
        `r="11" stroke="${hl.color}"><title>Corner ${c}</title></circle>`,
    );
  }

  if (showIds) {
    for (const edge of GEO.edges) {
      const [a, b] = edge.corners.map((c) => GEO.corners[c]);
      parts.push(
        `<text class="debug-id edge-id" x="${px((a.x + b.x) / 2)}" y="${py((a.y + b.y) / 2)}">e${edge.id}</text>`,
      );
    }
    for (const corner of GEO.corners) {
      parts.push(`<text class="debug-id corner-id" x="${px(corner.x)}" y="${py(corner.y)}">c${corner.id}</text>`);
    }
  }

  return (
    `<svg class="board" viewBox="${minX} ${minY} ${width} ${height}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Catan board">` +
    parts.join('') +
    `</svg>`
  );
}

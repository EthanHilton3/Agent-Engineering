import { terrainResource } from '../engine/resources';
import { TOPOLOGY } from '../engine/topology';
import type { Building, CornerId, EdgeId, GameState, Hex, HexId } from '../engine/types';
import { svg } from './dom';

/** What the board should offer for clicking; the caller gets these lists from the engine's legal-spot queries. */
export interface BoardViewOptions {
  clickableCorners: CornerId[];
  clickableEdges: EdgeId[];
  clickableHexes: HexId[];
  /** Debug: label every hex, corner, and edge with the ID its `data-*` attribute and the engine use. */
  showIds: boolean;
  onCornerClick: (corner: CornerId) => void;
  onEdgeClick: (edge: EdgeId) => void;
  onHexClick: (hex: HexId) => void;
}

/** Renders the board as SVG: terrain, numbers, robber, pieces, and the clickable legal spots. */
export function renderBoard(state: GameState, opts: BoardViewOptions): SVGSVGElement {
  const board = svg('svg', { class: 'board', viewBox: boardViewBox(), role: 'img', 'aria-label': 'Game board' }, [
    svg('g', { class: 'hexes' }, state.board.hexes.map((hex) => renderHex(hex, opts.clickableHexes.includes(hex.id)))),
    renderRobber(state.robberHex),
    svg('g', { class: 'roads' }, renderRoads(state)),
    svg('g', { class: 'edge-targets' }, opts.clickableEdges.map(renderEdgeTarget)),
    svg('g', { class: 'buildings' }, renderBuildings(state)),
    svg('g', { class: 'corner-targets' }, opts.clickableCorners.map(renderCornerTarget)),
    opts.showIds && renderIdLabels(),
  ]);
  board.addEventListener('click', (event) => handleBoardClick(event, opts));
  return board;
}

// Geometry is in the topology's units (hex size 1), so the viewBox does all the scaling.
const BOARD_PADDING = 0.4;
const TOKEN_RADIUS = 0.32;
const ROBBER_OFFSET_Y = 0.56;
const ROBBER_RADIUS = 0.18;
const LABEL_OFFSET_Y = -0.5;
const ROAD_INSET = 0.12; // fraction trimmed off each road end so corners stay visible
const CORNER_TARGET_RADIUS = 0.17;
const BUILDING_SCALE = 0.17;
// Up and left of the number token, clear of the terrain label, the robber, and the edge/corner labels.
const HEX_ID_OFFSET: Point = { x: -0.45, y: -0.28 };
const RED_NUMBERS = [6, 8];

const SETTLEMENT_SHAPE: Point[] = [
  { x: 0, y: -1 },
  { x: 1, y: -0.3 },
  { x: 1, y: 1 },
  { x: -1, y: 1 },
  { x: -1, y: -0.3 },
];
const CITY_SHAPE: Point[] = [
  { x: -1.4, y: 1 },
  { x: 1.4, y: 1 },
  { x: 1.4, y: -0.2 },
  { x: 0.3, y: -0.2 },
  { x: 0.3, y: -0.6 },
  { x: -0.55, y: -1.2 },
  { x: -1.4, y: -0.6 },
];

interface Point {
  x: number;
  y: number;
}

/** Reads the clicked spot's ID from its data attribute, the same attribute that labels it in the DOM. */
function handleBoardClick(event: MouseEvent, opts: BoardViewOptions): void {
  if (!(event.target instanceof Element)) return;
  const target = event.target.closest('.target');
  if (!target) return;
  const corner = target.getAttribute('data-corner');
  if (corner !== null) opts.onCornerClick(Number(corner));
  const edge = target.getAttribute('data-edge');
  if (edge !== null) opts.onEdgeClick(Number(edge));
  const hex = target.getAttribute('data-hex');
  if (hex !== null) opts.onHexClick(Number(hex));
}

function boardViewBox(): string {
  const xs = TOPOLOGY.cornerPositions.map((p) => p.x);
  const ys = TOPOLOGY.cornerPositions.map((p) => p.y);
  const minX = Math.min(...xs) - BOARD_PADDING;
  const minY = Math.min(...ys) - BOARD_PADDING;
  const width = Math.max(...xs) + BOARD_PADDING - minX;
  const height = Math.max(...ys) + BOARD_PADDING - minY;
  return [minX, minY, width, height].map((n) => n.toFixed(3)).join(' ');
}

function renderHex(hex: Hex, clickable: boolean): SVGGElement {
  const center = hexCenter(hex.id);
  const targetClass = clickable ? ' target hex-target' : '';
  return svg('g', { class: `hex terrain-${hex.terrain}${targetClass}`, 'data-hex': hex.id }, [
    svg('polygon', { class: 'hex-shape', points: pointsAttr(TOPOLOGY.hexCorners[hex.id].map(cornerPoint)) }),
    svg('text', { class: 'terrain-label', x: center.x, y: center.y + LABEL_OFFSET_Y }, [terrainLabel(hex)]),
    hex.number !== null && renderNumberToken(hex.number, center),
  ]);
}

function renderNumberToken(value: number, center: Point): SVGGElement {
  const emphasis = RED_NUMBERS.includes(value) ? ' red-number' : '';
  return svg('g', { class: `number-token${emphasis}` }, [
    svg('circle', { cx: center.x, cy: center.y, r: TOKEN_RADIUS }),
    svg('text', { x: center.x, y: center.y }, [String(value)]),
  ]);
}

function renderRobber(hex: HexId): SVGGElement {
  const center = hexCenter(hex);
  return svg('g', { class: 'robber' }, [
    svg('circle', { cx: center.x, cy: center.y + ROBBER_OFFSET_Y, r: ROBBER_RADIUS }),
    svg('text', { x: center.x, y: center.y + ROBBER_OFFSET_Y }, ['R']),
    svg('title', {}, ['Robber']),
  ]);
}

function renderRoads(state: GameState): SVGLineElement[] {
  const roads: SVGLineElement[] = [];
  state.roads.forEach((owner, edge) => {
    if (owner === null) return;
    const line = edgeLine(edge, 'road');
    line.setAttribute('stroke', state.players[owner].color);
    roads.push(line);
  });
  return roads;
}

function renderEdgeTarget(edge: EdgeId): SVGLineElement {
  const line = edgeLine(edge, 'target edge-target');
  line.setAttribute('data-edge', String(edge));
  return line;
}

function edgeLine(edge: EdgeId, className: string): SVGLineElement {
  const [a, b] = TOPOLOGY.edgeCorners[edge].map(cornerPoint);
  const start = lerp(a, b, ROAD_INSET);
  const end = lerp(a, b, 1 - ROAD_INSET);
  return svg('line', { class: className, x1: start.x, y1: start.y, x2: end.x, y2: end.y });
}

function renderBuildings(state: GameState): SVGPolygonElement[] {
  const buildings: SVGPolygonElement[] = [];
  state.buildings.forEach((building, corner) => {
    if (building) buildings.push(renderBuilding(building, corner, state.players[building.owner].color));
  });
  return buildings;
}

function renderBuilding(building: Building, corner: CornerId, color: string): SVGPolygonElement {
  const shape = building.kind === 'city' ? CITY_SHAPE : SETTLEMENT_SHAPE;
  const center = cornerPoint(corner);
  const points = shape.map((p) => ({ x: center.x + p.x * BUILDING_SCALE, y: center.y + p.y * BUILDING_SCALE }));
  return svg('polygon', { class: `building ${building.kind}`, points: pointsAttr(points), fill: color });
}

function renderCornerTarget(corner: CornerId): SVGCircleElement {
  const center = cornerPoint(corner);
  return svg('circle', {
    class: 'target corner-target',
    'data-corner': corner,
    cx: center.x,
    cy: center.y,
    r: CORNER_TARGET_RADIUS,
  });
}

/** Hex IDs ("H9") near the number token, corner IDs ("C12") on corners, edge IDs ("E40") on edge midpoints. */
function renderIdLabels(): SVGGElement {
  const hexLabels = TOPOLOGY.hexCoords.map((_, hex) => {
    const center = hexCenter(hex);
    return idLabel('hex-id', `H${hex}`, { x: center.x + HEX_ID_OFFSET.x, y: center.y + HEX_ID_OFFSET.y });
  });
  const edgeLabels = TOPOLOGY.edgeCorners.map(([a, b], edge) =>
    idLabel('edge-id', `E${edge}`, lerp(cornerPoint(a), cornerPoint(b), 0.5)),
  );
  const cornerLabels = TOPOLOGY.cornerPositions.map((point, corner) => idLabel('corner-id', `C${corner}`, point));
  return svg('g', { class: 'id-labels' }, [...hexLabels, ...edgeLabels, ...cornerLabels]);
}

function idLabel(kind: string, text: string, at: Point): SVGTextElement {
  return svg('text', { class: `id-label ${kind}`, x: at.x, y: at.y }, [text]);
}

function terrainLabel(hex: Hex): string {
  return terrainResource(hex.terrain) ?? hex.terrain;
}

function hexCenter(hex: HexId): Point {
  const corners = TOPOLOGY.hexCorners[hex].map(cornerPoint);
  return {
    x: corners.reduce((sum, p) => sum + p.x, 0) / corners.length,
    y: corners.reduce((sum, p) => sum + p.y, 0) / corners.length,
  };
}

function cornerPoint(corner: CornerId): Point {
  return TOPOLOGY.cornerPositions[corner];
}

function lerp(a: Point, b: Point, t: number): Point {
  return { x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t };
}

function pointsAttr(points: Point[]): string {
  return points.map((p) => `${p.x.toFixed(3)},${p.y.toFixed(3)}`).join(' ');
}

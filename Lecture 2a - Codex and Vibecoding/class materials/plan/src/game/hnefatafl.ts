export const BOARD_SIZE = 11;

export type Side = "attackers" | "defenders";
export type PieceType = "attacker" | "defender" | "king";

export interface Piece {
  type: PieceType;
  side: Side;
}

export interface Position {
  row: number;
  col: number;
}

export interface Move {
  from: Position;
  to: Position;
}

export interface GameState {
  board: (Piece | null)[][];
  currentTurn: Side;
  winner: Side | null;
  moveCount: number;
  lastMove: Move | null;
}

const THRONE: Position = { row: 5, col: 5 };
const CORNERS: Position[] = [
  { row: 0, col: 0 },
  { row: 0, col: 10 },
  { row: 10, col: 0 },
  { row: 10, col: 10 },
];

const ATTACKER_STARTS: Position[] = [
  { row: 0, col: 3 },
  { row: 0, col: 4 },
  { row: 0, col: 5 },
  { row: 0, col: 6 },
  { row: 0, col: 7 },
  { row: 1, col: 5 },
  { row: 3, col: 0 },
  { row: 4, col: 0 },
  { row: 5, col: 0 },
  { row: 6, col: 0 },
  { row: 7, col: 0 },
  { row: 5, col: 1 },
  { row: 3, col: 10 },
  { row: 4, col: 10 },
  { row: 5, col: 10 },
  { row: 6, col: 10 },
  { row: 7, col: 10 },
  { row: 5, col: 9 },
  { row: 10, col: 3 },
  { row: 10, col: 4 },
  { row: 10, col: 5 },
  { row: 10, col: 6 },
  { row: 10, col: 7 },
  { row: 9, col: 5 },
];

const DEFENDER_STARTS: Position[] = [
  { row: 5, col: 3 },
  { row: 5, col: 4 },
  { row: 5, col: 6 },
  { row: 5, col: 7 },
  { row: 3, col: 5 },
  { row: 4, col: 5 },
  { row: 6, col: 5 },
  { row: 7, col: 5 },
  { row: 4, col: 4 },
  { row: 4, col: 6 },
  { row: 6, col: 4 },
  { row: 6, col: 6 },
];

const DIRECTIONS: Position[] = [
  { row: -1, col: 0 },
  { row: 1, col: 0 },
  { row: 0, col: -1 },
  { row: 0, col: 1 },
];

export function createInitialGameState(): GameState {
  const board = Array.from({ length: BOARD_SIZE }, () =>
    Array.from({ length: BOARD_SIZE }, () => null as Piece | null),
  );

  for (const position of ATTACKER_STARTS) {
    board[position.row][position.col] = { type: "attacker", side: "attackers" };
  }

  for (const position of DEFENDER_STARTS) {
    board[position.row][position.col] = { type: "defender", side: "defenders" };
  }

  board[THRONE.row][THRONE.col] = { type: "king", side: "defenders" };

  return {
    board,
    currentTurn: "attackers",
    winner: null,
    moveCount: 0,
    lastMove: null,
  };
}

export function cloneGameState(state: GameState): GameState {
  return {
    ...state,
    board: state.board.map((row) => row.map((piece) => (piece ? { ...piece } : null))),
    lastMove: state.lastMove
      ? { from: { ...state.lastMove.from }, to: { ...state.lastMove.to } }
      : null,
  };
}

export function getLegalMoves(state: GameState, from: Position): Position[] {
  const piece = getPiece(state, from);
  if (!piece || state.winner || piece.side !== state.currentTurn) {
    return [];
  }

  const legalMoves: Position[] = [];

  for (const direction of DIRECTIONS) {
    let row = from.row + direction.row;
    let col = from.col + direction.col;

    while (isWithinBoard({ row, col })) {
      if (state.board[row][col]) {
        break;
      }

      if (isRestrictedSquare({ row, col }) && piece.type !== "king") {
        break;
      }

      legalMoves.push({ row, col });
      row += direction.row;
      col += direction.col;
    }
  }

  return legalMoves;
}

export function applyMove(state: GameState, from: Position, to: Position): GameState {
  const legalMoves = getLegalMoves(state, from);
  if (!legalMoves.some((move) => samePosition(move, to))) {
    return state;
  }

  const nextState = cloneGameState(state);
  const movingPiece = nextState.board[from.row][from.col];
  nextState.board[from.row][from.col] = null;
  nextState.board[to.row][to.col] = movingPiece;
  nextState.moveCount += 1;
  nextState.lastMove = { from: { ...from }, to: { ...to } };

  resolveCaptures(nextState, to);
  nextState.winner = getWinner(nextState);
  if (!nextState.winner) {
    nextState.currentTurn = state.currentTurn === "attackers" ? "defenders" : "attackers";
  }

  return nextState;
}

export function getWinner(state: GameState): Side | null {
  const kingPosition = findKing(state);
  if (!kingPosition) {
    return "attackers";
  }

  if (isCorner(kingPosition)) {
    return "defenders";
  }

  return null;
}

export function getGameStatus(state: GameState): string {
  if (state.winner === "attackers") {
    return "Attackers win by surrounding the king.";
  }
  if (state.winner === "defenders") {
    return "Defenders win by guiding the king to a corner.";
  }
  return state.currentTurn === "attackers" ? "Attackers to move." : "Defenders to move.";
}

export function getPiece(state: GameState, position: Position): Piece | null {
  if (!isWithinBoard(position)) {
    return null;
  }
  return state.board[position.row][position.col];
}

export function isRestrictedSquare(position: Position): boolean {
  return isThrone(position) || isCorner(position);
}

export function isThrone(position: Position): boolean {
  return samePosition(position, THRONE);
}

export function isCorner(position: Position): boolean {
  return CORNERS.some((corner) => samePosition(corner, position));
}

function findKing(state: GameState): Position | null {
  for (let row = 0; row < BOARD_SIZE; row += 1) {
    for (let col = 0; col < BOARD_SIZE; col += 1) {
      if (state.board[row][col]?.type === "king") {
        return { row, col };
      }
    }
  }
  return null;
}

function resolveCaptures(state: GameState, movedTo: Position): void {
  const movingPiece = getPiece(state, movedTo);
  if (!movingPiece) {
    return;
  }

  for (const direction of DIRECTIONS) {
    const target = {
      row: movedTo.row + direction.row,
      col: movedTo.col + direction.col,
    };
    const opposite = {
      row: target.row + direction.row,
      col: target.col + direction.col,
    };
    const targetPiece = getPiece(state, target);

    if (!targetPiece || targetPiece.side === movingPiece.side) {
      continue;
    }

    if (targetPiece.type === "king") {
      if (isKingCaptured(state, target)) {
        state.board[target.row][target.col] = null;
      }
      continue;
    }

    if (isCaptureSupport(state, opposite, movingPiece.side)) {
      state.board[target.row][target.col] = null;
    }
  }
}

function isKingCaptured(state: GameState, kingPosition: Position): boolean {
  return DIRECTIONS.every((direction) => {
    const adjacent = {
      row: kingPosition.row + direction.row,
      col: kingPosition.col + direction.col,
    };
    if (!isWithinBoard(adjacent)) {
      return false;
    }

    const piece = getPiece(state, adjacent);
    if (piece?.side === "attackers") {
      return true;
    }

    return isHostileSquare(state, adjacent, "defenders");
  });
}

function isCaptureSupport(state: GameState, position: Position, capturingSide: Side): boolean {
  if (!isWithinBoard(position)) {
    return false;
  }

  const piece = getPiece(state, position);
  if (piece?.side === capturingSide) {
    return true;
  }

  const enemySide = capturingSide === "attackers" ? "defenders" : "attackers";
  return isHostileSquare(state, position, enemySide);
}

function isHostileSquare(state: GameState, position: Position, targetSide: Side): boolean {
  if (isCorner(position)) {
    return true;
  }

  if (!isThrone(position)) {
    return false;
  }

  const throneOccupant = getPiece(state, position);
  if (!throneOccupant) {
    return true;
  }

  return throneOccupant.side !== targetSide;
}

function isWithinBoard(position: Position): boolean {
  return (
    position.row >= 0 &&
    position.row < BOARD_SIZE &&
    position.col >= 0 &&
    position.col < BOARD_SIZE
  );
}

function samePosition(a: Position, b: Position): boolean {
  return a.row === b.row && a.col === b.col;
}

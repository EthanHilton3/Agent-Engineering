const BOARD_SIZE = 11;
const THRONE = { row: 5, col: 5 };
const REFUGES = new Set(["0,0", "0,10", "10,0", "10,10"]);
const DIRS = [
  [1, 0],
  [-1, 0],
  [0, 1],
  [0, -1],
];

const initialAttackers = [
  [0, 3], [0, 4], [0, 5], [0, 6], [0, 7],
  [1, 5],
  [3, 0], [4, 0], [5, 0], [6, 0], [7, 0],
  [5, 1],
  [10, 3], [10, 4], [10, 5], [10, 6], [10, 7],
  [9, 5],
  [3, 10], [4, 10], [5, 10], [6, 10], [7, 10],
  [5, 9],
];

const initialDefenders = [
  [5, 3], [5, 4], [5, 6], [5, 7],
  [3, 5], [4, 5], [6, 5], [7, 5],
  [4, 4], [4, 6], [6, 4], [6, 6],
];

const boardEl = document.getElementById("board");
const turnLabelEl = document.getElementById("turn-label");
const statusTextEl = document.getElementById("status-text");
const selectionTextEl = document.getElementById("selection-text");
const moveHistoryEl = document.getElementById("move-history");
const historyCountEl = document.getElementById("history-count");
const attackerCountEl = document.getElementById("attacker-count");
const defenderCountEl = document.getElementById("defender-count");
const resetButtonEl = document.getElementById("reset-button");

const state = {
  board: [],
  currentPlayer: "attackers",
  selected: null,
  validMoves: [],
  moveHistory: [],
  winner: null,
  lastMove: null,
};

function createEmptyBoard() {
  return Array.from({ length: BOARD_SIZE }, () => Array(BOARD_SIZE).fill(null));
}

function createInitialBoard() {
  const board = createEmptyBoard();

  for (const [row, col] of initialAttackers) {
    board[row][col] = { type: "attacker", side: "attackers" };
  }

  for (const [row, col] of initialDefenders) {
    board[row][col] = { type: "defender", side: "defenders" };
  }

  board[THRONE.row][THRONE.col] = { type: "king", side: "defenders" };
  return board;
}

function resetGame() {
  state.board = createInitialBoard();
  state.currentPlayer = "attackers";
  state.selected = null;
  state.validMoves = [];
  state.moveHistory = [];
  state.winner = null;
  state.lastMove = null;
  render();
}

function coordKey(row, col) {
  return `${row},${col}`;
}

function isInBounds(row, col) {
  return row >= 0 && row < BOARD_SIZE && col >= 0 && col < BOARD_SIZE;
}

function isRefuge(row, col) {
  return REFUGES.has(coordKey(row, col));
}

function isThrone(row, col) {
  return row === THRONE.row && col === THRONE.col;
}

function isSpecialCell(row, col) {
  return isRefuge(row, col) || isThrone(row, col);
}

function isHostileSquare(row, col, piece) {
  if (!isInBounds(row, col)) {
    return false;
  }

  if (!isSpecialCell(row, col)) {
    return false;
  }

  if (piece.type === "king") {
    return false;
  }

  return true;
}

function belongsToCurrentPlayer(piece) {
  return piece && piece.side === state.currentPlayer;
}

function getPieceLabel(piece) {
  if (!piece) return "None";
  if (piece.type === "king") return "King";
  return piece.type === "attacker" ? "Attacker" : "Defender";
}

function getCellName(row, col) {
  return `${String.fromCharCode(65 + col)}${row + 1}`;
}

function computeValidMoves(row, col) {
  const piece = state.board[row][col];
  if (!piece) return [];

  const moves = [];

  for (const [dRow, dCol] of DIRS) {
    let nextRow = row + dRow;
    let nextCol = col + dCol;

    while (isInBounds(nextRow, nextCol) && !state.board[nextRow][nextCol]) {
      const blockedBySpecial = isSpecialCell(nextRow, nextCol) && piece.type !== "king";
      if (blockedBySpecial) {
        break;
      }

      moves.push({ row: nextRow, col: nextCol });
      nextRow += dRow;
      nextCol += dCol;
    }
  }

  return moves;
}

function handleCellClick(row, col) {
  if (state.winner) {
    return;
  }

  const clickedPiece = state.board[row][col];
  const clickedMove = state.validMoves.find((move) => move.row === row && move.col === col);

  if (clickedMove && state.selected) {
    movePiece(state.selected.row, state.selected.col, row, col);
    return;
  }

  if (belongsToCurrentPlayer(clickedPiece)) {
    state.selected = { row, col };
    state.validMoves = computeValidMoves(row, col);
  } else {
    state.selected = null;
    state.validMoves = [];
  }

  render();
}

function movePiece(fromRow, fromCol, toRow, toCol) {
  const piece = state.board[fromRow][fromCol];
  state.board[toRow][toCol] = piece;
  state.board[fromRow][fromCol] = null;
  state.lastMove = {
    from: { row: fromRow, col: fromCol },
    to: { row: toRow, col: toCol },
  };

  const captures = resolveCaptures(toRow, toCol);
  const winner = determineWinner(toRow, toCol);

  const moveText = `${state.currentPlayer === "attackers" ? "Attackers" : "Defenders"}: ${getPieceLabel(piece)} ${getCellName(fromRow, fromCol)} to ${getCellName(toRow, toCol)}${captures.length ? `, captured ${captures.length}` : ""}`;
  state.moveHistory.unshift(moveText);

  state.selected = null;
  state.validMoves = [];

  if (winner) {
    state.winner = winner;
  } else {
    state.currentPlayer = state.currentPlayer === "attackers" ? "defenders" : "attackers";
  }

  render();
}

function resolveCaptures(row, col) {
  const mover = state.board[row][col];
  const captured = [];

  for (const [dRow, dCol] of DIRS) {
    const enemyRow = row + dRow;
    const enemyCol = col + dCol;

    if (!isInBounds(enemyRow, enemyCol)) {
      continue;
    }

    const enemy = state.board[enemyRow][enemyCol];
    if (!enemy || enemy.side === mover.side || enemy.type === "king") {
      continue;
    }

    const supportRow = enemyRow + dRow;
    const supportCol = enemyCol + dCol;
    const supportPiece = isInBounds(supportRow, supportCol) ? state.board[supportRow][supportCol] : null;
    const supportedByAlly = supportPiece && supportPiece.side === mover.side;
    const supportedByHostileSquare = isHostileSquare(supportRow, supportCol, enemy);

    if (supportedByAlly || supportedByHostileSquare) {
      state.board[enemyRow][enemyCol] = null;
      captured.push({ row: enemyRow, col: enemyCol, piece: enemy });
    }
  }

  return captured;
}

function findKing() {
  for (let row = 0; row < BOARD_SIZE; row += 1) {
    for (let col = 0; col < BOARD_SIZE; col += 1) {
      const piece = state.board[row][col];
      if (piece?.type === "king") {
        return { row, col };
      }
    }
  }

  return null;
}

function determineWinner(lastRow, lastCol) {
  const movedPiece = state.board[lastRow][lastCol];

  if (movedPiece?.type === "king" && isRefuge(lastRow, lastCol)) {
    return "defenders";
  }

  const kingPos = findKing();
  if (!kingPos) {
    return "attackers";
  }

  const surrounded = DIRS.every(([dRow, dCol]) => {
    const row = kingPos.row + dRow;
    const col = kingPos.col + dCol;

    if (!isInBounds(row, col)) {
      return false;
    }

    const occupant = state.board[row][col];
    if (occupant?.side === "attackers") {
      return true;
    }

    return isSpecialCell(row, col);
  });

  return surrounded ? "attackers" : null;
}

function getCounts() {
  let attackers = 0;
  let defenders = 0;

  for (const row of state.board) {
    for (const piece of row) {
      if (!piece) continue;
      if (piece.type === "attacker") attackers += 1;
      if (piece.type === "defender" || piece.type === "king") defenders += 1;
    }
  }

  return { attackers, defenders };
}

function renderBoard() {
  boardEl.innerHTML = "";

  for (let row = 0; row < BOARD_SIZE; row += 1) {
    for (let col = 0; col < BOARD_SIZE; col += 1) {
      const cell = document.createElement("button");
      cell.type = "button";
      cell.className = "cell";
      cell.setAttribute("aria-label", `${getCellName(row, col)}`);

      if ((row + col) % 2 === 1) {
        cell.classList.add("dark");
      }

      if (isRefuge(row, col)) {
        cell.classList.add("refuge");
      } else if (isThrone(row, col)) {
        cell.classList.add("throne");
      }

      if (state.selected?.row === row && state.selected?.col === col) {
        cell.classList.add("selected");
      }

      if (state.validMoves.some((move) => move.row === row && move.col === col)) {
        cell.classList.add("valid-move");
      }

      if (
        state.lastMove &&
        ((state.lastMove.from.row === row && state.lastMove.from.col === col) ||
          (state.lastMove.to.row === row && state.lastMove.to.col === col))
      ) {
        cell.classList.add("last-move");
      }

      const piece = state.board[row][col];
      if (piece) {
        const pieceEl = document.createElement("div");
        pieceEl.className = `piece ${piece.type}`;
        pieceEl.textContent = piece.type === "king" ? "K" : piece.type === "attacker" ? "A" : "D";
        cell.appendChild(pieceEl);
      }

      cell.addEventListener("click", () => handleCellClick(row, col));
      boardEl.appendChild(cell);
    }
  }
}

function renderStatus() {
  const counts = getCounts();
  attackerCountEl.textContent = counts.attackers;
  defenderCountEl.textContent = counts.defenders;

  if (state.winner) {
    turnLabelEl.textContent = state.winner === "attackers" ? "Attackers win" : "Defenders win";
    statusTextEl.textContent =
      state.winner === "attackers"
        ? "The king has been surrounded. Reset to start a new raid."
        : "The king escaped to a refuge corner. Reset to play again.";
  } else {
    turnLabelEl.textContent = state.currentPlayer === "attackers" ? "Attackers to move" : "Defenders to move";
    statusTextEl.textContent =
      state.currentPlayer === "attackers"
        ? "Attackers move first. Control lanes and choke the king."
        : "Defenders must carve a route to a corner refuge.";
  }

  if (state.selected) {
    const piece = state.board[state.selected.row][state.selected.col];
    selectionTextEl.textContent = `${getPieceLabel(piece)} on ${getCellName(state.selected.row, state.selected.col)} with ${state.validMoves.length} legal move${state.validMoves.length === 1 ? "" : "s"}.`;
  } else {
    selectionTextEl.textContent = "None";
  }
}

function renderHistory() {
  moveHistoryEl.innerHTML = "";
  historyCountEl.textContent = `${state.moveHistory.length} move${state.moveHistory.length === 1 ? "" : "s"}`;

  for (const entry of state.moveHistory) {
    const item = document.createElement("li");
    item.textContent = entry;
    moveHistoryEl.appendChild(item);
  }
}

function render() {
  renderBoard();
  renderStatus();
  renderHistory();
}

resetButtonEl.addEventListener("click", resetGame);

resetGame();

import { useState } from "react";
import {
  BOARD_SIZE,
  applyMove,
  createInitialGameState,
  getGameStatus,
  getLegalMoves,
  getPiece,
  isCorner,
  isThrone,
  type GameState,
  type Position,
} from "./game/hnefatafl";

const columnLabels = "ABCDEFGHIJK".split("");

function App() {
  const [gameState, setGameState] = useState<GameState>(() => createInitialGameState());
  const [selected, setSelected] = useState<Position | null>(null);

  const legalMoves = selected ? getLegalMoves(gameState, selected) : [];

  function handleSquareClick(position: Position) {
    if (gameState.winner) {
      return;
    }

    const clickedPiece = getPiece(gameState, position);
    const isLegalMove = legalMoves.some(
      (move) => move.row === position.row && move.col === position.col,
    );

    if (selected && isLegalMove) {
      setGameState((current) => applyMove(current, selected, position));
      setSelected(null);
      return;
    }

    if (clickedPiece && clickedPiece.side === gameState.currentTurn) {
      setSelected(position);
      return;
    }

    setSelected(null);
  }

  function handleRestart() {
    setGameState(createInitialGameState());
    setSelected(null);
  }

  return (
    <main className="app-shell">
      <section className="hero">
        <p className="eyebrow">Viking Chess</p>
        <h1>Hnefatafl</h1>
        <p className="hero-copy">
          One board, two local players, and a king trying to break through the siege.
        </p>
      </section>

      <section className="game-layout">
        <div className="board-panel">
          <div className="board-frame" role="application" aria-label="Hnefatafl board">
            <div
              className="board"
              style={{ gridTemplateColumns: `auto repeat(${BOARD_SIZE}, 1fr)` }}
            >
              <div className="corner-label spacer" />
              {columnLabels.map((label) => (
                <div className="axis-label" key={label}>
                  {label}
                </div>
              ))}

              {Array.from({ length: BOARD_SIZE }, (_, row) => (
                <BoardRow
                  key={row}
                  gameState={gameState}
                  legalMoves={legalMoves}
                  onSquareClick={handleSquareClick}
                  row={row}
                  selected={selected}
                />
              ))}
            </div>
          </div>
        </div>

        <aside className="sidebar">
          <div className="status-card">
            <p className="status-label">Status</p>
            <p className="status-text">{getGameStatus(gameState)}</p>
            <p className="turn-pill">{gameState.currentTurn}</p>
          </div>

          <div className="status-card">
            <p className="status-label">Match</p>
            <p>Move {gameState.moveCount + 1}</p>
            <p>
              Goal: defenders escort the king to a corner while attackers close the net.
            </p>
          </div>

          <button className="restart-button" onClick={handleRestart} type="button">
            Restart match
          </button>
        </aside>
      </section>
    </main>
  );
}

interface BoardRowProps {
  gameState: GameState;
  legalMoves: Position[];
  onSquareClick: (position: Position) => void;
  row: number;
  selected: Position | null;
}

function BoardRow({ gameState, legalMoves, onSquareClick, row, selected }: BoardRowProps) {
  return (
    <>
      <div className="axis-label">{BOARD_SIZE - row}</div>
      {Array.from({ length: BOARD_SIZE }, (_, col) => {
        const position = { row, col };
        const piece = getPiece(gameState, position);
        const isSelected = Boolean(
          selected && selected.row === position.row && selected.col === position.col,
        );
        const isLegalMove = legalMoves.some(
          (move) => move.row === position.row && move.col === position.col,
        );
        const squareClasses = [
          "square",
          isThrone(position) ? "square-throne" : "",
          isCorner(position) ? "square-corner" : "",
          isSelected ? "is-selected" : "",
          isLegalMove ? "is-legal" : "",
        ]
          .filter(Boolean)
          .join(" ");

        return (
          <button
            aria-label={`Row ${BOARD_SIZE - row} Column ${columnLabels[col]}`}
            className={squareClasses}
            key={`${row}-${col}`}
            onClick={() => onSquareClick(position)}
            type="button"
          >
            {piece ? <PieceGlyph type={piece.type} /> : null}
          </button>
        );
      })}
    </>
  );
}

function PieceGlyph({ type }: { type: "attacker" | "defender" | "king" }) {
  const label = type === "attacker" ? "A" : type === "defender" ? "D" : "K";
  return <span className={`piece piece-${type}`}>{label}</span>;
}

export default App;

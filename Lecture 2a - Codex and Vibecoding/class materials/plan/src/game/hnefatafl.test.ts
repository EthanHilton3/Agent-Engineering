import {
  applyMove,
  createInitialGameState,
  getLegalMoves,
  getPiece,
  getWinner,
  type GameState,
} from "./hnefatafl";

function emptyState(): GameState {
  const state = createInitialGameState();
  state.board = state.board.map((row) => row.map(() => null));
  state.currentTurn = "attackers";
  state.winner = null;
  state.moveCount = 0;
  state.lastMove = null;
  return state;
}

describe("hnefatafl rules", () => {
  it("starts with attackers to move and the king on the throne", () => {
    const state = createInitialGameState();

    expect(state.currentTurn).toBe("attackers");
    expect(getPiece(state, { row: 5, col: 5 })?.type).toBe("king");
  });

  it("prevents non-king pieces from entering the throne or corners", () => {
    const throneState = emptyState();
    throneState.board[5][2] = { type: "attacker", side: "attackers" };

    const throneMoves = getLegalMoves(throneState, { row: 5, col: 2 });

    expect(throneMoves).not.toContainEqual({ row: 5, col: 5 });

    const cornerState = emptyState();
    cornerState.board[0][2] = { type: "attacker", side: "attackers" };

    const cornerMoves = getLegalMoves(cornerState, { row: 0, col: 2 });

    expect(cornerMoves).not.toContainEqual({ row: 0, col: 0 });
  });

  it("allows the king to move to a corner and win", () => {
    const state = emptyState();
    state.currentTurn = "defenders";
    state.board[0][5] = { type: "king", side: "defenders" };

    const moved = applyMove(state, { row: 0, col: 5 }, { row: 0, col: 0 });

    expect(getWinner(moved)).toBe("defenders");
    expect(moved.winner).toBe("defenders");
  });

  it("captures a defender by sandwiching it between attackers", () => {
    const state = emptyState();
    state.board[4][3] = { type: "attacker", side: "attackers" };
    state.board[4][4] = { type: "defender", side: "defenders" };
    state.board[1][5] = { type: "attacker", side: "attackers" };

    const moved = applyMove(state, { row: 1, col: 5 }, { row: 4, col: 5 });

    expect(getPiece(moved, { row: 4, col: 4 })).toBeNull();
  });

  it("captures the king when surrounded on all four sides", () => {
    const state = emptyState();
    state.board[5][5] = { type: "king", side: "defenders" };
    state.board[4][5] = { type: "attacker", side: "attackers" };
    state.board[5][4] = { type: "attacker", side: "attackers" };
    state.board[5][6] = { type: "attacker", side: "attackers" };
    state.board[7][5] = { type: "attacker", side: "attackers" };

    const moved = applyMove(state, { row: 7, col: 5 }, { row: 6, col: 5 });

    expect(getPiece(moved, { row: 5, col: 5 })).toBeNull();
    expect(moved.winner).toBe("attackers");
  });

  it("switches turns after a successful move", () => {
    const state = createInitialGameState();

    const moved = applyMove(state, { row: 0, col: 3 }, { row: 2, col: 3 });

    expect(moved.currentTurn).toBe("defenders");
    expect(moved.moveCount).toBe(1);
  });
});

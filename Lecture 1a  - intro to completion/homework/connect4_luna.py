"""A small, colorful command-line Connect Four game.

Run with: python connect4_luna.py
"""

from __future__ import annotations

import os
import sys
from typing import Optional

ROWS, COLUMNS = 6, 7
EMPTY = " "
RED = "\033[91m"
YELLOW = "\033[93m"
DIM = "\033[2m"
RESET = "\033[0m"


def clear_screen() -> None:
    """Clear the terminal, when possible."""
    os.system("cls" if os.name == "nt" else "clear")


def make_board() -> list[list[str]]:
    return [[EMPTY for _ in range(COLUMNS)] for _ in range(ROWS)]


def draw_board(board: list[list[str]], message: str = "") -> None:
    """Print a simple Connect Four board using colored discs."""
    print("\n        CONNECT 4")
    print("     " + "   ".join(str(n) for n in range(1, COLUMNS + 1)))
    print("   [36m+---+---+---+---+---+---+---+[0m")
    for row in board:
        cells = []
        for cell in row:
            if cell == "R":
                cells.append(f"{RED}[1m●{RESET}")
            elif cell == "Y":
                cells.append(f"{YELLOW}[1m●{RESET}")
            else:
                cells.append(" ")
        print("   [36m|[0m " + " | ".join(cells) + " [36m|[0m")
        print("   [36m+---+---+---+---+---+---+---+[0m")
    if message:
        print(f"\n{message}")


def drop(board: list[list[str]], column: int, piece: str) -> Optional[tuple[int, int]]:
    """Drop a piece into a zero-based column and return its position."""
    for row in range(ROWS - 1, -1, -1):
        if board[row][column] == EMPTY:
            board[row][column] = piece
            return row, column
    return None


def has_won(board: list[list[str]], piece: str) -> bool:
    """Return whether piece has four connected discs."""
    directions = ((0, 1), (1, 0), (1, 1), (1, -1))
    for row in range(ROWS):
        for column in range(COLUMNS):
            if board[row][column] != piece:
                continue
            for row_step, column_step in directions:
                if all(
                    0 <= row + row_step * i < ROWS
                    and 0 <= column + column_step * i < COLUMNS
                    and board[row + row_step * i][column + column_step * i] == piece
                    for i in range(4)
                ):
                    return True
    return False


def board_full(board: list[list[str]]) -> bool:
    return all(board[0][column] != EMPTY for column in range(COLUMNS))


def play() -> None:
    board = make_board()
    names = {"R": "Red", "Y": "Yellow"}
    piece = "R"

    while True:
        clear_screen()
        draw_board(board, f"{names[piece]}'s turn ({piece}). Choose 1-7, or q to quit.")
        choice = input("\n  Column: ").strip().lower()
        if choice in {"q", "quit", "exit"}:
            print("Goodbye!")
            return
        if not choice.isdigit() or not 1 <= int(choice) <= COLUMNS:
            input("  Please enter a column from 1 to 7. Press Enter...")
            continue

        column = int(choice) - 1
        if drop(board, column, piece) is None:
            input("  That column is full. Press Enter to choose another...")
            continue
        if has_won(board, piece):
            clear_screen()
            draw_board(board, f"{names[piece]} wins! Four in a row!")
            break
        if board_full(board):
            clear_screen()
            draw_board(board, "It's a draw! The board is full.")
            break
        piece = "Y" if piece == "R" else "R"

    input("\n  Press Enter to exit...")


if __name__ == "__main__":
    try:
        play()
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye!")
        sys.exit(0)

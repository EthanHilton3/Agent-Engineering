# Description: A friendly terminal-based Connect Four game with a colorful visual board, clear instructions, input validation, replay support, and both single-player mode against a computer opponent and two-player mode for local multiplayer. The computer uses a practical strategy that prioritizes winning moves, blocking the human player, and choosing strong central columns.
# ----------------------------------------

#!/usr/bin/env python3
"""Connect Four - terminal edition.

Run with:
    python connect4game.py
"""

import random
import shutil

ROWS = 6
COLS = 7
EMPTY = " "
HUMAN = "X"
COMPUTER = "O"

# ANSI colors; the game still works in terminals that do not display colors.
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
GREEN = "\033[92m"
RESET = "\033[0m"
BOLD = "\033[1m"


def clear_screen():
    print("\033[2J\033[H", end="")


def color_piece(piece):
    if piece == HUMAN:
        return f"{RED}{BOLD}{piece}{RESET}"
    if piece == COMPUTER:
        return f"{YELLOW}{BOLD}{piece}{RESET}"
    return piece


def new_board():
    return [[EMPTY for _ in range(COLS)] for _ in range(ROWS)]


def print_board(board, message=""):
    clear_screen()
    print(f"{CYAN}{BOLD}CONNECT FOUR{RESET}")
    print("Connect four pieces in a row horizontally, vertically, or diagonally.\n")
    print("    " + "   ".join(str(i) for i in range(1, COLS + 1)))
    print("  +" + "---+" * COLS)
    for row in board:
        print("  |" + "|".join(f" {color_piece(cell)} " for cell in row) + "|")
        print("  +" + "---+" * COLS)
    if message:
        print(f"\n{message}")


def valid_columns(board):
    return [column for column in range(COLS) if board[0][column] == EMPTY]


def drop_piece(board, column, piece):
    if column not in valid_columns(board):
        return False
    for row in range(ROWS - 1, -1, -1):
        if board[row][column] == EMPTY:
            board[row][column] = piece
            return True
    return False


def winning_move(board, piece):
    # Horizontal
    for row in range(ROWS):
        for col in range(COLS - 3):
            if all(board[row][col + i] == piece for i in range(4)):
                return True
    # Vertical
    for row in range(ROWS - 3):
        for col in range(COLS):
            if all(board[row + i][col] == piece for i in range(4)):
                return True
    # Down-right diagonal
    for row in range(ROWS - 3):
        for col in range(COLS - 3):
            if all(board[row + i][col + i] == piece for i in range(4)):
                return True
    # Up-right diagonal
    for row in range(3, ROWS):
        for col in range(COLS - 3):
            if all(board[row - i][col + i] == piece for i in range(4)):
                return True
    return False


def board_full(board):
    return not valid_columns(board)


def choose_computer_move(board):
    """Choose a move using winning, blocking, center preference, and randomness."""
    columns = valid_columns(board)

    # Win immediately if possible.
    for column in columns:
        test = [row[:] for row in board]
        drop_piece(test, column, COMPUTER)
        if winning_move(test, COMPUTER):
            return column

    # Block the human's immediate win.
    for column in columns:
        test = [row[:] for row in board]
        drop_piece(test, column, HUMAN)
        if winning_move(test, HUMAN):
            return column

    # Prefer the center, with a little variety for a natural feel.
    center_first = sorted(columns, key=lambda c: abs((COLS // 2) - c))
    best_distance = abs((COLS // 2) - center_first[0])
    best = [c for c in center_first if abs((COLS // 2) - c) == best_distance]
    return random.choice(best)


def ask_column(board, player_name):
    while True:
        answer = input(f"{player_name}, choose a column (1-{COLS}) or Q to quit: ").strip().lower()
        if answer in ("q", "quit"):
            return None
        if answer.isdigit() and 1 <= int(answer) <= COLS:
            column = int(answer) - 1
            if column in valid_columns(board):
                return column
            print("That column is full. Try another one.")
        else:
            print(f"Please enter a number from 1 to {COLS}.")


def choose_mode():
    while True:
        print(f"{BOLD}Choose a game mode:{RESET}")
        print("  1) Single player (you vs. computer)")
        print("  2) Two players (local multiplayer)")
        choice = input("Enter 1 or 2: ").strip()
        if choice in ("1", "2"):
            return choice
        print("Please choose 1 or 2.\n")


def play_game(mode):
    board = new_board()
    current = HUMAN
    names = {HUMAN: "Player 1", COMPUTER: "Computer"}
    if mode == "2":
        names[COMPUTER] = "Player 2"

    while True:
        if mode == "1" and current == COMPUTER:
            print_board(board, "Computer is thinking...")
            column = choose_computer_move(board)
        else:
            print_board(board, f"{names[current]}'s turn ({color_piece(current)})")
            column = ask_column(board, names[current])
            if column is None:
                return "quit"

        drop_piece(board, column, current)
        if winning_move(board, current):
            print_board(board, f"{GREEN}{BOLD}{names[current]} wins! Congratulations!{RESET}")
            return "finished"
        if board_full(board):
            print_board(board, f"{CYAN}{BOLD}It's a draw! The board is full.{RESET}")
            return "finished"
        current = COMPUTER if current == HUMAN else HUMAN


def main():
    while True:
        clear_screen()
        print(f"{CYAN}{BOLD}Welcome to Connect Four!{RESET}\n")
        mode = choose_mode()
        result = play_game(mode)
        if result == "quit":
            print("\nThanks for playing!")
            return
        again = input("\nPlay again? (y/n): ").strip().lower()
        if again not in ("y", "yes"):
            print("\nThanks for playing!")
            return


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nThanks for playing!")

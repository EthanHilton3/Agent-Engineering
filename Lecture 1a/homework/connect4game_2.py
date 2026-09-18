#!/usr/bin/env python3

import math
import os
import random
import sys
import time

ROWS = 6
COLS = 7

EMPTY = 0
RED_PLAYER = 1
YELLOW_PLAYER = 2

AI_DEPTH = 5

# Use colors when running in a terminal.
USE_COLOR = sys.stdout.isatty()

ANSI_RED = "\033[91m"
ANSI_YELLOW = "\033[93m"
ANSI_RESET = "\033[0m"


def clear_screen():
    """Clear the terminal screen when possible."""
    if not sys.stdout.isatty():
        return

    if os.name == "nt":
        os.system("cls")
    else:
        print("\033[2J\033[H", end="")


def create_board():
    """Create an empty Connect 4 board."""
    return [[EMPTY for _ in range(COLS)] for _ in range(ROWS)]


def copy_board(board):
    return [row[:] for row in board]


def get_token(piece):
    """Return a visually friendly token for a player."""
    if piece == RED_PLAYER:
        if USE_COLOR:
            return f"{ANSI_RED}●{ANSI_RESET}"
        return "R"

    if piece == YELLOW_PLAYER:
        if USE_COLOR:
            return f"{ANSI_YELLOW}●{ANSI_RESET}"
        return "Y"

    return " "


def display_board(board):
    """Display the current game board."""
    print()
    print("                 CONNECT 4")
    print()

    print("     " + "   ".join(str(column) for column in range(1, COLS + 1)))
    print("   +" + "---+" * COLS)

    for row in board:
        cells = []
        for piece in row:
            cells.append(f" {get_token(piece)} ")
        print("   |" + "|".join(cells) + "|")
        print("   +" + "---+" * COLS)

    print()


def get_valid_columns(board):
    """Return columns that still have room for a token."""
    return [column for column in range(COLS) if board[0][column] == EMPTY]


def drop_piece(board, column, piece):
    """Drop a piece into a column. Return the row used, or None if full."""
    for row in range(ROWS - 1, -1, -1):
        if board[row][column] == EMPTY:
            board[row][column] = piece
            return row

    return None


def winning_move(board, piece):
    """Check whether a player has four pieces in a row."""
    # Horizontal check
    for row in range(ROWS):
        for column in range(COLS - 3):
            if all(board[row][column + offset] == piece for offset in range(4)):
                return True

    # Vertical check
    for row in range(ROWS - 3):
        for column in range(COLS):
            if all(board[row + offset][column] == piece for offset in range(4)):
                return True

    # Diagonal: down and right
    for row in range(ROWS - 3):
        for column in range(COLS - 3):
            if all(
                board[row + offset][column + offset] == piece
                for offset in range(4)
            ):
                return True

    # Diagonal: up and right
    for row in range(3, ROWS):
        for column in range(COLS - 3):
            if all(
                board[row - offset][column + offset] == piece
                for offset in range(4)
            ):
                return True

    return False


def board_is_full(board):
    return len(get_valid_columns(board)) == 0


def evaluate_window(window, piece):
    """Score a group of four cells for the AI."""
    opponent = RED_PLAYER if piece == YELLOW_PLAYER else YELLOW_PLAYER

    piece_count = window.count(piece)
    opponent_count = window.count(opponent)
    empty_count = window.count(EMPTY)

    score = 0

    if piece_count == 4:
        score += 100000
    elif piece_count == 3 and empty_count == 1:
        score += 100
    elif piece_count == 2 and empty_count == 2:
        score += 10

    if opponent_count == 3 and empty_count == 1:
        score -= 120
    elif opponent_count == 2 and empty_count == 2:
        score -= 8

    return score


def score_position(board, piece):
    """Evaluate how favorable a board position is for a player."""
    score = 0
    opponent = RED_PLAYER if piece == YELLOW_PLAYER else YELLOW_PLAYER

    # Prefer the center column.
    center_column = [board[row][COLS // 2] for row in range(ROWS)]
    score += center_column.count(piece) * 6

    # Horizontal windows
    for row in range(ROWS):
        for column in range(COLS - 3):
            window = [
                board[row][column + offset]
                for offset in range(4)
            ]
            score += evaluate_window(window, piece)

    # Vertical windows
    for row in range(ROWS - 3):
        for column in range(COLS):
            window = [
                board[row + offset][column]
                for offset in range(4)
            ]
            score += evaluate_window(window, piece)

    # Diagonal windows: down and right
    for row in range(ROWS - 3):
        for column in range(COLS - 3):
            window = [
                board[row + offset][column + offset]
                for offset in range(4)
            ]
            score += evaluate_window(window, piece)

    # Diagonal windows: up and right
    for row in range(3, ROWS):
        for column in range(COLS - 3):
            window = [
                board[row - offset][column + offset]
                for offset in range(4)
            ]
            score += evaluate_window(window, piece)

    # Small bonus for having more pieces on the board than the opponent.
    score += board_count(board, piece) - board_count(board, opponent)

    return score


def board_count(board, piece):
    return sum(row.count(piece) for row in board)


def is_terminal_node(board):
    return (
        winning_move(board, RED_PLAYER)
        or winning_move(board, YELLOW_PLAYER)
        or board_is_full(board)
    )


def ordered_columns(board):
    """
    Try the center columns first.
    This improves the AI's play and makes alpha-beta pruning faster.
    """
    center = COLS // 2
    preferred_order = [center, center - 1, center + 1,
                       center - 2, center + 2,
                       center - 3, center + 3]

    valid = get_valid_columns(board)
    return [column for column in preferred_order if column in valid]


def minimax(board, depth, alpha, beta, maximizing_player):
    """Minimax search with alpha-beta pruning."""
    valid_columns = ordered_columns(board)
    terminal = is_terminal_node(board)

    if depth == 0 or terminal:
        if winning_move(board, YELLOW_PLAYER):
            return None, 1_000_000 + depth

        if winning_move(board, RED_PLAYER):
            return None, -1_000_000 - depth

        if board_is_full(board):
            return None, 0

        return None, score_position(board, YELLOW_PLAYER)

    if maximizing_player:
        best_score = -math.inf
        best_columns = []

        for column in valid_columns:
            simulated_board = copy_board(board)
            drop_piece(simulated_board, column, YELLOW_PLAYER)

            _, score = minimax(
                simulated_board,
                depth - 1,
                alpha,
                beta,
                False,
            )

            if score > best_score:
                best_score = score
                best_columns = [column]
            elif score == best_score:
                best_columns.append(column)

            alpha = max(alpha, best_score)

            if alpha >= beta:
                break

        if not best_columns:
            return None, 0

        return random.choice(best_columns), best_score

    best_score = math.inf
    best_columns = []

    for column in valid_columns:
        simulated_board = copy_board(board)
        drop_piece(simulated_board, column, RED_PLAYER)

        _, score = minimax(
            simulated_board,
            depth - 1,
            alpha,
            beta,
            True,
        )

        if score < best_score:
            best_score = score
            best_columns = [column]
        elif score == best_score:
            best_columns.append(column)

        beta = min(beta, best_score)

        if alpha >= beta:
            break

    if not best_columns:
        return None, 0

    return random.choice(best_columns), best_score


def choose_ai_move(board):
    """Choose a move for the computer."""
    valid_columns = get_valid_columns(board)

    if not valid_columns:
        return None

    # If possible, win immediately.
    for column in valid_columns:
        simulated_board = copy_board(board)
        drop_piece(simulated_board, column, YELLOW_PLAYER)

        if winning_move(simulated_board, YELLOW_PLAYER):
            return column

    # If necessary, block the human's immediate winning move.
    for column in valid_columns:
        simulated_board = copy_board(board)
        drop_piece(simulated_board, column, RED_PLAYER)

        if winning_move(simulated_board, RED_PLAYER):
            return column

    column, _ = minimax(
        board,
        AI_DEPTH,
        -math.inf,
        math.inf,
        True,
    )

    if column is not None:
        return column

    return random.choice(valid_columns)


def ask_human_move(board, player_name):
    """Ask a human player to select a column."""
    while True:
        try:
            choice = input(
                f"{player_name}, choose a column from 1-{COLS} "
                "(or Q to quit): "
            ).strip().lower()
        except EOFError:
            return None

        if choice in {"q", "quit", "exit"}:
            return None

        if choice in {"h", "help", "?"}:
            print()
            print("Enter a number from 1 to 7 to drop your token.")
            print("Enter Q at any time to quit the current game.")
            print()
            continue

        try:
            column = int(choice) - 1
        except ValueError:
            print("Please enter a valid column number from 1 to 7.")
            continue

        if column < 0 or column >= COLS:
            print(f"Please choose a number from 1 to {COLS}.")
            continue

        if column not in get_valid_columns(board):
            print("That column is full. Please choose another one.")
            continue

        return column


def choose_game_mode():
    """Ask the user which type of game to play."""
    while True:
        clear_screen()
        print("======================================")
        print("             CONNECT 4")
        print("======================================")
        print()
        print("Drop four tokens in a row to win.")
        print("Red always goes first.")
        print()
        print("1. Single player vs. computer")
        print("2. Two human players")
        print("Q. Quit")
        print()

        try:
            choice = input("Choose a game mode: ").strip().lower()
        except EOFError:
            return None

        if choice == "1":
            return 1

        if choice == "2":
            return 2

        if choice in {"q", "quit", "exit"}:
            return None

        print("Please choose 1, 2, or Q.")
        time.sleep(1)


def ask_play_again():
    """Ask whether another game should be started."""
    while True:
        try:
            choice = input("\nPlay another game? (Y/N): ").strip().lower()
        except EOFError:
            return False

        if choice in {"y", "yes"}:
            return True

        if choice in {"n", "no", "q", "quit"}:
            return False

        print("Please enter Y or N.")


def play_game(mode):
    """
    Run one game.

    Returns True if the game ended normally.
    Returns False if the player quit.
    """
    board = create_board()
    current_player = RED_PLAYER

    while True:
        clear_screen()
        display_board(board)

        if mode == 1:
            print("You are Red. The computer is Yellow.")
            print()

        if mode == 1 and current_player == YELLOW_PLAYER:
            print("The computer is thinking...")
            time.sleep(0.4)
            column = choose_ai_move(board)
            player_name = "Computer"
        else:
            if mode == 2:
                player_name = (
                    "Red player"
                    if current_player == RED_PLAYER
                    else "Yellow player"
                )
            else:
                player_name = "You"

            column = ask_human_move(board, player_name)

            if column is None:
                return False

        drop_piece(board, column, current_player)

        if winning_move(board, current_player):
            clear_screen()
            display_board(board)

            if mode == 1:
                if current_player == RED_PLAYER:
                    print("Congratulations! You defeated the computer!")
                else:
                    print("The computer wins this time!")
            else:
                winner = (
                    "Red player"
                    if current_player == RED_PLAYER
                    else "Yellow player"
                )
                print(f"{winner} wins!")

            return True

        if board_is_full(board):
            clear_screen()
            display_board(board)
            print("It's a draw! The board is full.")
            return True

        current_player = (
            YELLOW_PLAYER
            if current_player == RED_PLAYER
            else RED_PLAYER
        )


def main():
    while True:
        mode = choose_game_mode()

        if mode is None:
            clear_screen()
            print("Thanks for playing Connect 4!")
            return

        game_completed = play_game(mode)

        if not game_completed:
            clear_screen()
            print("Game abandoned.")
            print("Thanks for playing Connect 4!")
            return

        if not ask_play_again():
            clear_screen()
            print("Thanks for playing Connect 4!")
            return


if __name__ == "__main__":
    main()
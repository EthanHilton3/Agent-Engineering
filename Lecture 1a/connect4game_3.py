#!/usr/bin/env python3
"""
Console Connect Four

Features:
- Single-player mode against a computer opponent
- Two-player mode on the same machine
- Easy, Medium, and Hard computer difficulty
- Colored console pieces when supported
- Input validation and simple menu controls
"""

from __future__ import annotations

import math
import os
import random
import sys
import time
from typing import Dict, List, Optional, Tuple


ROWS = 6
COLS = 7
EMPTY = 0

Board = List[List[int]]

# ANSI colors
RED = "\033[31m"
YELLOW = "\033[33m"
RESET = "\033[0m"

COLOUR_ENABLED = False


def setup_terminal() -> None:
    """Enable colors when the current terminal appears to support them."""
    global COLOUR_ENABLED

    windows_color_support = (
        os.name != "nt"
        or "WT_SESSION" in os.environ
        or "ANSICON" in os.environ
        or os.environ.get("TERM") is not None
    )

    COLOUR_ENABLED = bool(
        sys.stdout.isatty()
        and os.environ.get("TERM", "").lower() != "dumb"
        and windows_color_support
    )


def clear_screen() -> None:
    """Clear the terminal screen."""
    if not sys.stdout.isatty():
        print("\n" * 3)
        return

    if os.name == "nt":
        os.system("cls")
    elif os.environ.get("TERM", "").lower() != "dumb":
        print("\033[2J\033[H", end="")
    else:
        print("\n" * 3)


def read_input(prompt: str) -> Optional[str]:
    """Read input while handling Ctrl+C and end-of-file cleanly."""
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        print("\nReturning to the main menu.")
        return None


def piece_symbol(player: int) -> str:
    """Return the display symbol for a board piece."""
    if player == EMPTY:
        return " "

    if COLOUR_ENABLED:
        colour = RED if player == 1 else YELLOW
        return f"{colour}●{RESET}"

    # Fallback symbols when colors are unavailable.
    return "X" if player == 1 else "O"


def print_title() -> None:
    """Print the game title."""
    print("╔════════════════════════════════════╗")
    print("║              CONNECT 4             ║")
    print("╚════════════════════════════════════╝")


class ConnectFour:
    """Represents a Connect Four game board."""

    def __init__(self) -> None:
        self.board: Board = [
            [EMPTY for _ in range(COLS)]
            for _ in range(ROWS)
        ]
        self.current_player = 1

    def valid_columns(self) -> List[int]:
        """Return columns that can still accept a piece."""
        return [
            column
            for column in range(COLS)
            if self.board[0][column] == EMPTY
        ]

    def drop_piece(self, column: int, player: int) -> int:
        """
        Drop a piece into a column.

        Returns:
            The row where the piece landed.

        Raises:
            ValueError: If the column is invalid or full.
        """
        if column < 0 or column >= COLS:
            raise ValueError("Invalid column.")

        if self.board[0][column] != EMPTY:
            raise ValueError("That column is full.")

        for row in range(ROWS - 1, -1, -1):
            if self.board[row][column] == EMPTY:
                self.board[row][column] = player
                return row

        raise ValueError("That column is full.")

    def remove_piece(self, row: int, column: int) -> None:
        """Remove a piece, primarily for computer move simulation."""
        self.board[row][column] = EMPTY

    def is_full(self) -> bool:
        """Return True when the board has no empty spaces."""
        return len(self.valid_columns()) == 0

    def has_winner(self, player: int) -> bool:
        """Return True if the specified player has four in a row."""
        return winning_move(self.board, player)


def render_board(game: ConnectFour, names: Dict[int, str]) -> None:
    """Draw the current game board."""
    print(
        f"  {piece_symbol(1)} {names.get(1, 'Player 1')}"
        f"       {piece_symbol(2)} {names.get(2, 'Player 2')}"
    )
    print()

    # Column numbers
    print("    " + "   ".join(str(number) for number in range(1, COLS + 1)))

    top_border = "┌" + "┬".join(["───"] * COLS) + "┐"
    middle_border = "├" + "┼".join(["───"] * COLS) + "┤"
    bottom_border = "└" + "┴".join(["───"] * COLS) + "┘"

    print("  " + top_border)

    for row_index, row in enumerate(game.board):
        cells = [piece_symbol(piece) for piece in row]
        print("  │ " + " │ ".join(cells) + " │")

        if row_index < ROWS - 1:
            print("  " + middle_border)

    print("  " + bottom_border)


def winning_move(board: Board, player: int) -> bool:
    """Check whether a player has four consecutive pieces."""

    # Horizontal checks
    for row in range(ROWS):
        for column in range(COLS - 3):
            if all(board[row][column + offset] == player for offset in range(4)):
                return True

    # Vertical checks
    for row in range(ROWS - 3):
        for column in range(COLS):
            if all(board[row + offset][column] == player for offset in range(4)):
                return True

    # Diagonal checks: down and right
    for row in range(ROWS - 3):
        for column in range(COLS - 3):
            if all(
                board[row + offset][column + offset] == player
                for offset in range(4)
            ):
                return True

    # Diagonal checks: up and right
    for row in range(3, ROWS):
        for column in range(COLS - 3):
            if all(
                board[row - offset][column + offset] == player
                for offset in range(4)
            ):
                return True

    return False


def evaluate_window(window: List[int], player: int) -> int:
    """Score a group of four board positions."""
    opponent = 1 if player == 2 else 2
    score = 0

    player_count = window.count(player)
    opponent_count = window.count(opponent)
    empty_count = window.count(EMPTY)

    if player_count == 4:
        score += 100
    elif player_count == 3 and empty_count == 1:
        score += 5
    elif player_count == 2 and empty_count == 2:
        score += 2

    if opponent_count == 3 and empty_count == 1:
        score -= 4
    elif opponent_count == 2 and empty_count == 2:
        score -= 1

    return score


def score_position(board: Board, player: int) -> int:
    """Estimate how favorable a board position is for a player."""
    score = 0

    # Center columns are strategically valuable.
    center_column = [board[row][COLS // 2] for row in range(ROWS)]
    score += center_column.count(player) * 3

    # Horizontal windows
    for row in range(ROWS):
        for column in range(COLS - 3):
            window = board[row][column:column + 4]
            score += evaluate_window(window, player)

    # Vertical windows
    for row in range(ROWS - 3):
        for column in range(COLS):
            window = [
                board[row + offset][column]
                for offset in range(4)
            ]
            score += evaluate_window(window, player)

    # Diagonal windows: down and right
    for row in range(ROWS - 3):
        for column in range(COLS - 3):
            window = [
                board[row + offset][column + offset]
                for offset in range(4)
            ]
            score += evaluate_window(window, player)

    # Diagonal windows: up and right
    for row in range(3, ROWS):
        for column in range(COLS - 3):
            window = [
                board[row - offset][column + offset]
                for offset in range(4)
            ]
            score += evaluate_window(window, player)

    return score


def ordered_columns(columns: List[int]) -> List[int]:
    """Order columns from the center outward."""
    center = COLS // 2
    return sorted(
        columns,
        key=lambda column: (abs(center - column), column),
    )


def place_on_board(board: Board, column: int, player: int) -> int:
    """Place a piece on a simulated board and return its row."""
    for row in range(ROWS - 1, -1, -1):
        if board[row][column] == EMPTY:
            board[row][column] = player
            return row

    raise ValueError("Cannot place a piece in a full column.")


def minimax(
    board: Board,
    depth: int,
    alpha: float,
    beta: float,
    maximizing_player: bool,
    ai_player: int,
) -> Tuple[Optional[int], float]:
    """Choose a move using minimax with alpha-beta pruning."""
    opponent = 1 if ai_player == 2 else 2

    valid_locations = [
        column
        for column in range(COLS)
        if board[0][column] == EMPTY
    ]

    ai_won = winning_move(board, ai_player)
    opponent_won = winning_move(board, opponent)

    if depth == 0 or ai_won or opponent_won or not valid_locations:
        if ai_won:
            return None, 10_000_000 + depth
        if opponent_won:
            return None, -10_000_000 - depth
        if not valid_locations:
            return None, 0

        return None, score_position(board, ai_player)

    columns = ordered_columns(valid_locations)

    if maximizing_player:
        best_score = -math.inf
        best_column = columns[0]

        for column in columns:
            row = place_on_board(board, column, ai_player)

            _, score = minimax(
                board,
                depth - 1,
                alpha,
                beta,
                False,
                ai_player,
            )

            board[row][column] = EMPTY

            if score > best_score:
                best_score = score
                best_column = column

            alpha = max(alpha, best_score)
            if alpha >= beta:
                break

        return best_column, best_score

    best_score = math.inf
    best_column = columns[0]

    for column in columns:
        row = place_on_board(board, column, opponent)

        _, score = minimax(
            board,
            depth - 1,
            alpha,
            beta,
            True,
            ai_player,
        )

        board[row][column] = EMPTY

        if score < best_score:
            best_score = score
            best_column = column

        beta = min(beta, best_score)
        if alpha >= beta:
            break

    return best_column, best_score


def creates_winning_move(
    game: ConnectFour,
    column: int,
    player: int,
) -> bool:
    """Test whether a player would win by playing in a column."""
    row = game.drop_piece(column, player)
    result = game.has_winner(player)
    game.remove_piece(row, column)
    return result


def choose_ai_column(
    game: ConnectFour,
    ai_player: int,
    difficulty: str,
) -> Optional[int]:
    """Select a computer move based on the chosen difficulty."""
    valid_columns = game.valid_columns()

    if not valid_columns:
        return None

    columns = ordered_columns(valid_columns)
    opponent = 1 if ai_player == 2 else 2

    # Always take an immediate winning move.
    for column in columns:
        if creates_winning_move(game, column, ai_player):
            return column

    # Always block an immediate opponent win.
    for column in columns:
        if creates_winning_move(game, column, opponent):
            return column

    if difficulty == "easy":
        # Favor center columns, but make occasional weaker moves.
        weights = [
            max(1, 4 - abs((COLS // 2) - column))
            for column in columns
        ]
        return random.choices(columns, weights=weights, k=1)[0]

    depth = 3 if difficulty == "medium" else 5

    selected_column, _ = minimax(
        game.board,
        depth,
        -math.inf,
        math.inf,
        True,
        ai_player,
    )

    if selected_column is not None:
        return selected_column

    return random.choice(valid_columns)


def ask_for_column(
    game: ConnectFour,
    player_name: str,
) -> Optional[int]:
    """Ask a human player to choose a column."""
    while True:
        answer = read_input(
            f"\n{player_name}, choose a column "
            f"(1-{COLS}), or M for menu: "
        )

        if answer is None:
            return None

        choice = answer.strip().lower()

        if choice in {"m", "menu", "q", "quit"}:
            return None

        if choice in {"h", "help", "?"}:
            print("\nEnter a number from 1 to 7 to drop your piece.")
            print("Enter M at any time to return to the main menu.")
            continue

        try:
            column = int(choice) - 1
        except ValueError:
            print(f"Please enter a number from 1 to {COLS}.")
            continue

        if column < 0 or column >= COLS:
            print(f"Please choose a column from 1 to {COLS}.")
            continue

        if column not in game.valid_columns():
            print("That column is full. Choose another one.")
            continue

        return column


def show_final_state(
    game: ConnectFour,
    names: Dict[int, str],
    message: str,
) -> None:
    """Display the final board and result message."""
    clear_screen()
    print_title()
    print()
    render_board(game, names)
    print(f"\n{message}")
    read_input("\nPress Enter to continue...")


def run_game(
    names: Dict[int, str],
    ai_player: Optional[int],
    difficulty: str,
    starting_player: int,
) -> str:
    """
    Run one game.

    Returns:
        "finished" when the game ends normally.
        "menu" when a human player returns to the menu.
    """
    game = ConnectFour()
    game.current_player = starting_player

    while True:
        clear_screen()
        print_title()
        print()
        render_board(game, names)

        current_player = game.current_player

        if ai_player is not None and current_player == ai_player:
            print(
                f"\n{names[current_player]} "
                f"({piece_symbol(current_player)}) is thinking..."
            )
            sys.stdout.flush()

            if sys.stdout.isatty():
                time.sleep(0.4)

            column = choose_ai_column(
                game,
                ai_player,
                difficulty,
            )

            if column is None:
                show_final_state(
                    game,
                    names,
                    "The board is full. The game is a draw!",
                )
                return "finished"

            game.drop_piece(column, current_player)

        else:
            print(
                f"\n{names[current_player]}'s turn "
                f"({piece_symbol(current_player)})."
            )

            column = ask_for_column(
                game,
                names[current_player],
            )

            if column is None:
                return "menu"

            game.drop_piece(column, current_player)

        if game.has_winner(current_player):
            show_final_state(
                game,
                names,
                (
                    f"{piece_symbol(current_player)} "
                    f"{names[current_player]} wins! "
                    "Congratulations!"
                ),
            )
            return "finished"

        if game.is_full():
            show_final_state(
                game,
                names,
                "The board is full. The game is a draw!",
            )
            return "finished"

        game.current_player = 1 if current_player == 2 else 2


def choose_difficulty() -> Optional[str]:
    """Ask the player to select the computer difficulty."""
    print("\nChoose computer difficulty:")
    print("  1. Easy   - relaxed and unpredictable")
    print("  2. Medium - thinks a few moves ahead")
    print("  3. Hard   - stronger strategic play")

    while True:
        answer = read_input(
            "\nDifficulty [2] "
            "(B to go back): "
        )

        if answer is None:
            return None

        choice = answer.strip().lower()

        if choice in {"b", "back", "m", "menu"}:
            return None

        if choice == "":
            return "medium"

        if choice == "1":
            return "easy"

        if choice == "2":
            return "medium"

        if choice == "3":
            return "hard"

        print("Please choose 1, 2, or 3.")


def choose_starting_player(
    first_label: str,
    second_label: str,
) -> Optional[int]:
    """Ask which of two players should start."""
    print("\nWho should go first?")
    print(f"  1. {first_label}")
    print(f"  2. {second_label}")

    while True:
        answer = read_input(
            "\nChoose [1] "
            "(B to go back): "
        )

        if answer is None:
            return None

        choice = answer.strip().lower()

        if choice in {"b", "back", "m", "menu"}:
            return None

        if choice == "":
            return 1

        if choice in {"1", "2"}:
            return int(choice)

        print("Please choose 1 or 2.")


def ask_player_name(label: str, default: str) -> Optional[str]:
    """Ask for a player name."""
    answer = read_input(f"{label} [{default}]: ")

    if answer is None:
        return None

    cleaned = "".join(
        character
        for character in answer.strip()
        if character.isprintable()
    )

    return cleaned[:20] or default


def single_player_mode() -> None:
    """Set up and run single-player games."""
    clear_screen()
    print_title()
    print("\nSingle-player mode")
    print("You will play against the computer.")

    difficulty = choose_difficulty()
    if difficulty is None:
        return

    starter = choose_starting_player("You", "Computer")
    if starter is None:
        return

    names = {
        1: "You",
        2: "Computer",
    }

    while True:
        result = run_game(
            names=names,
            ai_player=2,
            difficulty=difficulty,
            starting_player=starter,
        )

        if result != "finished":
            return

        answer = read_input(
            "\nPlay again with the same settings? [Y/N]: "
        )

        if answer is None:
            return

        if answer.strip().lower() not in {"y", "yes", "r", "again"}:
            return


def two_player_mode() -> None:
    """Set up and run two-player games."""
    clear_screen()
    print_title()
    print("\nTwo-player mode")

    player_one = ask_player_name(
        "Player 1 name",
        "Player 1",
    )
    if player_one is None:
        return

    player_two = ask_player_name(
        "Player 2 name",
        "Player 2",
    )
    if player_two is None:
        return

    starter = choose_starting_player(player_one, player_two)
    if starter is None:
        return

    names = {
        1: player_one,
        2: player_two,
    }

    while True:
        result = run_game(
            names=names,
            ai_player=None,
            difficulty="medium",
            starting_player=starter,
        )

        if result != "finished":
            return

        answer = read_input(
            "\nPlay again? The starting player will alternate. [Y/N]: "
        )

        if answer is None:
            return

        if answer.strip().lower() not in {"y", "yes", "r", "again"}:
            return

        starter = 1 if starter == 2 else 2


def main() -> None:
    """Run the main menu."""
    setup_terminal()

    while True:
        clear_screen()
        print_title()
        print("\nMake four pieces in a row horizontally, vertically,")
        print("or diagonally to win.\n")

        print("  1. One player - play against the computer")
        print("  2. Two players - play on the same computer")
        print("  3. Quit")

        choice = read_input("\nChoose an option: ")

        if choice is None:
            break

        choice = choice.strip().lower()

        if choice == "1":
            single_player_mode()
        elif choice == "2":
            two_player_mode()
        elif choice in {"3", "q", "quit"}:
            break
        else:
            print("Please choose 1, 2, or 3.")
            if sys.stdout.isatty():
                time.sleep(0.8)

    print("\nThanks for playing Connect 4!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nGoodbye!")
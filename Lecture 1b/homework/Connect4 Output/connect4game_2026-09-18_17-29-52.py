Description: A friendly console-based Connect Four game with a colorful, clearly labeled 6-by-7 board. Players can choose single-player mode against an AI opponent or two-player mode for local multiplayer. The program validates moves, detects wins and draws, provides helpful instructions, and allows players to start new games or quit after each match.
----------------------------------------

import random
import shutil

ROWS = 6
COLS = 7
EMPTY = " "
HUMAN = "X"
AI = "O"


def clear_screen():
    print("\033[2J\033[H", end="")


def make_board():
    return [[EMPTY for _ in range(COLS)] for _ in range(ROWS)]


def print_board(board):
    print("\n     CONNECT FOUR\n")
    print("   " + "   ".join(str(i + 1) for i in range(COLS)))
    print("  +---" * COLS + "+")
    for row in board:
        print("  | " + " | ".join(row) + " |")
        print("  +---" * COLS + "+")
    print("     " + "   ".join(str(i + 1) for i in range(COLS)))
    print()


def valid_columns(board):
    return [column for column in range(COLS) if board[0][column] == EMPTY]


def drop_piece(board, column, piece):
    for row in range(ROWS - 1, -1, -1):
        if board[row][column] == EMPTY:
            board[row][column] = piece
            return row
    return None


def winning_move(board, piece):
    directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
    for row in range(ROWS):
        for column in range(COLS):
            if board[row][column] != piece:
                continue
            for dr, dc in directions:
                cells = []
                for step in range(4):
                    r, c = row + dr * step, column + dc * step
                    if 0 <= r < ROWS and 0 <= c < COLS:
                        cells.append(board[r][c])
                if len(cells) == 4 and all(cell == piece for cell in cells):
                    return True
    return False


def board_full(board):
    return not valid_columns(board)


def score_window(window, piece):
    opponent = HUMAN if piece == AI else AI
    score = 0
    if window.count(piece) == 4:
        score += 100
    elif window.count(piece) == 3 and window.count(EMPTY) == 1:
        score += 8
    elif window.count(piece) == 2 and window.count(EMPTY) == 2:
        score += 3
    if window.count(opponent) == 3 and window.count(EMPTY) == 1:
        score -= 7
    return score


def evaluate(board, piece=AI):
    score = 0
    center = [board[row][COLS // 2] for row in range(ROWS)]
    score += center.count(piece) * 4

    for row in range(ROWS):
        for column in range(COLS - 3):
            score += score_window(board[row][column:column + 4], piece)
    for column in range(COLS):
        for row in range(ROWS - 3):
            score += score_window([board[row + i][column] for i in range(4)], piece)
    for row in range(ROWS - 3):
        for column in range(COLS - 3):
            score += score_window([board[row + i][column + i] for i in range(4)], piece)
    for row in range(3, ROWS):
        for column in range(COLS - 3):
            score += score_window([board[row - i][column + i] for i in range(4)], piece)
    return score


def minimax(board, depth, maximizing, alpha=-float("inf"), beta=float("inf")):
    possible = valid_columns(board)
    if winning_move(board, AI):
        return None, 1000000 + depth
    if winning_move(board, HUMAN):
        return None, -1000000 - depth
    if depth == 0 or not possible:
        return None, evaluate(board)

    if maximizing:
        best_value = -float("inf")
        best_column = random.choice(possible)
        for column in possible:
            test = [row[:] for row in board]
            drop_piece(test, column, AI)
            _, value = minimax(test, depth - 1, False, alpha, beta)
            if value > best_value:
                best_value, best_column = value, column
            alpha = max(alpha, best_value)
            if alpha >= beta:
                break
        return best_column, best_value
    else:
        best_value = float("inf")
        best_column = random.choice(possible)
        for column in possible:
            test = [row[:] for row in board]
            drop_piece(test, column, HUMAN)
            _, value = minimax(test, depth - 1, True, alpha, beta)
            if value < best_value:
                best_value, best_column = value, column
            beta = min(beta, best_value)
            if alpha >= beta:
                break
        return best_column, best_value


def get_column(player_name):
    while True:
        choice = input(f"{player_name}, choose a column (1-{COLS}) or Q to quit: ").strip().lower()
        if choice == "q":
            return None
        if choice.isdigit() and 1 <= int(choice) <= COLS:
            return int(choice) - 1
        print(f"Please enter a number from 1 to {COLS}.")


def play_game(single_player):
    board = make_board()
    current = HUMAN

    while True:
        clear_screen()
        print_board(board)
        if single_player and current == AI:
            print("The computer is thinking...")
            column, _ = minimax(board, 4, True)
            column = column if column is not None else random.choice(valid_columns(board))
            drop_piece(board, column, AI)
            print(f"The computer chose column {column + 1}.")
        else:
            name = "Player 1" if current == HUMAN else "Player 2"
            column = get_column(name)
            if column is None:
                return False
            if column not in valid_columns(board):
                print("That column is full. Choose another one.")
                input("Press Enter to continue...")
                continue
            drop_piece(board, column, current)

        if winning_move(board, current):
            clear_screen()
            print_board(board)
            winner = "The computer" if single_player and current == AI else ("Player 1" if current == HUMAN else "Player 2")
            print(f"Congratulations, {winner} wins!")
            return True
        if board_full(board):
            clear_screen()
            print_board(board)
            print("It's a draw! Every column is full.")
            return True
        current = AI if current == HUMAN and single_player else (HUMAN if current == AI else AI)


def main():
    while True:
        clear_screen()
        print("================================")
        print("       CONNECT FOUR")
        print("================================")
        print("1) Single player vs computer")
        print("2) Two players")
        print("Q) Quit")
        choice = input("Choose a mode: ").strip().lower()
        if choice == "q":
            print("Thanks for playing!")
            break
        if choice not in ("1", "2"):
            print("Please choose 1, 2, or Q.")
            input("Press Enter to continue...")
            continue
        if not play_game(choice == "1"):
            break
        again = input("Play again? (y/n): ").strip().lower()
        if again not in ("y", "yes"):
            print("Thanks for playing!")
            break


if __name__ == "__main__":
    main()

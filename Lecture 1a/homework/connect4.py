import os
import sys

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_board(board):
    print('\n  1 2 3 4 5 6 7')
    print(' +-------------+')
    for row in board:
        print(' |' + ' '.join(row) + '|')
    print(' +-------------+')

def create_board():
    return [['.' for _ in range(7)] for _ in range(6)]

def is_valid_column(board, col):
    return board[0][col] == '.'

def get_next_open_row(board, col):
    for r in range(5, -1, -1):
        if board[r][col] == '.':
            return r
    return -1

def drop_piece(board, row, col, piece):
    board[row][col] = piece

def winning_move(board, piece):
    # Check horizontal
    for c in range(4):
        for r in range(6):
            if all(board[r][c+i] == piece for i in range(4)):
                return True
    # Check vertical
    for c in range(7):
        for r in range(3):
            if all(board[r+i][c] == piece for i in range(4)):
                return True
    # Check positively sloped diagonals
    for c in range(4):
        for r in range(3,6):
            if all(board[r-i][c+i] == piece for i in range(4)):
                return True
    # Check negatively sloped diagonals
    for c in range(4):
        for r in range(3):
            if all(board[r+i][c+i] == piece for i in range(4)):
                return True
    return False

def board_full(board):
    return all(board[0][col] != '.' for col in range(7))

def main():
    board = create_board()
    game_over = False
    turn = 0
    pieces = ['X', 'O']

    while not game_over:
        clear_screen()
        print_board(board)
        print(f"Player {turn+1} ({pieces[turn]}), choose a column (1-7): ", end='')
        try:
            col = int(input()) - 1
        except ValueError:
            print('Invalid input. Press Enter to continue...')
            input()
            continue
        if col < 0 or col > 6 or not is_valid_column(board, col):
            print('Column full or invalid. Press Enter to continue...')
            input()
            continue
        row = get_next_open_row(board, col)
        drop_piece(board, row, col, pieces[turn])
        if winning_move(board, pieces[turn]):
            clear_screen()
            print_board(board)
            print(f'Player {turn+1} ({pieces[turn]}) wins!')
            game_over = True
        elif board_full(board):
            clear_screen()
            print_board(board)
            print('Game is a draw!')
            game_over = True
        else:
            turn = (turn + 1) % 2

if __name__ == '__main__':
    main()

ROWS = 6
COLS = 7
EMPTY = 0
PLAYER_1 = 1
PLAYER_2 = 2


def create_board():
    return [[EMPTY for _ in range(COLS)] for _ in range(ROWS)]


def is_valid_move(board, column):
    return isinstance(column, int) and 0 <= column < COLS and board[0][column] == EMPTY


def make_move(board, column, player):
    if not is_valid_move(board, column):
        return False

    for row in range(ROWS - 1, -1, -1):
        if board[row][column] == EMPTY:
            board[row][column] = player
            return True

    return False


def check_winner(board, player):
    # Horizontal
    for row in range(ROWS):
        for column in range(COLS - 3):
            if all(board[row][column + offset] == player for offset in range(4)):
                return True

    # Vertical
    for row in range(ROWS - 3):
        for column in range(COLS):
            if all(board[row + offset][column] == player for offset in range(4)):
                return True

    # Diagonal descendente
    for row in range(ROWS - 3):
        for column in range(COLS - 3):
            if all(board[row + offset][column + offset] == player for offset in range(4)):
                return True

    # Diagonal ascendente
    for row in range(3, ROWS):
        for column in range(COLS - 3):
            if all(board[row - offset][column + offset] == player for offset in range(4)):
                return True

    return False


def is_draw(board):
    board_is_full = all(cell != EMPTY for row in board for cell in row)
    has_winner = check_winner(board, PLAYER_1) or check_winner(board, PLAYER_2)
    return board_is_full and not has_winner

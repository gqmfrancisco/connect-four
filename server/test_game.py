import unittest

from server.game import (
    COLS,
    EMPTY,
    PLAYER_1,
    PLAYER_2,
    ROWS,
    check_winner,
    create_board,
    is_draw,
    is_valid_move,
    make_move,
)


class TestConnectFour(unittest.TestCase):
    def test_create_empty_board_with_correct_dimensions(self):
        board = create_board()

        self.assertEqual(len(board), ROWS)
        self.assertTrue(all(len(row) == COLS for row in board))
        self.assertTrue(all(cell == EMPTY for row in board for cell in row))

    def test_created_boards_are_independent(self):
        first_board = create_board()
        second_board = create_board()

        first_board[0][0] = PLAYER_1

        self.assertEqual(second_board[0][0], EMPTY)

    def test_valid_move(self):
        board = create_board()

        self.assertTrue(is_valid_move(board, 3))
        self.assertTrue(make_move(board, 3, PLAYER_1))
        self.assertEqual(board[ROWS - 1][3], PLAYER_1)

    def test_piece_gravity(self):
        board = create_board()

        make_move(board, 2, PLAYER_1)
        make_move(board, 2, PLAYER_2)

        self.assertEqual(board[ROWS - 1][2], PLAYER_1)
        self.assertEqual(board[ROWS - 2][2], PLAYER_2)

    def test_full_column(self):
        board = create_board()
        for row in range(ROWS):
            board[row][0] = PLAYER_1

        board_before_move = [row[:] for row in board]

        self.assertFalse(is_valid_move(board, 0))
        self.assertFalse(make_move(board, 0, PLAYER_2))
        self.assertEqual(board, board_before_move)

    def test_invalid_column(self):
        board = create_board()
        board_before_move = [row[:] for row in board]

        self.assertFalse(is_valid_move(board, -1))
        self.assertFalse(is_valid_move(board, COLS))
        self.assertFalse(make_move(board, COLS, PLAYER_1))
        self.assertEqual(board, board_before_move)

    def test_horizontal_win(self):
        board = create_board()
        for column in range(4):
            board[ROWS - 1][column] = PLAYER_1

        self.assertTrue(check_winner(board, PLAYER_1))

    def test_vertical_win(self):
        board = create_board()
        for row in range(ROWS - 4, ROWS):
            board[row][0] = PLAYER_2

        self.assertTrue(check_winner(board, PLAYER_2))

    def test_ascending_diagonal_win(self):
        board = create_board()
        for offset in range(4):
            board[ROWS - 1 - offset][offset] = PLAYER_1

        self.assertTrue(check_winner(board, PLAYER_1))

    def test_descending_diagonal_win(self):
        board = create_board()
        for offset in range(4):
            board[2 + offset][offset] = PLAYER_2

        self.assertTrue(check_winner(board, PLAYER_2))

    def test_draw(self):
        board = [
            [1, 1, 2, 2, 1, 1, 2],
            [2, 2, 1, 1, 2, 2, 1],
            [1, 1, 2, 2, 1, 1, 2],
            [2, 2, 1, 1, 2, 2, 1],
            [1, 1, 2, 2, 1, 1, 2],
            [2, 2, 1, 1, 2, 2, 1],
        ]

        self.assertTrue(is_draw(board))


if __name__ == "__main__":
    unittest.main()

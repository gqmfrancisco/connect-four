import json
import unittest
from unittest.mock import patch

from server.game import PLAYER_1, PLAYER_2, ROWS, create_board
from server.server import (
    create_room,
    find_player_room,
    generate_room_code,
    handle_leave_room,
    handle_move,
    handle_rematch_request,
    remove_disconnected_player,
    rooms,
)


class FakeWebSocket:
    def __init__(self):
        self.messages = []

    async def send(self, message):
        self.messages.append(json.loads(message))


class TestRoomCode(unittest.TestCase):
    def setUp(self):
        rooms.clear()

    def tearDown(self):
        rooms.clear()

    def test_room_code_has_four_characters(self):
        self.assertEqual(len(generate_room_code()), 4)

    def test_room_code_uses_uppercase_letters(self):
        code = generate_room_code()

        self.assertTrue(code.isalpha())
        self.assertEqual(code, code.upper())

    @patch("server.server.random.choices")
    def test_room_code_is_not_already_in_rooms(self, mock_choices):
        rooms["ABCD"] = {}
        mock_choices.side_effect = [list("ABCD"), list("EFGH")]

        self.assertEqual(generate_room_code(), "EFGH")


class TestMoveIntegration(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        rooms.clear()
        self.player1 = FakeWebSocket()
        self.player2 = FakeWebSocket()
        self.room = {
            "code": "TEST",
            "players": [
                {
                    "name": "Gustavo",
                    "websocket": self.player1,
                    "player_number": PLAYER_1,
                },
                {
                    "name": "João",
                    "websocket": self.player2,
                    "player_number": PLAYER_2,
                },
            ],
            "board": create_board(),
            "turn": PLAYER_1,
            "status": "playing",
            "rematch_requests": set(),
            "next_starting_player": PLAYER_2,
        }
        rooms["TEST"] = self.room

    def tearDown(self):
        rooms.clear()

    async def test_move_out_of_turn_is_rejected(self):
        await handle_move(self.player2, {"column": 0})

        self.assertEqual(self.player2.messages[-1]["type"], "error")
        self.assertEqual(self.player2.messages[-1]["message"], "Não é a sua vez.")
        self.assertEqual(self.room["board"], create_board())
        self.assertEqual(self.room["turn"], PLAYER_1)

    async def test_invalid_column_is_rejected(self):
        for column in (True, -1, 7):
            with self.subTest(column=column):
                await handle_move(self.player1, {"column": column})
                self.assertEqual(self.player1.messages[-1]["message"], "Coluna inválida.")

        self.assertEqual(self.room["board"], create_board())
        self.assertEqual(self.room["turn"], PLAYER_1)

    async def test_full_column_is_rejected(self):
        for row in range(ROWS):
            self.room["board"][row][0] = PLAYER_1 if row % 2 == 0 else PLAYER_2
        board_before_move = [row[:] for row in self.room["board"]]

        await handle_move(self.player1, {"column": 0})

        self.assertEqual(self.player1.messages[-1]["message"], "A coluna está cheia.")
        self.assertEqual(self.room["board"], board_before_move)
        self.assertEqual(self.room["turn"], PLAYER_1)

    async def test_valid_move_changes_turn(self):
        await handle_move(self.player1, {"column": 3})

        self.assertEqual(self.room["turn"], PLAYER_2)
        self.assertEqual(self.player1.messages[-1]["type"], "game_state")
        self.assertEqual(self.player2.messages[-1]["turn"], PLAYER_2)

    async def test_valid_move_changes_board(self):
        await handle_move(self.player1, {"column": 3})

        self.assertEqual(self.room["board"][ROWS - 1][3], PLAYER_1)

    async def test_win_finishes_game(self):
        for column in range(3):
            self.room["board"][ROWS - 1][column] = PLAYER_1

        await handle_move(self.player1, {"column": 3})

        self.assertEqual(self.room["status"], "finished")
        self.assertEqual(self.room["turn"], PLAYER_1)
        self.assertEqual(self.player1.messages[-1]["type"], "game_over")
        self.assertEqual(self.player1.messages[-1]["result"], "win")
        self.assertEqual(self.player2.messages[-1]["winner"], PLAYER_1)

    async def test_move_after_finished_game_is_rejected(self):
        self.room["status"] = "finished"
        board_before_move = [row[:] for row in self.room["board"]]

        await handle_move(self.player1, {"column": 0})

        self.assertEqual(self.player1.messages[-1]["message"], "A partida já terminou.")
        self.assertEqual(self.room["board"], board_before_move)
        self.assertEqual(self.player2.messages, [])

    async def test_draw_finishes_game(self):
        self.room["board"] = [
            [0, 1, 2, 2, 1, 1, 2],
            [2, 2, 1, 1, 2, 2, 1],
            [1, 1, 2, 2, 1, 1, 2],
            [2, 2, 1, 1, 2, 2, 1],
            [1, 1, 2, 2, 1, 1, 2],
            [2, 2, 1, 1, 2, 2, 1],
        ]

        await handle_move(self.player1, {"column": 0})

        self.assertEqual(self.room["status"], "finished")
        self.assertEqual(self.player1.messages[-1]["result"], "draw")
        self.assertIsNone(self.player2.messages[-1]["winner"])


class TestRematchIntegration(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        rooms.clear()
        self.player1 = FakeWebSocket()
        self.player2 = FakeWebSocket()
        self.room = {
            "code": "TEST",
            "players": [
                {
                    "name": "Gustavo",
                    "websocket": self.player1,
                    "player_number": PLAYER_1,
                },
                {
                    "name": "João",
                    "websocket": self.player2,
                    "player_number": PLAYER_2,
                },
            ],
            "board": create_board(),
            "turn": PLAYER_1,
            "status": "finished",
            "rematch_requests": set(),
            "next_starting_player": PLAYER_2,
        }
        rooms["TEST"] = self.room

    def tearDown(self):
        rooms.clear()

    async def test_rematch_during_active_game_is_rejected(self):
        self.room["status"] = "playing"

        await handle_rematch_request(self.player1)

        self.assertEqual(self.player1.messages[-1]["type"], "error")
        self.assertEqual(self.room["rematch_requests"], set())

    async def test_first_player_requests_rematch(self):
        await handle_rematch_request(self.player1)

        self.assertEqual(self.room["rematch_requests"], {PLAYER_1})
        self.assertEqual(self.room["status"], "finished")
        self.assertEqual(self.player1.messages[-1]["type"], "rematch_status")
        self.assertEqual(self.player2.messages[-1]["accepted_players"], [PLAYER_1])

    async def test_duplicate_request_does_not_restart_game(self):
        old_board = self.room["board"]

        await handle_rematch_request(self.player1)
        await handle_rematch_request(self.player1)

        self.assertIs(self.room["board"], old_board)
        self.assertEqual(self.room["status"], "finished")
        self.assertEqual(self.room["rematch_requests"], {PLAYER_1})
        self.assertEqual(self.player1.messages[-1]["type"], "error")

    async def test_second_acceptance_starts_rematch(self):
        self.room["board"][ROWS - 1][0] = PLAYER_1
        old_board = self.room["board"]

        await handle_rematch_request(self.player1)
        await handle_rematch_request(self.player2)

        self.assertIsNot(self.room["board"], old_board)
        self.assertEqual(self.room["board"], create_board())
        self.assertEqual(self.room["status"], "playing")
        self.assertEqual(self.room["turn"], PLAYER_2)
        self.assertEqual(self.room["rematch_requests"], set())
        self.assertEqual(self.player1.messages[-1]["type"], "rematch_started")
        self.assertEqual(self.player2.messages[-1]["board"], create_board())

    async def test_starting_player_alternates_between_rematches(self):
        await handle_rematch_request(self.player1)
        await handle_rematch_request(self.player2)
        self.assertEqual(self.room["turn"], PLAYER_2)

        self.room["status"] = "finished"
        await handle_rematch_request(self.player1)
        await handle_rematch_request(self.player2)

        self.assertEqual(self.room["turn"], PLAYER_1)
        self.assertEqual(self.room["next_starting_player"], PLAYER_2)

    async def test_disconnect_cancels_pending_rematch(self):
        await handle_rematch_request(self.player1)

        await remove_disconnected_player(self.player2)

        self.assertEqual(self.room["rematch_requests"], set())
        self.assertEqual(self.room["status"], "waiting")
        self.assertEqual(len(self.room["players"]), 1)
        self.assertEqual(self.player1.messages[-1]["type"], "player_disconnected")

    async def test_rematch_with_one_player_is_rejected(self):
        self.room["players"].pop()

        await handle_rematch_request(self.player1)

        self.assertEqual(self.player1.messages[-1]["type"], "error")
        self.assertEqual(self.room["rematch_requests"], set())


class TestLeaveRoomIntegration(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        rooms.clear()
        self.player1 = FakeWebSocket()
        self.player2 = FakeWebSocket()
        self.room = {
            "code": "TEST",
            "players": [
                {
                    "name": "Gustavo",
                    "websocket": self.player1,
                    "player_number": PLAYER_1,
                },
                {
                    "name": "João",
                    "websocket": self.player2,
                    "player_number": PLAYER_2,
                },
            ],
            "board": create_board(),
            "turn": PLAYER_2,
            "status": "finished",
            "rematch_requests": {PLAYER_1},
            "next_starting_player": PLAYER_1,
        }
        self.room["board"][ROWS - 1][0] = PLAYER_1
        rooms["TEST"] = self.room

    def tearDown(self):
        rooms.clear()

    async def test_player_leaves_and_room_returns_to_waiting_state(self):
        await handle_leave_room(self.player1)

        room_code, _, _ = find_player_room(self.player1)
        self.assertIsNone(room_code)
        self.assertEqual(self.player1.messages[-1]["type"], "left_room")
        self.assertEqual(len(self.room["players"]), 1)
        self.assertIs(self.room["players"][0]["websocket"], self.player2)
        self.assertEqual(self.room["status"], "waiting")
        self.assertEqual(self.room["turn"], PLAYER_1)
        self.assertEqual(self.room["board"], create_board())
        self.assertEqual(self.room["next_starting_player"], PLAYER_2)
        self.assertEqual(self.room["rematch_requests"], set())
        self.assertEqual(self.player2.messages[-1]["type"], "player_disconnected")
        self.assertEqual(
            self.player2.messages[-1]["message"],
            "O outro jogador saiu da sala.",
        )

    async def test_last_player_leaving_removes_empty_room(self):
        self.room["players"] = [self.room["players"][0]]

        await handle_leave_room(self.player1)

        self.assertNotIn("TEST", rooms)
        self.assertEqual(self.player1.messages[-1]["type"], "left_room")

    async def test_player_can_create_another_room_after_leaving(self):
        await handle_leave_room(self.player1)

        await create_room(self.player1, {"player_name": "Gustavo"})

        new_room_code, new_room, player = find_player_room(self.player1)
        self.assertIsNotNone(new_room_code)
        self.assertIsNot(new_room, self.room)
        self.assertEqual(player["name"], "Gustavo")
        self.assertEqual(self.player1.messages[-1]["type"], "room_created")

    async def test_leave_outside_room_returns_controlled_error(self):
        outsider = FakeWebSocket()

        await handle_leave_room(outsider)

        self.assertEqual(outsider.messages[-1]["type"], "error")
        self.assertEqual(
            outsider.messages[-1]["message"],
            "Você não participa de uma sala.",
        )
        self.assertIn("TEST", rooms)


if __name__ == "__main__":
    unittest.main()

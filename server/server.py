import asyncio
import json
import random
import string

import websockets
from websockets.exceptions import ConnectionClosed

try:
    from .game import COLS, check_winner, create_board, is_draw, is_valid_move, make_move
except ImportError:
    from game import COLS, check_winner, create_board, is_draw, is_valid_move, make_move


rooms = {}
rooms_lock = asyncio.Lock()


def generate_room_code():
    while True:
        code = "".join(random.choices(string.ascii_uppercase, k=4))
        if code not in rooms:
            return code


def find_player_room(websocket):
    for room_code, room in rooms.items():
        for player in room["players"]:
            if player["websocket"] is websocket:
                return room_code, room, player
    return None, None, None


async def send_json(websocket, data):
    await websocket.send(json.dumps(data, ensure_ascii=False))


async def send_error(websocket, message):
    await send_json(websocket, {"type": "error", "message": message})


async def broadcast(players, message):
    for player in list(players):
        try:
            await send_json(player["websocket"], message)
        except ConnectionClosed:
            pass


def build_game_state(room):
    return {
        "type": "game_state",
        "board": [row[:] for row in room["board"]],
        "turn": room["turn"],
        "status": room["status"],
    }


async def create_room(websocket, data):
    player_name = data.get("player_name")
    if not isinstance(player_name, str) or not player_name.strip():
        await send_error(websocket, "Nome do jogador não pode estar vazio.")
        return

    player_name = player_name.strip()

    async with rooms_lock:
        current_room_code, _, _ = find_player_room(websocket)
        if current_room_code is not None:
            response = {"type": "error", "message": "Você já participa de uma sala."}
        else:
            room_code = generate_room_code()
            rooms[room_code] = {
                "code": room_code,
                "players": [
                    {
                        "name": player_name,
                        "websocket": websocket,
                        "player_number": 1,
                    }
                ],
                "board": create_board(),
                "turn": 1,
                "status": "waiting",
                "rematch_requests": set(),
                "next_starting_player": 2,
            }
            response = {
                "type": "room_created",
                "room_code": room_code,
                "player_number": 1,
            }

    await send_json(websocket, response)


async def join_room(websocket, data):
    player_name = data.get("player_name")
    room_code = data.get("room_code")

    if not isinstance(player_name, str) or not player_name.strip():
        await send_error(websocket, "Nome do jogador não pode estar vazio.")
        return
    if not isinstance(room_code, str) or not room_code.strip():
        await send_error(websocket, "Código da sala não pode estar vazio.")
        return

    player_name = player_name.strip()
    room_code = room_code.strip().upper()
    players_to_notify = None
    game_ready = None
    game_state = None

    async with rooms_lock:
        current_room_code, _, _ = find_player_room(websocket)

        if current_room_code is not None:
            response = {"type": "error", "message": "Você já participa de uma sala."}
        elif room_code not in rooms:
            response = {"type": "error", "message": "Sala inexistente."}
        elif len(rooms[room_code]["players"]) >= 2:
            response = {"type": "error", "message": "Sala cheia."}
        else:
            room = rooms[room_code]
            used_numbers = {player["player_number"] for player in room["players"]}
            player_number = 1 if 1 not in used_numbers else 2
            room["players"].append(
                {
                    "name": player_name,
                    "websocket": websocket,
                    "player_number": player_number,
                }
            )
            room["status"] = "playing"

            response = {
                "type": "room_joined",
                "room_code": room_code,
                "player_number": player_number,
            }
            players_to_notify = list(room["players"])
            game_ready = {
                "type": "game_ready",
                "room_code": room_code,
                "players": [
                    {
                        "name": player["name"],
                        "player_number": player["player_number"],
                    }
                    for player in room["players"]
                ],
                "turn": room["turn"],
            }
            game_state = build_game_state(room)

    await send_json(websocket, response)

    if game_ready is not None:
        await broadcast(players_to_notify, game_ready)
        await broadcast(players_to_notify, game_state)


async def handle_move(websocket, data):
    error_message = None
    players_to_notify = None
    game_message = None

    async with rooms_lock:
        _, room, player = find_player_room(websocket)

        if room is None:
            error_message = "Você não participa de uma sala."
        elif room["status"] == "finished":
            error_message = "A partida já terminou."
        elif room["status"] != "playing":
            error_message = "A partida ainda não começou."
        elif len(room["players"]) != 2:
            error_message = "A partida ainda não começou."
        elif room["turn"] != player["player_number"]:
            error_message = "Não é a sua vez."
        else:
            column = data.get("column")

            if type(column) is not int or not 0 <= column < COLS:
                error_message = "Coluna inválida."
            elif not is_valid_move(room["board"], column):
                error_message = "A coluna está cheia."
            else:
                player_number = player["player_number"]
                make_move(room["board"], column, player_number)
                players_to_notify = list(room["players"])

                if check_winner(room["board"], player_number):
                    room["status"] = "finished"
                    game_message = {
                        "type": "game_over",
                        "result": "win",
                        "winner": player_number,
                        "board": [row[:] for row in room["board"]],
                    }
                elif is_draw(room["board"]):
                    room["status"] = "finished"
                    game_message = {
                        "type": "game_over",
                        "result": "draw",
                        "winner": None,
                        "board": [row[:] for row in room["board"]],
                    }
                else:
                    room["turn"] = 2 if player_number == 1 else 1
                    game_message = build_game_state(room)

    if error_message is not None:
        await send_error(websocket, error_message)
    else:
        await broadcast(players_to_notify, game_message)


async def handle_rematch_request(websocket):
    error_message = None
    players_to_notify = None
    rematch_message = None

    async with rooms_lock:
        _, room, player = find_player_room(websocket)

        if room is None:
            error_message = "Você não participa de uma sala."
        elif len(room["players"]) != 2:
            error_message = "A revanche exige dois jogadores conectados."
        elif room["status"] != "finished":
            error_message = "A revanche só pode ser solicitada após o fim da partida."
        elif player["player_number"] in room["rematch_requests"]:
            error_message = "Você já solicitou revanche."
        else:
            room["rematch_requests"].add(player["player_number"])
            players_to_notify = list(room["players"])

            if len(room["rematch_requests"]) == 2:
                room["board"] = create_board()
                room["turn"] = room["next_starting_player"]
                room["next_starting_player"] = 1 if room["turn"] == 2 else 2
                room["status"] = "playing"
                room["rematch_requests"].clear()
                rematch_message = {
                    "type": "rematch_started",
                    "board": [row[:] for row in room["board"]],
                    "turn": room["turn"],
                    "status": room["status"],
                }
            else:
                rematch_message = {
                    "type": "rematch_status",
                    "accepted_players": sorted(room["rematch_requests"]),
                }

    if error_message is not None:
        await send_error(websocket, error_message)
    else:
        await broadcast(players_to_notify, rematch_message)


async def remove_disconnected_player(websocket):
    players_to_notify = None

    async with rooms_lock:
        room_code, room, player = find_player_room(websocket)
        if room_code is None:
            return

        room["players"].remove(player)
        room["rematch_requests"].clear()

        if room["players"]:
            room["status"] = "waiting"
            room["turn"] = 1
            players_to_notify = list(room["players"])
        else:
            del rooms[room_code]

    if players_to_notify:
        await broadcast(
            players_to_notify,
            {
                "type": "player_disconnected",
                "message": "O outro jogador desconectou.",
            },
        )


async def handle_connection(websocket):
    print("Cliente conectado.")

    try:
        async for message in websocket:
            print(f"Mensagem recebida: {message}")

            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                await send_error(websocket, "JSON inválido.")
                continue

            if not isinstance(data, dict):
                await send_error(websocket, "O JSON deve ser um objeto.")
            elif "type" not in data:
                await send_error(websocket, "Campo 'type' ausente.")
            elif data["type"] == "create_room":
                await create_room(websocket, data)
            elif data["type"] == "join_room":
                await join_room(websocket, data)
            elif data["type"] == "move":
                await handle_move(websocket, data)
            elif data["type"] == "rematch_request":
                await handle_rematch_request(websocket)
            elif data["type"] == "message":
                content = data.get("content")
                if not isinstance(content, str):
                    await send_error(websocket, "Campo 'content' inválido.")
                else:
                    await send_json(
                        websocket,
                        {
                            "type": "message_response",
                            "content": f"Servidor recebeu: {content}",
                        },
                    )
            else:
                await send_error(websocket, "Tipo de mensagem desconhecido.")
    except ConnectionClosed:
        pass
    finally:
        await remove_disconnected_player(websocket)
        print("Cliente desconectado.")


async def main():
    async with websockets.serve(handle_connection, "localhost", 8765):
        print("Servidor WebSocket iniciado em ws://localhost:8765")
        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

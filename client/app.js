const connectionStatusElement = document.getElementById("connection-status");
const playerNameInput = document.getElementById("player-name");
const roomCodeInput = document.getElementById("room-code");
const createRoomButton = document.getElementById("create-room-button");
const joinRoomButton = document.getElementById("join-room-button");
const roomStatusElement = document.getElementById("room-status");
const gameStatusElement = document.getElementById("game-status");
const rematchButton = document.getElementById("rematch-button");
const boardElement = document.getElementById("board");
const connectionBadge = document.getElementById("connection-badge");
const lobbyPanel = document.getElementById("lobby-panel");
const gamePanel = document.getElementById("game-panel");
const roomCodeDisplay = document.getElementById("room-code-display");
const player1NameElement = document.getElementById("player-1-name");
const player2NameElement = document.getElementById("player-2-name");
const player1Card = document.getElementById("player-1-card");
const player2Card = document.getElementById("player-2-card");

let playerNumber = null;
let gameActive = false;
let rematchRequested = false;

const socket = new WebSocket("ws://localhost:8765");

function setConnectionStatus(text, statusClass) {
    connectionStatusElement.textContent = text;
    connectionBadge.className = `connection-badge ${statusClass}`;
}

function setNotice(message, tone = "") {
    roomStatusElement.textContent = message;
    roomStatusElement.className = `notice${tone ? ` notice-${tone}` : ""}`;
}

function setGameStatus(message, statusClass) {
    gameStatusElement.textContent = message;
    gameStatusElement.className = `game-status ${statusClass}`;
}

function updatePlayerIdentity() {
    player1Card.classList.toggle("is-you", playerNumber === 1);
    player2Card.classList.toggle("is-you", playerNumber === 2);
}

function showGamePanel(roomCode) {
    lobbyPanel.hidden = true;
    gamePanel.hidden = false;
    roomCodeDisplay.textContent = roomCode;
    updatePlayerIdentity();
}

function setBoardAvailability(isActive) {
    boardElement.classList.toggle("board-disabled", !isActive);
}

socket.onopen = () => {
    setConnectionStatus("Conectado", "status-connected");
};

socket.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.type === "room_created") {
        playerNumber = data.player_number;
        rematchButton.hidden = true;
        player1NameElement.textContent = playerNameInput.value.trim() || "Jogador 1";
        player2NameElement.textContent = "Aguardando...";
        showGamePanel(data.room_code);
        setNotice(
            `Sala ${data.room_code} criada. Aguardando outro jogador...`,
        );
    } else if (data.type === "room_joined") {
        playerNumber = data.player_number;
        rematchButton.hidden = true;
        player2NameElement.textContent = playerNameInput.value.trim() || "Jogador 2";
        showGamePanel(data.room_code);
        setNotice(`Você entrou na sala ${data.room_code}.`, "success");
    } else if (data.type === "game_ready") {
        const player1 = data.players.find((player) => player.player_number === 1);
        const player2 = data.players.find((player) => player.player_number === 2);

        showGamePanel(data.room_code);
        player1NameElement.textContent = player1.name;
        player2NameElement.textContent = player2.name;
        setNotice("Partida pronta!", "success");
    } else if (data.type === "game_state") {
        renderBoard(data.board);
        gameActive = data.status === "playing";
        rematchButton.hidden = true;
        setBoardAvailability(gameActive);

        const turnMessage = data.turn === playerNumber
            ? "Sua vez!"
            : "Aguarde o adversário.";
        setGameStatus(
            `Vez do Jogador ${data.turn} - ${turnMessage}`,
            data.turn === playerNumber ? "status-turn" : "status-waiting",
        );
    } else if (data.type === "game_over") {
        renderBoard(data.board);
        gameActive = false;
        setBoardAvailability(false);
        rematchRequested = false;
        rematchButton.hidden = false;
        rematchButton.disabled = false;
        rematchButton.textContent = "Solicitar revanche";

        if (data.result === "draw") {
            setGameStatus("Empate!", "status-draw");
        } else if (data.winner === playerNumber) {
            setGameStatus("Você venceu!", "status-win");
        } else {
            setGameStatus(
                `Você perdeu. Jogador ${data.winner} venceu.`,
                "status-loss",
            );
        }
    } else if (data.type === "rematch_status" && !gameActive) {
        rematchButton.hidden = false;

        if (data.accepted_players.includes(playerNumber)) {
            rematchRequested = true;
            rematchButton.disabled = true;
            setNotice(
                "Revanche solicitada. Aguardando adversário...",
            );
        } else {
            rematchRequested = false;
            rematchButton.disabled = false;
            rematchButton.textContent = "Aceitar revanche";
            setNotice("O adversário quer uma revanche.");
        }
    } else if (data.type === "rematch_started") {
        renderBoard(data.board);
        gameActive = data.status === "playing";
        setBoardAvailability(gameActive);
        rematchRequested = false;
        rematchButton.hidden = true;
        rematchButton.disabled = false;
        rematchButton.textContent = "Solicitar revanche";
        setNotice("Revanche iniciada.", "success");

        const turnMessage = data.turn === playerNumber
            ? "Sua vez!"
            : "Aguarde o adversário.";
        setGameStatus(
            `Vez do Jogador ${data.turn} - ${turnMessage}`,
            data.turn === playerNumber ? "status-turn" : "status-waiting",
        );
    } else if (data.type === "player_disconnected") {
        gameActive = false;
        setBoardAvailability(false);
        rematchRequested = false;
        rematchButton.hidden = true;
        setNotice(data.message, "error");
        setGameStatus("Partida interrompida.", "status-alert");
    } else if (data.type === "error") {
        if (!gameActive && !rematchButton.hidden) {
            rematchRequested = false;
            rematchButton.disabled = false;
        }
        setNotice(data.message, "error");
    }
};

socket.onclose = () => {
    gameActive = false;
    setBoardAvailability(false);
    rematchButton.hidden = true;
    setConnectionStatus("Desconectado", "status-disconnected");
};

socket.onerror = () => {
    setConnectionStatus("Erro de conexão", "status-error");
};

createRoomButton.addEventListener("click", () => {
    if (socket.readyState !== WebSocket.OPEN) {
        setNotice("WebSocket não está conectado.", "error");
        return;
    }

    socket.send(
        JSON.stringify({
            type: "create_room",
            player_name: playerNameInput.value.trim(),
        }),
    );
});

function renderBoard(board) {
    boardElement.replaceChildren();

    board.forEach((row, rowIndex) => {
        row.forEach((value, columnIndex) => {
            const cell = document.createElement("button");
            cell.type = "button";
            cell.className = "cell";
            cell.classList.add(
                value === 1 ? "player-1" : value === 2 ? "player-2" : "empty",
            );
            cell.dataset.column = columnIndex;
            cell.setAttribute(
                "aria-label",
                `Linha ${rowIndex + 1}, coluna ${columnIndex + 1}`,
            );
            boardElement.appendChild(cell);
        });
    });
}

boardElement.addEventListener("click", (event) => {
    const cell = event.target.closest(".cell");

    if (cell === null || !gameActive || socket.readyState !== WebSocket.OPEN) {
        return;
    }

    socket.send(
        JSON.stringify({
            type: "move",
            column: Number(cell.dataset.column),
        }),
    );
});

rematchButton.addEventListener("click", () => {
    if (
        socket.readyState !== WebSocket.OPEN ||
        gameActive ||
        rematchRequested
    ) {
        return;
    }

    rematchRequested = true;
    rematchButton.disabled = true;
    socket.send(JSON.stringify({ type: "rematch_request" }));
});

const emptyBoard = Array.from({ length: 6 }, () => Array(7).fill(0));
renderBoard(emptyBoard);
setBoardAvailability(false);

joinRoomButton.addEventListener("click", () => {
    if (socket.readyState !== WebSocket.OPEN) {
        setNotice("WebSocket não está conectado.", "error");
        return;
    }

    const roomCode = roomCodeInput.value.trim().toUpperCase();
    roomCodeInput.value = roomCode;

    socket.send(
        JSON.stringify({
            type: "join_room",
            player_name: playerNameInput.value.trim(),
            room_code: roomCode,
        }),
    );
});

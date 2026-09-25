# Connect Four Multiplayer com WebSocket

Jogo Connect Four (Lig-4) multiplayer em tempo real, desenvolvido para demonstrar comunicacao bidirecional com WebSocket entre um servidor Python e clientes JavaScript no navegador.

O projeto foi mantido simples para fins academicos: nao usa framework no cliente, banco de dados, autenticacao, Docker ou servicos externos.

## Arquitetura

```text
Cliente HTML/CSS/JavaScript
        |
        | WebSocket / JSON
        v
Servidor Python com asyncio
        |
        v
Estado oficial das salas e partidas
```

O servidor e a autoridade sobre salas, jogadores, tabuleiro, turnos, chat e cronometro. O cliente apenas envia acoes e renderiza os estados recebidos.

Arquivos principais:

```text
client/index.html   Estrutura da interface
client/style.css    Estilos da tela do jogo
client/app.js       Conexao WebSocket e renderizacao do cliente
server/game.py      Regras puras do Connect Four
server/server.py    Servidor WebSocket, salas, chat, timer e concorrencia
server/test_game.py Testes das regras do jogo
server/test_server.py Testes de integracao do servidor
```

## Funcionalidades

- Criacao de salas por codigo de quatro letras.
- Entrada de um segundo jogador na mesma sala.
- Jogo em tempo real usando uma conexao WebSocket por cliente.
- Servidor validando jogadas, turnos, vitoria e empate.
- Salas independentes.
- Chat WebSocket por sala, sem HTTP extra.
- Cronometro de 30 segundos por turno controlado pelo servidor.
- Perda de vez quando o tempo acaba.
- Revanche com aceite dos dois jogadores.
- Tratamento de saida e desconexao.

## Instalacao

Na raiz do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r server/requirements.txt
```

Se o PowerShell bloquear a ativacao:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Como Executar Em Um Computador

Terminal 1:

```powershell
.\.venv\Scripts\python.exe server/server.py
```

Terminal 2:

```powershell
python -m http.server 8000 --directory client
```

Abra duas abas:

```text
http://localhost:8000
```

Em uma aba, informe o nome e crie a sala. Na outra, informe outro nome e entre com o codigo exibido.

## Salas

Cada sala tem:

- codigo;
- lista de jogadores conectados;
- tabuleiro;
- jogador da vez;
- status (`waiting`, `playing` ou `finished`);
- pedidos de revanche;
- task de cronometro do turno atual.

Mensagens de jogo e chat sao enviadas somente aos jogadores da sala correspondente.

## Chat

O chat usa a mesma conexao WebSocket do jogo. O cliente envia `chat_message`; o servidor identifica o autor pela propria conexao WebSocket, valida a mensagem e faz broadcast apenas para a sala.

Validacoes:

- mensagem deve ser texto;
- mensagem vazia e recusada;
- limite de `200` caracteres;
- cliente fora de sala recebe erro.

No navegador, mensagens recebidas sao inseridas com `textContent`, evitando interpretar conteudo enviado por outro jogador como HTML.

## Cronometro

Cada turno tem 30 segundos. O servidor cria uma `asyncio.Task` para a sala quando a partida comeca, quando uma jogada valida troca o turno e quando uma revanche inicia.

Quando o tempo acaba:

- o servidor troca o turno;
- nenhuma jogada automatica e feita;
- um novo timer de 30 segundos e iniciado;
- os clientes recebem `game_state` com o novo `turn` e `turn_deadline`.

O JavaScript usa `turn_deadline` apenas para mostrar a contagem visual. A regra real de timeout fica no servidor.

Timers sao cancelados quando:

- uma jogada valida acontece;
- a partida termina por vitoria ou empate;
- um jogador sai ou desconecta;
- a sala e removida;
- uma revanche reinicia a partida.

## Concorrencia

O servidor usa `asyncio` para lidar com varias conexoes WebSocket de forma concorrente. O dicionario global `rooms` e protegido por `asyncio.Lock`.

O padrao usado nos handlers e:

1. adquirir o lock;
2. validar e alterar o estado da sala;
3. preparar a mensagem de resposta;
4. liberar o lock;
5. enviar mensagens pela rede.

Isso evita segurar o lock durante operacoes de rede. Para o cronometro, cada sala possui `timer_version`; quando uma jogada e um timeout acontecem quase ao mesmo tempo, a acao atrasada percebe que a versao mudou e nao troca o turno novamente.

## Protocolo WebSocket

As mensagens sao JSON.

Cliente para servidor:

```json
{ "type": "create_room", "player_name": "Ana" }
{ "type": "join_room", "room_code": "ABCD", "player_name": "Bruno" }
{ "type": "move", "column": 3 }
{ "type": "chat_message", "message": "Boa jogada!" }
{ "type": "rematch_request" }
{ "type": "leave_room" }
```

Servidor para cliente:

```json
{ "type": "room_created", "room_code": "ABCD", "player_number": 1 }
{ "type": "room_joined", "room_code": "ABCD", "player_number": 2 }
{ "type": "game_ready", "room_code": "ABCD", "players": [], "turn": 1 }
```

Estado da partida:

```json
{
  "type": "game_state",
  "board": [[0, 0, 0, 0, 0, 0, 0]],
  "turn": 1,
  "status": "playing",
  "turn_time_limit": 30,
  "turn_deadline": 1790340000.5
}
```

Chat:

```json
{
  "type": "chat_message",
  "player": 1,
  "player_name": "Ana",
  "message": "Boa jogada!"
}
```

Fim de jogo e revanche:

```json
{ "type": "game_over", "result": "win", "winner": 1, "board": [] }
{ "type": "game_over", "result": "draw", "winner": null, "board": [] }
{ "type": "rematch_status", "accepted_players": [1] }
{ "type": "rematch_started", "board": [], "turn": 2, "status": "playing" }
```

Saida, desconexao e erro:

```json
{ "type": "left_room" }
{ "type": "player_disconnected", "message": "O outro jogador desconectou." }
{ "type": "error", "message": "Mensagem de erro" }
```

O servidor ainda mantem o tipo legado `message`/`message_response`, usado apenas como eco simples.

## Logs

O servidor imprime logs didaticos, por exemplo:

```text
[WS] Cliente conectado.
[ROOM] Sala ABCD criada por jogador 1.
[ROOM] Jogador 2 entrou na sala ABCD.
[GAME] Sala ABCD: jogador 1 -> coluna 3.
[CHAT] Sala ABCD: jogador 2 enviou mensagem.
[TIMER] Sala ABCD: tempo do jogador 1 expirou.
[WS] Cliente desconectado.
```

## Testes

Execute:

```powershell
.\.venv\Scripts\python.exe -m unittest server.test_game server.test_server -v
```

A suite cobre regras do Connect Four, criacao e entrada em salas, jogadas, revanche, saida, chat, cronometro, limpeza de tasks e uma corrida entre jogada e timeout.

Na ultima execucao local, `47` testes passaram e `0` falharam.

## Demonstracao Sugerida

1. Inicie o servidor WebSocket local.
2. Inicie o servidor HTTP do cliente.
3. Abra `http://localhost:8000` em duas abas.
4. Crie uma sala e entre nela pelo codigo.
5. Mostre uma jogada sendo validada pelo servidor.
6. Envie mensagens no chat.
7. Aguarde o cronometro expirar para mostrar a perda de vez.
8. Finalize a partida e solicite revanche.

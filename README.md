# Connect Four Multiplayer com WebSocket

Jogo Connect Four (Lig-4) multiplayer em tempo real, desenvolvido para demonstrar comunicação bidirecional com WebSocket entre um servidor Python e clientes JavaScript executados no navegador.

## Tecnologias

- Python
- asyncio
- websockets
- JavaScript
- HTML
- CSS
- JSON
- unittest

## Arquitetura

```text
Cliente (HTML/CSS/JavaScript)
              ↕ WebSocket
        Servidor Python
              ↓
    Estado global das salas
```

O servidor mantém o estado oficial das salas e partidas, incluindo jogadores, tabuleiro, turno e status. O cliente envia ações, como criar uma sala, entrar nela ou selecionar uma coluna. O servidor valida cada ação, altera o estado quando permitido e distribui o novo estado aos clientes conectados.

Essa separação impede que o navegador decida localmente se uma jogada é válida, onde uma peça deve cair ou quem venceu a partida.

## Funcionalidades

- Criação de salas com código aleatório de quatro letras.
- Entrada de um segundo jogador pelo código da sala.
- Multiplayer em tempo real para dois jogadores.
- Tabuleiro tradicional de 6 linhas por 7 colunas.
- Controle de turnos pelo servidor.
- Validação de jogadas e colunas disponíveis.
- Detecção de vitórias horizontais, verticais e diagonais.
- Detecção de empate.
- Tratamento de desconexões.
- Revanche iniciada após a aceitação dos dois jogadores.
- Alternância do jogador inicial entre revanches.

## Protocolo WebSocket

O navegador inicia a conexão com um handshake HTTP que solicita a atualização do protocolo para WebSocket. Depois do handshake, a conexão permanece aberta e permite o envio bidirecional de mensagens sem criar uma nova requisição HTTP para cada ação.

As mensagens são objetos JSON. Por exemplo, ao selecionar uma coluna, o cliente envia:

```json
{
  "type": "move",
  "column": 3
}
```

Após validar e executar uma jogada normal, o servidor pode responder aos dois jogadores com:

```json
{
  "type": "game_state",
  "board": [
    [0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 1, 0, 0, 0]
  ],
  "turn": 2,
  "status": "playing"
}
```

Outros tipos importantes incluem `create_room`, `join_room`, `game_ready`, `game_over`, `rematch_request`, `rematch_started`, `player_disconnected` e `error`. Quando a conexão é encerrada, o servidor remove o jogador da sala, avisa o participante restante e elimina salas vazias.

## Concorrência

O servidor utiliza `asyncio` para atender múltiplas conexões WebSocket de forma concorrente em uma única thread de eventos. Cada cliente possui um fluxo assíncrono de recebimento de mensagens.

Como o dicionário global de salas é compartilhado entre essas conexões, operações críticas são protegidas por `asyncio.Lock`. Validação e alteração do estado acontecem dentro do lock, evitando que duas ações usem simultaneamente o mesmo turno ou a mesma vaga em uma sala. Os broadcasts são realizados depois da liberação do lock para que operações de rede não bloqueiem outras alterações de estado.

## Estrutura do projeto

```text
connect-four-websocket/
├── client/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── server/
│   ├── server.py
│   ├── game.py
│   ├── test_game.py
│   ├── test_server.py
│   └── requirements.txt
├── .gitignore
└── README.md
```

## Como executar

### Pré-requisitos

- Windows com Python 3 instalado.
- Git, caso o projeto seja obtido por clonagem.

### Instalação

1. Clone o repositório e entre na pasta do projeto:

   ```powershell
   git clone <URL_DO_REPOSITORIO>
   cd connect-four-websocket
   ```

2. Crie o ambiente virtual:

   ```powershell
   python -m venv .venv
   ```

3. Ative o ambiente no PowerShell:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

   Se a política de execução bloquear o script, utilize somente na sessão atual:

   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   .\.venv\Scripts\Activate.ps1
   ```

4. Instale a dependência do servidor:

   ```powershell
   python -m pip install -r server/requirements.txt
   ```

### Execução

1. Na raiz do projeto, inicie o servidor WebSocket:

   ```powershell
   python server/server.py
   ```

2. Em outro terminal, inicie um servidor HTTP para o cliente:

   ```powershell
   python -m http.server 8000 --directory client
   ```

3. Abra no navegador:

   ```text
   http://localhost:8000
   ```

Duas abas do navegador podem ser usadas para testar os dois jogadores localmente.

## Testes

Execute toda a suíte a partir da raiz do projeto:

```powershell
python -m unittest server.test_game server.test_server -v
```

No momento desta revisão, a suíte possui 29 casos cobrindo regras do Connect Four, códigos de sala, jogadas multiplayer, turnos, vitória, empate, encerramento e revanche.

## Demonstração

1. O Jogador 1 informa seu nome e cria uma sala.
2. O Jogador 2 informa seu nome e entra com o código recebido.
3. O servidor inicia a partida e envia o tabuleiro oficial.
4. As jogadas são validadas e sincronizadas entre os clientes.
5. O servidor detecta vitória ou empate e encerra a partida.
6. Os jogadores podem solicitar uma revanche na mesma sala.

## Autores

- Nome do integrante 1
- Nome do integrante 2
- Nome do integrante 3

## Contexto acadêmico

Projeto desenvolvido como atividade acadêmica de Sistemas Distribuídos/Redes para demonstrar comunicação WebSocket entre um servidor assíncrono em Python e um cliente em JavaScript.

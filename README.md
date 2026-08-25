# 🐍 Snake Royale

**A real-time multiplayer Snake game built from the ground up with Python, Pygame, TCP sockets, multithreading, and a custom application-layer protocol.**

Snake Royale turns the classic Snake game into a networked 1v1 multiplayer experience with live matchmaking, synchronized gameplay, spectators, private chat, player customization, and server-authoritative game logic.

The project explores the engineering behind real-time networked applications: **TCP message framing, concurrent connections, state synchronization, client-server architecture, game-loop design, and failure handling.**

<p align="center">
  <img src="assets/gameplay.png" alt="Snake Royale multiplayer gameplay" width="850">
</p>

---

## ✨ Features

### 🎮 Real-Time Multiplayer

* Competitive **1v1 Snake matches**
* Server-authoritative game simulation
* Fixed-rate game loop for synchronized state updates
* Five-second pre-match countdown
* Health-based collision system
* Timed matches with automatic winner/draw resolution

### 🌐 Multiplayer Lobby

* Live list of connected players
* Player availability states
* Direct player challenges
* Challenge acceptance and rejection
* Automatic lobby updates when player state changes

### 👀 Spectator System

* Connected users can spectate the active match
* Spectators receive the same live game-state updates as players
* Join and leave spectating without interrupting the match
* Spectator cheering system with temporary in-game messages

### 💬 Private Chat

* Direct messaging between connected users
* Per-user conversation history
* Unread-message counters
* Temporary chat notifications
* Server-side message validation and length limiting

### 🎨 Customization

* Player-selectable snake colors
* Customization synchronized through the server
* Color changes reflected in the lobby and active game state

### 🍰 Game Mechanics

* Health system rather than instant death
* Walls, obstacles, self-collisions, and player collisions
* Collision rollback to the last valid position
* Food collection and health rewards
* Periodic power pies
* Temporary **crown advantage** affecting player collisions
* Automatic spawning only on unoccupied board positions

---

## 📸 Screenshots

<table>
  <tr>
    <td align="center"><b>Multiplayer Lobby</b></td>
    <td align="center"><b>Live Match</b></td>
  </tr>
  <tr>
    <td><img src="assets/lobby.png" alt="Snake Royale lobby" width="440"></td>
    <td><img src="assets/gameplay.png" alt="Snake Royale gameplay" width="440"></td>
  </tr>
  <tr>
    <td align="center"><b>Player Customization</b></td>
    <td align="center"><b>Spectator Mode</b></td>
  </tr>
  <tr>
    <td><img src="assets/customization.png" alt="Snake customization" width="440"></td>
    <td><img src="assets/spectator.png" alt="Snake Royale spectator mode" width="440"></td>
  </tr>
</table>

---

## 🏗️ Architecture

Snake Royale uses a **TCP client-server architecture** in which the server owns the canonical game state.

```mermaid
flowchart LR
    C1["Player 1 Client<br/>Pygame UI"] -->|"TCP / JSON"| S["Snake Royale Server"]
    C2["Player 2 Client<br/>Pygame UI"] -->|"TCP / JSON"| S
    C3["Spectator Client<br/>Pygame UI"] -->|"TCP / JSON"| S

    S --> P["Protocol Layer<br/>Length-Prefixed Messages"]
    S --> G["Authoritative Game Engine"]
    S --> L["Lobby / Matchmaking"]
    S --> CH["Chat / Spectator Services"]

    G -->|"GAME_STATE"| S
    S -->|"Broadcast"| C1
    S -->|"Broadcast"| C2
    S -->|"Broadcast"| C3
```

Clients are responsible for **input and presentation**. The server is responsible for **validation, simulation, matchmaking, and game-state ownership**.

A player therefore does not directly update their snake's position. Instead:

1. The client captures a directional input.
2. An `INPUT` message is sent over TCP.
3. The server validates and stores the requested direction.
4. The authoritative game loop advances the simulation.
5. The resulting game state is serialized.
6. The server broadcasts the new state to both players and all spectators.
7. Each client renders the state locally.

This prevents individual clients from independently deciding the outcome of the simulation.

---

## 🔌 Custom TCP Protocol

TCP provides a reliable byte stream, but it does **not preserve application message boundaries**.

Snake Royale therefore implements its own message-framing protocol instead of assuming that one call to `recv()` corresponds to one complete message.

Each message is structured as:

```text
┌──────────────────────┬─────────────────────────────┐
│ 4-byte length header │ UTF-8 JSON message          │
│ Network byte order   │ {"type": ..., "payload":...}│
└──────────────────────┴─────────────────────────────┘
```

The sender:

1. Serializes the message to JSON.
2. Encodes it as UTF-8.
3. Calculates the payload length.
4. Packs that length into a **4-byte unsigned integer in network byte order**.
5. Sends the header and payload together.

The receiver first reads exactly four bytes to determine the message length, then continues reading until the entire payload has arrived.

This correctly handles cases where TCP splits a logical message across multiple packets or socket reads.

Example application message:

```json
{
  "type": "INPUT",
  "payload": {
    "direction": "UP"
  }
}
```

### Protocol Message Types

The application protocol supports events including:

```text
REGISTER
REGISTER_OK
REGISTER_FAIL

USER_LIST

CHALLENGE
CHALLENGE_RECEIVED
CHALLENGE_ACCEPT
CHALLENGE_REJECT

GAME_START
INPUT
GAME_STATE
GAME_OVER

SPECTATE_REQUEST
LEAVE_SPECTATE
CHEER

CHAT_SEND
CHAT_MESSAGE

CUSTOMIZATION_UPDATE

INFO
ERROR
```

Keeping message definitions in a dedicated protocol layer separates network transport from application logic.

---

## ⚙️ Server Design

The server manages:

* TCP connections
* User registration
* Online-player state
* Matchmaking
* Player customization
* Chat routing
* Spectator membership
* Player inputs
* Game simulation
* State broadcasts
* Client disconnections

### Concurrent Connections

Each accepted TCP connection is handled by its own daemon thread:

```text
                    ┌── Client Handler Thread ── Player A
TCP Server ─────────┼── Client Handler Thread ── Player B
                    ├── Client Handler Thread ── Spectator A
                    └── Client Handler Thread ── Spectator B
```

Shared server state is protected with a `threading.Lock`, including:

* connected clients
* usernames
* player statuses
* customization data
* pending challenges
* active-match state

The active match runs on a separate game-loop thread.

---

## ⏱️ Authoritative Game Loop

The simulation runs at a fixed:

```text
5 ticks / second
```

The server uses a monotonic high-resolution timer to schedule ticks and compensate for execution time between iterations.

At every tick, the server:

```text
Player inputs
     ↓
Validate directions
     ↓
Calculate next snake positions
     ↓
Resolve simultaneous movement
     ↓
Detect collisions
     ↓
Apply damage / rollback if needed
     ↓
Process food and power-ups
     ↓
Update timer and win conditions
     ↓
Serialize authoritative state
     ↓
Broadcast GAME_STATE
```

The client renders independently at a higher frame rate while gameplay decisions remain controlled by the server.

---

## 💥 Collision System

Snake Royale uses a more involved collision model than traditional instant-death Snake.

The game distinguishes between:

* board boundaries
* obstacles
* self-collisions
* collisions with the opponent
* simultaneous head-to-head collisions

For recoverable collisions, the server stores each snake's **last safe body state**.

If a snake hits a wall or obstacle:

```text
Invalid next position
        ↓
Restore last safe body
        ↓
Apply collision damage
        ↓
Continue match if health > 0
```

This avoids leaving the authoritative game state in an invalid position while supporting health-based gameplay.

Simultaneous movement for both snakes is calculated before either player's final position is committed, allowing head-to-head interactions to be handled consistently.

---

## 👑 Power-Pie Mechanic

Normal pies restore health.

After a configured number of regular pies, a **power pie** is spawned.

Collecting it grants the player the crown temporarily. During that period, collision behavior changes in favor of the crowned snake.

The effect expires after additional pies have been consumed, returning the match to its normal collision rules.

Pie spawning checks the current game state and selects only from unoccupied board positions, avoiding:

* snakes
* obstacles
* existing pies

---

## 🖥️ Client Architecture

The Pygame client separates networking from rendering and interface logic.

```text
                     ┌─ Connect Screen
                     ├─ Username Screen
                     ├─ Lobby Screen
Pygame Client ───────┼─ Customization
                     ├─ Game Screen
                     └─ Result Screen

                            ↕
                     Screen Manager

                            ↕
                       Client State

                            ↕
                     Network Client

                            ↕
                       TCP Server
```

The network client maintains a background receive thread so blocking socket reads do not freeze the Pygame interface.

Incoming network messages are placed into a queue and processed by the main client loop, keeping network I/O separate from UI rendering and event handling.

The application also uses a centralized screen manager and shared client state to coordinate transitions between connection, lobby, gameplay, spectating, and result screens.

---

## 🔄 Example Match Flow

```mermaid
sequenceDiagram
    participant A as Player A
    participant S as Server
    participant B as Player B
    participant V as Spectator

    A->>S: REGISTER
    B->>S: REGISTER
    S-->>A: USER_LIST
    S-->>B: USER_LIST

    A->>S: CHALLENGE Player B
    S-->>B: CHALLENGE_RECEIVED

    B->>S: CHALLENGE_ACCEPT
    S-->>A: GAME_START
    S-->>B: GAME_START

    V->>S: SPECTATE_REQUEST
    S-->>V: GAME_START (SPECTATOR)

    loop Fixed-rate server ticks
        A->>S: INPUT
        B->>S: INPUT
        S->>S: Advance authoritative simulation
        S-->>A: GAME_STATE
        S-->>B: GAME_STATE
        S-->>V: GAME_STATE
    end

    S-->>A: GAME_OVER
    S-->>B: GAME_OVER
    S-->>V: GAME_OVER
```

---

## 🛡️ Connection & Failure Handling

The networking layer includes several safeguards for real-world socket behavior:

* `TCP_NODELAY` minimizes latency from TCP's Nagle algorithm.
* `SO_KEEPALIVE` enables detection of broken connections.
* `SO_REUSEADDR` makes restarting the server easier.
* Failed sends are caught without crashing the entire server.
* Partial TCP reads are reconstructed by the protocol layer.
* Duplicate usernames are rejected.
* Clients must register before other commands are accepted.
* Invalid or unknown messages receive server-side errors.
* Disconnected players are removed from server state.
* Pending challenges involving disconnected users are cleared.
* If a player disconnects during a match, the opponent is declared the winner and spectators are returned to idle state.

---

## 🧠 Engineering Highlights

This project was designed around several systems-programming concepts:

**Application-layer protocol design**
A custom length-prefixed JSON protocol provides reliable message framing over TCP.

**Concurrency**
Independent client-handler threads allow the server to maintain multiple live TCP connections while a separate thread advances the game simulation.

**Synchronization**
Shared mutable server state is protected with locking to avoid unsafe concurrent access.

**Authoritative state**
Game outcomes are determined by one server simulation rather than independently by each client.

**Real-time state distribution**
The latest authoritative game state is continuously serialized and broadcast to all relevant clients.

**Separation of concerns**
Protocol handling, network transport, simulation, client state, UI components, and screen management are separated into distinct modules.

**Failure handling**
Disconnects, invalid requests, duplicate usernames, failed sends, and interrupted TCP messages are handled without requiring the entire application to terminate.

---

## 🧰 Tech Stack

| Technology                 | Purpose                                              |
| -------------------------- | ---------------------------------------------------- |
| **Python**                 | Core application and server logic                    |
| **Pygame**                 | Rendering, UI, input, and audio                      |
| **TCP/IP sockets**         | Reliable client-server communication                 |
| **Python ****`threading`** | Concurrent connection handling and network receiving |
| **JSON**                   | Application-message serialization                    |
| **`struct`**               | Binary 4-byte message-length headers                 |
| **Dataclasses**            | Structured game-domain models                        |

---

## 📁 Project Structure

```text
snake-royale/
│
├── server.py               # TCP server, matchmaking, game loop and clients
├── client.py               # Pygame client and application loop
├── network.py              # Client-side networking abstraction
├── protocol.py             # TCP message framing and protocol definitions
│
├── game_engine.py          # Authoritative gameplay simulation
├── models.py               # Game-domain dataclasses
├── constants.py            # Gameplay constants
├── client_state.py         # Shared client-side state
│
├── screen_manager.py       # Client screen transitions
├── base_screen.py          # Shared screen behavior
├── connect_screen.py       # Server connection UI
├── username_screen.py      # Registration UI
├── lobby_screen.py         # Lobby, challenges and chat
├── customize_screen.py     # Snake customization UI
├── game_screen.py          # Match and spectator rendering
├── result_screen.py        # Match result UI
│
├── button.py               # Reusable UI button
├── list_box.py             # Reusable list component
├── text_input.py           # Reusable text input
├── art.py                  # Shared visual rendering
├── config.py               # Client display configuration
│
├── assets/                 # Game assets
├── requirements.txt
└── README.md
```

---

## 🚀 Running Locally

### Prerequisites

* Python 3
* `pip`
* Two or more client instances for multiplayer testing

### 1. Clone the repository

```bash
git clone https://github.com/MaherKaram/snake-royale.git
cd snake-royale
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

The only external Python dependency is:

```text
pygame
```

### 3. Start the server

Choose an available TCP port, for example `5555`:

```bash
python server.py 5555
```

The server prints connection information similar to:

```text
Server listening on port: 5555
The laptop running the server should connect to: 127.0.0.1
Other laptops on the same network should connect to: <LAN-IP>
```

### 4. Start a client

Open another terminal:

```bash
python client.py
```

For a client running on the **same machine** as the server, connect to:

```text
Host: 127.0.0.1
Port: 5555
```

For another computer on the **same local network**, use the LAN IP printed by the server.

### 5. Start additional clients

Run:

```bash
python client.py
```

again in separate terminals or on other devices.

Choose unique usernames, challenge another available player from the lobby, and start the match.

Other connected users can spectate the active game.

---

## 🎯 Gameplay

| Setting               |               Value |
| --------------------- | ------------------: |
| Board                 |             12 × 14 |
| Starting health       |                  50 |
| Collision damage      |                   5 |
| Pie health reward     |                  10 |
| Match duration        |         120 seconds |
| Server tick rate      |                5 Hz |
| Starting snake length |                   3 |
| Power pie interval    | After 5 normal pies |

### Controls

Use the directional controls during a match to steer your snake.

The server rejects invalid direction changes such as immediately reversing into the snake's own body.

### Winning

A match ends when:

* one player's health reaches zero,
* both players reach zero health simultaneously, resulting in a draw, or
* the 120-second match timer expires.

If time expires, the player with more remaining health wins. Equal health results in a draw.

---

## 🚧 Current Scope

Snake Royale currently runs one active 1v1 match per server instance while allowing additional connected users to remain in the lobby or spectate that match.

Potential future extensions include:

* Multiple simultaneous matches
* Match rooms
* Persistent player accounts
* Leaderboards and statistics
* Server discovery
* Authentication
* Automated networking and game-engine tests
* Client-side interpolation for smoother high-latency gameplay
* Deployment to a public server

---

## 👨‍💻 My Contribution

My primary focus was the **server and networking side of the project**, including the client-server communication layer and multiplayer protocol.

Key areas included:

* TCP socket communication
* Custom message protocol
* Server-side multiplayer coordination
* Concurrent client handling
* Lobby and multiplayer communication flows
* Synchronization between clients and authoritative server state

Working on Snake Royale provided hands-on experience with networking concepts beyond calling an existing API: defining how clients communicate, handling TCP as a byte stream, coordinating concurrent connections, and keeping multiple clients synchronized around a single authoritative source of truth.

---

## 📄 License

This project was developed as a software engineering project and is provided for educational and portfolio purposes.

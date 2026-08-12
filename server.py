import socket
import threading
import sys
import time

from constants import (
    TICK_RATE,
    BOARD_WIDTH,
    BOARD_HEIGHT,
)

from protocol import (
    send_message,
    receive_message,
    REGISTER,
    REGISTER_OK,
    REGISTER_FAIL,
    USER_LIST,
    CHALLENGE,
    CHALLENGE_RECEIVED,
    CHALLENGE_ACCEPT,
    CHALLENGE_REJECT,
    SPECTATE_REQUEST,
    INPUT,
    CUSTOMIZATION_UPDATE,
    GAME_START,
    GAME_STATE,
    GAME_OVER,
    CHAT_SEND,
    CHAT_MESSAGE,
    INFO,
    ERROR, 
    LEAVE_SPECTATE,
    LEAVE_SPECTATE_OK,
    CHEER,
)

from game_engine import (
    create_match,
    process_player_input,
    advance_tick,
    get_match_state,
    is_match_over,
    get_match_result,
)


HOST = "0.0.0.0"
MATCH_START_COUNTDOWN_SECONDS = 5
DEFAULT_SNAKE_COLOR = "pink"

clients = {}
client_usernames = {}
client_status = {}
client_customization = {}
pending_challenges = {}
current_game = None
lock = threading.Lock()


def configure_socket(sock):
    try:
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    except Exception:
        pass

    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    except Exception:
        pass


def safe_send(sock, msg_type, payload=None):
    try:
        send_message(sock, msg_type, payload)
        return True
    except Exception:
        return False


def normalize_color_name(color_name):
    valid_colors = {
        "red",
        "pink",
        "orange",
        "yellow",
        "green",
        "cyan",
        "blue",
        "purple",
        "white",
        "black",
    }

    clean_color = str(color_name).strip().lower()
    if clean_color in valid_colors:
        return clean_color
    return DEFAULT_SNAKE_COLOR


def create_current_game(player1_username, player2_username):
    player1_color = client_customization.get(player1_username, {}).get("snake_color", DEFAULT_SNAKE_COLOR)
    player2_color = client_customization.get(player2_username, {}).get("snake_color", DEFAULT_SNAKE_COLOR)

    return {
        "players": [player1_username, player2_username],
        "player_id_map": {
            player1_username: "P1",
            player2_username: "P2",
        },
        "spectators": set(),
        "cheers": {
            player1_username: None,
            player2_username: None,
        },
        "match": create_match(player1_username, player2_username, player1_color, player2_color),
        "starts_at": time.time() + MATCH_START_COUNTDOWN_SECONDS,
    }


def build_game_state_payload(game):
    state = get_match_state(game["match"])
    state = dict(state)

    if "type" in state:
        del state["type"]

    state["cheers"] = dict(game.get("cheers", {}))
    return state


def get_player_id(game, username):
    if username not in game["player_id_map"]:
        raise ValueError(f"Unknown player username: {username}")
    return game["player_id_map"][username]


def get_current_countdown_seconds(game):
    return max(0.0, game.get("starts_at", 0.0) - time.time())


def get_lan_ip():
    test_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        test_socket.connect(("8.8.8.8", 80))
        return test_socket.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        test_socket.close()


def broadcast_user_list():
    users = []

    with lock:
        for username in clients:
            users.append({
                "username": username,
                "status": client_status[username],
                "snake_color": client_customization.get(username, {}).get("snake_color", DEFAULT_SNAKE_COLOR),
            })
        sockets = list(clients.values())

    for sock in sockets:
        safe_send(sock, USER_LIST, {"users": users})


def handle_customization_update(username, payload):
    new_color = normalize_color_name(payload.get("snake_color", DEFAULT_SNAKE_COLOR))

    with lock:
        if username not in clients:
            return

        client_customization.setdefault(username, {})
        client_customization[username]["snake_color"] = new_color

        if current_game is not None and username in current_game["players"]:
            match = current_game["match"]
            if match.player1.username == username:
                match.player1.color = new_color
            elif match.player2.username == username:
                match.player2.color = new_color

    broadcast_user_list()


def handle_challenge(challenger, target):
    global current_game

    with lock:
        if challenger not in clients:
            return

        if current_game is not None:
            safe_send(clients[challenger], ERROR, {"reason": "A game is already running"})
            return

        if target not in clients:
            safe_send(clients[challenger], ERROR, {"reason": "Target is not online"})
            return

        if challenger == target:
            safe_send(clients[challenger], ERROR, {"reason": "You cannot challenge yourself"})
            return

        if client_status[challenger] != "IDLE" or client_status[target] != "IDLE":
            safe_send(clients[challenger], ERROR, {"reason": "One of the players is busy"})
            return

        pending_challenges[target] = challenger
        target_socket = clients[target]
        challenger_socket = clients[challenger]

    safe_send(target_socket, CHALLENGE_RECEIVED, {"from": challenger})
    safe_send(challenger_socket, INFO, {"message": "Challenge sent"})


def handle_accept(target, challenger):
    global current_game

    with lock:
        if target not in clients or challenger not in clients:
            return

        if target not in pending_challenges:
            safe_send(clients[target], ERROR, {"reason": "No pending challenge"})
            return

        if pending_challenges[target] != challenger:
            safe_send(clients[target], ERROR, {"reason": "Invalid challenge"})
            return

        if current_game is not None:
            safe_send(clients[target], ERROR, {"reason": "A game is already running"})
            return

        del pending_challenges[target]
        client_status[challenger] = "IN_GAME"
        client_status[target] = "IN_GAME"
        current_game = create_current_game(challenger, target)

        challenger_socket = clients[challenger]
        target_socket = clients[target]
        initial_state = build_game_state_payload(current_game)

    safe_send(challenger_socket, GAME_START, {
        "role": "PLAYER",
        "opponent": target,
        "you": challenger,
        "board_width": BOARD_WIDTH,
        "board_height": BOARD_HEIGHT,
        "tick_rate": TICK_RATE,
        "countdown_seconds": MATCH_START_COUNTDOWN_SECONDS,
    })

    safe_send(target_socket, GAME_START, {
        "role": "PLAYER",
        "opponent": challenger,
        "you": target,
        "board_width": BOARD_WIDTH,
        "board_height": BOARD_HEIGHT,
        "tick_rate": TICK_RATE,
        "countdown_seconds": MATCH_START_COUNTDOWN_SECONDS,
    })

    safe_send(challenger_socket, GAME_STATE, initial_state)
    safe_send(target_socket, GAME_STATE, initial_state)

    broadcast_user_list()

    game_thread = threading.Thread(target=run_game_loop, daemon=True)
    game_thread.start()


def handle_reject(target, challenger):
    with lock:
        if target in pending_challenges and pending_challenges[target] == challenger:
            del pending_challenges[target]
            if challenger in clients:
                safe_send(clients[challenger], CHALLENGE_REJECT, {"from": target})


def handle_input(username, direction):
    global current_game

    with lock:
        if current_game is None:
            if username in clients:
                safe_send(clients[username], ERROR, {"reason": "No game is running"})
            return

        if username not in current_game["players"]:
            if username in clients:
                safe_send(clients[username], ERROR, {"reason": "You are not part of the current game"})
            return

        if time.time() < current_game.get("starts_at", 0):
            return

        try:
            player_id = get_player_id(current_game, username)
            accepted = process_player_input(current_game["match"], player_id, direction)

            if not accepted:
                return

        except Exception as e:
            if username in clients:
                safe_send(clients[username], ERROR, {"reason": str(e)})


def handle_chat(sender, target, text):
    clean_text = str(text).replace("\n", " ").strip()
    if not clean_text:
        if sender in clients:
            safe_send(clients[sender], ERROR, {"reason": "Cannot send an empty message"})
        return

    if len(clean_text) > 180:
        clean_text = clean_text[:180]

    with lock:
        sender_socket = clients.get(sender)
        target_socket = clients.get(target)

    if sender == target:
        if sender_socket:
            safe_send(sender_socket, ERROR, {"reason": "You cannot chat with yourself"})
        return

    if target_socket is None:
        if sender_socket:
            safe_send(sender_socket, ERROR, {"reason": "Target is not online"})
        return

    incoming_payload = {
        "from": sender,
        "to": target,
        "message": clean_text,
        "outgoing": False,
    }
    outgoing_payload = {
        "from": sender,
        "to": target,
        "message": clean_text,
        "outgoing": True,
    }

    safe_send(target_socket, CHAT_MESSAGE, incoming_payload)
    if sender_socket:
        safe_send(sender_socket, CHAT_MESSAGE, outgoing_payload)


def handle_spectate_request(spectator, target):
    global current_game

    with lock:
        if spectator not in clients:
            return

        if current_game is None:
            safe_send(clients[spectator], ERROR, {"reason": "No game is currently running"})
            return

        if target not in current_game["players"]:
            safe_send(clients[spectator], ERROR, {"reason": "That player is not in the active match"})
            return

        if spectator in current_game["players"]:
            safe_send(clients[spectator], ERROR, {"reason": "Players cannot spectate their own match"})
            return

        if client_status.get(spectator) != "IDLE":
            safe_send(clients[spectator], ERROR, {"reason": "You are busy right now"})
            return

        current_game["spectators"].add(spectator)
        client_status[spectator] = "SPECTATING"

        spectator_socket = clients[spectator]
        watched_players = list(current_game["players"])
        countdown_seconds = get_current_countdown_seconds(current_game)
        initial_state = build_game_state_payload(current_game)

    safe_send(spectator_socket, GAME_START, {
        "role": "SPECTATOR",
        "you": spectator,
        "watching": watched_players,
        "board_width": BOARD_WIDTH,
        "board_height": BOARD_HEIGHT,
        "tick_rate": TICK_RATE,
        "countdown_seconds": countdown_seconds,
    })

    safe_send(spectator_socket, GAME_STATE, initial_state)
    safe_send(spectator_socket, INFO, {
        "message": f"Now spectating {watched_players[0]} vs {watched_players[1]}"
    })

    broadcast_user_list()

def handle_leave_spectate(username):
    global current_game

    with lock:
        if username not in clients:
            return

        if current_game is None or username not in current_game.get("spectators", set()):
            safe_send(clients[username], ERROR, {"reason": "You are not spectating any match"})
            return

        current_game["spectators"].discard(username)
        client_status[username] = "IDLE"
        spectator_socket = clients[username]

    safe_send(spectator_socket, LEAVE_SPECTATE_OK, {
        "message": "You left the spectated match"
    })

    broadcast_user_list()

def handle_cheer(spectator, target):
    global current_game

    with lock:
        if spectator not in clients:
            return

        if current_game is None:
            safe_send(clients[spectator], ERROR, {"reason": "No game is currently running"})
            return

        if spectator not in current_game.get("spectators", set()):
            safe_send(clients[spectator], ERROR, {"reason": "Only spectators can cheer"})
            return

        if target not in current_game["players"]:
            safe_send(clients[spectator], ERROR, {"reason": "Invalid cheer target"})
            return

        current_game.setdefault("cheers", {})
        current_game["cheers"][target] = {
            "message": f"{spectator}: Let's Go {target}!",
            "expires_tick": current_game["match"].tick_count + (TICK_RATE * 4),
        }

        payload = build_game_state_payload(current_game)

        usernames_to_update = list(current_game["players"]) + list(current_game.get("spectators", set()))
        sockets_to_update = [clients[name] for name in usernames_to_update if name in clients]

    for sock in sockets_to_update:
        safe_send(sock, GAME_STATE, payload)

def remove_client(client_socket):
    global current_game
    result_to_send = None
    result_usernames = []

    with lock:
        if client_socket not in client_usernames:
            try:
                client_socket.close()
            except Exception:
                pass
            return

        username = client_usernames[client_socket]
        del client_usernames[client_socket]

        if username in clients:
            del clients[username]

        if username in client_status:
            del client_status[username]

        if username in client_customization:
            del client_customization[username]

        targets_to_remove = []
        for target in pending_challenges:
            if target == username or pending_challenges[target] == username:
                targets_to_remove.append(target)

        for target in targets_to_remove:
            del pending_challenges[target]

        if current_game is not None and username in current_game.get("spectators", set()):
            current_game["spectators"].discard(username)

        if current_game is not None and username in current_game["players"]:
            winner = None
            for player in current_game["players"]:
                if player != username:
                    winner = player

            spectator_usernames = list(current_game.get("spectators", set()))
            for spectator in spectator_usernames:
                if spectator in client_status:
                    client_status[spectator] = "IDLE"

            if winner is not None and winner in client_status:
                client_status[winner] = "IDLE"

            result_to_send = get_match_result(current_game["match"])
            result_to_send["winner"] = winner
            result_to_send["reason"] = "opponent_disconnected"
            result_usernames = [name for name in [winner, *spectator_usernames] if name in clients]
            current_game = None

    try:
        client_socket.shutdown(socket.SHUT_RDWR)
    except Exception:
        pass

    try:
        client_socket.close()
    except Exception:
        pass

    if result_to_send:
        for username_to_notify in result_usernames:
            try:
                safe_send(clients[username_to_notify], GAME_OVER, result_to_send)
            except Exception:
                pass

    print(username, "disconnected")
    broadcast_user_list()


def handle_client(client_socket):
    username = None

    configure_socket(client_socket)

    try:
        msg = receive_message(client_socket)

        if msg is None or msg.get("type") != REGISTER:
            safe_send(client_socket, REGISTER_FAIL, {"reason": "You must register first"})
            client_socket.close()
            return

        username = msg.get("payload", {}).get("username", "").strip()

        with lock:
            if username == "":
                safe_send(client_socket, REGISTER_FAIL, {"reason": "Empty username"})
                client_socket.close()
                return

            if username in clients:
                safe_send(client_socket, REGISTER_FAIL, {"reason": "Username already in use"})
                client_socket.close()
                return

            clients[username] = client_socket
            client_usernames[client_socket] = username
            client_status[username] = "IDLE"
            client_customization[username] = {
                "snake_color": DEFAULT_SNAKE_COLOR,
            }

        safe_send(client_socket, REGISTER_OK, {"message": "Registered successfully"})
        broadcast_user_list()

        while True:
            msg = receive_message(client_socket)
            if msg is None:
                break

            msg_type = msg.get("type")
            payload = msg.get("payload", {})

            if msg_type == CHALLENGE:
                target = payload.get("target", "")
                handle_challenge(username, target)

            elif msg_type == CHALLENGE_ACCEPT:
                challenger = payload.get("from", "")
                handle_accept(username, challenger)

            elif msg_type == CHALLENGE_REJECT:
                challenger = payload.get("from", "")
                handle_reject(username, challenger)

            elif msg_type == INPUT:
                direction = payload.get("direction", "")
                handle_input(username, direction)

            elif msg_type == CHAT_SEND:
                handle_chat(username, payload.get("target", ""), payload.get("message", ""))

            elif msg_type == CUSTOMIZATION_UPDATE:
                handle_customization_update(username, payload)

            elif msg_type == SPECTATE_REQUEST:
                handle_spectate_request(username, payload.get("target", ""))

            elif msg_type == LEAVE_SPECTATE:
                handle_leave_spectate(username)

            elif msg_type == CHEER:
                handle_cheer(username, payload.get("target", ""))

            else:
                safe_send(client_socket, ERROR, {"reason": "Unknown message type"})

    except Exception:
        pass

    remove_client(client_socket)


def run_game_loop():
    global current_game

    tick_delay = 1.0 / TICK_RATE
    next_tick = time.perf_counter()

    while True:
        with lock:
            if current_game is None:
                return

            starts_at = current_game.get("starts_at", 0)
            match = current_game["match"]

            players = list(current_game["players"])
            spectators = list(current_game.get("spectators", set()))
            usernames_to_update = players + spectators

            sockets_to_update = []
            for name in usernames_to_update:
                if name in clients:
                    sockets_to_update.append(clients[name])

        now = time.time()
        if now < starts_at:
            time.sleep(min(0.02, starts_at - now))
            next_tick = time.perf_counter()
            continue

        with lock:
            if current_game is None:
                return

            advance_tick(match)
            payload = build_game_state_payload(current_game)
            match_over = is_match_over(match)

        for sock in sockets_to_update:
            safe_send(sock, GAME_STATE, payload)

        if match_over:
            result = get_match_result(match)

            with lock:
                if current_game is None:
                    return

                finished_players = list(current_game["players"])
                finished_spectators = list(current_game.get("spectators", set()))
                finished_users = finished_players + finished_spectators

                for username in finished_users:
                    if username in client_status:
                        client_status[username] = "IDLE"

                result_sockets = [clients[name] for name in finished_users if name in clients]
                current_game = None

            for sock in result_sockets:
                safe_send(sock, GAME_OVER, result)

            broadcast_user_list()
            return

        next_tick += tick_delay
        sleep_time = next_tick - time.perf_counter()

        if sleep_time > 0:
            time.sleep(sleep_time)
        else:
            next_tick = time.perf_counter()


def main():
    if len(sys.argv) != 2:
        print("Usage: python server.py <port>")
        return

    port = int(sys.argv[1])

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    configure_socket(server_socket)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, port))
    server_socket.listen()

    lan_ip = get_lan_ip()

    print(f"Server listening on port: {port}")
    print(f"The laptop running the server should connect to: 127.0.0.1")
    print(f"Other laptops on the same network should connect to: {lan_ip}")

    try:
        while True:
            client_socket, address = server_socket.accept()
            configure_socket(client_socket)
            print("Connection from", address)
            thread = threading.Thread(target=handle_client, args=(client_socket,), daemon=True)
            thread.start()
    except KeyboardInterrupt:
        print("Server shutting down")
    finally:
        server_socket.close()


if __name__ == "__main__":
    main()
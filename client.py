import os
import time
from collections import deque
import pygame
import config

from screen_manager import ScreenManager
from client_state import create_client_state
from network import NetworkClient
from game_screen import GameScreen
from result_screen import ResultScreen

from connect_screen import ConnectScreen
from lobby_screen import LobbyScreen
from username_screen import UsernameScreen
from art import draw_scene_background


def start_background_music():
    try:
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.mixer.init()
        music_path = os.path.join("assets", "Battle_music.mp3")
        if os.path.exists(music_path):
            pygame.mixer.music.load(music_path)
            pygame.mixer.music.set_volume(0.5)
            pygame.mixer.music.play(-1)
        else:
            print("Music file not found:", music_path)
    except Exception as e:
        print("Music could not start:", e)


def add_chat_message(client_state, other_user, sender, text, outgoing):
    histories = client_state.setdefault("chat_histories", {})
    histories.setdefault(other_user, []).append({
        "sender": sender,
        "text": text,
        "outgoing": outgoing,
        "time": time.strftime("%H:%M"),
    })

    if len(histories[other_user]) > 60:
        histories[other_user] = histories[other_user][-60:]


def push_chat_notification(client_state, message):
    notifications = client_state.setdefault("chat_notifications", [])
    notifications.append({
        "message": message,
        "expires_at": time.time() + 4.0,
    })

    if len(notifications) > 4:
        client_state["chat_notifications"] = notifications[-4:]


def format_game_over_status(payload, was_spectator=False):
    winner = payload.get("winner")

    if winner:
        result_text = f"{winner} won"
    else:
        result_text = "Draw"

    if was_spectator:
        return f"Watching ended: {result_text}"

    return f"Game over: {result_text}"


def compute_viewport(window_size, base_size):
    window_w, window_h = window_size
    base_w, base_h = base_size

    if window_w <= 0 or window_h <= 0:
        return {
            "scale_x": 1.0,
            "scale_y": 1.0,
            "scaled_width": base_w,
            "scaled_height": base_h,
            "offset_x": 0,
            "offset_y": 0,
        }

    scale_x = window_w / base_w
    scale_y = window_h / base_h

    return {
        "scale_x": scale_x,
        "scale_y": scale_y,
        "scaled_width": window_w,
        "scaled_height": window_h,
        "offset_x": 0,
        "offset_y": 0,
    }


def transform_mouse_event(event, viewport):
    if not hasattr(event, "pos"):
        return event

    scale_x = viewport["scale_x"]
    scale_y = viewport["scale_y"]
    offset_x = viewport["offset_x"]
    offset_y = viewport["offset_y"]

    if scale_x <= 0 or scale_y <= 0:
        return event

    mx, my = event.pos
    logical_x = int((mx - offset_x) / scale_x)
    logical_y = int((my - offset_y) / scale_y)

    event_dict = event.dict.copy()
    event_dict["pos"] = (logical_x, logical_y)

    if event.type == pygame.MOUSEMOTION and "rel" in event_dict:
        rx, ry = event_dict["rel"]
        event_dict["rel"] = (rx / scale_x, ry / scale_y)

    return pygame.event.Event(event.type, event_dict)


def transform_events(events, viewport, base_size):
    transformed = []
    base_w, base_h = base_size

    for event in events:
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            if hasattr(event, "pos"):
                converted = transform_mouse_event(event, viewport)
                cx, cy = converted.pos

                if event.type == pygame.MOUSEMOTION:
                    transformed.append(converted)
                else:
                    if 0 <= cx < base_w and 0 <= cy < base_h:
                        transformed.append(converted)
            else:
                transformed.append(event)
        else:
            transformed.append(event)

    return transformed


def main():
    pygame.init()

    base_width = config.WINDOW_WIDTH
    base_height = config.WINDOW_HEIGHT
    base_size = (base_width, base_height)

    window = pygame.display.set_mode(base_size, pygame.RESIZABLE)
    pygame.display.set_caption(config.WINDOW_TITLE)
    clock = pygame.time.Clock()

    render_surface = pygame.Surface(base_size).convert()
    viewport = compute_viewport(window.get_size(), base_size)

    start_background_music()

    client_state = create_client_state()
    manager = ScreenManager()

    incoming_messages = deque()
    disconnected_events = deque()

    def on_message(msg):
        incoming_messages.append(msg)

    def on_disconnect():
        disconnected_events.append(True)

    network = NetworkClient(
        client_state,
        on_message=on_message,
        on_disconnect=on_disconnect
    )

    def process_server_message(msg):
        msg_type = msg.get("type")
        payload = msg.get("payload", {})

        if msg_type == "REGISTER_OK":
            client_state["error"] = ""
            client_state["info"] = ""
            client_state["status"] = payload.get("message", "Registered successfully")

            manager.set_screen(LobbyScreen(manager, client_state, network))

            current = manager.current_screen
            if isinstance(current, LobbyScreen):
                current.set_players(client_state.get("online_players", []))

        elif msg_type == "REGISTER_FAIL":
            client_state["error"] = payload.get("reason", "Registration failed")
            client_state["info"] = ""
            client_state["status"] = ""

        elif msg_type == "USER_LIST":
            users = payload.get("users", [])
            client_state["online_players"] = users

            current = manager.current_screen
            if isinstance(current, LobbyScreen):
                current.set_players(users)

        elif msg_type == "CHALLENGE_RECEIVED":
            challenger = payload.get("from", "")
            client_state["pending_challenge_from"] = challenger
            client_state["status"] = f"Challenge received from {challenger}"

        elif msg_type == "CHALLENGE_REJECT":
            from_user = payload.get("from", "")
            client_state["status"] = f"Challenge rejected by {from_user}"

        elif msg_type == "CHAT_MESSAGE":
            sender = payload.get("from", "")
            target = payload.get("to", "")
            text = payload.get("message", "")
            outgoing = payload.get("outgoing", False)
            other_user = target if outgoing else sender

            add_chat_message(client_state, other_user, sender, text, outgoing)

            if outgoing:
                client_state["status"] = f"Message sent to {other_user}"
            else:
                active_chat_user = client_state.get("active_chat_user")
                in_lobby = isinstance(manager.current_screen, LobbyScreen)

                if not (in_lobby and active_chat_user == other_user):
                    unread = client_state.setdefault("unread_chats", {})
                    unread[other_user] = unread.get(other_user, 0) + 1
                    push_chat_notification(client_state, f"Message from {other_user}")

                client_state["status"] = f"New message from {other_user}"

        elif msg_type == "INFO":
            client_state["info"] = payload.get("message", "")
            client_state["status"] = client_state["info"]

        elif msg_type == "ERROR":
            client_state["error"] = payload.get("reason", "Unknown server error")
            client_state["status"] = client_state["error"]

        elif msg_type == "GAME_START":
            countdown = float(payload.get("countdown_seconds", 0))
            role = payload.get("role", "PLAYER")
            watching_players = payload.get("watching", [])

            client_state["in_game"] = True
            client_state["is_spectator"] = role == "SPECTATOR"
            client_state["watching_players"] = watching_players
            client_state["result"] = None
            client_state["previous_game_state"] = None
            client_state["game_state"] = None
            client_state["pending_challenge_from"] = None
            client_state["you"] = payload.get("you")
            client_state["opponent"] = payload.get("opponent")
            client_state["countdown_seconds"] = countdown
            client_state["match_starts_at"] = time.time() + max(0.0, countdown)
            client_state["server_tick_rate"] = payload.get("tick_rate", 3)

            if client_state["is_spectator"] and len(watching_players) == 2:
                client_state["status"] = f"Spectating {watching_players[0]} vs {watching_players[1]}"
            else:
                client_state["status"] = f"Match starts in {int(max(0.0, countdown) + 0.999)} seconds"

            manager.set_screen(GameScreen(manager, client_state, network))

        elif msg_type == "GAME_STATE":
            client_state["previous_game_state"] = client_state.get("game_state")
            client_state["game_state"] = payload
            client_state["game_state_received_at"] = time.time()

        elif msg_type == "GAME_OVER":
            was_spectator = client_state.get("is_spectator", False)

            client_state["in_game"] = False
            client_state["result"] = payload
            client_state["status"] = format_game_over_status(payload, was_spectator)
            client_state["match_starts_at"] = 0.0
            client_state["countdown_seconds"] = 0

            manager.set_screen(ResultScreen(manager, client_state, network))

        elif msg_type == "LEAVE_SPECTATE_OK":
            client_state["in_game"] = False
            client_state["is_spectator"] = False
            client_state["watching_players"] = []
            client_state["game_state"] = None
            client_state["previous_game_state"] = None
            client_state["game_state_received_at"] = 0.0
            client_state["match_starts_at"] = 0.0
            client_state["countdown_seconds"] = 0
            client_state["you"] = None
            client_state["opponent"] = None
            client_state["status"] = payload.get("message", "You left the spectated match")

            lobby = LobbyScreen(manager, client_state, network)
            lobby.set_players(client_state.get("online_players", []))
            manager.set_screen(lobby)

        else:
            client_state["status"] = f"Unhandled message type: {msg_type}"

    def process_disconnect():
        client_state["connected"] = False
        client_state["in_game"] = False

        current = manager.current_screen
        if isinstance(current, UsernameScreen):
            client_state["status"] = ""
        else:
            client_state["status"] = "Disconnected from server."

    manager.set_screen(ConnectScreen(manager, client_state, network))

    running = True
    while running:
        raw_events = pygame.event.get()

        for event in raw_events:
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.VIDEORESIZE:
                new_width = max(900, event.w)
                new_height = max(650, event.h)
                window = pygame.display.set_mode((new_width, new_height), pygame.RESIZABLE)
                viewport = compute_viewport(window.get_size(), base_size)

            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        while incoming_messages:
            msg = incoming_messages.popleft()
            process_server_message(msg)

        while disconnected_events:
            disconnected_events.popleft()
            process_disconnect()

        viewport = compute_viewport(window.get_size(), base_size)
        events = transform_events(raw_events, viewport, base_size)

        manager.handle_events(events)
        manager.update()

        draw_scene_background(render_surface)
        manager.draw(render_surface)

        if (
            viewport["scaled_width"] == base_width
            and viewport["scaled_height"] == base_height
        ):
            window.blit(render_surface, (0, 0))
        else:
            scaled_surface = pygame.transform.scale(
                render_surface,
                (viewport["scaled_width"], viewport["scaled_height"])
            )
            window.blit(scaled_surface, (0, 0))

        pygame.display.flip()
        clock.tick(config.FPS)

    try:
        pygame.mixer.music.stop()
    except Exception:
        pass

    network.close(silent=True)
    pygame.quit()


if __name__ == "__main__":
    main()
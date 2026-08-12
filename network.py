import socket
import threading

from protocol import (
    send_message,
    receive_message,
    REGISTER,
    CHALLENGE,
    CHALLENGE_ACCEPT,
    CHALLENGE_REJECT,
    SPECTATE_REQUEST,
    LEAVE_SPECTATE,
    CHEER,
    INPUT,
    CHAT_SEND,
    CUSTOMIZATION_UPDATE,
)


class NetworkClient:
    def __init__(self, client_state, on_message=None, on_disconnect=None):
        self.client_state = client_state
        self.on_message = on_message
        self.on_disconnect = on_disconnect
        self.sock = None
        self.running = False
        self.recv_thread = None

    def connect(self, host, port):
        self.close(silent=True)

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

            self.sock.connect((host, int(port)))

            self.running = True
            self.recv_thread = threading.Thread(target=self.receive_loop, daemon=True)
            self.recv_thread.start()

            self.client_state["connected"] = True
            self.client_state["server_ip"] = host
            self.client_state["server_port"] = str(port)
            return True, None

        except Exception as e:
            self.client_state["connected"] = False
            self.sock = None
            return False, str(e)

    def receive_loop(self):
        try:
            while self.running and self.sock:
                msg = receive_message(self.sock)
                if msg is None:
                    break

                if self.on_message:
                    self.on_message(msg)

        except Exception:
            pass

        self.close()

    def close(self, silent=False):
        was_connected = self.client_state.get("connected", False) or self.sock is not None

        self.running = False
        self.client_state["connected"] = False

        try:
            if self.sock:
                self.sock.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass

        try:
            if self.sock:
                self.sock.close()
        except Exception:
            pass

        self.sock = None

        if (not silent) and was_connected and self.on_disconnect:
            self.on_disconnect()

    def safe_send(self, msg_type, payload=None):
        if not self.sock or not self.running:
            return

        try:
            send_message(self.sock, msg_type, payload)
        except Exception:
            self.close()

    def send_username(self, username):
        self.client_state["username"] = username
        self.safe_send(REGISTER, {"username": username})

    def send_challenge(self, opponent):
        self.safe_send(CHALLENGE, {"target": opponent})

    def send_challenge_accept(self, challenger):
        self.safe_send(CHALLENGE_ACCEPT, {"from": challenger})

    def send_challenge_reject(self, challenger):
        self.safe_send(CHALLENGE_REJECT, {"from": challenger})

    def send_move(self, direction):
        self.safe_send(INPUT, {"direction": direction.upper()})

    def send_chat_message(self, target, text):
        self.safe_send(CHAT_SEND, {"target": target, "message": text})

    def request_online_players(self):
        pass

    def send_spectate_request(self, target):
        self.safe_send(SPECTATE_REQUEST, {"target": target})

    def send_leave_spectate(self):
        self.safe_send(LEAVE_SPECTATE, {})

    def send_cheer(self, target):
        self.safe_send(CHEER, {"target": target})

    def send_customization(self, color, controls):
        self.client_state["snake_color"] = str(color).lower()
        self.client_state["controls"] = dict(controls)

        if self.sock and self.client_state.get("connected"):
            self.safe_send(CUSTOMIZATION_UPDATE, {
                "snake_color": self.client_state["snake_color"],
                "controls": self.client_state["controls"]
            })
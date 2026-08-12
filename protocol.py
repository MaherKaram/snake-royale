import json
import struct


REGISTER = "REGISTER"
REGISTER_OK = "REGISTER_OK"
REGISTER_FAIL = "REGISTER_FAIL"

USER_LIST = "USER_LIST"

CHALLENGE = "CHALLENGE"
CHALLENGE_RECEIVED = "CHALLENGE_RECEIVED"
CHALLENGE_ACCEPT = "CHALLENGE_ACCEPT"
CHALLENGE_REJECT = "CHALLENGE_REJECT"
SPECTATE_REQUEST = "SPECTATE_REQUEST"
LEAVE_SPECTATE = "LEAVE_SPECTATE"
LEAVE_SPECTATE_OK = "LEAVE_SPECTATE_OK"
CHEER = "CHEER"

INPUT = "INPUT"
CUSTOMIZATION_UPDATE = "CUSTOMIZATION_UPDATE"

GAME_START = "GAME_START"
GAME_STATE = "GAME_STATE"
GAME_OVER = "GAME_OVER"

CHAT_SEND = "CHAT_SEND"
CHAT_MESSAGE = "CHAT_MESSAGE"

INFO = "INFO"
ERROR = "ERROR"


class ProtocolError(Exception):
    pass


def send_message(sock, msg_type, payload=None):
    if payload is None:
        payload = {}

    message = {
        "type": msg_type,
        "payload": payload
    }

    try:
        json_string = json.dumps(message)
        encoded_message = json_string.encode("utf-8")
        header = struct.pack("!I", len(encoded_message))
        sock.sendall(header + encoded_message)
    except Exception as e:
        raise ProtocolError(f"Send failed: {e}")


def receive_exact(sock, size):
    data = b""

    while len(data) < size:
        try:
            packet = sock.recv(size - len(data))
        except Exception as e:
            raise ProtocolError(f"Receive failed: {e}")

        if not packet:
            if len(data) == 0:
                return None
            raise ProtocolError("Connection closed during receive.")

        data += packet

    return data


def receive_message(sock):
    header = receive_exact(sock, 4)
    if header is None:
        return None

    try:
        message_length = struct.unpack("!I", header)[0]
    except Exception as e:
        raise ProtocolError(f"Invalid header: {e}")

    payload = receive_exact(sock, message_length)
    if payload is None:
        return None

    try:
        json_string = payload.decode("utf-8")
        message = json.loads(json_string)
    except Exception as e:
        raise ProtocolError(f"JSON decode failed: {e}")

    if not isinstance(message, dict):
        raise ProtocolError("Protocol message must be a dictionary.")

    if "type" not in message:
        raise ProtocolError("Protocol message missing 'type' field.")

    if "payload" not in message:
        message["payload"] = {}

    if not isinstance(message["payload"], dict):
        raise ProtocolError("Protocol payload must be a dictionary.")

    return message
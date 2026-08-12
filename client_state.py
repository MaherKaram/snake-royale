def create_client_state():
    return {
        "connected": False,
        "username": "",
        "server_ip": "",
        "server_port": "",

        "online_players": [],
        "selected_opponent": None,
        "pending_challenge_from": None,

        "snake_color": "pink",
        "controls": {
            "up": "w",
            "down": "s",
            "left": "a",
            "right": "d"
        },

        "in_game": False,
        "is_spectator": False,
        "watching_players": [],
        "you": None,
        "opponent": None,

        "game_state": None,
        "previous_game_state": None,
        "game_state_received_at": 0.0,
        "damage_flash_until": {},
        "result": None,

        "match_starts_at": 0.0,
        "countdown_seconds": 0,

        "error": "",
        "info": "",
        "status": ""
    }
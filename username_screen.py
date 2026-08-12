import os
import pygame
import config
from base_screen import BaseScreen
from button import Button
from text_input import TextInput


class UsernameScreen(BaseScreen):
    def __init__(self, manager, client_state, network):
        super().__init__(manager)
        self.client_state = client_state
        self.network = network

        self.input = TextInput((350, 487, 300, 58),"Enter Username",text_align="center")
        self.submit_button = Button((370, 578, 260, 86), "PLAY", self.submit_username)

        self.background = self.load_background()

    def load_background(self):
        path = os.path.join("assets", "snake_royale_bg.png")
        img = pygame.image.load(path).convert()
        img = pygame.transform.smoothscale(img, (config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
        return img

    def reconnect_if_needed(self):
        if self.client_state.get("connected"):
            return True

        host = self.client_state.get("server_ip", "").strip()
        port = self.client_state.get("server_port", "").strip()

        if not host or not port:
            self.client_state["error"] = "Missing server connection info."
            self.client_state["info"] = ""
            self.client_state["status"] = ""
            return False

        ok, msg = self.network.connect(host, port)
        if not ok:
            self.client_state["error"] = f"Reconnect failed: {msg}"
            self.client_state["info"] = ""
            self.client_state["status"] = ""
            return False

        return True

    def submit_username(self):
        username = self.input.text.strip()

        if username == "":
            self.client_state["error"] = "Please enter a username."
            self.client_state["info"] = ""
            self.client_state["status"] = ""
            return

        self.client_state["username"] = username
        self.client_state["error"] = ""
        self.client_state["info"] = "Checking username..."
        self.client_state["status"] = ""

        if not self.reconnect_if_needed():
            return

        try:
            self.network.send_username(username)
        except Exception:
            self.client_state["error"] = "Could not send username to server."
            self.client_state["info"] = ""
            self.client_state["status"] = ""

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit

            old_text = self.input.text
            self.input.handle_event(event)
            self.submit_button.handle_event(event)

            if self.input.text != old_text:
                self.client_state["error"] = ""
                self.client_state["info"] = ""
                self.client_state["status"] = ""

            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN and self.input.active:
                self.submit_username()

    def update(self):
        pass

    def draw(self, surface):
        surface.blit(self.background, (0, 0))
        self.input.draw(surface)
        self.submit_button.draw(surface)

        error_text = self.client_state.get("error", "")
        info_text = self.client_state.get("info", "")

        if error_text:
            err = config.SMALL_FONT.render(error_text, True, config.ERROR_COLOR)
            err_rect = err.get_rect(center=(config.WINDOW_WIDTH // 2, 680))
            surface.blit(err, err_rect)
        elif info_text:
            info = config.SMALL_FONT.render(info_text, True, config.WHITE)
            info_rect = info.get_rect(center=(config.WINDOW_WIDTH // 2, 680))
            surface.blit(info, info_rect)
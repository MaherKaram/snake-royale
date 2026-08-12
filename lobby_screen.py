from typing import Any
import os
import time
import pygame
import config
from base_screen import BaseScreen
from button import Button
from list_box import ListBox
from text_input import TextInput


class LobbyScreen(BaseScreen):
    def __init__(self, manager, client_state: dict[str, Any], network):
        super().__init__(manager)
        self.client_state: dict[str, Any] = client_state
        self.network = network

        self.username = self.client_state.get("username") or "Player"
        self.error_message = ""
        self.status_message = "Click Players to view online users."

        self.players = []
        self.list_box = ListBox((700, 140, 260, 320), self.players)

        self.panel_open = False
        self.panel_x = 1000

        self.players_button = Button((800, 30, 160, 60), "Players", self.toggle_panel)
        self.challenge_button = Button((720, 490, 220, 70), "Challenge", self.challenge_player)
        self.spectate_button = Button((720, 490, 220, 70), "Spectate", self.spectate_selected_player)
        self.chat_button = Button((720, 570, 220, 70), "Chat", self.open_chat_with_selected)
        self.game_option_button = Button((28, 30, 220, 65), "Game Option", self.open_game_options)
        self.send_button = Button((500, 512, 150, 56), "Send", self.send_chat_message)
        self.close_chat_button = Button((610, 125, 40, 40), "X", self.close_chat)

        self.accept_button = Button((28, 200, 120, 55), "Accept", self.accept_challenge)
        self.reject_button = Button((168, 200, 120, 55), "Reject", self.reject_challenge)

        self.chat_input = TextInput(
            (336, 510, 155, 58),
            "Type a message",
            max_length=180,
            font=config.TINY_FONT,
            placeholder_font=config.TINY_FONT,
            padding_x=12
        )

        self.background = self.load_background()

    def load_background(self):
        path = os.path.join("assets", "snake_royale_bg.png")
        img = pygame.image.load(path).convert()
        img = pygame.transform.smoothscale(img, (config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
        return img

    def fit_tail_ellipsis(self, text, font, max_width):
        text = str(text)

        if font.size(text)[0] <= max_width:
            return text

        ellipsis = "..."
        ellipsis_width = font.size(ellipsis)[0]

        if ellipsis_width >= max_width:
            return ellipsis

        available_width = max_width - ellipsis_width
        suffix = ""

        for char in reversed(text):
            test_suffix = char + suffix

            if font.size(test_suffix)[0] > available_width:
                break

            suffix = test_suffix

        return ellipsis + suffix

    def fit_end_ellipsis(self, text, font, max_width):
        text = str(text)

        if font.size(text)[0] <= max_width:
            return text

        ellipsis = "..."

        if font.size(ellipsis)[0] >= max_width:
            return ellipsis

        trimmed = text

        while trimmed and font.size(trimmed + ellipsis)[0] > max_width:
            trimmed = trimmed[:-1]

        return trimmed + ellipsis

    def wrap_text(self, text, font, max_width, max_lines=3):
        text = str(text)

        if not text:
            return [""]

        words = text.split(" ")
        lines = []
        current_line = ""

        for word in words:
            test_line = word if current_line == "" else current_line + " " + word

            if font.size(test_line)[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                    current_line = word
                else:
                    broken = ""

                    for char in word:
                        test_word = broken + char

                        if font.size(test_word)[0] <= max_width:
                            broken = test_word
                        else:
                            if broken:
                                lines.append(broken)
                            broken = char

                    current_line = broken

            if len(lines) >= max_lines:
                break

        if current_line and len(lines) < max_lines:
            lines.append(current_line)

        return lines

    def open_game_options(self):
        from customize_screen import CustomizeScreen
        self.manager.set_screen(CustomizeScreen(self.manager, self.client_state, self.network))

    def toggle_panel(self):
        self.panel_open = not self.panel_open

        if self.panel_open:
            self.status_message = "Choose a player to challenge or chat with."
        else:
            self.status_message = "Players panel closed."

    def set_players(self, players):
        filtered = [p for p in players if p.get("username") != self.username]
        self.players = filtered
        self.list_box.set_items(filtered)

        active_chat = self.client_state.get("active_chat_user")
        online_names = {player.get("username") for player in filtered}

        if active_chat and active_chat not in online_names:
            self.client_state["active_chat_user"] = None

        if len(filtered) == 0:
            self.status_message = "No other players online yet."
        else:
            self.status_message = "Choose a player to challenge or chat with."

    def challenge_player(self):
        selected = self.list_box.get_selected_item()

        if not selected:
            self.error_message = "Select a player first."
            return

        self.error_message = ""
        opponent = selected["username"]
        self.client_state["selected_opponent"] = opponent

        if self.network:
            self.network.send_challenge(opponent)

        self.status_message = f"Challenge sent to {opponent}."

    def open_chat_with_selected(self):
        selected = self.list_box.get_selected_item()

        if not selected:
            self.error_message = "Select a player first."
            return

        chat_user = selected["username"]
        self.client_state["active_chat_user"] = chat_user
        self.client_state.setdefault("chat_histories", {}).setdefault(chat_user, [])
        self.client_state.setdefault("unread_chats", {})[chat_user] = 0

        self.chat_input.clear()
        self.chat_input.active = True

        self.error_message = ""
        self.status_message = f"Chat opened with {chat_user}."

    def close_chat(self):
        self.client_state["active_chat_user"] = None
        self.chat_input.active = False

    def send_chat_message(self):
        target = self.client_state.get("active_chat_user")
        message = self.chat_input.get_value().strip()

        if not target:
            self.error_message = "Open a chat first."
            return

        if not message:
            self.error_message = "Type a message first."
            return

        self.error_message = ""

        if self.network:
            self.network.send_chat_message(target, message)

        self.chat_input.clear()
        self.chat_input.active = True

    def accept_challenge(self):
        challenger = self.client_state.get("pending_challenge_from")

        if not challenger:
            self.error_message = "No incoming challenge."
            return

        self.error_message = ""

        if self.network:
            self.network.send_challenge_accept(challenger)

        self.status_message = f"Accepted challenge from {challenger}."
        self.client_state["pending_challenge_from"] = None

    def reject_challenge(self):
        challenger = self.client_state.get("pending_challenge_from")

        if not challenger:
            self.error_message = "No incoming challenge."
            return

        self.error_message = ""

        if self.network:
            self.network.send_challenge_reject(challenger)

        self.status_message = f"Rejected challenge from {challenger}."
        self.client_state["pending_challenge_from"] = None

    def get_selected_player_action(self):
        selected = self.list_box.get_selected_item()

        if not selected:
            return None

        status = str(selected.get("status", "")).upper()

        if status == "IDLE":
            return "challenge"

        if status == "IN_GAME":
            return "spectate"

        return None

    def spectate_selected_player(self):
        selected = self.list_box.get_selected_item()

        if not selected:
            self.error_message = "Select a player first."
            return

        if str(selected.get("status", "")).upper() != "IN_GAME":
            self.error_message = "That player is not currently in a match."
            return

        target = selected["username"]
        self.error_message = ""

        if self.network:
            self.network.send_spectate_request(target)

        self.status_message = f"Requesting to spectate {target}'s match."

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit

            self.players_button.handle_event(event)
            self.game_option_button.handle_event(event)

            if self.panel_open:
                self.list_box.handle_event(event)

                action = self.get_selected_player_action()

                if action == "challenge":
                    self.challenge_button.handle_event(event)
                elif action == "spectate":
                    self.spectate_button.handle_event(event)

                self.chat_button.handle_event(event)

            if self.client_state.get("pending_challenge_from"):
                self.accept_button.handle_event(event)
                self.reject_button.handle_event(event)

            if self.client_state.get("active_chat_user"):
                self.chat_input.handle_event(event)
                self.send_button.handle_event(event)
                self.close_chat_button.handle_event(event)

                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN and self.chat_input.active:
                    self.send_chat_message()

    def update(self):
        target_x = 680 if self.panel_open else 1000
        speed = 24

        if self.panel_x < target_x:
            self.panel_x = min(self.panel_x + speed, target_x)
        elif self.panel_x > target_x:
            self.panel_x = max(self.panel_x - speed, target_x)

        self.list_box.rect.x = self.panel_x + 20
        self.challenge_button.rect.x = self.panel_x + 40
        self.chat_button.rect.x = self.panel_x + 40
        self.spectate_button.rect.x = self.panel_x + 40

        notifications = []

        for note in self.client_state.get("chat_notifications", []):
            if note.get("expires_at", 0) > time.time():
                notifications.append(note)

        self.client_state["chat_notifications"] = notifications

        if self.client_state.get("error"):
            self.error_message = self.client_state["error"]
            self.client_state["error"] = ""

        elif self.client_state.get("status"):
            self.status_message = self.client_state["status"]

    def draw_top_bar(self, surface):
        welcome_text = f"Welcome, {self.username}"

        shadow = config.TITLE_FONT.render(welcome_text, True, (80, 40, 10))
        gold = config.TITLE_FONT.render(welcome_text, True, (255, 220, 90))
        glow = config.TITLE_FONT.render(welcome_text, True, (255, 245, 180))

        scale = 0.62
        sw = int(shadow.get_width() * scale)
        sh = int(shadow.get_height() * scale)

        shadow = pygame.transform.smoothscale(shadow, (sw, sh))
        gold = pygame.transform.smoothscale(gold, (sw, sh))
        glow = pygame.transform.smoothscale(glow, (sw, sh))

        center_x = config.WINDOW_WIDTH // 2
        center_y = 365

        text_x = center_x - sw // 2
        text_y = center_y - sh // 2

        surface.blit(shadow, (text_x + 2, text_y + 4))
        surface.blit(gold, (text_x, text_y))
        surface.blit(glow, (text_x + 1, text_y + 1))

    def draw_message_box(self, surface):
        msg = self.error_message if self.error_message else self.status_message
        color = config.ERROR_COLOR if self.error_message else config.WHITE

        display_msg = self.fit_tail_ellipsis(msg, config.SMALL_FONT, 700)

        shadow = config.SMALL_FONT.render(display_msg, True, (20, 20, 30))
        text = config.SMALL_FONT.render(display_msg, True, color)

        center_x = config.WINDOW_WIDTH // 2
        center_y = 645

        shadow_rect = shadow.get_rect(center=(center_x + 2, center_y + 2))
        text_rect = text.get_rect(center=(center_x, center_y))

        surface.blit(shadow, shadow_rect)
        surface.blit(text, text_rect)

    def draw_side_panel(self, surface):
        panel = pygame.Rect(self.panel_x, 100, 300, 560)

        pygame.draw.rect(surface, (8, 16, 48), panel, border_radius=22)
        pygame.draw.rect(surface, (95, 220, 255), panel, 3, border_radius=22)

        self.list_box.draw(surface)

        selected = self.list_box.get_selected_item()

        if selected:
            name = selected["username"]
            unread_count = self.client_state.get("unread_chats", {}).get(name, 0)

            selected_text = self.fit_end_ellipsis(f"Selected: {name}", config.SMALL_FONT, 240)
            txt = config.SMALL_FONT.render(selected_text, True, config.WHITE)
            surface.blit(txt, (self.panel_x + 30, 462))

            action = self.get_selected_player_action()

            if action == "challenge":
                self.challenge_button.draw(surface)
            elif action == "spectate":
                self.spectate_button.draw(surface)

            self.chat_button.draw(surface)

            if unread_count:
                badge_radius = 13
                badge_x = self.chat_button.rect.right - 16
                badge_y = self.chat_button.rect.y + 12

                pygame.draw.circle(surface, (120, 0, 0), (badge_x, badge_y), badge_radius + 3)
                pygame.draw.circle(surface, (255, 55, 55), (badge_x, badge_y), badge_radius)

                if unread_count > 9:
                    badge_text = "9+"
                else:
                    badge_text = str(unread_count)

                number = config.TINY_FONT.render(badge_text, True, config.WHITE)
                number_rect = number.get_rect(center=(badge_x, badge_y))
                surface.blit(number, number_rect)

    def draw_current_game_option(self, surface):
        color_name = self.client_state.get("snake_color", "blue")
        label = f"Snake Color: {color_name.upper()}"

        panel = pygame.Rect(28, 105, 265, 54)

        pygame.draw.rect(surface, (8, 18, 55), panel, border_radius=14)
        pygame.draw.rect(surface, (95, 220, 255), panel, 2, border_radius=14)

        shadow = config.SMALL_FONT.render(label, True, (50, 25, 10))
        gold = config.SMALL_FONT.render(label, True, (255, 220, 90))
        glow = config.SMALL_FONT.render(label, True, (255, 245, 180))

        surface.blit(shadow, (45, 121))
        surface.blit(gold, (43, 119))
        surface.blit(glow, (44, 120))

        color_preview = {
            "red": (255, 90, 90),
            "pink": (255, 110, 190),
            "orange": (255, 165, 70),
            "yellow": (255, 215, 70),
            "green": (90, 220, 140),
            "cyan": (90, 235, 255),
            "blue": (70, 140, 255),
            "purple": (170, 100, 255),
            "white": (245, 245, 245),
            "black": (45, 45, 55)
        }.get(color_name, (70, 140, 255))

        pygame.draw.circle(surface, color_preview, (270, 132), 10)
        pygame.draw.circle(surface, (255, 255, 255), (270, 132), 2)

    def draw_pending_challenge(self, surface):
        challenger = self.client_state.get("pending_challenge_from")

        if not challenger:
            return

        box = pygame.Rect(28, 270, 300, 120)

        pygame.draw.rect(surface, (8, 18, 55), box, border_radius=18)
        pygame.draw.rect(surface, (255, 220, 90), box, 2, border_radius=18)

        title = config.SMALL_FONT.render("Incoming Challenge!", True, (255, 220, 90))
        challenger_text = self.fit_tail_ellipsis(f"From: {challenger}", config.TINY_FONT, 260)
        msg = config.TINY_FONT.render(challenger_text, True, config.WHITE)

        surface.blit(title, (48, 290))
        surface.blit(msg, (48, 325))

        self.accept_button.draw(surface)
        self.reject_button.draw(surface)

    def draw_chat_window(self, surface):
        chat_user = self.client_state.get("active_chat_user")

        if not chat_user:
            return

        box = pygame.Rect(320, 100, 350, 480)

        pygame.draw.rect(surface, (8, 18, 55), box, border_radius=20)
        pygame.draw.rect(surface, (255, 220, 90), box, 2, border_radius=20)

        header_text = self.fit_end_ellipsis(f"Chat with: {chat_user}", config.SMALL_FONT, 245)
        header = config.SMALL_FONT.render(header_text, True, config.WHITE)
        surface.blit(header, (340, 125))

        unread = self.client_state.setdefault("unread_chats", {})
        unread[chat_user] = 0

        messages_rect = pygame.Rect(336, 170, 318, 325)
        pygame.draw.rect(surface, (16, 26, 70), messages_rect, border_radius=16)

        messages = self.client_state.get("chat_histories", {}).get(chat_user, [])
        shown = messages[-5:]

        y = messages_rect.y + 12
        max_message_bottom = messages_rect.bottom - 10

        for message in shown:
            sender = "You" if message.get("outgoing") else message.get("sender", chat_user)
            sender = self.fit_tail_ellipsis(sender, config.TINY_FONT, 190)

            full_message_text = str(message.get("text", ""))

            bubble_w = 210
            text_max_width = bubble_w - 20

            message_lines = self.wrap_text(
                full_message_text,
                config.TINY_FONT,
                text_max_width,
                max_lines=3
            )

            bubble_h = 28 + (len(message_lines) * 17)
            bubble_h = max(42, bubble_h)

            if y + bubble_h > max_message_bottom:
                break

            bubble_x = messages_rect.x + 96 if message.get("outgoing") else messages_rect.x + 8
            bubble = pygame.Rect(bubble_x, y, bubble_w, bubble_h)

            fill = (50, 120, 210) if message.get("outgoing") else (45, 70, 120)
            border = (255, 220, 90) if message.get("outgoing") else (95, 220, 255)

            pygame.draw.rect(surface, fill, bubble, border_radius=14)
            pygame.draw.rect(surface, border, bubble, 2, border_radius=14)

            title = config.TINY_FONT.render(sender, True, config.WHITE)
            surface.blit(title, (bubble.x + 10, bubble.y + 4))

            line_y = bubble.y + 22

            for line in message_lines:
                line_surface = config.TINY_FONT.render(line, True, config.WHITE)
                surface.blit(line_surface, (bubble.x + 10, line_y))
                line_y += 17

            y += bubble_h + 10

        self.chat_input.draw(surface)
        self.send_button.draw(surface)
        self.close_chat_button.draw(surface)

    def draw_chat_notifications(self, surface):
        notifications = self.client_state.get("chat_notifications", [])[-2:]

        x = 28
        y = 420

        for note in notifications:
            box = pygame.Rect(x, y, 260, 52)

            pygame.draw.rect(surface, (255, 220, 90), box, border_radius=16)
            pygame.draw.rect(surface, (8, 18, 55), box.inflate(-4, -4), border_radius=14)

            note_text = self.fit_end_ellipsis(note.get("message", ""), config.TINY_FONT, 225)
            txt = config.TINY_FONT.render(note_text, True, config.WHITE)

            surface.blit(txt, (x + 16, y + 17))
            y += 62

    def draw(self, surface):
        surface.blit(self.background, (0, 0))

        overlay = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 35))
        surface.blit(overlay, (0, 0))

        self.draw_top_bar(surface)
        self.players_button.draw(surface)
        self.game_option_button.draw(surface)
        self.draw_current_game_option(surface)
        self.draw_message_box(surface)
        self.draw_side_panel(surface)
        self.draw_pending_challenge(surface)
        self.draw_chat_window(surface)
        self.draw_chat_notifications(surface)
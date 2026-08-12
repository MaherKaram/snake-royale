import os
import math
import pygame
import config
from base_screen import BaseScreen
from button import Button


class CustomizeScreen(BaseScreen):
    DEFAULT_CONTROLS = {
        "up": "w",
        "down": "s",
        "left": "a",
        "right": "d",
    }

    CONTROL_DIRECTIONS = [
        ("up", "UP"),
        ("down", "DOWN"),
        ("left", "LEFT"),
        ("right", "RIGHT"),
    ]

    def __init__(self, manager, client_state, network):
        super().__init__(manager)
        self.client_state = client_state
        self.network = network
        self.background = self.load_background()

        self.colors = [
            ("red", (255, 60, 60)),
            ("pink", (255, 100, 180)),
            ("orange", (255, 150, 50)),
            ("yellow", (255, 230, 60)),
            ("green", (80, 240, 120)),
            ("cyan", (60, 240, 255)),
            ("blue", (50, 130, 255)),
            ("purple", (160, 90, 255)),
            ("white", (240, 240, 245)),
            ("black", (40, 40, 50)),
        ]

        current_name = str(self.client_state.get("snake_color", "blue")).lower()
        self.selected_color_name = current_name
        self.selected_color_value = self.get_color_value(current_name)

        self.controls = self.normalize_controls(
            self.client_state.get("controls", self.DEFAULT_CONTROLS)
        )

        self.waiting_for_action = None
        self.error_message = ""
        self.status_message = "Click a movement box, then press the key you want to use."

        self.reset_button = Button((220, 610, 220, 60), "RESET KEYS", self.reset_controls)
        self.confirm_button = Button((540, 610, 240, 60), "CONFIRM", self.confirm_customization)
        self.back_button = Button((60, 22, 140, 55), "BACK", self.go_back)

    def load_background(self):
        path = os.path.join("assets", "snake_royale_bg.png")
        try:
            img = pygame.image.load(path).convert()
            img = pygame.transform.smoothscale(img, (config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
            return img
        except Exception:
            bg = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
            bg.fill((5, 5, 15))
            return bg

    def get_color_value(self, name):
        target = str(name).lower()
        for color_name, val in self.colors:
            if color_name.lower() == target:
                return val
        return (50, 130, 255)

    def normalize_controls(self, controls):
        normalized = dict(self.DEFAULT_CONTROLS)

        if isinstance(controls, dict):
            for action in normalized:
                value = str(controls.get(action, normalized[action])).strip().lower()
                if value:
                    normalized[action] = value

        values = list(normalized.values())
        if len(values) != len(set(values)):
            return dict(self.DEFAULT_CONTROLS)

        return normalized

    def get_control_rects(self):
        rects = {}
        start_x = 95
        y = 525
        width = 190
        height = 58
        gap = 20

        for index, (action, label) in enumerate(self.CONTROL_DIRECTIONS):
            rects[action] = pygame.Rect(start_x + index * (width + gap), y, width, height)

        return rects

    def get_palette_rects(self):
        rects = []
        x_start = 185
        y_pos = 430
        b_size = 48
        gap = 15

        for i, (name, val) in enumerate(self.colors):
            rect = pygame.Rect(x_start + i * (b_size + gap), y_pos, b_size, b_size)
            rects.append((name, val, rect))

        return rects

    def key_display_name(self, key_name):
        pretty = str(key_name).upper()
        replacements = {
            "SPACE": "SPACE",
            "UP": "ARROW UP",
            "DOWN": "ARROW DOWN",
            "LEFT": "ARROW LEFT",
            "RIGHT": "ARROW RIGHT",
            "LEFT SHIFT": "L SHIFT",
            "RIGHT SHIFT": "R SHIFT",
            "LEFT CTRL": "L CTRL",
            "RIGHT CTRL": "R CTRL",
        }
        return replacements.get(pretty, pretty)

    def validate_controls(self):
        missing = [action for action in self.DEFAULT_CONTROLS if not self.controls.get(action)]
        if missing:
            return False, "Every movement direction must have a key."

        assigned = list(self.controls.values())
        if len(assigned) != len(set(assigned)):
            return False, "Each movement direction must use a different key."

        return True, ""

    def go_back(self):
        from lobby_screen import LobbyScreen
        lobby = LobbyScreen(self.manager, self.client_state, self.network)
        if hasattr(lobby, "set_players"):
            lobby.set_players(self.client_state.get("online_players", []))
        self.manager.set_screen(lobby)

    def confirm_customization(self):
        ok, reason = self.validate_controls()
        if not ok:
            self.error_message = reason
            self.status_message = "Fix the movement keys before confirming."
            return

        controls_to_save = dict(self.controls)
        self.network.send_customization(self.selected_color_name.lower(), controls_to_save)
        self.go_back()

    def reset_controls(self):
        self.controls = dict(self.DEFAULT_CONTROLS)
        self.waiting_for_action = None
        self.error_message = ""
        self.status_message = "Movement keys reset to W A S D."

    def assign_key(self, event):
        if not self.waiting_for_action:
            return

        key_name = pygame.key.name(event.key).strip().lower()

        if not key_name or key_name == "unknown":
            self.error_message = "This key cannot be used. Choose another one."
            return

        if key_name == "escape":
            self.error_message = "Escape is reserved for closing the game. Choose another key."
            return

        for action, current_key in self.controls.items():
            if action != self.waiting_for_action and current_key == key_name:
                self.error_message = f"{self.key_display_name(key_name)} is already used for {action.upper()}."
                return

        action_name = self.waiting_for_action
        self.controls[action_name] = key_name
        self.waiting_for_action = None
        self.error_message = ""
        self.status_message = f"{action_name.upper()} is now set to {self.key_display_name(key_name)}."

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit

            if event.type == pygame.KEYDOWN and self.waiting_for_action:
                self.assign_key(event)
                continue

            self.confirm_button.handle_event(event)
            self.reset_button.handle_event(event)
            self.back_button.handle_event(event)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for name, val, rect in self.get_palette_rects():
                    if rect.collidepoint(event.pos):
                        self.selected_color_name = name
                        self.selected_color_value = val
                        self.error_message = ""
                        self.status_message = f"Snake color set to {name.upper()}."
                        break

                for action, rect in self.get_control_rects().items():
                    if rect.collidepoint(event.pos):
                        self.waiting_for_action = action
                        self.error_message = ""
                        self.status_message = f"Press a key for {action.upper()}."
                        break

    def update(self):
        pass

    def draw_sleek_snake(self, surface):
        base = self.selected_color_value
        dark = (
            max(0, base[0] - 75),
            max(0, base[1] - 75),
            max(0, base[2] - 75),
        )
        light = (
            min(255, base[0] + 35),
            min(255, base[1] + 35),
            min(255, base[2] + 35),
        )

        pts = [
            (685, 270),
            (640, 245),
            (590, 232),
            (535, 235),
            (480, 255),
            (425, 285),
            (365, 300),
            (305, 288),
            (255, 258),
        ]

        for i in range(len(pts) - 1):
            a = pts[i]
            b = pts[i + 1]

            width = max(22, 48 - i * 2)

            pygame.draw.line(surface, (15, 15, 30), (a[0] + 5, a[1] + 7), (b[0] + 5, b[1] + 7), width)
            pygame.draw.line(surface, dark, a, b, width)
            pygame.draw.line(
                surface,
                base,
                (a[0], a[1] - 4),
                (b[0], b[1] - 4),
                max(10, width - 10),
            )


        for i, (x, y) in enumerate(pts):
            r = max(17, 27 - i)

            pygame.draw.circle(surface, (15, 15, 30), (x + 5, y + 7), r)
            pygame.draw.circle(surface, dark, (x, y), r)
            pygame.draw.circle(surface, base, (x, y - 3), max(8, r - 4))

            shine_rect = pygame.Rect(
                x - r // 2,
                y - r // 2 - 4,
                max(5, r),
                max(4, r // 2),
            )
            pygame.draw.ellipse(surface, light, shine_rect)

        hx, hy = pts[0]
        head_r = 34

        pygame.draw.circle(surface, (15, 15, 30), (hx + 5, hy + 8), head_r)
        pygame.draw.circle(surface, dark, (hx, hy), head_r)
        pygame.draw.circle(surface, base, (hx, hy - 4), head_r - 5)

        head_shine = pygame.Rect(hx - 18, hy - 24, 32, 16)
        pygame.draw.ellipse(surface, light, head_shine)

        
        pygame.draw.circle(surface, config.WHITE, (hx - 10, hy - 13), 8)
        pygame.draw.circle(surface, config.WHITE, (hx + 13, hy - 10), 8)
        pygame.draw.circle(surface, config.BLACK, (hx - 8, hy - 12), 3)
        pygame.draw.circle(surface, config.BLACK, (hx + 15, hy - 9), 3)

        pygame.draw.line(surface, dark, (hx - 19, hy - 23), (hx - 4, hy - 18), 3)
        pygame.draw.line(surface, dark, (hx + 5, hy - 18), (hx + 22, hy - 22), 3)

        tongue_points = [
            (hx + 25, hy + 8),
            (hx + 55, hy + 15),
            (hx + 77, hy + 6),
        ]
        pygame.draw.lines(surface, (255, 70, 100), False, tongue_points, 4)
        pygame.draw.line(surface, (255, 70, 100), (hx + 55, hy + 15), (hx + 72, hy + 25), 3)

        spot_color = (
            max(0, base[0] - 35),
            max(0, base[1] - 35),
            max(0, base[2] - 35),
        )

        for i, (x, y) in enumerate(pts[2:7]):
            pygame.draw.circle(surface, spot_color, (x + 8, y + 4), max(4, 8 - i // 2))

    def draw_control_box(self, surface, action, label, rect):
        is_active = self.waiting_for_action == action
        border_color = (255, 230, 90) if is_active else (100, 150, 255)
        fill_color = (28, 35, 85) if is_active else (12, 18, 55)

        glow = pygame.Surface((rect.w + 16, rect.h + 16), pygame.SRCALPHA)
        pygame.draw.rect(glow, (*border_color, 45), (8, 8, rect.w, rect.h), border_radius=16)
        surface.blit(glow, (rect.x - 8, rect.y - 8))

        pygame.draw.rect(surface, fill_color, rect, border_radius=15)
        pygame.draw.rect(surface, border_color, rect, 3, border_radius=15)

        label_text = config.TINY_FONT.render(label, True, (180, 220, 255))
        key_text = config.NORMAL_FONT.render(
            self.key_display_name(self.controls.get(action, "")),
            True,
            (255, 255, 255),
        )

        surface.blit(label_text, (rect.centerx - label_text.get_width() // 2, rect.y + 5))
        surface.blit(key_text, (rect.centerx - key_text.get_width() // 2, rect.y + 23))

    def draw(self, surface):
        surface.blit(self.background, (0, 0))

        overlay = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 145))
        surface.blit(overlay, (0, 0))

        frame = pygame.Rect(60, 85, 880, 595)
        pygame.draw.rect(surface, (20, 20, 35), frame, border_radius=25)
        pygame.draw.rect(surface, (100, 150, 255), frame, 2, border_radius=25)

        title = config.TITLE_FONT.render("CUSTOMIZE SNAKE & KEYS", True, (255, 255, 255))
        surface.blit(title, (config.WINDOW_WIDTH // 2 - title.get_width() // 2, 105))

        preview_rect = pygame.Rect(120, 165, 760, 210)
        pygame.draw.rect(surface, (10, 10, 20), preview_rect, border_radius=15)
        pygame.draw.rect(surface, (60, 110, 210), preview_rect, 2, border_radius=15)
        self.draw_sleek_snake(surface)

        status_text = config.SMALL_FONT.render(
            f"COLOR: {self.selected_color_name.upper()}",
            True,
            (255, 255, 255),
        )
        text_x = config.WINDOW_WIDTH // 2 - status_text.get_width() // 2

        pygame.draw.circle(surface, (255, 255, 255), (text_x - 25, 403), 12)
        pygame.draw.circle(surface, self.selected_color_value, (text_x - 25, 403), 9)
        surface.blit(status_text, (text_x, 391))

        for name, val, rect in self.get_palette_rects():
            if self.selected_color_name.lower() == name.lower():
                pygame.draw.rect(surface, (255, 255, 255), rect.inflate(8, 8), 3, border_radius=12)

            pygame.draw.rect(surface, val, rect, border_radius=10)

            gloss = pygame.Surface((rect.w, rect.h // 2), pygame.SRCALPHA)
            gloss.fill((255, 255, 255, 40))
            surface.blit(gloss, (rect.x, rect.y))

        keys_title = config.SMALL_FONT.render("MOVEMENT KEYS", True, (255, 255, 255))
        surface.blit(keys_title, (config.WINDOW_WIDTH // 2 - keys_title.get_width() // 2, 493))

        for action, label in self.CONTROL_DIRECTIONS:
            self.draw_control_box(surface, action, label, self.get_control_rects()[action])

        message = self.error_message if self.error_message else self.status_message
        message_color = config.ERROR_COLOR if self.error_message else (190, 230, 255)
        message_text = config.TINY_FONT.render(message, True, message_color)
        surface.blit(message_text, (config.WINDOW_WIDTH // 2 - message_text.get_width() // 2, 588))

        self.confirm_button.draw(surface)
        self.reset_button.draw(surface)
        self.back_button.draw(surface)
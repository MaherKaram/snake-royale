import pygame
import config

class ListBox:
    def __init__(self, rect, items=None):
        self.rect = pygame.Rect(rect)
        self.items = items or []
        self.selected_index = None
        self.item_height = 58
        self.header_h = 52
        self.rows = []

    def set_items(self, items):
        self.items = items
        if self.selected_index is not None and self.selected_index >= len(self.items):
            self.selected_index = None

    def get_selected_item(self):
        if self.selected_index is None:
            return None
        if 0 <= self.selected_index < len(self.items):
            return self.items[self.selected_index]
        return None

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for idx, row in enumerate(self.rows):
                if row.collidepoint(event.pos):
                    self.selected_index = idx
                    return

    def fit_name(self, text, max_width):
        if config.NORMAL_FONT.size(text)[0] <= max_width:
            return text
        trimmed = text
        while trimmed and config.NORMAL_FONT.size(trimmed + "...")[0] > max_width:
            trimmed = trimmed[:-1]
        return trimmed + "..."

    def draw(self, surface):
        x, y, w, h = self.rect
        self.rows = []

        shadow = pygame.Rect(x + 6, y + 8, w, h)
        pygame.draw.rect(surface, (20, 30, 70), shadow, border_radius=18)

        pygame.draw.rect(surface, (18, 24, 60), self.rect, border_radius=18)
        pygame.draw.rect(surface, (95, 220, 255), self.rect, 3, border_radius=18)

        title = config.NORMAL_FONT.render("ONLINE PLAYERS", True, config.WHITE)
        surface.blit(title, (x + 18, y + 14))

        start_y = y + self.header_h
        for i, item in enumerate(self.items):
            row = pygame.Rect(x + 12, start_y + i * self.item_height, w - 24, 46)
            self.rows.append(row)

            if i == self.selected_index:
                pygame.draw.rect(surface, (45, 80, 170), row, border_radius=12)
                pygame.draw.rect(surface, (255, 215, 70), row, 2, border_radius=12)
            else:
                pygame.draw.rect(surface, (28, 38, 90), row, border_radius=12)

            status = str(item.get("status", "IDLE")).upper()
            dot = (90, 220, 140) if status == "IDLE" else (255, 180, 70)

            pygame.draw.circle(surface, dot, (row.x + 18, row.y + 23), 6)

            name = str(item.get("username", "Unknown"))
            name = self.fit_name(name, max_width=150)

            name_text = config.NORMAL_FONT.render(name, True, config.WHITE)
            status_text = config.TINY_FONT.render(status, True, (180, 210, 235))

            surface.blit(name_text, (row.x + 34, row.y + 8))
            surface.blit(status_text, (row.right - status_text.get_width() - 12, row.y + 15))
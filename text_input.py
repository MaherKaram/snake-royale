import pygame
import config


class TextInput:
    def __init__(
        self,
        rect,
        placeholder="",
        text="",
        max_length=22,
        font=None,
        placeholder_font=None,
        padding_x=14,
        text_align="left"
    ):
        self.rect = pygame.Rect(rect)
        self.placeholder = placeholder
        self.text = text
        self.active = False
        self.max_length = max_length

        self.font = font or config.NORMAL_FONT
        self.placeholder_font = placeholder_font or self.font
        self.padding_x = padding_x 
        self.text_align = text_align

    def get_value(self):
        return self.text

    def set_value(self, value):
        self.text = str(value)

    def clear(self):
        self.text = ""

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.active = self.rect.collidepoint(event.pos)

        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]

            elif event.key == pygame.K_RETURN:
                pass

            else:
                if len(event.unicode) == 1 and len(self.text) < self.max_length:
                    self.text += event.unicode

    def get_tail_ellipsis_display(self, text, font, max_width):
        """
        Shortens only the DISPLAYED text.
        It never changes self.text, so the real typed message stays complete.
        """
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

    def draw(self, surface):
        x, y, w, h = self.rect

        glow = pygame.Surface((w + 24, h + 24), pygame.SRCALPHA)
        pygame.draw.rect(glow, (90, 220, 255, 45), (12, 12, w, h), border_radius=18)
        pygame.draw.rect(glow, (90, 220, 255, 25), (6, 6, w + 12, h + 12), border_radius=22)
        surface.blit(glow, (x - 12, y - 12))

        outer = pygame.Rect(x, y, w, h)
        pygame.draw.rect(surface, (20, 28, 70), outer, border_radius=16)

        border_color = (255, 220, 90) if self.active else (110, 235, 255)
        pygame.draw.rect(surface, border_color, outer, 3, border_radius=16)

        inner = pygame.Rect(x + 4, y + 4, w - 8, h - 8)
        pygame.draw.rect(surface, (8, 16, 48), inner, border_radius=14)

        shine = pygame.Surface((max(1, w - 20), 12), pygame.SRCALPHA)
        pygame.draw.rect(shine, (180, 245, 255, 55), (0, 0, max(1, w - 20), 12), border_radius=8)
        surface.blit(shine, (x + 10, y + 8))

        has_text = bool(self.text)

        original_text = self.text if has_text else self.placeholder
        font = self.font if has_text else self.placeholder_font
        color = (235, 245, 255) if has_text else (165, 210, 230)

        max_text_width = max(20, w - self.padding_x * 2)

        display_text = self.get_tail_ellipsis_display(
            original_text,
            font,
            max_text_width
        )

        text_surf = font.render(display_text, True, color)
        text_rect = text_surf.get_rect()
        text_rect.centery = outer.centery

        if self.text_align == "center":
            text_rect.centerx = outer.centerx
        else:
            text_rect.x = x + self.padding_x

        old_clip = surface.get_clip()
        surface.set_clip(inner.inflate(-8, -8))
        surface.blit(text_surf, text_rect)
        surface.set_clip(old_clip)
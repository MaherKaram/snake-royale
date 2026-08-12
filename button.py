import pygame
import config

class Button:
    def __init__(self, rect, text, callback, bg=None, hover=None, text_color=None):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.callback = callback

        self.bg = bg or (68, 96, 150)
        self.hover = hover or (82, 112, 168)
        self.pressed = (54, 78, 126)
        self.border = (170, 142, 88)
        self.border_light = (225, 200, 138)
        self.text_color = text_color or config.WHITE

        self.is_hovered = False
        self.is_pressed = False
        self.anim_scale = 1.0
        self.anim_offset_y = 0.0

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.is_pressed = True

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was_pressed = self.is_pressed
            self.is_pressed = False
            if was_pressed and self.rect.collidepoint(event.pos):
                self.callback()

    def update_animation(self):
        target_scale = 0.985 if self.is_pressed else (1.015 if self.is_hovered else 1.0)
        target_offset = 4 if self.is_pressed else (1 if self.is_hovered else 0)

        self.anim_scale += (target_scale - self.anim_scale) * 0.22
        self.anim_offset_y += (target_offset - self.anim_offset_y) * 0.22

    def current_fill(self):
        if self.is_pressed:
            return self.pressed
        if self.is_hovered:
            return self.hover
        return self.bg

    def draw(self, surface):
        self.update_animation()

        color = self.current_fill()

        cx, cy = self.rect.center
        draw_w = int(self.rect.w * self.anim_scale)
        draw_h = int(self.rect.h * self.anim_scale)
        draw_x = cx - draw_w // 2
        draw_y = cy - draw_h // 2 + int(self.anim_offset_y)

        outer = pygame.Rect(draw_x, draw_y, draw_w, draw_h)
        shadow = pygame.Rect(draw_x, draw_y + 6, draw_w, draw_h)

        pygame.draw.rect(surface, (18, 20, 32), shadow, border_radius=14)

        pygame.draw.rect(surface, self.border, outer, border_radius=14)
        pygame.draw.rect(surface, self.border_light, outer, 2, border_radius=14)

        inner = outer.inflate(-8, -8)
        pygame.draw.rect(surface, color, inner, border_radius=12)

        lower = pygame.Rect(inner.x, inner.y + inner.h // 2, inner.w, inner.h // 2)
        lower_color = (
            max(0, color[0] - 18),
            max(0, color[1] - 18),
            max(0, color[2] - 18)
        )
        pygame.draw.rect(surface, lower_color, lower, border_radius=12)

        shine = pygame.Surface((max(1, inner.w - 18), 10), pygame.SRCALPHA)
        pygame.draw.rect(shine, (255, 255, 255, 38), (0, 0, shine.get_width(), 10), border_radius=6)
        surface.blit(shine, (inner.x + 9, inner.y + 7))

        text_surf = config.NORMAL_FONT.render(self.text, True, self.text_color)
        text_shadow = config.NORMAL_FONT.render(self.text, True, (25, 28, 38))

        tx = outer.centerx - text_surf.get_width() // 2
        ty = outer.centery - text_surf.get_height() // 2 - 1

        surface.blit(text_shadow, (tx + 1, ty + 2))
        surface.blit(text_surf, (tx, ty))
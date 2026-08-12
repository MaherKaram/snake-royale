import math
import pygame
import config

def draw_vertical_gradient(surface, top, bottom):
    w, h = surface.get_size()
    for y in range(h):
        t = y / max(1, h - 1)
        r = int(top[0] * (1 - t) + bottom[0] * t)
        g = int(top[1] * (1 - t) + bottom[1] * t)
        b = int(top[2] * (1 - t) + bottom[2] * t)
        pygame.draw.line(surface, (r, g, b), (0, y), (w, y))

def draw_cloud(surface, x, y, s=1.0):
    c = (238, 244, 255)
    pygame.draw.circle(surface, c, (int(x), int(y)), int(24 * s))
    pygame.draw.circle(surface, c, (int(x + 26 * s), int(y - 12 * s)), int(30 * s))
    pygame.draw.circle(surface, c, (int(x + 60 * s), int(y)), int(24 * s))
    pygame.draw.ellipse(surface, c, (x - 12 * s, y, 95 * s, 30 * s))

def draw_tower(surface, x, base_y, scale=1.0):
    body_w = int(82 * scale)
    body_h = int(180 * scale)
    body = pygame.Rect(x, base_y - body_h, body_w, body_h)

    pygame.draw.rect(surface, (175, 185, 205), body, border_radius=10)
    pygame.draw.rect(surface, (110, 118, 148), body, 3, border_radius=10)

    brick_h = int(18 * scale)
    for yy in range(body.y + 16, body.bottom - 12, brick_h):
        pygame.draw.line(surface, (145, 155, 180), (body.x + 5, yy), (body.right - 5, yy), 2)

    crenel_w = int(16 * scale)
    for i in range(4):
        rr = pygame.Rect(body.x + 5 + i * (crenel_w + 4), body.y - 14, crenel_w, 18)
        pygame.draw.rect(surface, (185, 195, 215), rr, border_radius=3)
        pygame.draw.rect(surface, (110, 118, 148), rr, 2, border_radius=3)

    door = pygame.Rect(body.centerx - 12, body.bottom - 34, 24, 34)
    pygame.draw.rect(surface, (90, 70, 60), door, border_radius=8)

def draw_banner(surface, x, y, color, flip=False):
    pole_color = (120, 90, 55)
    pygame.draw.rect(surface, pole_color, (x, y - 6, 6, 90), border_radius=3)

    if not flip:
        pts = [(x + 5, y), (x + 55, y + 10), (x + 45, y + 72), (x + 25, y + 58), (x + 8, y + 72)]
    else:
        pts = [(x + 5, y), (x - 45, y + 10), (x - 35, y + 72), (x - 15, y + 58), (x + 2, y + 72)]

    dark = tuple(max(0, c - 60) for c in color)
    pygame.draw.polygon(surface, dark, pts)
    inset = [(px, py - 4) for px, py in pts]
    pygame.draw.polygon(surface, color, inset)

def draw_panel(surface, rect, fill, border=(255, 255, 255), shadow=True):
    if shadow:
        shadow_rect = pygame.Rect(rect.x + 8, rect.y + 8, rect.w, rect.h)
        pygame.draw.rect(surface, (25, 25, 45), shadow_rect, border_radius=24)
    pygame.draw.rect(surface, fill, rect, border_radius=24)
    pygame.draw.rect(surface, border, rect, 3, border_radius=24)

def draw_scene_background(surface):
    w, h = surface.get_size()

    draw_vertical_gradient(surface, (110, 170, 235), (52, 83, 145))

    draw_cloud(surface, 85, 90, 1.15)
    draw_cloud(surface, 430, 70, 0.9)
    draw_cloud(surface, 770, 100, 1.1)

    pygame.draw.ellipse(surface, (86, 142, 112), (-120, h - 220, 420, 180))
    pygame.draw.ellipse(surface, (94, 154, 120), (180, h - 215, 360, 170))
    pygame.draw.ellipse(surface, (88, 148, 116), (520, h - 230, 430, 190))

    draw_tower(surface, 40, h - 190, 1.1)
    draw_tower(surface, w - 122, h - 190, 1.1)

    draw_banner(surface, 145, 170, (170, 40, 40), flip=False)
    draw_banner(surface, w - 145, 170, (60, 110, 190), flip=True)

    ground = pygame.Rect(0, h - 120, w, 120)
    pygame.draw.rect(surface, (94, 120, 78), ground)

    for y in range(h - 118, h, 18):
        pygame.draw.line(surface, (120, 146, 96), (0, y), (w, y), 2)

    for x in range(0, w, 42):
        pygame.draw.line(surface, (118, 140, 90), (x, h - 120), (x + 20, h), 2)
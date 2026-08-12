import pygame

WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 700
FPS = 60
WINDOW_TITLE = "Snake Royale"

WHITE = (255, 255, 255)
BLACK = (20, 20, 30)
GRAY = (170, 170, 190)
ERROR_COLOR = (255, 140, 140)

BG_TOP = (110, 190, 255)
BG_BOTTOM = (210, 245, 255)

TEXT_COLOR = WHITE
TITLE_COLOR = (70, 60, 120)

PANEL_GLASS = (8, 18, 55, 190)


ARENA_TILE = (110, 220, 255)
ARENA_BORDER = (70, 180, 240)
ARENA_GRID = (210, 255, 255)


PINK = (255, 140, 200)
CYAN = (90, 220, 255)
YELLOW = (255, 220, 110)
GREEN = (140, 230, 170)
PURPLE = (170, 140, 255)
RED = (255, 80, 120)

pygame.font.init()
TITLE_FONT = pygame.font.SysFont("arial", 54, bold=True)
NORMAL_FONT = pygame.font.SysFont("arial", 28, bold=True)
SMALL_FONT = pygame.font.SysFont("arial", 22)
TINY_FONT = pygame.font.SysFont("arial", 18)
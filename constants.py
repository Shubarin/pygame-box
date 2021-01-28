import os
import pygame
import sqlite3

SIZE = SCREEN_WIDTH, SCREEN_HEIGHT = 550, 500
tile_width = tile_height = 50
ROWS = SCREEN_HEIGHT // tile_height
COLUMNS = SCREEN_WIDTH // tile_width
GRAVITY = 0.4
FPS = 30
STEP = 5
DOWN_BORDER = 30
screen_rect = (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT - tile_height - DOWN_BORDER)
ERROR_RATE = 10
LINE_PER_LEVEL = 3
START_V = 15
BOMBS_INTERVALS = 500
INSTERVALS_PITCH = 200
IMAGES_PATH = os.path.join('data', 'images')
MUSIC_PATH = os.path.join('data', 'music')
DB_NAME = os.path.join('data', 'db.db')
DEFAULT_DIFFICULT = 'Средне'
MARGIN_STATUS = 25
HEALTHS = 10

# Настройка управления
RIGHT_KEY = pygame.K_RIGHT
LEFT_KEY = pygame.K_LEFT
UP_KEY = pygame.K_SPACE


def setup_controller() -> None:
    """
    переопределяет кнопки управления
    :return None:
    """
    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()
    keys_in_db = cur.execute(
        'SELECT key '
        'FROM controller '
        'ORDER BY id'
    ).fetchall()
    global UP_KEY, RIGHT_KEY, LEFT_KEY
    RIGHT_KEY = keys_in_db[0][0]
    LEFT_KEY = keys_in_db[1][0]
    UP_KEY = keys_in_db[2][0]


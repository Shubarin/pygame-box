import os

SIZE = SCREEN_WIDTH, SCREEN_HEIGHT = 550, 500
tile_width = tile_height = 50
ROWS = SCREEN_HEIGHT // tile_height
COLUMNS = SCREEN_WIDTH // tile_width
GRAVITY = 0.4
FPS = 30
STEP = 5
DOWN_BORDER = 30
screen_rect = (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT - tile_height - DOWN_BORDER)
ERROR_RATE = 35
LINE_PER_LEVEL = 3
START_V = 15
BOMBS_INTERVALS = 500
INSTERVALS_PITCH = 500
IMAGES_PATH = os.path.join('data', 'images')
MUSIC_PATH = os.path.join('data', 'music')
DB_NAME = os.path.join('data', 'db.db')
DEFAULT_DIFFICULT = 'Средне'
MARGIN_STATUS = 25
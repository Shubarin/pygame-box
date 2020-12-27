import os
import sys
from random import randrange

import pygame

pygame.init()
SIZE = SCREEN_WIDTH, SCREEN_HEIGHT = 550, 500
tile_width = tile_height = 50
ROWS = SCREEN_HEIGHT // tile_height
COLUMNS = SCREEN_WIDTH // tile_width
GRAVITY = 0.2
clock = pygame.time.Clock()
FPS = 30
STEP = 10
screen = pygame.display.set_mode(SIZE)
screen_rect = (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT - tile_height - 30)
pygame.key.set_repeat(200, 70)
DOWN_BORDER = 20
BOMBGENERATE = pygame.USEREVENT + 1
pygame.time.set_timer(BOMBGENERATE, 3000)

all_sprites = pygame.sprite.Group()
tiles_group = pygame.sprite.Group()
player_group = pygame.sprite.Group()


def get_parametrs_object(obj):
    x, w = obj.rect.left, obj.rect.right
    y, h = obj.rect.top, obj.rect.bottom
    return x, w, y, h


def load_image(name, colorkey=None):
    fullname = os.path.join('data', name)
    image = pygame.image.load(fullname).convert()
    if colorkey is not None:
        if colorkey == -1:
            colorkey = image.get_at((0, 0))
        image.set_colorkey(colorkey)
    else:
        image = image.convert_alpha()
    return image


def terminate():
    pygame.quit()
    sys.exit()


def start_screen():
    intro_text = [
        'Коробочки', '',
        'Правила игры:',
        'С неба сбрасывают коробки.',
        "Герой должен расставлять их в линию,",
        'чтобы не дать вырасти столбикам до неба.',
        'При попадании по персонажу коробкой теряются жизни'
    ]

    fon = pygame.transform.scale(load_image('background-start.png'),
                                 (SCREEN_WIDTH, SCREEN_HEIGHT))
    screen.blit(fon, (0, 0))
    font = pygame.font.Font(None, 30)
    text_coord = 50
    for line in intro_text:
        string_rendered = font.render(line, 1, pygame.Color('black'))
        intro_rect = string_rendered.get_rect()
        text_coord += 10
        intro_rect.top = text_coord
        intro_rect.x = 10
        text_coord += intro_rect.height
        screen.blit(string_rendered, intro_rect)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                terminate()
            elif event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                return  # начинаем игру
        pygame.display.flip()
        clock.tick(FPS)


tile_images = {'box': load_image('box.png')}
player_image = load_image('mario.png')


class Tile(pygame.sprite.Sprite):
    def __init__(self, tile_type, pos_x):
        super().__init__(tiles_group, all_sprites)
        self.image = tile_images[tile_type]
        self.rect = self.image.get_rect().move(tile_width * pos_x,
                                               screen.get_rect().top)
        self.col = pos_x
        self.v = 5

    def update(self, *args, **kwargs) -> None:
        if self.rect.colliderect(screen_rect) and len(
                pygame.sprite.spritecollide(self, tiles_group, False)) == 1:
            self.rect.y += self.v
        else:
            for row in range(ROWS - 1, -1, -1):
                if self in game.board[row]:
                    return
                c, r = self.get_coords()
                if game.board[r][c] == 0:
                    self.rect.y = tile_height * r + DOWN_BORDER + (ROWS - r) * 2
                    self.rect.x = tile_width * c
                    game.board[r][c] = self
                break

    def get_coords(self):
        return self.rect.x * COLUMNS // SCREEN_WIDTH, \
               self.rect.y * ROWS // SCREEN_HEIGHT


screen_rect_for_player = (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT - tile_height - 20)


def side_collide(obj1, obj2):
    if not obj2:
        return
    x1, w1, y1, h1 = get_parametrs_object(obj1)
    x2, w2, y2, h2 = get_parametrs_object(obj2)
    sides = []
    if x1 + STEP <= x2:
        sides.append('объект справа')
    if x2 + STEP <= x1:
        sides.append('объект слева')
    if y1 + STEP <= y2:
        sides.append('на объекте')
    if y2 + STEP <= y1:
        sides.append('под объектом')
    return sides


class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__(player_group, all_sprites)
        self.image = player_image
        self.mask = self.image.get_masks()
        self.rect = self.image.get_rect().move(
            screen.get_rect().centerx - self.image.get_width() // 2,
            screen.get_rect().bottom - self.image.get_height() - 30
        )
        self.v = 1
        self.is_in_air = False
        self.gravity = GRAVITY
        self.flip = False
        self.jump = 9 * STEP

    def move_player(self, keys):
        side = side_collide(self,
                            pygame.sprite.spritecollideany(self, tiles_group))
        under_tile = False
        if side:
            under_tile = 'под объектом' in side

        # if under_tile and len(pygame.sprite.spritecollide(self, tiles_group, False)) > 0:
        #     pygame.sprite.spritecollide(self, tiles_group, True)

        if keys[pygame.K_UP] and not self.is_in_air and self.rect.y - self.jump > 0:
            self.rect.y -= self.jump
            self.is_in_air = True
        elif keys[pygame.K_DOWN] and self.rect.colliderect(
                screen_rect_for_player):
            self.is_in_air = False

        col, row = self.get_coords()
        left = False
        if keys[pygame.K_LEFT] and col >= 0:
            left = True
            self.rect.x -= STEP
            if self.flip:
                self.flip = False
                self.image = pygame.transform.flip(self.image, True, False)
        life_around_cell = self.get_count_around_tiles(row, col)
        if left and col - 1 > -1 and not game.board[row][col - 1] and life_around_cell == 0:
        # if left and col - 1 > -1 and not game.board[row][col - 1] and (col + 1 >= COLUMNS or not game.board[row][col + 1]) and not game.board[row - 1][col]:
            if game.board[row][col]:
                game.board[row][col].rect = game.board[row][col].rect.move(-tile_width, 0)
                game.board[row][col], game.board[row][col - 1] = game.board[row][col - 1], game.board[row][col]

        right = False
        if keys[pygame.K_RIGHT] and col + 1 < COLUMNS:
            right = True
            self.rect.x += STEP
            if not self.flip:
                self.image = pygame.transform.flip(self.image, True, False)
                self.flip = True
        life_around_cell = self.get_count_around_tiles(row, col)
        # if right and col + 2 < COLUMNS and not game.board[row][col + 2] and not game.board[row][col] and not game.board[row - 1][col + 2] and not game.board[row - 1][col + 1]:
        if right and col + 2 < COLUMNS and not game.board[row][col + 2] and life_around_cell <= 1:
            if game.board[row][col + 1]:
                game.board[row][col + 1].rect = game.board[row][col + 1].rect.move(tile_width, 0)
                game.board[row][col + 1], game.board[row][col + 2] = game.board[row][col + 2], game.board[row][col + 1]

    def get_count_around_tiles(self, row, col):
        dx = [1, 1, 1, 0, 0, -1, -1, -1]
        dy = [0, 1, -1, 1, -1, 1, -1, 0]
        life_around_cell = 0
        for x, y in zip(dx, dy):
            if x + col < 0 or x + col >= COLUMNS:
                continue
            if y + row < 0 or y + row >= ROWS:
                continue
            delta_col = col + x
            delta_row = row + y
            if game.board[delta_row][delta_col]:
                life_around_cell += 1
        return life_around_cell

    def get_coords(self):
        return (self.rect.x - self.image.get_width() // 2) * COLUMNS // SCREEN_WIDTH, \
               self.rect.y * ROWS // SCREEN_HEIGHT

    def update(self, *args, **kwargs) -> None:
        if args:
            self.move_player(args[0])
        if self.rect.colliderect(
                screen_rect_for_player) and not pygame.sprite.spritecollideany(
            self, tiles_group):
            self.v += self.gravity
            self.rect.y += self.v
        else:
            self.v = 1
            self.is_in_air = False


class Game:
    def __init__(self):
        self.player = Player()
        self.board = [[0] * COLUMNS for _ in range(ROWS)]

    def get_box(self, row, col):
        return self.board[row][col] == 1

    def check_line(self):
        for i, row in enumerate(self.board):
            if all(row):
                self.delete_row(i)

    def delete_row(self, row):
        for i in range(COLUMNS):
            self.board[row][i].kill()
            self.board[row][i] = 0
        del self.board[row]
        clock.tick(FPS)
        new_board = [[0] * COLUMNS]
        for r in range(ROWS - 1):
            line = []
            for tile in self.board[r]:
                if tile:
                    delta = 5 if r > 1 else 25
                    tile.rect.y = tile_height * r - DOWN_BORDER
                line.append(tile)
            new_board.append(line)
        self.board.clear()
        for r in new_board:
            self.board.append(r)


start_screen()

generation = False
game = Game()
keys = pygame.key.get_pressed()
i = 0
if __name__ == '__main__':
    while True:
        fon = pygame.transform.scale(load_image('background.png'),
                                     (SCREEN_WIDTH, SCREEN_HEIGHT))
        screen.blit(fon, (0, 0))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                terminate()
            if event.type == BOMBGENERATE:
                generation = True
            keys = pygame.key.get_pressed()
        if generation:
            col = randrange(COLUMNS)
            while game.board[3][col]:
                col = randrange(COLUMNS)
            Tile('box', 5)
            # Tile('box', i % COLUMNS)
            # i += 1
        generation = False
        player_group.update(keys)
        tiles_group.draw(screen)
        player_group.draw(screen)
        all_sprites.update()
        game.check_line()
        pygame.display.flip()
        clock.tick(FPS)

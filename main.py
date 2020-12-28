import os
import sys
from random import randrange
from typing import Union, List

import pygame

import constants

# инициализация констант
pygame.init()
clock = pygame.time.Clock()
screen: pygame.Surface = pygame.display.set_mode(constants.SIZE)
pygame.key.set_repeat(200, 70)
BOMBGENERATE: pygame.event = pygame.USEREVENT + 1
pygame.time.set_timer(BOMBGENERATE, 1000)  # интервал сброса коробочек


# загрузка игры
def load_image(name: str, colorkey: int = None) -> pygame.Surface:
    """
    Принимает на входе имя файла и необязательны параметр наличия фона.
        Преобразует файл в объект pygame.image, и удаляет фоновый цвет
    :param name: str
    :param colorkey: int
    :return image: pygame.Surface
    """
    try:
        fullname = os.path.join('data', name)
        image = pygame.image.load(fullname).convert()
        if colorkey is not None:
            if colorkey == -1:
                colorkey = image.get_at((0, 0))
            image.set_colorkey(colorkey)
        else:
            image = image.convert_alpha()
        return image
    except Exception:
        terminate()


all_sprites = pygame.sprite.Group()
tiles_group = pygame.sprite.Group()
player_group = pygame.sprite.Group()

tile_images: dict = {'box': load_image('box.png')}
player_image: pygame.Surface = load_image('mario.png')


# выход из программы
def terminate() -> None:
    """
    Выход из программы
    :return:
    """
    pygame.quit()
    sys.exit()


# игровой цикл стартового экрана
def start_screen() -> None:
    """
    Запускает игровой цикл для отрисовки стартового окна
    :return:
    """
    intro_text: list = [
        'Коробочки', '',
        'Правила игры:',
        'С неба сбрасывают коробки.',
        "Герой должен расставлять их в линию,",
        'чтобы не дать вырасти столбикам до неба.',
        'При попадании по персонажу коробкой теряются жизни'
    ]

    fon: pygame.Surface = pygame.transform.scale(
        load_image('background-start.png'), (
            constants.SCREEN_WIDTH,
            constants.SCREEN_HEIGHT
        )
    )
    screen.blit(fon, (0, 0))
    font = pygame.font.Font(None, 30)
    text_coord: int = 50
    for line in intro_text:
        string_rendered = font.render(line, True, pygame.Color('black'))
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
            elif event.type == pygame.KEYDOWN or \
                    event.type == pygame.MOUSEBUTTONDOWN:
                return  # начинаем игру
        pygame.display.flip()
        clock.tick(constants.FPS)


# класс главного героя
class Player(pygame.sprite.Sprite):
    """
    Класс отвечает за настройку и состояние главного героя.
        Атрибуты:
            :param: image: pygame.Surface
            :param: mask
            :param: rect: pygame.sprite.Sprite.rect
            :param: v: int
            :param: gravity: float
            :param: is_flip: bool
            :param: is_in_air: bool
            :param: jump: float
    """

    def __init__(self):
        super().__init__(player_group, all_sprites)
        self.image: pygame.Surface = player_image
        self.mask = self.image.get_masks()
        self.rect = self.image.get_rect().move(
            screen.get_rect().centerx - self.image.get_width() // 2,
            screen.get_rect().bottom - self.image.get_height() - 30
        )
        self.v: int = 1  # скорость
        self.gravity: float = constants.GRAVITY
        self.is_flip: bool = False
        self.is_in_air: bool = False  # статус прыжка
        self.jump: float = 1.5 * constants.tile_height

    def update(self, *args, **kwargs) -> None:
        """
        Обновляет состояние главного героя после действий пользователя
        :param args:
        :param kwargs:
        :return:
        """
        if args:
            pass
        if self.rect.colliderect(constants.screen_rect) and \
                not pygame.sprite.spritecollideany(self, tiles_group):
            self.v += self.gravity
            self.rect.y += self.v
        else:
            self.v = 1
            self.is_in_air = False


# класс тайлов коробочек
class Tile(pygame.sprite.Sprite):
    """
    Класс отвечает за настройку и состояние коробочек на поле
    :param: image: pygame.Surface
    :param: rect: pygame.sprite.Sprite.rect
    :param: col: int
    :param: v: int
    """

    def __init__(self, tile_type: str, pos_x: int):
        """
        :param tile_type: str
        :param pos_x: int
        """
        super().__init__(tiles_group, all_sprites)
        self.image: pygame.Surface = tile_images[tile_type]
        self.rect = self.image.get_rect().move(constants.tile_width * pos_x,
                                               screen.get_rect().top)
        self.col: int = pos_x
        self.v: int = 5

    def update(self, *args, **kwargs) -> None:
        """
        Обновляет состояние коробочки после действий пользователя
        :param args:
        :param kwargs:
        :return:
        """
        if self.rect.colliderect(constants.screen_rect) and len(
                pygame.sprite.spritecollide(self, tiles_group, False)) == 1:
            self.rect.y += self.v
        else:
            for row in range(constants.ROWS - 1, -1, -1):
                if self in game.board[row]:
                    return
                c, r = self.get_coords()
                if game.board[r][c] == 0:
                    self.rect.y = constants.tile_height * r + \
                                  constants.DOWN_BORDER + \
                                  (constants.ROWS - r) * 2
                    self.rect.x = constants.tile_width * c
                    game.board[r][c] = self
                break

    def get_coords(self) -> [int, int]:
        """
        Возвращает координаты тайла на игровом поле (в клетках: столбец, строка)
        :return: tuple[int, int]
        """
        return self.rect.x * constants.COLUMNS // constants.SCREEN_WIDTH, \
            self.rect.y * constants.ROWS // constants.SCREEN_HEIGHT


# класс игры
class Game:
    """
    Класс отвечающий за состояние игры.
        Атрибуты:
            Player: player
            list: board
        Методы:
            check_line - проверяет нет ли на поле полностью заполненных линий
            delete_row - проводит удаление строки со смещением всех объектов
            check_game_over - проверяет окончание игры
    """

    def __init__(self):
        self.player = Player()
        self.board: List[List[Union[int, Tile]]] = [[0] * constants.COLUMNS
                                                    for _ in
                                                    range(constants.ROWS)]

    def check_line(self, *args, **kwargs) -> None:
        """
        Если в строке все элементы заполнены, то строка удаляется
        :param args:
        :param kwargs:
        :return:
        """
        for i, row in enumerate(self.board):
            if all(row):
                self.delete_row(i)

    def check_game_over(self, *args, **kwargs) -> None:
        """
        Проверка состояния игры на окончание
        :param args:
        :param kwargs:
        :return:
        """
        pass

    def delete_row(self, row: int) -> None:
        """
        Принимает номер строки, которую нужно удалить.
            Перед удалением строки, все элементы удаляются из групп спрайтов
        :param row:int
        :return:
        """
        for i in range(constants.COLUMNS):
            self.board[row][i].kill()
            self.board[row][i] = 0
        del self.board[row]
        clock.tick(constants.FPS)
        new_board = [[0] * constants.COLUMNS]
        for r in range(constants.ROWS - 1):
            line = []
            for tile in self.board[r]:
                if tile:
                    tile.rect.y = constants.tile_height * r - \
                                  constants.DOWN_BORDER
                line.append(tile)
            new_board.append(line)
        self.board.clear()
        for r in new_board:
            self.board.append(r)

    def draw(self, keys: [bool] = None, *args, **kwargs) -> None:
        """
        Отрисовка игрового мира
        :parameter
        :param keys: Sequence [bool
        :param args:
        :param kwargs:
        :return:
        """
        fon = pygame.transform.scale(load_image('background.png'),
                                     (constants.SCREEN_WIDTH,
                                      constants.SCREEN_HEIGHT))
        screen.blit(fon, (0, 0))
        player_group.update(keys)
        tiles_group.draw(screen)
        player_group.draw(screen)
        all_sprites.update()
        self.check_line()
        self.check_game_over()


# начинаем игру стартовым экраном
start_screen()
# создаём игровое окружение
game = Game()
keys = pygame.key.get_pressed()
if __name__ == '__main__':
    while True:
        generation = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                terminate()
            if event.type == BOMBGENERATE:
                generation = True
            keys = pygame.key.get_pressed()
        if generation:
            col = randrange(constants.COLUMNS)
            while game.board[3][col]:
                game.check_game_over()
                col = randrange(constants.COLUMNS)
            Tile('box', col)
        game.draw(keys)
        pygame.display.flip()
        clock.tick(constants.FPS)

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
def load_image(name: str, color_key: int = None) -> pygame.Surface:
    """
    Принимает на входе имя файла и необязательны параметр наличия фона.
        Преобразует файл в объект pygame.image, и удаляет фоновый цвет
    :param name: str
    :param color_key: int
    :return image: pygame.Surface
    """
    fullname = os.path.join('data', name)
    try:
        image = pygame.image.load(fullname).convert()
    except pygame.error as message:
        print('Cannot load image:', name)
        raise SystemExit(message)

    if color_key is not None:
        if color_key == -1:
            color_key = image.get_at((0, 0))
        image.set_colorkey(color_key)
    else:
        image = image.convert_alpha()
    return image


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
            :param: rect: pygame.sprite.Sprite.rect
            :param: v: int
            :param: gravity: float
            :param: is_flip: bool
            :param: is_in_air: bool
            :param: jump: float
    """

    def __init__(self, sheet, columns, rows, x, y):
        super().__init__(player_group, all_sprites)
        self.frames = []
        self.cut_sheet(sheet, columns, rows)
        self.cur_frame = 0
        self.count_animate = 4
        self.image: pygame.Surface = self.frames[self.cur_frame]
        self.rect = self.rect.move(
            screen.get_rect().centerx - self.image.get_width() // 2,
            screen.get_rect().bottom - self.image.get_height() - constants.DOWN_BORDER)
        # self.rect = self.image.get_rect().move(
        #     screen.get_rect().centerx - self.image.get_width() // 2,
        #     screen.get_rect().bottom - self.image.get_height() - 30
        # )
        self.v: int = 1  # скорость
        self.gravity: float = constants.GRAVITY
        self.is_flip: bool = False
        self.is_in_air: bool = False  # статус прыжка
        self.jump: float = 1.5 * constants.tile_height

    def cut_sheet(self, sheet, columns, rows):
        self.rect = pygame.Rect(0, 0, sheet.get_width() // columns,
                                sheet.get_height() // rows)
        for j in range(rows):
            for i in range(columns):
                frame_location = (self.rect.w * i, self.rect.h * j)
                self.frames.append(
                    pygame.transform.scale(
                        sheet.subsurface(pygame.Rect(
                            frame_location, self.rect.size)
                        ),
                        (constants.tile_width, constants.tile_height)
                    )
                )

    def move(self, keys: [bool]) -> None:
        """
        Управляет перемещением героя по полю
        :param keys: [bool]
        :return:
        """
        if keys[pygame.K_LEFT]:
            if self.is_flip:
                self.image = pygame.transform.flip(self.image, True, False)
            if self.is_can_move_left():
                self.rect.x -= constants.STEP
        if keys[pygame.K_RIGHT]:
            if not self.is_flip:
                self.image = pygame.transform.flip(self.image, True, False)
            if self.is_can_move_right():
                self.rect.x += constants.STEP
        if keys[pygame.K_UP]:
            if self.is_can_jump():
                self.rect.y -= self.jump
                self.is_in_air = True

    def is_can_jump(self) -> bool:
        """
        Проверяет возможность прыгнуть вверх
        :return: bool
        """
        return self.rect.top - self.jump > 0 and not self.is_in_air

    def is_can_move_left(self) -> bool:
        """
        Проверяет возможность пойти налево
        :return: bool
        """
        return self.rect.left >= 0

    def is_can_move_right(self) -> bool:
        """
        Проверяет возможность пойти направо
        :return: bool
        """
        return self.rect.right < constants.SCREEN_WIDTH

    def update(self, *args, **kwargs) -> None:
        """
        Обновляет состояние главного героя после действий пользователя
        :param args:
        :param kwargs:
        :return:
        """
        self.cur_frame = (self.rect.x * constants.COLUMNS * 4 // constants.SCREEN_WIDTH) % len(self.frames)
        self.image = self.frames[self.cur_frame]
        self.rect.width = constants.tile_width
        self.rect.height = constants.tile_height
        if args:
            self.move(args[0])
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
        self.setup_collide()

    def move(self, keys: [bool]) -> None:
        hits = pygame.sprite.spritecollide(self, all_sprites, False)
        for obj in hits:
            if obj == self:
                continue
            # Проверка что есть объект справа
            if obj.rect.left < self.rect.right and \
                    obj.rect.left > self.rect.left and \
                    obj.rect.bottom - self.rect.top <= constants.tile_height + constants.ERROR_RATE and \
                    self.rect.bottom - obj.rect.top <= constants.tile_height + constants.ERROR_RATE:
                if isinstance(obj, Player):
                    self.is_hero_collide_right = True
                else:
                    self.is_collide_right = True
            # Проверка что есть объект слева
            if obj.rect.right > self.rect.left and \
                    obj.rect.left < self.rect.left and \
                    obj.rect.bottom - self.rect.top <= constants.tile_height + constants.ERROR_RATE and \
                    self.rect.bottom - obj.rect.top <= constants.tile_height + constants.ERROR_RATE:
                if isinstance(obj, Player):
                    self.is_hero_collide_left = True
                else:
                    self.is_collide_left = True

        if keys[pygame.K_LEFT] and self.is_can_move_left():
            self.rect.x -= constants.STEP

        if keys[pygame.K_RIGHT] and self.is_can_move_right():
            self.rect.x += constants.STEP

    def is_can_move_left(self) -> bool:
        is_can = (
                self.rect.x > 0 and
                not self.is_collide_left and
                not self.is_collide_top and
                self.is_hero_collide_right
        )
        return is_can

    def is_can_move_right(self) -> bool:
        is_can = (
                self.rect.right < constants.SCREEN_WIDTH and
                not self.is_collide_right and
                not self.is_collide_top and
                self.is_hero_collide_left
        )
        return is_can

    def setup_collide(self):
        self.is_collide_left: bool = False
        self.is_collide_right: bool = False
        self.is_collide_top: bool = False
        self.is_collide_bottom: bool = False
        self.is_hero_collide_right: bool = False
        self.is_hero_collide_left: bool = False
        self.is_hero_collide_top: bool = False
        self.is_hero_collide_bottom: bool = False

    def update(self, *args, **kwargs) -> None:
        """
        Обновляет состояние коробочки после действий пользователя
        :param args:
        :param kwargs:
        :return:
        """
        if args:
            self.move(args[0])
        if self.rect.colliderect(constants.screen_rect) and len(
                pygame.sprite.spritecollide(self, tiles_group, False)) == 1:
            self.rect.y += self.v
        else:
            for row in range(constants.ROWS - 1, -1, -1):
                if self in game.board[row]:
                    return
                c, r = self.get_coords()
                try:
                    if game.board[r][c] == 0:
                        game.board[r][c] = self
                    break
                except IndexError as e:
                    # При вылете за границы смотрим в чем проблема
                    print(e, (r, c), constants.ROWS, constants.COLUMNS)
        self.setup_collide()

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
        self.player = Player(load_image("dragon.png"), 8, 2, 50, 50)
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
                    # TODO: высота зависит от constant.screen_rect...
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
        # tiles_group.update(keys)
        # player_group.update(keys)
        tiles_group.draw(screen)
        player_group.draw(screen)
        all_sprites.update(keys)
        self.check_line()
        self.check_game_over()


# начинаем игру стартовым экраном
start_screen()
# создаём игровое окружение
game = Game()
keys = pygame.key.get_pressed()
# временный счетчик генерируемых коробок
count = 1
if __name__ == '__main__':
    while True:
        generation = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                terminate()
            if event.type == BOMBGENERATE:
                generation = True
            keys = pygame.key.get_pressed()
        if generation and count:
            col = randrange(constants.COLUMNS)
            while game.board[3][col]:
                game.check_game_over()
                col = randrange(constants.COLUMNS)
            Tile('box', 4)
            count -= 1
        game.draw(keys)
        pygame.display.flip()
        clock.tick(constants.FPS)

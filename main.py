import os
import sqlite3
import sys
from copy import copy
from random import randrange, choice
from typing import Union, List

import pygame
import pygame_gui

import constants
import inputbox

# инициализация констант
pygame.mixer.init()
main_theme = pygame.mixer.Sound(
    os.path.join(constants.MUSIC_PATH, "main_theme.ogg"))
jump_sound = pygame.mixer.Sound(
    os.path.join(constants.MUSIC_PATH, "jump.ogg"))
jump_sound.set_volume(0.1)
hit_sound = pygame.mixer.Sound(
    os.path.join(constants.MUSIC_PATH, "hit.ogg"))
hit_sound.set_volume(0.1)
line_sound = pygame.mixer.Sound(
    os.path.join(constants.MUSIC_PATH, "line.ogg"))
line_sound.set_volume(0.1)
gameover_sound = pygame.mixer.Sound(
    os.path.join(constants.MUSIC_PATH, "gameover.ogg"))
pygame.init()
clock = pygame.time.Clock()
screen: pygame.Surface = pygame.display.set_mode(constants.SIZE)

screen_game_over: pygame.Surface = pygame.display.set_mode(constants.SIZE)
pygame.key.set_repeat(200, 70)
BOMBGENERATE: pygame.event = pygame.USEREVENT + 1
CURRENT_BOMB_INTERVAL = constants.BOMBS_INTERVALS


# Генерация частиц
def create_particles(position: [int, int]) -> None:
    """
    Генератор частиц, срабатывает при попадании коробки в героя
    :param position: [int, int]
    :return:
    """
    particle_count = 20
    # возможные скорости
    numbers = range(-5, 6)
    for _ in range(particle_count):
        Particle(position, choice(numbers), choice(numbers))


# загрузка изображений
def load_image(name: str, color_key: int = None) -> pygame.Surface:
    """
    Принимает на входе имя файла и необязательны параметр наличия фона.
        Преобразует файл в объект pygame.image, и удаляет фоновый цвет
    :param name: str
    :param color_key: int
    :return image: pygame.Surface
    """
    fullname: str = os.path.join(constants.IMAGES_PATH, name)
    try:
        image = pygame.image.load(fullname).convert()
    except pygame.error as message:
        print('Cannot load image:', name)
        raise SystemExit(message)
    except FileNotFoundError as message:
        print('Cannot found file:', name)
        raise SystemExit(message)

    if color_key is not None:
        if color_key == -1:
            color_key = image.get_at((0, 0))
        image.set_colorkey(color_key)
    else:
        image = image.convert_alpha()
    return image


all_sprites = pygame.sprite.Group()
gameover_group = pygame.sprite.Group()
game_status = pygame.sprite.Group()
tiles_group = pygame.sprite.Group()
player_group = pygame.sprite.Group()

tile_images: dict = {'box': load_image('box.png')}
color_box = [
    'box-black.png',
    'box-blue.png',
    'box-cyan.png',
    'box-green.png',
    'box-pink.png',
    'box-red.png',
    'box-yellow.png'
]


# выход из программы
def terminate() -> None:
    """
    Выход из программы
    :return:
    """
    pygame.quit()
    sys.exit()


# класс игры
class Game:
    """
    Класс отвечающий за состояние игры.
        Атрибуты:
            :param: player: Player
            :param: board: List[List[Union[int, Tile]]]
            :param: game_over_screen: GameOver
            :param: health_status: List[StatusHearts]
            :param: is_paused: bool
        Методы:
            check_line - проверяет нет ли на поле полностью заполненных линий
            delete_row - проводит удаление строки со смещением всех объектов
            check_game_over - проверяет окончание игры
    """

    def __init__(self):
        self.player: Player = Player(load_image("dragon.png"), 8, 2, 50, 50)
        self.board: List[List[Union[int, Tile]]] = [[0] * constants.COLUMNS
                                                    for _ in
                                                    range(constants.ROWS)]
        self.health_status: List[StatusHearts] = [StatusHearts() for _ in
                                                  range(self.player.health)]
        self.score_status: StatusScore = StatusScore()
        self.score_level: StatusLevel = StatusLevel()
        self.score: int = 0
        self.level: int = 0
        for i, obj in enumerate(self.health_status):
            obj.rect.x = obj.rect.width * i * 0.5
            obj.rect.y = 10
        self.is_game_over: bool = False
        self.is_paused: bool = False
        self.is_start_screen: bool = True
        self.difficult_id = None
        self.con = sqlite3.connect(constants.DB_NAME)

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
        line_sound.play()
        del self.board[row]
        self.score += constants.COLUMNS
        if self.score % constants.LINE_PER_LEVEL == 0:
            self.level += 1
            Tile.increase_speed()
        new_board = []
        for r in range(constants.ROWS - 1):
            line = []
            for tile in self.board[r]:
                if tile:
                    tile.rect.y = constants.tile_height * r - constants.DOWN_BORDER
                line.append(tile)
            new_board.append(line)
        # добавляем пустую верхнюю строку
        new_board.append([0] * constants.COLUMNS)
        self.board.clear()
        for r in new_board:
            self.board.append(r)

    def check_game_over(self, *args, **kwargs) -> None:
        """
        Проверка состояния игры на окончание
        :param args:
        :param kwargs:
        :return:
        """
        self.is_game_over = any(self.board[1]) or not self.player.health

    def set_difficult(self, difficult_name):
        difficult_name = difficult_name or constants.DEFAULT_DIFFICULT
        cur = self.con.cursor()
        difficult_line = cur.execute(
            'SELECT * '
            'FROM difficult '
            f'WHERE difficult_name="{difficult_name}" '
        ).fetchone()
        self.difficult_id, _, start_v, interval =  difficult_line
        constants.START_V = start_v
        constants.BOMBS_INTERVALS = int(interval)
        global CURRENT_BOMB_INTERVAL
        CURRENT_BOMB_INTERVAL = constants.BOMBS_INTERVALS
        pygame.time.set_timer(BOMBGENERATE, 0)
        Tile.reset_v()

    # игровой цикл стартового экрана
    def start_screen(self) -> None:
        """
        Запускает игровой цикл для отрисовки стартового окна
        :return:
        """
        manager: pygame_gui.UIManager = pygame_gui.UIManager(constants.SIZE)
        item_list = [difficult_name[0] for difficult_name in
                     self.con.cursor().execute(
                         'SELECT difficult_name '
                         'FROM difficult '
                         'ORDER BY id ASC'
                     ).fetchall()]
        difficult_state = pygame_gui.elements.ui_selection_list.UISelectionList(
            relative_rect=pygame.Rect(
                (constants.SCREEN_WIDTH // 4 - 50,
                 1.5 * constants.SCREEN_HEIGHT // 4 + 5),
                (100, 108)
            ),
            item_list=item_list,
            manager=manager
        )
        start_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                (constants.SCREEN_WIDTH // 4 - 50,
                 2.5 * constants.SCREEN_HEIGHT // 4),
                (100, 50)
            ),
            text='Start',
            manager=manager
        )
        results_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                (constants.SCREEN_WIDTH // 4 - 50,
                 3 * constants.SCREEN_HEIGHT // 4),
                (100, 50)
            ),
            text='Results',
            manager=manager
        )
        exit_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                (constants.SCREEN_WIDTH // 4 - 50,
                 3.5 * constants.SCREEN_HEIGHT // 4),
                (100, 50)
            ),
            text='Quit',
            manager=manager
        )
        intro_text: list = [
            'Правила игры:',
            'С неба сбрасывают коробки. Герой должен расставлять',
            'их в линию, чтобы не дать вырасти столбикам до неба.',
            'При попадании по персонажу коробкой теряются жизни',
            '','',
            '      Уровень сложности:'
        ]

        fon: pygame.Surface = pygame.transform.scale(
            load_image('background-start.jpg'), (
                constants.SCREEN_WIDTH,
                constants.SCREEN_HEIGHT
            )
        )

        while True:
            screen.blit(fon, (0, 0))
            font = pygame.font.Font(None, 35)
            string_rendered = font.render('Коробочки', True, pygame.Color('white'))
            intro_rect = string_rendered.get_rect()
            intro_rect.centerx = constants.SCREEN_WIDTH // 2
            intro_rect.y = 10
            screen.blit(string_rendered, intro_rect)
            font = pygame.font.Font(None, 25)
            text_coord: int = 30
            for line in intro_text:
                string_rendered = font.render(line, True, pygame.Color('white'))
                intro_rect = string_rendered.get_rect()
                text_coord += 5
                intro_rect.top = text_coord
                intro_rect.x = 10
                text_coord += intro_rect.height
                screen.blit(string_rendered, intro_rect)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    terminate()
                if event.type == pygame.USEREVENT:
                    if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                        if event.ui_element == start_button:
                            self.set_difficult(difficult_state.get_single_selection())
                            main_theme.play(loops=-1)
                            main_theme.set_volume(0.1)
                            self.is_start_screen = False
                            return
                        if event.ui_element == results_button:
                            self.result_screen()
                        if event.ui_element == exit_button:
                            terminate()
                manager.process_events(event)
            manager.update(constants.FPS)
            manager.draw_ui(screen)
            pygame.display.flip()
            clock.tick(constants.FPS)

    # игровой цикл экрана паузы
    def pause_screen(self) -> None:
        """
        Запускает игровой цикл для отрисовки стартового окна
        :return:
        """
        manager: pygame_gui.UIManager = pygame_gui.UIManager(constants.SIZE)
        restart_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                (constants.SCREEN_WIDTH // 4 - 50,
                 2.5 * constants.SCREEN_HEIGHT // 4),
                (100, 50)
            ),
            text='Restart',
            manager=manager
        )
        resume_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                (constants.SCREEN_WIDTH // 4 - 50,
                 3 * constants.SCREEN_HEIGHT // 4),
                (100, 50)
            ),
            text='Resume',
            manager=manager
        )
        exit_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                (constants.SCREEN_WIDTH // 4 - 50,
                 3.5 * constants.SCREEN_HEIGHT // 4),
                (100, 50)
            ),
            text='Quit',
            manager=manager
        )
        intro_text: list = [
            'Пауза', '',
            f'Score: {self.score}',
            f'Осталось жизней: {len(self.health_status)}',
        ]

        fon: pygame.Surface = pygame.transform.scale(
            load_image('background-start.jpg'), (
                constants.SCREEN_WIDTH,
                constants.SCREEN_HEIGHT
            )
        )
        screen.blit(fon, (0, 0))
        font = pygame.font.Font(None, 35)
        text_coord: int = 50
        for line in intro_text:
            string_rendered = font.render(line, True, pygame.Color('white'))
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
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.is_paused = False
                        return
                if event.type == pygame.USEREVENT:
                    if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                        if event.ui_element == restart_button:
                            self.reset_game()
                            return
                        if event.ui_element == resume_button:
                            self.is_paused = False
                            return
                        if event.ui_element == exit_button:
                            terminate()
                manager.process_events(event)
            manager.update(constants.FPS)
            manager.draw_ui(screen)
            pygame.display.flip()
            clock.tick(constants.FPS)

    # игровой цикл экрана конца игры
    def game_over_screen(self) -> None:
        """
        Запускает игровой цикл для отрисовки стартового окна
        :return:
        """
        manager: pygame_gui.UIManager = pygame_gui.UIManager(constants.SIZE)

        fon: pygame.Surface = pygame.transform.scale(
            load_image('gameover.png'), (
                constants.SCREEN_WIDTH,
                load_image('gameover.png').get_height()
            )
        )
        x = -fon.get_width()
        y = constants.SCREEN_HEIGHT // 2 - fon.get_height() // 2
        screen.blit(fon, (x, y))
        speed = 5
        restart_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                (constants.SCREEN_WIDTH // 4 - 50,
                 y + fon.get_height()),
                (100, 50)
            ),
            text='Restart',
            manager=manager
        )
        results_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                (constants.SCREEN_WIDTH // 2 - 50,
                 y + fon.get_height()),
                (100, 50)
            ),
            text='Results',
            manager=manager
        )
        exit_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                (3 * constants.SCREEN_WIDTH // 4 - 50,
                 y + fon.get_height()),
                (100, 50)
            ),
            text='Quit',
            manager=manager
        )
        name = None
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    terminate()
                if event.type == pygame.USEREVENT:
                    if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                        if event.ui_element == restart_button:
                            self.reset_game()
                            return
                        if event.ui_element == results_button:
                            self.result_screen()
                            screen.fill('black')
                            screen.blit(fon, (x, y))
                        if event.ui_element == exit_button:
                            terminate()
                manager.process_events(event)
            if x + fon.get_width() >= constants.SCREEN_WIDTH:
                speed = 0
                if not name:
                    name = inputbox.ask(screen, 'Your name')
                    if not name:
                        continue
                    total = self.score * self.difficult_id
                    cur = self.con.cursor()
                    cur.execute(
                        'INSERT INTO records(name, score, level, difficult_id, total) '
                        'VALUES(?, ?, ?, ?, ?)', (name, self.score, self.level, self.difficult_id, total)
                    )
                    self.con.commit()
                manager.update(constants.FPS)
                manager.draw_ui(screen)
            x += speed
            screen.blit(fon, (x, y))
            pygame.display.flip()
            clock.tick(constants.FPS)

    # игровой цикл стартового экрана
    def result_screen(self) -> None:
        """
        Запускает игровой цикл для отрисовки стартового окна
        :return:
        """
        screen_result = pygame.display.set_mode(constants.SIZE)
        manager: pygame_gui.UIManager = pygame_gui.UIManager(constants.SIZE)
        item_list = ['Name    Score    Level    Difficult    Total']
        item_list += [''.join([str(x).ljust(13, ' ') for x in difficult_name[1:]]) for difficult_name in
                     self.con.cursor().execute(
                         'SELECT * '
                         'FROM records '
                         'ORDER BY total DESC '
                         'LIMIT 7'
                     ).fetchall()]
        back_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                (constants.SCREEN_WIDTH // 4 - 50,
                 2.5 * constants.SCREEN_HEIGHT // 4),
                (100, 50)
            ),
            text='Back',
            manager=manager
        )
        exit_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                (constants.SCREEN_WIDTH // 4 - 50,
                 3 * constants.SCREEN_HEIGHT // 4),
                (100, 50)
            ),
            text='Quit',
            manager=manager
        )
        fon: pygame.Surface = pygame.transform.scale(
            load_image('results.jpg'), (
                constants.SCREEN_WIDTH,
                constants.SCREEN_HEIGHT
            )
        )
        screen_result.blit(fon, (0, 0))
        font = pygame.font.Font(None, 25)
        text_coord: int = 100
        for line in item_list:
            string_rendered = font.render(line, True, pygame.Color('white'))
            intro_rect = string_rendered.get_rect()
            text_coord += 5
            intro_rect.top = text_coord
            intro_rect.x = 100
            text_coord += intro_rect.height
            screen_result.blit(string_rendered, intro_rect)
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    terminate()
                if event.type == pygame.USEREVENT:
                    if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                        if event.ui_element == back_button:
                            return
                        if event.ui_element == exit_button:
                            screen_result.quit()
                            terminate()
                manager.process_events(event)
            manager.update(constants.FPS)
            manager.draw_ui(screen)
            pygame.display.flip()
            clock.tick(constants.FPS)

    def reset_game(self):
        main_theme.stop()
        self.player.kill()
        self.board: List[List[Union[int, Tile]]] = [[0] * constants.COLUMNS
                                                    for _ in
                                                    range(constants.ROWS)]
        for obj in self.health_status:
            obj.kill()
        self.score_status.kill()
        self.score_level.kill()
        self.score: int = 0
        self.level: int = 0
        for i, obj in enumerate(self.health_status):
            obj.rect.x = obj.rect.width * i * 0.5
            obj.rect.y = 10
        for obj in tiles_group:
            obj.kill()
        Tile.reset_v()
        self.__init__()

    def update(self, keys: [bool] = None, *args, **kwargs) -> None:
        """
        Отрисовка игрового мира
        :parameter
        :param keys: Sequence [bool
        :param args:
        :param kwargs:
        :return:
        """
        self.check_game_over()
        if self.is_game_over:
            main_theme.stop()
            gameover_sound.play()
            self.game_over_screen()
            return
        if self.is_start_screen:
            self.start_screen()
            return
        if self.is_paused:
            self.pause_screen()
            return
        fon = pygame.transform.scale(load_image('background.png'),
                                     (constants.SCREEN_WIDTH,
                                      constants.SCREEN_HEIGHT))
        screen.blit(fon, (0, 0))
        tiles_group.draw(screen)
        player_group.draw(screen)
        game_status.draw(screen)
        if not self.is_paused:
            game_status.update()
            all_sprites.update(keys)
        self.check_line()


# класс главного героя
class Player(pygame.sprite.Sprite):
    """
    Класс отвечает за настройку и состояние главного героя.
        Атрибуты:
            :param: count_animate: int
            :param: cur_frame: int
            :param: frames: list[pygame.Surface]
            :param: image: pygame.Surface
            :param: rect: pygame.sprite.Sprite.rect
            :param: v: int
            :param: gravity: float
            :param: is_flip: bool
            :param: is_in_air: bool
            :param: jump: float
            :param: col: int
            :param: row: int
            :param: is_in_air: bool
            :param: health: int
    """

    def __init__(self, sheet, columns, rows, x, y):
        super().__init__(player_group, all_sprites)
        self.frames = []
        self.cut_sheet(sheet, columns, rows)
        self.cur_frame: int = 0
        self.count_animate: int = 4  # количество циклов повторений анимации на экран
        self.image: pygame.Surface = self.frames[self.cur_frame]
        self.rect = self.rect.move(
            screen.get_rect().centerx - self.image.get_width() // 2,
            screen.get_rect().bottom - self.image.get_height() - constants.DOWN_BORDER)
        self.v: int = 1  # скорость
        self.gravity: float = constants.GRAVITY
        self.is_flip: bool = False
        self.is_in_air: bool = False  # статус прыжка
        self.jump: float = 1.5 * constants.tile_height
        self.col, self.row = self.get_coords()
        self.health: int = 10

    def cut_sheet(self, sheet, columns, rows):
        self.rect = pygame.Rect(0, 0, sheet.get_width() // columns,
                                sheet.get_height() // rows)
        for j in range(rows):
            for i in range(columns):
                frame_location = (self.rect.w * i, self.rect.h * j)
                frame = pygame.transform.scale(
                    sheet.subsurface(pygame.Rect(
                        frame_location, self.rect.size)
                    ),
                    (constants.tile_width, constants.tile_height)
                )
                self.frames.append(frame)

    def get_coords(self) -> [int, int]:
        """
        Возвращает координаты тайла на игровом поле (в клетках: столбец, строка)
        :return: tuple[int, int]
        """
        return self.rect.x * constants.COLUMNS // constants.SCREEN_WIDTH, \
               self.rect.y * constants.ROWS // constants.SCREEN_HEIGHT

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
        return self.col >= 0 and self.rect.left >= 0 and not \
            game.board[self.row][self.col]

    def is_can_move_right(self) -> bool:
        """
        Проверяет возможность пойти направо
        :return: bool
        """
        right_col = (self.rect.centerx + self.rect.width // 4) * \
                    constants.COLUMNS // constants.SCREEN_WIDTH
        return (self.col + 1 < constants.COLUMNS and
                self.rect.right < constants.SCREEN_WIDTH and
                not game.board[self.row][right_col])

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
                jump_sound.play()
                self.rect.y -= self.jump
                self.is_in_air = True

    def update(self, *args, **kwargs) -> None:
        """
        Обновляет состояние главного героя после действий пользователя
        :param args:
        :param kwargs:
        :return:
        """
        self.cur_frame = (self.rect.x * constants.COLUMNS * 4 //
                          constants.SCREEN_WIDTH) % len(self.frames)
        self.image = self.frames[self.cur_frame]
        self.mask = pygame.mask.from_surface(self.image)
        self.rect.width = constants.tile_width
        self.rect.height = constants.tile_height + self.v
        self.col, self.row = self.get_coords()
        if args:
            self.move(args[0])
        if self.rect.colliderect(constants.screen_rect) and \
                not any([pygame.sprite.collide_mask(self, tile) for tile in
                         tiles_group]):
            self.v += self.gravity
            self.rect.y += self.v
        else:
            self.v = 1
            self.is_in_air = False


class StatusHearts(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__(game_status)
        self.image = load_image("heart.png", color_key=-1)
        self.image = pygame.transform.scale(self.image, (self.image.get_width(),
                                                         self.image.get_height()))
        self.rect = self.image.get_rect()


class StatusScore(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__(game_status)
        self.font = pygame.font.Font(None, 30)
        self.image = self.font.render('Score: ', True, pygame.Color('white'))
        self.rect = self.image.get_rect()
        self.rect.right = constants.SCREEN_WIDTH - self.rect.width
        self.rect.top = 25

    def update(self, *args, **kwargs) -> None:
        self.image = self.font.render(f'Score: {game.score}', True,
                                      pygame.Color('white'))
        self.rect.right = constants.SCREEN_WIDTH - self.rect.width


class StatusLevel(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__(game_status)
        self.font = pygame.font.Font(None, 30)
        self.image = self.font.render('Level: ', True, pygame.Color('white'))
        self.rect = self.image.get_rect()
        self.rect.right = constants.SCREEN_WIDTH - 3 * self.rect.width
        self.rect.top = 25

    def update(self, *args, **kwargs) -> None:
        self.image = self.font.render(f'Level: {game.level}', True,
                                      pygame.Color('white'))
        self.rect.right = constants.SCREEN_WIDTH - 3 * self.rect.width


# создаём игровое окружение
game = Game()


# класс тайлов коробочек
class Tile(pygame.sprite.Sprite):
    """
    Класс отвечает за настройку и состояние коробочек на поле
    :param: image: pygame.Surface
    :param: rect: pygame.sprite.Sprite.rect
    :param: col: int
    :param: v: int
    :param: can_move_left: bool
    :param: can_move_right: bool
    :param: sprite_copy: pygame.sprite.Sprite
    """

    v: int = constants.START_V

    def __init__(self, tile_type: str, pos_x: int):
        """
        :param tile_type: str
        :param pos_x: int
        """
        super().__init__(tiles_group, all_sprites)
        self.image: pygame.Surface = load_image(tile_type)
        self.rect = self.image.get_rect().move(constants.tile_width * pos_x,
                                               screen.get_rect().top)
        self.col: int = pos_x
        self.row: int = 0
        self.setup_collide()
        self.can_move_left: bool = True
        self.can_move_right: bool = True
        # копия объекта с увеличенной координатой y, для коррекции пересечений
        # на разных скоростях с нижними объектами
        self.sprite_copy: pygame.sprite.Sprite = copy(self)
        self.sprite_copy.rect.height += self.v
        self.mask = pygame.mask.from_surface(self.image)
        self.is_collide_left: bool = False
        self.is_collide_right: bool = False
        self.is_collide_top: bool = False
        self.is_collide_bottom: bool = False
        self.is_hero_collide_right: bool = False
        self.is_hero_collide_left: bool = False
        self.is_hero_collide_top: bool = False
        self.is_hero_collide_bottom: bool = False
        self.is_in_air = True

    def get_coords(self) -> [int, int]:
        """
        Возвращает координаты тайла на игровом поле (в клетках: столбец, строка)
        :return: tuple[int, int]
        """
        return self.rect.x * constants.COLUMNS // constants.SCREEN_WIDTH, \
               self.rect.y * constants.ROWS // constants.SCREEN_HEIGHT

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

    def move(self, keys: [bool]) -> None:
        """
        Управляет перемещением коробок по полю
        :param keys: [bool]
        :return:
        """
        hits: list = pygame.sprite.spritecollide(self, all_sprites, False)
        for obj in hits:
            if obj == self:
                continue
            # Проверка что есть объект справа
            if self.rect.right > obj.rect.left > self.rect.left and \
                    obj.rect.bottom - self.rect.top <= (constants.tile_height +
                                                        constants.ERROR_RATE) and \
                    self.rect.bottom - obj.rect.top <= (constants.tile_height +
                                                        constants.ERROR_RATE):
                if isinstance(obj, Player):
                    self.is_hero_collide_right = True
                else:
                    self.is_collide_right = True
            # Проверка что есть объект слева
            if obj.rect.right > self.rect.left > obj.rect.left and \
                    obj.rect.bottom - self.rect.top <= (constants.tile_height +
                                                        constants.ERROR_RATE) and \
                    self.rect.bottom - obj.rect.top <= (constants.tile_height +
                                                        constants.ERROR_RATE):
                if isinstance(obj, Player):
                    self.is_hero_collide_left = True
                else:
                    self.is_collide_left = True
            # Проверка что есть объект сверху
            if obj.rect.right > self.rect.left and \
                    obj.rect.left < self.rect.right and \
                    obj.rect.bottom <= (self.rect.top +
                                        constants.ERROR_RATE) and \
                    obj.rect.top <= (self.rect.bottom +
                                     constants.ERROR_RATE):
                if isinstance(obj, Player):
                    self.is_hero_collide_top = True
                else:
                    self.is_collide_top = True
            # Проверка что есть объект снизу
            if obj.rect.right > self.rect.left and \
                    obj.rect.left < self.rect.right and \
                    obj.rect.bottom >= (self.rect.top +
                                        constants.ERROR_RATE) and \
                    obj.rect.top <= (self.rect.bottom +
                                     constants.ERROR_RATE):
                if not isinstance(obj, Player):
                    self.is_collide_bottom = True

            # проверяем что не упали на героя
            if obj.rect.right > self.rect.left and \
                    obj.rect.left < self.rect.right and \
                    obj.rect.top < (self.rect.bottom +
                                    constants.ERROR_RATE) and \
                    constants.tile_height < obj.rect.top - self.rect.top <= (
                    constants.tile_height +
                    constants.ERROR_RATE):
                self.is_hero_collide_bottom = True
            self.can_move_left = self.is_can_move_left()
            self.can_move_right = self.is_can_move_right()

        if keys[pygame.K_LEFT] and self.can_move_left:
            self.rect.x -= constants.tile_width

        if keys[pygame.K_RIGHT] and self.can_move_right:
            self.rect.x += constants.tile_width

    @classmethod
    def reset_v(cls):
        global CURRENT_BOMB_INTERVAL
        cls.v = constants.START_V
        CURRENT_BOMB_INTERVAL = constants.BOMBS_INTERVALS
        pygame.time.set_timer(BOMBGENERATE, CURRENT_BOMB_INTERVAL)

    @classmethod
    def increase_speed(cls):
        global CURRENT_BOMB_INTERVAL
        cls.v += 1
        CURRENT_BOMB_INTERVAL -= constants.INSTERVALS_PITCH
        pygame.time.set_timer(BOMBGENERATE, CURRENT_BOMB_INTERVAL)
        for tile in tiles_group:
            tile.image = load_image(color_box[game.level % len(color_box)])

    def setup_collide(self):
        self.is_collide_left: bool = False
        self.is_collide_right: bool = False
        self.is_collide_top: bool = False
        self.is_collide_bottom: bool = False
        self.is_hero_collide_right: bool = False
        self.is_hero_collide_left: bool = False
        self.is_hero_collide_top: bool = False
        self.is_hero_collide_bottom: bool = False
        self.is_in_air = True

    def update(self, *args, **kwargs) -> None:
        """
        Обновляет состояние коробочки после действий пользователя
        :param args:
        :param kwargs:
        :return:
        """
        self.can_move_left = self.is_can_move_left()
        self.can_move_right = self.is_can_move_right()
        if args:
            self.move(args[0])
        # Проверка что не упали на героя
        if (self.is_hero_collide_bottom and
                not self.is_hero_collide_left and
                not self.is_hero_collide_right and
                not self.is_hero_collide_top and
                len(pygame.sprite.spritecollide(self, tiles_group, False)) == 1
        ):
            game.player.health -= 1
            hit_sound.play()
            if game.board[self.row][self.col]:
                game.board[self.row][self.col] = 0
            self.kill()
            create_particles((self.rect.centerx, self.rect.top))
            game.health_status.pop().kill()
        if self.sprite_copy.rect.colliderect(
                constants.screen_rect) and not self.is_collide_bottom:
            self.rect.y += self.v
        else:
            new_col, new_row = self.get_coords()
            try:
                if game.board[new_row][new_col] == 0:
                    game.board[new_row][new_col], game.board[self.row][
                        self.col] = self, 0
                    self.col, self.row = new_col, new_row
                    self.rect.y = constants.tile_height * (
                            self.row + 1) - constants.DOWN_BORDER
            except IndexError as e:
                # При вылете за границы смотрим в чем проблема
                print(e, (new_row, new_col), constants.ROWS, constants.COLUMNS)
        self.rect.x = constants.tile_width * self.col
        self.setup_collide()


class Particle(pygame.sprite.Sprite):
    fire = [choice(game.player.frames)]
    for scale in (5, 10, 20, 30):
        fire.append(pygame.transform.scale(fire[0], (scale, scale)))

    def __init__(self, pos, dx, dy):
        super().__init__(all_sprites, player_group)
        self.image = choice(self.fire)
        self.rect = self.image.get_rect()
        self.velocity = [dx, dy]
        self.rect.x, self.rect.y = pos
        self.gravity = constants.GRAVITY

    def update(self, *args, **kwargs):
        self.velocity[1] += self.gravity
        self.rect.x += self.velocity[0]
        self.rect.y += self.velocity[1]
        if not self.rect.colliderect(constants.screen_rect):
            self.kill()


keys = pygame.key.get_pressed()
is_paused = False
if __name__ == '__main__':
    while True:
        generation = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                terminate()
            if event.type == BOMBGENERATE and not is_paused:
                generation = True
            keys = pygame.key.get_pressed()
            if keys[pygame.K_ESCAPE]:
                game.is_paused = not game.is_paused
        if generation:
            col = randrange(1, constants.COLUMNS - 1)
            Tile(color_box[game.level % len(color_box)], col)
        game.update(keys)
        pygame.display.flip()
        clock.tick(constants.FPS)

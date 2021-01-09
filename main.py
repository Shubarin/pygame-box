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

# Загрузка и настройка звуковых эффектов
sound_main_theme: pygame.mixer.Sound = pygame.mixer.Sound(
    os.path.join(constants.MUSIC_PATH, "main_theme.ogg"))

sound_jump: pygame.mixer.Sound = pygame.mixer.Sound(
    os.path.join(constants.MUSIC_PATH, "jump.ogg"))
sound_jump.set_volume(0.1)

sound_hit: pygame.mixer.Sound = pygame.mixer.Sound(
    os.path.join(constants.MUSIC_PATH, "hit.ogg"))
sound_hit.set_volume(0.1)

sound_line: pygame.mixer.Sound = pygame.mixer.Sound(
    os.path.join(constants.MUSIC_PATH, "line.ogg"))
sound_line.set_volume(0.1)

sound_gameover: pygame.mixer.Sound = pygame.mixer.Sound(
    os.path.join(constants.MUSIC_PATH, "gameover.ogg"))

# Настройка игровых параметров
pygame.init()
clock: pygame.time.Clock = pygame.time.Clock()
screen: pygame.Surface = pygame.display.set_mode(constants.SIZE)

screen_game_over: pygame.Surface = pygame.display.set_mode(constants.SIZE)
BOMBGENERATE: pygame.event = pygame.USEREVENT + 1
# интервал будет уменьшаться с ростом скорости и уровня
CURRENT_BOMB_INTERVAL = constants.BOMBS_INTERVALS
pygame.key.set_repeat(200, 70)


# Генерация частиц
def create_particles(position: [int, int]) -> None:
    """
    Генератор частиц, срабатывает при попадании коробки в героя
    :param position: [int, int]
    :return None:
    """
    particle_count = 5
    # возможные скорости
    numbers = range(-1, 3)
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
cursor_group = pygame.sprite.Group()

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
    :return None:
    """
    pygame.quit()
    sys.exit()


# класс игры
class Game:
    """
    Класс отвечающий за состояние игры.
        Свойства:
    player: Player
    board: List[List[Union[int, Tile]]]
    game_over_screen: GameOver
    status_health: List[StatusHearts]
    is_game_over: bool
    is_paused: bool
        Методы:
    check_line - проверяет нет ли на поле полностью заполненных линий
    check_game_over - проверяет окончание игры
    delete_row - проводит удаление строки со смещением всех объектов
    reset_game - cбрасывает игру на начальные настройки перед рестартом
    set_difficult - Настраивает игровой процесс
                    в соответствии с уровнем сложности
    screen_game_over - игровой цикл экрана конца игры
    screen_pause - игровой цикл экрана паузы
    screen_result - игровой цикл экрана результатов
    screen_start - игровой цикл стартового экрана
    update - метод для обновления состояния игры
    """

    def __init__(self):
        self.board: List[List[Union[int, Tile]]] = [[0] * constants.COLUMNS
                                                    for _ in
                                                    range(constants.ROWS)]
        self.con: sqlite3.connect = sqlite3.connect(constants.DB_NAME)
        self.difficult_id = None
        self.level: int = 0
        self.is_game_over: bool = False
        self.is_paused: bool = False
        self.is_start_screen: bool = True
        self.player: Player = Player(load_image("dragon.png"), 8, 2)
        self.score: int = 0
        self.status_health: List[StatusHearts] = [StatusHearts() for _ in
                                                  range(self.player.health)]
        self.status_score: StatusScore = StatusScore()
        self.status_level: StatusLevel = StatusLevel()
        # размещаем жизни на экране
        for i, obj in enumerate(self.status_health):
            obj.rect.x = obj.rect.width * i * 0.5
            obj.rect.y = 10

    def check_game_over(self) -> None:
        """
        Проверка состояния игры на окончание
        :return None:
        """
        self.is_game_over = any(self.board[1]) or not self.player.health

    def check_line(self) -> None:
        """
        Если в строке все элементы заполнены, то строка удаляется
        :return None:
        """
        for i, row in enumerate(self.board):
            if all(row):
                self.delete_row(i)

    def delete_row(self, row: int) -> None:
        """
        Принимает номер строки, которую нужно удалить.
            Перед удалением строки, все элементы удаляются из групп спрайтов
        :param row:int
        :return None:
        """
        # очищаем строку, удаляем спрайты
        for i in range(constants.COLUMNS):
            self.board[row][i].kill()
            self.board[row][i] = 0

        sound_line.play()

        # удаляем нужную строку
        del self.board[row]

        # увеличиваем счетчик очков и уровень (при необходимости)
        self.score += constants.COLUMNS
        if self.score % constants.LINE_PER_LEVEL == 0:
            self.level += 1
            Tile.increase_speed()

        # создаем новое игровое поле после удаления строки
        new_board = []
        for r in range(constants.ROWS - 1):
            line = []
            for tile in self.board[r]:
                if tile:
                    # смещаем спрайт на нужное расстояние
                    tile.rect.y = constants.tile_height * r - \
                                  constants.DOWN_BORDER
                line.append(tile)
            new_board.append(line)
        # добавляем пустую верхнюю строку
        new_board.append([0] * constants.COLUMNS)
        self.board.clear()
        for r in new_board:
            self.board.append(r)

    def reset_game(self) -> None:
        """
        Сбрасывает игру на начальные настройки перед рестартом
        :return None:
        """
        sound_main_theme.stop()
        self.player.kill()
        self.board: List[List[Union[int, Tile]]] = [[0] * constants.COLUMNS
                                                    for _ in
                                                    range(constants.ROWS)]
        for obj in self.status_health:
            obj.kill()
        self.status_score.kill()
        self.status_level.kill()
        self.score: int = 0
        self.level: int = 0
        for i, obj in enumerate(self.status_health):
            obj.rect.x = obj.rect.width * i * 0.5
            obj.rect.y = 10
        for obj in tiles_group:
            obj.kill()
        Tile.reset_v()
        self.__init__()

    def set_difficult(self, difficult_name) -> None:
        """
        Настраивает игровой процесс в соответствии с уровнем сложности
        :param difficult_name: str
        :return None:
        """
        difficult_name = difficult_name or constants.DEFAULT_DIFFICULT
        cur = self.con.cursor()
        difficult_line = cur.execute(
            'SELECT * '
            'FROM difficult '
            f'WHERE difficult_name="{difficult_name}" '
        ).fetchone()
        self.difficult_id, _, start_v, interval = difficult_line
        constants.START_V = start_v
        constants.BOMBS_INTERVALS = int(interval)
        global CURRENT_BOMB_INTERVAL
        CURRENT_BOMB_INTERVAL = constants.BOMBS_INTERVALS
        pygame.time.set_timer(BOMBGENERATE, 0)
        Tile.reset_v()

    # игровой цикл экрана конца игры
    def screen_game_over(self) -> None:
        """
        Запускает игровой цикл для отрисовки окна проигрыша
        :return None:
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
                if event.type == pygame.MOUSEMOTION:
                    x_, y_ = event.pos
                    cursor.rect.x = x_
                    cursor.rect.y = y_
                if event.type == pygame.USEREVENT:
                    if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                        if event.ui_element == restart_button:
                            self.reset_game()
                            return
                        if event.ui_element == results_button:
                            self.screen_result()
                            screen.blit(fon, (x, y))
                        if event.ui_element == exit_button:
                            terminate()
                manager.process_events(event)
            if x + fon.get_width() >= constants.SCREEN_WIDTH:
                speed = 0
                total = self.score * self.difficult_id
                minimum_cur = self.con.cursor()
                current_minimum_top = minimum_cur.execute(
                    'SELECT MIN(total) '
                    'FROM records '
                    'ORDER BY total '
                    'LIMIT 7'
                ).fetchone()[0]
                if not name and total > current_minimum_top:
                    name = inputbox.ask(screen, 'Your name')
                    if not name:
                        continue
                    cur = self.con.cursor()
                    cur.execute(
                        'INSERT INTO records(name, score, level, difficult_id, total) '
                        'VALUES(?, ?, ?, ?, ?)',
                        (name, self.score, self.level, self.difficult_id, total)
                    )
                    self.con.commit()
                manager.update(constants.FPS)
                manager.draw_ui(screen)
            x += speed
            screen.blit(fon, (x, y))
            if (
                    fon.get_rect().y + 100 < cursor.rect.y < 380 or
                    restart_button.rect.collidepoint(cursor.rect.center) or
                    results_button.rect.collidepoint(cursor.rect.center) or
                    exit_button.rect.collidepoint(cursor.rect.center)
            ) and pygame.mouse.get_focused():
                cursor_group.draw(screen)
                cursor_group.update()
            pygame.display.flip()
            clock.tick(constants.FPS)

    # игровой цикл экрана паузы
    def screen_pause(self) -> None:
        """
        Запускает игровой цикл для отрисовки окна паузы
        :return None:
        """
        manager: pygame_gui.UIManager = pygame_gui.UIManager(constants.SIZE)
        control_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                (3 * constants.SCREEN_WIDTH // 4 - 50,
                 3.5 * constants.SCREEN_HEIGHT // 4),
                (150, 50)
            ),
            text='Setup controller',
            manager=manager
        )
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
            f'Осталось жизней: {len(self.status_health)}',
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
            text_coord: int = 50
            for line in intro_text:
                string_rendered = font.render(line, True, pygame.Color('white'))
                intro_rect = string_rendered.get_rect()
                text_coord += 10
                intro_rect.top = text_coord
                intro_rect.x = 10
                text_coord += intro_rect.height
                screen.blit(string_rendered, intro_rect)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    terminate()
                if event.type == pygame.MOUSEMOTION:
                    x, y = event.pos
                    cursor.rect.x = x
                    cursor.rect.y = y
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.is_paused = False
                        return
                if event.type == pygame.USEREVENT:
                    if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                        if event.ui_element == control_button:
                            self.screen_setup_control()
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
            if pygame.mouse.get_focused():
                cursor_group.draw(screen)
                cursor_group.update()
            pygame.display.flip()
            clock.tick(constants.FPS)

    # игровой цикл экрана результатов
    def screen_result(self) -> None:
        """
        Запускает игровой цикл для отрисовки окна результатов
        :return None:
        """
        screen_result = pygame.display.set_mode(constants.SIZE)
        manager: pygame_gui.UIManager = pygame_gui.UIManager(constants.SIZE)
        item_list = ['Name    Score    Level    Difficult    Total']
        item_list += [
            ''.join([str(x).ljust(13, ' ') for x in difficult_name[1:]]) for
            difficult_name in
            self.con.cursor().execute(
                'SELECT * '
                'FROM records '
                'ORDER BY total DESC '
                'LIMIT 7'
            ).fetchall()]
        back_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                (constants.SCREEN_WIDTH // 4,
                 2.5 * constants.SCREEN_HEIGHT // 4),
                (100, 50)
            ),
            text='Back',
            manager=manager
        )
        clear_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                (constants.SCREEN_WIDTH // 4,
                 3 * constants.SCREEN_HEIGHT // 4),
                (100, 50)
            ),
            text='Clear',
            manager=manager
        )
        exit_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                (constants.SCREEN_WIDTH // 4,
                 3.5 * constants.SCREEN_HEIGHT // 4),
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
            intro_rect.x = 150
            text_coord += intro_rect.height
            screen_result.blit(string_rendered, intro_rect)
        while True:
            screen.fill('black')
            screen_result.blit(fon, (0, 0))
            font = pygame.font.Font(None, 25)
            text_coord: int = 100
            for line in item_list:
                string_rendered = font.render(line, True, pygame.Color('white'))
                intro_rect = string_rendered.get_rect()
                text_coord += 5
                intro_rect.top = text_coord
                intro_rect.x = 150
                text_coord += intro_rect.height
                screen_result.blit(string_rendered, intro_rect)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    terminate()
                if event.type == pygame.MOUSEMOTION:
                    x, y = event.pos
                    cursor.rect.x = x
                    cursor.rect.y = y
                if event.type == pygame.USEREVENT:
                    if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                        if event.ui_element == back_button:
                            return
                        if event.ui_element == clear_button:
                            pygame_gui.windows.UIConfirmationDialog(
                                rect=pygame.Rect(
                                    constants.SCREEN_WIDTH // 2 - 130,
                                    constants.SCREEN_HEIGHT // 2 - 100,
                                    260, 200),
                                manager=manager,
                                action_long_desc='Вы действительно '
                                                 'хотите очистить базу данных?',
                                window_title='Удалить все записи?'
                            )
                        if event.ui_object_id == '#confirmation_dialog.#confirm_button':
                            item_list = [
                                'Name    Score    Level    Difficult    Total']
                            self.con.cursor().execute(
                                'DELETE FROM records'
                            ).connection.commit()
                        if event.ui_object_id == '#confirmation_dialog.#cancel_button':
                            pass
                        if event.ui_element == exit_button:
                            terminate()
                manager.process_events(event)
            manager.update(constants.FPS)
            manager.draw_ui(screen)
            if pygame.mouse.get_focused():
                cursor_group.draw(screen)
                cursor_group.update()
            pygame.display.flip()
            clock.tick(constants.FPS)

    def screen_setup_control(self):
        control_image = {
            'control-right.jpg': constants.RIGHT_KEY,
            'control-left.jpg': constants.LEFT_KEY,
            'control-jump.jpg': constants.UP_KEY,
        }
        for filename, const_key in control_image.items():
            fon: pygame.Surface = pygame.transform.scale(
                load_image(filename), (
                    constants.SCREEN_WIDTH,
                    constants.SCREEN_HEIGHT
                )
            )
            running = True
            while running:
                screen.fill('black')
                screen.blit(fon, (0, 0))
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        terminate()
                    if event.type == pygame.KEYDOWN:
                        running = False
                        cur = self.con.cursor()
                        cur.execute(
                            'UPDATE controller '
                            f'SET key={event.key} '
                            f'WHERE key={const_key}'
                        )
                        self.con.commit()
                pygame.display.flip()
                clock.tick(constants.FPS)
        constants.setup_controller()

    # игровой цикл стартового экрана
    def screen_start(self) -> None:
        """
        Запускает игровой цикл для отрисовки стартового окна
        :return None:
        """
        manager: pygame_gui.UIManager = pygame_gui.UIManager(constants.SIZE)
        item_list = [difficult_name[0] for difficult_name in
                     self.con.cursor().execute(
                         'SELECT difficult_name '
                         'FROM difficult '
                         'ORDER BY id ASC'
                     ).fetchall()]
        control_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                (3 * constants.SCREEN_WIDTH // 4 - 50,
                 3.5 * constants.SCREEN_HEIGHT // 4),
                (150, 50)
            ),
            text='Setup controller',
            manager=manager
        )
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
            '', '',
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
            string_rendered = font.render('Коробочки', True,
                                          pygame.Color('white'))
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
                if event.type == pygame.MOUSEMOTION:
                    x, y = event.pos
                    cursor.rect.x = x
                    cursor.rect.y = y
                if event.type == pygame.USEREVENT:
                    if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                        if event.ui_element == start_button:
                            self.set_difficult(
                                difficult_state.get_single_selection())
                            sound_main_theme.play(loops=-1)
                            sound_main_theme.set_volume(0.1)
                            self.is_start_screen = False
                            return
                        if event.ui_element == results_button:
                            self.screen_result()
                        if event.ui_element == control_button:
                            self.screen_setup_control()
                        if event.ui_element == exit_button:
                            terminate()
                manager.process_events(event)
            manager.update(constants.FPS)
            manager.draw_ui(screen)
            if pygame.mouse.get_focused():
                cursor_group.draw(screen)
                cursor_group.update()
            pygame.display.flip()
            clock.tick(constants.FPS)

    def update(self, keys: [bool] = None, *args, **kwargs) -> None:
        """
        Отрисовка игрового мира
        :param keys: Sequence [bool]
        :param args:
        :param kwargs:
        :return None:
        """
        self.check_game_over()
        if self.is_game_over:
            sound_main_theme.stop()
            sound_gameover.play()
            self.screen_game_over()
            return
        if self.is_start_screen:
            self.screen_start()
            return
        if self.is_paused:
            self.screen_pause()
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
        Методы:
    cut_sheet - раскадровка из карты спрайта
    get_coords - возвращает координаты тайла на игровом поле
    is_can_jump - проверяет возможность прыгнуть вверх
    is_can_move_left - проверяет возможность пойти налево
    is_can_move_right - проверяет возможность пойти направо
    move - управляет перемещением героя по полю
    update - обновляет состояние главного героя после действий пользователя
    """

    def __init__(self, sheet: pygame.Surface, columns: int, rows: int):
        """
        :param sheet: pygame.Surface:
        :param columns: int:
        :param rows: int:
        """
        super().__init__(player_group, all_sprites)
        # количество циклов повторений анимации на экран
        self.count_animate: int = 4
        self.frames = []
        self.cut_sheet(sheet, columns, rows)
        self.cur_frame: int = 0
        self.gravity: float = constants.GRAVITY
        self.health: int = constants.HEALTHS
        self.image: pygame.Surface = self.frames[self.cur_frame]
        self.is_flip: bool = False  # статус разворота спрайта
        self.is_in_air: bool = False  # статус прыжка
        self.jump: float = 1.5 * constants.tile_height
        self.mask: pygame.mask = pygame.mask.from_surface(self.image)
        self.rect = self.rect.move(
            screen.get_rect().centerx - self.image.get_width() // 2,
            screen.get_rect().bottom - self.image.get_height() - constants.DOWN_BORDER
        )
        self.col, self.row = self.get_coords()
        self.v: int = 1  # скорость

    def cut_sheet(self, sheet: pygame.Surface, columns: int, rows: int) -> None:
        """
        Раскадровка из карты спрайта
        :param sheet:
        :param columns:
        :param rows:
        :return None:
        """
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
        :return bool:
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
        right_col = (
                (self.rect.centerx + self.rect.width // 4) *
                constants.COLUMNS // constants.SCREEN_WIDTH
        )
        return (self.col + 1 < constants.COLUMNS and
                self.rect.right < constants.SCREEN_WIDTH and
                not game.board[self.row][right_col])

    def move(self, keys: [bool]) -> None:
        """
        Управляет перемещением героя по полю
        :param keys: [bool]
        :return:
        """
        if keys[constants.LEFT_KEY]:
            if self.is_flip:
                self.image = pygame.transform.flip(self.image, True, False)
            if self.is_can_move_left():
                self.rect.x -= constants.STEP
        if keys[constants.RIGHT_KEY]:
            if not self.is_flip:
                self.image = pygame.transform.flip(self.image, True, False)
            if self.is_can_move_right():
                self.rect.x += constants.STEP
        if keys[constants.UP_KEY]:
            if self.is_can_jump():
                sound_jump.play()
                self.rect.y -= self.jump
                self.is_in_air = True

    def update(self, *args, **kwargs) -> None:
        """
        Обновляет состояние главного героя после действий пользователя
        :param args:
        :param kwargs:
        :return None:
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
    """
    Класс отвечающий за отрисовку жизни
    """

    def __init__(self):
        super().__init__(game_status)
        self.image: pygame.Surface = load_image("heart.png", color_key=-1)
        self.image = pygame.transform.scale(
            self.image, (self.image.get_width(),
                         self.image.get_height())
        )
        self.rect = self.image.get_rect()


class StatusScore(pygame.sprite.Sprite):
    """
    Класс отвечающий за отрисовку набранных очков
    """

    def __init__(self):
        super().__init__(game_status)
        self.font: pygame.font.Font = pygame.font.Font(None, 30)
        self.image: pygame.Surface = self.font.render('Score: ',
                                                      True,
                                                      pygame.Color('white'))
        self.rect = self.image.get_rect()
        self.rect.right = constants.SCREEN_WIDTH - self.rect.width
        self.rect.top = constants.MARGIN_STATUS

    def update(self, *args, **kwargs) -> None:
        self.image = self.font.render(f'Score: {game.score}', True,
                                      pygame.Color('white'))
        self.rect.right = constants.SCREEN_WIDTH - self.rect.width


class StatusLevel(pygame.sprite.Sprite):
    """
    Класс отвечающий за отрисовку текущего уровня
    """

    def __init__(self):
        super().__init__(game_status)
        self.font: pygame.font.Font = pygame.font.Font(None, 30)
        self.image: pygame.Surface = self.font.render('Level: ',
                                                      True,
                                                      pygame.Color('white'))
        self.rect = self.image.get_rect()
        self.rect.right = constants.SCREEN_WIDTH - 3 * self.rect.width
        self.rect.top = constants.MARGIN_STATUS

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
        Свойства:
    can_move_left: bool
    can_move_right: bool
    col: int
    image: pygame.Surface
    is_collide_bottom: bool
    is_collide_left: bool
    is_collide_right: bool
    is_collide_top: bool
    is_hero_collide_bottom: bool
    is_hero_collide_left: bool
    is_hero_collide_right: bool
    is_hero_collide_top: bool
    is_in_air: bool
    row: int
    sprite_copy: pygame.sprite.Sprite
    v: int
        Методы:
    get_coords - возвращает координаты тайла на игровом поле
    have_bottom_collide - Проверка что есть объект снизу
    have_hero_hit - Проверка что попали на героя сверху
    have_left_collide - Проверка что есть объект справа
    have_right_collide - Проверка что есть объект справа
    have_top_collide - Проверка что есть объект сверху
    increase_speed (@classmethod) - Меняет настройки скорости тайлов и
                                    сбрасывает таймер генерации коробок
    is_can_move_left - проверяет возможность сдвинуть коробку влево
    is_can_move_right - проверяет возможность сдвинуть коробку вправо
    move - управляет перемещением коробок по полю
    reset_v - сбрасывает скорости на начальные значения при рестарте
    setup_collide - сбрасывает значения пересечений
    update - обновляет состояние спрайта
    """

    v: int = constants.START_V

    def __init__(self, tile_type: str, pos_x: int) -> None:
        """
        :param tile_type: str
        :param pos_x: int
        :return None:
        """
        super().__init__(tiles_group, all_sprites)
        self.can_move_left: bool = True
        self.can_move_right: bool = True
        self.col: int = pos_x
        self.image: pygame.Surface = load_image(tile_type)
        self.is_collide_bottom: bool = False
        self.is_collide_left: bool = False
        self.is_collide_right: bool = False
        self.is_collide_top: bool = False
        self.is_hero_collide_bottom: bool = False
        self.is_hero_collide_left: bool = False
        self.is_hero_collide_right: bool = False
        self.is_hero_collide_top: bool = False
        self.is_in_air: bool = True
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect().move(constants.tile_width * pos_x,
                                               screen.get_rect().top)
        self.row: int = 0
        self.setup_collide()
        # копия объекта с увеличенной координатой y, для коррекции пересечений
        # на разных скоростях с нижними объектами
        self.sprite_copy: pygame.sprite.Sprite = copy(self)
        self.sprite_copy.rect.height += Tile.v

    def get_coords(self) -> [int, int]:
        """
        Возвращает координаты тайла на игровом поле (в клетках: столбец, строка)
        :return tuple[int, int]:
        """
        return self.rect.x * constants.COLUMNS // constants.SCREEN_WIDTH, \
               self.rect.y * constants.ROWS // constants.SCREEN_HEIGHT

    def have_bottom_collide(self, obj: pygame.sprite.Sprite) -> None:
        """
        Проверка что есть объект снизу
        :param obj: pygame.sprite.Sprite:
        :return None:
        """
        if obj.rect.right > self.rect.left and \
                obj.rect.left < self.rect.right and \
                obj.rect.bottom >= (self.rect.top +
                                    constants.ERROR_RATE) and \
                obj.rect.top <= (self.rect.bottom +
                                 constants.ERROR_RATE):
            if not isinstance(obj, Player):
                self.is_collide_bottom = True

    def have_hero_hit(self, obj: pygame.sprite.Sprite) -> None:
        """
        Проверка что попали на героя сверху
        :param obj: pygame.sprite.Sprite:
        :return None:
        """
        if obj.rect.right > self.rect.left and \
                obj.rect.left < self.rect.right and \
                obj.rect.top < (self.rect.bottom +
                                constants.ERROR_RATE) and \
                constants.tile_height < obj.rect.top - self.rect.top <= (
                constants.tile_height +
                constants.ERROR_RATE):
            self.is_hero_collide_bottom = True

    def have_left_collide(self, obj: pygame.sprite.Sprite) -> None:
        """
        Проверка что есть объект справа
        :param obj: pygame.sprite.Sprite:
        :return None:
        """
        if obj.rect.right > self.rect.left > obj.rect.left and \
                obj.rect.bottom - self.rect.top <= (constants.tile_height +
                                                    constants.ERROR_RATE) and \
                self.rect.bottom - obj.rect.top <= (constants.tile_height +
                                                    constants.ERROR_RATE):
            if isinstance(obj, Player):
                self.is_hero_collide_left = True
            else:
                self.is_collide_left = True

    def have_right_collide(self, obj: pygame.sprite.Sprite) -> None:
        """
        Проверка что есть объект справа
        :param obj: pygame.sprite.Sprite:
        :return None:
        """
        if self.rect.right > obj.rect.left > self.rect.left and \
                obj.rect.bottom - self.rect.top <= (constants.tile_height +
                                                    constants.ERROR_RATE) and \
                self.rect.bottom - obj.rect.top <= (constants.tile_height +
                                                    constants.ERROR_RATE):
            if isinstance(obj, Player):
                self.is_hero_collide_right = True
            else:
                self.is_collide_right = True

    def have_top_collide(self, obj: pygame.sprite.Sprite) -> None:
        """
        Проверка что есть объект сверху
        :param obj: pygame.sprite.Sprite:
        :return None:
        """
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

    @classmethod
    def increase_speed(cls) -> None:
        """
        Меняет настройки скорости тайлов и сбрасывает таймер генерации коробок
        :return None:
        """
        global CURRENT_BOMB_INTERVAL
        cls.v += 1
        CURRENT_BOMB_INTERVAL -= constants.INSTERVALS_PITCH
        pygame.time.set_timer(BOMBGENERATE, CURRENT_BOMB_INTERVAL)
        for tile in tiles_group:
            tile.image = load_image(color_box[game.level % len(color_box)])

    def is_can_move_left(self) -> bool:
        """
        Проверяет возможность сдвинуть коробку влево
        :return bool:
        """
        is_can = (
                self.rect.x > 0 and
                not self.is_collide_left and
                not self.is_collide_top and
                self.is_hero_collide_right
        )
        return is_can

    def is_can_move_right(self) -> bool:
        """
        Проверяет возможность сдвинуть коробку вправо
        :return None:
        """
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
        :return None:
        """
        hits: list = pygame.sprite.spritecollide(self, all_sprites, False)
        for obj in hits:
            if obj == self:
                continue
            # Проверка что есть объект справа
            self.have_right_collide(obj)
            # Проверка что есть объект слева
            self.have_left_collide(obj)
            # Проверка что есть объект сверху
            self.have_top_collide(obj)
            # Проверка что есть объект снизу
            self.have_bottom_collide(obj)
            # проверяем что не упали на героя
            self.have_hero_hit(obj)
            self.can_move_left = self.is_can_move_left()
            self.can_move_right = self.is_can_move_right()

        if keys[constants.LEFT_KEY] and self.can_move_left:
            self.rect.x -= constants.tile_width

        if keys[constants.RIGHT_KEY] and self.can_move_right:
            self.rect.x += constants.tile_width

    @classmethod
    def reset_v(cls) -> None:
        """
        Сбрасывает скорости на начальные значения при рестарте
        :return None:
        """
        global CURRENT_BOMB_INTERVAL
        cls.v = constants.START_V
        CURRENT_BOMB_INTERVAL = constants.BOMBS_INTERVALS
        pygame.time.set_timer(BOMBGENERATE, CURRENT_BOMB_INTERVAL)

    def setup_collide(self) -> None:
        """
        Сбрасывает значения пересечений
        :return None:
        """
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
        :return None:
        """
        self.can_move_left = self.is_can_move_left()
        self.can_move_right = self.is_can_move_right()
        if args:
            self.move(args[0])
        # Проверка что не упали на героя
        if (
                self.is_hero_collide_bottom and
                not self.is_hero_collide_left and
                not self.is_hero_collide_right and
                not self.is_hero_collide_top and
                len(pygame.sprite.spritecollide(self, tiles_group, False)) == 1
        ):
            game.player.health -= 1
            sound_hit.play()
            if game.board[self.row][self.col]:
                game.board[self.row][self.col] = 0
            self.kill()
            create_particles((self.rect.centerx, self.rect.top))
            game.status_health.pop().kill()
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
    """
    Частицы для анимации попадания в героя
    """
    fire = [choice(game.player.frames)]
    for scale in (5, 10, 20, 30):
        fire.append(pygame.transform.scale(fire[0], (scale, scale)))

    def __init__(self, pos, dx, dy):
        super().__init__(all_sprites, player_group)
        self.image: pygame.Surface = choice(self.fire)
        self.rect = self.image.get_rect()
        self.velocity = [dx, dy]
        self.rect.x, self.rect.y = pos
        self.gravity: float = constants.GRAVITY

    def update(self, *args, **kwargs):
        self.velocity[1] += self.gravity
        self.rect.x += self.velocity[0]
        self.rect.y += self.velocity[1]
        if not self.rect.colliderect(constants.screen_rect):
            self.kill()


cursor = pygame.sprite.Sprite(cursor_group)
cursor.image = load_image("arrow.png")
cursor.rect = cursor.image.get_rect()

keys = pygame.key.get_pressed()
is_paused = False
if __name__ == '__main__':
    pygame.mouse.set_visible(False)
    while True:
        generation = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                terminate()
            if event.type == pygame.MOUSEMOTION:
                x, y = event.pos
                cursor.rect.x = x
                cursor.rect.y = y
            if event.type == BOMBGENERATE and not is_paused:
                generation = True
            keys = pygame.key.get_pressed()
            if keys[pygame.K_ESCAPE]:
                game.is_paused = not game.is_paused
        if generation:
            # ограничиваем крайние столбики, чтобы не было завала
            col = randrange(1, constants.COLUMNS - 1)
            Tile(color_box[game.level % len(color_box)], col)
        game.update(keys)
        pygame.display.flip()
        clock.tick(constants.FPS)

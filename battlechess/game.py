# -*- coding: utf-8 -*-

'''
@name: battlechess
@author: Memory
@date: 2019/11/14
@document: 皇家战棋游戏的主要文件
'''

import time
import pygame
from random import choice
from .base import BaseGame, Button, Chess
from .utils import *
from .configs import *


class BeginGame(BaseGame):
    """游戏开始选择的画面和逻辑处理"""
    def __init__(self, factory, user, offline=False):
        super(BeginGame, self).__init__(WINDOW_TITILE, WINDOW_SIZE)
        pygame.display.set_icon(get_surface('icon'))
        self.factory = factory
        self.user = user
        self.offline = offline
        self.state = 'start'
        self.load_src()
        self.init_buttons()

    def load_src(self):
        '''
        载入所需的资源。
        '''
        self.img_bg = get_surface('bg')
        self.img_trans_bg = get_surface('trans_bg')
        self.img_begin = get_surface('begin')
        self.img_match = surface_clip_by_col(get_surface('match'), 2)
        self.img_button_cancel = surface_clip_by_row(get_surface('button_cancel'), 2)
        self.img_button_mode = surface_clip(get_surface('button_mode'), 2, 2, 'col')

    def init_buttons(self):
        def local(button):
            self.begin('local')

        def match(button):
            if not self.lose_connection() and self.user:
                data = {'type': 'match', 'name': self.user['name']}
                self.sendata(data)
                self.state = 'match'
                self.start_wait(self.img_match[0], self.buttons['cancel'])
            else:
                self.start_wait(self.img_wait[1][3], self.buttons['cancel'])

        def cancel(button):
            if self.state == 'match':
                data = {'type': 'unmatch', 'name': self.user['name']}
                self.sendata(data)
            button.set_visible(False)
            self.state = 'start'
            self.stop_wait()

        self.buttons['loacl'] = Button(self.screen, (300, 500), self.img_button_mode[0][0],
                                       'local', self.img_button_mode[0][1], local)
        self.buttons['match'] = Button(self.screen, (555, 500), self.img_button_mode[1][0],
                                       'match', self.img_button_mode[1][1], match)

        self.buttons['cancel'] = Button(self.screen, (445, 300), self.img_button_cancel[0],
                                        'local', self.img_button_cancel[1], cancel, False)

    def begin(self, mode, data=None):
        uninstall_game()
        game = BattleChess(self.factory, self.user, mode, data)
        self.state = None
        install_game(game)

    def update(self):
        if self.state == 'start':
            self.buttons['loacl'].set_click(True)
            if self.offline:
                self.buttons['match'].set_click(False)
            else:
                self.buttons['match'].set_click(True)

        elif self.state == 'match':
            data = self.getdata()
            if data and data['type'] == 'init':
                self.begin('online', data)

    def draw(self):
        self.screen.blit(self.img_bg, (0, 0))
        self.screen.blit(self.img_begin, (0, 0))
        for button in self.buttons.values():
            button.draw()


class BattleChess(BaseGame):
    """战棋的主类"""
    def __init__(self, factory, user, mode, data='None'):
        super(BattleChess, self).__init__(WINDOW_TITILE, WINDOW_SIZE)
        pygame.display.set_icon(get_surface('icon'))    # 设置窗口图标
        self.factory = factory                  # 网络连接的工厂，用来获取服务器传来的数据
        self.my_user = user                     # 用户
        self.mode = mode                        # 游戏模式，local 或者 online
        self.offline = user is None

        self.init_param()                       # 初始化参数
        self.load_src()                         # 载入资源
        self.init_game(data)                    # 初始化游戏
        self.init_head()                        # 初始化头像框
        self.init_button()                      # 初始化按钮
        self.bind_click(1, self.click)          # 绑定鼠标左键点击事件

        self.start_time = time.time()           # 开始计时

    @property
    def local(self):
        return self.mode == 'local'

    @property
    def online(self):
        return self.mode == 'online'

    @property
    def my_turn(self):
        return self.turn == self.my_color

    @property
    def enemy_color(self):
        if self.my_color == 'red':
            return 'blue'
        return 'red'

    def init_param(self):
        '''
        参数的初始化。
        '''
        self.start = False                      # 游戏是否开始
        self.start_time = -1                    # 上一步操作的时间
        self.wait_end = False                   # 是否结束游戏，进入等待退出的界面
        self.timeout = {'red': 0, 'blue': 0}    # 双方超时的次数
        self.no_eat = 0                         # 多少步没有吃子或者翻开棋子
        self.step = 0                           # 目前走的总步数
        # 棋盘相关的参数
        self.select = (-1, -1)                  # 选中的棋盘格子的位置，(-1, -1)表示无选中
        self.last_step = None                   # 记录上一步的操作，如果是翻开棋子，记录位置，如果是移动，记录前后的位置
        self.next_list = []                     # 选中的棋子下一步可走的地方
        self.cb_color = [[None for i in range(ROW)] for j in range(ROW)]    # 每个格子的颜色
        self.chess_left = {'red': 18, 'blue': 18, None: 0}   # 红蓝双方剩下的棋子
        self.chess = [[None for i in range(ROW)] for j in range(ROW)]   # 所有的棋子
        # 资源相关的参数，具体见 load_scr() 函数的说明
        self.img_unopen = []
        self.img_red_chess = [[[None, None] for i in range(ROW)] for j in range(ROW)]
        self.img_blue_chess = [[[None, None] for i in range(ROW)] for j in range(ROW)]

    def load_src(self):
        '''
        加载资源文件。
        self.img_unopen 是未被翻开时的棋子图像，共有6个尺寸。
        self.img_red_chess 存储红方棋子的图像，self.img_red_chess[i][j][k]含义如下：
            i: 0~5，分别表示：国王，将军，骑士，弓箭手，禁卫军，刺客
            j: 0~5，表示从上往下数第j层的棋子图像（因为每一层的尺寸不一样）
            k: 0: 棋子面向左边，1: 棋子面向右边。
        img_blue_chess 同上。
        '''
        img_unopen = get_surface('unopen')
        img_chess = get_surface('chess')
        self.img_red_head = get_surface('head_red')
        self.img_blue_head = get_surface('head_blue')
        self.img_bg = get_surface('bg')
        self.img_time = get_surface('time')
        self.img_button_ok = surface_clip_by_row(get_surface('button_ok'), 2)
        self.img_button_giveup = surface_clip(get_surface('button_giveup'), 2, 2, 'col')
        for i in range(ROW):
            size = CHESS_SIZE[i]
            self.img_unopen.append(pygame.transform.scale(img_unopen, (size, size)))
            chess_img = pygame.transform.scale(img_chess, (size*6, size*2))
            for j in range(ROW):
                red_temp = chess_img.subsurface((j*size, 0), (size, size))
                blue_temp = chess_img.subsurface((j*size, size), (size, size))
                self.img_red_chess[j][i][0] = red_temp
                self.img_blue_chess[j][i][0] = blue_temp
                self.img_red_chess[j][i][1] = pygame.transform.flip(red_temp, True, False)
                self.img_blue_chess[j][i][1] = pygame.transform.flip(blue_temp, True, False)

        # 加载字体文件
        self.font_time = pygame.font.SysFont("Calibri", 40, True)       # 剩余时间所用的字体
        self.font_text = pygame.font.SysFont("SimHei", 13, True)        # 超时次数所用的字体
        self.font_name = pygame.font.SysFont("SimHei", 14, True)        # 玩家的名字
        self.font_title = pygame.font.SysFont("SimHei", 18, True)       # 玩家的称号

    def init_game(self, data):
        '''
        根据模式初始化游戏参数。
        本地模式时，使用随机的棋盘和随机的先后手。
        网络模式时，使用服务器传来的游戏数据。
        '''
        if self.local:    # 本地对战时本地生成棋子，联网对战时服务器生成棋子
            self.load_chess(random_chess())
            if not self.my_user:
                self.my_user = random_user()
            self.your_user = random_user()
            self.turn = choice(['red', 'blue'])
            self.my_color = self.turn
        elif self.online:
            self.load_chess(data['chess'])
            self.your_user = data['you']
            self.turn = data['turn']
            self.my_color = data['color']

    def load_chess(self, chess):
        '''
        载入random_chess()传来的棋子信息，联网对战时，
        服务器传来的棋子信息也是random_chess()生成的。
        '''
        for i, j in self.traverse():
            color = chess[i][j][0]
            level = chess[i][j][1]
            if color == 'red':
                self.chess[i][j] = Chess(color, (i, j), level, self.img_red_chess, self.chess)
            elif color == 'blue':
                self.chess[i][j] = Chess(color, (i, j), level, self.img_blue_chess, self.chess)

    def init_head(self):
        '''
        初始化头像框。根据双方的颜色选择头像框，
        由于游戏过程中不需要变化，所以直接把用户信息都绘制上去。
        需要使用 copy() 方法得到一份副本，否则会影响下一次的游戏。
        '''
        if self.my_color == 'red':
            self.my_head = self.img_red_head.copy()
            self.your_head = self.img_blue_head.copy()
        else:
            self.my_head = self.img_blue_head.copy()
            self.your_head = self.img_red_head.copy()
        self.draw_head(self.my_head, self.my_user)
        self.draw_head(self.your_head, self.your_user)

    def draw_head(self, head, user):
        '''
        将用户信息绘制到头像框上。
        '''
        title = self.font_title.render(user['title'], True, COLOR['time_text'])
        name = self.font_name.render(user['name'], True, (255, 255, 255))
        credit = self.font_name.render(str(user['credit']), True, (255, 255, 255))
        rect = head.get_rect()
        pos = title.get_rect(centerx=rect.centerx)
        head.blit(title, (pos.x, 97))
        head.blit(name, (85, 134))
        head.blit(credit, (85, 159))

    def init_button(self):
        '''初始化按钮。'''
        def ok(button):
            self.end = True
            uninstall_game()
            user = None if self.offline else self.my_user
            begin = BeginGame(self.factory, user, self.offline)
            install_game(begin)

        # 这个按钮是在最后游戏结束显示结果时才会出现的,点击后结束游戏并返回到开始界面。
        self.buttons['ok'] = Button(self.screen, (445, 300), self.img_button_ok[0],
                                    'ok', self.img_button_ok[1], ok)
        # 开始时不可见
        self.buttons['ok'].set_visible(False)

        def giveup(button):
            if self.online:
                data = {'type': 'giveup'}
                self.sendata(data)
            self.win_game(self.enemy_color)

        # 这个按钮是用来认输的，只有游戏超过一定的步数时才可以点击。
        self.buttons['giveup'] = Button(self.screen, (427, 580), self.img_button_giveup[1][0],
                                        'giveup', self.img_button_giveup[1][1], giveup)
        self.buttons['giveup'].set_click(False)

    def win_game(self, color):
        '''
        color 表示哪一方已经获胜，据此选择合适的结束界面。
        如果是网络对战，给服务器发送一个结束游戏的包。
        '''
        self.wait_end = True
        self.buttons['giveup'].set_click(False)
        if self.local:
            mapcolor = {'red': 0, 'blue': 1, None: 2}
            self.img_wait_end = self.img_wait[1][mapcolor[color]]
        elif self.online:
            if not color:
                self.img_wait_end = self.img_wait[0][2]
                data = {'type': 'endgame', 'user': None}
            elif color != self.my_color:
                self.img_wait_end = self.img_wait[0][1]
                self.my_user['credit'] -= WIN_CREDIT
                self.my_user['title'] = get_title(self.my_user['credit'])
                data = {'type': 'endgame', 'user': self.my_user}
            elif color == self.my_color:
                self.img_wait_end = self.img_wait[0][0]
                self.my_user['credit'] += WIN_CREDIT
                self.my_user['title'] = get_title(self.my_user['credit'])
                data = {'type': 'endgame', 'user': self.my_user}
            self.sendata(data)
        self.start_wait(self.img_wait_end, self.buttons['ok'])

    def update(self):
        '''
        判断是否游戏结束，并且解析服务器传来的数据。
        '''
        if self.wait_end:
            return
        if self.online and self.lose_connection():
            self.wait_end = True
            self.offline = True
            self.start_wait(self.img_wait[0][3], self.buttons['ok'])
            return
        redleft, blueleft = self.chess_left['red'], self.chess_left['blue']
        redtime, bluetime = self.timeout['red'], self.timeout['blue']
        # 检测是否有一方棋子全被吃掉
        if redleft == 0:
            self.win_game('blue')
        elif blueleft == 0:
            self.win_game('red')
        # 检测双方是否都只剩下一个棋子，若是，谁的比较大谁就获胜
        elif redleft == 1 and blueleft == 1:
            left = {}
            for i, j in self.traverse():
                chess = self.Chess[i][j]
                if chess:
                    left[chess.color] = chess
            if left['red'].eat(left['blue']):
                self.win_game('red')
            else:
                self.win_game('blue')
        # 谁超时了 MAX_TIMEOUT 次就算输
        if redtime >= MAX_TIMEOUT:
            self.win_game('blue')
        elif bluetime >= MAX_TIMEOUT:
            self.win_game('red')
        # MAX_NOEAT 步内没有吃子或者翻开棋子就自动和棋
        if self.no_eat >= MAX_NOEAT:
            self.win_game(None)
        # 至少 MIN_GIVEUP 步以后才能认输
        if self.step >= MIN_GIVEUP:
            self.buttons['giveup'].set_click(True)

        self.parse_data()

    def parse_data(self):
        '''
        解析服务器传来的数据，根据数据进行操作。
        '''
        if not self.factory or not self.factory.data or self.wait_end:
            return
        # todo: 加入断线检测。
        if self.factory.lost:
            pass
        data = self.factory.data
        typ = data['type']
        if typ == 'move':
            x, y = data['from'][0], data['from'][1]
            self.move_chess(self.chess[x][y], *data['to'])
        elif typ == 'open':
            x, y = data['from'][0], data['from'][1]
            self.open_chess(x, y)
        elif typ == 'giveup':
            self.win_game(self.my_color)
        self.factory.data = None

    def update_color(self):
        '''
        更新棋盘每个格子的颜色。
        '''
        if self.wait_end:
            return
        for i, j in self.traverse():
            p = [CHESSBOARD[i][j], CHESSBOARD[i+1][j], CHESSBOARD[i+1][j+1], CHESSBOARD[i][j+1]]
            if (i+j) % 2 == 0:
                self.cb_color[i][j] = COLOR['board_1']
            else:
                self.cb_color[i][j] = COLOR['board_2']

            if self.last_step == (i, j):
                self.cb_color[i][j] = COLOR['last_step']

            if (i, j) in self.next_list:
                self.cb_color[i][j] = COLOR['next']
            # 选中的棋子所在的棋盘格
            x, y = pygame.mouse.get_pos()
            if self.select == (i, j):
                self.cb_color[i][j] = COLOR['select']
            # 鼠标悬停的棋盘格
            elif isInsidePolygon((x, y), p):
                self.cb_color[i][j] = COLOR['hover']

    def draw_time(self):
        '''
        绘制双方剩余的时间。
        '''
        if self.wait_end:
            return
        time_img = self.img_time.copy()
        t = int(time.time() - self.start_time)
        if t > MAX_TIME:
            self.start_time = time.time()
            t = 0
            self.timeout[self.turn] += 1
            print(self.timeout)

        time_left = self.font_time.render(str(MAX_TIME-t), True, pygame.color.Color(self.turn))
        rect = time_img.get_rect()
        pos = time_left.get_rect(centerx=rect.centerx, bottom=rect.bottom-20)
        time_img.blit(time_left, pos)
        if self.local:
            text = '你已超时 %d 次' % self.timeout[self.turn]
            time_pos = TIME_POS[0] if self.turn == 'red' else TIME_POS[1]
        elif self.my_color == self.turn:
            text = '你已超时 %d 次' % self.timeout[self.turn]
            time_pos = TIME_POS[0]
        else:
            text = '对方已超时 %d 次' % self.timeout[self.turn]
            time_pos = TIME_POS[1]
        time_text = self.font_text.render(text, True, COLOR['time_text'])
        pos = time_text.get_rect(centerx=rect.centerx, top=rect.top+20)
        time_img.blit(time_text, pos)
        self.screen.blit(time_img, time_pos)

    def draw(self):
        '''
        绘制画面。
        '''
        # 填充背景
        self.update_color()
        self.screen.blit(self.img_bg, (0, 0))
        # 绘制棋盘的边框
        pygame.draw.polygon(self.screen, COLOR['boder'], BODER)
        # 绘制头像框
        self.screen.blit(self.my_head, (20, 50))
        self.screen.blit(self.your_head, (780, 50))
        # 绘制剩余时间
        self.draw_time()
        for i, j in self.traverse():
            # 画棋盘
            p = [CHESSBOARD[i][j], CHESSBOARD[i+1][j], CHESSBOARD[i+1][j+1], CHESSBOARD[i][j+1]]
            pygame.draw.polygon(self.screen, self.cb_color[i][j], p)

            # 画棋子
            chess = self.chess[i][j]
            if chess is None:
                continue
            if not chess.open:
                self.screen.blit(self.img_unopen[i], CHESS_POS[i][j])
            else:
                chess.draw(self.screen)
        self.buttons['giveup'].draw()

    def traverse(self):
        '''
        遍历整个棋盘，返回每个位置(i, j)
        '''
        for i in range(ROW):
            for j in range(ROW):
                yield i, j

    def find_position(self, x, y):
        '''
        找到位置 (x, y) 属于哪一个棋盘格。
        @(x, y): 像素位置。
        @return：棋盘位置(i, j)
        '''
        for i, j in self.traverse():
            p = [CHESSBOARD[i][j], CHESSBOARD[i+1][j], CHESSBOARD[i+1][j+1], CHESSBOARD[i][j+1]]
            if isInsidePolygon((x, y), p):
                return (i, j)
        return (-1, -1)

    def get_selcet_chess(self):
        '''
        返回鼠标选中的棋子。
        '''
        x, y = self.select[0], self.select[1]
        return self.chess[x][y]

    def turn_color(self):
        '''
        转换目前活动的阵营。
        '''
        if self.turn == 'red':
            self.turn = 'blue'
        else:
            self.turn = 'red'
        if self.local:
            self.my_color = self.turn
        self.step += 1
        self.start_time = time.time()

    def click(self, x, y):
        '''
        鼠标点击一个位置时的响应事件。
        @(x, y)： 鼠标点击的位置
        '''
        if self.wait_end:
            return
        x, y = self.find_position(x, y)
        if x == -1 and y == -1:
            return
        elif self.local:
            self.click_help(x, y)
        elif self.online:
            if self.my_color != self.turn:
                return
            self.click_help(x, y)

    def open_chess(self, x, y):
        '''
        翻开棋子。
        '''
        self.no_eat = 0
        self.chess[x][y].open = True
        self.last_step = (x, y)
        self.turn_color()

    def move_chess(self, sc, x, y):
        '''
        移动棋子。
        sc 是要移动的棋子，(x, y) 是要移动去的位置。
        '''
        self.last_step = (x, y)
        dead = sc.move(x, y)
        if not dead:
            self.no_eat += 1
        else:
            self.no_eat = 0
            self.chess_left[dead] -= 1
        self.turn_color()
        self.next_list = []

    def click_help(self, x, y):
        '''
        点击棋盘时的逻辑判断，不要瞎改。
        理一遍这个逻辑很难受，所以没事不改这个。
        '''
        chess = self.chess[x][y]
        if self.select == (-1, -1):
            self.next_list = []
            if chess is None:
                return
            if not chess.open:
                if self.online:
                    data = {'type': 'open', 'from': [x, y]}
                    self.sendata(data)
                self.open_chess(x, y)
            elif chess.color == self.turn:
                self.select = (x, y)
                self.next_list = self.get_selcet_chess().next()
        else:
            sc = self.get_selcet_chess()
            self.select = (-1, -1)
            if (x, y) in self.next_list:
                if self.online:
                    data = {'type': 'move', 'from': [sc.x, sc.y], 'to': [x, y]}
                    self.sendata(data)
                self.move_chess(sc, x, y)
            elif self.select != (x, y):
                self.next_list = []
                self.click_help(x, y)

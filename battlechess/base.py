#!python3
# -*- coding: utf-8 -*-
'''
@name: base
@author: Memory&Xinxin
@date: 2019/11/22
@document: 游戏的基类，棋子类和按键类
'''
import json
import pygame
from pygame.locals import *
from twisted.internet import reactor
from .utils import uninstall_game, get_surface, surface_clip
from .configs import *


class BaseGame(object):
    def __init__(self, title, size):
        self.size = size
        pygame.init()
        self.screen = pygame.display.set_mode(size, 0, 32)
        pygame.display.set_caption(title)
        self.clicks = {}
        self.buttons = {}
        self.end = False
        self.offline = False
        self.fullscreen = False
        self.is_draw = True
        self.factory = None
        self._wait = False
        self.img_trans_bg = get_surface('trans_bg')
        self.img_wait = surface_clip(get_surface('wait'), 2, 4)

    def bind_click(self, button, action):
        self.clicks[button] = action

    def start_wait(self, img, button):
        self._wait_img = img
        self._wait_button = button
        self._wait_button.set_visible(True)
        self._wait = True

    def stop_wait(self):
        self._wait = False

    def show_wait(self):
        if not self._wait:
            return
        self.screen.blit(self.img_trans_bg, (0, 0))
        r = self.screen.get_rect()
        pos = self._wait_img.get_rect(center=r.center)
        self.screen.blit(self._wait_img, (pos.x, pos.y-100))
        self._wait_button.draw()

    def sendata(self, data):
        '''
        将数据发送到服务器。会出现粘包现象，即分开发送的数据，服务器是一次性收到的。
        '''
        if not self.factory or not self.factory.protocol:
            return
        self.factory.protocol.transport.write(json.dumps(data).encode('utf-8'))
        # self.factory.protocol.transport.getHandle().sendall(json.dumps(data).encode('utf-8'))

    def getdata(self, clean=True):
        if not self.factory:
            return None
        if self.factory.data:
            data = self.factory.data
            if clean:
                self.factory.data = None
            return data
        return None

    def lose_connection(self):
        if self.offline:
            return False
        if self.factory and self.factory.lost:
            return True
        return False

    def handle_input(self, event):
        if event.type == pygame.QUIT:
            self.quit()
            return
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button in self.clicks.keys():
                self.clicks[event.button](*event.pos)

        for button in self.buttons.values():
            button.update(event)

    def run(self):
        for event in pygame.event.get():
            self.handle_input(event)
        if self.end:
            return

        self.update()
        self.draw()
        self.show_wait()
        pygame.display.update()

    def quit(self):
        uninstall_game()
        pygame.quit()
        self.end = True
        reactor.stop()

    def is_end(self):
        return self.end

    def update(self):
        pass

    def draw(self):
        pass


class Button(object):
    '''
    定义一个简单的按钮类。
    '''
    def __init__(self, screen, pos, img, name, img_hover=None, click=None, visible=True):
        '''
        Args:
            pos: 按钮的位置
            img: 按钮显示的图片，Surface对象
            img_hover: 鼠标悬停时显示的图片，Surface对象
            click: 点击时的函数
        '''
        self.screen = screen
        self.img = img
        self.img_origin = img
        self.img_hover = img_hover
        self.name = name
        self.click = click
        self.is_click = self.click is not None
        self.visible = visible
        self.rect = pygame.Rect(pos, self.img.get_rect().size)

    def update(self, event=None):
        if not self.visible:
            return
        if not self.img_hover or not self.is_click:
            self.img = self.img_origin
            return
        x, y = pygame.mouse.get_pos()
        if self.rect.collidepoint(x, y):
            self.img = self.img_hover
            if self.is_click and self.click and event and event.type == MOUSEBUTTONDOWN:
                self.click(self)
        else:
            self.img = self.img_origin

    def draw(self):
        if self.visible:
            self.screen.blit(self.img, self.rect)

    def set_visible(self, v):
        self.visible = v

    def set_click(self, c):
        self.is_click = c


class WaitButton(Button):
    """docstring for WaitButton"""
    def __init__(self, screen, img, name, img_hover=None, click=None):
        super(WaitButton, self).__init__(screen, (445, 300), img, name, img_hover, click)
        self.visible = False


class Chess(object):
    '''
    棋子类。
    '''
    def __init__(self, color, pos, level, img_chess, cb):
        self.color = color                  # 颜色，即阵营
        self.x, self.y = pos[0], pos[1]     # 位置
        self.level = level                  # 等级，0~5，分别表示：国王，将军，骑士，弓箭手，禁卫军，刺客，越小越厉害
        self.img = img_chess[level]         # 图像
        self.open = False                   # 是否被翻开
        self.dire = 0                       # 方向，0是左边，1是右边
        self.cb = cb                        # 二位数组，存储整个棋盘所有的棋子

    def draw(self, screen):
        screen.blit(self.img[self.x][self.dire], CHESS_POS[self.x][self.y])

    def move(self, x, y):
        '''
        棋子的移动。
        @(x, y): 棋子要移动到的位置。
        @return: 如果有棋子死亡，返回死亡的阵营：'red' 或 'blue'。
                 如果没有棋子死亡，返回 'none'。
        '''
        # 更新棋子的方向
        d = y - self.y
        if d != 0:
            self.dire = 0 if d == -1 else 1
        # 获取死亡情况
        chess = self.cb[x][y]
        dead = None
        if chess is not None:
            dead = chess.color

        # 移动棋子，并更新位置
        self.cb[self.x][self.y] = None
        self.x, self.y = x, y
        self.cb[self.x][self.y] = self

        return dead

    def pos(self):
        return (self.x, self.y)

    def eat(self, chess):
        if self.level == 0 and chess.level == 5:
            return False
        if self.level == 5 and chess.level == 0:
            return True
        if self.level <= chess.level:
            return True

    def next(self):
        next_list = []
        for d, v in DIRECTION.items():
            nx = self.x + v[0]
            ny = self.y + v[1]
            if nx < 0 or nx >= ROW or ny < 0 or ny >= ROW:
                continue
            chess = self.cb[nx][ny]
            if chess is None:
                next_list.append((nx, ny))
            elif chess.open and chess.color != self.color:
                if self.eat(chess):
                    next_list.append((nx, ny))
        return next_list

# -*- coding: utf-8 -*-

'''
@name: utils
@author: Memory&Xinxin
@date: 2019/11/22
@document: 为游戏提供一些辅助类和辅助函数
'''

import os
import json
import pygame
import sqlite3
from random import choice, randint
from datetime import datetime
from twisted.internet import task
from .configs import *


_game = None
def install_game(basegame, ms=30, reactor=None):
    """
    将一个basegame游戏对象安装到reactor中，其实就是隔30ms就调用一下basegame的
    run() 方法，这样子可以让其不用运行在另一个线程中，可以避免很多麻烦。
    这个方法是由 tksupport 文件改来的，具体可见：
    https://twistedmatrix.com/documents/8.1.0/api/twisted.internet.tksupport.html
    """
    global _game
    _game = task.LoopingCall(basegame.run)
    _game.start(ms / 1000.0, False)


def uninstall_game():
    '''
    停止定时任务。
    '''
    global _game
    _game.stop()
    _game = None


def qqmsg(name, op):
    '''
    为了和另nonebot交互，可以把服务器的一些日志发送到QQ上，
    就在服务端调用这个函数，把一些消息写到文件中，再由nonebot
    读取并发送到QQ。
    '''
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S : ')
    msg = "%s%s %s。\n" % (now, name, op)
    with open(LOGIN_LOG, 'a+') as f:
        f.write(msg)


class Logging(object):
    '''用来打印日志的类'''
    def __init__(self, path=None):
        self.path = path
        self.output = True
        if not os.path.exists(path):
            os.makedirs(path)

    def print(self, *args):
        '''
        打印日志，并写入到文件中。
        '''
        # 构造日志格式
        datenow = datetime.now()
        now = datenow.strftime('%Y-%m-%d %H:%M:%S : ')
        log = [str(s) for s in args]
        logstr = now + ' '.join(log)
        # 打印
        print(logstr)
        if not self.path or not self.output:
            return
        # 写入到文件中
        log_file = datenow.strftime('log_%Y_%m_%d.txt')
        log_file = os.path.join(self.path, log_file)
        with open(log_file, 'a+') as f:
            f.write(logstr+'\n')


def excuteSQL(sql, value=None, db=USERDB):
    '''
    执行一条SQL语句，如果是select，就返回查询结果，如果出错返回None。
    '''
    sql = sql.upper()
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    result = []
    try:
        if value:
            cursor.execute(sql, value)
        else:
            cursor.execute(sql)
        if sql.startswith('SELECT'):
            result = cursor.fetchall()
    except:
        return None
    finally:
        cursor.close()
        conn.commit()
        conn.close()
        return result


def spilt_data(data):
    '''
    用来将服务器传来的数据包分开。
    默认客户端和服务器端每次传送的数据都是
    一个标准的json字符串加上换行符，因此只要
    根据换行符进行数据分离就可以了。
    '''
    jsons = []
    lines = data.decode('utf-8').split('\n')
    for line in lines:
        line = line.strip()
        if line == '':
            continue
        try:
            # 防止传来的不是json数据导致解析出错
            j = json.loads(line)
            jsons.append(j)
        except:
            Logging(SERVER_LOG_PATH).print('json数据解析失败，内容为： %s' % line)

    return jsons


def dict2bin(data):
    '''
    将字典数据转换成字符串，然后加上一个换行符，
    再转换成二进制数据。
    '''
    strdata = json.dumps(data)
    strdata = strdata + '\n'
    return strdata.encode('utf-8')


def get_user(name):
    '''
    查询一个用户名的信息。
    '''
    sql = 'SELECT credit, title FROM user WHERE name=?'
    value = (name, )
    result = excuteSQL(sql, value)[0]
    return {'name': name, 'credit': result[0], 'title': result[1]}


all_surface = {}


def get_surface(name):
    '''
    返回文件名对应的Surface，都存在一个字典里，避免重复读取。
    '''
    global all_surface
    if name in all_surface:
        return all_surface[name]
    file = ALL_IMG[name]
    surface = pygame.image.load(file).convert_alpha()
    all_surface[name] = surface
    return surface


def surface_clip_by_row(src, row):
    '''
    将一个surface按行分割。
    '''
    w, h = src.get_size()
    h = h // row
    dst = []
    for i in range(row):
        dst.append(src.subsurface((0, i*h), (w, h)))
    return dst


def surface_clip_by_col(src, col):
    '''
    将一个surface按列分割。
    '''
    w, h = src.get_size()
    w = w // col
    dst = []
    for i in range(col):
        dst.append(src.subsurface((i*w, 0), (w, h)))
    return dst


def surface_clip(src, row, col, mode='row'):
    '''
    将一个surface划分成row*col个等大的subsurface，
    如果 mode=='row'，返回dst[row][col]
    如果 mode=='col'，返回dst[col][row]
    '''
    w, h = src.get_size()
    h = h // row
    w = w // col
    dst = []
    if mode == 'row':
        for r in surface_clip_by_row(src, row):
            dst.append(surface_clip_by_col(r, col))
    elif mode == 'col':
        for c in surface_clip_by_col(src, col):
            dst.append(surface_clip_by_row(c, row))
    return dst


def random_chess():
    '''
    随机生成一盘棋局。
    '''
    CHESS_NUM = [2, 2, 4, 4, 8, 16]
    all_pos = [(i, j) for i in range(6) for j in range(6)]
    chess = [[0 for i in range(6)] for j in range(6)]
    level = 0
    for i in range(36):
        x, y = choice(all_pos)
        all_pos.remove((x, y))
        if i % 2 == 0:
            chess[x][y] = ['red', level]
        else:
            chess[x][y] = ['blue', level]

        CHESS_NUM[level] -= 1
        if CHESS_NUM[level] <= 0:
            level += 1
    return chess


def random_user():
    '''
    随机生成一个用户。
    '''
    X = choice(XING)
    M = "".join(choice(MING) for i in range(randint(1, 2)))
    T = choice(list(TITLE))
    name = {'name': X+M, 'title': T, 'credit': randint(TITLE[T][0], TITLE[T][1]-1)}
    return name


def get_title(credit):
    '''
    给定积分credit，返回对应的称号。
    '''
    if credit < 0:
        return '平民'
    for t, c in TITLE.items():
        if c[0] <= credit < c[1]:
            return t
    return '教皇'


def hex2rgb(color):
    '''
    将16进制的颜色转换为 (r, g, b) 形式。
    '''
    b = color % 256
    color = color >> 8
    g = color % 256
    color = color >> 8
    r = color % 256
    return (r, g, b)


def isInsidePolygon(pt, poly):
    '''
    判断一个点是否在一个多边形内部。
    @pt: (x, y)
    @poly: 多边形点的列表
    @return： bool
    '''
    c = False
    i = -1
    j = len(poly) - 1
    while i < len(poly)-1:
        i += 1
        if ((poly[i][0] <= pt[0] and pt[0] < poly[j][0]) or (poly[j][0] <= pt[0] and pt[0] < poly[i][0])):
            if (pt[1] < (poly[j][1] - poly[i][1]) * (pt[0] - poly[i][0]) / (poly[j][0] - poly[i][0]) + poly[i][1]):
                c = not c
        j = i
    return c


def warpPerspective(trans, src):
    '''
    给定投影变换矩阵和源点，返回目标点
    @trans：投影变换矩阵，大小是3*3
    @src：源点(x, y)
    @return：目标点(x, y)
    '''
    dst = np.matmul(trans, np.array([src[0], src[1], 1], np.float32).T)
    dst = dst / dst[-1]
    dst = dst.astype(np.int)
    return dst[:2]


def gen_chessboard():
    '''
    因为考虑到后面可能要打包成exe文件，为了减少依赖，
    所以用这个函数生成棋盘矩阵，然后硬编码到代码里。
    '''
    # src定义了棋盘的正方形，将被划分成6*6的格子，这里选择的是每个格子95*95
    src = np.array([[15, 15], [15, 585], [585, 585], [585, 15]], np.float32)
    # dst定义了src进行投影变换后的四边形
    dst = np.array([[80, 210], [15, 585], [585, 585], [520, 210]], np.float32)
    # 先计算出投影矩阵trans
    trans = cv2.getPerspectiveTransform(src, dst)
    # boder定义了棋盘的正方形边框，比棋盘大了一点
    boder = [[0, 0], [0, 600], [600, 600], [600, 0]]
    # 计算出投影后的四边形
    transboder = [warpPerspective(trans, s).tolist() for s in boder]
    print(transboder)
    # 6*6的棋盘由7条横线和7条竖线相交得到，这里计算出7*7个交点
    cb_list = []
    for y in range(7):
        tb = []
        for x in range(7):
            d = warpPerspective(trans, (15+x*95, y*95+15))
            tb.append(d.tolist())
        cb_list.append(tb)
    print(cb_list)
    return cb_list


if __name__ == '__main__':
    # 如果需要运行这个文件，才需要安装下面这两个库
    import cv2
    import numpy as np
    gen_chessboard()

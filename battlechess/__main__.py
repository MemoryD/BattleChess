# -*- coding: utf-8 -*-

'''
@name: battlechess
@author: Memory&Xinxin
@date: 2019/11/22
@document: 皇家战棋游戏的入口文件
'''

from twisted.internet import reactor, tksupport
from .configs import HOST, PORT
from .client import BCClientFactory
from .login import LoginUI


if __name__ == '__main__':
    '''
    整个运行的流程是从登录界面开始的，
    如果登录成功则进入游戏开始界面，
    如果无法连接网络，则提示用户是否以离线模式启动，
    离线模式时，无法进入联网对战。
    进入开始界面以后，用户再选择是本地对战还是网络对战，
    如果是本地对战，那使用本地生成的棋盘信息和随机用户信息进行对战。
    如果是网络对战，则先匹配对手，匹配到了用服务器发来的棋盘信息进行对战。
    '''
    # 先实例化一个登录界面
    ui = LoginUI()
    # 初始化一个协议的工厂
    factory = BCClientFactory(ui)
    # 连接到服务器
    reactor.connectTCP(HOST, PORT, factory)
    # 开始运行登录界面
    tksupport.install(ui)
    # 开始运行网络协议
    reactor.run()

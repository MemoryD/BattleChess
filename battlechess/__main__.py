# -*- coding: utf-8 -*-

'''
@name: battlechess
@author: Memory
@date: 2019/11/14
@document: 皇家战棋游戏的入口文件
'''

from twisted.internet import reactor, tksupport
from .configs import HOST, PORT
from .client import BCClientFactory
from .login import UserUI


if __name__ == '__main__':
    ui = UserUI()
    factory = BCClientFactory(ui)
    reactor.connectTCP(HOST, PORT, factory)
    tksupport.install(ui)
    reactor.run()

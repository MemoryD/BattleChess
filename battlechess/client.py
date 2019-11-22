# -*- coding: utf-8 -*-

'''
@name: client
@author: Memory&Xinxin
@date: 2019/11/15
@document: 皇家战棋游戏网络传输的客户端协议的实现
'''

import json
from tkinter.messagebox import showinfo
from twisted.internet.protocol import Protocol, ClientFactory
from .utils import Logging, spilt_data
from .configs import CLIENT_LOG_PATH


class BCClientProtocol(Protocol):
    def __init__(self, factory, ui):
        self.factory = factory
        self.connected = False
        self.log = Logging(CLIENT_LOG_PATH)
        self.ui = ui

    def connectionMade(self):
        '''
        建立连接。
        '''
        self.connected = True

    def connectionLost(self, reason):
        '''
        丢失连接。
        '''
        self.connected = False

    def dataReceived(self, data):
        '''
        收到服务器的数据时采取的动作。
        由于数据可能粘包，所以需要先进行分包，然后再逐个处理。
        '''
        jsons = spilt_data(data)

        for data in jsons:
            if 'type' not in data:
                continue
            if data['type'] in ['signin', 'signup']:
                self.user_login(data)
            else:
                self.factory.data.append(data)

    def user_login(self, data):
        typ = data['type']
        result = data['result']

        if typ == 'signin':
            if result == 'success':
                self.ui.user = data['user']
                self.ui.begin(False)
            else:
                showinfo('登录失败', data['reason'])
        elif typ == 'signup':
            if result == 'success':
                showinfo('注册成功', '注册成功，可以登录了！')
            else:
                showinfo('注册失败', data['reason'])


class BCClientFactory(ClientFactory):
    def __init__(self, ui):
        self.protocol = None
        self.data = []
        self.failed = False
        self.lost = False
        self.log = Logging(CLIENT_LOG_PATH)
        self.ui = ui
        self.ui.factory = self

    def startedConnecting(self, connector):
        self.log.print("正在连接到服务器...")

    def buildProtocol(self, addr):
        self.log.print("连接到服务器成功。")
        self.protocol = BCClientProtocol(self, self.ui)
        return self.protocol

    def clientConnectionLost(self, connector, reason):
        self.lost = True
        self.log.print("和服务器的连接中断. 原因: %s" % (reason))

    def clientConnectionFailed(self, connector, reason):
        self.failed = True
        self.log.print("连接到服务器失败失败。 原因: %s" % (reason))

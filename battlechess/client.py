# -*- coding: utf-8 -*-

'''
@name: battlechess_server
@author: Memory
@date: 2019/11/15
@document: 皇家战棋游戏网络传输的客户端文件
'''

import json
from tkinter.messagebox import showinfo
from twisted.internet.protocol import Protocol, ClientFactory
from .utils import Logging
from .configs import CLIENT_LOG_PATH


class BCClientProtocol(Protocol):
    def __init__(self, factory, ui):
        self.factory = factory
        self.connected = False
        self.log = Logging(CLIENT_LOG_PATH)
        self.ui = ui

    def connectionMade(self):
        self.connected = True

    def connectionLost(self, reason):
        self.connected = False

    def dataReceived(self, data):
        data = json.loads(data.decode('utf-8'))

        if data['type'] in ['signin', 'signup']:
            self.user_login(data)
        else:
            self.factory.data = data

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
        self.data = None
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
        # answer = askyesno("无法连接服务器", "无法连接到服务器，是否进入离线模式？", default='yes')
        # if answer:
        #     self.ui.begin(True)
        # todo: 此处插入询问是否进入离线模式
        print("连接到服务器失败失败。 原因: %s" % (reason))

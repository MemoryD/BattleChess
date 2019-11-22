# -*- coding: utf-8 -*-

'''
@name: login
@author: Memory&Xinxin
@date: 2019/11/22
@document: 游戏的登录界面
'''

import os
import json
from twisted.internet import reactor, tksupport

import tkinter as tk
from tkinter import Tk, Entry, Button
from tkinter.ttk import Label
from tkinter.messagebox import showinfo, askyesno
from .configs import IMG_PATH
from .utils import install_game, dict2bin
from .game import BeginGame


class LoginUI(Tk):
    def __init__(self):
        Tk.__init__(self)
        self.factory = None
        self.width = 520
        self.height = 350
        self.title('皇家战棋用户登录')
        self.center_window(self.width, self.height)
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.set_ui()
        self.is_listen = True
        self.user = None

    def set_ui(self):
        global img_bg
        img_bg = tk.PhotoImage(file=os.path.join(IMG_PATH, 'login_bg.png'))
        label_bg = Label(self, image=img_bg)
        label_bg.place(x=-2, y=-2)

        global img_signup
        img_signup = tk.PhotoImage(file=os.path.join(IMG_PATH, 'button_signup.png'))
        button_signup = Button(self, bd=0, image=img_signup, bg='#606060',
                               activebackground='#606060', command=self.signup)
        button_signup.place(x=98, y=240)

        global img_signin
        img_signin = tk.PhotoImage(file=os.path.join(IMG_PATH, 'button_signin.png'))
        button_signin = Button(self, bd=0, image=img_signin, bg='#606060',
                               activebackground='#606060', command=self.signin)
        button_signin.place(x=275, y=240)

        self.entry_user = Entry(self, width=20, bd=0, background='#606060',
                                foreground='#eeeeee', font="Helvetica 16")
        self.entry_user.place(x=160, y=100, height=35)
        self.entry_pwsd = Entry(self, width=20, bd=0, background='#606060',
                                foreground='#eeeeee', font="Helvetica 16", show='*')
        self.entry_pwsd.place(x=160, y=173, height=35)

    def signup(self, event=None):
        if not self.factory.protocol or self.factory.failed:
            answer = askyesno("无法连接服务器", "无法连接到服务器，是否进入离线模式？", default='yes')
            if answer:
                self.begin(True)
            return
        name = self.entry_user.get()
        passwd = self.entry_pwsd.get()
        if not name or not passwd:
            showinfo('错误', '输入不完整。')
            return
        data = {'type': 'signup', 'user': {'name': name, 'passwd': passwd}}
        self.factory.protocol.transport.write(dict2bin(data))

    def signin(self, event=None):
        if not self.factory.protocol or self.factory.failed:
            answer = askyesno("无法连接服务器", "无法连接到服务器，是否进入离线模式？", default='yes')
            if answer:
                self.begin(True)
            return
        name = self.entry_user.get()
        passwd = self.entry_pwsd.get()
        if not name or not passwd:
            showinfo('错误', '输入不完整。')
            return
        data = {'type': 'signin', 'user': {'name': name, 'passwd': passwd}}
        self.factory.protocol.transport.write(dict2bin(data))

    def center_window(self, width, height):   # 窗口居中
        screenwidth = self.winfo_screenwidth()
        screenheight = self.winfo_screenheight()
        size = '%dx%d+%d+%d' % (width, height, (screenwidth - width)/2, (screenheight - height)/2)
        self.geometry(size)

    def on_close(self):
        tksupport.uninstall()
        self.destroy()
        self.quit()
        reactor.stop()

    def begin(self, offline):
        '''
        登录成功，进入游戏开始界面。
        '''
        self.is_listen = False
        b = BeginGame(self.factory, self.user, offline)
        tksupport.uninstall()
        install_game(b)
        self.destroy()
        self.quit()

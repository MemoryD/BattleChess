# -*- coding: utf-8 -*-

'''
@name: server
@author: Memory&Xinxin
@date: 2019/11/22
@document: 皇家战棋游戏的服务端文件
'''
import os
from twisted.internet.protocol import Protocol
from twisted.internet.protocol import Factory
from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.internet import reactor
from .utils import *
from .configs import SERVER_LOG_PATH, USERDB, DATABASE_PATH


class BCServerProtocol(Protocol):
    """docstring for BCServerProtocol"""
    def __init__(self, factory):
        # super(BCServerProtocol, self).__init__()
        self.factory = factory
        self.log = Logging(SERVER_LOG_PATH)
        self.parse = {'signin': self.signin,
                      'signup': self.signup,
                      'match': self.match,
                      'unmatch': self.unmatch,
                      'endgame': self.endgame}

    def connectionMade(self):
        '''
        建立连接时的动作。
        '''
        self.factory.connection_num += 1
        self.factory.id += 1
        self.id = self.factory.id
        self.user = None

    def connectionLost(self, reason):
        '''
        失去连接时的操作。
        '''
        self.factory.connection_num -= 1
        if not self.user:
            return
        self.log.print("用户 %s 失去了连接。" % self.user)
        qqmsg(self.user, '退出了游戏')
        # 如果有正在进行的游戏，则判定为输
        if self.user in self.factory.matched:
            data = {'type': 'giveup'}
            self.sendToMatched(dict2bin(data))
            v = self.cleangame()
            if v:
                self.log.print("因为 %s 掉线，%s 和 %s 的游戏结束!" % (self.user, self.user, v))
        elif self.user in self.factory.wait:
            self.factory.wait.remove(self.user)
            self.log.print("用户 %s 放弃了匹配。" % self.user)

        # 从客户池中删除
        self.factory.clients.pop(self.user)

    def dataReceived(self, _data):
        '''
        收到数据时的处理操作。
        '''
        # strdata = data.decode('utf-8')
        # jsons = strdata.replace('}{', '}}{{').split('}{')

        datas = spilt_data(_data)
        for data in datas:
            typ = data['type']
            if typ in self.parse:
                self.parse[typ](data)
            else:
                self.log.print('用户 %s 进行了游戏操作: %s' % (self.user, typ))
                self.sendToMatched(dict2bin(data))

    def signin(self, data):
        '''
        处理用户的登录请求。
        '''
        user = data['user']
        self.log.print('用户 %s 发起了登录请求。' % user['name'])
        if user['name'] in self.factory.clients:
            reply = {'type': 'signin', 'result': 'failed', 'reason': '该账号在其他地方已登录。'}
            self.transport.write(dict2bin(reply))
            self.log.print('用户 %s 登录失败。 因为： %s' % (user['name'], reply['reason']))
            return
        # 查询是否存在该用户
        sql = 'SELECT passwd FROM user WHERE name=?'
        value = (user['name'], )
        result = excuteSQL(sql, value)
        if result is None:      # 查询失败
            reply = {'type': 'signin', 'result': 'failed', 'reason': '系统出了一点问题。'}
        elif result == []:      # 查不到用户
            reply = {'type': 'signin', 'result': 'failed', 'reason': '用户名 %s 不存在。' % (user['name'])}
        elif result[0][0] != user['passwd']:    # 密码不匹配
            reply = {'type': 'signin', 'result': 'failed', 'reason': '密码错误。'}
        else:                   # 登录成功
            reply = {'type': 'signin', 'user': get_user(user['name']), 'result': 'success'}
            qqmsg(user['name'], '登录了游戏')
            # 添加到用户池
            self.factory.clients[user['name']] = self
            self.user = user['name']
        # 打印日志
        if reply['result'] == 'failed':
            self.log.print('用户 %s 登录失败。 因为： %s' % (user['name'], reply['reason']))
        else:
            self.log.print('用户 %s 登录成功。' % user['name'])
        # 将结果发送给用户
        self.transport.write(dict2bin(reply))

    def signup(self, data):
        '''
        处理用户的注册请求。
        '''
        user = data['user']
        self.log.print('用户 %s 请求注册。' % user['name'])
        # 查询是否存在同名的用户
        sql = 'SELECT * FROM user WHERE name=?'
        value = (user['name'], )
        result = excuteSQL(sql, value)
        if result is None:      # 查询失败
            reply = {'type': 'signup', 'result': 'failed', 'reason': '服务器出了一点问题。'}
        elif result == []:      # 查询成功，无同名用户
            # 将新用户添加到数据库
            sql = 'INSERT INTO user(name, passwd, credit, title) VALUES(?, ?, ?, ?)'
            value = (user['name'], user['passwd'], 0, '平民')
            if excuteSQL(sql, value) is not None:       # 插入成功，即注册成功
                reply = {'type': 'signup', 'name': user['name'], 'result': 'success'}
                qqmsg(user['name'], '注册成为了新用户')
            else:
                reply = {'type': 'signup', 'result': 'failed', 'reason': '服务器出了一点问题。'}
        else:
            reply = {'type': 'signup', 'result': 'failed', 'reason': '用户名 %s 已被注册。' % (user['name'])}
        # 打印日志
        if reply['result'] == 'failed':
            self.log.print('用户 %s 注册失败。 因为： %s' % (user['name'], reply['reason']))
        else:
            self.log.print('用户 %s 注册成功。' % user['name'])
        # 将结果发送给用户
        self.transport.write(dict2bin(reply))

    def match(self, user):
        '''
        用户请求匹配对手时，查看是否有等待的用户，如果有，就配对，如果没有，就等待。
        '''
        self.log.print('用户 %s 请求匹配游戏对手。' % user['name'])
        qqmsg(user['name'], '请求匹配游戏对手')
        if user['name'] not in self.factory.wait:
            self.factory.wait.append(user['name'])

        if len(self.factory.wait) < 2:
            # self.factory.wait = user['name']
            self.log.print('用户 %s 正在等待匹配。' % user['name'])
        else:
            you = self.factory.wait[0]
            me = self.factory.wait[1]
            self.factory.matched[me] = you
            self.factory.matched[you] = me
            self.factory.wait.remove(me)
            self.factory.wait.remove(you)
            self.log.print('用户 %s 和 用户 %s 匹配成功。' % (me, you))
            qqmsg('%s 和 %s' % (me, you), '匹配成功')

            chess = random_chess()
            my_user = get_user(me)
            your_user = get_user(you)
            data1 = {'type': 'init', 'chess': chess, 'turn': 'red', 'color': 'red', 'me': my_user, 'you': your_user}
            data2 = {'type': 'init', 'chess': chess, 'turn': 'red', 'color': 'blue', 'me': your_user, 'you': my_user}
            self.transport.write(dict2bin(data1))
            self.sendToMatched(dict2bin(data2))

    def unmatch(self, user):
        '''
        用户取消请求匹配对手时的操作。
        '''
        if user['name'] in self.factory.wait:
            self.factory.wait.remove(user['name'])
            self.log.print("用户 %s 放弃了匹配。" % user['name'])
            qqmsg(user['name'], '放弃了匹配')

    def sendToMatched(self, data):
        '''
        在游戏过程中，将游戏的数据包发送给对手
        '''
        if self.user in self.factory.matched:
            toid = self.factory.matched[self.user]
            to = self.factory.clients[toid]
            to.transport.write(data)

    def cleangame(self):
        if self.user in self.factory.matched:
            v = self.factory.matched[self.user]
            self.factory.matched.pop(self.user)
            if v in self.factory.matched:
                self.factory.matched.pop(v)
            return v

    def endgame(self, data):
        '''
        一局游戏结束时，玩家发送'endgame'数据包，服务端更新用户积分
        '''
        v = self.cleangame()
        if v:
            self.log.print('%s 和 %s 的游戏正常结束。' % (self.user, v))
            qqmsg('%s 和 %s' % (self.user, v), '的游戏结束')
        user = data['user']
        if not user:
            return
        self.log.print('更新用户数据：', user)
        sql = 'UPDATE user SET credit=?, title=? WHERE name=?'
        value = (user['credit'], user['title'], user['name'])
        excuteSQL(sql, value)


class BCServerFactory(Factory):
    """docstring for BCServerFactory"""
    def __init__(self):
        self.connection_num = 0
        self.id = 0
        self.clients = {}
        self.matched = {}
        self.wait = []
        self.log = Logging(SERVER_LOG_PATH)
        self.log.print('启动服务器。')

    def buildProtocol(self, addr):
        return BCServerProtocol(self)


def runserver(port):
    endpoint = TCP4ServerEndpoint(reactor, 1122)
    endpoint.listen(BCServerFactory())
    reactor.run()


def createDatabase():
    if not os.path.exists(USERDB):
        if not os.path.exists(DATABASE_PATH):
            os.makedirs(DATABASE_PATH)
        sql = '''
                CREATE TABLE USER
                (
                NAME VARCHAR(20) PRIMARY KEY,
                PASSWD VARCHAR(20) NOT NULL,
                CREDIT INT NOT NULL,
                TITLE VARCHAR(8)
                );
                '''
        excuteSQL(sql)
        sql = 'INSERT INTO USER(NAME, PASSWD, CREDIT, TITLE) VALUES("xinxin", "2333", 1095, "小城主")'
        excuteSQL(sql)
        sql = 'INSERT INTO USER(NAME, PASSWD, CREDIT, TITLE) VALUES("memory", "2333", 1095, "小城主")'
        excuteSQL(sql)


if __name__ == '__main__':
    createDatabase()
    runserver(1122)

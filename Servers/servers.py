from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.server import SimpleXMLRPCRequestHandler
import os
import base64
import argparse
import threading
import time
import sys
from logger import Logger
import ctypes

BASE_PORT = 25000
CALL_MSG = '<<server id:%s\tcall function %s>>'
SERVER_DIR = os.getcwd() + '/' + 'Servers/ServerFiles/'
# key: filename value: -1,write; 0,nolock; n>0, read
LOCK = {}

def serverFiles():
    return [f for f in os.listdir(SERVER_DIR) if os.path.isfile(os.path.join(SERVER_DIR, f))]

def printCall(id, function_name):
    print(CALL_MSG % (id, function_name))

def getFilePath(filename):
    return os.path.join(SERVER_DIR, filename)

def getFileContent(filename):
    file_path = getFilePath(filename)
    with open(file_path, 'rb') as f:
        file_content = f.read()
    file_content = base64.b64encode(file_content).decode('utf8')
    return file_content

class RPCServer():
    def __init__(self, id, server_num) -> None:
        self.users = {}
        self.id = id
        self.server_num = server_num
        self.loadUsers()

    # 提供给代理服务器的接口
    def getServerNum(self):
        printCall(self.id, 'get_server_num')
        return self.server_num

    def loadUsers(self):
        '''加载用户'''
        #print('users:')
        with open(os.getcwd() + '/Servers/user.txt') as f:
            for line in f:
                username, password = line.strip().split(' ')
                #print(f'username: {username}, password: {password}')
                self.users[username] = password

    def authentication(self, username, password):
        '''验证登录用户'''
        printCall(self.id, 'authentication')
        state = False
        if username not in list(self.users.keys()):
            msg = 'user not exists'
        elif self.users[username] == password:
            msg = 'login'
            state = True
        else:
            msg = 'password wrong'
        return state, msg

    def ls(self):
        printCall(self.id, 'ls')
        return serverFiles()

    def lock(self):
        printCall(self.id, 'lock')
        return LOCK

    def createFile(self, filename):
        printCall(self.id, 'createFile')
        if filename in serverFiles():
            return 'file already exists'
        else:
            file_path = getFilePath(filename)
            with open(file_path, 'w') as file:
                pass
            return f'file {filename} create successfully'

    def deleteFile(self, filename):
        printCall(self.id, 'deleteFile')
        if filename not in serverFiles():
            return 'file not exist'
        elif filename in list(LOCK.keys()) and LOCK[filename] != 0:
            return 'file is reading/writing by others'
        else:
            file_path = getFilePath(filename)
            os.remove(file_path)
            return f'file {filename} deleted successfully'

    def setLock(self, filename, mode):
        printCall(self.id, 'setLock')
        setState = False
        msg = ''
        if filename not in serverFiles():
            msg = filename + ' not exist'
        # 检查锁冲突
        elif filename in list(LOCK.keys()) and LOCK[filename] != 0: 
            # 都为共享锁
            if LOCK[filename] > 0 and mode == 'read':
                LOCK[filename] += 1
                setState = True
            # 已有写锁, mode为读或写
            elif LOCK[filename] < 0:
                msg = filename + ' is writing by others'
            # 已有共享锁, mode为写
            elif LOCK[filename] > 0 and mode == 'write':
                msg = filename +' is reading by others'
        # 没有锁, 直接获取锁
        else:
            LOCK[filename] = 1 if mode == 'read' else -1
            setState = True
        
        return setState, msg

    def openFile(self, filename, mode):
        printCall(self.id, 'openFile')
        state, msg = self.setLock(filename, mode)
        if state:
            file_content = getFileContent(filename)
            return True, file_content
        else:
            return False, msg

    # 关闭读文件, LOCK对应值减1
    def closeFile(self, filename):
        printCall(self.id, 'closeFile')
        LOCK[filename] -= 1
        return True
    
    # 结束写文件, LOCK设为0
    def writeFile(self, filename, content):
        printCall(self.id, 'writeFile')
        LOCK[filename] = 0
        content = base64.b64decode(content)
        with open(getFilePath(filename), 'wb') as f:
            f.write(content)
        return True

# 服务器线程, 实现ctrl+c 能够退出程序
class MyServerThread(threading.Thread):
    def __init__(self, server, group=None, target=None, name=None, args=(), kwargs=None, *, daemon=None) -> None:
        super().__init__(group, target, name, args, kwargs, daemon=daemon)
        self.server = server
    
    def run(self):
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            pass

if __name__ == '__main__':
    # 窗口命名
    ctypes.windll.kernel32.SetConsoleTitleW("Server")
    parser = argparse.ArgumentParser()
    parser.add_argument('--n', type=int, default=2)
    args = vars(parser.parse_args())
    server_num = args['n']
    threads = []
    servers = []

    sys.stdout = Logger(f"Servers/log/server.log", sys.stdout)

    for i in range(server_num):
        server = SimpleXMLRPCServer(('localhost', BASE_PORT + i), requestHandler=SimpleXMLRPCRequestHandler)
        server.register_instance(RPCServer(i, server_num))
        print(f'XML-RPC server id={i} listening on port {BASE_PORT+i}')
        thread = MyServerThread(server=server)
        thread.start()

        servers.append(server)
        threads.append(thread)

    try: 
        while True:
            time.sleep(1)
    # 退出
    except KeyboardInterrupt:
        print('main thread received KeyboardInterrupt')
        for i in range(server_num):
            servers[i].shutdown()
            threads[i].join()

        sys.exit(0)

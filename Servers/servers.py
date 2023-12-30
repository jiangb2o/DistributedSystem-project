from xmlrpc.server import SimpleXMLRPCServer
from socketserver import ThreadingMixIn
import os
import base64

CALL_MSG = '<<call function %s>>'
SERVER_DIR = os.getcwd() + '/' + 'Servers/ServerFiles/'
# key: filename value: -1,write; 0,nolock; n>0, read
LOCK = {}

class ThreadXMLRPCServer(ThreadingMixIn, SimpleXMLRPCServer):
    pass

def serverFiles():
    return [f for f in os.listdir(SERVER_DIR) if os.path.isfile(os.path.join(SERVER_DIR, f))]

def printCall(function_name):
    print(CALL_MSG % function_name)

def getFilePath(filename):
    return os.path.join(SERVER_DIR, filename)

def getFileContent(filename):
    file_path = getFilePath(filename)
    with open(file_path, 'rb') as f:
        file_content = f.read()
    file_content = base64.b64encode(file_content).decode('utf8')
    return file_content

class RPCServer():
    def __init__(self) -> None:
        self.users = {}
        self.loadUsers()

    def loadUsers(self):
        '''加载用户'''
        print('users:')
        with open(os.getcwd() + '/Servers/user.txt') as f:
            for line in f:
                username, password = line.strip().split(' ')
                print(f'username: {username}, password: {password}')
                self.users[username] = password

    def authentication(self, username, password):
        '''验证登录用户'''
        state = False
        if username not in list(self.users.keys()):
            msg = 'user not exists'
        elif self.users[username] == password:
            msg = 'login'
            state = True
        else:
            msg = 'password wrong'
        return msg, state

    def ls(self):
        printCall('ls')
        return serverFiles()

    def lock(self):
        printCall('lock')
        return LOCK

    def createFile(self, filename):
        printCall('createFile')
        if filename in serverFiles():
            return 'file already exists'
        else:
            file_path = getFilePath(filename)
            with open(file_path, 'w') as file:
                pass
            return f'file {filename} create successfully'

    def deleteFile(self, filename):
        printCall('deleteFile')
        if filename not in serverFiles():
            return 'file not exist'
        else:
            file_path = getFilePath(filename)
            os.remove(file_path)
            return f'file {filename} deleted successfully'

    def setLock(self, filename, mode):
        printCall('setLock')
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
        printCall('openFile')
        state, msg = self.setLock(filename, mode)
        if state:
            file_content = getFileContent(filename)
            return True, file_content
        else:
            return False, msg

    # 关闭读文件, LOCK对应值减1
    def closeFile(self, filename):
        printCall('closeFile')
        LOCK[filename] -= 1
        return True
    
    # 结束写文件, LOCK设为0
    def writeFile(self, filename, content):
        printCall('writeFile')
        LOCK[filename] = 0
        content = base64.b64decode(content)
        with open(getFilePath(filename), 'wb') as f:
            f.write(content)
        return True

if __name__ == '__main__':
    proxy = RPCServer()
    server = SimpleXMLRPCServer(('localhost', 25000))
    # 注册实例
    server.register_instance(proxy)
    print('XML-RPC server listening on port 25000')
    server.serve_forever()
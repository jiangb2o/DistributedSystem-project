from xmlrpc.server import SimpleXMLRPCServer
from socketserver import ThreadingMixIn
import xmlrpc.client
import random
import sys
from logger import Logger

class ThreadXMLRPCServer(ThreadingMixIn, SimpleXMLRPCServer):
    pass

# 客户端代理, 连接到基端口, 为客户端分配连接到的服务器id
class RPCProxy():
    BASE_PORT = 25000
    def __init__(self) -> None:
        self.proxy = xmlrpc.client.ServerProxy(f'http://localhost:{self.BASE_PORT}')
    
    def getBasePort(self):
        return self.BASE_PORT

    def allocate(self, username, password):
        state, msg = self.proxy.authentication(username, password)
        if state:
            id = random.randint(0, self.proxy.getServerNum() - 1)
            print(id)
            print(f'allocate server {id} to user {username}')
            msg = id

        return state, msg
    
if __name__ == '__main__':
    proxy = RPCProxy()
    server = SimpleXMLRPCServer(('localhost', 8888))
    sys.stdout = Logger(f"Servers/log/proxy.log", sys.stdout)
    # 注册实例
    server.register_instance(proxy)
    print('proxy server listening on port 8888')
    server.serve_forever()
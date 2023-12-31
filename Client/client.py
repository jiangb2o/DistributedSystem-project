import os
import argparse
import xmlrpc.client
import base64
import shutil
import ctypes

PROXY_PORT = 8888

def create_folder_if_not_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"floder '{path}' created")

def remove_floder_if_exists(path):
    if os.path.exists(path):
        os.rmdir(path)
        print(f'floder "{path}" removed')

class RPCClient():
    BUFFER_SIZE = 5     # 缓存文件最大数量
    # command
    command_dir = {}
    command_dir['ls']           = '查看服务器目录的文件'
    command_dir['lock']         = '查看文件锁情况'
    command_dir['create %s']    = '在服务器创建文件'
    command_dir['delete %s']    = '删除服务器文件'
    command_dir['read %s']      = '读取服务器文件'
    command_dir['write %s']     = '写服务器文件'
    command_dir['close %s']     = '关闭读取的文件'
    command_dir['upload %s']    = '上传写完的文件'

    def __init__(self, username, password, user_dir) -> None:
        self.username = username
        self.password = password
        self.dir = user_dir
        self.buffer_dir = user_dir + 'buffer/'
        self.read_dir = user_dir + 'read/'
        self.write_dir = user_dir + 'write/'
        self.proxy = xmlrpc.client.ServerProxy(f'http://localhost:8888')
        self.is_running = True
        self.getServerFromProxy()

    def getServerFromProxy(self):
        '''申请从代理服务器获得一个可用的服务器'''
        state, msg = self.proxy.allocate(self.username, self.password)
        if state:
            self.server_port = self.proxy.getBasePort() + msg
            print('---------------------------------------------')
            print(f'USER: {self.username}\nCONNECT TO SERVER <{msg}> SUCCESSFULLY!\nWELCOM TO DISTRIBUTED FILE SYSTEM!')
            print('---------------------------------------------')
            # 若不存在则创建用户目录
            create_folder_if_not_exists(self.dir)
            self.run()
        else:
            print(msg)

    def getFileContent(self, path):
        with open(path, 'rb') as f:
            file_content = f.read()
        file_content = base64.b64encode(file_content).decode('utf8')
        return file_content

    def run(self):
        '''连接目标服务器, 循环等待用户指令'''
        self.proxy = xmlrpc.client.ServerProxy(f'http://localhost:{self.server_port}')
        # 已缓存, 正在read/write 的文件
        self.buffer_files = {}
        self.read_files = []
        self.write_files = []
        # 创建文件目录
        create_folder_if_not_exists(self.buffer_dir)
        create_folder_if_not_exists(self.write_dir)
        create_folder_if_not_exists(self.read_dir)
        print('input command("exit": close client, "help" look commands format)')
        while(self.is_running):
            user_input = input(f'Client@{self.username}> ')
            user_input = user_input.lower()
            try:
                command, filename = user_input.split()
            except:
                command = user_input
            try:
                if command == 'exit':
                    self.exit()
                elif command == 'help':
                    self.help()
                elif command == 'ls':
                    self.ls()
                elif command == 'lock':
                    self.lock()
                elif command == 'create':
                    self.create(filename)
                elif command == 'delete':
                    self.delete(filename)
                elif command == 'read':
                    self.read(filename)
                elif command == 'write':
                    self.write(filename)
                elif command == 'close':
                    self.close(filename)
                elif command == 'upload':
                    self.upload(filename)
                else:
                    print(f'not exists command "{command}"')
            except:
                self.exit()

    def help(self):
        help_header = 'command: %s\nfunction: %s\n'
        for k,v in self.command_dir.items():
            if k == 'ls' or k == 'lock':
                print(help_header % (k, v))
            else:
                print(help_header % (k % 'filename', v))

    def ls(self):
        files = self.proxy.ls()
        print('Files in server directory:')
        for file in files:
            print(file)

    def lock(self):
        print(self.proxy.lock())

    def create(self, filename):
        msg = self.proxy.createFile(filename)
        print(msg)

    def delete(self, filename):
        msg = self.proxy.deleteFile(filename)
        print(msg)

    def read(self, filename):
        if filename in self.read_files:
            return
        
        state = self.openfile(filename, 'read')
        if state:
            # 直接将缓存的文件复制客户端目录
            shutil.copy(self.buffer_dir + filename, self.read_dir + filename)
            self.read_files.append(filename)

    # read 结束
    def close(self, filename):
        try:
            os.remove(self.read_dir + filename)
            self.proxy.closeFile(filename)
            self.read_files.remove(filename)
        except ValueError:
            pass
        except FileNotFoundError:
            pass

    def write(self, filename):
        if filename in self.write_files:
            return
        # 已有共享锁
        if filename in self.read_files:
            # 先释放共享锁
            self.close(filename)
        
        state = self.openfile(filename, 'write')
        if state:
            shutil.copy(self.buffer_dir + filename, self.write_dir + filename)
            self.write_files.append(filename)

    # write 结束后upload
    def upload(self, filename):
        try:
            self.write_files.remove(filename)
            file_content = self.getFileContent(self.write_dir + filename)
            self.proxy.writeFile(filename, file_content)
            # 写完后本地buffer也更新
            if filename in self.buffer_files:
                shutil.copy(self.write_dir + filename, self.buffer_dir + filename)
            os.remove(self.write_dir + filename)
        except ValueError:
            pass
        except FileNotFoundError:
            pass

    def openfile(self, filename, mode):
        # 要打开新的文件, 检查buffer是否已满
        self.checkBuffer()
        state, content = self.proxy.openFile(filename, mode)
        # 不在buffer中要重新读数据
        if state and filename not in list(self.buffer_files.keys()):
            content = base64.b64decode(content)
            with open(os.path.join(self.buffer_dir, filename), 'wb') as f:
                f.write(content)
            self.buffer_files[filename] = mode  # buff 文件包含状态
        # 在buffer中, 返回
        elif state and filename in list(self.buffer_files.keys()):
            pass
        else:
            print(f'failed msg: {content}')
        return state

    def checkBuffer(self):
        # 缓存已满
        while len(self.buffer_files) >= self.BUFFER_SIZE:
            remove_file = input(f'buffer if full, enter the file you want to remove:\n{list(self.buffer_files.keys())}\n')
            if remove_file in list(self.buffer_files.keys()):
                try:
                    # 删除缓存中的文件以及open_files中的键值
                    os.remove(self.buffer_dir + remove_file)
                    print(f'remove file "{remove_file}" from buffer')
                    del self.buffer_files[remove_file]
                except FileNotFoundError:
                    print(f'not find "{remove_file}" in buffer')
            else:
                print(f'not find "{remove_file}" in buffer')

    def deleteBuffer(self):
        # 直接根据buffer文件夹下文件进行删除
        buffer_files = [f for f in os.listdir(self.buffer_dir) if os.path.isfile(os.path.join(self.buffer_dir, f))]
        for f in buffer_files:
            try:
                os.remove(self.buffer_dir + f)
                del self.buffer_files[f]
                print(f'remove file "{f}" from buffer')
            except FileNotFoundError:
                print(f'not find "{f}" in buffer')
            except KeyError:
                pass

    def closeRead(self):
        # 直接根据read文件夹下文件进行删除
        read_files = [f for f in os.listdir(self.read_dir) if os.path.isfile(os.path.join(self.read_dir, f))]
        for f in read_files:
            print(f'close file {f}')
            self.close(f)

    def uploadWrite(self):
        # 直接根据write文件夹下文件进行上传
        write_files = [f for f in os.listdir(self.write_dir) if os.path.isfile(os.path.join(self.write_dir, f))]
        for f in write_files:
            print(f'upload file {f}')
            self.upload(f)

    def exit(self):
        self.is_running = False
        # 删除所有缓存
        self.deleteBuffer()
        # 关闭所有读文件
        self.closeRead()
        # 处理所有写文件
        self.uploadWrite()
        # 删除buffer, read, write 目录
        remove_floder_if_exists(self.buffer_dir)
        remove_floder_if_exists(self.read_dir)
        remove_floder_if_exists(self.write_dir)

def main(username, password):
    current_dir = os.getcwd()
    client_dir = f'{current_dir}/Client/ClientFiles'
    user_dir = f'{client_dir}/{username}/'
    # 客户端目录
    create_folder_if_not_exists(client_dir)
    RPCClient(username, password, user_dir)


if __name__ == "__main__": 
    parser = argparse.ArgumentParser()
    parser.add_argument('--username', type=str, default='test')
    parser.add_argument('--password', type=str, default='test')
    args = vars(parser.parse_args())
    username = args['username']
    password = args['password']
    ctypes.windll.kernel32.SetConsoleTitleW(f"Client {username}")
    print('connect to server...')
    main(username, password)
    input('Press any key to close window...')
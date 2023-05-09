import logging
from nodes.message import Message
import socket
from threading import Thread
import pickle
from timeit import default_timer as timer
from nodes.threshold import Party, Params, ThresholdPaillierPubKey


class Node:
    cnt = 0

    def __init__(self, addr: str, node_addr_list: []):
        # 节点信息
        Node.cnt += 1
        self.id = Node.cnt
        self.addr = addr
        self.peer_addr_list = node_addr_list
        self.start_time = timer()
        if addr in self.peer_addr_list:
            self.peer_addr_list.remove(addr)

        # 运行状态
        self.isRunning = False

    def initialize(self, params, dealer, index):
        self.party = Party(params, dealer, index)

    def to_string(self) -> str:
        return "Node-%02d, addr=%s, isRunning=%d" % (self.id, self.addr, self.isRunning)

    def start_server(self):
        server_socket = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM)  # 创建服务端
        # 设置端口复用
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        logging.debug(self.addr)
        host, port = self.addr.split(":")
        port = int(port)  # 设置端口
        server_socket.bind((host, port))  # 绑定IP和Port
        # TODO Exception: 远程主机强迫关闭了一个现有的连接
        server_socket.listen(len(self.peer_addr_list) *
                             3)  # 代办事件中排队等待connect的最大数目

        self.isRunning = True
        while self.isRunning:
            client_socket, client_addr = server_socket.accept()
            # 创建线程为客户端服务
            Thread(target=self.handle_message, args=(
                client_socket, client_addr)).start()

        server_socket.close()

    def stop_server(self):
        self.isRunning = False

    def handle_message(self, client_socket: socket, client_addr: str):
        data = client_socket.recv(1024)

        msg = pickle.loads(data)
        if not isinstance(msg, Message):
            print("maybe some error occurred socket from:", client_addr)
            return
        # self.parse_message(msg)
        sender_index = msg.sender_index
        msg_data = msg.data
        ret = self.handle_function(msg_data)
        client_socket.send(pickle.dumps(Message(self.party.index,sender_index,{"function":msg_data["function"],"ret":ret})))
        client_socket.close()  # 关闭连接

    def parse_message(self, msg: Message):
        string = "Time cost: %.17fs" % (timer() - self.start_time)
        # "stage 3 cost: %.17f" % (timer() - self.cost_time)
        print(string)
        pass

    def send_message(self, addr: str, msg: Message):
        ip, port = addr.split(":")
        port = int(port)
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        try:
            client_socket.connect((ip, port))
            client_socket.send(pickle.dumps(msg))

            self.handle_funcresult(pickle.loads(client_socket.recv(1024)))

            client_socket.close()
        except BaseException as e:
            string = str(e) + " || target addr: " + ip + ":" + \
                         str(port) + " || " + str(msg.data)
            print(string)


    def handle_function(self,msg_data):
        function = msg_data["function"]
        args = msg_data["args"]

        if (function == "test"):
            ret = self.party.test(*args)
        elif(function=="initial_decrypt"):
            ret = self.party.initial_decrypt(*args)
        elif(function=="initial_encrypt"):
            ret = self.party.initial_encrypt(*args)
        elif(function=="share_decrypt"):
            ret = self.party.share_decrypt(*args)

        return ret
    
    def handle_funcresult(self,msg_ret):
        sender_index = msg_ret.sender_index
        funcresult = msg_ret.data
        function = funcresult["function"]
        ret = funcresult["ret"]
        if(function=="initial_encrypt"):
            pass
        elif(function=="initial_decrypt"):
            self.party.Lie[sender_index]=ret
        elif(function=="share_decrypt"):
            self.party.c[sender_index]=ret

    


def broadcast_message(addr_list: [], msg: Message):
    thread_list = []
    for addr in addr_list:
        thread_list.append(Thread(target=send_message, args=(addr, msg)))

    for thread in thread_list:
        thread.start()  # 开启线程


def broadcast_message_list(addr_list: [], msg_list: []):
    if len(addr_list) != len(msg_list):
        raise Exception("The number of messages to be sent is incorrect")
    i = 0
    thread_list = []
    while i < len(addr_list):
        thread_list.append(Thread(target=send_message, args=(addr_list[i], msg_list[i])))  # 创建线程为客户端服务
        i += 1

    for thread in thread_list:
        thread.start()  # 开启线程


def send_message(addr: str, msg: Message):
    ip, port = addr.split(":")
    port = int(port)
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
    try:
        client_socket.connect((ip, port))
        client_socket.send(pickle.dumps(msg))
        client_socket.close()
    except BaseException as e:
        string = str(e) + " || target addr: " + ip + ":" + str(port) + " || " + str(msg.data)
        print(string)

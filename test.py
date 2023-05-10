import logging
import time
from threading import Thread
from nodes.node import Node
from nodes.message import Message
from nodes.threshold import genThresholdPaillierKeypair

committee_addr_list = ["127.0.0.1:4"+"0"*(3-len(str(i)))+str(i) for i in range(140)]

def generate_nodes(num):
    node_list = []
    for i in range(num):
        node_list.append(
            Node(committee_addr_list[i], committee_addr_list[:num]))
    return node_list


def dic2list(dic):
    l = []
    for key in dic:
        l.append((key, dic[key]))
    l.sort(key=lambda elem: elem[0])
    l = [i[1] for i in l]
    return l

def wait2die(thread_list):
    flag = 1
    while flag:
        flag = 0
        for i in thread_list:
            if i.is_alive():
                flag += 1

def send_call(sender, party_list, func, args):
    # 调用节点函数
    # sender 为发送者节点
    # party_list 为接收者节点编号组成的列表
    # func 为调用的函数名
    # args 为调用参数，以元组的形式存放，如果仅有一个参数形式为 (arg,)
    sender_node = node_list[sender-1]
    thread_list = []
    for i in party_list:
        reveive_node = node_list[i-1]
        thread_list.append(
            Thread(target=sender_node.send_message,
                   args=(reveive_node.addr,
                         Message(sender_node.party.index,
                                 reveive_node.party.index,
                                 {"function": func, "args": args})),
                   daemon=True))
    for thread in thread_list:
        thread.start()
    wait2die(thread_list)


def start(n, t, e, party_list):
    params, pubKey, priKey = genThresholdPaillierKeypair(n, t)

    global node_list
    node_list = generate_nodes(n)
    for i in range(len(node_list)):
        node_list[i].initialize(params, pubKey, i+1)
    for _node in node_list:
        Thread(target=_node.start_server, daemon=True).start()
    dealer_node = Node(committee_addr_list[i], committee_addr_list)  #dealer_node 暂时没用到
    node_list[i].initialize(params, pubKey, 0)
    Thread(target=dealer_node.start_server, daemon=True).start()
    incoming_node = node_list[e-1]

    # dealer 计算 fi
    flist = [0]*(t+1)
    for i in range(t+1):
        flist[i] = priKey.eval(i+1)

    # 托管加密阶段 initial_encrypt
    start = time.time()
    for i in party_list:
        send_call(e, [i], "initial_encrypt", (flist[i-1],))
    end = time.time()
    print("initial_encrypt_time:",end-start)

    # 份额初步解密阶段 initial_decrypt
    start = time.time()
    send_call(e,party_list,"initial_decrypt",(e, party_list))
    end = time.time()
    print("initial_decrypt_time:",end-start)

    # 份额重构阶段 combine_share
    Lie_list = dic2list(incoming_node.party.Lie)
    start = time.time()
    Le = incoming_node.party.combine_share(Lie_list)
    # end = time.time()
    # print("combine_share_time:",end-start)

    # # 门限 Paillier 解密阶段 share_decrypt
    # start = time.time()
    send_call(e,party_list,"share_decrypt",(Le,))
    end = time.time()
    print("share_decrypt:",end-start)

    # 新份额提取阶段 share_extract
    ci_list = dic2list(incoming_node.party.c)
    start = time.time()
    fe = incoming_node.party.share_extract(ci_list, party_list)
    end = time.time()
    print("share_extract:",end-start)
    print(fe)
    print(priKey.eval(e) % pubKey.module)

    for i in node_list:
        print(i.party.time)

    for _node in node_list:
        _node.stop_server()

node_list = []
if __name__ == '__main__':
    n = 128
    t = 126
    e = n
    # 节点编号从 1 开始，到 n 结束
    # t+1 为委员会成员数量，默认为前 t+1 个节点
    # e 为新加入成员的编号，默认为最后一个节点，即为 n
    # 最后一个参数为委员会成员编号组成的列表，默认为 [1,2,...,t+1]
    start(n, t, e,list(range(1,t+2)))

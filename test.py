import logging
import time
from threading import Thread, activeCount
from nodes.node import Node, broadcast_message, send_message
from nodes.message import Message
from nodes.threshold import genThresholdPaillierKeypair

committee_addr_list = [
    "127.0.0.1:4001",
    "127.0.0.1:4002",
    "127.0.0.1:4003",
    "127.0.0.1:4004",
    "127.0.0.1:4005",
    "127.0.0.1:4006",
    "127.0.0.1:4007",
    "127.0.0.1:4008",
    "127.0.0.1:4009",
    "127.0.0.1:4010",
    "127.0.0.1:4011",
    "127.0.0.1:4012",
    "127.0.0.1:4013",
    "127.0.0.1:4014",
    "127.0.0.1:4015",
]


def generate_nodes(num):
    committee_list = []
    for i in range(num):
        committee_list.append(
            Node(committee_addr_list[i], committee_addr_list[:num]))
    return committee_list


def dic2list(dic):
    l = []
    for key in dic:
        l.append((key,dic[key]))
    l.sort(key=lambda elem: elem[0])
    l = [i[1] for i in l]
    return l

def start(node_num: int):
    print("n = {}".format(node_num))
    if node_num > len(committee_addr_list):
        logging.error("too much nodes")
        return
    if node_num < 5:
        print(committee_addr_list[:node_num])
    else:
        print("committee: [{} ~ {}]".format(
            committee_addr_list[0], committee_addr_list[node_num - 1]))

    # 创建委员会
    committee_list = generate_nodes(node_num)
    for _node in committee_list:
        Thread(target=_node.start_server, daemon=True).start()

    time.sleep(2)

    for _node in committee_list:
        while not _node.isRunning:
            pass
    print("================ All nodes are online now ==================")

    return committee_list

    # thread_list = []
    # for node in committee_list:
    #     thread_list.append(
    #         Thread(target=broadcast_message, args=(node.peer_addr_list, Message("node", "node", {"a": 123})),
    #                daemon=True))
    # for thread in thread_list:
    #     thread.start()

    # for _node in committee_list:
    #     _node.stop_server()
    print("================ All nodes are shutdown now =================")


if __name__ == '__main__':
    # committee_list = start(15)
    # node = committee_list[0]
    # new_node = committee_list[-1]
    # new_node.send_message(node.addr,Message("node","node",{"function":"test","args":123}))

    # for _node in committee_list:
    #     _node.stop_server()
    n = 10
    t = n-2
    e = n

    params, pubKey, priKey = genThresholdPaillierKeypair(n, t)
    flist = [0]*(t+1)
    for i in range(t+1):
        flist[i] = priKey.eval(i+1)

    committee_list = generate_nodes(n)
    for i in range(len(committee_list)):
        committee_list[i].initialize(params, pubKey, i+1)

    for _node in committee_list:
        Thread(target=_node.start_server, daemon=True).start()

    new_node = committee_list[-1]

    thread_list = []
    for i in range(len(committee_list[:n-1])):
        cur_node = committee_list[i]
        thread_list.append(
            Thread(target=new_node.send_message, args=(cur_node.addr, Message(new_node.party.index, cur_node.party.index, {"function": "initial_encrypt", "args": (flist[i],)})), daemon=True))
    for thread in thread_list:
        thread.start()
    flag = 1
    while flag:
        flag = 0
        for i in thread_list:
            if i.is_alive():
                flag += 1

    thread_list = []
    for index in new_node.party.CN:
        cn_tuple = new_node.party.CN[index]
        CNa = cn_tuple[0]
        CNb = cn_tuple[1]
        cur_node = committee_list[index-1]
        thread_list.append(
            Thread(target=new_node.send_message, args=(cur_node.addr, Message(new_node.party.index, cur_node.party.index, {"function": "initial_decrypt", "args": (CNa, CNb, e, list(range(1, n)))})), daemon=True))
    for thread in thread_list:
        thread.start()
    flag = 1
    while flag:
        flag = 0
        for i in thread_list:
            if i.is_alive():
                flag += 1

    Lie_list = dic2list(new_node.party.Lie)
    Le = new_node.party.combine_share(Lie_list)

    thread_list = []
    for i in range(len(committee_list[:n-1])):
        cur_node = committee_list[i]
        thread_list.append(
            Thread(target=new_node.send_message, args=(cur_node.addr, Message(new_node.party.index, cur_node.party.index, {"function": "share_decrypt", "args": (Le,)})), daemon=True))
    for thread in thread_list:
        thread.start()
    flag = 1
    while flag:
        flag = 0
        for i in thread_list:
            if i.is_alive():
                flag += 1

    # print(new_node.party.c)
    ci_list = dic2list(new_node.party.c)
    fe = new_node.party.share_extract(ci_list, list(range(1, n)))
    print(fe)
    print(priKey.eval(e) % pubKey.module)

    for _node in committee_list:
        _node.stop_server()

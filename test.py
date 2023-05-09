import logging
import time
from threading import Thread
from nodes.node import Node
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
    dealer_node = Node(committee_addr_list[i], committee_addr_list)
    node_list[i].initialize(params, pubKey, 0)
    Thread(target=dealer_node.start_server, daemon=True).start()
    incoming_node = node_list[e-1]
    

    # dealer 计算 fi
    flist = [0]*(t+1)
    for i in range(t+1):
        flist[i] = priKey.eval(i+1)
    for i in party_list:
        send_call(e, [i], "initial_encrypt", (flist[i-1],))

    send_call(e,party_list,"initial_decrypt",(e, party_list))

    Lie_list = dic2list(incoming_node.party.Lie)
    Le = incoming_node.party.combine_share(Lie_list)

    send_call(e,party_list,"share_decrypt",(Le,))

    # print(incoming_node.party.c)
    ci_list = dic2list(incoming_node.party.c)
    fe = incoming_node.party.share_extract(ci_list, party_list)
    print(fe)
    print(priKey.eval(e) % pubKey.module)

    for _node in node_list:
        _node.stop_server()

node_list = []
if __name__ == '__main__':
    start(10, 8, 10,list(range(1,10)))

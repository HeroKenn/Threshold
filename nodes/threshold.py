from phe.util import getprimeover, invert, is_prime
import random
import time

DEFAULT_KEYSIZE = 512

def feval(alist, x, module):
    ret = 0
    xret = 1
    for i in range(len(alist)):
        ret = (ret+alist[i]*xret) % module
        xret = (xret*x) % module
    return ret


def factorial(n):
    ret = 1
    for i in range(1, n+1):
        ret *= i
    return ret

# party_list 为 Party.index 组成的列表
def lagrange(i, e, party_list, module):
    # 插值节点为 1,2,...,n
    ret = 1
    for j in range(len(party_list)):
        if party_list[j] == i:
            continue
        ret = (ret*(e-party_list[j]) *
               invert(i-party_list[j], module)) % module
    return ret


def l_function( x, p):
    """Computes the L function as defined in Paillier's paper. That is: L(x,p) = (x-1)/p"""
    return (x - 1) // p


def genThresholdPaillierKeypair(n, t, module_length=DEFAULT_KEYSIZE):
    # p = q = module = None
    # pp = qq = None
    # module_len = 0
    # while 1:
    #     pp = getprimeover(module_length // 2 -1)
    #     qq = pp
    #     while qq == pp:
    #         qq = getprimeover(module_length // 2-1)
    #     p = 2*pp+1
    #     q = 2*qq+1
    #     module = p * q
    #     module_len = module.bit_length()
    #     if(is_prime(p) and is_prime(q)) and module_len == module_length:
    #         break

    p = 230327035621301404578835631544404925079663088076143733049504025124355571485967
    q = 209974829741118339060344833991174756155956243871475729381186459342052503376047
    pp = 115163517810650702289417815772202462539831544038071866524752012562177785742983
    qq = 104987414870559169530172416995587378077978121935737864690593229671026251688023
    module = p*q
    m = pp*qq

    beta = random.randint(1, module-1)
    while beta == 0:
        beta = random.randint(1, module-1)
    theta = m*beta % module

    params = Params(n, t, module, m)
    pubKey = ThresholdPaillierPubKey(params,module, theta)
    priKey = ThresholdPaillierPriKey(params,pubKey, beta*m)

    return params, pubKey, priKey

class Params:
    def __init__(self, n, t, module, m):
        self.n = n
        self.t = t

        self.delta = factorial(self.n)

        self.modulem = module*m

        self.h = random.randint(1, module**2-1)
        while (self.h == 0):
            self.h = random.randint(1, module**2-1)

class ThresholdPaillierPubKey:
    def __init__(self, params, module, theta):


        self.module = module
        self.modulesquare = module**2

        self.g = self.module+1

        self.theta = theta

class ThresholdPaillierPriKey:
    def __init__(self, params, pubKey, betam):
        self.params = params
        self.pubKey = pubKey

        self.betam = betam

        # dealer 生成随机函数
        self.f = [0]*(params.t+1)
        for i in range(params.t+1):
            self.f[i] = random.randint(1, params.modulem-1)
        self.f[0] = self.betam

    # 请求计算份额
    def eval(self, i):
        return feval(self.f, i, self.params.modulem)

class Party:
    def __init__(self, params, dealer: ThresholdPaillierPubKey, index):
        self.dealer = dealer
        self.params = params

        self.index = index

        self.sk = random.randint(1, dealer.modulesquare-1)
        while (self.sk == 0):
            self.sk = random.randint(1, dealer.modulesquare-1)
        self.pubKey = pow(params.h, self.sk, dealer.modulesquare)

        self.CNa = 0
        self.CNb = 0
        self.Lie = {}
        self.c = {}
        
        self.time = {}

    def initial_encrypt(self, fi):
        # 份额托管阶段，利用自身独立公钥对门限份额进行加密
        # fi 需要是自己对应的份额
        self.time["initial_encrypt_start"] = time.time()
        self.fi = fi

        ri = random.randint(1, self.dealer.modulesquare-1)
        si = random.randint(1, self.dealer.modulesquare-1)
        self.CNa = pow(self.dealer.g, fi, self.dealer.modulesquare) *\
            pow(ri, self.dealer.module, self.dealer.modulesquare) *\
            pow(self.pubKey, si, self.dealer.modulesquare) %\
            self.dealer.modulesquare
        self.CNb = pow(self.params.h, si, self.dealer.modulesquare)
        self.time["initial_encrypt_end"] = time.time()
        self.time["initial_encrypt"]=self.time["initial_encrypt_end"]-self.time["initial_encrypt_start"]
        return True

    # party_list 为 Part.index 组成的列表
    def initial_decrypt(self, e, party_list):
        # 份额初步解密阶段
        # party_list 是委员会成员集合
        # e 是新成员编号
        self.time["initial_decrypt_start"] = time.time()
        CSDi = self.CNa*invert(
            pow(self.CNb, self.sk, self.dealer.modulesquare),
            self.dealer.modulesquare) % \
            self.dealer.modulesquare
        
        LAie = lagrange(self.index, e, party_list, self.params.modulem)

        Lie = pow(CSDi, LAie, self.dealer.modulesquare)
        self.time["initial_decrypt_end"] = time.time()
        self.time["initial_decrypt"]=self.time["initial_decrypt_end"]-self.time["initial_decrypt_start"]
        return Lie

    def share_decrypt(self, Le):
        # 门限Paillier解密阶段
        # Le 为新成员的重构份额
        self.time["share_decrypt_start"] = time.time()
        ci = pow(Le, 2*self.params.delta*self.fi, self.dealer.modulesquare)
        self.time["share_decrypt_end"] = time.time()
        self.time["share_decrypt"]=self.time["share_decrypt_end"]-self.time["share_decrypt_start"]
        return ci

    def combine_share(self,Lie_list):
        # 份额重构阶段
        # Lie_list 为收集到的拉格朗日参数集合
        self.time["combine_share_start"] = time.time()
        Le = 1
        for i in Lie_list:
            Le = Le*i % self.dealer.modulesquare
        self.time["combine_share_end"] = time.time()
        self.time["combine_share"]=self.time["combine_share_end"]-self.time["combine_share_start"]
        return Le

    def share_extract(self, ci_list, party_list):
        # 新份额提取阶段
        self.time["share_extract_start"] = time.time()
        LAi0_list = [0]*len(party_list)
        for i in range(len(party_list)):
            LAi0_list[i] = lagrange(party_list[i], 0,
                                    party_list, self.params.modulem)

        ret = 1
        for i in range(len(ci_list)):
            ret = ret*pow(ci_list[i], 2*self.params.delta * LAi0_list[i], self.dealer.modulesquare)
        ret = l_function(ret, self.dealer.module)
        ret = ret*invert(4*self.params.delta*self.params.delta *
                        self.dealer.theta, self.dealer.module) % self.dealer.module
        self.time["share_extract_end"] = time.time()
        self.time["share_extract"]=self.time["share_extract_end"]-self.time["share_extract_start"]
        return ret
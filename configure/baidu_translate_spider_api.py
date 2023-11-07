# -*- coding:utf-8 -*-
# 享受雷霆感受雨露
# author xyy,time:2023/11/7

import math
import random
import re
import requests

from urllib.parse import quote
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.ssl_ import create_urllib3_context

########### 百度翻译

# 获取百度翻译的cookie和token
# This is the 2.11 Requests cipher string, containing 3DES.
CIPHERS = (
    'ECDH+AESGCM:DH+AESGCM:ECDH+AES256:DH+AES256:RSA+3DES:!aNULL:'
    '!eNULL:!MD5'
)
def get_baiducookie_token(max_try_nums=3):
    """:type
    max_try_nums : 最大重试次数
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{}.0.4472.124 Safari/537.36'.format(random.choice([100,101,102,103,104,105,106]))
    }

    session = requests.Session()
    session.get("http://www.baidu.com",headers=headers)
    res = session.get("https://fanyi.baidu.com/?aldtype=85#zh/en/%E4%BB%8A%E5%A4%A9%E6%98%AF%E4%B8%AA%E5%BC%80%E5%BF%83%E7%9A%84%E6%97%A5%E5%AD%90",headers=headers)
    BAIDUID = re.findall(r"BAIDUID_BFESS=(.*?):",res.headers.get("Set-Cookie",""))
    token = re.findall(r"token: '(.*)'",res.text)
    if max_try_nums<0:
        return "",""
    if not bool(BAIDUID) or not bool(token): # 有一个没取到都会有问题
        return get_baiducookie_token(max_try_nums=max_try_nums-1)
    return BAIDUID[0] ,token[0]

# 获取百度翻译的sign
def baidufanyi_sign(src):

    def a(r):
        if isinstance(r, list):
            t = [0] * len(r)
            for o in range(len(r)):
                t[o] = r[o]
            return t
        return list(r)

    def n(r, o):
        for t in range(0, len(o) - 2, 3):
            a = o[t + 2]
            a = ord(a) - 87 if a >= "a" else int(a)
            a = r >> a if o[t + 1] == "+" else r << a
            r = r + a & 4294967295 if o[t] == "+" else r ^ a
        return r

    def e(r):
        o = re.findall(r'[\uD800-\uDBFF][\uDC00-\uDFFF]', r)
        if o is None:
            t = len(r)
            if t > 30:
                r = "" + r[:10] + r[math.floor(t / 2) - 5:math.floor(t / 2) + 5] + r[-10:]
        else:
            e = re.split(r'[\uD800-\uDBFF][\uDC00-\uDFFF]', r)
            f = []
            for C in range(len(e)):
                if e[C] != "":
                    f.extend(a(list(e[C])))
                if C != len(e) - 1:
                    f.append(o[C])
            g = len(f)
            if g > 30:
                r = ''.join(f[:10]) + ''.join(f[math.floor(g / 2) - 5:math.floor(g / 2) + 5]) + ''.join(f[-10:])

        u = None
        l = "" + chr(103) + chr(116) + chr(107)
        u = i if i is not None else "320305.131321201" or ""
        d = u.split(".")
        m = int(d[0]) if d[0] else 0
        s = int(d[1]) if d[1] else 0
        S = []
        c = 0
        for v in range(len(r)):
            A = ord(r[v])
            if A < 128:
                S.append(A)
            else:
                if A < 2048:
                    S.append(A >> 6 | 192)
                else:
                    if 55296 == (64512 & A) and v + 1 < len(r) and 56320 == (64512 & ord(r[v + 1])):
                        A = 65536 + ((1023 & A) << 10) + (1023 & ord(r[v + 1]))
                        S.append(A >> 18 | 240)
                        S.append(A >> 12 & 63 | 128)
                        v += 1
                    else:
                        S.append(A >> 12 | 224)
                        S.append(A >> 6 & 63 | 128)
                S.append(63 & A | 128)

        p = m
        F = "" + chr(43) + chr(45) + chr(97) + ("" + chr(94) + chr(43) + chr(54))
        D = "" + chr(43) + chr(45) + chr(51) + ("" + chr(94) + chr(43) + chr(98)) + ("" + chr(43) + chr(45) + chr(102))
        for b in range(len(S)):
            p += S[b]
            p = n(p, F)
        p = n(p, D)
        p ^= s
        if p < 0:
            p = (2147483647 & p) + 2147483648
        p %= 1000000
        return str(p) + "." + str(p ^ m)

    i = None
    return e(src)

# ja3指纹验证 高版本python urllib3 不兼容低版本的简单处理方案 urllib3.util.ssl_.DEFAULT_CIPHERS += 'HIGH:!DH:!aNULL'
class DESAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context(ciphers=CIPHERS)
        kwargs['ssl_context'] = context
        return super(DESAdapter, self).init_poolmanager(*args, **kwargs)

    def proxy_manager_for(self, *args, **kwargs):
        context = create_urllib3_context(ciphers=CIPHERS)
        kwargs['ssl_context'] = context
        return super(DESAdapter, self).proxy_manager_for(*args, **kwargs)
# 百度翻译 api
def baidutrans(text, src, dest):
    session = requests.Session()

    session.mount('https://fanyi.baidu.com', DESAdapter())


    session.proxies = None
    # if config.video.get("proxy",""):
    #     proxies = {
    #         'http': config.video['proxy'],
    #         'https': config.video['proxy']
    #     }
    #     session.proxies = proxies

    sign = baidufanyi_sign(text)
    BAIDUID,token = get_baiducookie_token()
    # print(sign,BAIDUID,token)
    url = "https://fanyi.baidu.com/v2transapi"

    payload = f"from={src}&to={dest}&query={quote(text)}&transtype=realtime&simple_means_flag=3&sign={sign}&token={token}&domain=common"
    headers = {
        'authority': 'fanyi.baidu.com',
        'accept': '*/*',
        'x-requested-with': 'XMLHttpRequest',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.122 Safari/537.36',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'origin': 'https://fanyi.baidu.com',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
        'referer': 'https://fanyi.baidu.com/translate?aldtype=16047&query=&keyfrom=baidu&smartresult=dict&lang=auto2zh',
        'accept-language': 'zh-CN,zh;q=0.9',
        'cookie': f'BIDUPSID={BAIDUID}; BAIDUID={BAIDUID}:FG=1;'
    }

    try:

        response = session.post(url, headers=headers, data=payload,timeout=6)
        # print(response.json())
        if response.status_code != 200:
            return f"error translation code={response.status_code}"
        re_result = response.json().get("trans_result",{}).get("data",[])
        # print("re_result",re_result)
    except:
        return "[error google api] Please check the connectivity of the proxy or consider changing the IP address."
    return "error on translation" if len(re_result) < 1 else re_result[0].get("dst","")

##########
if __name__ == '__main__':
    info = baidutrans(text="今天是个好日子", src="zh", dest="en")
    print(info)
# -*- coding: utf-8 -*-
import os
import re
import time
import urllib

import requests

from videotrans.configure import config
from videotrans.util  import tools


def googletrans(text, src, dest,*,set_p=True):
    url = f"https://translate.google.com/m?sl={urllib.parse.quote(src)}&tl={urllib.parse.quote(dest)}&hl={urllib.parse.quote(dest)}&q={urllib.parse.quote(text)}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    proxies = None
    serv = tools.set_proxy()
    if serv:
        proxies = {
            'http://': serv,
            'https://': serv
        }
    nums=0
    msg=f"[error]google error:{text=}"
    while nums<2:
        nums+=1
        try:
            response = requests.get(url, proxies=proxies, headers=headers, timeout=40)
            print(f"google translate code={response.status_code}")
            if response.status_code != 200:
                msg=f"[error] google error status_code={response.status_code}"
                time.sleep(3)
                continue

            re_result = re.findall(
                r'(?s)class="(?:t0|result-container)">(.*?)<', response.text)
            if len(re_result)<1:
                msg='[error]google error'
                time.sleep(3)
                continue
            return re_result[0]
        except Exception as e:
            msg=f"[error]google error {serv=}: is connect to google {str(e)}?"
            time.sleep(3)
    return msg

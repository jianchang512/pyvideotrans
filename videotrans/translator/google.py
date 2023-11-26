# -*- coding: utf-8 -*-
import re
import time
import urllib

import requests

from videotrans.configure import config

def googletrans(text, src, dest):
    url = f"https://translate.google.com/m?sl={urllib.parse.quote(src)}&tl={urllib.parse.quote(dest)}&hl={urllib.parse.quote(dest)}&q={urllib.parse.quote(text)}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    proxies = None
    if config.video['proxy']:
        proxies = {
            'http': config.video['proxy'],
            'https': config.video['proxy']
        }
    nums=0
    msg=f"[error]google 翻译失败:{text=}"
    while nums<2:
        nums+=1
        try:
            response = requests.get(url, proxies=proxies, headers=headers, timeout=40)
            print(f"google translate code={response.status_code}")
            if response.status_code != 200:
                msg=f"[error] google翻译失败 status_code={response.status_code}"
                time.sleep(3)
                continue

            re_result = re.findall(
                r'(?s)class="(?:t0|result-container)">(.*?)<', response.text)
            if len(re_result)<1:
                msg='[error]google翻译失败了'
                time.sleep(3)
                continue
            return re_result[0]
        except Exception as e:
            msg=f"[error]google 翻译失败:请确认能连接到google" + str(e)
            time.sleep(3)
    return msg

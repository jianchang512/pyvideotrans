# -*- coding: utf-8 -*-
import re
import time
import urllib
import requests
from videotrans.configure import config
from videotrans.util import tools

def trans(text_list, target_language="en", *, set_p=True):
    """
    text_list:
        可能是多行字符串，也可能是格式化后的字幕对象数组
    target_language:
        目标语言
    set_p:
        是否实时输出日志，主界面中需要
    """
    serv = tools.set_proxy()
    proxies = None
    if serv:
        proxies = {
            'http://': serv,
            'https://': serv
        }
    # 翻译后的文本
    target_text = []
    # 整理待翻译的文字为 List[str]
    if isinstance(text_list, str):
        source_text = text_list.strip().split("\n")
    else:
        source_text = [f"{t['text']}" for t in text_list]

    # 切割为每次翻译多少行，值在 set.ini中设定，默认10
    split_size = int(config.settings['trans_thread'])
    print(f'{split_size=}')
    split_source_text = [source_text[i:i + split_size] for i in range(0, len(source_text), split_size)]

    for it in split_source_text:
        try:
            source_length=len(it)
            print(f'{source_length=}')
            text = "\n".join(it)
            url = f"https://translate.google.com/m?sl=auto&tl={urllib.parse.quote(target_language)}&hl={urllib.parse.quote(target_language)}&q={urllib.parse.quote(text)}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, proxies=proxies, headers=headers, timeout=300)
            if response.status_code != 200:
                config.logger.info(f'Google 返回响应:{response.text}\nurl={url}')
                time.sleep(10)
                return trans(text_list, target_language, set_p=set_p)

            re_result = re.findall(
                r'(?s)class="(?:t0|result-container)">(.*?)<', response.text)
            if len(re_result) < 1:
                if set_p:
                    tools.set_process(f'Google limit rate,wait 10s')
                config.logger.info(f'Google limit rate,wait 10s:{response.text}\nurl={url}')
                time.sleep(10)
                return trans(text_list, target_language, set_p=set_p)
            if re_result[0]:
                result=re_result[0].strip().replace('&#39;','"').split("\n")
                if set_p:
                    tools.set_process("\n\n".join(result), 'subtitle')
                result_length=len(result)
                print(f'{result_length=}')
                config.logger.info(f'{result_length=},{source_length=}')
                while result_length<source_length:
                    result.append("")
                    result_length+=1
                result=result[:source_length]
                target_text.extend(result)
            else:
                raise Exception(f'no result:{re_result}')
        except Exception as e:
            error = str(e)
            if error.find("HTTPSConnection")>-1:
                if set_p:
                    tools.set_process(f'Google HTTPSConnectionPool error,after 5s retry')
                config.logger.error(f'Google HTTPSConnectionPool error,after 5s retry:\n{url=}')
                time.sleep(5)
                return trans(text_list, target_language, set_p=set_p)
            config.logger.error(f'Google error:{str(error)}')
            raise Exception(f'Google error:{str(error)}')
    if isinstance(text_list, str):
        return "\n".join(target_text)

    max_i = len(target_text)
    for i, it in enumerate(text_list):
        if i < max_i:
            text_list[i]['text'] = target_text[i]
    return text_list

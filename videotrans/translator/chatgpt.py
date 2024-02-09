# -*- coding: utf-8 -*-
import re
import time
import httpx
import openai
from openai import OpenAI
from videotrans.configure import config
from videotrans.util import tools


def get_url(url=""):
    if not url:
        return "https://api.openai.com/v1"
    url=url.strip().rstrip('/')
    url=re.sub(r'/v1/.*?$','/v1',url)
    if not url.startswith('http'):
        url=f'https://{url}'
    if not url.endswith('/v1'):
        url+='/v1'
    url=url.replace('chat.openai.com','api.openai.com')
    return url
    # return "https://api.openai.com/v1"


def create_openai_client(proxies):
    api_url = "https://api.openai.com/v1"
    if config.params['chatgpt_api']:
        api_url = get_url(config.params['chatgpt_api'])
    openai.base_url = api_url
    try:
        client = OpenAI(base_url=api_url,
                    http_client=httpx.Client(proxies=proxies))
    except Exception as e:
        raise Exception(f'API={api_url},{str(e)}')
    return client


def set_proxies(serv):
    proxies = None
    if serv:
        proxies = {
            'http://': serv,
            'https://': serv
        }
    return proxies


def trans(text_list, target_language="English", *, set_p=True,inst=None,stop=0):
    """
    text_list:
        可能是多行字符串，也可能是格式化后的字幕对象数组
    target_language:
        目标语言
    set_p:
        是否实时输出日志，主界面中需要
    """
    serv = tools.set_proxy()
    proxies = set_proxies(serv)

    # 翻译后的文本
    target_text = []
    # 整理待翻译的文字为 List[str]
    if isinstance(text_list, str):
        source_text = text_list.strip().split("\n")
    else:
        source_text = [t['text'] for t in text_list]

    client = create_openai_client(proxies)
    # 切割为每次翻译多少行，值在 set.ini中设定，默认10
    split_size = int(config.settings['trans_thread'])
    split_source_text = [source_text[i:i + split_size] for i in range(0, len(source_text), split_size)]

    for i,it in enumerate(split_source_text):
        if stop>0:
            time.sleep(stop)
        try:
            source_length=len(it)
            message = [
                {'role': 'system',
                 'content': config.params['chatgpt_template'].replace('{lang}', target_language)},
                {'role': 'user', 'content': "\n".join(it)},
            ]
            config.logger.info(f"\n[chatGPT start]待翻译:{message=}")
            response = client.chat.completions.create(
                model=config.params['chatgpt_model'],
                messages=message
            )
            config.logger.info(f'chatGPT 返回响应:{response}')

            if response.choices:
                result = response.choices[0].message.content.strip()
            elif response.data and response.data['choices']:
                result = response.data['choices'][0]['message']['content'].strip()
            else:
                raise Exception(f"chatGPT {response}")
            result=result.strip().replace('&#39;','"').split("\n")

            if inst and inst.precent < 75:
                inst.precent += round((i + 1) * 5 / len(split_source_text), 2)
            if set_p:
                tools.set_process("\n\n".join(result), 'subtitle')
                tools.set_process(config.transobj['starttrans'])
            else:
                tools.set_process("\n\n".join(result), func_name="set_fanyi")
            result_length = len(result)
            while result_length < source_length:
                result.append("")
                result_length += 1
            result = result[:source_length]
            target_text.extend(result)
        except Exception as e:
            error = str(e)
            if set_p and config.current_status=='ing':
                tools.set_process(f'出错了,等待30s后重试:{error}' if config.defaulelang=='zh' else f'wait 30s retry:{error}')
                time.sleep(30)
                return trans(text_list, target_language, set_p=set_p,inst=inst,stop=3)
            raise Exception(f'chatGPT:{str(error)}')
    if isinstance(text_list, str):
        return "\n".join(target_text)

    max_i = len(target_text)
    for i, it in enumerate(text_list):
        if i < max_i:
            text_list[i]['text'] = target_text[i]
    return text_list

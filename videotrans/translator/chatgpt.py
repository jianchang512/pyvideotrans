# -*- coding: utf-8 -*-
import os
import re

import openai
from openai import OpenAI

from ..configure import config
from ..configure.config import logger
from ..configure import tools as sptools


def chatgpttrans(text):
    if re.match(r'^[.,=_?!@#$%^&*()+\s -]+$', text):
        return text
    proxies=None
    if config.video['proxy']:
        proxies = {
            'http': 'http://%s' % config.video['proxy'].replace("http://", ''),
            'https': 'http://%s' % config.video['proxy'].replace("http://", '')
        }
    else:
        serv=os.environ.get('http_proxy') or os.environ.get('HTTP_PROXY')
        if serv:
            proxies = {
                'http': 'http://%s' % serv.replace("http://", ''),
                'https': 'http://%s' % serv.replace("http://", '')
            }
    if proxies:
        openai.proxies = proxies
    if config.video['chatgpt_api']:
        openai.base_url = config.video['chatgpt_api']

    lang = config.video['target_language_chatgpt']
    messages = [
        {'role': 'system',
         'content': config.video['chatgpt_template'].replace('{lang}', lang)},
        {'role': 'user', 'content': f"{text}"},
    ]
    try:
        client = OpenAI(base_url=None if not config.video['chatgpt_api'] else config.video['chatgpt_api'])
        response = client.chat.completions.create(
            model=config.video['chatgpt_model'],
            messages=messages,
            max_tokens=2048
        )
    except Exception as e:
        logger.error(f"chatGPT request error:" + str(e))
        sptools.set_process(f"[error]chatGPT翻译请求失败error:" + str(e))
        return f"[error]:chatgpt translate error:" + str(e)
    try:
        if response.code != 0 and response.message:
            sptools.set_process(f"[error]chatGPT翻译请求失败error:" + response.message)
            return "[error]"+response.message
        result = response.data['choices'][0]['message']['content'].strip()
        if re.match(r"Sorry, but I'm unable to translate the content", result, re.I):
            sptools.set_process(f"[error]chatGPT翻译失败error:不可翻译的内容")
            return "[error]:no translate"
        return result
    except Exception as e:
        logger.error(f"chatGPT response:" + str(e))
        sptools.set_process(f"[error]chatGPT 请求失败:" + str(e))
        return f"[error]:chatGPT response error:" + str(e)

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
    proxies = None
    if config.video['proxy']:
        proxies = {
            'http': 'http://%s' % config.video['proxy'].replace("http://", ''),
            'https': 'http://%s' % config.video['proxy'].replace("http://", '')
        }
    else:
        serv = os.environ.get('http_proxy') or os.environ.get('HTTP_PROXY')
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

    total_result = []
    # 字幕整理成字幕信息list
    split_text = text.strip().split("\n\n")
    split_size = 10
    # 按照 split_size 将字幕每组8个分成多组,是个二维列表，一维是包含8个字幕的list，二维是每个字幕list
    msg_q = [split_text[i:i + split_size] for i in range(0, len(split_text), split_size)]

    # 分别按组翻译，每组翻译 split_size个字幕
    for m in msg_q:
        # 存放时间和行数
        origin = []
        # 存放待翻译文本
        trans = []
        # 处理每个字幕信息
        for n in m:
            n_1 = n.split("\n")
            # 行数和时间信息
            origin.append({"line": n_1[0], "time": n_1[1], "text": ""})
            # 纯粹文本信息
            trans.append("".join(n_1[2:]).replace("\n", "."))
        len_sub = len(origin)

        messages = [
            {'role': 'system',
             'content': config.video['chatgpt_template'].replace('{lang}', lang)},
            {'role': 'user', 'content': "####".join(trans)},
        ]
        # continue
        try:
            client = OpenAI(base_url=None if not config.video['chatgpt_api'] else config.video['chatgpt_api'])
            response = client.chat.completions.create(
                model=config.video['chatgpt_model'],
                messages=messages
            )
            if response.code != 0 and response.message:
                sptools.set_process(f"[error]chatGPT翻译请求失败error:" + response.message)
                trans_text = ["[error]" + response.message] * len_sub
            else:
                result = response.data['choices'][0]['message']['content'].strip()
                if result[:4] == '####':
                    result = result[4:]
                sptools.set_process(f"chatGPT翻译成功")
                trans_text = result.split('####')
        except Exception as e:
            logger.error(f"chatGPT response:" + str(e))
            sptools.set_process(f"[error]chatGPT 请求失败:" + str(e))
            trans_text = [f"[error]chatGPT 请求失败:" + str(e)] * len_sub
        # 处理
        for index, it in enumerate(origin):
            origin[index]["text"] = "-" if index >= len(trans_text) else trans_text[index]
        total_result.extend(origin)

    subtitles = ""
    for it in total_result:
        subtitles += f"{it['line']}\n{it['time']}\n{it['text']}\n\n"
    return subtitles.strip()

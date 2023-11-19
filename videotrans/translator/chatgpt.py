# -*- coding: utf-8 -*-
import json
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
    api_url="https://api.openai.com/v1"
    if config.video['chatgpt_api']:
        api_url=config.video['chatgpt_api']

    openai.base_url=api_url

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
            if len(n_1)<3:
                continue
            # 纯粹文本信息
            txt_tmp=("".join(n_1[2:])).replace("\n", ".").replace("\r",'').strip()
            if not txt_tmp:
                continue
            trans.append(txt_tmp)
            # 行数和时间信息
            origin.append({"line": n_1[0], "time": n_1[1], "text": ""})
        len_sub = len(origin)

        logger.info(f"\n[chatGPT start]待翻译文本:"+"\n".join(trans))
        messages = [
            {'role': 'system',
             'content': config.video['chatgpt_template'].replace('{lang}', lang)},
            {'role': 'user', 'content': "\n".join(trans)},
        ]
        # continue
        try:
            client = OpenAI(base_url=None if not config.video['chatgpt_api'] else config.video['chatgpt_api'])
            response = client.chat.completions.create(
                model=config.video['chatgpt_model'],
                messages=messages
            )
            # 是否在 code 判断时就已出错
            occur_error=False
            try:
                if response.code != 0 and response.message:
                    sptools.set_process(f"[error]chatGPT翻译请求失败error:" + response.message)
                    logger.error(f"[chatGPT error-1]翻译失败r:" + response.message)
                    trans_text = ["[error]" + response.message] * len_sub
                    occur_error=True
            except Exception as e:
                msg=f"【chatGPT Error-0】翻译失败:openaiAPI={api_url}:{str(e)}:{str(response)}"
                logger.error(msg)
                sptools.set_process(msg)
                trans_text = ["[error]" +str(e)] * len_sub
                occur_error=True

            if not occur_error:
                result = response.data['choices'][0]['message']['content'].strip()
                # 如果返回的是合法js字符串，则解析为json，否则以\n解析
                if result.startswith('[') and result.endswith(']'):
                    try:
                        trans_text=json.loads(result)
                    except:
                        trans_text=result.split("\n")
                else:
                    trans_text=result.split("\n")
                logger.info(f"\n[chatGPT OK]翻译成功:{result}")
                sptools.set_process(f"chatGPT 翻译成功")
        except Exception as e:
            logger.error(f"【chatGPT Error-2】翻译失败:openaiAPI={api_url} :" + str(e))
            if not api_url.startswith("https://api.openai.com"):
                sptools.set_process(f"[error]chatGPT,当前请求api={api_url}是第三方接口，请尝试接口地址末尾增加或去掉 /v1 后再试:" + str(e))
            else:
                sptools.set_process(f"[error]chatGPT,当前请求api={api_url} 请求失败:" + str(e))
            trans_text = [f"[error]chatGPT 请求失败:" + str(e)] * len_sub
        # 处理
        for index, it in enumerate(origin):
            origin[index]["text"] = "-" if index >= len(trans_text) else trans_text[index]
        total_result.extend(origin)

    subtitles = ""
    for it in total_result:
        subtitles += f"{it['line']}\n{it['time']}\n{it['text']}\n\n"
    return subtitles.strip()

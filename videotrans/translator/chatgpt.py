# -*- coding: utf-8 -*-
import json
import os
import re
import time

import httpx
import openai
from openai import OpenAI
from videotrans.configure import config
from videotrans.configure.config import logger
from videotrans.util import tools

def create_messages(text_list, lang):
    messages = [
        {'role': 'system',
         'content': config.params['chatgpt_template'].replace('{lang}', lang)},
        {'role': 'user', 'content': text_list},
    ]
    return messages

def create_openai_client(proxies):
    client = OpenAI(base_url=None if not config.params['chatgpt_api'] else config.params['chatgpt_api'],
                    http_client=httpx.Client(proxies=proxies))
    return client

def process_response(response):
    vail_data = None
    try:
        if response.choices:
            result = response.choices[0].message.content.strip()
            return result
        elif response.data and response.data['choices']:
            result = response.data['choices'][0]['message']['content'].strip()
            return result
        else:
            logger.error(f'chatGPT error:{response}')
    except Exception as e:
        print(e)
        return f'[error] {str(e)}'

def set_proxies(serv):
    proxies = None
    if serv:
        proxies = {
            'http://': serv,
            'https://': serv
        }
    return proxies

def handle_error(error, api_url, set_p):
    logger.error(f"【chatGPT Error-2】翻译失败:openaiAPI={api_url} :{error}")
    if set_p:
        tools.set_process(f"[error]ChatGPT error,api={api_url}:{error}",'error')
    raise Exception(f"[error]ChatGPT error,api={api_url}:{error}")


def process_result(result,len_sub=1):
    return result.split("\n") if isinstance(result, str) else ["[error]ChatGPT error"] * len_sub

def update_origin(trans_text, origin, set_p):
    srts = ''
    for index, it in enumerate(origin):
        if index < len(trans_text):
            it["text"] = trans_text[index]
            origin[index] = it
            st = f"{it['line']}\n{it['time']}\n{it['text']}\n\n"
            if set_p:
                tools.set_process(st, 'subtitle')
            srts += st

    return origin, srts

def chatgpttrans(text_list, target_language_chatgpt="English", *, set_p=True):
    serv = tools.set_proxy()
    proxies = set_proxies(serv)
    api_url = "https://api.openai.com/v1"
    if config.params['chatgpt_api']:
        api_url = config.params['chatgpt_api']

    openai.base_url = api_url
    lang = target_language_chatgpt
    error=''

    if isinstance(text_list, str):
        messages = create_messages(text_list, lang)
        client = create_openai_client(proxies)

        try:
            response = client.chat.completions.create(
                model=config.params['chatgpt_model'],
                messages=messages
            )
            return process_response(response)
        except Exception as e:
            error = str(e)
            return (f"【ChatGPT Error-2.5】error:openaiAPI={api_url} :{error}")
    else:
        total_result = []
        split_size = 10
        srt_lists = [text_list[i:i + split_size] for i in range(0, len(text_list), split_size)]
        srts = ''

        for srt_list in srt_lists:
            origin = []
            trans = []
            for it in srt_list:
                trans.append(it['text'].strip())
                origin.append({"line": it["line"], "time": it["time"], "text": ""})
            len_sub = len(origin)
            logger.info(f"\n[chatGPT start]待翻译文本:" + "\n".join(trans))
            messages = create_messages("\n".join(trans), lang)
            client = create_openai_client(proxies)

            try:
                response = client.chat.completions.create(
                    model=config.params['chatgpt_model'],
                    messages=messages
                )
                result = process_response(response)
                if result.startswith('[error]'):
                    error=result
            except Exception as e:
                error = str(e)
                result = "[error]ChatGPT error"

            if re.search(r'Rate limit', error, re.I) is not None:
                if set_p:
                    tools.set_process(f'ChatGPT limit rate, wait 30s')
                time.sleep(30)
                return chatgpttrans(text_list)
            elif error:
                handle_error(error, api_url, set_p)
                return False

            trans_text = process_result(result,len_sub)
            origin, srts = update_origin(trans_text, origin, set_p)
            total_result.extend(origin)

    if set_p:
        tools.set_process(srts, 'replace_subtitle')
    return total_result
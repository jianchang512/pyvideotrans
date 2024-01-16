# -*- coding: utf-8 -*-
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

def get_url(url=""):
    if not url:
        return "https://api.openai.com/v1"
    m=re.match(r'(https?://(?:[_\w-]+\.)+[a-zA-Z]+/?)',url)
    if m is not None and len(m.groups())==1:
        return f'{m.groups()[0]}/v1'
    return "https://api.openai.com/v1"


def create_openai_client(proxies):
    api_url = "https://api.openai.com/v1"
    if config.params['chatgpt_api']:
        api_url = get_url(config.params['chatgpt_api'])


    openai.base_url = api_url
    client = OpenAI(base_url=api_url,
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
        msg=f'chatGPT error:{response}'

        logger.error(msg)
        raise Exception(msg)
    except Exception as e:
        print(e)
        raise Exception(f'[error] {str(e)}')

def set_proxies(serv):
    proxies = None
    if serv:
        proxies = {
            'http://': serv,
            'https://': serv
        }
    return proxies

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

    lang = target_language_chatgpt

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
            raise Exception(f"【ChatGPT Error-2.5】error:{error}")
    else:
        total_result = []
        split_size = config.settings['OPTIM']['trans_thread']
        srt_lists = [text_list[i:i + split_size] for i in range(0, len(text_list), split_size)]
        srts = ''
        client = create_openai_client(proxies)
        for srt_list in srt_lists:
            origin = []
            trans = []
            for it in srt_list:
                trans.append(it['text'].strip())
                origin.append({"line": it["line"], "time": it["time"], "text": ""})
                if set_p:
                    tools.set_process(f'chatGPT Line: {it["line"]}')
            len_sub = len(origin)
            logger.info(f"\n[chatGPT start]待翻译文本:" + "\n".join(trans))
            messages = create_messages("\n".join(trans), lang)
            try:
                response = client.chat.completions.create(
                    model=config.params['chatgpt_model'],
                    messages=messages
                )
                result = process_response(response)
            except Exception as e:
                error = str(e)
                if re.search(r'Rate limit', error, re.I) is not None:
                    if set_p:
                        tools.set_process(f'ChatGPT limit rate, wait 30s')
                    time.sleep(30)
                    return chatgpttrans(text_list)
                else:
                    raise Exception(f'chatGPT error:{str(error)}')
            trans_text = process_result(result,len_sub)
            origin, srts = update_origin(trans_text, origin, set_p)
            total_result.extend(origin)
    if set_p:
        tools.set_process(srts, 'replace_subtitle')
    return total_result
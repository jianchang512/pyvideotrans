# -*- coding: utf-8 -*-
import re

import openai

from ..configure import config
from ..configure.config import logger


def chatgpttrans(text):
    if re.match(r'^[.,=_?!@#$%^&*()+\s -]+$', text):
        return text
    if config.video['proxy']:
        proxies = {
            'http': 'http://%s' % config.video['proxy'].replace("http://", ''),
            'https': 'http://%s' % config.video['proxy'].replace("http://", '')
        }
        openai.proxy = proxies
    if config.video['chatgpt_api']:
        openai.api_base = config.video['chatgpt_api']
    openai.api_key = config.video['chatgpt_key']

    lang = config.video['target_language_chatgpt']
    messages = [
        {'role': 'system',
         'content': config.video['chatgpt_template'].replace('{lang}', lang)},
        {'role': 'user', 'content': f"{text}"},
    ]
    try:
        response = openai.ChatCompletion.create(
            model=config.video['chatgpt_model'],
            messages=messages,
            max_tokens=2048
        )
    except Exception as e:
        logger.error(f"chatGPT request error:" + str(e))
        return f"[error]:chatgpt translate error:" + str(e)
    print(response)
    if response['code'] != 0 and response['message']:
        return "[error]"+response['message']
    data = response.data
    if "choices" not in data:
        return "[error]:chatGPT error:"+data["status"]
    for choice in data.choices:
        if 'text' in choice:
            return choice.text

    result = data.choices[0].message.content.strip()
    if re.match(r"Sorry, but I'm unable to translate the content", result, re.I):
        return "[error]:no translate"
    return result

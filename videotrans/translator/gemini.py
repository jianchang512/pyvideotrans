# -*- coding: utf-8 -*-
import os
import re
import time
from videotrans.configure import config
from videotrans.util import tools
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

safetySettings = [
    {
        "category": HarmCategory.HARM_CATEGORY_HARASSMENT,
        "threshold": HarmBlockThreshold.BLOCK_NONE,
    },
    {
        "category": HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        "threshold": HarmBlockThreshold.BLOCK_NONE,
    },
    {
        "category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        "threshold": HarmBlockThreshold.BLOCK_NONE,
    },
    {
        "category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        "threshold": HarmBlockThreshold.BLOCK_NONE,
    },
]


def trans(text_list, target_language="English", *, set_p=True):
    """
    text_list:
        可能是多行字符串，也可能是格式化后的字幕对象数组
    target_language:
        目标语言
    set_p:
        是否实时输出日志，主界面中需要
    """
    serv = tools.set_proxy()
    if serv:
        os.environ['http_proxy'] = serv
        os.environ['https_proxy'] = serv
    try:
        genai.configure(api_key=config.params['gemini_key'])
        model = genai.GenerativeModel('gemini-pro')
    except Exception as e:
        err = str(e)
        raise Exception(f'[error]Gemini error:{err}')

    # 翻译后的文本
    target_text = []
    # 整理待翻译的文字为 List[str]
    if isinstance(text_list, str):
        source_text = text_list.strip().split("\n")
    else:
        source_text = [t['text'] for t in text_list]

    # 切割为每次翻译多少行，值在 set.ini中设定，默认10
    split_size = int(config.settings['trans_thread'])
    split_source_text = [source_text[i:i + split_size] for i in range(0, len(source_text), split_size)]

    for it in split_source_text:
        try:
            source_length=len(it)
            print(f'{source_length=}')
            response = model.generate_content(
                config.params['gemini_template'].replace('{lang}', target_language) + "\n".join(it),
                safety_settings=safetySettings
            )


            if response.text:
                result = response.text.strip()
                if set_p:
                    tools.set_process("\n\n".join(result), 'subtitle')
                result=result.strip().replace('&#39;','"').split("\n")
                result_length = len(result)
                print(f'{result_length=}')
                while result_length < source_length:
                    result.append("")
                    result_length += 1
                result = result[:source_length]
                target_text.extend(result)
            else:
                config.logger.info(f'Gemini 返回响应:{response}')
                raise Exception(f'no result:{response.prompt_feedback}')
        except Exception as e:
            error = str(e)
            if set_p and re.search(r'limit', error, re.I):
                tools.set_process(f'Gemini errir,wait 30s:{error}')
                time.sleep(30)
                return trans(text_list, target_language, set_p=set_p)
            else:
                raise Exception(f'Gemini error:{str(error)}')
    if isinstance(text_list, str):
        return "\n".join(target_text)

    max_i = len(target_text)
    for i, it in enumerate(text_list):
        if i < max_i:
            text_list[i]['text'] = target_text[i]
    return text_list

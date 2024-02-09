# -*- coding: utf-8 -*-

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

def get_error(num=5):
    REASON_CN={
        2:"超出长度",
        3:"安全限制",
        4:"文字过度重复",
        5:"其他原因"
    }
    REASON_EN={
        2:"The maximum number of tokens as specified",
        3:"The candidate content was flagged for safety",
        4:"The candidate content was flagged",
        5:"Unknown reason"
    }
    if config.defaulelang=='zh':
        return REASON_CN[num]
    return REASON_EN[num]

def trans(text_list, target_language="English", *, set_p=True,inst=None,stop=0):
    """
    text_list:
        可能是多行字符串，也可能是格式化后的字幕对象数组
    target_language:
        目标语言
    set_p:
        是否实时输出日志，主界面中需要
    """

    try:
        genai.configure(api_key=config.params['gemini_key'])
        model = genai.GenerativeModel('gemini-pro')
    except Exception as e:
        err = str(e)
        raise Exception(f'Gemini:请正确设置http代理,{err}')

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
    response=None
    for i,it in enumerate(split_source_text):
        if stop>0:
            time.sleep(stop)
        try:
            source_length=len(it)
            response = model.generate_content(
                config.params['gemini_template'].replace('{lang}', target_language) + "\n".join(it),
                safety_settings=safetySettings
            )
            result = response.text.strip()
            result=result.strip().replace('&#39;','"').split("\n")
            if inst and inst.precent < 75:
                inst.precent += round((i + 1) * 5 / len(split_source_text), 2)
            if set_p:
                tools.set_process("\n\n".join(result), 'subtitle')
                tools.set_process(config.transobj['starttrans'])
            else:
                tools.set_process("\n\n".join(result), func_name="set_fanyi")
            while len(result) < source_length:
                result.append("")
            result = result[:source_length]
            target_text.extend(result)

        except Exception as e:
            error = str(e)
            if response and response.candidates[0].finish_reason != 0:
                raise Exception(f'Gemini:{get_error(response.candidates[0].finish_reason)}：从第{(i*split_size)+1}条开始的{split_size}条字幕')
            raise Exception(f'Gemini:{str(error)}')

    if isinstance(text_list, str):
        return "\n".join(target_text)

    max_i = len(target_text)
    for i, it in enumerate(text_list):
        if i < max_i:
            text_list[i]['text'] = target_text[i]
    return text_list

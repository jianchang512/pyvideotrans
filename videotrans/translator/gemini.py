# -*- coding: utf-8 -*-
import os
import re
import time

from videotrans.configure import config
from videotrans.configure.config import logger
from videotrans.util import tools
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

'''
输入
[{'line': 1, 'time': 'aaa', 'text': '\n我是中国人,你是哪里人\n'}, {'line': 2, 'time': 'bbb', 'text': '我身一头猪'}]

输出
[{'line': 1, 'time': 'aaa', 'text': 'I am Chinese, where are you from?'}, {'line': 2, 'time': 'bbb', 'text': 'I am a pig'}]

'''
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


def geminitrans(text_list, target_language_chatgpt="English", *, set_p=True):
    serv = tools.set_proxy()
    if serv:
        os.environ['http_proxy'] = serv
        os.environ['https_proxy'] = serv
    try:
        genai.configure(api_key=config.params['gemini_key'])
    except Exception as e:
        err = str(e)
        if isinstance(text_list, str):
            return err
        else:
            raise Exception(f'[error]Gemini error:{err}')

    lang = target_language_chatgpt
    if isinstance(text_list, str):
        try:
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(
                config.params['gemini_template'].replace('{lang}', lang) + f"\n{text_list}",
                safety_settings=safetySettings
            )
            return response.text.strip()
        except Exception as e:
            error = str(e)
            raise Exception(f"Gemini error:{error}")

    total_result = []
    split_size = config.settings['OPTIM']['trans_thread']
    # 按照 split_size 将字幕每组8个分成多组,是个二维列表，一维是包含8个字幕dict的list，二维是每个字幕dict的list
    srt_lists = [text_list[i:i + split_size] for i in range(0, len(text_list), split_size)]
    srts = ''
    model = genai.GenerativeModel('gemini-pro')
    # 分别按组翻译，每组翻译 srt_list是个list列表，内部有10个字幕dict
    for srt_list in srt_lists:
        # 存放时间和行数
        origin = []
        # 存放待翻译文本
        trans = []
        # 处理每个字幕信息，it是字幕dict
        for it in srt_list:
            # 纯粹文本信息， 第一行是 行号，第二行是 时间，第三行和以后都是文字
            trans.append(it['text'].strip())
            # 行数和时间信息
            origin.append({"line": it["line"], "time": it["time"], "text": ""})
            if set_p:
                tools.set_process(f'Gemini Line: {it["line"]}')

        len_sub = len(origin)
        logger.info(f"\n[Gemini start]待翻译文本:" + "\n".join(trans))
        error = ""
        response = None
        try:
            response = model.generate_content(
                config.params['gemini_template'].replace('{lang}', lang) + "\n" + "\n".join(trans),
                safety_settings=safetySettings
            )
            if not response.parts and set_p:
                raise Exception(f"[error]Gemini error:{response.prompt_feedback}")

            trans_text = response.text.split("\n")
            if set_p:
                tools.set_process(f"Gemini OK")
        except Exception as e:
            error = str(e)
            if response:
                error += f',{response.prompt_feedback=}'
            if error:
                if set_p:
                    tools.set_process(f'Gemini limit rate,wait 30s')
                time.sleep(30)
                return geminitrans(text_list)
        # 处理

        for index, it in enumerate(origin):
            it["text"] = trans_text[index] if index < len(trans_text) else ""
            origin[index] = it
            # 更新字幕
            st = f"{it['line']}\n{it['time']}\n{it['text']}\n\n"
            if set_p:
                tools.set_process(st, 'subtitle')
            srts += st
        total_result.extend(origin)
    if set_p:
        tools.set_process(srts, 'replace_subtitle')
    return total_result

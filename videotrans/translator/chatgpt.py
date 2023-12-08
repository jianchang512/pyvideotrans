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

'''
输入
[{'line': 1, 'time': 'aaa', 'text': '\n我是中国人,你是哪里人\n'}, {'line': 2, 'time': 'bbb', 'text': '我身一头猪'}]

输出
[{'line': 1, 'time': 'aaa', 'text': 'I am Chinese, where are you from?'}, {'line': 2, 'time': 'bbb', 'text': 'I am a pig'}]

'''

def chatgpttrans(text_list,target_language_chatgpt="English",*,set_p=True):
    proxies = None
    serv = tools.set_proxy()
    if serv:
        proxies = {
            'http://': serv,
            'https://': serv
        }
    api_url="https://api.openai.com/v1"
    if config.chatgpt_api:
        api_url=config.chatgpt_api

    openai.base_url=api_url
    lang = target_language_chatgpt
    print(f'{config.chatgpt_template=}')
    if isinstance(text_list,str):
        messages = [
            {'role': 'system',
             'content': config.chatgpt_template.replace('{lang}', lang)},
            {'role': 'user', 'content': text_list},
        ]
        print(messages)
        response=""
        try:
            client = OpenAI(base_url=None if not config.chatgpt_api else config.chatgpt_api, http_client=httpx.Client(proxies=proxies))
            response = client.chat.completions.create(
                model=config.chatgpt_model,
                messages=messages
            )
            if "choices" in response:
                return response['choices'][0]['message']['content'].strip()
            try:
                if response.choices:
                    return response.choices[0]['message']['content'].strip()
            except Exception as e:
                print(e)
            try:
                if response.data and response.data['choices']:
                    return response.data['choices'][0]['message']['content'].strip()
            except Exception as e:
                print(str(e))
        except Exception as e:
            error = str(e)
            return (f"【chatGPT Error-2】翻译失败:openaiAPI={api_url} :{error}")
        return f"翻译失败:{response=}"


    total_result = []
    split_size = 10
    # 按照 split_size 将字幕每组8个分成多组,是个二维列表，一维是包含8个字幕dict的list，二维是每个字幕dict的list
    srt_lists = [text_list[i:i + split_size] for i in range(0, len(text_list), split_size)]
    logger.info(f"\n==={srt_lists}\n=======\n")
    srts=''
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

        len_sub = len(origin)
        logger.info(f"\n[chatGPT start]待翻译文本:"+"\n".join(trans))
        messages = [
            {'role': 'system',
             'content': config.chatgpt_template.replace('{lang}', lang)},
            {'role': 'user', 'content': "\n".join(trans)},
        ]
        logger.info(f"发送消息{messages=}")
        error=""
        try:
            client = OpenAI(base_url=None if not config.chatgpt_api else config.chatgpt_api, http_client=httpx.Client(proxies=proxies))
            response = client.chat.completions.create(
                model=config.chatgpt_model,
                messages=messages
            )
            logger.info(f"返回响应:{response=}")

            # 是否在 code 判断时就已出错
            vail_data=None
            # 返回可能多种形式，openai和第三方

            try:
                if "choices" in response:
                    vail_data=response['choices']
            except Exception as e:
                error+=str(e)
            if not vail_data:
                try:
                    if response.choices:
                        vail_data=response.choices
                except Exception as e:
                    error+=str(e)
            if not vail_data:
                try:
                    if response.data and response.data['choices']:
                        vail_data=response.data['choices']
                except Exception as e:
                    error+=str(e)
            if not vail_data:
                try:
                    if ("code" in response) and response['code'] != 0:
                        if set_p:
                            tools.set_process(f"[error]chatGPT翻译请求失败error:" + str(response))
                        logger.error(f"[chatGPT error-1]翻译失败r:" + str(response))
                except:
                    pass
            if vail_data:
                result = vail_data[0]['message']['content'].strip()
                # 如果返回的是合法js字符串，则解析为json，否则以\n解析
                if result.startswith('[') and result.endswith(']'):
                    try:
                        trans_text=json.loads(result)
                    except:
                        trans_text=result.split("\n")
                else:
                    trans_text=result.split("\n")
                logger.info(f"\n[chatGPT OK]翻译成功:{result}")
                if set_p:
                    tools.set_process(f"chatGPT 翻译成功")
            else:
                trans_text = ["[error]chatGPT翻译失败"] * len_sub
                if set_p:
                    tools.set_process(f"[error]chatGPT出错:{error}")
        except Exception as e:
            error=str(e)
            logger.error(f"【chatGPT Error-2】翻译失败:openaiAPI={api_url} :{error}")
            if not api_url.startswith("https://api.openai.com"):
                if set_p:
                    tools.set_process(f"[error]chatGPT,当前请求api={api_url}是第三方接口，请尝试接口地址末尾增加或去掉 /v1 后再试:{error}")
            elif set_p:
                tools.set_process(f"[error]chatGPT,当前请求api={api_url} 请求失败:{error}")
            trans_text = [f"[error]chatGPT 请求失败"] * len_sub
        if error and re.search(r'Rate limit',error,re.I) is not None:
            if set_p:
                tools.set_process(f'chatGPT请求速度被限制，暂停30s后自动重试')
            time.sleep(30)
            return chatgpttrans(text_list)
        # 处理

        for index, it in enumerate(origin):
            if index < len(trans_text):
                it["text"]=trans_text[index]
                origin[index]=it
                # 更新字幕
                st=f"{it['line']}\n{it['time']}\n{it['text']}\n\n"
                if set_p:
                    tools.set_process(st,'subtitle')
                srts+=st
        total_result.extend(origin)
    if set_p:
        tools.set_process(srts,'replace_subtitle')
    return total_result
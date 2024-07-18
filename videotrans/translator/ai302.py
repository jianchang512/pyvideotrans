# -*- coding: utf-8 -*-
import json
import os
import re
import time
import httpx
import openai
import requests
from openai import OpenAI, APIError
from videotrans.configure import config
from videotrans.util import tools



def get_content(d,*,prompt=None,assiant=None):
    text="\n".join([i.strip() for i in d]) if isinstance(d,list) else d
    payload = {
        "model": config.params['ai302_model'],
        "messages": [
            {'role': 'system', 'content': prompt},
            {'role': 'user', 'content':  f'{prompt}"""{text}"""'},
        ]
    }

    try:

        response=requests.post('https://api.302.ai/v1/chat/completions',headers= {
           'Accept': 'application/json',
           'Authorization': f'Bearer {config.params["ai302_key"]}',
           'User-Agent': 'python',
           'Content-Type': 'application/json'
        },json=payload,verify=False)
        config.logger.info(f'[302.ai]响应:{response=}')
        if response.status_code !=200:
            raise Exception(response.text)
    except ConnectionError as e:
        config.logger.error(f'[302.ai]请求失败:{str(e)}')
        raise
    except Exception as e:
        config.logger.error(f'[302.ai]请求失败:{str(e)}')
        raise
    else:
        res=response.json()
        if res['choices']:
            result = res['choices'][0]['message']['content']
            result = result.replace('##', '').strip().replace('&#39;', '"').replace('&quot;', "'")
            return re.sub(r'\n{2,}',"\n",result)
        else:
            raise Exception(f"{res}")




def trans(text_list, target_language="English", *, set_p=True,inst=None,stop=0,source_code="",is_test=False):
    """
    text_list:
        可能是多行字符串，也可能是格式化后的字幕对象数组
    target_language:
        目标语言
    set_p:
        是否实时输出日志，主界面中需要
    """

    # 翻译后的文本
    target_text = {"0":[],"srts":[]}
    index = 0  # 当前循环需要开始的 i 数字,小于index的则跳过
    iter_num = 0  # 当前循环次数，如果 大于 config.settings.retries 出错
    err = ""
    is_srt=False if  isinstance(text_list, str) else True

    # 切割为每次翻译多少行，值在 set.ini中设定，默认10
    split_size = int(config.settings['trans_thread'])

    prompt=config.params['chatgpt_template'].replace('{lang}', target_language)
    with open(config.rootdir+"/videotrans/chatgpt"+("" if config.defaulelang=='zh' else '-en')+".txt",'r',encoding="utf-8") as f:
        prompt=f.read().replace('{lang}', target_language)




    end_point="。" if config.defaulelang=='zh' else '. '
    # 整理待翻译的文字为 List[str]
    if not is_srt:
        source_text = [t.strip() for t in text_list.strip().split("\n") if t.strip()]
    else:
        source_text=[]
        for i,it in enumerate(text_list):
            source_text.append(it['text'].strip().replace('\n','.'))
    split_source_text = [source_text[i:i + split_size] for i in range(0, len(source_text), split_size)]
    while 1:
        if config.exit_soft or (config.current_status!='ing' and config.box_trans!='ing' and not is_test):
            return
        if iter_num >= config.settings['retries']:
            err=f'{iter_num}{"次重试后依然出错" if config.defaulelang == "zh" else " retries after error persists "}:{err}'
            break
        iter_num += 1
        if iter_num > 1:
            if set_p:
                tools.set_process(
                    f"第{iter_num}次出错重试" if config.defaulelang == 'zh' else f'{iter_num} retries after error',btnkey=inst.init['btnkey'] if inst else "")
            time.sleep(10)

        for i,it in enumerate(split_source_text):
            if config.exit_soft or  (config.current_status != 'ing' and config.box_trans != 'ing' and not is_test):
                return
            if i < index:
                continue
            if stop>0:
                time.sleep(stop)

            try:
                result=get_content(it,prompt=prompt)

                if inst and inst.precent < 75:
                    inst.precent += 0.01

                if not is_srt:
                    target_text["0"].append(result)
                    if not set_p:
                        tools.set_process_box(text=result + "\n",func_name="fanyi",type="set")
                    continue

                sep_res = tools.cleartext(result).split("\n")
                raw_len = len(it)
                sep_len = len(sep_res)
                # 如果返回结果相差原字幕仅少一行，对最后一行进行拆分
                if sep_len+1==raw_len:
                    config.logger.error('如果返回结果相差原字幕仅少一行，对最后一行进行拆分')
                    sep_res=tools.split_line(sep_res)
                    if sep_res:
                        sep_len=len(sep_res)

                # 如果返回数量和原始语言数量相差超过1，或再拆分失败
                if sep_len < raw_len:
                    config.logger.error(f'翻译前后数量不一致，重新单个进行翻译')
                    sep_res = []
                    for it_n in it:
                        t= get_content(it_n.strip(),prompt=prompt)
                        sep_res.append(t)

                for x,result_item in enumerate(sep_res):
                    if x < len(it):
                        target_text["srts"].append(result_item.strip().rstrip(end_point))
                        if set_p:
                            tools.set_process(result_item + "\n", 'subtitle')
                            tools.set_process(config.transobj['starttrans'] + f' {i * split_size + x+1} ',btnkey=inst.init['btnkey'] if inst else "")
                        elif not is_test:
                            tools.set_process_box(text=result_item + "\n", func_name="fanyi",type="set")
                if len(sep_res)<len(it):
                    tmp=["" for x in range(len(it)-len(sep_res))]
                    target_text["srts"]+=tmp

            except Exception as e:
                err=str(e)
                break
            else:
                # 未出错
                err=''
                iter_num=0
                index=0 if i<=1 else i
        else:
            break

    if err:
        config.logger.error(f'[302.ai]翻译请求失败:{err=}')
        if err.lower().find("Connection error")>-1:
            err='连接失败 '+err
        raise Exception(f'302.ai:{err}')

    if not is_srt:
        return "\n".join(target_text["0"])

    if len(target_text['srts']) < len(text_list)/2:
        raise Exception(f'302.ai:{config.transobj["fanyicuowu2"]}')

    for i, it in enumerate(text_list):
        if i< len(target_text['srts']):
            text_list[i]['text'] = target_text['srts'][i]
        else:
            text_list[i]['text']=""
    return text_list
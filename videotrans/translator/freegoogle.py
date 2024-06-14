# -*- coding: utf-8 -*-
import os
import re
import time
import urllib
from urllib.parse import quote
import requests
from requests import Timeout

from videotrans.configure import config
from videotrans.util import tools
import random

urls=[
"https://g0.pyvideotrans.com",
"https://g1.pyvideotrans.com"
]

shound_del=False
def update_proxy(type='set'):
    global shound_del
    if type=='del' and shound_del:
        del os.environ['http_proxy']
        del os.environ['https_proxy']
        del os.environ['all_proxy']
        shound_del=False
    elif type=='set':
        raw_proxy=os.environ.get('http_proxy')
        if not raw_proxy:
            proxy=tools.set_proxy()
            if proxy:
                shound_del=True
                os.environ['http_proxy'] = proxy
                os.environ['https_proxy'] = proxy
                os.environ['all_proxy'] = proxy
                return proxy
    return None


def trans(text_list, target_language="en", *, set_p=True,inst=None,stop=0,source_code=""):
    """
    text_list:
        可能是多行字符串，也可能是格式化后的字幕对象数组
    target_language:
        目标语言
    set_p:
        是否实时输出日志，主界面中需要
    """
    proxies=None
    pro=update_proxy(type='set')
    if pro:
        proxies={"https":pro,"http":pro}
    # 翻译后的文本
    target_text = []

    index = 0  # 当前循环需要开始的 i 数字,小于index的则跳过
    iter_num = 0  # 当前循环次数，如果 大于 config.settings.retries 出错
    err = ""
    google_url=random.choice(urls)
    while 1:
        if config.exit_soft or (config.current_status!='ing' and config.box_trans!='ing'):
            return
        if iter_num >= config.settings['retries']:
            err=f'{iter_num}{"次重试后依然出错,请尝试填写网络代理或更换其他翻译渠道" if config.defaulelang == "zh" else " retries after error persists "}:{err}'
            break

        iter_num += 1

        if iter_num > 1:
            if set_p:
                tools.set_process(
                    f"第{iter_num}次出错重试" if config.defaulelang == 'zh' else f'{iter_num} retries after error',btnkey=inst.init['btnkey'] if inst else "")
            time.sleep(10)

        # 整理待翻译的文字为 List[str]
        if isinstance(text_list, str):
            source_text = text_list.strip().split("\n")
        else:
            source_text = [f"{t['text']}" for t in text_list]

        # 切割为每次翻译多少行，值在 set.ini中设定，默认10
        split_size = int(config.settings['trans_thread'])

        split_source_text = [source_text[i:i + split_size] for i in range(0, len(source_text), split_size)]

        for i,it in enumerate(split_source_text):
            if config.exit_soft or (config.current_status != 'ing' and config.box_trans != 'ing'):
                return
            if i<index:
                continue
            if stop>0:
                time.sleep(stop)
            try:
                source_length=len(it)
                text = "\n".join(it)

                url = f"{google_url}/m?sl=auto&tl={quote(target_language)}&hl={quote(target_language)}&q={quote(text)}"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                config.logger.info(f'[FreeGoole] 发送请求:{url=}')
                response = requests.get(url,  headers=headers, timeout=300,proxies=proxies)
                config.logger.info(f'[FreeGoole] 返回:{response.text=}')
                if response.status_code != 200:
                    config.logger.error(f'{response.text=}')
                    err=f'{google_url} error_code={response.status_code}'
                    break

                re_result = re.findall(
                    r'(?s)class="(?:t0|result-container)">(.*?)<', response.text)
                if len(re_result) < 1 or not re_result[0]:
                    err=f'{google_url} {re_result}'
                    break
                result=tools.cleartext(re_result[0]).split("\n")
                result_length=len(result)
                # 如果返回数量和原始语言数量不一致，则重新切割
                if result_length<source_length:
                    print(f'翻译前后数量不一致，需要重新切割')
                    result=tools.format_result(it,result,target_lang=target_language)
                if inst and inst.precent < 75:
                    inst.precent += round((i + 1) * 5 / len(split_source_text), 2)
                if set_p:
                    tools.set_process( f'{result[0]}\n\n' if split_size==1 else "\n\n".join(result), 'subtitle')
                    tools.set_process(config.transobj['starttrans']+f' {i*split_size+1} ',btnkey=inst.init['btnkey'] if inst else "")
                else:
                    tools.set_process("\n\n".join(result), func_name="set_fanyi")
                config.logger.info(f'{result_length=},{source_length=}')
                result_length = len(result)
                while result_length<source_length:
                    result.append("")
                    result_length+=1
                result=result[:source_length]
                target_text.extend(result)

            except ConnectionError or Timeout as e:
                err=f'无法连接到 {google_url}，请正确填写代理地址'
                break
            except Exception as e:
                err =  f' {google_url} {str(e)}'
                break
            else:
                # 未出错
                err=''
                iter_num=0
                index=0 if i<=1 else i
        else:
            break

    update_proxy(type='del')

    if err:
        config.logger.error(f'[FreeGoogle]翻译请求失败:{err=}')
        if err.lower().find("Connection error")>-1:
            err='连接失败 '+err
        raise Exception(f'FreeGoogle:{err}')
    if isinstance(text_list, str):
        return "\n".join(target_text)

    max_i = len(target_text)
    if max_i < len(text_list)/2:
        raise Exception(f'FreeGoogle:{config.transobj["fanyicuowu2"]}')

    for i, it in enumerate(text_list):
        if i < max_i:
            text_list[i]['text'] = target_text[i]
        else:
            text_list[i]['text'] = ""
    return text_list

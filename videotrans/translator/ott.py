# -*- coding: utf-8 -*-
import os
import re
import time
import requests
from videotrans.configure import config
from videotrans.util import tools
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

def trans(text_list, target_language="en", *, set_p=True,inst=None,stop=0,source_code=""):
    """
    text_list:
        可能是多行字符串，也可能是格式化后的字幕对象数组
    target_language:
        目标语言
    set_p:
        是否实时输出日志，主界面中需要
    """
    url=config.params['ott_address'].strip().rstrip('/').lower().replace('/translate','')+'/translate'
    url=url.replace('//translate','/translate')
    if not url.startswith('http'):
        url=f"http://{url}"
    if re.search(r'localhost',url) or re.match(r'https?://(\d+\.){3}\d+',url):
        update_proxy(type='set')
    # 翻译后的文本
    target_text = []
    index = 0  # 当前循环需要开始的 i 数字,小于index的则跳过
    iter_num = 0  # 当前循环次数，如果 大于 config.settings.retries 出错
    err = ""
    while 1:
        if config.exit_soft or (config.current_status!='ing' and config.box_trans!='ing'):
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
        # 整理待翻译的文字为 List[str]
        if isinstance(text_list, str):
            source_text = text_list.strip().split("\n")
        else:
            source_text = [t['text'] for t in text_list]

        # 切割为每次翻译多少行，值在 set.ini中设定，默认10
        split_size = int(config.settings['trans_thread'])
        split_source_text = [source_text[i:i + split_size] for i in range(0, len(source_text), split_size)]

        for i,it in enumerate(split_source_text):
            if config.exit_soft or (config.current_status != 'ing' and config.box_trans != 'ing'):
                return
            if i < index:
                continue
            if stop>0:
                time.sleep(stop)
            try:
                source_length = len(it)
                data = {
                    "q": "\n".join(it),
                    "source": "auto",
                    "target": target_language
                }


                try:
                    response = requests.post(url=url,json=data)
                except Exception as e:
                    err=str(e)
                    break

                if response.status_code != 200:
                    err=response.text
                    break
                try:
                    result = response.json()
                except Exception:
                    err=config.transobj['notjson']+result.text
                    break

                if "error" in result:
                    err=result['error']
                    break
                result=result['translatedText'].strip().replace('&#39;','"').replace('&quot;',"'").split("\n")
                if inst and inst.precent < 75:
                    inst.precent += round((i + 1) * 5 / len(split_source_text), 2)
                if set_p:
                    tools.set_process( f'{result[0]}\n\n' if split_size==1 else "\n\n".join(result), 'subtitle')
                    tools.set_process(config.transobj['starttrans']+f' {i*split_size+1} ',btnkey=inst.init['btnkey'] if inst else "")
                else:
                    tools.set_process("\n\n".join(result), func_name="set_fanyi")
                result_length = len(result)
                while result_length < source_length:
                    result.append("")
                    result_length += 1
                result = result[:source_length]
                target_text.extend(result)
            except Exception as e:
                err = f'请检查部署和地址:{str(e)}'
                break
            else:
                err=''
                index=0 if i<=1 else i
                iter_num=0
        else:
            break
    update_proxy(type="del")

    if err:
        config.logger.error(f'[OTT]翻译请求失败:{err=}')
        raise Exception(f'OTT:{err}')

    if isinstance(text_list, str):
        return "\n".join(target_text)

    max_i = len(target_text)
    if max_i < len(text_list) / 2:
        raise Exception(f'OTT:{config.transobj["fanyicuowu2"]}')
    for i, it in enumerate(text_list):
        if i < max_i:
            text_list[i]['text'] = target_text[i]
        else:
            text_list[i]['text'] = ""
    return text_list

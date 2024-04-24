# -*- coding: utf-8 -*-
import re
import time
import urllib

import requests
from videotrans.configure import config
from videotrans.util import tools


def trans(text_list, target_language="en", *, set_p=True,inst=None,stop=0,source_code=None,is_test=False):
    """
    text_list:
        可能是多行字符串，也可能是格式化后的字幕对象数组
    target_language:
        目标语言
    set_p:
        是否实时输出日志，主界面中需要
    """
    # 翻译后的文本
    url=config.params['trans_api_url'].strip().rstrip('/').lower()
    if not url.startswith('http'):
        url=f"http://{url}"
    if url.find('?')>0:
        url+='&'
    else:
        url+='/?'
    serv = tools.set_proxy()
    proxies = None
    if serv:
        proxies = {
            'http': serv,
            'https': serv
        }
    if re.search(r'localhost',url) or re.match(r'https?://(\d+\.){3}\d+',url):
        proxies={"http":"","https":""}
    target_text = []
    index = 0  # 当前循环需要开始的 i 数字,小于index的则跳过
    iter_num = 0  # 当前循环次数，如果 大于 config.settings.retries 出错
    err = ""
    while 1:
        if config.exit_soft:
            return False
        if config.current_status!='ing' and config.box_trans!='ing' and not is_test:
            break
        if iter_num >= config.settings['retries']:
            raise Exception(
                f'{iter_num}{"次重试后依然出错" if config.defaulelang == "zh" else " retries after error persists "}:{err}')
        iter_num += 1
        if iter_num > 1:
            if set_p:
                tools.set_process(
                    f"第{iter_num}次出错重试" if config.defaulelang == 'zh' else f'{iter_num} retries after error',btnkey=inst.btnkey if inst else "")
            time.sleep(5)
        # 整理待翻译的文字为 List[str]
        if isinstance(text_list, str):
            source_text = text_list.strip().split("\n")
        else:
            source_text = [t['text'] for t in text_list]

        # 切割为每次翻译多少行，值在 set.ini 中设定，默认10
        split_size = 1#int(config.settings['trans_thread'])
        split_source_text = [source_text[i:i + split_size] for i in range(0, len(source_text), split_size)]
        response=None
        for i,it in enumerate(split_source_text):
            if config.current_status != 'ing' and config.box_trans != 'ing' and not is_test:
                break
            if i < index:
                continue
            if stop>0:
                time.sleep(stop)
            try:

                data = {
                    "text": urllib.parse.quote("".join(it)),
                    "secret":config.params['trans_secret'],
                    "source_language": 'zh' if source_code.startswith('zh') else source_code,
                    "target_language": 'zh' if target_language.startswith('zh') else  target_language
                }
                config.logger.info(f'data,{i=}, {data}')

                response = requests.get(url=f"{url}target_language={data['target_language']}&source_language={data['source_language']}&text={data['text']}&secret={data['secret']}",proxies=proxies)
                if response.status_code!=200:
                    raise Exception(f'code={response.status_code},{response.text}')
                try:
                    result = response.json()
                    if result["code"]!=0:
                        raise result['msg']
                except Exception as e:
                    raise Exception(f'{str(e)}')
                result=result['text'].strip().replace('&#39;','"').replace('&quot;',"'")
                if not result:
                    raise Exception(f'{response.text=}')

                config.logger.info(f'result,{i=}, {result=}')
                if inst and inst.precent < 75:
                    inst.precent += round((i + 1) * 5 / len(split_source_text), 2)
                if set_p:
                    tools.set_process( f'{result}\n\n')
                    tools.set_process(config.transobj['starttrans']+f' {i*split_size+1} ',btnkey=inst.btnkey if inst else "")
                else:
                    tools.set_process(result+"\n\n", func_name="set_fanyi")

                target_text.append(result)
                iter_num=0
            except Exception as e:
                error = str(e)
                config.logger.info(f'Transapi {error}')
                err=error
                index=i
                break
        else:
            break

    if isinstance(text_list, str):
        return "\n".join(target_text)

    max_i = len(target_text)
    for i, it in enumerate(text_list):
        if i < max_i:
            text_list[i]['text'] = target_text[i]
        else:
            text_list[i]['text'] = ""
    return text_list

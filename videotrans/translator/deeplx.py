# -*- coding: utf-8 -*-
import time
import requests
from videotrans.configure import config
from videotrans.util import tools


def trans(text_list, target_language="en", *, set_p=True,inst=None,stop=0):
    """
    text_list:
        可能是多行字符串，也可能是格式化后的字幕对象数组
    target_language:
        目标语言
    set_p:
        是否实时输出日志，主界面中需要
    """
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
            source_length = len(it)
            data = {
                "text": "\n".join(it),
                "source_lang": "auto",
                "target_lang": target_language
            }
            url=config.params['deeplx_address'].strip().rstrip('/').replace('/translate','')+'/translate'
            if not url.startswith('http'):
                url=f"http://{url}"
            response = requests.post(url=url, json=data, proxies={"http":"","https":""})
            if response.status_code!=200:
                raise Exception(f'code={response.status_code}')
            result = response.json()
            result=result['data'].strip().replace('&#39;','"').split("\n")
            if inst and inst.precent < 75:
                inst.precent += round((i + 1) * 5 / len(split_source_text), 2)
            if set_p:
                tools.set_process("\n\n".join(result), 'subtitle')
                tools.set_process(config.transobj['starttrans'])
            else:
                tools.set_process("\n\n".join(result), func_name="set_fanyi")
            result_length = len(result)
            while result_length < source_length:
                result.append("")
                result_length += 1
            result = result[:source_length]
            target_text.extend(result)
        except Exception as e:
            error = str(e)
            config.logger.info(f'DeepLx {error}')
            if set_p  and config.current_status=='ing':
                tools.set_process(f'出错了,等待5s后重试:{error}' if config.defaulelang=='zh' else f'wait 5s retry:{error}')
                time.sleep(5)
                return trans(text_list,target_language,set_p=set_p,stop=3,inst=inst)
            raise Exception(error)

    if isinstance(text_list, str):
        return "\n".join(target_text)

    max_i = len(target_text)
    for i, it in enumerate(text_list):
        if i < max_i:
            text_list[i]['text'] = target_text[i]
    return text_list

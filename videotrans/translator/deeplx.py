# -*- coding: utf-8 -*-
import time
import requests
from videotrans.configure import config
from videotrans.util import tools


def trans(text_list, target_language="en", *, set_p=True,inst=None,stop=0,source_code=None):
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
    index = 0  # 当前循环需要开始的 i 数字,小于index的则跳过
    iter_num = 0  # 当前循环次数，如果 大于 config.settings.retries 出错
    err = ""
    while 1:
        if config.current_status!='ing' and config.box_trans!='ing':
            break
        if iter_num >= config.settings['retries']:
            raise Exception(
                f'{iter_num}{"次重试后依然出错" if config.defaulelang == "zh" else " retries after error persists "}:{err}')
        iter_num += 1
        print(f'第{iter_num}次')
        if iter_num > 1:
            if set_p:
                tools.set_process(
                    f"第{iter_num}次出错重试" if config.defaulelang == 'zh' else f'{iter_num} retries after error')
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
            if config.current_status != 'ing' and config.box_trans != 'ing':
                break
            if i < index:
                continue
            if stop>0:
                time.sleep(stop)
            try:
                source_length = len(it)                    
                data = {
                    "text": "\n".join(it),
                    "source_lang": "auto",
                    "target_lang": 'zh' if target_language.startswith('zh') else  target_language
                }
                config.logger.info(f'data,{i=}, {data}')
                url=config.params['deeplx_address'].strip().rstrip('/').replace('/translate','')+'/translate'
                if not url.startswith('http'):
                    url=f"http://{url}"
                response = requests.post(url=url, json=data, proxies={"http":"","https":""})
                if response.status_code!=200:
                    raise Exception(f'code={response.status_code}')
                try:
                    result = response.json()
                except Exception as e:
                    raise Exception(f'{response.text=},{str(e)}')
                result=result['data'].strip().replace('&#39;','"').replace('&quot;',"'")
                if not result:
                    raise Exception(f'{response.text=}')
                result=result.split("\n")
                config.logger.info(f'result,{i=}, {result=}')
                if inst and inst.precent < 75:
                    inst.precent += round((i + 1) * 5 / len(split_source_text), 2)
                if set_p:
                    tools.set_process( f'{result[0]}\n\n' if split_size==1 else "\n\n".join(result), 'subtitle')
                    tools.set_process(config.transobj['starttrans']+f' {i*split_size+1} ')
                else:
                    tools.set_process("\n\n".join(result), func_name="set_fanyi")
                result_length = len(result)
                while result_length < source_length:
                    result.append("")
                    result_length += 1
                result = result[:source_length]
                target_text.extend(result)
                iter_num=0
            except Exception as e:
                error = str(e)
                config.logger.info(f'DeepLx {error}')
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
    return text_list

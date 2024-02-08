# -*- coding: utf-8 -*-
import time
import requests
from videotrans.configure import config
from videotrans.util import tools

def trans(text_list, target_language="en", *, set_p=True):
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
        source_text = [f"{t['text']}" for t in text_list]

    # 切割为每次翻译多少行，值在 set.ini中设定，默认10
    split_size = int(config.settings['trans_thread'])
    split_source_text = [source_text[i:i + split_size] for i in range(0, len(source_text), split_size)]
    auth=requests.get('https://edge.microsoft.com/translate/auth',proxies={"http":"","https":""})
    for it in split_source_text:
        try:
            source_length=len(it)
            text = "\n".join(it)
            url = f"https://api-edge.cognitive.microsofttranslator.com/translate?from=&to={target_language}&api-version=3.0&includeSentenceLength=true"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                "Authorization":f"Bearer {auth.text}"
            }
            response = requests.post(url,  json=[{"Text":text}],headers=headers, timeout=300,proxies={"http":"","https":""})
            if response.status_code != 200:
                config.logger.info(f'Microsoft 返回响应:{response.text}\nurl={url}')
                if set_p:
                    tools.set_process(f'error_code={response.status_code},暂停10s后重试')
                time.sleep(10)
                return trans(text_list, target_language, set_p=set_p)

            re_result=response.json()
            if len(re_result)>0 and len(re_result[0]['translations'])>0:
                result=re_result[0]['translations'][0]['text'].strip().replace('&#39;','"').split("\n")
                if set_p:
                    tools.set_process("\n\n".join(result), 'subtitle')
                else:
                    tools.set_process("\n\n".join(result), func_name="set_fanyi")
                result_length=len(result)
                config.logger.info(f'{result_length=},{source_length=}')
                while result_length<source_length:
                    result.append("")
                    result_length+=1
                result=result[:source_length]
                target_text.extend(result)
            else:
                if set_p:
                    tools.set_process(f'error_code={response.status_code},暂停10s后重试')
                    time.sleep(10)
                    return trans(text_list, target_language, set_p=set_p)
                raise Exception(f'Microsoft no result:{re_result}')
        except Exception as e:
            error = str(e)
            config.logger.error(error)
            if set_p:
                tools.set_process(f'Microsoft HTTPSConnectionPool error,5s后重试')
                time.sleep(5)
                return trans(text_list, target_language, set_p=set_p)
            raise Exception(f'Microsoft error:{str(error)}')
    if isinstance(text_list, str):
        return "\n".join(target_text)

    max_i = len(target_text)
    for i, it in enumerate(text_list):
        if i < max_i:
            text_list[i]['text'] = target_text[i]
    return text_list

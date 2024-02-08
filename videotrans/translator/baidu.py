# -*- coding: utf-8 -*-
import hashlib
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
        source_text = [t['text'] for t in text_list]

    # 切割为每次翻译多少行，值在 set.ini中设定，默认10
    split_size = int(config.settings['trans_thread'])
    split_source_text = [source_text[i:i + split_size] for i in range(0, len(source_text), split_size)]

    for it in split_source_text:
        try:
            source_length = len(it)
            text="\n".join(it)
            salt = int(time.time())
            strtext = f"{config.params['baidu_appid']}{text}{salt}{config.params['baidu_miyue']}"
            md5 = hashlib.md5()
            md5.update(strtext.encode('utf-8'))
            sign = md5.hexdigest()

            res = requests.get(
                f"http://api.fanyi.baidu.com/api/trans/vip/translate?q={text}&from=auto&to={target_language}&appid={config.params['baidu_appid']}&salt={salt}&sign={sign}")
            res = res.json()
            if "error_code" in res or "trans_result" not in res:
                config.logger.info(f'Google 返回响应:{res}')
                if res['error_msg'].find('Access Limit')>-1:
                    if set_p:
                        tools.set_process("Limit Access, stop 5s")
                    time.sleep(5)
                    return trans(text_list=text_list, target_language=target_language,set_p=set_p)
                raise Exception("[error]百度翻译失败:" + res['error_msg'])

            result = res['trans_result'][0]['dst']
            if not isinstance(result,list):
                result=result.strip().replace('&#39;','"').split("\n")
            if set_p:
                tools.set_process("\n\n".join(result), 'subtitle')
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
            raise Exception(f'Baidu error:{str(error)}')

    if isinstance(text_list, str):
        return "\n".join(target_text)

    max_i = len(target_text)
    for i, it in enumerate(text_list):
        if i < max_i:
            text_list[i]['text'] = target_text[i]
    return text_list

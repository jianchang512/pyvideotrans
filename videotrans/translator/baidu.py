# -*- coding: utf-8 -*-
import hashlib
import os
import time
import requests
from videotrans.configure import config
from videotrans.util import tools

def trans(text_list, target_language="en", *, set_p=True,inst=None,stop=0,source_code=""):
    """
    text_list:
        可能是多行字符串，也可能是格式化后的字幕对象数组
    target_language:
        目标语言
    set_p:
        是否实时输出日志，主界面中需要
    """
    proxy = os.environ.get('http_proxy')
    if proxy:
        del os.environ['http_proxy']
        del os.environ['https_proxy']
        del os.environ['all_proxy']

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
            if config.exit_soft or ( config.current_status != 'ing' and config.box_trans != 'ing'):
                return
            if i<index:
                continue
            if stop>0:
                time.sleep(stop)
            try:
                source_length = len(it)
                text="\n".join(it)
                salt = int(time.time())
                strtext = f"{config.params['baidu_appid']}{text}{salt}{config.params['baidu_miyue']}"
                md5 = hashlib.md5()
                md5.update(strtext.encode('utf-8'))
                sign = md5.hexdigest()

                requrl= f"http://api.fanyi.baidu.com/api/trans/vip/translate?q={text}&from=auto&to={target_language}&appid={config.params['baidu_appid']}&salt={salt}&sign={sign}"

                config.logger.info(f'[Baidu]请求数据:{requrl=}')
                resraw = requests.get(requrl)
                config.logger.info(f'[Baidu]返回响应:{resraw=}')
                try:
                    res = resraw.json()
                except Exception:
                    err=config.transobj['notjson']+resraw
                    break

                if "error_code" in res or "trans_result" not in res or len(res['trans_result'])<1:
                    config.logger.info(f'Baidu 返回响应:{resraw}')
                    if res['error_msg'].find('Access Limit')>-1:
                        time.sleep(10)
                        break
                    err= res['error_msg']
                    break

                result = [tools.cleartext(tres['dst']) for tres in  res['trans_result']]
                if not result or len(result)<1:
                    err=f'{resraw}'
                    break
                result_length = len(result)
                # 如果返回数量和原始语言数量不一致，则重新切割
                if result_length < source_length:
                    print(f'翻译前后数量不一致，需要重新切割')
                    result = tools.format_result(it, result, target_lang=target_language)

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
                err = str(e)
                break
            else:
                # 未出错
                err=''
                iter_num=0
                index=0 if i<=1 else i
        else:
            break

    if proxy:
        os.environ['http_proxy']=proxy
        os.environ['https_proxy']=proxy
        os.environ['all_proxy']=proxy


    if err:
        config.logger.error(f'[Baidu]翻译请求失败:{err=}')
        raise Exception(f'百度翻译:{err}')
    if isinstance(text_list, str):
        return "\n".join(target_text)

    max_i = len(target_text)
    if max_i < len(text_list) / 2:
        raise Exception(f'百度翻译：出错数量超过一半，请检查')

    for i, it in enumerate(text_list):
        if i < max_i :
            text_list[i]['text'] = target_text[i]
        else:
            text_list[i]['text'] = ""
    return text_list

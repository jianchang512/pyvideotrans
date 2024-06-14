# -*- coding: utf-8 -*-
import os
import re
import time
import httpx
from openai import AzureOpenAI, APIError
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

def get_content(d,*,model=None,prompt=None):
    message = [
        {'role': 'system', 'content': "You are a professional, authentic translation engine, only returns translations."},
        {'role': 'user', 'content': prompt.replace('[TEXT]',"\n".join(d))},
    ]

    config.logger.info(f"\n[AzureGPT]请求数据:{message=}")
    try:
        response = model.chat.completions.create(
            model=config.params["azure_model"],
            messages=message
        )
        config.logger.info(f'[AzureGPT]返回响应:{response=}')
    except APIError as e:
        config.logger.error(f'[AzureGPT]请求失败:{str(e)}')
        raise Exception(f'{e.message=}')
    except Exception as e:
        config.logger.error(f'[AzureGPT]请求失败:{str(e)}')
        raise Exception(e)

    if response.choices:
        result = response.choices[0].message.content.strip()
    elif response.data and response.data['choices']:
        result = response.data['choices'][0]['message']['content'].strip()
    else:
        config.logger.error(f'[AzureGPT]请求失败:{response=}')
        raise Exception(f"{response}")
    result = result.replace('##', '').strip().replace('&#39;', '"').replace('&quot;', "'")
    return result, response

def trans(text_list, target_language="English", *, set_p=True,inst=None,stop=0,source_code="",is_test=False):
    """
    text_list:
        可能是多行字符串，也可能是格式化后的字幕对象数组
    target_language:
        目标语言
    set_p:
        是否实时输出日志，主界面中需要
    """
    update_proxy(type='set')

    # 翻译后的文本
    target_text = {"0":[]}
    index = 0  # 当前循环需要开始的 i 数字,小于index的则跳过
    iter_num = 0  # 当前循环次数，如果 大于 config.settings.retries 出错
    err = ""
    is_srt=False if isinstance(text_list, str) else True
    # 切割为每次翻译多少行，值在 set.ini中设定，默认10
    split_size = int(config.settings['trans_thread'])

    prompt = config.params['azure_template'].replace('{lang}', target_language)
    with open(config.rootdir+"/videotrans/azure.txt",'r',encoding="utf-8") as f:
        prompt=f.read()
    prompt=prompt.replace('{lang}', target_language)

    end_point="。" if config.defaulelang=='zh' else '. '
    # 整理待翻译的文字为 List[str]
    if not is_srt:
        source_text = [t.strip() for t in text_list.strip().split("\n") if t.strip()]
    else:
        source_text=[]
        for i,it in enumerate(text_list):
            source_text.append(it['text'].strip().replace('\n','.'))
    split_source_text = [source_text[i:i + split_size] for i in range(0, len(source_text), split_size)]


    response=None
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

        client = AzureOpenAI(
            api_key=config.params["azure_key"],
            api_version="2023-05-15",
            azure_endpoint=config.params["azure_api"],
            http_client=httpx.Client()
        )


        for i,it in enumerate(split_source_text):
            if config.exit_soft or (config.current_status != 'ing' and config.box_trans != 'ing' and not is_test):
                return
            if i<index:
                continue
            if stop>0:
                time.sleep(stop)
            try:
                result,response=get_content(it,model=client,prompt=prompt)
                if inst and inst.precent < 75:
                    inst.precent += 0.01
                if not is_srt:
                    target_text["0"].append(result)
                    if not set_p:
                        tools.set_process_box(text=result + "\n", func_name="fanyi",type="set")
                    continue

                sep_res = tools.cleartext(result).split("\n")
                raw_len = len(it)
                sep_len = len(sep_res)
                # 如果返回数量和原始语言数量不一致，则重新切割
                if sep_len < raw_len:
                    print(f'翻译前后数量不一致，需要重新切割')
                    sep_res = tools.format_result(it, sep_res, target_lang=target_language)
                # if sep_len != raw_len:
                #     sep_res = []
                #     for it_n in it:
                #         t, response = get_content([it_n.strip()],model=client,prompt=prompt)
                #         sep_res.append(t)
                for x,result_item in enumerate(sep_res):
                    if x < len(it):
                        target_text["srts"].append(result_item.strip().rstrip(end_point))
                        if set_p:
                            tools.set_process(result_item + "\n", 'subtitle')
                            tools.set_process(config.transobj['starttrans'] + f' {i * split_size + x+1} ',btnkey=inst.init['btnkey'] if inst else "")
                        else:
                            tools.set_process_box(text=result_item + "\n", func_name="fanyi",type="set")
                if len(sep_res)<len(it):
                    tmp=["" for x in range(len(it)-len(sep_res))]
                    target_text["srts"]+=tmp

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


    update_proxy(type='del')

    if err:
        config.logger.error(f'[AzureGPT]翻译请求失败:{err=}')
        raise Exception(f'AzureGPT:{err}')

    if not is_srt:
        return "\n".join(target_text["0"])
    if len(target_text['srts']) < len(text_list) / 2:
        raise Exception(f'AzureGPT:{config.transobj["fanyicuowu2"]}')

    for i, it in enumerate(text_list):
        line=str(it["line"])
        if line in target_text:
            text_list[i]['text'] = target_text[line]
        else:
            text_list[i]['text']=""
    return text_list
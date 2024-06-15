# -*- coding: utf-8 -*-
import time
import requests
from requests import JSONDecodeError
from videotrans.configure import config
from videotrans.util import tools



def get_content(d,*,prompt=None,assiant=None):
    message = [
        {'role': 'system', 'content': prompt},
        {'role': 'assistant', 'content': assiant},
        {'role': 'user', 'content':  "\n".join(d)},
    ]
    config.logger.info(f"\n[字节火山引擎]发送请求数据:{message=}")
    print(f"接入点名称:{config.params['zijiehuoshan_model']}")
    try:
        req={
            "model":config.params['zijiehuoshan_model'],
            "messages":message
        }
        resp=requests.post("https://ark.cn-beijing.volces.com/api/v3/chat/completions",proxies={"https":"","http":""},json=req,headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.params['zijiehuoshan_key']}"
        })
        config.logger.info(f'[字节火山引擎]响应:{resp.text=}')
        data=resp.json()
        if 'choices' not in data or len(data['choices'])<1:
            raise Exception(f'字节火山翻译失败:{resp.text}')
        result = data['choices'][0]['message']['content'].strip()
    except JSONDecodeError as e:
        raise Exception('字节火山翻译失败，返回数据不是有效json格式')
    else:
        return result



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
    #if is_srt and split_size>1:
    prompt=config.params['zijiehuoshan_template'].replace('{lang}', target_language)
    with open(config.rootdir+"/videotrans/zijie.txt",'r',encoding="utf-8") as f:
        prompt=f.read()
    prompt=prompt.replace('{lang}', target_language)
    assiant=f"Sure, please provide the text you need translated into {target_language}"


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


        for i,it in enumerate(split_source_text):
            if config.exit_soft or  (config.current_status != 'ing' and config.box_trans != 'ing' and not is_test):
                return
            if i < index:
                continue
            if stop>0:
                time.sleep(stop)

            try:
                result=get_content(it,prompt=prompt,assiant=assiant)

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
                # 如果返回数量和原始语言数量不一致，则重新切割
                if sep_len < raw_len:
                    print(f'翻译前后数量不一致，需要重新切割')
                    sep_res = tools.format_result(it, sep_res, target_lang=target_language)

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
        config.logger.error(f'[字节火山引擎]翻译请求失败:{err=}')
        raise Exception(f'字节火山引擎:{err}')

    if not is_srt:
        return "\n".join(target_text["0"])

    if len(target_text['srts']) < len(text_list)/2:
        raise Exception(f'字节火山引擎:{config.transobj["fanyicuowu2"]}')

    for i, it in enumerate(text_list):
        if i< len(target_text['srts']):
            text_list[i]['text'] = target_text['srts'][i]
        else:
            text_list[i]['text']=""
    return text_list
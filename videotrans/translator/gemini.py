# -*- coding: utf-8 -*-

import re,os
import time
from videotrans.configure import config
from videotrans.util import tools
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold



safetySettings = [
    {
        "category": HarmCategory.HARM_CATEGORY_HARASSMENT,
        "threshold": HarmBlockThreshold.BLOCK_NONE,
    },
    {
        "category": HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        "threshold": HarmBlockThreshold.BLOCK_NONE,
    },
    {
        "category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        "threshold": HarmBlockThreshold.BLOCK_NONE,
    },
    {
        "category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        "threshold": HarmBlockThreshold.BLOCK_NONE,
    },
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

def get_error(num=5, type='error'):
    REASON_CN = {
        2: "超出长度",
        3: "安全限制",
        4: "文字过度重复",
        5: "其他原因"
    }
    REASON_EN = {
        2: "The maximum number of tokens as specified",
        3: "The candidate content was flagged for safety",
        4: "The candidate content was flagged",
        5: "Unknown reason"
    }
    forbid_cn = {
        1: "被Gemini禁止翻译:出于安全考虑，提示已被屏蔽",
        2: "被Gemini禁止翻译:由于未知原因，提示已被屏蔽"
    }
    forbid_en = {
        1: "Translation banned by Gemini:for security reasons, the prompt has been blocked",
        2: "Translation banned by Gemini:prompt has been blocked for unknown reasons"
    }
    if config.defaulelang == 'zh':
        return REASON_CN[num] if type == 'error' else forbid_cn[num]
    return REASON_EN[num] if type == 'error' else forbid_en[num]

def get_content(d,*,model=None,prompt=None):
    update_proxy(type='set')
    response=None
    try:
        message=prompt.replace('{text}',"\n".join(d))
        response = model.generate_content(
            message
        )
        config.logger.info(f'[Gemini]请求发送:{message=}')

        result = response.text.replace('##', '').strip().replace('&#39;', '"').replace('&quot;', "'")
        config.logger.info(f'[Gemini]返回:{result=}')
        if not result:
            raise Exception("fail")
        return result, response
    except Exception as e:
        error=str(e)
        config.logger.error(f'[Gemini]请求失败:{error=}')
        if response and response.prompt_feedback.block_reason:
            raise Exception(get_error(response.prompt_feedback.block_reason, "forbid"))

        if error.find('User location is not supported') > -1 or error.find('time out') > -1:
            raise Exception("当前请求ip(或代理服务器)所在国家不在Gemini API允许范围")

        if response and len(response.candidates) > 0 and response.candidates[0].finish_reason not in [0, 1]:
            raise Exception(get_error(response.candidates[0].finish_reason))

        if response and len(response.candidates) > 0 and response.candidates[0].finish_reason == 1 and \
                response.candidates[0].content and response.candidates[0].content.parts:
            result = response.text.replace('##','').strip().replace('&#39;', '"').replace('&quot;', "'")
            return result,response
        raise Exception(error)



def trans(text_list, target_language="English", *, set_p=True, inst=None, stop=0, source_code="",is_test=False):
    """
    text_list:
        可能是多行字符串，也可能是格式化后的字幕对象数组
    target_language:
        目标语言
    set_p:
        是否实时输出日志，主界面中需要
    """

    try:
        genai.configure(api_key=config.params['gemini_key'])
        model = genai.GenerativeModel('gemini-pro', safety_settings=safetySettings)
    except Exception as e:
        err = str(e)
        raise Exception(f'请正确设置http代理,{err}')

    # 翻译后的文本
    target_text = {"0": [],"srts":[]}
    index = 0  # 当前循环需要开始的 i 数字,小于index的则跳过
    iter_num = 0  # 当前循环次数，如果 大于 config.settings.retries 出错
    err = ""
    is_srt = False if  isinstance(text_list, str) else True
    split_size = int(config.settings['trans_thread'])


    prompt = config.params['gemini_template']
    with open(config.rootdir+"/videotrans/gemini.txt",'r',encoding="utf-8") as f:
        prompt=f.read()
    prompt=prompt.replace('{lang}', target_language)

    # 切割为每次翻译多少行，值在 set.ini中设定，默认10
    end_point="。" if config.defaulelang=='zh' else ' . '
    # 整理待翻译的文字为 List[str]
    if not is_srt:
        source_text = [t.strip() for t in text_list.strip().split("\n") if t.strip()]
    else:
        source_text=[]
        for i,it in enumerate(text_list):
            source_text.append(it['text'].strip().replace('\n','.')+end_point)
    split_source_text = [source_text[i:i + split_size] for i in range(0, len(source_text), split_size)]



    while 1:
        if config.exit_soft or (config.current_status != 'ing' and config.box_trans != 'ing' and not is_test):
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

        response = None
        for i, it in enumerate(split_source_text):
            if config.exit_soft or (config.current_status != 'ing' and config.box_trans != 'ing' and not is_test):
                return
            if i < index:
                continue
            if stop > 0:
                time.sleep(stop)
            try:
                result,response=get_content(it,model=model,prompt=prompt)
                if inst and inst.precent < 75:
                    inst.precent += 0.01
                if not is_srt:
                    target_text["0"].append(result)
                    if not set_p:
                        tools.set_process_box(text=result + "\n",func_name="fanyi",type="set")
                    continue

                sep_res = tools.cleartext(result).split("\n")
                raw_len=len(it)
                sep_len=len(sep_res)
                # 如果返回数量和原始语言数量不一致，则重新切割
                if sep_len<raw_len:
                    print(f'翻译前后数量不一致，需要重新切割')
                    sep_res=tools.format_result(it,sep_res,target_lang=target_language)
                # if sep_len>raw_len:
                #     sep_res[raw_len-1]=".".join(sep_len[raw_len-1:])
                #     sep_res=sep_res[:raw_len]
                # if sep_len != raw_len:
                #     sep_res=[]
                #     for it_n in it:
                #         try:
                #             t,response=get_content([it_n.strip()],model=model,prompt=prompt)
                #         except Exception as e:
                #             config.logger.error(f'触发安全限制，{t=},{it_n=}')
                #             t="--"
                #         sep_res.append(t)

                for x, result_item in enumerate(sep_res):
                    if x < len(it):
                        target_text["srts"].append(result_item.strip().rstrip(end_point))
                        if set_p:
                            tools.set_process(result_item + "\n", 'subtitle')
                            tools.set_process(config.transobj['starttrans'] + f' {i * split_size + x + 1} ',btnkey=inst.init['btnkey'] if inst else "")
                        else:
                            tools.set_process_box(text=result_item + "\n", func_name="fanyi",type="set")

                if len(sep_res) < len(it):
                    tmp = ["" for x in range(len(it) - len(sep_res))]
                    target_text["srts"] += tmp

            except Exception as e:
                err = str(e)
                break
            else:
                # 未出错
                err = ''
                iter_num = 0
                index = 0 if i <= 1 else i
        else:
            break
    update_proxy(type='del')

    if err:
        config.logger.error(f'[Gemini]翻译请求失败:{err=}')
        if err.lower().find("Connection error")>-1:
            err='连接失败 '+err
        raise Exception(f'Gemini:{err}')

    if not is_srt:
        return "\n".join(target_text["0"])

    if len(target_text['srts']) < len(text_list) / 2:
        raise Exception(f'Gemini:{config.transobj["fanyicuowu2"]}')

    for i, it in enumerate(text_list):
        if i < len(target_text['srts']):
            text_list[i]['text'] = target_text['srts'][i]
        else:
            text_list[i]['text'] = ""
    return text_list

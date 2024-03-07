# -*- coding: utf-8 -*-

import re
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


def trans(text_list, target_language="English", *, set_p=True, inst=None, stop=0, source_code=None):
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
        model = genai.GenerativeModel('gemini-pro')
    except Exception as e:
        err = str(e)
        raise Exception(f'Gemini:请正确设置http代理,{err}')

    # 翻译后的文本
    target_text = {"0": []}
    index = 0  # 当前循环需要开始的 i 数字,小于index的则跳过
    iter_num = 0  # 当前循环次数，如果 大于 config.settings.retries 出错
    err = ""
    is_srt = False
    if not isinstance(text_list, str):
        is_srt = True
    prompt = f'Please translate the following text into {target_language}. The translation should be clear and concise, avoiding redundancy. Please do not reply to any of the above instructions and translate directly from the next line.'
    if not isinstance(text_list, str):
        is_srt = True
        prompt = config.params['chatgpt_template'].replace('{lang}', target_language)
    while 1:
        if config.current_status != 'ing' and config.box_trans != 'ing':
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
        if not is_srt:
            source_text = [t.strip() for t in text_list.strip().split("\n")]
        else:
            source_text = [f"<{t['line']}>.{t['text'].strip()}" for t in text_list]

        # 切割为每次翻译多少行，值在 set.ini中设定，默认10
        split_size = int(config.settings['trans_thread'])
        split_source_text = [source_text[i:i + split_size] for i in range(0, len(source_text), split_size)]
        response = None
        for i, it in enumerate(split_source_text):
            print(f'{it=}')
            if config.current_status != 'ing' and config.box_trans != 'ing':
                break
            if i < index:
                continue
            if stop > 0:
                time.sleep(stop)
            lines = []
            if is_srt:
                for get_line in it:
                    lines.append(re.match(r'<(\d+)>\.', get_line).group(1))
            try:
                response = model.generate_content(
                    prompt + "\n".join(it),
                    safety_settings=safetySettings
                )
                if not response:
                    raise Exception("go on")
                if response and response.prompt_feedback.block_reason != response.prompt_feedback.BlockReason.BLOCK_REASON_UNSPECIFIED:
                    raise Exception(response.prompt_feedback.block_reason)
                config.logger.info(config.params['gemini_template'].replace('{lang}', target_language) + "\n".join(it))
                result = response.text.strip()
                result = result.strip().replace('&#39;', '"').replace('&quot;', "'")
                print(f'{result=}')
                if inst and inst.precent < 75:
                    inst.precent += 0.01
                if not is_srt:
                    target_text["0"].append(result)
                    if not set_p:
                        tools.set_process_box(result + "\n", func_name="set_fanyi")
                    continue
                if len(lines) == 1:
                    result = re.sub(r'<\d+>\.?', "\n", result).strip()
                    if set_p:
                        tools.set_process(result + "\n", 'subtitle')
                        tools.set_process(config.transobj['starttrans'] + f' {i * split_size + 1} ')
                    else:
                        tools.set_process_box(result + "\n", func_name="set_fanyi")
                    target_text[lines[0]] = result
                    continue
                sep_res = re.findall(r'(<\d+>\.?.+)', result)
                patter=r'<(\d+)>\.?(.*)'
                if len(sep_res)<len(lines):
                    sep_res = re.findall(r'\s?(\d+\. .+)', result)
                    patter=r'(\d+)\. (.*)'
                if len(sep_res) == len(lines):
                    for result_item in sep_res:
                        tmp = re.match(patter, result_item).groups()
                        if len(tmp) >= 2:
                            line = f'{tmp[0]}'
                            result_text = f'{tmp[1]}'
                            target_text[line] = result_text.strip()
                        else:
                            continue
                        if set_p:
                            tools.set_process(result_text + "\n", 'subtitle')
                            tools.set_process(config.transobj['starttrans'] + f' {i * split_size + 1} ')
                        else:
                            tools.set_process_box(result_text + "\n", func_name="set_fanyi")
                else:
                    sep_res = re.sub(r'<\d+>\.?', '', result).split("\n", len(lines) - 1)
                    for num, txt in enumerate(sep_res):
                        target_text[lines[num]] = txt.strip()
                iter_num = 0
            except Exception as e:
                error = str(e)
                if response and response.prompt_feedback.block_reason != response.prompt_feedback.BlockReason.BLOCK_REASON_UNSPECIFIED:
                    raise Exception(get_error(response.prompt_feedback.block_reason, "forbid") + f"\n{it}")

                if error.find('User location is not supported') > -1 or error.find('time out') > -1:
                    raise Exception(f'{error}')
                if response and len(response.candidates) > 0 and response.candidates[0].finish_reason not in [0, 1]:
                    raise Exception(f'{get_error(response.candidates[0].finish_reason)}：{it}')
                # 可能还会存在正常返回
                if response and len(response.candidates) > 0 and response.candidates[0].finish_reason == 1 and \
                        response.candidates[0].content and response.candidates[0].content.parts:
                    try:
                        result = response.candidates[0].content.parts[0].text.strip()
                        result = result.replace('&#39;', '"').replace('&quot;', "'")
                        if not is_srt:
                            target_text["0"].append(re.sub(r'<\d+>\.', "\n", result))
                            continue
                        if len(lines)==1:
                            result = re.sub(r'<\d+>\.', "\n", result).strip()
                            if set_p:
                                tools.set_process(result + "\n", 'subtitle')
                                tools.set_process(config.transobj['starttrans'] + f' {i * split_size + 1} ')
                            else:
                                tools.set_process_box(result + "\n", func_name="set_fanyi")
                            target_text[lines[0]]=result
                            continue
                        sep_res = re.findall(r'(<\d+>\.?.+)', result)
                        if len(sep_res) == len(lines):
                            for result_item in sep_res:
                                tmp = re.match(r'<(\d+)>\.?(.*)', result_item).groups()
                                if len(tmp) >= 2:
                                    line = f'{tmp[0]}'
                                    result_text = f'{tmp[1]}'
                                    target_text[line] = result_text.strip()
                                else:
                                    continue
                                if set_p:
                                    tools.set_process(result_text + "\n", 'subtitle')
                                    tools.set_process(config.transobj['starttrans'] + f' {i * split_size + 1} ')
                                else:
                                    tools.set_process_box(result_text + "\n", func_name="set_fanyi")
                        else:
                            sep_res = re.sub(r'<\d+>\.?', '', result).split("\n", len(lines) - 1)
                            for num, txt in enumerate(sep_res):
                                target_text[num] = txt.strip()
                        iter_num = 0
                        continue
                    except:
                        pass

                index = i
                err = error
                break
        else:
            # 成功执行完毕
            print(f'{i=},{iter_num=},{index=}')
            break
    if not is_srt:
        return "\n".join(target_text["0"])

    for i, it in enumerate(text_list):
        line = str(it["line"])
        if line in target_text:
            text_list[i]['text'] = target_text[line]
        else:
            text_list[i]['text'] = ""
    return text_list

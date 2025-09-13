import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Union
from urllib.parse import quote

import dashscope
import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans import translator
from videotrans.configure import config
from videotrans.configure._except import NO_RETRY_EXCEPT, StopRetry
from videotrans.translator._base import BaseTrans
from videotrans.util import tools

RETRY_NUMS = 3
RETRY_DELAY = 5


@dataclass
class QwenMT(BaseTrans):
    def __post_init__(self):
        super().__post_init__()



    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
           wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
           after=after_log(config.logger, logging.INFO))
    def _item_task(self, data: Union[List[str], str]) -> str:
        if self._exit(): return
        text = "\n".join([i.strip() for i in data]) if isinstance(data, list) else data
        model_name=config.params.get('qwenmt_model', 'qwen-mt-turbo')
        if model_name.startswith('qwen-mt'):

            messages = [
                {
                    "role": "user",
                    "content":text
                }
            ]
            try:
                target_language=translator.LANG_CODE.get(self.target_code)[9]
            except:
                # 根据zh和非zh分别显示中文和英文
                raise StopRetry( f"获取目标语言名字失败，请检查:{self.target_code=}" if config.defaulelang=='zh' else f'Failed to obtain the target language name, please check:{self.target_code=}')
            translation_options = {
                "source_lang": "auto",
                "target_lang": target_language
            }
            # 术语表
            term=tools.qwenmt_glossary()
            if term:
                translation_options['terms']=term
            if config.params.get("qwenmt_domains"):
                translation_options['domains']=config.params.get("qwenmt_domains")
            print(translation_options)

            response = dashscope.Generation.call(
                # 若没有配置环境变量，请用阿里云百炼API Key将下行替换为：api_key="sk-xxx",
                api_key=config.params.get('qwenmt_key',''),
                model=model_name,
                messages=messages,
                result_format='message',
                translation_options=translation_options
            )
            if response.code or not response.output:
                raise StopRetry(response.message)
            return self.clean_srt(response.output.choices[0].message.content)

        target_language=translator.LANG_CODE.get(self.target_code)[8]
        self.prompt = tools.get_prompt(ainame='bailian', is_srt=self.is_srt).replace('{lang}', target_language)
        message = [
            {
                'role': 'system',
                'content': "You are a top-notch subtitle translation engine." if config.defaulelang != 'zh' else '您是一名顶级的字幕翻译引擎。'},
            {
                'role': 'user',
                'content': self.prompt.replace('<INPUT></INPUT>', f'<INPUT>{text}</INPUT>')},
        ]
        response = dashscope.Generation.call(
            # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx",
            api_key=config.params.get('qwenmt_key',''),
            model=model_name,
            # 此处以qwen-plus为例，可按需更换模型名称。模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
            messages=message,
            result_format='message'
        )

        if response.code or not response.output:
            raise StopRetry(response.message)
        match = re.search(r'<TRANSLATE_TEXT>(.*?)</TRANSLATE_TEXT>', response.output.choices[0].message.content, re.S)
        if match:
            return match.group(1)
        return ''



    def clean_srt(self, srt):
        # 替换特殊符号
        srt = re.sub(r'&gt;', '>', srt)
        # ：: 换成 :
        srt = re.sub(r'([：:])\s*', ':', srt)
        # ,， 换成 ,
        srt = re.sub(r'([,，])\s*', ',', srt)
        srt = re.sub(r'([`’\'\"])\s*', '', srt)

        # 秒和毫秒间的.换成,
        srt = re.sub(r'(:\d+)\.\s*?(\d+)', r'\1,\2', srt)
        # 时间行前后加空格
        time_line = r'(\s?\d+:\d+:\d+(?:,\d+)?)\s*?-->\s*?(\d+:\d+:\d+(?:,\d+)?\s?)'
        srt = re.sub(time_line, r"\n\1 --> \2\n", srt)
        # twenty one\n00:01:18,560 --> 00:01:22,000\n
        srt = re.sub(r'\s?[a-zA-Z ]{3,}\s*?\n?(\d{2}:\d{2}:\d{2}\,\d{3}\s*?\-\->\s*?\d{2}:\d{2}:\d{2}\,\d{3})\s?\n?',
                     "\n" + r'1\n\1\n', srt)
        # 去除多余的空行
        srt = "\n".join([it.strip() for it in srt.splitlines() if it.strip()])

        # 删掉以空格或换行连接的多个时间行
        time_line2 = r'(\s\d+:\d+:\d+(?:,\d+)?)\s*?-->\s*?(\d+:\d+:\d+(?:,\d+)?\s)(?:\s*\d+:\d+:\d+(?:,\d+)?)\s*?-->\s*?(\d+:\d+:\d+(?:,\d+)?\s*)'
        srt = re.sub(time_line2, r'\n\1 --> \2\n', srt)
        srt_list = [it.strip() for it in srt.splitlines() if it.strip()]

        remove_list = []
        for it in srt_list:
            if len(remove_list) > 0 and str(it) == str(remove_list[-1]):
                if re.match(r'^\d{1,4}$', it):
                    continue
                if re.match(r'\d+:\d+:\d+([,.]\d+)? --> \d+:\d+:\d+([,.]\d+)?'):
                    continue
            remove_list.append(it)

        srt = "\n".join(remove_list)

        # 行号前添加换行符
        srt = re.sub(r'\s?(\d+)\s+?(\d+:\d+:\d+)', r"\n\n\1\n\2", srt)
        return srt.strip().replace('&#39;', '"').replace('&quot;', "'")

import logging
import re
from dataclasses import dataclass
from typing import List, Union
import dashscope
from tenacity import retry, retry_if_not_exception_type, wait_fixed, stop_after_attempt, before_log, after_log
from videotrans.configure.excepts import TranslateSrtError, NO_RETRY_EXCEPT
from videotrans.configure.config import params, logger, settings
from videotrans.translator._base import BaseTrans
from videotrans.util import tools


@dataclass
class QwenMT(BaseTrans):

    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO),after=after_log(logger, logging.INFO))
    def _item_task(self, data: Union[List[str], str]) -> str:
        if self._exit(): return
        text = "\n".join([i.strip() for i in data]) if isinstance(data, list) else data
        model_name=params.get('qwenmt_model', 'qwen-mt-turbo')
        if model_name=='qwen-turbo':
            model_name='qwen-mt-turbo'
        if model_name.startswith('qwen-mt'):
            messages = [
                {
                    "role": "user",
                    "content":text
                }
            ]
            logger.debug(f'qwen-mt请求:{messages}')

            translation_options = {
                "source_lang": "auto",
                "target_lang": self.target_language_name
            }
            # 术语表
            term=tools.qwenmt_glossary()
            if term:
                translation_options['terms']=term
            if params.get("qwenmt_domains"):
                translation_options['domains']=params.get("qwenmt_domains")


            response = dashscope.Generation.call(
                # 若没有配置环境变量，请用阿里云百炼API Key将下行替换为：api_key="sk-xxx",
                api_key=params.get('qwenmt_key',''),
                model=model_name,
                messages=messages,
                result_format='message',
                translation_options=translation_options
            )
            if response.code or not response.output:
                raise TranslateSrtError(response.message)
            if not response.output.choices:
                raise TranslateSrtError(f'qwen-mt returned empty choices')
            logger.debug(f'qwen-mt返回响应:{response.output.choices[0].message.content}')
            return self.clean_srt(response.output.choices[0].message.content)

        self.prompt = tools.get_prompt(ainame='bailian',aisendsrt=self.aisendsrt).replace('{lang}', self.target_language_name)
        message = [
            {
                'role': 'system',
                'content':'You are a top-tier Subtitle Translation Engine.'},
            {
                'role': 'user',
                'content': self.prompt.replace('{batch_input}', f'{text}')
                },
        ]
        response = dashscope.Generation.call(
            # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx",
            api_key=params.get('qwenmt_key',''),
            model=model_name,
            # 此处以qwen-plus为例，可按需更换模型名称。模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
            messages=message,
            result_format='message'
        )

        if response.code or not response.output:
            if "url error" in response.message:
                raise TranslateSrtError(f'需要纯文本模型，但 {model_name} 可能是多模态模型')
            raise TranslateSrtError(response.message)
        if not response.output.choices:
            raise TranslateSrtError(f'qwen-mt returned empty choices')
        logger.debug(f'阿里百炼 AI响应:{response.output.choices[0].message.content}')
        # match = re.search(r'<TRANSLATE_TEXT>(.*?)</TRANSLATE_TEXT>', response.output.choices[0].message.content, re.S)
        result = response.output.choices[0].message.content
        match = re.search(r'<TRANSLATE_TEXT>(.*?)</TRANSLATE_TEXT>', result, re.S)
        if match:
            return match.group(1)
        return result.strip()



    def clean_srt(self, srt):
        # 替换特殊符号
        srt = re.sub(r'&gt;', '>', srt,flags=re.I | re.S)
        # ：: 换成 :
        srt = re.sub(r'([：:])\s*', ':', srt,flags=re.I | re.S)
        # ,， 换成 ,
        srt = re.sub(r'([,，])\s*', ',', srt,flags=re.I | re.S)
        srt = re.sub(r'([`’\"])\s*', '', srt,flags=re.I | re.S)

        # 秒和毫秒间的.换成,
        srt = re.sub(r'(:\d+)\.\s*?(\d+)', r'\1,\2', srt,flags=re.I | re.S)
        # 时间行前后加空格
        time_line = r'(\s?\d+:\d+:\d+(?:,\d+)?)\s*?-->\s*?(\d+:\d+:\d+(?:,\d+)?\s?)'
        srt = re.sub(time_line, r"\n\1 --> \2\n", srt,flags=re.I | re.S)
        # twenty one\n00:01:18,560 --> 00:01:22,000\n
        #srt = re.sub(r'\s?[a-zA-Z ]{3,}\s*?\n?(\d{2}:\d{2}:\d{2},\d{3}\s*?-->\s*?\d{2}:\d{2}:\d{2},\d{3})\s?\n?',
        # "\n" + r'1\n\1\n', srt,flags=re.I | re.S)
        srt = re.sub(r'\s?([a-zA-Z ]{3,})\s*?\n?(\d{2}:\d{2}:\d{2}\,\d{3}\s*?\-\->\s*?\d{2}:\d{2}:\d{2}\,\d{3})\s?\n?', r'\n1\n\2\n\1', srt,flags=re.I | re.S)
        # 去除多余的空行
        srt = "\n".join([it.strip() for it in srt.splitlines() if it.strip()])

        # 删掉以空格或换行连接的多个时间行
        time_line2 = r'(\s\d+:\d+:\d+(?:,\d+)?)\s*?-->\s*?(\d+:\d+:\d+(?:,\d+)?\s)(?:\s*\d+:\d+:\d+(?:,\d+)?)\s*?-->\s*?(\d+:\d+:\d+(?:,\d+)?\s*)'
        srt = re.sub(time_line2, r'\n\1 --> \2\n', srt,flags=re.I | re.S)
        srt_list = [it.strip() for it in srt.splitlines() if it.strip()]

        remove_list = []
        for it in srt_list:
            if len(remove_list) > 0 and str(it) == str(remove_list[-1]):
                if re.match(r'^\d{1,4}$', it):
                    continue
                if re.match(r'\d+:\d+:\d+([,.]\d+)? --> \d+:\d+:\d+([,.]\d+)?',it):
                    continue
            remove_list.append(it)

        srt = "\n".join(remove_list)

        # 行号前添加换行符
        srt = re.sub(r'\s?(\d+)\s+?(\d+:\d+:\d+)', r"\n\n\1\n\2", srt,flags=re.I | re.S)
        # return srt.strip().replace('&#39;', '"').replace('&quot;', "'")
        return srt.strip().replace('&#39;', "'").replace('&quot;', '"')

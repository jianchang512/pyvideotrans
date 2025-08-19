# -*- coding: utf-8 -*-
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Union

import httpx
import json
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure import config
from videotrans.configure._except import RetryRaise
from videotrans.translator._base import BaseTrans
from videotrans.util import tools

RETRY_NUMS = 2
RETRY_DELAY = 10


@dataclass
class ChatGPT(BaseTrans):
    prompt: str = field(init=False)

    def __post_init__(self):
        super().__post_init__()
        self.trans_thread = int(config.settings.get('aitrans_thread', 50))
        self.api_url = self._get_url(config.params['chatgpt_api'])
        self.model_name = config.params["chatgpt_model"]

        self.prompt = tools.get_prompt(ainame='chatgpt', is_srt=self.is_srt).replace('{lang}',
                                                                                     self.target_language_name)

        self._check_proxy()

    def llm_segment(self, words_all, inst=None, ai_type='openai'):
        config.logger.info('llm_segment:self._exit()=' + str(self._exit()))
        # if self._exit(): return
        # 以2000个字或单词分成一批
        prompts_template = Path(config.ROOT_DIR + '/videotrans/recharge-llm.txt').read_text(encoding='utf-8')
        chunk_size = int(config.settings.get('llm_chunk_size', 500))

        @retry(retry=retry_if_not_exception_type(RetryRaise.NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
               wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
               after=after_log(config.logger, logging.INFO), retry_error_callback=RetryRaise._raise)
        def _send(words, batch_num=0):
            prompts = json.dumps(words, ensure_ascii=False)

            message = [
                {"role": "system", "content": prompts_template},
                {
                    'role': 'user',
                    'content': prompts
                }
            ]
            config.logger.info(f'需要断句的:{message=}')

            api_key = config.params['chatgpt_key'] if ai_type == 'openai' else config.params['deepseek_key']
            model_name = config.params['chatgpt_model'] if ai_type == 'openai' else config.params['deepseek_model']
            api_url = self._get_url(
                config.params['chatgpt_api']) if ai_type == 'openai' else 'https://api.deepseek.com/v1'
            proxy = None
            pro = self._set_proxy(type='set')
            if pro:
                proxy = pro
            config.logger.info(f'LLM re-segments:{api_url=},{pro=}')
            model = OpenAI(api_key=api_key, base_url=api_url, http_client=httpx.Client(proxy=proxy, timeout=7200))

            msg = f'第{batch_num}批次 LLM断句，每批次 {chunk_size} 个字或单词' if config.defaulelang == 'zh' else f'Start sending {batch_num} batches of LLM segments, {chunk_size} words per batch'
            config.logger.info(msg)
            if inst:
                inst.status_text = msg
                self._signal(text=msg)
            response = model.chat.completions.create(
                model=model_name,
                max_completion_tokens=max(int(config.params.get('chatgpt_max_token', 8192)), 8192),
                messages=message,
                response_format={"type": "json_object"}
            )
            msg = f'第{batch_num}批次 LLM断句 完成' if config.defaulelang == 'zh' else f'Ended  {batch_num} batches of LLM segments'
            config.logger.info(msg)
            if inst:
                inst.status_text = msg
                self._signal(text=msg)

            if not hasattr(response, 'choices') or not response.choices:
                config.logger.error(f'[LLM re-segments]第{batch_num}批次重新断句失败:{response=}')
                raise RuntimeError(f"no choices:{response=}")

            if response.choices[0].finish_reason == 'length':
                raise RuntimeError(f"Please increase max_token")
            if not response.choices[0].message.content:
                config.logger.error(f'[LLM re-segments]第{batch_num}批次重新断句失败:{response=}')
                raise RuntimeError(f"no choices:{response=}")

            result = response.choices[0].message.content

            j = json.loads(result)
            if isinstance(j, dict) and "subtitles" in j:
                return j['subtitles']
            if isinstance(j, dict) and "output" in j and "subtitles" in j['output']:
                return j['output']['subtitles']
            config.logger.error(f'LLM断句获取list失败，返回数据:{result=}')
            raise RuntimeError(f'No valid json data is returned. {j.get("error", "") if isinstance(j, dict) else ""}')

        new_sublist = []
        order_num = 0
        for idx in range(0, len(words_all), chunk_size):
            order_num += 1
            sub_list = _send(words_all[idx: idx + chunk_size], order_num)
            config.logger.info(f'LLM断句结果:{sub_list=}')
            for i, s in enumerate(sub_list):
                tmp = {}
                tmp['startraw'] = tools.ms_to_time_string(ms=s["start"] * 1000)
                tmp['endraw'] = tools.ms_to_time_string(ms=s["end"] * 1000)
                tmp['time'] = f"{tmp['startraw']} --> {tmp['endraw']}"
                tmp['text'] = s['text'].strip()
                tmp['line'] = i + 1
                new_sublist.append(tmp)
        return new_sublist

    def _check_proxy(self):
        if self.api_url and (
                re.search('localhost', self.api_url) or re.match(r'^https?://(\d+\.){3}\d+(:\d+)?', self.api_url)):
            self.proxies = None
            return
        pro = self._set_proxy(type='set')
        if pro:
            self.proxies = pro

    def _get_url(self, url=""):
        if not url:
            return "https://api.openai.com/v1"
        if not url.startswith('http'):
            url = 'http://' + url
            # 删除末尾 /
        url = url.rstrip('/').lower()
        if url.find(".openai.com") > -1:
            return "https://api.openai.com/v1"
        if url.endswith('/v1'):
            return url
        # 存在 /v1/xx的，改为 /v1
        if url.endswith('/v1/chat/completions'):
            return re.sub(r'/v1.*$', '/v1', url)

        if re.match(r'^https?://[^/]+[a-zA-Z]+$', url):
            return url + "/v1"
        return url

    @retry(retry=retry_if_not_exception_type(RetryRaise.NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
           wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
           after=after_log(config.logger, logging.INFO), retry_error_callback=RetryRaise._raise)
    def _item_task(self, data: Union[List[str], str]) -> str:
        if self._exit(): return
        text = "\n".join([i.strip() for i in data]) if isinstance(data, list) else data
        message = [
            {
                'role': 'system',
                'content': "You are a top-notch subtitle translation engine." if config.defaulelang != 'zh' else '您是一名顶级的字幕翻译引擎。'},
            {
                'role': 'user',
                'content': self.prompt.replace('<INPUT></INPUT>', f'<INPUT>{text}</INPUT>')},
        ]

        config.logger.info(f"\n[chatGPT]发送请求数据:{message=}")
        model = OpenAI(api_key=config.params['chatgpt_key'], base_url=self.api_url,
                       http_client=httpx.Client(proxy=self.proxies, timeout=7200))
        response = model.chat.completions.create(
            model=config.params['chatgpt_model'],
            timeout=7200,
            max_completion_tokens=int(config.params.get('chatgpt_max_token', 8192)),
            messages=message
        )
        config.logger.info(f'[chatGPT]响应:{response=}')
        result = ""
        if hasattr(response, 'choices') and response.choices:
            result = response.choices[0].message.content.strip()
        else:
            config.logger.error(f'[chatGPT]请求失败:{response=}')
            raise RuntimeError(f"no choices:{response=}")

        match = re.search(r'<TRANSLATE_TEXT>(.*?)</TRANSLATE_TEXT>',
                          re.sub(r'<think>(.*?)</think>', '', result, re.S | re.I), re.S | re.I)
        if match:
            return match.group(1)
        return result.strip()

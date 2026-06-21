# -*- coding: utf-8 -*-
import logging,json
import re
import time,httpcore,httpx
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Union
from openai import OpenAI, LengthFinishReasonError,NotFoundError, AuthenticationError, PermissionDeniedError,BadRequestError,APIConnectionError,APIError
from tenacity import before_log, retry_if_not_exception_type, wait_fixed, stop_after_attempt, after_log, retry

from videotrans.configure.excepts import NO_RETRY_EXCEPT, TranslateSrtError, LLMSegmentError, StopTask
from videotrans.configure.config import logger, settings, params, ROOT_DIR, tr
from videotrans.task.taskcfg import SrtItem
from videotrans.translator._base import BaseTrans

from videotrans.util import tools


@dataclass
class OpenAICampat(BaseTrans):
    ainame:str=None
    prompt: str = field(init=False)
    api_key: str = field(init=False)
    api_url: str = field(init=False)
    temperature:float=1.0
    max_tokens:int=8192
    reasoning_effort:str=None
    extra_body:Union[dict,None]=None

    def __post_init__(self):
        super().__post_init__()
        self.temperature=float(settings.get('aitrans_temperature', 1.0))
        self.prompt = tools.get_prompt(ainame=self.ainame,aisendsrt=self.aisendsrt).replace('{lang}',self.target_language_name)
        try:
            self.max_tokens=int(self.max_tokens)
        except (ValueError,TypeError) as e:
            logger.error(f'当前渠道{self.ainame}设置的最大输出tokens错误，应填写整数，实际填写的是`{self.max_tokens}`\n{e}')
            self.max_tokens=8192

    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO),after=after_log(logger, logging.INFO))
    def _item_task(self, data: Union[List[str], str]) -> str:
        if self._exit(): return
        if len(self.api_url)<10:
            raise StopTask(f'API URL is error: {self.api_url}')
        
        text = "\n".join([i.strip() for i in data]) if isinstance(data, list) else data
        
        message = [
            {
                'role': 'system',
                'content': 'You are a top-tier Subtitle Translation Engine.'},
            {
                'role': 'user',
                'content': self.prompt.replace('{batch_input}', f'{text}')
            },
        ]


        kwargs={
            "model":self.model_name,
            "timeout":300,
            "temperature":float(self.temperature)            
        }
        # 针对 openai 官方或 GPT模型，使用 max_completion_tokens 参数，其他第三方使用 max_tokens 参数            
        if "api.openai.com" in self.api_url or (self.ainame=='chatgpt' and re.match(r'^(gpt|o\d)', self.model_name, flags=re.I)):
            kwargs["max_completion_tokens"]=int(self.max_tokens)
        else:
            kwargs["max_tokens"]=int(self.max_tokens)
        
        if self.reasoning_effort:
            kwargs["reasoning_effort"]=self.reasoning_effort
            
        logger.debug(f'字幕翻译:[{self.ainame=},{kwargs=}]')
        kwargs["messages"]=message
        try:
            model = OpenAI(api_key=self.api_key, base_url=self.api_url)
            response = model.chat.completions.create(**kwargs, extra_body=self.extra_body)
        except APIConnectionError as e:
            raise StopTask(f'[{self.ainame}] {tr("Unable to connect to API",self.api_url)}\n{e.body.get("message")}') from e
        except (NotFoundError,AuthenticationError,PermissionDeniedError,BadRequestError) as e:
            del kwargs['messages']
            raise StopTask(e.body.get('message')+f'\n{self.api_url}\n{kwargs}') from e
        except APIError as e: 
            if re.search(r"insufficient.*?balance",e.message,flags=re.I):
                raise StopTask(tr('The server returned an error message: Insufficient balance',tools.get_tanslate_type(self.translate_type),self.api_url))
            raise
            
        result = ""
        if not hasattr(response,'choices') or not response.choices:
            raise TranslateSrtError(str(response))
        if response.choices[0].finish_reason=='length':
            raise LengthFinishReasonError(completion=response)
        if not response.choices[0].message.content:
            logger.warning(f'[{self.ainame}]请求失败:{response=}')
            raise TranslateSrtError(f"[{self.ainame}] {self.api_url} {response.choices[0].finish_reason}:{response}")
        result = response.choices[0].message.content.strip()
        match = re.search(r'<TRANSLATE_TEXT>(.*?)</TRANSLATE_TEXT>', re.sub(r'<think>(.*?)</think>', '',result), re.S)
        if match:
            return match.group(1)
        return result.strip()


    def llm_segment(self, srt_list,step='')->List[SrtItem]:
        _st=time.time()
        api_url=params.get('chatgpt_api') if self.ainame!='deepseek' else 'https://api.deepseek.com/v1/'
        if len(api_url)<10:
            raise StopTask(f'API URL is error: {api_url}')

        prompts_template = Path(f'{ROOT_DIR}/videotrans/prompts/recharge/recharge-llm{step}.txt').read_text(encoding='utf-8')
        prompts_template = prompts_template.replace('{max_speech_s}', str(settings.get('max_speech_duration_s', 6)))
        chunk_size = int(settings.get('llm_chunk_size', 20))
        model_name=params.get(f'{self.ainame}_model')
        max_tokens=max(8192,int( float(params.get(f'{self.ainame}_max_token', 8192)) ))
        temperature=float(settings.get('aitrans_temperature', 1.0))
        api_key=params.get(f'{self.ainame}_key')           
        reasoning_effort='high' if self.ainame=='deepseek' else None
        
        if reasoning_effort is None:
            _reason=params.get('chatgpt_reasoning_effort')
            reasoning_effort=None if not _reason or _reason=='No' else _reason
        
        kwargs={
                "model":model_name,
                
                "temperature":temperature,
                "timeout":300,  # 超过5分钟为失败           
        }
        if reasoning_effort:
            kwargs['reasoning_effort']=reasoning_effort
        if "api.openai.com" in api_url or ( self.ainame=='chatgpt' and re.match(r'^(gpt|o\d)', model_name, flags=re.I)):
            kwargs["max_completion_tokens"]=int(max_tokens)
        else:
            kwargs["max_tokens"]=int(max_tokens)
        logger.debug(f'LLM Re-segmenting:{self.ainame=},{kwargs=}')
        @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(2)),
               wait=wait_fixed(5), before=before_log(logger, logging.INFO),
               after=after_log(logger, logging.INFO))
        def _send(srt):
            nonlocal kwargs
            
            message = [
                {"role": "system", "content": prompts_template},
                {
                    'role': 'user',
                    'content': f"""```srt\n{srt}\n```"""
                }
            ]
            kwargs["messages"]=message
            model = OpenAI(api_key=api_key, base_url=api_url)
            response = model.chat.completions.create(
                    **kwargs,
                    extra_body={"thinking": {"type": "enabled"}} if self.ainame=='deepseek' else None
            )
            if not hasattr(response, 'choices') or not response.choices:
                logger.warning(f'[{self.ainame}]重新断句失败:{response=}')
                raise LLMSegmentError(f"[{self.ainame}]{response}")

            if response.choices[0].finish_reason == 'length':
                raise LLMSegmentError(f"[{self.ainame}] Please increase max_token")
            if not response.choices[0].message.content:
                logger.warning(f'[{self.ainame}]重新断句失败:{response=}')
                raise LLMSegmentError(f"[{self.ainame}] {response}")

            result = response.choices[0].message.content
            match = re.search(r'<SRT>(.*?)</SRT>', re.sub(r'<think>(.*?)</think>', '', result, flags=re.I | re.S), re.S | re.I)
            if match:
                return match.group(1)
            return result.strip()
        
        logger.debug(f'LLM断句:{self.ainame=},{model_name=},{api_url=}')
        new_sublist = []
        for idx in range(0, len(srt_list), chunk_size):
            self.signal(text=f'[{idx}] {self.ainame} ' + tr("Re-segmenting..."))
            srt_str = "\n\n".join(
                [f"{line + 1}\n{it['time']}\n{it['text']}" for line, it in enumerate(srt_list[idx: idx + chunk_size])])
            new_sublist.append(_send(srt_str))

        _srtlist = tools.get_subtitle_from_srt("\n\n".join(new_sublist), is_file=False)
        # 修正可能存在的时间戳错误
        _len = len(_srtlist)
        for i, it in enumerate(_srtlist):
            _had_edit = False
            if i < _len - 1 and it['end_time'] > _srtlist[i + 1]['start_time']:
                it['end_time'] = _srtlist[i + 1]['start_time']
                _had_edit = True
            if it['start_time'] > it['end_time']:
                it['start_time'] = it['end_time']
                _had_edit = True
            if _had_edit:
                it['startraw'] = tools.ms_to_time_string(ms=it['start_time'])
                it['endraw'] = tools.ms_to_time_string(ms=it['end_time'])
                it["time"] = f"{it['startraw']} --> {it['endraw']}"
        logger.debug(f'{"【二次识别后】"  if step else ""}LLM重新断句完成,原始字幕行:{len(srt_list)}, 新字幕行:{len(_srtlist)}, 用时:{time.time()-_st}s')
        return _srtlist

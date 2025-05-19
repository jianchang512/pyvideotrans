# -*- coding: utf-8 -*-
import re,math,time
from pathlib import Path
from typing import Union, List

import httpx,requests,json
from openai import OpenAI, APIConnectionError, APIError,RateLimitError

from videotrans.configure import config
from videotrans.translator._base import BaseTrans
from videotrans.util import tools


class ChatGPT(BaseTrans):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.trans_thread=int(config.settings.get('aitrans_thread',50))
        self.api_url = self._get_url(config.params['chatgpt_api'])
        if not config.params['chatgpt_key']:
            raise Exception('必须在翻译设置 - OpenAI ChatGPT 填写 SK' if config.defaulelang=='zh' else 'please input your sk password')
        
        # 是srt则获取srt的提示词
        self.prompt = tools.get_prompt(ainame='chatgpt',is_srt=self.is_srt).replace('{lang}', self.target_language_name)
        self._check_proxy()
        self.model_name=config.params["chatgpt_model"]

    def llm_segment(self,words_all,inst=None):
        # 以2000个字或单词分成一批
        prompts_template=Path(config.ROOT_DIR+'/videotrans/recharge-llm.txt').read_text(encoding='utf-8')
        chunk_size=int(config.settings.get('llm_chunk_size',2000))
        
        
        def _send(words,batch_num=0):        
            prompts=prompts_template.replace('<INPUT></INPUT>','<INPUT>'+json.dumps(words,ensure_ascii=False)+'</INPUT>')
            

            message = [
                {
                    'role': 'user',
                    'content': prompts
                }
            ]
            #config.logger.info(f'{prompts=}')
            model = OpenAI(api_key=config.params['chatgpt_key'], base_url=self.api_url,
                           http_client=httpx.Client(proxy=self.proxies,timeout=7200))
            try:
                msg=f'第{batch_num}批次 LLM断句，每批次 {chunk_size} 个字或单词' if config.defaulelang=='zh' else f'Start sending {batch_num} batches of LLM segments, {chunk_size} words per batch'
                config.logger.info(msg)
                if inst:
                    inst.status_text=msg
                response = model.chat.completions.create(
                    model='gpt-4o-mini' if config.params['chatgpt_model'].lower().find('gpt-3.5') > -1 else config.params['chatgpt_model'],
                    timeout=7200,
                    max_tokens= max(int(config.params.get('chatgpt_max_token')) if config.params.get('chatgpt_max_token') else 4096,4096),
                    messages=message
                )
                msg=f'第{batch_num}批次 LLM断句 完成' if config.defaulelang=='zh' else f'Ended  {batch_num} batches of LLM segments'
                config.logger.info(msg)
                if inst:
                    inst.status_text=msg
            except RateLimitError:
                config.logger.error(f'[chatGPT]第{batch_num}批次重新断句失败:429请求频繁，暂停10s后重试')
                time.sleep(10)
                return _send(words,batch_num=0)
            except APIConnectionError as e:
                config.logger.exception(e, exc_info=True)            
                raise Exception('无法连接到OpenAI服务，请尝试使用或更换代理' if config.defaulelang == 'zh' else 'Cannot connect to OpenAI service, please try using or changing proxy')
            except APIError as e:
                config.logger.exception(e,exc_info=True)
                raise
            except Exception as e:
                config.logger.exception(e,exc_info=True)
                raise

            if not hasattr(response,'choices'):
                config.logger.error(f'[chatGPT]第{batch_num}批次重新断句失败:{response=}')
                raise Exception(f"no choices:{response=}")
            if response.choices[0].finish_reason=='length':
                raise Exception(f"请增加最大输出token或降低LLM重新断句每批次字/单词数")
            if not response.choices[0].message.content:
                config.logger.error(f'[chatGPT]第{batch_num}批次重新断句失败:{response=}')
                raise Exception(f"no choices:{response=}")
                
            result = response.choices[0].message.content.strip()
            match = re.search(r'<DICT_LIST>(.*?)(</DICT_LIST>|$)',result, re.S|re.I)
            if not match:
                config.logger.error(f'[chatGPT]第{batch_num}批次重新断句失败:{result=}')
                raise Exception(f"ChatGPT 重新断句失败")
            llm_result=match.group(1).replace("\n","").strip()
            config.logger.info(f'第{batch_num}批次LLM断句结果:{llm_result}')
            sub_list=json.loads( re.sub(r'\,\]$',']', llm_result))
            return sub_list
        
        
        new_sublist=[]
        order_num=0
        for idx in range(0, len(words_all), chunk_size):
            order_num+=1        
            sub_list=_send(words_all[idx : idx + chunk_size],order_num)
            for i,s in enumerate(sub_list):
                tmp={}
                tmp['startraw']=tools.ms_to_time_string(ms=s["start"]*1000)
                tmp['endraw']=tools.ms_to_time_string(ms=s["end"]*1000)
                tmp['time'] = f"{tmp['startraw']} --> {tmp['endraw']}"
                tmp['text']=s['text'].strip()
                tmp['line']=i+1
                new_sublist.append(tmp)
        return new_sublist

        
    def _check_proxy(self):
        if re.search('localhost', self.api_url) or re.match(r'^https?://(\d+\.){3}\d+(:\d+)?', self.api_url):
            self.proxies=None
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

        if re.match(r'^https?://[^/]+[a-zA-Z]+$',url):
            return url + "/v1"
        return url

    def _item_task(self, data: Union[List[str], str]) -> str:
        if self.refine3:
            return self._item_task_refine3(data)
        text="\n".join([i.strip() for i in data]) if isinstance(data,list) else data    
        message = [
            {
                'role': 'system',
                'content': "You are a translation assistant specializing in converting SRT subtitle content from one language to another while maintaining the original format and structure." if config.defaulelang != 'zh' else '您是一名翻译助理，专门负责将 SRT 字幕内容从一种语言转换为另一种语言，同时保持原始格式和结构。'},
            {
                'role': 'user',
                'content': self.prompt.replace('<INPUT></INPUT>',f'<INPUT>{text}</INPUT>')},
        ]

        config.logger.info(f"\n[chatGPT]发送请求数据:{message=}")
        model = OpenAI(api_key=config.params['chatgpt_key'], base_url=self.api_url,
                       http_client=httpx.Client(proxy=self.proxies,timeout=7200))
        try:
            response = model.chat.completions.create(
                model='gpt-4o-mini' if config.params['chatgpt_model'].lower().find('gpt-3.5') > -1 else config.params['chatgpt_model'],
                timeout=7200,
                max_tokens= int(config.params.get('chatgpt_max_token')) if config.params.get('chatgpt_max_token') else 4096,
                temperature=float(config.params.get('chatgpt_temperature',0.7)),
                top_p=float(config.params.get('chatgpt_top_p',1.0)),
                messages=message
            )
        except APIError as e:
            config.logger.exception(e,exc_info=True)
            raise
        except Exception as e:
            config.logger.exception(e,exc_info=True)
            raise
        config.logger.info(f'[chatGPT]响应:{response=}')
        result=""
        if response.choices:
            result = response.choices[0].message.content.strip()
        else:
            config.logger.error(f'[chatGPT]请求失败:{response=}')
            raise Exception(f"no choices:{response=}")
        
        match = re.search(r'<TRANSLATE_TEXT>(.*?)</TRANSLATE_TEXT>', re.sub(r'<think>(.*?)</think>','',result,re.S|re.I),re.S|re.I)
        if match:
            return match.group(1)
        return result.strip()


    def _item_task_refine3(self, data: Union[List[str], str]) -> str:
        prompt=self._refine3_prompt()
        text="\n".join([i.strip() for i in data]) if isinstance(data,list) else data
        prompt=prompt.replace('{lang}',self.target_language_name).replace('<INPUT></INPUT>',f'<INPUT>{text}</INPUT>')

        message = [
            {
                'role': 'system',
                'content':  "You are a translation assistant specializing in converting SRT subtitle content from one language to another while maintaining the original format and structure." if config.defaulelang != 'zh' else '您是一名翻译助理，专门负责将 SRT 字幕内容从一种语言转换为另一种语言，同时保持原始格式和结构。'},
            {
                'role': 'user',
                'content': prompt},
        ]

        config.logger.info(f"\n[chatGPT]发送请求数据:{message=}")
        model = OpenAI(api_key=config.params['chatgpt_key'], base_url=self.api_url,
                       http_client=httpx.Client(proxy=self.proxies,timeout=7200))
        try:
            response = model.chat.completions.create(
                model=config.params['chatgpt_model'],
                timeout=7200,
                max_tokens=4096,
                messages=message
            )
        except APIConnectionError as e:
            config.logger.error(f'[chatGPT]:{e=}')
            raise
        config.logger.info(f'[chatGPT]响应:{response=}')

        if response.choices:
            result = response.choices[0].message.content.strip()
        else:
            config.logger.error(f'[chatGPT]请求失败:{response=}')
            raise Exception(f"no choices:{response=}")

        match = re.search(r'<step3_refined_translation>(.*?)</step3_refined_translation>', re.sub(r'<think>(.*?)</think>','',result,re.S|re.I), re.S|re.I)
        if not match:
            match = re.search(r'<TRANSLATE_TEXT>(.*?)</TRANSLATE_TEXT>', re.sub(r'<think>(.*?)</think>','',result,re.S|re.I), re.S|re.I)
        if match:
            return match.group(1)
        return result.strip()
        
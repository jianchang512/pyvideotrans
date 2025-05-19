# -*- coding: utf-8 -*-

import re
import socket
from typing import Union, List
import requests
import google
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from google.api_core.exceptions import ServerError,TooManyRequests,RetryError

safetySettings = {
    'HATE': 'BLOCK_NONE',
    'HARASSMENT': 'BLOCK_NONE',
    'SEXUAL' : 'BLOCK_NONE',
    'DANGEROUS' : 'BLOCK_NONE'
}


# 代理修改  site-packages\google\ai\generativelanguage_v1beta\services\generative_service\transports\grpc_asyncio.py __init__方法的 options 添加 ("grpc.http_proxy",os.environ.get('http_proxy') or os.environ.get('https_proxy'))
class Gemini():
       
        
    def _item_task(self, filename):
        while 1:
        try:
            response = None
            api_key='AIzaSyDdZkHTkKu3D3wiqvRk5n_9gDd5rrhw4zs'
            genai.configure(api_key=api_key)
            
            model = genai.GenerativeModel(
                model_name='gemini-2.0-flash',
                generation_config={"max_output_tokens": 8192},
                system_instruction="请将我发给你的markdown文章翻译为英文，并实现人类翻译的高质量，翻译中请保留markdown中的所有标记，例如图片、链接等。你只需要返回翻译结果，不要附加其他任何内容"
                )
            with open(filename,'r',encoding='utf-8') as f:
                message=f.read()
            response = model.generate_content(
                message,
                safety_settings=safetySettings
            )

            result = response.text      
            with open(filename,'w',encoding='utf-8') as f:
                f.write(result)
            break
        except TooManyRequests as e:
            print('429超过请求次数，请尝试更换其他Gemini模型后重试')
            time.sleep(10)
        except Exception as e:
            error = str(e)
            print(f'{error=}')
            with open('error.txt','a',encoding='utf-8') as f:
                f.write(f"\n{filename=}\n{error=}\n=====\n")



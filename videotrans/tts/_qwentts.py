import logging
from dataclasses import dataclass
from typing import Union, Dict, List

import dashscope
import requests
from dashscope.common.error import AuthenticationError
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log
from videotrans.configure.config import params, logger, settings
from videotrans.configure.excepts import NO_RETRY_EXCEPT, StopTask
from videotrans.tts._base import BaseTTS
from videotrans.util import tools
from videotrans import translator

# 强制单线程 防止远端限制出错
@dataclass
class QWENTTS(BaseTTS):
    target_language: str = None
    
    def __post_init__(self):
        super().__post_init__()
        self.role_dict=tools.get_qwen3tts_rolelist()
        self.api_key=params.get('qwentts_key', '')
        spaceid=params.get('qwentts_spaceid', '')
        if spaceid:
            dashscope.base_http_api_url = f'https://{spaceid}.cn-beijing.maas.aliyuncs.com/api/v1'
        _langnames = translator.LANG_CODE.get(self.language, [])
        self.target_language = _langnames[9].capitalize() if _langnames and len(_langnames) >= 10 else 'Auto'
        self.model=params.get('qwentts_model', 'qwen3-tts-flash')
        if self.model.startswith('qwen-tts'):
            self.model='qwen3-tts-flash'

    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO), after=after_log(logger, logging.INFO))
    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        role = self.role_dict.get(data_item['role'],'Cherry')
        try:
            logger.debug(f"[Qwen-TTS(bailian)]{self.model=},{self.api_key=},{role=},{data_item['text']=},{self.target_language=}")
            response = dashscope.MultiModalConversation.call(
                model=self.model,
                # 新加坡和北京地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
                # 若没有配置环境变量，请用阿里云百炼API Key将下行替换为：api_key = "sk-xxx"
                api_key=self.api_key,
                text=data_item['text'],
                voice=role,
                language_type=self.target_language, 
                stream=False
            )

            if response is None:
                return "API call returned None response"

            if "Access denied" in response.message:
                return response.message

            if not hasattr(response, 'output') or response.output is None or not hasattr(response.output, 'audio'):
                return  f"{response.message if hasattr(response, 'message') else str(response)}"

            resurl = requests.get(response.output.audio["url"])
            resurl.raise_for_status()  # 检查请求是否成功
            with open(data_item['filename'] + '.wav', 'wb') as f:
                f.write(resurl.content)
            self.convert_to_wav(data_item['filename'] + ".wav", data_item['filename'])
        except AuthenticationError as e:
            raise StopTask(str(e))
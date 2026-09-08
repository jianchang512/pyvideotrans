import logging
import re,httpx
from dataclasses import dataclass, field
from typing import List, Union
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log
from videotrans.configure.excepts import NO_RETRY_EXCEPT, TranslateSrtError, StopTask
from videotrans.configure.config import tr,settings,params,logger
from videotrans.translator._base import BaseTrans
from google import genai
from google.genai import types,errors


@dataclass
class Gemini(BaseTrans):
    ainame:str="gemini"
    prompt: str = field(init=False)
    api_keys: List[str] = field(init=False, repr=False)  # Use repr=False for sensitive data

    def __post_init__(self):
        super().__post_init__()
        self.model_name = params.get("gemini_model",'gemini-flash-latest')
        self.prompt=self._set_context()
        self.api_keys = params.get('gemini_key', '').strip().split(',')
        logger.debug(f'{self.ainame=},{self.source_code=},{self.target_code=},{self.target_language_name=},{self.aisendsrt=}')


    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO),after=after_log(logger, logging.INFO))
    def _item_task(self, data: Union[List[str], str]) -> str:
        if self._exit(): return
        text = "\n".join([i.strip() for i in data]) if isinstance(data, list) else data
        client=None
        try:
            model = params.get("gemini_model","gemini-flash-latest")
            generation_config={}
            if model.startswith('gemini-3') or model.startswith('gemini-4') or model.startswith('gemini-flash'):
                generation_config["thinking_level"]="high"
            
            api_key = self.api_keys.pop(0)
            self.api_keys.append(api_key)
            client = genai.Client(
                api_key=api_key,
                http_options = types.HttpOptions(
                    client_args={'proxy': self.proxy_str},
                    async_client_args={'proxy': self.proxy_str},
                ) if self.proxy_str else None
            )
            
            message=self.prompt.replace('{batch_input}', f'{text}')
            logger.debug(f'{message=}')
            result = client.interactions.create(
                model=model,
                input=message,
                system_instruction="You are a top-tier Subtitle Translation Engine.",
                generation_config=generation_config
            )
            if not result:
                logger.warning(f'[gemini]请求失败')
                raise TranslateSrtError(f"[Gemini]result is empty")

            match = re.search(r'<TRANSLATE_TEXT>(.*?)(?:</TRANSLATE_TEXT>|$)',
                              re.sub(r'<think>(.*?)</think>', '', result.output_text, flags=re.I | re.S), re.S | re.I)
            if match:
                return match.group(1)
            raise TranslateSrtError(f"Gemini result is emtpy")
        except httpx.ConnectTimeout as e:
            raise StopTask(f' {tr("Unable to connect to remote API","Gemini AI")}\n{e}') from e
        except errors.APIError as e:
            logger.warning(f'{e=}')
            if e.code in [400,403,404,429,500]:
                raise StopTask(e.message)
            raise TranslateSrtError(e.message)
        finally:
            if client:
                client.close()
import concurrent.futures
import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Union
from gradio_client import Client
from tenacity import wait_fixed, before_log, after_log, stop_after_attempt, retry_if_not_exception_type, retry

from videotrans.configure.config import params, logger, settings,tr
from videotrans.configure.excepts import StopTask, NO_RETRY_EXCEPT
from videotrans.tts._base import BaseTTS
from videotrans.util import tools
import urllib3,httpx


thread_local = threading.local()


@dataclass
class GradioBase(BaseTTS):
    ainame: str = None

    def __post_init__(self):
        super().__post_init__()
        api_url = params.get(f'{self.ainame}_url', '').strip().rstrip('/').lower()
        if len(api_url)<4:
            raise StopTask(f'API URL is error: {api_url}')
        self.api_url = f'http://{api_url}' if not api_url.startswith('http') else api_url
        self.roledict = tools.get_f5tts_role()

    def get_thread_client(self)->Client:
        # 检查当前线程是否已经有存活的 client
        if not hasattr(thread_local, "client") or thread_local.client is None:
            logger.debug(f"正在为线程 {threading.current_thread().name} 初始化 Gradio Client: {self.api_url}")
            thread_local.client = Client(
                    self.api_url,
                    httpx_kwargs={"timeout": 3600}, # 连接超时设置短一点因为只是拉取配置
                    ssl_verify=False
                )
        return thread_local.client


    # 实际发送进行推理
    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO), after=after_log(logger, logging.INFO))
    def _send(self, kwargs,data_item)->Union[str,None]:
        if self._exit() or not data_item.get('text','').strip() or tools.vail_file(data_item['filename']):
            return
        try:
            logger.debug(f'TTS-name={self.ainame}')
            client = self.get_thread_client()
            result = client.predict(**kwargs)
            logger.debug(f'result={result}')
            wav_file = result[0] if isinstance(result, (list, tuple)) and result else result
            if isinstance(wav_file, dict) and "value" in wav_file:
                wav_file = wav_file['value']
            
            if not isinstance(wav_file, str) or not Path(wav_file).is_file():
                return str(result)+f"\n{self.api_name=} {self.api_url=}"
            if self.ainame=='cosyvoice' and str(result).endswith('playlist.m3u8'):
                raise StopTask('请修改 CosyVoice3 的官方 webui.py 文件，搜索代码 streaming=True ，改为 streaming=False  然后保存重启 CosyVoice3\n\nPlease modify the official webui.py file for CosyVoice3, search for the line streaming=True , change it to  streaming=False , then save and restart CosyVoice3.\n详见 https://pyvideotrans.com/cosyvoice')
            self.convert_to_wav(wav_file, data_item['filename'])
        except (TypeError,ValueError,IndexError,AttributeError,urllib3.exceptions.NewConnectionError,httpx.ConnectError) as e:
            _quit_errors=[
                "Unknown protocol",
                "WinError 10061",
                "Could not fetch config for",
                "Could not get Gradio config from",
                "Failed to establish a new connection"
            ]
            err=str(e)
            for _title in  _quit_errors:
                if _title in err :
                    raise StopTask(f"{self.ainame} {tr('This channel needs deployed and started before available')}\n{self.api_url=}\n{err}") from e
            return err
        except concurrent.futures.CancelledError as e:
            logger.exception(f'配音失败:{self.ainame}',exc_info=True)
            # 清理当前线程的客户端缓存，防止下次复用一个已损坏的连接
            if hasattr(thread_local, "client"):
                del thread_local.client
            return str(e)+f"\n{self.api_url=}"
        except Exception as e:
            return +f"{self.api_name} {self.api_url} \n{str(e)}"
        return




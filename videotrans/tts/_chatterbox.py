import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Union
import requests
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log
from videotrans.configure.config import params, logger, settings, app_cfg, ROOT_DIR
from videotrans.configure.excepts import NO_RETRY_EXCEPT, StopTask, DubbingSrtError
from videotrans.tts._base import BaseTTS
from videotrans.util import tools
try:
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS as ChatterboxTTS
except ImportError:
    logger.critical('please run  uv sync --extra chatterbox ')

import soundfile as sf
RETRY_NUMS = 2
RETRY_DELAY = 5


@dataclass
class ChatterBoxTTS(BaseTTS):
    def __post_init__(self):
        super().__post_init__()
        self.roledict=tools.get_chatterbox_role()

    def _download(self):
            if not Path(f'{ROOT_DIR}/models/chatterbox/ve.pt').exists():
                tools.check_and_down_hf("", 'resembleAI/chatterbox', f'{ROOT_DIR}/models/chatterbox', callback=self._process_callback,allow_list=['ve.pt','s3gen.pt','conds.pt','t3_cfg.pt','t3_mtl23ls_v2.safetensors','Cangjie5_TC.json','grapheme_mtl_merged_expanded_v1.json','mtl_tokenizer.json','tokenizer.json'])
            return True

    def _exec(self):
        model = ChatterboxTTS.from_local(f'{ROOT_DIR}/models/chatterbox',device='cpu' if not self.is_cuda else 'cuda')

        ok, err = 0, 0
        _except = None
        cfg_weight=float(params.get("chatterbox_cfg_weight",'0.5'))
        exaggeration=float(params.get("chatterbox_exaggeration",'0.5'))
        lang=self.language.split('-')[0]
        for item in self.queue_tts:
            if app_cfg.exit_soft: return
            ref_wav=None
            try:
                ref_wav,_=self.get_ref_wav(item)
            except Exception:
                logger.debug('无参考音频，使用内置音色')
            try:
                wav_tensor = model.generate(item['text'],exaggeration=exaggeration,cfg_weight=cfg_weight,language_id=lang,audio_prompt_path=ref_wav)
                wav_tensor = wav_tensor.detach().cpu()
                if wav_tensor.ndim == 2:
                    wav_np = wav_tensor.transpose(0, 1).numpy()
                else:
                    wav_np = wav_tensor.numpy()
                 # 写入 WAV 格式到内存
                sf.write(item['filename'] + "-24k.wav", wav_np, model.sr, format='wav')
                if not tools.vail_file(item['filename'] + '-24k.wav'):
                    err += 1
                    continue
                ok += 1
                self.convert_to_wav(item['filename'] + '-24k.wav', item['filename'])
                self.signal(text=f"Dubbing {ok}")
            except Exception as e:
                _except = e
                logger.exception(f'vits dubbing error:{e}', exc_info=True)
                err += 1

        try:
            del model
        except Exception:
            pass
        if ok == 0:
            raise _except if _except else DubbingSrtError('ChatterBox-TTS dubbing error')

        msg = "dubbing ended"
        if err > 0 and ok > 0:
            msg = f'[{err}] errors, {ok} succeed'


        self.signal(text=msg)
        logger.debug(f'ChatterBox 配音结束：{msg}')

    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO), after=after_log(logger, logging.INFO))
    def _run00(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        try:
            ref_wav,_=self.get_ref_wav(data_item)
        except Exception:
            logger.debug('无参考音频，使用内置音色')
        else:
            return self._clone(data_item['text'], ref_wav, data_item['filename'])

        client = OpenAI(api_key='123456', base_url=self.api_url + '/v1')
        response = client.audio.speech.create(
            model="chatterbox-tts",  # 这是一个兼容性参数
            voice=self.language.split('-')[0],  # 这也是一个兼容性参数
            input=data_item['text'],
            speed=float(params.get("chatterbox_cfg_weight",'1.0')),  # 兼容，用于传递 cfg_weight
            instructions=str(params.get("chatterbox_exaggeration",'')),  # 兼容传递 exaggeration
            response_format="mp3"  # 请求mp3格式
        )

        response.stream_to_file(data_item['filename'] + ".mp3")
        self.convert_to_wav(data_item['filename'] + ".mp3", data_item['filename'])


    def _clone(self, text, ref_wav=None, filename=None):
        mime_type = 'audio/wav'
        with open(ref_wav, 'rb') as audio_file:
            # 定义form-data中的文件部分
            # key 'audio_prompt' 必须与 Flask 服务器端 `request.files['audio_prompt']` 匹配
            files_payload = {
                'audio_prompt': (os.path.basename(ref_wav), audio_file, mime_type)
            }
            # 定义form-data中的文本部分
            # key 'input' 必须与 Flask 服务器端 `request.form['input']` 匹配
            form_data = {
                'input': text,
                'response_format': 'mp3',
                'cfg_weight': params.get("chatterbox_cfg_weight",'0.3'),
                'exaggeration': params.get("chatterbox_exaggeration",''),
                'language': self.language.split('-')[0]
            }
            # 发送POST请求，设置合理的超时时间
            response = requests.post(
                self.api_url + '/v2/audio/speech_with_prompt',
                data=form_data,
                files=files_payload,
                timeout=7200  # TTS可能需要一些时间，设置一个较长的超时
            )
            # 检查HTTP响应状态码，如果不是2xx，则会引发HTTPError
            response.raise_for_status()
            # 将返回的二进制音频内容写入文件
            with open(filename + ".mp3", 'wb') as output_file:
                output_file.write(response.content)
            self.convert_to_wav(filename + ".mp3", filename)

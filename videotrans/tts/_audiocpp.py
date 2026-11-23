import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any

import requests

from videotrans.configure import config
from videotrans.configure._i18n import tr
from videotrans.configure._languages_dict import LANGUAGE_FIRERED3
from videotrans.configure._paths import REDUBB_STATUS_FILE, REDUBB_QUEUE_FILE
from videotrans.configure.config import params, logger, app_cfg, ROOT_DIR
from videotrans.configure.excepts import DubbingSrtError
from videotrans.tts._base import BaseTTS
from videotrans.util.help_audiocpp import activate_audiocpp_server
from videotrans.util.help_role import get_f5tts_role
from videotrans.util.help_misc import vail_file
from videotrans.util.help_down import down_file_from_hf, down_audiocpp_bin


@dataclass(repr=False)
class AudiocppTTS(BaseTTS):
    jsondata: Dict[str, Any] = field(default_factory=dict, repr=False)
    gguf_obj: Dict[str, Any] = field(default_factory=dict, repr=False)
    model_path: str = field(default="", repr=False)

    def __post_init__(self):
        super().__post_init__()
        self.roledict = get_f5tts_role()
        self.jsondata = json.loads(Path(f'{ROOT_DIR}/videotrans/voicejson/audiocpp.json').read_text(encoding='utf-8'))
        # 未传入模型时（如单视频配音角色面板中的试听、webui、cli），使用最后保存的模型
        if not self.model_name:
            self.model_name = params.get("audiocpp_model", "omnivoice") or "omnivoice"


    def _download(self):
        self.signal(text=f'Checking audio.cpp cli exists ')
        down_audiocpp_bin(process_callback=self._process_callback)

        self.gguf_obj = self.jsondata.get(self.model_name)

        if not self.gguf_obj or not self.gguf_obj.get('file') or not self.gguf_obj.get('url'):
            raise RuntimeError(f'error:{self.model_name=},{self.gguf_obj=}')

        self.model_path=gguf_file = f"{ROOT_DIR}/models/{self.gguf_obj.get('file')}"

        if Path(gguf_file).exists():
            return True

        model_url = self.gguf_obj.get('url', '')
        down_file_from_hf(
            Path(gguf_file).parent.as_posix(),
            [model_url],
            self._process_callback)
        return True


    # The batch mode has been removed, making management inconvenient. We will uniformly use exec_audiocpp to execute audio.cpp
    def _exec(self):
        ok, err = 0, 0
        _except = None
        lang = self.language.split('-')[0]
        queue_tts = self.queue_tts
        if self.model_name=='fireredtts3':
            lang=LANGUAGE_FIRERED3.get(lang,'Chinese')

        activate_audiocpp_server(self)
        while 1:
            if self.is_redubb and Path(REDUBB_STATUS_FILE).exists():
                return True
            if self.is_redubb:
                try:
                    queue_tts = json.loads(Path(REDUBB_QUEUE_FILE).read_text(encoding='utf-8'))
                except (OSError, json.JSONDecodeError) as e:
                    logger.exception(f'audio.cpp: {e}', exc_info=True)
                    raise

            for i, item in enumerate(queue_tts):
                if app_cfg.exit_soft or (self.is_redubb and Path(REDUBB_STATUS_FILE).exists()):
                    return True
                if vail_file(item['filename']):
                    ok += 1
                    continue
                ref_wav, ref_text = self.get_ref_wav(item)

                try:
                    self.signal(text=f'{tr("Dubbing")} {i}/{self.len}')
                    payload={
                        "model":self.model_name,
                        "input":item['text'],
                        "voice_ref": { "type": "path", "path":ref_wav },
                    }
                    if self.gguf_obj.get("is_reference_text") and ref_text:
                        payload['reference_text']=ref_text
                    if self.gguf_obj.get("is_language"):
                        payload['language']=lang
                    self._api(payload,filename=item['filename'])

                    if not vail_file(item['filename'] + '-24k.wav'):
                        err += 1
                        continue
                    ok += 1
                    self.convert_to_wav(item['filename'] + '-24k.wav', item['filename'])
                except Exception as e:
                    _except = e
                    logger.exception(e, exc_info=True)
                    err += 1
            if self.is_redubb:
                time.sleep(0.5)
                continue
            break

        if ok == 0:
            raise _except if _except else DubbingSrtError('audio.cpp dubbing error')

        msg = f"{tr('Dubbing')} ended"
        if err > 0 and ok > 0:
            msg = f'[{err}] errors, {ok} succeed'

        self.signal(text=msg)
        logger.debug(f'audio.cpp 配音结束：{msg}')


    def _api(self,payload,filename):
        response = requests.post(f'{config.AUDIO_SERVER_CFG.api_endpoint}/v1/audio/speech', headers={
            "content-type": "application/json",
        }, json=payload)
        if response.status_code!=200:
            try:
                msg=response.json().get("error",{}).get("message",response.text)
                raise RuntimeError(f'{msg}\n' + (tr('Insufficient permissions') if "Access is denied" in msg else ""))
            except json.JSONDecodeError:
                raise RuntimeError(response.text)

        with open(f'{filename}-24k.wav', 'wb') as f:
            f.write(response.content)
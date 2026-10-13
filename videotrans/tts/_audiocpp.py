import json,subprocess,os
import time,platform
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any
from videotrans.configure._i18n import tr
from videotrans.configure._paths import REDUBB_STATUS_FILE, REDUBB_QUEUE_FILE
from videotrans.configure.config import params, logger, app_cfg, ROOT_DIR
from videotrans.configure.excepts import DubbingSrtError
from videotrans.configure.constants import AUDIO_CPP_MAC_MS,AUDIO_CPP_WIN_MS,AUDIO_CPP_WIN_HF,AUDIO_CPP_MAC_HF
from videotrans.tts._base import BaseTTS
from videotrans.util.help_role import get_f5tts_role
from videotrans.util.help_misc import vail_file, is_connect_hf
from videotrans.util.help_down import down_zip,down_file_from_hf


@dataclass(repr=False)
class AudiocppTTS(BaseTTS):
    jsondata:Dict[str, Any] = field(default_factory=dict, repr=False)
    gguf_obj:Dict[str, Any] = field(default_factory=dict, repr=False)
    def __post_init__(self):
        super().__post_init__()
        self.roledict = get_f5tts_role()
        self.jsondata=json.loads(Path(f'{ROOT_DIR}/videotrans/voicejson/audiocpp.json').read_text(encoding='utf-8'))

    def _download(self):
        _os=platform.system()
        cli_name="audiocpp_cli.exe" if _os=='Windows' else 'audiocpp_cli'
        p=Path(f'{ROOT_DIR}/audio_cpp/{cli_name}')
        if _os=='Linux' and not p.exists():
            raise RuntimeError(tr("The audio.cpp binary file does not exist",f'{ROOT_DIR}/audio_cpp','audiocpp_cli','https://github.com/0xShug0/audio.cpp/releases'))
        
        urls={
            "Darwin":{"ms":AUDIO_CPP_MAC_MS,"hf":AUDIO_CPP_MAC_HF},
            "Windows":{"ms":AUDIO_CPP_WIN_MS,"hf":AUDIO_CPP_WIN_HF}
        }
        is_con=is_connect_hf()
        if not p.exists():
            self.signal(text=f'Download audio.cpp ')
            down_zip(f'{ROOT_DIR}/audio_cpp', urls[_os]['hf']  if is_con else urls[_os]['ms'], callback=self._process_callback)
        
        
        self.gguf_obj=self.jsondata.get(params.get("audiocpp_model"))

        if not self.gguf_obj or not self.gguf_obj.get('file') or not self.gguf_obj.get('url'):
            raise RuntimeError(f'error:{params.get("audiocpp_model")=},{self.gguf_obj=}')
        
        gguf_file=f"{ROOT_DIR}/audio_cpp/models/{self.gguf_obj.get('file')}"
        
        if Path(gguf_file).exists(): return True
        model_url=self.gguf_obj.get('url')
        if not is_con:
            model_url=model_url.replace('huggingface.co','hf-mirror.com')
        down_file_from_hf(
                Path(gguf_file).parent.as_posix(),
                [model_url],
                self._process_callback)
        return True

    def _exec(self):
        ok, err = 0, 0
        _except = None
        lang = self.language.split('-')[0]
        queue_tts=self.queue_tts
        _path=f'{ROOT_DIR}/audio_cpp{os.pathsep}'
        if _path not in os.environ.get("PATH", ""):
            os.environ['PATH'] = _path + os.environ.get("PATH", "")
        
        txt_file = ROOT_DIR + '/pyvideotrans_audiocpp.txt'
        extra_cmd=[]
        if Path(txt_file).exists():
            extra_cmd=Path(txt_file).read_text(encoding='utf-8').strip().split(' ')
        # 循环，用于轮询重新配音数据，非重新配音时，第一轮直接返回
        while 1:
            if self.is_redubb and Path(REDUBB_STATUS_FILE).exists():
                return True
            if self.is_redubb:
                try:
                    queue_tts=json.loads(Path(REDUBB_QUEUE_FILE).read_text(encoding='utf-8'))
                except (OSError,json.JSONDecodeError) as e:
                    logger.exception(f'supertonic-3: {e}',exc_info=True)
                    raise

            for i,item in enumerate(queue_tts):
                if app_cfg.exit_soft or (self.is_redubb and Path(REDUBB_STATUS_FILE).exists()):
                    return True
                if vail_file(item['filename']):
                    continue
                ref_wav, ref_text = self.get_ref_wav(item)

                try:
                    self.signal(text=f'{tr("Dubbing")} {i}/{self.len}')
                    cmd=[
                         f"{ROOT_DIR}/audio_cpp/audiocpp_cli",
                         "--task",
                         self.gguf_obj.get('type','tts'),
                         "--family",
                         params.get("audiocpp_model"),
                         "--model",
                         f"models/{self.gguf_obj['file']}",
                         "--backend",
                         "best",
                         "--text",
                         f"{item['text']}",
                         "--voice-ref",
                         ref_wav
                    ]
                    if self.gguf_obj.get("is_reference_text") and ref_text:
                        cmd.append("--reference-text")
                        cmd.append(ref_text)
                    if self.gguf_obj.get("is_language"):
                        cmd.append("--language")
                        cmd.append(lang)
                    if self.gguf_obj.get("is_seed"):
                        cmd.append("--request-option")
                        cmd.append("seed=24")
                    
                    
                    cmd+=extra_cmd+ ["--out", item['filename'] + '-24k.wav' ]
                    logger.debug(f'audio.cpp {cmd=}')
                    output = subprocess.check_output( cmd ,
                        stderr=subprocess.STDOUT,
                        cwd=f"{ROOT_DIR}/audio_cpp",
                        encoding="utf-8",
                        errors='replace',
                        text=True,
                        creationflags=subprocess.CREATE_NO_WINDOW if platform.system()=='Windows' else 0,
                    )
                    logger.debug(f'{output=}')
                    if not vail_file(item['filename'] + '-24k.wav'):
                        err += 1
                        continue
                    ok += 1
                    self.convert_to_wav(item['filename'] + '-24k.wav', item['filename'])
                except subprocess.CalledProcessError as e:
                    if e.stdout and ("Access is denied" in e.stdout or "could not open" in e.stdout):
                        raise RuntimeError(tr('Insufficient permissions'))
                    if e.stdout and "mem_buffer" in e.stdout:
                        raise RuntimeError(tr('OOMerror'))
                        
                    _except=RuntimeError(f'{e.stdout or e} {e.stderr or ""}')
                    logger.exception(e,exc_info=True)
                except Exception as e:
                    _except = e
                    logger.exception(e,exc_info=True)
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

import json, subprocess, os, sys, tempfile
import time, platform
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from videotrans.configure._i18n import tr
from videotrans.configure._paths import REDUBB_STATUS_FILE, REDUBB_QUEUE_FILE, IPC_STATUS_FILE
from videotrans.configure.config import params, logger, app_cfg, ROOT_DIR
from videotrans.configure.excepts import DubbingSrtError
from videotrans.configure.constants import AUDIO_CPP_MAC_MS, AUDIO_CPP_WIN_MS, AUDIO_CPP_WIN_HF, AUDIO_CPP_MAC_HF
from videotrans.tts._base import BaseTTS
from videotrans.util.help_role import get_f5tts_role
from videotrans.util.help_misc import vail_file, is_connect_hf, exec_audiocpp
from videotrans.util.help_down import down_zip, down_file_from_hf, down_audiocpp_bin
from videotrans.util.gpus import get_audiocpp_backend_args


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
        print(f'[audio.cpp] 使用模型 {self.model_name=}')

    def _download(self):
        self.signal(text=f'Checking audio.cpp cli exists ')
        down_audiocpp_bin(process_callback=self._process_callback)

        self.gguf_obj = self.jsondata.get(self.model_name)

        if not self.gguf_obj or not self.gguf_obj.get('file') or not self.gguf_obj.get('url'):
            raise RuntimeError(f'error:{self.model_name=},{self.gguf_obj=}')

        gguf_file = f"{ROOT_DIR}/audio_cpp/models/{self.gguf_obj.get('file')}"
        self.model_path = f"models/{self.gguf_obj['file']}"

        if Path(gguf_file).exists():
            return True

        # Reuse already-downloaded OmniVoice safetensors directory if present
        if self.model_name == "omnivoice":
            safetensors_dir = Path(f"{ROOT_DIR}/models/models--k2-fsa--OmniVoice")
            if (safetensors_dir / "model.safetensors").exists():
                self.model_path = safetensors_dir.as_posix()
                return True

        model_url = self.gguf_obj.get('url', '').replace('https://huggingface.co', '')
        down_file_from_hf(
            Path(gguf_file).parent.as_posix(),
            [model_url],
            self._process_callback)
        return True

    def _resolve_ref(self, item: Dict[str, Any], lang: str) -> Tuple[Optional[str], Optional[str]]:
        ref_wav, ref_text = self.get_ref_wav(item)
        if ref_wav and Path(ref_wav).exists():
            return str(Path(ref_wav).resolve()), ref_text
        if self.gguf_obj.get("type") == "clon":
            default_wav = "zh_female_cn.wav" if lang in ("zh", "yue") else "en_female_1.wav"
            fallback_path = Path(f"{ROOT_DIR}/f5-tts/{default_wav}")
            if fallback_path.exists():
                fallback_text = self.roledict.get(default_wav, "")
                return str(fallback_path.resolve()), fallback_text
        return None, None

    def _run_batch_sequence(self, pending_items: list, lang: str, extra_cmd: list) -> Tuple[int, int, Optional[Exception]]:
        """Run all pending TTS requests in a single audio.cpp session so the model loads into VRAM only once."""
        requests_list = []
        id_to_item = {}
        for idx, item in enumerate(pending_items):
            req_id = f"seg_{idx}"
            id_to_item[req_id] = (idx, item)
            ref_wav, ref_text = self._resolve_ref(item, lang)
            req: Dict[str, Any] = {
                "id": req_id,
                "text": str(item["text"]),
            }
            if ref_wav:
                req["voice_ref"] = ref_wav
            if self.gguf_obj.get("is_reference_text") and ref_text:
                req["reference_text"] = ref_text
            if self.gguf_obj.get("is_language"):
                req["language"] = lang
            options: Dict[str, Any] = {}
            if self.gguf_obj.get("is_seed"):
                options["seed"] = "24"
            if self.model_name == "ming3_tts":
                if ref_text:
                    options["reference_text"] = ref_text
                options["language"] = lang
            if options:
                req["options"] = options
            requests_list.append(req)

        with tempfile.TemporaryDirectory(prefix="audiocpp_batch_") as tmp_dir:
            seq_file = Path(tmp_dir) / "requests.json"
            out_dir = Path(tmp_dir) / "outputs"
            out_dir.mkdir(parents=True, exist_ok=True)
            seq_file.write_text(json.dumps({"requests": requests_list}, ensure_ascii=False, indent=2), encoding="utf-8")

            cmd = [
                f"{ROOT_DIR}/audio_cpp/audiocpp_cli",
                "--task",
                self.gguf_obj.get("type", "tts"),
                "--family",
                self.model_name,
                "--model",
                self.model_path or f"models/{self.gguf_obj['file']}",
                *get_audiocpp_backend_args(),
                "--request-sequence",
                str(seq_file),
                "--out-dir",
                str(out_dir),
            ]
            if extra_cmd:
                cmd.extend([c for c in extra_cmd if c])

            logger.debug(f"audio.cpp batch start ({len(requests_list)} items): {cmd=}")
            self.signal(text=f'{tr("Dubbing")} 0/{self.len}')
            proc = subprocess.Popen(
                cmd,
                encoding="utf-8",
                errors="ignore",
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                cwd=f"{ROOT_DIR}/audio_cpp",
            )
            current_req_id = ""
            ok, err = 0, 0
            logs = []
            assert proc.stdout is not None
            for line in proc.stdout:
                if app_cfg.exit_soft or Path(IPC_STATUS_FILE).exists():
                    proc.kill()
                    proc.wait()
                    return ok, err, None
                s = line.strip()
                if s:
                    logs.append(s)
                if s.startswith("request_id="):
                    current_req_id = s[len("request_id="):]
                    if current_req_id in id_to_item:
                        idx, _ = id_to_item[current_req_id]
                        self.signal(text=f'{tr("Dubbing")} {idx + 1}/{self.len}')
                elif s.startswith("audio_out=") and current_req_id in id_to_item:
                    wav_path = s[len("audio_out="):]
                    _, item = id_to_item[current_req_id]
                    if vail_file(wav_path):
                        self.convert_to_wav(wav_path, item["filename"])
                        if vail_file(item["filename"]):
                            ok += 1
            proc.wait()

            # Check any remaining output files in out_dir
            for req_id, (_, item) in id_to_item.items():
                if not vail_file(item["filename"]):
                    cand = out_dir / f"{req_id}.wav"
                    if vail_file(cand.as_posix()):
                        self.convert_to_wav(cand.as_posix(), item["filename"])
                    if vail_file(item["filename"]):
                        ok += 1
                    else:
                        err += 1

            if proc.returncode != 0 and ok == 0:
                tail = "\n".join(logs[-20:])
                return ok, err, RuntimeError(f"audio.cpp batch failed ({proc.returncode}): {tail}")
            return ok, err, None

    def _exec(self):
        ok, err = 0, 0
        _except = None
        lang = self.language.split('-')[0]
        queue_tts = self.queue_tts
        _path = f'{ROOT_DIR}/audio_cpp{os.pathsep}'
        if _path not in os.environ.get("PATH", ""):
            os.environ['PATH'] = _path + os.environ.get("PATH", "")

        txt_file = ROOT_DIR + '/pyvideotrans_audiocpp.txt'
        extra_cmd = []
        if Path(txt_file).exists():
            extra_cmd = [c for c in Path(txt_file).read_text(encoding='utf-8').strip().split(' ') if c]
        # 循环，用于轮询重新配音数据，非重新配音时，第一轮直接返回
        while 1:
            if self.is_redubb and Path(REDUBB_STATUS_FILE).exists():
                return True
            if self.is_redubb:
                try:
                    queue_tts = json.loads(Path(REDUBB_QUEUE_FILE).read_text(encoding='utf-8'))
                except (OSError, json.JSONDecodeError) as e:
                    logger.exception(f'supertonic-3: {e}', exc_info=True)
                    raise

            from videotrans.util.help_misc import exec_audiocpp as _real_exec_audiocpp
            pending_items = [it for it in queue_tts if not vail_file(it['filename']) and it.get('text', '').strip()]
            if not self.is_redubb and len(pending_items) > 1 and exec_audiocpp is _real_exec_audiocpp:
                b_ok, b_err, b_exc = self._run_batch_sequence(pending_items, lang, extra_cmd)
                ok += b_ok
                err += b_err
                if b_exc:
                    _except = b_exc
                if ok > 0 and err == 0:
                    break
                # Any items that didn't succeed in batch fall through to individual retry below
                err = 0

            for i, item in enumerate(queue_tts):
                if app_cfg.exit_soft or (self.is_redubb and Path(REDUBB_STATUS_FILE).exists()):
                    return True
                if vail_file(item['filename']):
                    ok += 1
                    continue
                ref_wav, ref_text = self._resolve_ref(item, lang)

                try:
                    self.signal(text=f'{tr("Dubbing")} {i}/{self.len}')
                    cmd = [
                        f"{ROOT_DIR}/audio_cpp/audiocpp_cli",
                        "--task",
                        self.gguf_obj.get('type', 'tts'),
                        "--family",
                        self.model_name,
                        "--model",
                        self.model_path or f"models/{self.gguf_obj['file']}",
                        "--backend",
                        "best",
                        "--text",
                        f"{item['text']}",
                    ]
                    if ref_wav:
                        cmd.extend(["--voice-ref", ref_wav])
                    if self.gguf_obj.get("is_reference_text") and ref_text:
                        cmd.append("--reference-text")
                        cmd.append(ref_text)
                    if self.gguf_obj.get("is_language"):
                        cmd.append("--language")
                        cmd.append(lang)
                    if self.gguf_obj.get("is_seed"):
                        cmd.append("--request-option")
                        cmd.append("seed=24")
                    if self.model_name=='ming3_tts':
                        if ref_text:
                            cmd.extend(["--request-option", f'reference_text="{ref_text}"'])
                        cmd.extend(["--request-option", f'language={lang}'])

                    cmd.extend(extra_cmd + ["--out", os.path.normpath(item['filename'] + '-24k.wav')])

                    exec_audiocpp(cmd)
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


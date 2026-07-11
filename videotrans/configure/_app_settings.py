# -*- coding: utf-8 -*-
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

from videotrans.configure._paths import ROOT_DIR
from videotrans.configure._logging import _write_with_retry
from videotrans.configure.contants import (
    DEFAULT_GEMINI_MODEL, ChatTTS_VOICE, Qwentts_Models,
    Whisper_Models, Zijiehuoshan_Model, Zhipuai_Model, Localllm_Model, Azure_Model,
    Chatgpt_Model, Openairecognapi_Model, Qpenaitts_Model, Qwenmt_Model, Ai302_Models,
    Whisper_cpp_models, Deepseek_Model, Openrouter_Model, Guiji_Model, MINIMAX_MODELS,
    XIAOMI_MODELS
)


@dataclass
class AppSettings:
    """
    AppSettings: 对应 cfg.json，包含 parse_init 功能
    """
    homedir: str = ROOT_DIR + "/output"
    lang: str = ""
    initial_prompt_zh_cn: str = ""
    initial_prompt_zh_tw: str = ""
    hf_token: str = ""
    proxy: str = ''

    _json_path: str = f"{ROOT_DIR}/videotrans/cfg.json"
    WHISPER_MODEL_LIST: List = field(default_factory=list, repr=False)
    ChatTTS_voicelist: List = field(default_factory=list, repr=False)
    Whisper_CPP_MODEL_LIST: List = field(default_factory=list, repr=False)
    Whisper_NET_MODEL_LIST: List = field(default_factory=list, repr=False)

    def __post_init__(self):
        self.parse_init()

    def save(self, data: Dict = None):
        if data:
            return self.parse_init(data)
        self._save_to_disk()

    def parse_init(self, update_data: Dict = None) -> Dict:
        default = self._get_defaults()

        if update_data:
            self._apply_dict(update_data)
            self._save_to_disk()
            self.WHISPER_MODEL_LIST = re.split(r'[,，]', update_data.get('model_list', ''))
            return self.to_dict()

        if not Path(self._json_path).exists():
            self._apply_dict(default)
            self._save_to_disk()
            self.WHISPER_MODEL_LIST = re.split(r'[,，]', default.get('model_list', ''))
            return default

        try:
            temp_json = json.loads(Path(self._json_path).read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            self._apply_dict(default)
            return default

        merged_settings = {}
        hyphen_map = {"initial_prompt_zh-cn": "initial_prompt_zh_cn", "initial_prompt_zh-tw": "initial_prompt_zh_tw"}

        for key, val in temp_json.items():
            py_key = hyphen_map.get(key, key)

            if key not in default and py_key not in default:
                continue
            value = str(val).strip()
            if re.match(r'^\d+$', value):
                merged_settings[py_key] = int(value)
            elif re.match(r'^\d*\.\d+$', value):
                merged_settings[py_key] = float(value)
            elif value.lower() == 'true':
                merged_settings[py_key] = True
            elif value.lower() == 'false':
                merged_settings[py_key] = False
            elif value:
                merged_settings[py_key] = value

        _extend_models = ['localllm_model', 'zhipuai_model', 'deepseek_model', 'openrouter_model',
                          'guiji_model', 'zijiehuoshan_model', 'model_list', 'qwentts_models',
                          'gemini_model', 'chattts_voice']

        for m in _extend_models:
            def_val = str(default.get(m, ''))
            curr_val = str(merged_settings.get(m, def_val))

            _de = def_val.split(',')
            _cache = curr_val.split(',')
            _new = [str(it) for it in _cache if it and it not in _de]
            if _new:
                _de.extend(_new)
            merged_settings[m] = ",".join(_de)

        default.update(merged_settings)

        self.WHISPER_MODEL_LIST = re.split(r'[,，]', default.get('model_list', ''))
        self.ChatTTS_voicelist = re.split(r'[,，]', str(default.get('chattts_voice', '')))
        self.Whisper_CPP_MODEL_LIST = str(default.get('Whisper_cpp_models', 'ggml-tiny')).strip().split(',')
        self.Whisper_NET_MODEL_LIST = str(default.get('Whisper_net_models', 'ggml-tiny.bin')).strip().split(',')

        self._apply_dict(default)

        self._save_to_disk()
        self._handle_hf_token()

        return self.to_dict()

    def _get_defaults(self) -> Dict:
        return {
            "homedir": ROOT_DIR + "/output",
            "lang": "",
            "Faster_Whisper_XXL": "",
            "Whisper_cpp": "",
            "Whisper_cpp_models": Whisper_cpp_models,
            "Whisper_net_models": Whisper_cpp_models,
            "crf": 23,
            "fps_mode": "vfr",
            "hotwords": "",
            "edgetts_max_concurrent_tasks": 10,
            "edgetts_retry_nums": 3,
            "del_end_punc": True,
            "force_lib": False,
            "hw_decode": False,
            "preset": "slow",
            "ffmpeg_cmd": "",
            "aisendsrt": True,
            "dont_notify": False,
            "video_codec": 264,
            "out_video_ext": ".mp4",
            "noise_separate_nums": 4,
            "aitrans_temperature": 0.1,
            "aitrans_context": False,
            "batch_nums": 0,
            "ai302_models": Ai302_Models,
            'qwenmt_model': Qwenmt_Model,
            "openaitts_model": Qpenaitts_Model,
            "openairecognapi_model": Openairecognapi_Model,
            "chatgpt_model": Chatgpt_Model,
            "azure_model": Azure_Model,
            "localllm_model": Localllm_Model,
            "zhipuai_model": Zhipuai_Model,
            "deepseek_model": Deepseek_Model,
            "xiaomi_model": XIAOMI_MODELS,
            "openrouter_model": Openrouter_Model,
            "guiji_model": Guiji_Model,
            "zijiehuoshan_model": Zijiehuoshan_Model,
            "model_list": Whisper_Models,
            "max_audio_speed_rate": 100,
            "max_video_pts_rate": 10,
            "threshold": 0.5,
            "min_speech_duration_ms": 2000,
            "max_speech_duration_s": 5,
            "min_speech_duration_ms2": 1000,
            "max_speech_duration_s2": 2,
            "min_silence_duration_ms": 140,
            "no_speech_threshold": 0.6,
            "whisper_prepare": False,
            "merge_short_sub": False,
            "vad_type": "silero",
            "trans_thread": 10,
            "aitrans_thread": 50,
            "translation_wait": 0,
            "dubbing_wait": 1,
            "dubbing_thread": 1,
            "asr_wait": 0,
            "normal_text": False,
            "remove_dubb_silence": True,
            "save_segment_audio": False,
            "countdown_sec": 30,
            "backaudio_volume": 0.8,
            "loop_backaudio": 1,
            "cuda_com_type": "default",
            "initial_prompt_zh-cn": "",
            "initial_prompt_zh-tw": "",
            "initial_prompt_en": "",
            "initial_prompt_fr": "",
            "initial_prompt_de": "",
            "initial_prompt_ja": "",
            "initial_prompt_ko": "",
            "initial_prompt_ru": "",
            "initial_prompt_es": "",
            "initial_prompt_th": "",
            "initial_prompt_it": "",
            "initial_prompt_pt": "",
            "initial_prompt_vi": "",
            "initial_prompt_ar": "",
            "initial_prompt_tr": "",
            "initial_prompt_hi": "",
            "initial_prompt_hu": "",
            "initial_prompt_uk": "",
            "initial_prompt_id": "",
            "initial_prompt_ms": "",
            "initial_prompt_km": "",
            "initial_prompt_kk": "",
            "initial_prompt_nb": "",
            "initial_prompt_el": "",
            "initial_prompt_cs": "",
            "initial_prompt_pl": "",
            "initial_prompt_nl": "",
            "initial_prompt_bn": "",
            "initial_prompt_he": "",
            "initial_prompt_sv": "",
            "initial_prompt_fa": "",
            "initial_prompt_ur": "",
            "initial_prompt_yue": "",
            "initial_prompt_ro": "",
            "initial_prompt_fil": "",
            "beam_size": 5,
            "best_of": 5,
            "minimax_model": MINIMAX_MODELS,
            "uvr_models": "spleeter",
            "condition_on_previous_text": False,
            "temperature": "",
            "repetition_penalty": 1.0,
            "compression_ratio_threshold": 2.4,
            "qwentts_role": '',
            "qwentts_models": Qwentts_Models,
            "show_more_settings": False,
            "speaker_type": "built",
            "hf_token": "",
            "cjk_len": 15,
            "other_len": 40,
            "gemini_model": DEFAULT_GEMINI_MODEL,
            "llm_chunk_size": 50,
            "llm_ai_type": "deepseek",
            "gemini_recogn_chunk": 50,
            "zh_hant_s": True,
            "process_max": 0,
            "process_max_gpu": 1,
            "multi_gpus": False,
            "retry_nums": 1,
            "chattts_voice": ChatTTS_VOICE,
            "proxy": ""
        }

    def _apply_dict(self, data: Dict):
        for k, v in data.items():
            attr_name = k
            if k == "initial_prompt_zh-cn":
                attr_name = "initial_prompt_zh_cn"
            if k == "initial_prompt_zh-tw":
                attr_name = "initial_prompt_zh_tw"
            setattr(self, attr_name, v)

    def to_dict(self) -> Dict:
        data = {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
        if "initial_prompt_zh_cn" in data:
            data["initial_prompt_zh-cn"] = data.pop("initial_prompt_zh_cn")
        if "initial_prompt_zh_tw" in data:
            data["initial_prompt_zh-tw"] = data.pop("initial_prompt_zh_tw")
        return data

    def _save_to_disk(self):
        try:
            _write_with_retry(self._json_path, json.dumps(self.to_dict(), ensure_ascii=False))
        except Exception as e:
            logging.getLogger('VideoTrans').exception(f'保存settings到本地失败：{e}', exc_info=True)

    def _handle_hf_token(self):
        p = Path(ROOT_DIR + "/models/hf_token.txt")
        if p.is_file():
            tk = p.read_text().strip()
            if tk:
                self.hf_token = tk
        if not p.is_file() and self.hf_token:
            p.write_text(self.hf_token)

    def __getitem__(self, key):
        attr = key
        if key == "initial_prompt_zh-cn":
            attr = "initial_prompt_zh_cn"
        if key == "initial_prompt_zh-tw":
            attr = "initial_prompt_zh_tw"
        return getattr(self, attr)

    def __setitem__(self, key, value):
        attr = key
        if key == "initial_prompt_zh-cn":
            attr = "initial_prompt_zh_cn"
        if key == "initial_prompt_zh-tw":
            attr = "initial_prompt_zh_tw"
        setattr(self, attr, value)

    def get(self, key, default=None):
        float_type = [
            "aitrans_temperature",
            "threshold",
            "no_speech_threshold",
            "backaudio_volume",
            "repetition_penalty",
            "compression_ratio_threshold",
        ]
        int_type = [
            "crf",
            "edgetts_max_concurrent_tasks",
            "edgetts_retry_nums",
            "video_codec",
            "noise_separate_nums",
            "batch_nums",
            "max_audio_speed_rate",
            "max_video_pts_rate",
            "min_speech_duration_ms",
            "max_speech_duration_s",
            "min_silence_duration_ms",
            "trans_thread",
            "aitrans_thread",
            "translation_wait",
            "dubbing_wait",
            "dubbing_thread",
            "countdown_sec",
            "loop_backaudio",
            "beam_size",
            "best_of",
            "cjk_len",
            "other_len",
            "llm_chunk_size",
            "gemini_recogn_chunk",
            "process_max",
            "process_max_gpu",
            "retry_nums",
        ]
        try:
            if key in int_type:
                try:
                    return int(self[key])
                except (ValueError, TypeError, IndexError):
                    default = self._get_defaults()
                    return int(default[key])
            elif key in float_type:
                try:
                    return float(self[key])
                except (ValueError, TypeError, IndexError):
                    default = self._get_defaults()
                    return float(default[key])

            vl = self[key]

            if vl is False or key.lower() == 'false':
                return False
            if vl is True or key.lower() == 'true':
                return True
            return str(self[key])
        except (AttributeError, ValueError, IndexError, TypeError):
            return default

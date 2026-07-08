# -*- coding: utf-8 -*-
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from videotrans.configure._paths import ROOT_DIR
from videotrans.configure._logging import _write_with_retry
from videotrans.configure.contants import (
    DEFAULT_GEMINI_MODEL, OPENAITTS_ROLES, GEMINI_TTS_MODELS,
    XIAOMI_MODELS, XIAOMI_TTS_MODELS, ELEVENLABS_TTS_MODELS,
    MINIMAX_TTS_MODELS, MINIMAX_MODELS
)

# Module-level reference to settings singleton, set by config.py
_settings_ref = None


def set_settings_ref(settings):
    global _settings_ref
    _settings_ref = settings


@dataclass
class AppParams:
    """
    AppParams: 对应 params.json，包含 getset_params 功能
    """
    _json_path: str = f"{ROOT_DIR}/videotrans/params.json"

    def __post_init__(self):
        self.getset_params()

    def save(self, data: Dict = None):
        if data:
            return self.getset_params(data)
        self._save_to_disk()

    def getset_params(self, update_data: Dict = None) -> Dict:
        if update_data:
            self._apply_dict(update_data)
            self._save_to_disk()
            return self.to_dict()

        default = self._get_defaults()
        if Path(self._json_path).exists():
            try:
                loaded = json.loads(Path(self._json_path).read_text(encoding='utf-8'))
                # 单独更新 f5tts_role
                loaded['f5tts_role']=("\n".join(set( (loaded['f5tts_role'].strip()+"\n"+default['f5tts_role']).split("\n") ) )).strip()
                default.update(loaded)
            except (OSError, json.JSONDecodeError):
                pass
        else:
            self._apply_dict(default)
            self._save_to_disk()

        self._apply_dict(default)
        return self.to_dict()

    def _get_defaults(self):
        _settings = _settings_ref
        return {
            "last_opendir": os.path.expanduser("~"),
            "output_dir": "",
            "is_cuda": False,
            "line_roles": {},
            "rephrase": 0,
            "is_separate": False,
            "clear_cache": True,
            "embed_bgm": True,
            "remove_noise": False,
            "enable_diariz": False,
            "nums_diariz": 0,
            "target_dir": "",
            "source_language": "en",
            "target_language": "zh-cn",
            "translate_type": 0,
            "subtitle_type": 1,
            "tts_type": 0,
            "model_name": "large-v3-turbo",
            "recogn_type": 0,
            "fix_punc": 0,
            "stt_fix_punc": 0,
            "voice_autorate": True,
            "video_autorate": False,
            "align_sub_audio": True,
            "voice_role": "No",
            "voice_rate": "0",
            "deepl_authkey": "",
            "deepl_api": "",
            "deepl_gid": "",
            "deeplx_address": "http://127.0.0.1:1188",
            "deeplx_key": "",
            "libre_address": "",
            "libre_key": "",
            "tencent_SecretId": "",
            "tencent_SecretKey": "",
            "tencent_termlist": "",
            "ali_id": "",
            "ali_key": "",
            "baidu_appid": "",
            "baidu_miyue": "",
            "chatgpt_api": "",
            "chatgpt_key": "",
            "chatgpt_reasoning_effort": "No",
            "chatgpt_max_token": 16384,
            "chatgpt_model": str(_settings.get('chatgpt_model', '-')).strip().split(',')[0],
            "azure_api": "",
            "azure_key": "",
            "azure_version": "2025-04-01-preview",
            "azure_model": str(_settings.get('azure_model', '-')).strip().split(',')[0],
            "gemini_key": "",
            "gemini_model": DEFAULT_GEMINI_MODEL.split(',')[0],
            "gemini_maxtoken": 16384,
            "gemini_ttsstyle": "",
            "gemini_ttsmodel": GEMINI_TTS_MODELS.split(',')[0],
            "localllm_api": "",
            "localllm_key": "",
            "localllm_model": str(_settings.get('localllm_model', '-')).strip().split(',')[0],
            "localllm_max_token": 8192,
            "zhipu_key": "",
            "zhipu_model": str(_settings.get('zhipuai_model', '-')).strip().split(',')[0],
            "zhipu_max_token": 16384,
            "guiji_key": "",
            "guiji_model": str(_settings.get('guiji_model', '-')).strip().split(',')[0],
            "guiji_max_token": 16384,
            "deepseek_key": "",
            "deepseek_model": str(_settings.get('deepseek_model', '-')).strip().split(',')[0],
            "deepseek_max_token": 32768,
            "openrouter_key": "",
            "openrouter_reasoning_effort": "No",
            "openrouter_model": str(_settings.get('openrouter_model', '-')).strip().split(',')[0],
            "openrouter_max_token": 16384,
            "zijiehuoshan_key": "",
            "zijiehuoshan_model": str(_settings.get('zijiehuoshan_model', '-')).strip().split(',')[0],
            "qwenmt_key": "",
            "qwenmt_domains": "",
            "qwenmt_model": "qwen-mt-turbo",
            "qwenmt_asr_model": "qwen3-asr-flash",
            "qwenttslocal_prompt": "",
            "ai302_key": "",
            "ai302_model": "",
            "ai302_model_recogn": "whisper-1",
            "whipserx_api": "http://127.0.0.1:9092",
            "trans_api_url": "",
            "trans_secret": "",
            "elevenlabstts_role": [],
            "elevenlabstts_key": "",
            "elevenlabstts_models": ELEVENLABS_TTS_MODELS.split(',')[0],
            "openaitts_api": "",
            "openaitts_key": "",
            "openaitts_model": "tts-1",
            "openaitts_role": "",
            "xaitts_key": "",
            "xiaomi_ttsmodel": XIAOMI_TTS_MODELS.split(',')[0],
            "xiaomi_key": "",
            "xiaomi_model": XIAOMI_MODELS.split(',')[0],
            "xiaomi_maxtoken": 16384,
            "openaitts_instructions": "",
            "qwentts_key": "",
            "qwentts_model": "qwen-tts-latest",
            "qwentts_role": "Chelsie",
            "kokoro_api": "http://127.0.0.1:5066",
            "openairecognapi_url": "",
            "openairecognapi_key": "",
            "openairecognapi_prompt": "",
            "openairecognapi_model": "whisper-1",
            "parakeet_address": "",
            "clone_api": "http://127.0.0.1:9988",
            "clone_voicelist": ["clone"],
            "recognapi_url": "",
            "recognapi_key": "",
            "stt_url": "http://127.0.0.1:9977",
            "stt_model": "large-v3-turbo",
            "ttsapi_url": "",
            "ttsapi_voice_role": "",
            "ttsapi_extra": "pyvideotrans",
            "ttsapi_language_boost": "auto",
            "ttsapi_emotion": "happy",
            "minimaxi_apikey": "",
            "minimaxi_emotion": "",
            "minimaxi_apiurl": "api.minimaxi.com",
            "minimaxi_model": MINIMAX_TTS_MODELS.split(',')[0],
            "minimax_key": "",
            "minimax_model": MINIMAX_MODELS.split(',')[0],
            "minimax_max_tokens": 16384,
            "minimax_api": "https://api.minimaxi.com/v1",
            "ai302tts_key": "",
            "ai302tts_model": "",
            "ai302tts_role": OPENAITTS_ROLES,
            "azure_speech_region": "",
            "azure_speech_key": "",
            "chatterbox_cfg_weight": 0.5,
            "chatterbox_exaggeration": 0.5,
            "gptsovits_url": "http://127.0.0.1:9880",
            "gptsovits_role": "",
            "gptsovits_isv2": True,
            "cosyvoice_url": "http://127.0.0.1:8000",
            "omnivoice_url": "http://127.0.0.1:7860",
            "fishtts_url": "http://127.0.0.1:8080/v1/tts",
            "f5tts_url": "http://127.0.0.1:7860",
            "confuciustts_url": "http://127.0.0.1:7860",
            "f5tts_model": "",
            "f5tts_ttstype": "F5-TTS",
            "f5tts_role": "nverguo.wav#你说四大皆空，却为何，紧闭双眼，若你睁开眼睛看看我，我不相信你，两眼空空。\ncosy.wav#希望你以后，能够做的比我还好哟！\nzh_male_bj.wav#说起咱北京的烤鸭啊，那可真是外焦里嫩、色泽金黄，一口咬下去满嘴流油！\nzh_female_cn.wav#大家好呀，今天跟你们分享一下我的日常护肤小习惯，其实护肤不需要太复杂，清洁补水最重要。\nzh_female_tw.wav#台湾有许多隐藏版的小吃店，他们可能不起眼，但食物却十分美味，下次不妨多留意身边这样的小店吧！",
            "index_tts_version": 1,
            "f5tts_is_whisper": False,
            "indextts_url": "http://127.0.0.1:7860",
            "voxcpmtts_url": "http://127.0.0.1:7860",
            "voxcpmtts_version": "v2",
            "sparktts_url": "http://127.0.0.1:7860",
            "doubao2_appid": "",
            "doubao2_access": "",
            "zijierecognmodel_appid": "",
            "zijierecognmodel_token": "",
            "chattts_api": "http://127.0.0.1:9966",
            "app_mode": "biaozhun",
            "stt_source_language": 0,
            "stt_recogn_type": 0,
            "stt_model_name": "large-v3-turbo",
            "stt_cuda": False,
            "stt_remove_noise": False,
            "stt_enable_diariz": False,
            "stt_rephrase": 0,
            "stt_nums_diariz": 0,
            "subtitlecover_outformat": "srt",
            "deepgram_apikey": "",
            "trans_translate_type": 0,
            "trans_source_language": 0,
            "trans_target_language": 1,
            "trans_out_format": 0,
            "dubb_source_language": 0,
            "dubb_tts_type": 0,
            "dubb_role": 0,
            "dubb_out_format": 0,
            "dubb_voice_autorate": False,
            "dubb_hecheng_rate": 0,
            "dubb_pitch_rate": 0,
            "dubb_volume_rate": 0,
            "recogn2pass": False
        }

    def _apply_dict(self, data: Dict):
        for k, v in data.items():
            setattr(self, k, v)

    def to_dict(self) -> Dict:
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

    def _save_to_disk(self):
        try:
            _write_with_retry(self._json_path, json.dumps(self.to_dict(), ensure_ascii=False))
        except Exception as e:
            logging.getLogger('VideoTrans').exception(f'保存 params 到本地失败：{e}', exc_info=True)

    def __getitem__(self, item):
        return getattr(self, item)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def get(self, key, default=None):
        return getattr(self, key, default)

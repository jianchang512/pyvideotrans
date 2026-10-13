# -*- coding: utf-8 -*-
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from videotrans.configure._paths import ROOT_DIR
from videotrans.configure._logging import _write_with_retry


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
                loaded['f5tts_role'] = (
                    "\n".join(set((loaded['f5tts_role'].strip() + "\n" + default['f5tts_role']).split("\n")))).strip()
                default.update(loaded)
            except (OSError, json.JSONDecodeError):
                pass
        else:
            self._apply_dict(default)
            self._save_to_disk()

        self._apply_dict(default)
        return self.to_dict()
    @staticmethod
    def _get_defaults():

        fix_params= {
            "last_opendir": os.path.expanduser("~"),
            "output_dir": "",

            "recogn2pass": False, #是否选中 二次识别
            "rephrase": False,# LLM 纠错
            "clear_cache": True, # 是否清理已生成

            "is_cuda": False,#默认不启用CUDA加速

            "is_separate": False,# 默认不分离人声背景声
            "embed_bgm": True,# 默认选中 重新嵌入背景声
            "remove_noise": False,#默认不降噪
            "enable_diariz": False,#默认不启用说话人分离
            "nums_diariz": 0,# 0不限制说话人数量
            "fix_punc": 0, #1= 恢复标点，2= 删除标点

            "subtitle_type": 2,#默认嵌入软字母

            "target_dir": "",

            "source_language": "en",
            "target_language": "zh-cn",

            "recogn_type": 0,#语音识别默认 faster-whisper
            "translate_type": 0,# 默认 google翻译
            "tts_type": 0,# 默认 edge-tts

            "model_name": "large-v3-turbo",#默认语音识别模型


            "voice_autorate": True,# 默认选中配音加速
            "video_autorate": False,# 默认不选视频慢速
            "align_sub_audio": True,#默认选中字幕对齐
            "voice_role": "No",#默认不选中配音角色
            "voice_rate": "0",

            "f5tts_role": "zh_female_nverguo.wav#你说四大皆空，却为何，紧闭双眼，若你睁开眼睛看看我，我不相信你，两眼空空。\nzh_female_cosy.wav#希望你以后，能够做的比我还好哟！\nzh_male_bj.wav#说起咱北京的烤鸭啊，那可真是外焦里嫩、色泽金黄，一口咬下去满嘴流油！\nzh_female_cn.wav#大家好呀，今天跟你们分享一下我的日常护肤小习惯，其实护肤不需要太复杂，清洁补水最重要。\nzh_female_tw.wav#台湾有许多隐藏版的小吃店，他们可能不起眼，但食物却十分美味，下次不妨多留意身边这样的小店吧！\nen_female_1.wav#Genes of intracellular calcium metabolism and blood pressure control in primary hypertension.\nen_female_2.wav#Diamond develops and manufactures its own coils.",



            # 语音转录面板参数
            "stt_source_language": 0,
            "stt_recogn_type": 0,
            "stt_model_name": "large-v3-turbo",
            "stt_cuda": False,
            "stt_remove_noise": False,
            "stt_enable_diariz": False,
            "stt_spk_insert": True,
            "stt_rephrase": False,
            "stt_nums_diariz": 0,
            "stt_fix_punc": 0,
            "subtitlecover_outformat": "srt",
            # 翻译字幕面板
            "trans_translate_type": 0,
            "trans_source_language": 0,
            "trans_target_language": 1,
            "trans_out_format": 0,
            # 文字配音面板
            "dubb_source_language": 0,
            "dubb_tts_type": 0,
            "dubb_role": 0,
            "dubb_out_format": 0,
            "dubb_voice_autorate": False,
            "dubb_hecheng_rate": 0,
            "dubb_pitch_rate": 0,
            "dubb_volume_rate": 0

        }
        from ._default_params import channel_default_params
        fix_params.update(channel_default_params())
        return fix_params


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

import copy,os
import re
import shutil
import time
from pathlib import Path

from videotrans.configure._paths import DUBBING_CACHE
from videotrans.configure.config import tr, app_cfg, settings, params, logger
from videotrans.configure.excepts import DubbingSrtError, StopTask
from videotrans.tts import run as run_tts, SUPPORT_CLONE, AUDIOCPP_TTS, INDEX_TTS, TTS_MODEL_PARAMS, TTS_STYLE_PARAMS
from videotrans.tts._index_emotion import emotion_cache_suffix
from videotrans.util.help_misc import get_md5, vail_file
from videotrans.util.help_srt import get_subtitle_from_srt, delete_punc


class DubbingMixin:

    def dubbing(self) -> None:
        _st=time.time()
        if self._exit() or self.cfg.app_mode == 'tiqu':
            return
        if self.should_dubbing:
            self.signal(text=tr('kaishipeiyin'))
        self.precent += 3
        self._tts()
        
        if  Path(self.cfg.source_sub).exists():
            logger.debug('配音结束后，移除原始字幕中所有标点')
            subs = get_subtitle_from_srt(self.cfg.source_sub)
            for it in subs:
                if self.cfg.fix_punc==2:
                    it['text']=delete_punc(it['text'])
                it['text']=it['text'].strip('...').strip('…').strip()
            self._save_srt_target(subs, self.cfg.source_sub)
        if self.should_dubbing:
            self.signal(text=tr('The dubbing is finished'))
            logger.debug(f'[语音合成阶段结束耗时]:{time.time()-_st}s')

    def _tts(self) -> None:
        if not self.should_dubbing:
            self.signal(text='Skip tts')
            return
        queue_tts = []
        subs = get_subtitle_from_srt(self.cfg.target_sub)
        source_subs = get_subtitle_from_srt(self.cfg.source_sub)
        if len(subs) < 1:
            raise DubbingSrtError(f"SRT file error:{self.cfg.target_sub}")
        try:
            rate = int(str(self.cfg.voice_rate).replace('%', ''))
        except (ValueError,TypeError):
            rate = 0

        rate = f"+{rate}%" if rate >= 0 else f"{rate}%"

        line_roles = app_cfg.line_roles
        voice_role = self.cfg.voice_role
        logger.debug(f'{line_roles=}')
        _lang=self.cfg.detect_language.split('-')[0]
        # 渠道配音时使用的模型：Audio.cpp 使用任务指定的模型（主窗口和网页界面会指定），未指定时（如 cli）使用保存的模型
        # 其他在设置中选择模型的渠道不使用任务指定的模型，只使用 params 中保存的模型
        tts_model = self.cfg.tts_model_name
        _model_key = TTS_MODEL_PARAMS.get(self.cfg.tts_type)
        if _model_key and not (self.cfg.tts_type == AUDIOCPP_TTS and tts_model):
            tts_model = params.get(_model_key)
        # 提示词、情绪等设置也会改变配音效果，缓存键需包含渠道配音时读取的这些设置，否则修改后仍会用上之前的配音
        # 没有此类设置的渠道缓存键不变，已有的缓存仍可使用
        _style = ''.join(f"-{params.get(k)}" for k in TTS_STYLE_PARAMS.get(self.cfg.tts_type, []))
        for i, it in enumerate(subs):
            if it['end_time'] < it['start_time'] or not it['text'].strip():
                continue
            voice = line_roles.get(f'{it["line"]}', voice_role) if line_roles else voice_role
            _line_style = _style
            if self.cfg.tts_type == INDEX_TTS:
                # 未发送情感向量时后缀为空，已有缓存仍然有效
                try:
                    _line_style += emotion_cache_suffix(params, voice)
                except ValueError as e:
                    raise StopTask(str(e)) from e
            is_clone = str(voice).strip().lower() == 'clone' and self.cfg.tts_type in SUPPORT_CLONE
            # 克隆音色时，参考音频是从当前视频中裁切的，缓存键需包含视频 uuid，否则会用上其他视频中说话人的配音
            # uuid 由文件路径、大小和修改时间生成，再次处理同一视频时不变，仍会使用缓存
            _clone = f"-{self.uuid}" if is_clone else ''
            # 同一角色由不同模型配出的声音不同，缓存键需包含渠道所用的模型，否则换模型后仍会用上之前模型的配音
            # 没有模型设置的渠道缓存键不变，已有的缓存仍可使用
            _model = f"-{tts_model}" if tts_model else ''

            _key = get_md5(f"{self.cfg.target_language_code}-{it['text']}-{voice}-{rate}-{self.cfg.volume}-{self.cfg.pitch}-{self.cfg.tts_type}-{settings.get('remove_dubb_silence', True)}-{settings.get('remove_dubb_all_silence', True)}-{settings.get('remove_dubb_silence_level', 'default')}-{settings.get('dubbing_normalize',False)}{_clone}{_model}{_line_style}")

            tmp_dict = {
                "text": it['text'],
                "line": it['line'],
                "start_time": it['start_time'],
                "end_time": it['end_time'],
                "startraw": it['startraw'],
                "endraw": it['endraw'],
                "ref_text": source_subs[i]['text'] if source_subs and i < len(source_subs) else '',
                "start_time_source": source_subs[i]['start_time'] if source_subs and i < len(source_subs) else it[
                    'start_time'],
                "end_time_source": source_subs[i]['end_time'] if source_subs and i < len(source_subs) else it[
                    'end_time'],
                "role": voice,
                "rate": rate,
                "volume": self.cfg.volume,
                "pitch": self.cfg.pitch,
                "tts_type": self.cfg.tts_type,
                "filename": f"{self.cfg.cache_folder}/{i}-{_key}.wav"
            }
            _dubbing_cache=f'{DUBBING_CACHE}/{_key}.wav'
            if vail_file(_dubbing_cache):
                # 直接使用缓存
                shutil.copy2(_dubbing_cache,tmp_dict['filename'])
            if is_clone:
                tmp_dict['ref_wav'] = f"{self.cfg.cache_folder}/clone-{i}.wav"
                tmp_dict['ref_language'] = _lang
            queue_tts.append(tmp_dict)

        self.queue_tts = queue_tts

        if not self.queue_tts or len(self.queue_tts) < 1:
            raise RuntimeError(f'字幕长度为0，无法继续配音')

        if len([it.get("ref_wav") for it in self.queue_tts if it.get("ref_wav")]) > 0:
            self._create_ref_from_vocal()

        run_tts(
            queue_tts=copy.deepcopy(queue_tts),
            language=self.cfg.target_language_code,
            uuid=self.uuid,
            tts_type=self.cfg.tts_type,
            is_cuda=self.cfg.is_cuda,
            model_name=self.cfg.tts_model_name
        )
        outname=None
        if settings.get('save_segment_audio', False):
            outname = self.cfg.target_dir + f'/segment_audio_{self.cfg.noextname}'
            Path(outname).mkdir(parents=True, exist_ok=True)
        for it in self.queue_tts:
            it['text']=it['text'].strip('...').strip('…').strip()
            if self.cfg.fix_punc==2:
                it['text']=delete_punc(it['text'])
            if vail_file(it['filename']):
                # 保存缓存
                shutil.copy2(it['filename'],f'{DUBBING_CACHE}/'+Path(it['filename']).name.split('-')[-1])
                if outname:
                    text = re.sub(r'["\'*?\\/|:<>\r\n\t]+', '', it['text'], flags=re.I | re.S)
                    name = f'{outname}/{it["line"]}-{text[:60]}.wav'
                    shutil.copy2(it['filename'], os.path.normpath(name))
        
        self._save_srt_target(self.queue_tts, self.cfg.target_sub)
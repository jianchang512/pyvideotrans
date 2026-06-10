import json
import os
import re
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from videotrans.configure import contants
from videotrans.configure.config import ROOT_DIR, tr, settings, logger, HOME_DIR
from videotrans.configure import config
from videotrans.configure.excepts import SpeechToTextError
from videotrans.recognition import run
from videotrans.task._base import BaseTask
from videotrans.task.taskcfg import TaskCfgSTT
from videotrans.util import tools

"""
仅语音识别
"""


@dataclass
class SpeechToText(BaseTask):
    cfg: TaskCfgSTT = field(default_factory=TaskCfgSTT, repr=False)
    # 识别后输出的字幕格式，srt txt 等
    out_format: str = field(init=True, default='srt')
    # 在这个子类中，should_recogn 总是 True。
    should_recogn: bool = True
    # 是否需要将生成的字幕复制到原始视频所在目录下，并重命名为视频同名，以方便视频自动加载软字幕
    copysrt_rawvideo: bool = field(default=False, init=True)
    # 存放原始语言字幕
    source_srt_list: List = field(default_factory=list)
    # 插入说话人到字幕开头
    spk_insert: bool = False

    def __post_init__(self):
        super().__post_init__()
        # -1=不启用说话人，0=启用并且不限制说话人数量，>0+1是最大说话人数量
        self.max_speakers = self.cfg.nums_diariz if self.cfg.enable_diariz else -1
        if self.max_speakers > 0:
            self.max_speakers += 1
        # 存放目标文件夹
        if not self.cfg.target_dir:
            self.cfg.target_dir = HOME_DIR + f"/recogn"
        # 转录后的目标字幕文件，先统一转为srt，然后再使用ffmpeg转为其他格式字幕
        self.cfg.target_sub = self.cfg.target_dir + '/' + self.cfg.noextname + '.srt'
        # 临时文件夹
        self.cfg.cache_folder = config.TEMP_DIR + f'/{self.uuid}'
        # 处理为 16k 的wav单通道音频，供模型识别用
        self.cfg.shibie_audio = self.cfg.cache_folder + f'/{self.cfg.noextname}-{time.time()}.wav'
        self.signal(text=tr("Speech Recognition to Word Processing"))

    # 预先处理
    def prepare(self):
        if self._exit(): return
        Path(self.cfg.target_dir).mkdir(parents=True, exist_ok=True)
        Path(self.cfg.cache_folder).mkdir(parents=True, exist_ok=True)
        tools.conver_to_16k(self.cfg.name, self.cfg.shibie_audio)

    def recogn(self):
        while 1:
            if self._exit(): return
            # 尚未生成
            if Path(self.cfg.shibie_audio).exists():
                break
            time.sleep(0.5)

        # 需要降噪
        if self.cfg.remove_noise:
            logger.debug('开始降噪，实际使用人声分离操作替换降噪，速度更快')
            title = tr('Starting to process speech noise reduction, which may take a long time, please be patient')

            tools.down_file_from_ms(f'{ROOT_DIR}/models/onnx', [
                f"https://www.modelscope.cn/models/himyworld/videotrans/resolve/master/onnx/vocals.fp16.onnx",
                f"https://www.modelscope.cn/models/himyworld/videotrans/resolve/master/onnx/accompaniment.fp16.onnx"
            ], callback=self._process_callback)

            _44100_ac2 = f"{self.cfg.cache_folder}/44100-ac2.wav"
            _noise_wav = f"{config.TEMP_DIR}/{self.cfg.noextname}-{os.path.getsize(self.cfg.name)}-removed_noise.wav"
            tools.runffmpeg([
                "-y",
                "-i",
                self.cfg.name,
                "-ac",
                "2",
                "-ar",
                "44100",
                "-c:a",
                "pcm_s16le",
                _44100_ac2
            ])

            from videotrans.process.prepare_audio import vocal_bgm_spleeter
            kw = {
                "input_file": _44100_ac2,
                "vocal_file": _noise_wav,
                "instr_file": f"{self.cfg.cache_folder}/remove_noise.wav"
            }
            # 静默失败，不处理
            try:
                rs = self._new_process(callback=vocal_bgm_spleeter, title=title, is_cuda=False, kwargs=kw)
                if rs and tools.vail_file(_noise_wav):
                    cmd = [
                        "-y",
                        "-i",
                        _noise_wav,
                        "-ac",
                        "1",
                        "-ar",
                        "16000",
                        "-c:a",
                        "pcm_s16le",
                        '-af',
                        "volume=1.5",
                        self.cfg.shibie_audio
                    ]
                    tools.runffmpeg(cmd)
                    self.signal(text='remove noise end')
                logger.debug('降噪结束：批量语音转录使用分离人声替代降噪操作')
            except Exception as e:
                logger.exception(f'降噪静默失败 {e}', exc_info=True)

        if self._exit(): return
        raw_subtitles = run(
            recogn_type=self.cfg.recogn_type,
            uuid=self.uuid,
            model_name=self.cfg.model_name,
            audio_file=self.cfg.shibie_audio,
            detect_language=self.cfg.detect_language,
            cache_folder=self.cfg.cache_folder,
            is_cuda=self.cfg.is_cuda,
            subtitle_type=0,
            max_speakers=self.max_speakers,
            llm_post=self.cfg.rephrase == 1
        )
        if not raw_subtitles or len(raw_subtitles) < 1:
            raise SpeechToTextError(self.cfg.basename + tr('recogn result is empty'))
        self.source_srt_list = raw_subtitles
        self._save_srt_target(self.source_srt_list, self.cfg.target_sub)
        if self._exit() or self.cfg.detect_language == 'auto': return

        # 中英恢复标点符号
        if self.cfg.fix_punc==1 and self.cfg.detect_language[:2] in ['zh', 'en']:
            tools.down_file_from_ms(f'{ROOT_DIR}/models/puntc', [
                    "https://www.modelscope.cn/models/himyworld/videotrans/resolve/master/puntc/model.onnx",
                    "https://www.modelscope.cn/models/himyworld/videotrans/resolve/master/puntc/config.yaml",
                    "https://www.modelscope.cn/models/himyworld/videotrans/resolve/master/puntc/tokens.json",
            ], callback=self._process_callback)
            text_dict = {f'{it["line"]}': re.sub(r'[,.?!，。？！]', ' ', it["text"]) for it in self.source_srt_list}
            # 序列化后传递文件路径
            text_dict_file=f'{self.cfg.cache_folder}/text_dict_file_{time.time()}.json'
            Path(text_dict_file).write_text(json.dumps(text_dict),encoding="utf-8")
            kw = {"text_dict_file": text_dict_file, "is_cuda": self.cfg.is_cuda}

            from videotrans.process.prepare_audio import fix_punc

            try:
                _rs = self._new_process(callback=fix_punc, title=tr("Restoring punct"), kwargs=kw)
                if _rs:
                    text_dict_obj=json.loads(Path(text_dict_file).read_text(encoding='utf-8'))
                    for it in self.source_srt_list:
                        it['text'] = text_dict_obj.get(f'{it["line"]}', it['text'])
                        if self.cfg.detect_language[:2] == 'en':
                            it['text'] = it['text'].replace('，', ',').replace('。', '. ').replace('？', '?').replace(
                                '！', '!')
                    self._save_srt_target(self.source_srt_list, self.cfg.target_sub)
                else:
                    logger.error('标点恢复出错')
            except Exception as e:
                logger.exception(f'恢复标点出错，跳过{e}', exc_info=True)

        # 本身已有说话人识别的，就不再重新断句
        self.signal(text=Path(self.cfg.target_sub).read_text(encoding='utf-8'), type='replace_subtitle')
        if Path(self.cfg.cache_folder + "/speaker.json").exists(): return

        if self.cfg.rephrase == 1:
            # LLM重新断句
            try:
                from videotrans.translator._openaicompat import OpenAICampat
                ob = OpenAICampat(
                    ainame='chatgpt' if settings.get('llm_ai_type', 'chatgpt') != 'deepseek' else 'deepseek',
                    uuid=self.uuid)
                self.signal(text=tr("Re-segmenting..."))
                srt_list = ob.llm_segment(self.source_srt_list)
                if srt_list and len(srt_list) > len(self.source_srt_list) / 2:
                    self.source_srt_list = srt_list
                    self._save_srt_target(self.source_srt_list, self.cfg.target_sub)
                else:
                    logger.error(f'重新断句失败，已恢复原样,原始字幕行:{len(self.source_srt_list)}, 重新断句后字幕行:{len(srt_list)}\n断句结果:\n{srt_list=}')
            except Exception as e:
                self.signal(text=tr("Re-segmenting Error"))
                logger.exception(f"重新断句失败已恢复原样 {e}", exc_info=True)

    def diariz(self):
        if self._exit() or not self.cfg.enable_diariz or Path(self.cfg.cache_folder + "/speaker.json").exists():
            return

        speaker_type = settings.get('speaker_type', 'built')
        hf_token = settings.get('hf_token')
        if speaker_type == 'built' and self.cfg.detect_language[:2] not in ['zh', 'en']:
            logger.error(f'当前选择 built 说话人分离模型，但不支持当前语言:{self.cfg.detect_language}')
            return
        if speaker_type in ['pyannote', 'reverb'] and not hf_token:
            logger.error(f'当前选择 pyannote 说话人分离模型，但未设置 huggingface.co 的token: {self.cfg.detect_language}')
            return
        hf_endpoit = "https://huggingface.co"
        if speaker_type in ['pyannote', 'reverb']:
            try:
                import requests
                requests.head('https://huggingface.co', timeout=5)
            except Exception:
                logger.exception(f'当前选择 {speaker_type} 说话人分离模型，但无法连接到 https://huggingface.co,可能会失败', exc_info=True)
                hf_endpoit = "https://hf-mirror.com"

        self.precent += 3
        title = tr(f'Begin separating the speakers') + f':{speaker_type}'
        subtitles_file=f'{self.cfg.cache_folder}/diariz-{time.time()}.json'
        Path(subtitles_file).write_text(json.dumps([[it['start_time'], it['end_time']] for it in self.source_srt_list]),encoding='utf-8')
        kw = {
            "input_file": self.cfg.shibie_audio,
            "subtitles_file": subtitles_file,
            "speak_file":self.cfg.cache_folder + "/speaker.json",
            "num_speakers": self.max_speakers,
            "is_cuda": self.cfg.is_cuda
        }
        if speaker_type == 'built':
            tools.down_file_from_ms(f'{ROOT_DIR}/models/onnx', [
                "https://www.modelscope.cn/models/himyworld/videotrans/resolve/master/onnx/seg_model.onnx",
                "https://www.modelscope.cn/models/himyworld/videotrans/resolve/master/onnx/nemo_en_titanet_small.onnx",
                "https://www.modelscope.cn/models/himyworld/videotrans/resolve/master/onnx/3dspeaker_speech_eres2net_large_sv_zh-cn_3dspeaker_16k.onnx"
            ], callback=self._process_callback)
            from videotrans.process.prepare_audio import built_speakers as _run_speakers
            del kw['is_cuda']
            kw['num_speakers'] = -1 if self.max_speakers < 1 else self.max_speakers
            kw['language'] = self.cfg.detect_language
        elif speaker_type == 'ali_CAM':
            tools.check_and_down_ms(model_id='iic/speech_campplus_speaker-diarization_common',
                                    callback=self._process_callback)
            from videotrans.process.prepare_audio import cam_speakers as _run_speakers
        elif speaker_type == 'pyannote':
            from videotrans.process.prepare_audio import pyannote_speakers as _run_speakers
        elif speaker_type == 'reverb':
            from videotrans.process.prepare_audio import reverb_speakers as _run_speakers
        else:
            logger.error(f'当前所选说话人分离模型不支持:{speaker_type=}')
            return
        try:
            if speaker_type in ['pyannote', 'reverb']:
                self.signal(text='Downloading speakers models')
                from huggingface_hub import snapshot_download
                snapshot_download(
                    repo_id="pyannote/speaker-diarization-3.1" if speaker_type == 'pyannote' else "Revai/reverb-diarization-v1",
                    token=hf_token,
                    endpoint=hf_endpoit
                )
            _rs = self._new_process(callback=_run_speakers, title=title,
                                         is_cuda=self.cfg.is_cuda and speaker_type != 'built', kwargs=kw)

            logger.debug('分离说话人成功完成' if _rs else '分离失败说话人失败')
            self.signal(text=tr('separating speakers end'))
        except Exception as e:
            logger.exception(f'说话人分离失败，跳过 {e}', exc_info=True)
        self.signal(text=tr('separating speakers end'))

    def task_done(self):
        if self._exit(): return
        if self.cfg.detect_language and self.cfg.detect_language != 'auto':
            # 处理换行
            maxlen = int(
                settings.get('cjk_len', 15) if self.cfg.detect_language[:2] in contants.CJK_LANG else
                settings.get('other_len', 60))
            for i, it in enumerate(self.source_srt_list):
                it['text'] = tools.simple_wrap(it['text'], maxlen, self.cfg.detect_language)

        # 移除标点符号
        if self.cfg.fix_punc==2:
            for i, it in enumerate(self.source_srt_list):
                it['text'] = tools.delete_punc(it['text'])


        if self.cfg.enable_diariz and self.spk_insert and Path(
                self.cfg.cache_folder + "/speaker.json").exists():
            speakers = json.loads(Path(self.cfg.cache_folder + "/speaker.json").read_text(encoding='utf-8'))
            if speakers:
                speakers_len = len(speakers)
                for i, it in enumerate(self.source_srt_list):
                    if i < speakers_len and speakers[i]:
                        it['text'] = f'[{speakers[i]}]{it["text"]}'

        self._save_srt_target(self.source_srt_list, self.cfg.target_sub)
        if self.out_format == 'txt':
            self.cfg.target_sub = self.cfg.target_sub[:-3] + 'txt'
            Path(self.cfg.target_sub).write_text("\r\n".join([it["text"] for it in self.source_srt_list]),
                                                 encoding='utf-8')
        elif self.out_format != 'srt':
            tools.runffmpeg(['-y', '-i', self.cfg.target_sub, self.cfg.target_sub[:-3] + self.out_format])
            Path(self.cfg.target_sub).unlink(missing_ok=True)
            self.cfg.target_sub = self.cfg.target_sub[:-3] + self.out_format

        if self.copysrt_rawvideo:
            p = Path(self.cfg.name)
            try:
                shutil.copy2(self.cfg.target_sub, f'{p.parent.as_posix()}/{p.stem}.{self.out_format}')
            except shutil.SameFileError:
                pass
        self.set_end(True)

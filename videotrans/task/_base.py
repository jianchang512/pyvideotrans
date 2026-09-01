import copy
import json
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Union
from videotrans.configure.config import tr, app_cfg, logger, ROOT_DIR, settings
from videotrans.configure.base import BaseCon
from videotrans.configure.contants import BUILTINT_URL_MS, BUILTINT_URL_HF
from videotrans.task.taskcfg import TaskCfgBase, SrtItem
from videotrans.translator._registry import get_name_index
from videotrans.translator._runner import get_model_transobj
from videotrans.util.help_misc import is_connect_hf


@dataclass
class BaseTask(BaseCon):
    # 各项配置信息，例如 翻译、配音、识别渠道等
    cfg: TaskCfgBase = field(default_factory=TaskCfgBase, repr=False)
    # 进度记录
    precent: int = 1
    # 需要配音的原始字幕信息 List[dict]
    queue_tts: List = field(default_factory=list, repr=False)
    # 是否已结束
    hasend: bool = False
    # 是否需要语音识别
    should_recogn: bool = False
    # 是否需要字幕翻译
    should_trans: bool = False
    # 是否需要配音
    should_dubbing: bool = False
    # 是否需要嵌入配音或字幕
    should_hebing: bool = False

    def __post_init__(self):
        super().__post_init__()
        if self.cfg.uuid:
            self.uuid = self.cfg.uuid

    # 预先处理，例如从视频中拆分音频、人声背景分离、转码等
    def prepare(self):
        pass

    # 语音识别创建原始语言字幕
    def recogn(self):
        pass

    # 说话人识别，Funasr/豆包语音识别大模型 /Deepgram 除外，再判断是否已有说话人，Gemini/openai gpt4-dia 会生成说话人
    def diariz(self):
        pass

    # 将原始语言字幕翻译到目标语言字幕
    def trans(self):
        pass

    # 根据 queue_tts 进行配音
    def dubbing(self):
        pass

    # 配音加速、视频慢速对齐
    def align(self):
        pass

    # 视频、音频、字幕合并生成结果文件
    def assembling(self):
        pass

    # 删除临时文件，移动或复制，发送成功消息
    def task_done(self):
        pass

    # 删掉尺寸为0的无效文件
    @staticmethod
    def _unlink_size0(file: Union[str, List[str]]):
        if not file: return
        files = [file] if isinstance(file, str) else file
        for f in files:
            p = Path(f)
            if p.exists() and p.stat().st_size == 0:
                p.unlink(missing_ok=True)

    # 保存字幕文件 到目标文件夹
    def _save_srt_target(self, srt_list: List[SrtItem], file: str):
        from videotrans.util.help_srt import get_srt_from_list
        try:
            txt = get_srt_from_list(srt_list)
            Path(file).parent.mkdir(exist_ok=True, parents=True)
            with open(file, "w", encoding="utf-8", errors="ignore") as f:
                f.write(txt)
        except Exception as e:
            from videotrans.configure.excepts import VideoTransError
            raise VideoTransError(f'保存字幕前格式化srt失败:{file=}') from e

        self.signal(text=Path(file).read_text(encoding='utf-8', errors="ignore"), type='replace_subtitle')
        return True

    def _llmpost(self,raw_subtitles,step=''):
        try:
            _ai_type=settings.get('llm_ai_type',1)
            ob = get_model_transobj(translate_type=get_name_index(_ai_type,'index'),uuid=self.uuid)

            self.signal(text=tr("Re-segmenting..."))
            srt_list = ob.llm_segment(raw_subtitles,step=step)
            if srt_list and len(srt_list) > len(raw_subtitles) / 2:
                return srt_list
            logger.error(f'二次识别后LLM重新断句失败，已恢复原样,原始字幕行:{len(raw_subtitles)}, 重新断句后字幕行:{len(srt_list)}\n断句结果:\n{srt_list=}')
        except Exception as e:
            self.signal(text=tr("Re-segmenting Error"))
            logger.exception(f"二次识别后重新断句失败，已恢复原样 {e}", exc_info=True)
        return raw_subtitles

    # 如果启用了 LLM重新断句，则跳过该步骤，LLM断句后时间轴发生变更，无法和原始字幕对齐
    @staticmethod
    def check_target_sub(source_srt_list: List[SrtItem], target_srt_list: List[SrtItem]) -> List[SrtItem]:
        source_len = len(source_srt_list)
        target_len = len(target_srt_list)
        if source_len == target_len:
            logger.debug(f'原始语言字幕和目标语言字幕行数一致，均为 {source_len=}')
            return target_srt_list

        logger.warning(f'翻译结果行数{target_len}，原始字幕行数{source_len}，不一致,根据原始字幕时间轴获取对应目标字幕文本')
        # 根据原始字幕的时间轴，到目标字幕内寻找同样时间轴的字幕文本，更准确
        _time2srt = {}
        for it in target_srt_list:
            _time2srt[it['time']] = it['text']

        logger.debug(f'翻译结果行数{target_len} > 原始字幕行{source_len}，根据原始字幕的时间轴，到目标字幕内寻找同样时间轴的字幕文本')
        _source = copy.deepcopy(source_srt_list)
        for it in _source:
            it['text'] = _time2srt.get(it['time'], '')
        return _source

    # 手动调用设为结束，成功完成或出错时
    def set_end(self, succeed=False):
        self.hasend = True
        if succeed:
            self.precent = 100
            if self.uuid in app_cfg.stoped_uuid_set:
                return
            self.signal(text=f"{self.cfg.name}", type='succeed')
            if app_cfg.exec_mode == "cli":
                print(f'Save to:[ {self.cfg.target_dir} ]')
            else:
                from videotrans.util.help_ffmpeg import send_notification
                send_notification(tr('Succeed'), f"{self.cfg.basename}")
            # 清理临时文件
            try:
                if self.cfg.cache_folder:
                    shutil.rmtree(self.cfg.cache_folder, ignore_errors=True)
            except Exception as e:
                logger.exception(f'任务结束后清理临时文件失败，跳过,{e}:{self.cfg.cache_folder=}', exc_info=True)
        app_cfg.stoped_uuid_set.add(self.uuid)



    def _diariz_common(self,shibieaudio=None):
        _st=time.time()
        speaker_type = settings.get('speaker_type', 'built')
        hf_token = settings.get('hf_token')
        # if speaker_type == 'built' and self.cfg.detect_language.split('-')[0] not in ['zh', 'en','auto']:
        #     logger.error(f'当前选择 built 说话人分离模型，但不支持当前语言:{self.cfg.detect_language}')
        #     return
        if speaker_type in ['pyannote', 'reverb'] and not hf_token:
            logger.error(f'当前选择 pyannote 说话人分离模型，但未设置 huggingface.co 的token: {self.cfg.detect_language}')
            return
        from videotrans.util.help_down import down_file_from_hf, check_and_down_ms
        ishf=is_connect_hf()
        try:
            self.precent += 3
            title = tr('Speaker classification') + f':{speaker_type}'
            subtitles_file=f'{self.cfg.cache_folder}/diariz-{time.time()}.json'
            Path(subtitles_file).write_text(json.dumps([[it['start_time'], it['end_time']] for it in self.source_srt_list]),encoding='utf-8')
            kw = {
                "input_file": self.cfg.source_wav if not shibieaudio else shibieaudio,
                "subtitles_file": subtitles_file,
                "speak_file":self.cfg.cache_folder + "/speaker.json",
                "num_speakers": self.max_speakers,
                "is_cuda": self.cfg.is_cuda
            }
            if speaker_type == 'built':
                down_file_from_hf(f'{ROOT_DIR}/models/onnx', BUILTINT_URL_MS if not ishf else BUILTINT_URL_HF, callback=self._process_callback)
                from videotrans.process.prepare_audio import built_speakers as _run_speakers
                del kw['is_cuda']
                kw['num_speakers'] = -1 if self.max_speakers < 1 else self.max_speakers
                kw['language'] = self.cfg.detect_language
            elif speaker_type == 'ali_CAM':
                check_and_down_ms(model_id='iic/speech_campplus_speaker-diarization_common',
                    local_dir=f"{ROOT_DIR}/models/speech_campplus_speaker-diarization_common",
                    callback=self._process_callback)
                from videotrans.process.prepare_audio import cam_speakers as _run_speakers
            elif speaker_type in ['pyannote','reverb']:
                from videotrans.process.prepare_audio import pyannote_speakers as _run_speakers
            else:
                logger.error(f'当前所选说话人分离模型不支持:{speaker_type=}')
                return
            if speaker_type in ['pyannote', 'reverb']:
                from videotrans.util.help_down import check_and_down_hf
                check_and_down_hf(
                    speaker_type,
                    "pyannote/speaker-diarization-3.1",
                    f'{ROOT_DIR}/models/models--pyannote--speaker-diarization-3.1',
                    self._process_callback,
                    None,
                    hf_token)
                check_and_down_hf(
                    speaker_type,
                    "pyannote/segmentation-3.0",
                    f'{ROOT_DIR}/models/models--pyannote--segmentation-3.0',
                    self._process_callback,
                    None,
                    hf_token)
                check_and_down_hf(
                    speaker_type,
                    "pyannote/wespeaker-voxceleb-resnet34-LM",
                    f'{ROOT_DIR}/models/models--pyannote--wespeaker-voxceleb-resnet34-LM',
                    self._process_callback,
                    None,
                    hf_token)

            _rs = self._new_process(callback=_run_speakers, title=title,
                                         is_cuda=self.cfg.is_cuda and speaker_type != 'built', kwargs=kw)

            if _rs:
                logger.debug('分离说话人成功完成')
                shutil.copy2(self.cfg.cache_folder + "/speaker.json", self.cfg.target_dir + "/speaker.json")
            else:
                logger.error('分离失败说话人失败')
            self.signal(text=tr('separating speakers end'))
        except Exception as e:
            logger.exception(f'说话人分离失败，跳过 {e}', exc_info=True)

        logger.debug(f'[说话人分离阶段结束耗时]:{time.time()-_st}s')


    async def _edgetts_single(self, target_audio, kwargs):
        from edge_tts import Communicate
        from io import BytesIO
        from videotrans.configure.excepts import DubbingSrtError

        useproxy_initial = None if not self.proxy_str or Path(
            f'{ROOT_DIR}/edgetts-noproxy.txt').exists() else self.proxy_str
        proxies_to_try = [useproxy_initial]
        if useproxy_initial is not None:
            proxies_to_try.append(None)

        for proxy in proxies_to_try:
            try:
                audio_buffer = BytesIO()
                communicate_task = Communicate(
                    text=kwargs['text'],
                    voice=kwargs['voice'],
                    rate=kwargs['rate'],
                    volume=kwargs['volume'],
                    proxy=proxy,
                    pitch=kwargs['pitch']
                )
                idx = 0
                async for chunk in communicate_task.stream():
                    if chunk["type"] == "audio":
                        audio_buffer.write(chunk["data"])
                        self.signal(text=f'{idx} segment')
                        idx += 1
                audio_buffer.seek(0)
                from pydub import AudioSegment
                au = AudioSegment.from_file(audio_buffer, format="mp3")
                au.export(target_audio, format='mp3')
                return
            except Exception as e:
                raise DubbingSrtError(f'edge-tts error:{target_audio=}') from e
        raise DubbingSrtError(f'Dubbing error')

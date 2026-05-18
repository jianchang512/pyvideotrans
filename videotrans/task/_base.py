import copy
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Union
from videotrans.configure.config import tr, app_cfg, logger, ROOT_DIR
from videotrans.configure.base import BaseCon
from videotrans.configure.excepts import DubbingSrtError, VideoTransError
from videotrans.task.taskcfg import TaskCfgBase, SrtItem
from videotrans.util import tools


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
    shoud_recogn: bool = False
    # 是否需要字幕翻译
    shoud_trans: bool = False
    # 是否需要配音
    shoud_dubbing: bool = False
    # 是否需要人声分离
    shoud_separate: bool = False
    # 是否需要嵌入配音或字幕
    shoud_hebing: bool = False

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
    def _unlink_size0(self, file: Union[str, List[str]]):
        if not file: return
        files = [file] if isinstance(file, str) else file
        for f in files:
            p = Path(f)
            if p.exists() and p.stat().st_size == 0:
                p.unlink(missing_ok=True)

    # 保存字幕文件 到目标文件夹
    def _save_srt_target(self, srtstr: List[SrtItem], file: str):
        try:
            txt = tools.get_srt_from_list(srtstr)
            with open(file, "w", encoding="utf-8", errors="ignore") as f:
                f.write(txt)
        except Exception as e:
            raise VideoTransError(f'保存字幕前格式化srt失败:{file=}') from e

        self.signal(text=Path(file).read_text(encoding='utf-8', errors="ignore"), type='replace_subtitle')
        return True

    def check_target_sub(self, source_srt_list: List[SrtItem], target_srt_list: List[SrtItem]) -> List[SrtItem]:
        if len(source_srt_list) == 1 or len(target_srt_list) == 1:
            target_srt_list[0]['line'] = 1
            return target_srt_list[:1]
        source_len = len(source_srt_list)
        target_len = len(target_srt_list)

        if source_len == target_len:
            for i, it in enumerate(source_srt_list):
                tmp = copy.deepcopy(it)
                tmp['text'] = target_srt_list[i]['text']
                target_srt_list[i] = tmp
            return target_srt_list

        if target_len > source_len:
            logger.debug(f'翻译结果行数大于原始字幕行，截取0-{source_len}')
            return target_srt_list[:source_len]

        logger.debug(f'翻译结果行数少于原始字幕行，追加')
        for i, it in enumerate(source_srt_list):
            if i >= target_len:
                tmp = copy.deepcopy(it)
                tmp['text'] = ' '
                target_srt_list.append(tmp)
        return target_srt_list

    # 手动调用设为结束，成功完成或出错时
    def set_end(self, succeed=False):
        self.hasend = True
        if succeed:
            self.precent = 100
            if self.uuid in app_cfg.stoped_uuid_set:
                return
            self.signal(text=f"{self.cfg.name}", type='succeed')
            if app_cfg.exec_mode=="cli":
                print(f'Save to:[ {self.cfg.target_dir} ]')
            else:
                tools.send_notification(tr('Succeed'), f"{self.cfg.basename}")
            # 清理临时文件
            try:
                shutil.rmtree(self.cfg.cache_folder, ignore_errors=True)
            except Exception as e:
                logger.exception(f'任务结束后清理临时文件失败，跳过,{e}:{self.cfg.cache_folder=}', exc_info=True)
        app_cfg.stoped_uuid_set.add(self.uuid)

    async def _edgetts_single(self, target_audio, kwargs):
        from edge_tts import Communicate
        from io import BytesIO

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

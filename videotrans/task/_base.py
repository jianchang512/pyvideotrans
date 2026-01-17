import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from videotrans.configure import config
from videotrans.configure._base import BaseCon
from videotrans.task.taskcfg import TaskCfg
from videotrans.util import tools


@dataclass
class BaseTask(BaseCon):
    # 各项配置信息，例如 翻译、配音、识别渠道等
    cfg: TaskCfg = field(default_factory=TaskCfg, repr=False)
    # 进度记录
    precent: int = 1
    # 需要配音的原始字幕信息 List[dict]
    queue_tts: List = field(default_factory=list, repr=False)
    # 是否已结束
    hasend: bool = False

    # 名字规范化处理后，应该删除的文件名字
    shound_del_name: str = None

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
        if self.cfg.clear_cache and Path(self.cfg.target_dir).is_dir():
            shutil.rmtree(self.cfg.target_dir, ignore_errors=True)
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

    # 字幕是否存在并且有效
    def _srt_vail(self, file):
        if not file:
            return False
        if not tools.vail_file(file):
            return False
        try:
            tools.get_subtitle_from_srt(file)
        except Exception:
            try:
                Path(file).unlink(missing_ok=True)
            except OSError:
                pass
            return False
        return True

    # 删掉尺寸为0的无效文件
    def _unlink_size0(self, file):
        if not file:
            return
        p = Path(file)
        if p.exists() and p.stat().st_size == 0:
            p.unlink(missing_ok=True)

    # 保存字幕文件 到目标文件夹
    def _save_srt_target(self, srtstr, file):
        # 是字幕列表形式，重新组装
        try:
            txt = tools.get_srt_from_list(srtstr)
            with open(file, "w", encoding="utf-8",errors="ignore") as f:
                f.write(txt)
        except Exception:
            raise
        self._signal(text=Path(file).read_text(encoding='utf-8',errors="ignore"), type='replace_subtitle')
        return True

    def _check_target_sub(self, source_srt_list, target_srt_list):
        import re, copy
        if len(source_srt_list) == 1 or len(target_srt_list) == 1:
            target_srt_list[0]['line'] = 1
            return target_srt_list[:1]
        source_len = len(source_srt_list)
        target_len = len(target_srt_list)
        config.logger.debug(f'核对翻译结果前->原始语言字幕行数:{source_len},目标语言字幕行数:{target_len}')
        
        if source_len==target_len:
            for i,it in enumerate(source_srt_list):
                tmp = copy.deepcopy(it)
                tmp['text']=target_srt_list[i]['text']
                target_srt_list[i]=tmp
            return target_srt_list

        if target_len>source_len:
            config.logger.debug(f'翻译结果行数大于原始字幕行，截取0-{source_len}')
            return target_srt_list[:source_len]
        
        
        config.logger.debug(f'翻译结果行数少于原始字幕行，追加')
        for i,it in enumerate(source_srt_list):
            if i>=target_len:
                tmp=copy.deepcopy(it)
                tmp['text']=' '
                target_srt_list.append(tmp)
        return target_srt_list
        
    


    async def _edgetts_single(self,target_audio,kwargs):
        from edge_tts import Communicate
        from edge_tts.exceptions import NoAudioReceived
        import aiohttp,asyncio
        from io import BytesIO
        
        useproxy_initial = None if not self.proxy_str or Path(f'{config.ROOT_DIR}/edgetts-noproxy.txt').exists() else self.proxy_str
        proxies_to_try = [useproxy_initial]
        if useproxy_initial is not None:
            proxies_to_try.append(None)
        last_exception = None
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
                idx=0
                async for chunk in communicate_task.stream():
                    if chunk["type"] == "audio":
                        audio_buffer.write(chunk["data"])
                        self._signal(text=f'{idx} segment')
                        idx+=1
                audio_buffer.seek(0)        
                from pydub import AudioSegment
                au=AudioSegment.from_file(audio_buffer,format="mp3")
                au.export(target_audio,format='mp3')
                return
            except (NoAudioReceived, aiohttp.ClientError) as e:
                last_exception = e
            except Exception:
                raise
        raise last_exception if last_exception else RuntimeError(f'Dubbing error')
    # 完整流程判断是否需退出，子功能需重写
    def _exit(self):
        if config.exit_soft or config.current_status != 'ing':
            self.hasend=True
            return True
        return False

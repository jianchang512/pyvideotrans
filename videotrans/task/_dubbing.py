import copy
import datetime
import re
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from videotrans import tts
from videotrans.configure import config
from videotrans.configure.config import tr
from videotrans.task._base import BaseTask
from videotrans.task._rate import SpeedRate
from videotrans.util import tools

"""
仅配音任务：对应 批量为字幕配音 面板
"""


@dataclass
class DubbingSrt(BaseTask):
    # 是否是 字幕多角色配音 功能
    out_ext:str="wav"
    is_multi_role: bool = field(init=True,default=False)
    # 固定为True
    shoud_dubbing: bool = field(default=True, init=False)
    ignore_align:bool=False
    # 多角色配音时直接使用该字幕信息
    subs:List = field(default_factory=list, repr=False)
    def __post_init__(self):
        super().__post_init__()
        # 是否是 字幕多角色配音
        # 输出目标位置
        if not self.cfg.target_dir:
            self.cfg.target_dir = f"{config.HOME_DIR}/tts"
        if self.cfg.cache_folder:
            Path(self.cfg.cache_folder).mkdir(parents=True, exist_ok=True)
        Path(self.cfg.target_dir).mkdir(parents=True, exist_ok=True)
        # 需要配音的字幕文件
        self.cfg.target_sub = self.cfg.name
        # 配音后音频文件保存为
        self.cfg.target_wav = f'{self.cfg.target_dir}/{self.cfg.noextname}.{self.out_ext}'
        self._signal(text=tr("Dubbing from subtitles"))
        config.logger.debug(f'配音 {self.cfg=}')


    def dubbing(self):
        try:
            self._signal(text=Path(self.cfg.target_sub).read_text(encoding='utf-8'), type="replace")
            self._tts()
        except Exception as e:
            self.hasend = True
            raise

    # 字幕可能是gbk gb2312 等编码，需转为 utf-8
    def _convert_to_utf8_if_needed(self, file_path: str) -> str:
        import tempfile
        try:
            # 1. 尝试以 UTF-8 编码打开并完全读取文件，检查其有效性
            # 'strict' 是默认错误处理方式，遇到无法解码的字节会抛出 UnicodeDecodeError
            with open(file_path, 'r', encoding='utf-8', errors='strict') as f:
                f.read()
            return file_path
        except UnicodeDecodeError:

            # 2. 如果 UTF-8 解码失败，尝试使用其他常见编码
            #    你可以根据你的实际情况调整这个列表的顺序或内容
            fallback_encodings = ['gbk', 'gb2312', 'big5', 'latin-1']
            original_content = None
            # 以二进制模式读取一次文件内容，避免重复IO
            try:
                with open(file_path, 'rb') as f:
                    raw_data = f.read()
            except FileNotFoundError:
                raise
            for encoding in fallback_encodings:
                try:
                    original_content = raw_data.decode(encoding)
                    break  # 只要有一个成功就跳出循环
                except UnicodeDecodeError:
                    continue  # 如果此编码也失败，则尝试下一个

            # 3. 如果所有备选编码都失败了，则无法处理
            if original_content is None:
                return file_path

            # 4. 创建一个带名字的临时文件来保存转换后的内容
            #    - mode='w'：以文本模式写入
            #    - encoding='utf-8'：指定写入编码为 UTF-8
            #    - suffix='.txt'：让临时文件保持 .txt 扩展名
            #    - delete=False：保证在 with 语句块结束后，文件不会被自动删除
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.txt', delete=False) as temp_file:
                temp_file.write(original_content)
                temp_file_path = temp_file.name
            return temp_file_path
        except FileNotFoundError:
            raise

    # 配音预处理，去掉无效字符，整理开始时间
    def _tts(self) -> None:
        queue_tts = []
        # 获取字幕
        try:
            rate = int(str(self.cfg.voice_rate).replace('%', ''))
        except ValueError:
            rate = 0
        if rate >= 0:
            rate = f"+{rate}%"
        else:
            rate = f"{rate}%"
        # 如果渠道是 edge-tts,并且非多角色配音 
        _enter_edgetts_single=self.cfg.tts_type == tts.EDGE_TTS and not self.is_multi_role
        if _enter_edgetts_single:
            # 配音文件是txt
            if self.cfg.target_sub.endswith('.txt'):
                _enter_edgetts_single=True
            elif not self.cfg.voice_autorate and self.cfg.remove_silent_mid:
                # 或者未自动加速 并且移除了字幕间静音
                _enter_edgetts_single=True
            else:
                _enter_edgetts_single=False
        

        if _enter_edgetts_single:
            from edge_tts import Communicate
            import asyncio
            # 忽略对齐
            self.ignore_align=True
            self.cfg.target_sub = self._convert_to_utf8_if_needed(self.cfg.target_sub)
            
            tmp_name = self.cfg.target_wav if self.cfg.target_wav.endswith(
                '.mp3') else f"{self.cfg.cache_folder}/{self.cfg.noextname}-edgetts-txt-{time.time()}.mp3"
            if self.cfg.target_sub.endswith('.txt'):
                text=Path(self.cfg.target_sub).read_text(encoding='utf-8')
            else:
                text=""
                self.queue_tts=tools.get_subtitle_from_srt(self.cfg.target_sub)
                for it in self.queue_tts:
                    text+=it["text"]+"\n"
                self.queue_tts=self.queue_tts[:1]

            asyncio.run(self._edgetts_single(
                tmp_name,
                dict(text=text,
                    voice=tools.get_edge_rolelist(self.cfg.voice_role,locale=self.cfg.target_language_code),
                    rate=rate,
                    volume=self.cfg.volume,
                    pitch=self.cfg.pitch
                )
            ))
            config.logger.debug(f'edge-tts配音，未音频加速，未视频慢速，未强制对齐，已删字幕间静音，使用单独文本配音')
            if not self.cfg.target_wav.endswith('.mp3'):
                tools.runffmpeg(['-y', '-i', tmp_name, '-b:a', '128k', self.cfg.target_wav])
            return
        
        # 如果配音文件是txt，则转为单条字幕形式，以便统一处理
        if self.cfg.target_sub.endswith('.txt'):
            text = Path(self.cfg.target_sub).read_text(encoding='utf-8').strip()
            text = re.sub(r"(\s*?\r?\n\s*?){2,}", "\n", text,flags=re.I | re.S)
            text = re.sub(r"(\s*?\r?\n\s*?)", "\n", text,flags=re.I | re.S)
            text_list=re.findall(r'.*?(?:[?，。？！,?!\n]|\. )',text)
            text_str=""
            subs=[]
            for i,it in enumerate(text_list):
                if not it.strip():
                    continue
                text_str+=it
                if len(text_str)>=100:
                    subs.append({
                        "line": i+1,
                        "start_time": i*1000,
                        "end_time": i*1000+1000,
                        "startraw": f"00:00:00,000",
                        "endraw": "00:00:01,000",
                        "text": text_str
                    })
                    text_str=''
            if text_str:
                subs.append({
                        "line": len(subs)+1,
                        "start_time": len(subs)*1000,
                        "end_time": len(subs)*1000+1000,
                        "startraw": f"00:00:00,000",
                        "endraw": "00:00:01,000",
                        "text": text_str
                })
        elif self.subs:
            subs=self.subs
        else:
            subs = tools.get_subtitle_from_srt(self.cfg.target_sub)

        # 取出每一条字幕，行号\n开始时间 --> 结束时间\n内容
        for i, it in enumerate(subs):
            if it['end_time'] <= it['start_time']:
                continue
            try:
                spec_role = config.dubbing_role.get(int(it.get('line', 1))) if self.is_multi_role else None
            except (ValueError,LookupError):
                spec_role = None
            voice_role = spec_role if spec_role else self.cfg.voice_role

            tmp_dict = {
                "line": it['line'],
                "text": it['text'],
                "role": voice_role,
                "start_time": it['start_time'],
                "end_time": it['end_time'],
                "rate": rate,
                "volume": self.cfg.volume,
                "pitch": self.cfg.pitch,
                "tts_type": int(self.cfg.tts_type),
                "filename": f"{self.cfg.cache_folder}/dubb-{i}.wav"}
            queue_tts.append(tmp_dict)

        self.queue_tts = queue_tts

        if not self.queue_tts or len(self.queue_tts) < 1:
            raise RuntimeError(f'Queue tts length is 0')
        # 具体配音操作
        tts.run(
            queue_tts=copy.deepcopy(self.queue_tts),
            language=self.cfg.target_language_code,
            uuid=self.uuid,
            tts_type=self.cfg.tts_type
        )
        # 如果需要单独保存每条字幕的配音
        if config.settings.get('save_segment_audio', False):
            outname = self.cfg.target_dir + f'/segment_audio_{self.cfg.noextname}'
            Path(outname).mkdir(parents=True, exist_ok=True)
            for it in self.queue_tts:
                if Path(it['filename']).exists():
                    text = re.sub(r'["\'*?\\/\|:<>\r\n\t]+', '', it['text'],flags=re.I | re.S)
                    name = f'{outname}/{it["start_time"]}-{text[:60]}.wav'
                    try:
                        shutil.copy2(it['filename'], name)
                    except shutil.SameFileError:
                        pass

    
    
    # 音频加速对齐字幕
    def align(self) -> None:
        # txt配音并且是 edgetts，已结束
        if self.ignore_align:
            return
        # 只有一行
        if len(self.queue_tts) == 1:
            if self.cfg.tts_type != tts.EDGE_TTS:
                tools.runffmpeg(['-y', '-i', self.queue_tts[0]['filename'], '-b:a', '128k', self.cfg.target_wav])
            return

        if self.cfg.voice_autorate:
            self._signal(text=tr("Sound speed alignment stage"))
        try:
            target_path = Path(self.cfg.target_wav)
            # 目前文件夹内存在同名，则添加时间后缀
            if target_path.is_file() and target_path.stat().st_size > 0:
                self.cfg.target_wav = self.cfg.target_wav[:-4] + f'-{datetime.datetime.now().strftime("%Y%m%d-%H%M%S")}{target_path.suffix}'
            # txt 配音 不音频加速，移除字幕间静音即有空隙也忽略，直接配音文件相连
            # 单独配音功能不强制对齐
            rate_inst = SpeedRate(
                queue_tts=self.queue_tts,
                uuid=self.uuid,
                shoud_audiorate=self.cfg.voice_autorate if not self.cfg.target_sub.endswith('.txt') else False,# txt 配音禁止自动加速，需要移除字幕静音，即直接相连即可
                raw_total_time=self.queue_tts[-1]['end_time'],
                target_audio=self.cfg.target_wav,
                cache_folder=self.cfg.cache_folder,
                remove_silent_mid=self.cfg.remove_silent_mid if not self.cfg.target_sub.endswith('.txt') else True, # 是否移除字幕间空隙 仅在未自动加速时才起作用,txt配音时移除，即直接音频文件相连
                align_sub_audio=False # 不对齐字幕 仅在未自动加速时才起作用
            )
            self.queue_tts = rate_inst.run()


            volume = self.cfg.volume.strip()

            if volume != '+0%':
                try:
                    volume = 1 + float(volume) / 100
                    tmp_name = self.cfg.cache_folder + f'/volume-{volume}-{Path(self.cfg.target_wav).name}'
                    tools.runffmpeg(['-y', '-i', self.cfg.target_wav, '-af', f"volume={volume}", tmp_name])
                except Exception:
                    pass
        except Exception as e:
            self.hasend = True
            raise

    def task_done(self):
        if self._exit():
            return
        self.hasend = True
        self.precent = 100
        if Path(self.cfg.target_wav).is_file():
            # 移除末尾静音
            tools.remove_silence_from_end(self.cfg.target_wav, is_start=False)
            self._signal(text=f"{self.cfg.name}", type='succeed')
        try:
            if self.cfg.shound_del_name:
                Path(self.cfg.shound_del_name).unlink(missing_ok=True)
        except OSError:
            pass
        tools.send_notification(tr('Succeed'), f"{self.cfg.basename}")    

    def _exit(self):
        if config.exit_soft:
            self.hasend=True
            return True
        return False

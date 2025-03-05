import copy
import json
import re
import shutil
import time
from pathlib import Path
from typing import Dict

from videotrans.configure import config


from videotrans.task._base import BaseTask
from videotrans.task._rate import SpeedRate
from videotrans import tts
from videotrans.util import tools

"""
仅字幕翻译
"""


class DubbingSrt(BaseTask):
    """
    obj={
    name:原始音视频完整路径和名字
    dirname
    basename
    noextname
    ext
    target_dir
    uuid
    }

    cfg={
        translate_type
        text_list
        target_language
        inst
        uuid
        source_code
    }
    """

    def __init__(self, cfg: Dict = None, obj: Dict = None):
        super().__init__(cfg, obj)
        self.shoud_dubbing = True
        if 'target_dir' not in self.cfg or not self.cfg['target_dir']:
            self.cfg['target_dir'] = config.HOME_DIR + f"/tts"
        # 存放目标文件夹
        if not Path(self.cfg['target_dir']).exists():
            Path(self.cfg['target_dir']).mkdir(parents=True, exist_ok=True)
        # 字幕文件
        self.cfg['target_sub'] = self.cfg['name']
        # 配音文件
        self.cfg['target_wav'] = self.cfg['target_dir'] + f'/{self.cfg["noextname"]}.{self.cfg["out_ext"]}'

        Path(self.cfg["cache_folder"]).mkdir(parents=True, exist_ok=True)
        self._signal(text='字幕配音处理中' if config.defaulelang == 'zh' else ' Dubbing from subtitles ')
        self.rename=self.cfg.get('rename',False)

    def prepare(self):
        if self._exit():
            return

    def recogn(self):
        pass

    def trans(self):
        pass

    def dubbing(self):
        try:
            self._signal(text=Path(self.cfg['target_sub']).read_text(encoding='utf-8'), type="replace")
            self._tts()
        except Exception as e:
            self.hasend = True
            tools.send_notification(str(e), f'{self.cfg["basename"]}')
            raise

    # 配音预处理，去掉无效字符，整理开始时间
    def _tts(self) -> None:
        queue_tts = []
        # 获取字幕
        try:
            rate = int(str(self.cfg['voice_rate']).replace('%', ''))
        except:
            rate=0
        if rate >= 0:
            rate = f"+{rate}%"
        else:
            rate = f"{rate}%"
        
        if self.cfg['target_sub'].endswith('.txt') and self.cfg['tts_type']==tts.EDGE_TTS:
            from edge_tts import Communicate
            import asyncio
            pro=self._set_proxy(type='set')
            async def _async_dubb():
                communicate_task = Communicate(
                    text=Path(self.cfg['target_sub']).read_text(encoding='utf-8'), 
                    voice=self.cfg['voice_role'], 
                    rate=rate, 
                    volume=self.cfg['volume'],
                    proxy=pro if pro else None,
                    pitch=self.cfg['pitch']
                )
                tmp_name=self.cfg['target_wav'] if self.cfg["target_wav"].endswith('.mp3') else f"{self.cfg['cache_folder']}/{self.cfg['noextname']}-edgetts-txt-{time.time()}.mp3"
                await communicate_task.save(tmp_name)
                
                if not self.cfg["target_wav"].endswith('.mp3'):
                    tools.runffmpeg(['-y','-i',tmp_name,'-b:a','192k',self.cfg['target_wav']])
                
            asyncio.run(_async_dubb())
            return

        try:
            subs = tools.get_subtitle_from_srt(self.cfg['target_sub'])
        except Exception as e:
            raise
        # 取出每一条字幕，行号\n开始时间 --> 结束时间\n内容
        for i, it in enumerate(subs):
            if it['end_time'] <= it['start_time']:
                continue
            voice_role = self.cfg['voice_role']
            # 要保存到的文件
            tmp_dict= {"text": it['text'], "role": voice_role, "start_time": it['start_time'],
                       "end_time": it['end_time'], "rate": rate, "startraw": it['startraw'], "endraw": it['endraw'],
                       "volume": self.cfg['volume'],
                       "pitch": self.cfg['pitch'],
                       "tts_type": int(self.cfg['tts_type']),
                       "filename": config.TEMP_DIR + f"/dubbing_cache/{it['start_time']}-{it['end_time']}-{time.time()}-{len(it['text'])}-{i}.mp3"}
            queue_tts.append(tmp_dict)
        Path(config.TEMP_DIR + "/dubbing_cache").mkdir(parents=True,exist_ok=True)
        self.queue_tts = queue_tts
        if not self.queue_tts or len(self.queue_tts) < 1:
            raise Exception(f'Queue tts length is 0')
        # 具体配音操作
        tts.run(
            queue_tts=copy.deepcopy(self.queue_tts),
            language=self.cfg['target_language_code'],
            uuid=self.uuid
        )
        if config.settings.get('save_segment_audio',False):
            outname=self.cfg['target_dir']+f'/segment_audio_{self.cfg["noextname"]}'
            print(f'{outname=}')
            Path(outname).mkdir(parents=True, exist_ok=True)
            for it in self.queue_tts:
                text=re.sub(r'["\'*?\\/\|:<>\r\n\t]+','',it['text'])
                name= f'{outname}/{it["start_time"]}-{text[:60]}.mp3'
                shutil.copy2(it['filename'],name)

    def align(self) -> None:
        if self.cfg['target_sub'].endswith('.txt') and self.cfg['tts_type']==tts.EDGE_TTS:
            return
        if self.cfg['voice_autorate']:
            self._signal(text='声画变速对齐阶段' if config.defaulelang == 'zh' else 'Sound & video speed alignment stage')
        try:
            target_path=Path(self.cfg['target_wav'])
            if target_path.is_file() and target_path.stat().st_size > 0:
                self.cfg['target_wav']=self.cfg['target_wav'][:-4]+f'-{tools.get_current_time_as_yymmddhhmmss()}{target_path.suffix}'
            rate_inst = SpeedRate(
                queue_tts=self.queue_tts,
                uuid=self.uuid,
                shoud_audiorate=self.cfg['voice_autorate'] and int(float(config.settings.get('audio_rate',1))) > 1,
                raw_total_time=self.queue_tts[-1]['end_time'],
                noextname=self.cfg['noextname'],
                target_audio=self.cfg['target_wav'],
                cache_folder=self.cfg['cache_folder']
            )
            volume=self.cfg['volume'].strip()

            if volume !='+0%':
                try:
                    volume=1+float(volume)/100
                    tmp_name=self.cfg['cache_folder']+f'/volume-{volume}-{Path(self.cfg["target_wav"]).name}'
                    tools.runffmpeg(['-y','-i',self.cfg['target_wav'],'-af',f"volume={volume}",tmp_name])
                except:
                    pass
            self.queue_tts = rate_inst.run()
            # 更新字幕
            if config.settings['force_edit_srt']:
                srt = ""
                for (idx, it) in enumerate(self.queue_tts):
                    it['startraw'] = tools.ms_to_time_string(ms=it['start_time'])
                    it['endraw'] = tools.ms_to_time_string(ms=it['end_time'])
                    srt += f"{idx + 1}\n{it['startraw']} --> {it['endraw']}\n{it['text']}\n\n"
                # 字幕保存到目标文件夹
                with Path(self.cfg['target_sub'] + "-AlignToAudio.srt").open('w',encoding="utf-8") as f:
                    f.write(srt.strip())
                    f.flush()
        except Exception as e:
            self.hasend = True
            tools.send_notification(str(e), f'{self.cfg["basename"]}')
            raise

    def task_done(self):
        if self._exit():
            return
        self.hasend = True
        self.precent = 100
        if Path(self.cfg['target_wav']).is_file():
            tools.remove_silence_from_end(self.cfg['target_wav'],is_start=False)
            self._signal(text=f"{self.cfg['name']}", type='succeed')
            tools.send_notification(config.transobj['Succeed'], f"{self.cfg['basename']}")
        if 'shound_del_name' in self.cfg:
            Path(self.cfg['shound_del_name']).unlink(missing_ok=True)

    def _exit(self):
        if config.exit_soft or config.box_tts!='ing':
            return True
        return False

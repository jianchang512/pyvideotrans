import copy
import time
from pathlib import Path
from typing import Dict

from videotrans.configure import config
from videotrans.configure._except import LogExcept
from videotrans.task._base import BaseTask
from videotrans.task._rate import SpeedRate
from videotrans.tts import run
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

    config_params={
        translate_type
        text_list
        target_language
        inst
        uuid
        task_type
        source_code
    }
    """

    def __init__(self, config_params: Dict = None, obj: Dict = None):
        super().__init__(config_params, obj)
        self.shoud_dubbing = True

        # 存放目标文件夹
        if not Path(self.config_params['target_dir']).exists():
            Path(self.config_params['target_dir']).mkdir(parents=True, exist_ok=True)
        # 字幕文件
        self.config_params['target_sub'] = self.config_params['name']
        # 配音文件
        self.config_params['target_wav'] = self.config_params[
                                               'target_dir'] + f'/{self.config_params["noextname"]}.{self.config_params["out_ext"]}'

        Path(self.config_params["cache_folder"]).mkdir(parents=True, exist_ok=True)
        self._signal(text='字幕配音处理中' if config.defaulelang == 'zh' else ' Dubbing from subtitles ')

    def prepare(self):
        if self._exit():
            return

    def recogn(self):
        pass

    def trans(self):
        pass

    def dubbing(self):
        try:
            self._signal(text=Path(self.config_params['target_sub']).read_text(encoding='utf-8'), type="replace")
            self._tts()
        except Exception as e:
            self.hasend = True
            tools.send_notification(str(e), f'{self.config_params["basename"]}')
            raise

    # 配音预处理，去掉无效字符，整理开始时间
    def _tts(self) -> None:
        queue_tts = []
        # 获取字幕
        try:
            subs = tools.get_subtitle_from_srt(self.config_params['target_sub'])
            if len(subs) < 1:
                raise Exception(f"字幕格式不正确，请打开查看:{self.config_params['target_sub']}")
        except Exception as e:
            raise LogExcept(e)

        rate = int(str(self.config_params['voice_rate']).replace('%', ''))
        if rate >= 0:
            rate = f"+{rate}%"
        else:
            rate = f"{rate}%"
        # 取出每一条字幕，行号\n开始时间 --> 结束时间\n内容
        for i, it in enumerate(subs):
            if it['end_time'] <= it['start_time']:
                continue
            # 判断是否存在单独设置的行角色，如果不存在则使用全局
            voice_role = self.config_params['voice_role']
            # 要保存到的文件
            filename = self.config_params['cache_folder'] + "/" + tools.get_md5(
                f'{i}-{voice_role}-{time.time()}') + ".mp3"
            queue_tts.append({
                "text": it['text'],
                "role": voice_role,
                "start_time": it['start_time'],
                "end_time": it['end_time'],
                "rate": rate,
                "startraw": it['startraw'],
                "endraw": it['endraw'],
                "volume": self.config_params['volume'],
                "pitch": self.config_params['pitch'],
                "tts_type": self.config_params['tts_type'],
                "filename": filename})
        self.queue_tts = queue_tts
        if not self.queue_tts or len(self.queue_tts) < 1:
            raise Exception(f'Queue tts length is 0')
        # 具体配音操作
        run(
            queue_tts=copy.deepcopy(self.queue_tts),
            language=self.config_params['target_language_code'],
            uuid=self.uuid
        )

    def align(self) -> None:
        if self.config_params['voice_autorate']:
            self._signal(text='声画变速对齐阶段' if config.defaulelang == 'zh' else 'Sound & video speed alignment stage')
        try:
            rate_inst = SpeedRate(
                queue_tts=self.queue_tts,
                uuid=self.uuid,
                shoud_audiorate=self.config_params['voice_autorate'] and int(config.settings['audio_rate']) > 1,
                shoud_videorate=False,
                novoice_mp4=None,
                noextname=self.config_params['noextname'],
                target_audio=self.config_params['target_wav'],
                cache_folder=self.config_params['cache_folder']
            )
            self.queue_tts = rate_inst.run()
            # 更新字幕
            if config.settings['force_edit_srt']:
                srt = ""
                for (idx, it) in enumerate(self.queue_tts):
                    it['startraw'] = tools.ms_to_time_string(ms=it['start_time'])
                    it['endraw'] = tools.ms_to_time_string(ms=it['end_time'])
                    srt += f"{idx + 1}\n{it['startraw']} --> {it['endraw']}\n{it['text']}\n\n"
                # 字幕保存到目标文件夹
                Path(self.config_params['target_sub'] + "-AlignToAudio.srt").write_text(srt.strip(), encoding="utf-8",
                                                                                        errors="ignore")
        except Exception as e:
            self.hasend = True
            tools.send_notification(str(e), f'{self.config_params["basename"]}')
            raise

    def task_done(self):
        self.hasend = True
        self.precent = 100
        if Path(self.config_params['target_wav']).is_file():
            tools.remove_silence_from_end(self.config_params['target_wav'])
            self._signal(text=f"{self.config_params['name']}", type='succeed')
            tools.send_notification("Succeed", f"{self.config_params['basename']}")
        if 'shound_del_name' in self.config_params:
            Path(self.config_params['shound_del_name']).unlink(missing_ok=True)

    def _exit(self):
        if config.exit_soft or not config.box_trans:
            return True
        return False

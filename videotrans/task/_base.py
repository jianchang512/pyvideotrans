import re
import shutil
from pathlib import Path
from typing import Dict

from videotrans.configure import config
from videotrans.configure._base import BaseCon
from videotrans.util import tools


class BaseTask(BaseCon):

    def __init__(self, config_params: Dict = None, obj: Dict = None):
        # 任务id
        super().__init__()
        # 配置信息
        # 视频信息
        """
        result={
            "video_fps":0,
            "video_codec_name":"h264",
            "audio_codec_name":"aac",
            "width":0,
            "height":0,
            "time":0
        }
        """
        self.config_params = {
            "video_info": None,
            "h264": None,

            "cache_folder": None,
            "target_dir": None,

            "detect_language": None,
            'subtitle_language': None,

            "source_language_code": None,
            "target_language_code": None,

            "source_sub": None,
            "target_sub": None,

            "source_wav": None,
            "target_wav": None,

            "novoice_mp4": None,
            "targetdir_mp4": None,

            "instrument": None,
            "vocal": None,

            "shibie_audio": None,

            'background_music': None,

            'app_mode':"biaozhun",

            "subtitle_type":0,
            "append_video":False,
            'only_video':False
        }
        self.config_params.update(config_params)
        if obj:
            self.config_params.update(obj)
        # 名字规范化处理后，应该删除的
        self.shound_del_name=None
        if "uuid" in self.config_params and self.config_params['uuid']:
            self.uuid = self.config_params['uuid']

        # 进度
        self.precent = 1
        self.status_text = config.transobj['ing']
        # 存储处理好待配音信息
        self.queue_tts = []
        # 本次任务结束标识
        self.hasend = False
        # 264/265
        self.video_codec = int(config.settings['video_codec'])

        # 预处理，prepare 全部需要
        self.shound_del = False
        # 是否需要语音识别
        self.shoud_recogn = False
        # 是否需要字幕翻译
        self.shoud_trans = False
        # 是否需要配音
        self.shoud_dubbing = False
        # 是否需要人声分离
        self.shoud_separate = False
        # 是否需要嵌入配音或字幕
        self.shoud_hebing = False
        # 最后一步hebing move_emd 全部需要


    # 预先处理，例如从视频中拆分音频、人声背景分离、转码等
    def prepare(self):
        pass


    # 语音识别创建原始语言字幕
    def recogn(self):
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
        if not tools.vail_file(file):
            return False
        try:
            tools.get_subtitle_from_srt(file)
        except Exception:
            Path(file).unlink(missing_ok=True)
            return False
        return True

    # 删掉尺寸为0的无效文件
    def _unlink_size0(self, file):
        p = Path(file)
        if p.exists() and p.stat().st_size == 0:
            p.unlink(missing_ok=True)

    # 保存字幕文件 到目标文件夹
    def _save_srt_target(self, srtstr, file):
        # 是字幕列表形式，重新组装
        try:
            tools.save_srt(srtstr, file)
        except Exception as e:
            raise
        self._signal(text=Path(file).read_text(encoding='utf-8'), type='replace_subtitle')
        return True

    # 完整流程判断是否需退出，子功能需重写
    def _exit(self):
        if config.exit_soft or config.current_status != 'ing':
            return True
        return False

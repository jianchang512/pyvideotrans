from pathlib import Path
from typing import Dict

from videotrans.configure import config
from videotrans.util import tools


class BaseTask:

    def __init__(self,config_params:Dict=None,obj:Dict=None):
        # 配置信息
        self.config_params = config_params
        # 任务id
        self.uuid=None
        # 进度
        self.precent = 1
        self.status_text = config.transobj['ing']
        # 存储处理好待配音信息
        self.queue_tts = []
        # 本次任务结束标识
        self.hasend = False
        # 264/265
        self.video_codec = int(config.settings['video_codec'])

        # 是否需要语音识别
        self.shoud_recogn = False
        # 是否需要字幕翻译
        self.shoud_trans = False
        # 是否需要配音
        self.shoud_dubbing = False
        # 是否需要嵌入配音或字幕
        self.shoud_hebing = False
        # 是否需要人声分离
        self.shoud_separate = False

        # 初始化后的信息
        self.init = {
            'background_music': None,
            'detect_language': None,
            'subtitle_language': None
        }

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
        self.init['video_info'] = {}
        # 是否是标准264/265，如果是True，则无需重新编码，直接copy
        self.init['h264'] = False
        # 缓存目录
        self.init['cache_folder'] = None

        # 原始语言代码
        self.init['source_language_code'] = None
        # 目标语言代码
        self.init['target_language_code'] = None
        # 字幕检测语言代码
        self.init['detect_language'] = None

        # 拆分后的无声mp4
        self.init['novoice_mp4'] = None
        # 原语言字幕文件路径
        self.init['source_sub'] = None
        # 目标语言字幕文件路径
        self.init['target_sub'] = None
        # 原音频文件路径
        self.init['source_wav'] = None
        # 已配音完毕目标语言音频文件路径
        self.init['target_wav'] = None
        # 最终目标生成结果mp4文件路径
        self.init['targetdir_mp4'] = None
        # 分离出的背景音频文件路径
        self.init['instrument'] = None
        # 分离出的人声文件路径
        self.init['vocal'] = None
        # 用于语音识别的音频文件路径
        self.init['shibie_audio'] = None


        # 存在视频路径信息
        if obj:
            self.init.update({
                "name": obj['name'],
                "dirname": obj['dirname'],
                "basename": obj['basename'],
                "noextname": obj['noextname'],
                "ext": obj['ext'],
                "target_dir": obj['target_dir'],
                "uuid": obj['uuid']
            })
            self.uuid = obj['uuid']

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
    def hebing(self):
        pass
    # 删除临时文件，移动或复制，发送成功消息
    def move_at_end(self):
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
        tools.save_srt(srtstr, file)
        self._signal(text=Path(file).read_text(encoding='utf-8'), type='replace_subtitle')
        return True

    def _signal(self,text="",type="logs",nologs=False,uuid=None):
        tools.set_process(text=text,type=type,nologs=nologs,uuid=self.uuid)

    # 完整流程判断是否需退出，子功能需重写
    def _exit(self):
        if config.exit_soft or config.current_status!='ing':
            return True
        return False
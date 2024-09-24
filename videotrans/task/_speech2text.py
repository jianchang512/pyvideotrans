import time
from pathlib import Path
from typing import Dict

from videotrans.configure import config


from videotrans.recognition import run
from videotrans.task._base import BaseTask
from videotrans.util import tools

"""
仅语音识别
"""


class SpeechToText(BaseTask):
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
    source_language
    recogn_type 识别模式索引
    split_type 整体识别/均等分割
    model_name 模型名字
    cuda 是否启用cuda
    }
    """

    def __init__(self, config_params: Dict = None, obj: Dict = None):
        super().__init__(config_params, obj)
        self.shoud_recogn = True
        # 存放目标文件夹
        if 'target_dir' not in self.config_params or not self.config_params['target_dir']:
            self.config_params['target_dir'] = config.HOME_DIR + f"/recogn"
        if not Path(self.config_params['target_dir']).exists():
            Path(self.config_params['target_dir']).mkdir(parents=True, exist_ok=True)
        # 生成目标字幕文件
        self.config_params['target_sub'] = self.config_params['target_dir'] + '/' + self.config_params[
            'noextname'] + '.srt'
        # 临时文件夹
        self.config_params['cache_folder'] = config.TEMP_HOME + f'/speech2text'
        if not Path(self.config_params['cache_folder']).exists():
            Path(self.config_params['cache_folder']).mkdir(parents=True, exist_ok=True)
        self.config_params['shibie_audio'] = self.config_params[
                                                 'cache_folder'] + f'/{self.config_params["noextname"]}-{time.time()}.wav'
        self._signal(text='语音识别文字处理中' if config.defaulelang == 'zh' else 'Speech Recognition to Word Processing')

    def prepare(self):
        if self._exit():
            return
        tools.conver_to_16k(self.config_params['name'], self.config_params['shibie_audio'])

    def recogn(self):
        if self._exit():
            return
        while 1:
            if Path(self.config_params['shibie_audio']).exists():
                break
            time.sleep(1)
        try:

            raw_subtitles = run(
                # faster-whisper openai-whisper googlespeech
                recogn_type=self.config_params['recogn_type'],
                # 整体 预先 均等
                split_type=self.config_params['split_type'],
                uuid=self.uuid,
                # 模型名
                model_name=self.config_params['model_name'],
                # 识别音频
                audio_file=self.config_params['shibie_audio'],
                detect_language=self.config_params['detect_language'],
                cache_folder=self.config_params['cache_folder'],
                is_cuda=self.config_params['is_cuda'],
                inst=self)
            Path(self.config_params['shibie_audio']).unlink(missing_ok=True)
        except Exception as e:
            msg = f'{str(e)}{str(e.args)}'
            tools.send_notification(msg, f'{self.config_params["basename"]}')
            self._signal(text=f"{msg}", type='error')
            raise
        else:
            if self._exit():
                return
            if not raw_subtitles or len(raw_subtitles) < 1:
                raise Exception(
                    self.config_params['basename'] + config.transobj['recogn result is empty'].replace('{lang}',
                                                                                                       self.config_params[
                                                                                                           'detect_language']))
            self._save_srt_target(raw_subtitles, self.config_params['target_sub'])
            self._signal(text=f"{self.config_params['name']}", type='succeed')
            tools.send_notification("Succeed", f"{self.config_params['basename']}")

    def task_done(self):
        if 'shound_del_name' in self.config_params:
            Path(self.config_params['shound_del_name']).unlink(missing_ok=True)

    def _exit(self):
        if config.exit_soft or not config.box_recogn:
            return True
        return False

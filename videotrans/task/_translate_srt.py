from pathlib import Path
from typing import Dict

from videotrans.configure import config
from videotrans.configure._except import LogExcept
from videotrans.task._base import BaseTask
from videotrans.translator import run
from videotrans.util import tools

"""
仅字幕翻译
"""


class TranslateSrt(BaseTask):
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
        self.shoud_trans = True
        # 存放目标文件夹
        self.config_params['target_dir'] = config.HOME_DIR + f"/translate"
        if not Path(self.config_params['target_dir']).exists():
            Path(self.config_params['target_dir']).mkdir(parents=True, exist_ok=True)
        # 生成目标字幕文件
        self.config_params['target_sub'] = self.config_params['target_dir'] + '/' + self.config_params[
            'noextname'] + '.srt'
        self.config_params['source_sub'] = self.config_params['name']
        self._signal(text='字幕翻译处理中' if config.defaulelang == 'zh' else ' Transation subtitles ')

    def prepare(self):
        if self._exit():
            return

    def recogn(self):
        pass

    def trans(self):
        if self._exit():
            return
        try:
            raw_subtitles = run(
                translate_type=self.config_params['translate_type'],
                text_list=tools.get_subtitle_from_srt(self.config_params['source_sub']),
                target_language_name=self.config_params['target_language'],
                uuid=self.uuid,
                task_type=self.config_params['task_type'],
                source_code=self.config_params['source_code'])
            if not raw_subtitles or len(raw_subtitles) < 1:
                raise LogExcept(
                    self.config_params['basename'] + config.transobj['recogn result is empty'].replace('{lang}',
                                                                                                       self.config_params[
                                                                                                           'detect_language']))
            tools.save_srt(raw_subtitles, self.config_params['target_sub'])
            self._signal(text=Path(self.config_params['target_sub']).read_text(encoding='utf-8'), type='replace')
            # self._signal(text=f"{self.config_params['name']}", type='succeed')
        except Exception as e:
            msg = f'{str(e)}{str(e.args)}'
            tools.send_notification(msg, f'{self.config_params["basename"]}')
            self._signal(text=f"{msg}", type='error')
            raise

    def task_done(self):
        self.hasend = True
        self.precent = 100
        if Path(self.config_params['target_sub']).is_file():
            self._signal(text=f"{self.config_params['name']}", type='succeed')
            tools.send_notification("Succeed", f"{self.config_params['basename']}")
        if 'shound_del_name' in self.config_params:
            Path(self.config_params['shound_del_name']).unlink(missing_ok=True)

    def _exit(self):
        if config.exit_soft or not config.box_trans:
            return True
        return False

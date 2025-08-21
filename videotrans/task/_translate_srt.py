import copy
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from videotrans.configure import config
from videotrans.task._base import BaseTask
from videotrans.translator import run
from videotrans.util import tools

"""
仅字幕翻译
"""


@dataclass
class TranslateSrt(BaseTask):
    # 输出格式，例如单语字幕 双语字幕等。
    out_format: int = field(init=False)
    # 在这个子类中，shoud_trans 总是 True，我们直接在定义中声明这一点。
    shoud_trans: bool = field(default=True, init=False)

    def __post_init__(self):
        # 这会确保 self.cfg 被正确地合并(cfg+obj)并且 self.uuid 被设置。
        super().__post_init__()

        # 存放目标文件夹
        if 'target_dir' not in self.cfg or not self.cfg['target_dir']:
            self.cfg['target_dir'] = config.HOME_DIR + f"/translate"
        if not Path(self.cfg['target_dir']).exists():
            Path(self.cfg['target_dir']).mkdir(parents=True, exist_ok=True)
        self.out_format = int(self.cfg.get('out_format', 0))
        # 生成目标字幕文件
        self.cfg['target_sub'] = self.cfg['target_dir'] + '/' + self.cfg[
            'noextname'] + f'.{self.cfg["target_code"]}.srt'
        self.cfg['source_sub'] = self.cfg['name']
        if self.cfg['name'] == self.cfg['target_sub']:
            shutil.copy2(self.cfg['source_sub'], f"{self.cfg['source_sub']}-Raw-Subtitle.srt")
        self._signal(text='字幕翻译处理中' if config.defaulelang == 'zh' else ' Transation subtitles ')



    def trans(self):
        if self._exit():
            return
        try:
            source_sub_list = tools.get_subtitle_from_srt(self.cfg['source_sub'])
            raw_subtitles = run(
                translate_type=self.cfg['translate_type'],
                text_list=copy.deepcopy(source_sub_list),
                uuid=self.uuid,
                source_code=self.cfg['source_code'],
                target_code=self.cfg['target_code'],
            )

            if self._exit():
                return
            if not raw_subtitles or len(raw_subtitles) < 1:
                raise RuntimeError('字幕翻译结果为空' if config.defaulelang == 'zh' else 'Translation subtitles result is empty')
            raw_subtitles = self._check_target_sub(source_sub_list, raw_subtitles)
            if self.out_format == 0:
                self._save_srt_target(raw_subtitles, self.cfg['target_sub'])
                self._signal(text=Path(self.cfg['target_sub']).read_text(encoding='utf-8'), type='replace')
            else:
                target_length = len(raw_subtitles)
                srt_string = ""
                for i, it in enumerate(source_sub_list):
                    if self.out_format == 1:
                        tmp_text = f"{raw_subtitles[i]['text'].strip()}\n" if i < target_length else ''
                        tmp_text += it["text"].strip()
                    else:
                        tmp_text = f"{raw_subtitles[i]['text'].strip()}" if i < target_length else ''
                        tmp_text = f"{it['text'].strip()}\n{tmp_text}"
                    srt_string += f"{it['line']}\n{it['time']}\n{tmp_text}\n\n"
                self.cfg['target_sub'] = self.cfg['target_sub'][:-4] + f'-{self.out_format}.srt'
                with Path(self.cfg['target_sub']).open('w', encoding='utf-8') as f:
                    f.write(srt_string)
                self._signal(text=srt_string, type='replace')
        except Exception as e:
            tools.send_notification(str(e), f'{self.cfg["basename"]}')
            raise

    def task_done(self):
        if self._exit():
            return
        self.hasend = True
        self.precent = 100
        if Path(self.cfg['target_sub']).is_file():
            self._signal(text=f"{self.cfg['name']}", type='succeed')
            tools.send_notification(config.transobj['Succeed'], f"{self.cfg['basename']}")
        try:
            if 'shound_del_name' in self.cfg:
                Path(self.cfg['shound_del_name']).unlink(missing_ok=True)
        except:
            pass
    def _exit(self):
        if config.exit_soft or config.box_trans != 'ing':
            return True
        return False

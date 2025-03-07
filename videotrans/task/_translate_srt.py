import copy
from pathlib import Path
from typing import Dict
import datetime
from videotrans.configure import config

from videotrans.task._base import BaseTask
from videotrans.translator import run
from videotrans.util import tools
import shutil
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
        self.shoud_trans = True
        # 存放目标文件夹
        if 'target_dir' not in self.cfg or not self.cfg['target_dir']:
            self.cfg['target_dir'] = config.HOME_DIR + f"/translate"
        if not Path(self.cfg['target_dir']).exists():
            Path(self.cfg['target_dir']).mkdir(parents=True, exist_ok=True)
        self.out_format=int(cfg.get('out_format',0))
        # 生成目标字幕文件
        self.cfg['target_sub'] = self.cfg['target_dir'] + '/' + self.cfg[
            'noextname'] + f'.{self.cfg["target_code"]}.srt'
        self.cfg['source_sub'] = self.cfg['name']
        if self.cfg['name']==self.cfg['target_sub']:
            shutil.copy2(self.cfg['source_sub'],f"{self.cfg['source_sub']}-Raw-Subtitle.srt")
        self._signal(text='字幕翻译处理中' if config.defaulelang == 'zh' else ' Transation subtitles ')
        self.rename=cfg.get('rename',False)


    def prepare(self):
        if self._exit():
            return

    def recogn(self):
        pass

    def trans(self):
        if self._exit():
            return
        try:
            source_sub_list=tools.get_subtitle_from_srt(self.cfg['source_sub'])
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
                raise Exception('Is emtpy '+self.cfg['basename'])
            raw_subtitles=self._check_target_sub(source_sub_list,raw_subtitles)
            if self.out_format==0:
                tools.save_srt(raw_subtitles, self.cfg['target_sub'])
                self._signal(text=Path(self.cfg['target_sub']).read_text(encoding='utf-8'), type='replace')
            else:
                target_length = len(raw_subtitles)
                srt_string = ""
                for i, it in enumerate(source_sub_list):
                    if self.out_format==1:
                        tmp_text= f"{raw_subtitles[i]['text'].strip()}\n" if i<target_length else ''
                        tmp_text+=it["text"].strip()
                    else:
                        tmp_text= f"{raw_subtitles[i]['text'].strip()}" if i<target_length else ''
                        tmp_text=f"{it['text'].strip()}\n{tmp_text}"
                    srt_string += f"{it['line']}\n{it['time']}\n{tmp_text}\n\n"
                self.cfg['target_sub']=self.cfg['target_sub'][:-4]+f'-{self.out_format}.srt'
                with Path(self.cfg['target_sub']).open('w', encoding='utf-8') as f:
                    f.write(srt_string)
                print(f"{self.cfg['target_sub']=}")
                self._signal(text=srt_string, type='replace')
        except Exception as e:
            msg = f'{str(e)}{str(e.args)}'
            tools.send_notification(msg, f'{self.cfg["basename"]}')
            self._signal(text=f"{msg}", type='error')
            raise

    def _check_target_sub(self,source_srt_list,target_srt_list):
        for i,it in enumerate(source_srt_list):
            if i>=len(target_srt_list) or target_srt_list[i]['time']!=it['time']:
                # 在 target_srt_list 的 索引 i 位置插入一个dict
                tmp=copy.deepcopy(it)
                tmp['text']='  '
                if i>=len(target_srt_list):
                    target_srt_list.append(tmp)                
                else:
                    target_srt_list.insert(i,tmp)
            else:
                target_srt_list[i]['line']=it['line']
        return target_srt_list


    def task_done(self):
        if self._exit():
            return
        self.hasend = True
        self.precent = 100
        if Path(self.cfg['target_sub']).is_file():
            self._signal(text=f"{self.cfg['name']}", type='succeed')
            tools.send_notification(config.transobj['Succeed'], f"{self.cfg['basename']}")
        if 'shound_del_name' in self.cfg:
            Path(self.cfg['shound_del_name']).unlink(missing_ok=True)

    def _exit(self):
        if config.exit_soft or config.box_trans!='ing':
            return True
        return False

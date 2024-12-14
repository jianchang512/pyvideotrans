import time
from pathlib import Path
from typing import Dict

from videotrans.configure import config


from videotrans.recognition import run,Faster_Whisper_XXL
from videotrans.task._base import BaseTask
from videotrans.task._remove_noise import remove_noise
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

    cfg={
    source_language
    recogn_type 识别模式索引
    split_type 整体识别/均等分割
    model_name 模型名字
    cuda 是否启用cuda
    }
    """

    def __init__(self, cfg: Dict = None, obj: Dict = None):
        super().__init__(cfg, obj)
        self.out_format=cfg.get('out_format','srt')
        self.shoud_recogn = True
        # 存放目标文件夹
        if 'target_dir' not in self.cfg or not self.cfg['target_dir']:
            self.cfg['target_dir'] = config.HOME_DIR + f"/recogn"
        if not Path(self.cfg['target_dir']).exists():
            Path(self.cfg['target_dir']).mkdir(parents=True, exist_ok=True)
        # 生成目标字幕文件
        self.cfg['target_sub'] = self.cfg['target_dir'] + '/' + self.cfg['noextname'] + '.srt'
        # 临时文件夹
        self.cfg['cache_folder'] = config.TEMP_HOME + f'/speech2text'
        if not Path(self.cfg['cache_folder']).exists():
            Path(self.cfg['cache_folder']).mkdir(parents=True, exist_ok=True)
        self.cfg['shibie_audio'] = self.cfg['cache_folder'] + f'/{self.cfg["noextname"]}-{time.time()}.wav'
        self._signal(text='语音识别文字处理中' if config.defaulelang == 'zh' else 'Speech Recognition to Word Processing')

    def prepare(self):
        if self._exit():
            return
        tools.conver_to_16k(self.cfg['name'], self.cfg['shibie_audio'])

    def recogn(self):
        if self._exit():
            return
        while 1:
            if Path(self.cfg['shibie_audio']).exists():
                break
            time.sleep(1)
        try:
            if self.cfg.get('remove_noise'):
                self._signal(text='开始语音降噪处理，用时可能较久，请耐心等待' if config.defaulelang=='zh' else 'Starting to process speech noise reduction, which may take a long time, please be patient')
                self.cfg['shibie_audio']=remove_noise(self.cfg['shibie_audio'],f"{self.cfg['cache_folder']}/removed_noise_{time.time()}.wav")
            
            
            if self.cfg['recogn_type']==Faster_Whisper_XXL:
                import subprocess,shutil
                cmd=[
                    config.settings.get('Faster_Whisper_XXL',''),
                    self.cfg['shibie_audio'],
                    "-f","srt"
                ]
                if self.cfg['detect_language']!='auto':
                    cmd.extend(['-l',self.cfg['detect_language'][:2]])
                cmd.extend(['--model',self.cfg['model_name'],'--output_dir',self.cfg['target_dir']])
                txt_file=Path(config.settings.get('Faster_Whisper_XXL','')).parent.as_posix()+'/pyvideotrans.txt'
                if Path(txt_file).exists():
                    cmd.extend(Path(txt_file).read_text(encoding='utf-8').strip().split(' '))
                
                print(cmd)
                print(self.cfg['target_dir'])
                while 1:
                    if not config.copying:
                        break
                    time.sleep(1)
                subprocess.run(cmd)
                outsrt_file=self.cfg['target_dir']+'/'+Path(self.cfg['shibie_audio']).stem+".srt"
                if outsrt_file!=self.cfg['target_sub']:
                    shutil.copy2(outsrt_file,self.cfg['target_sub'])
                    Path(outsrt_file).unlink(missing_ok=True)
                self._signal(text=Path(self.cfg['target_sub']).read_text(encoding='utf-8'), type='replace_subtitle')
            else:
                raw_subtitles = run(
                    # faster-whisper openai-whisper googlespeech
                    recogn_type=self.cfg['recogn_type'],
                    # 整体 预先 均等
                    split_type=self.cfg['split_type'],
                    uuid=self.uuid,
                    # 模型名
                    model_name=self.cfg['model_name'],
                    # 识别音频
                    audio_file=self.cfg['shibie_audio'],
                    detect_language=self.cfg['detect_language'],
                    cache_folder=self.cfg['cache_folder'],
                    is_cuda=self.cfg['is_cuda'],
                    subtitle_type=0,
                    inst=self)
                if self._exit():
                    return
                if not raw_subtitles or len(raw_subtitles) < 1:
                    raise Exception(self.cfg['basename'] + config.transobj['recogn result is empty'].replace('{lang}',self.cfg['detect_language']))
                self._save_srt_target(raw_subtitles, self.cfg['target_sub'])

            Path(self.cfg['shibie_audio']).unlink(missing_ok=True)
        except Exception as e:
            msg = f'{str(e)}{str(e.args)}'
            tools.send_notification(msg, f'{self.cfg["basename"]}')
            self._signal(text=f"{msg}", type='error')
            raise

    def task_done(self):
        if self._exit():
            return
        self._signal(text=f"{self.cfg['name']}", type='succeed')
        tools.send_notification(config.transobj['Succeed'], f"{self.cfg['basename']}")
        if self.out_format=='txt':
            import re
            content=Path(self.cfg['target_sub']).read_text(encoding='utf-8')
            content=re.sub(r"(\r\n|\r|\n|\s|^)\d+(\r\n|\r|\n)","\n",content)
            content=re.sub(r'\n\d+:\d+:\d+(\,\d+)\s*-->\s*\d+:\d+:\d+(\,\d+)?\n?','',content)
            with open(self.cfg['target_sub'][:-3]+'txt','w',encoding='utf-8') as f:
                f.write(content)            
        elif self.out_format !='srt':
            tools.runffmpeg(['-y', '-i',  self.cfg['target_sub'],  self.cfg['target_sub'][:-3]+self.out_format])
            Path(self.cfg['target_sub']).unlink(missing_ok=True)

        if 'shound_del_name' in self.cfg:
            Path(self.cfg['shound_del_name']).unlink(missing_ok=True)

    def _exit(self):
        if config.exit_soft or config.box_recogn !='ing':
            return True
        return False

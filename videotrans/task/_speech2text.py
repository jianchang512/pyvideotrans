import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path

from videotrans.configure import config
from videotrans.configure.config import tr, logs
from videotrans.recognition import run, Faster_Whisper_XXL,Whisper_CPP
from videotrans.task._base import BaseTask
from videotrans.task._remove_noise import remove_noise
from videotrans.util import tools

"""
仅语音识别
"""


@dataclass
class SpeechToText(BaseTask):
    # 识别后输出的字幕格式，srt txt 等
    out_format: str = field(init=True,default='srt')
    # 在这个子类中，shoud_recogn 总是 True。
    shoud_recogn: bool = field(default=True, init=False)
    # 是否需要将生成的字幕复制到原始视频所在目录下，并重命名为视频同名，以方便视频自动加载软字幕
    copysrt_rawvideo: bool = field(default=False, init=True)

    def __post_init__(self):
        super().__post_init__()
        # 存放目标文件夹
        if not self.cfg.target_dir:
            self.cfg.target_dir = config.HOME_DIR + f"/recogn"
        # 转录后的目标字幕文件，先统一转为srt，然后再使用ffmpeg转为其他格式字幕
        self.cfg.target_sub = self.cfg.target_dir + '/' + self.cfg.noextname + '.srt'
        # 临时文件夹
        self.cfg.cache_folder = config.TEMP_HOME + f'/speech2text'
        Path(self.cfg.target_dir).mkdir(parents=True, exist_ok=True)
        Path(self.cfg.cache_folder).mkdir(parents=True, exist_ok=True)
        # 处理为 16k 的wav单通道音频，供模型识别用
        self.cfg.shibie_audio = self.cfg.cache_folder + f'/{self.cfg.noextname}-{time.time()}.wav'
        self._signal(text=tr("Speech Recognition to Word Processing"))

    # 预先处理
    def prepare(self):
        if self._exit():
            return
        tools.conver_to_16k(self.cfg.name, self.cfg.shibie_audio)

    def recogn(self):
        if self._exit(): return
        while 1:
            # 尚未生成
            if Path(self.cfg.shibie_audio).exists():
                break
            time.sleep(0.5)
        try:
            # 需要降噪
            if self.cfg.remove_noise:
                self._signal(
                    text=tr("Starting to process speech noise reduction, which may take a long time, please be patient"))
                self.cfg.shibie_audio = remove_noise(self.cfg.shibie_audio, f"{self.cfg.cache_folder}/removed_noise_{time.time()}.wav")
            if self._exit(): return
            # faster_xxl.exe 单独处理
            if self.cfg.recogn_type == Faster_Whisper_XXL:
                import subprocess, shutil
                cmd = [
                    config.settings.get('Faster_Whisper_XXL', ''),
                    self.cfg.shibie_audio,
                    "-pp",
                    "-f", "srt"
                ]
                if self.cfg.detect_language != 'auto':
                    cmd.extend(['-l', self.cfg.detect_language.split('-')[0]])
                
                prompt=None
                if self.cfg.detect_language!='auto':
                    prompt = config.settings.get(f'initial_prompt_{self.cfg.detect_language}')
                if prompt:
                    cmd+=['--initial_prompt',prompt]
                
                cmd.extend(['--model', self.cfg.model_name, '--output_dir', self.cfg.target_dir])
                txt_file = Path(config.settings.get('Faster_Whisper_XXL', '')).parent.as_posix() + '/pyvideotrans.txt'
                if Path(txt_file).exists():
                    cmd.extend(Path(txt_file).read_text(encoding='utf-8').strip().split(' '))

                outsrt_file = self.cfg.target_dir + '/' + Path(self.cfg.shibie_audio).stem + ".srt"
                cmdstr = " ".join(cmd)
                logs(f'Faster_Whisper_XXL: {cmdstr=}\n{outsrt_file=}\n{self.cfg.target_sub=}')

                self._external_cmd_with_wrapper(cmd)


                try:
                    shutil.copy2(outsrt_file, self.cfg.target_sub)
                except shutil.SameFileError:
                    pass
                self._signal(text=Path(self.cfg.target_sub).read_text(encoding='utf-8'), type='replace_subtitle')
                return
            if self.cfg.recogn_type == Whisper_CPP:

                import subprocess, shutil
                cpp_path=config.settings.get('Whisper.cpp', 'whisper-cli')
                cmd = [
                    cpp_path,
                    "-f",
                    self.cfg.shibie_audio,
                    "-osrt",
                    "-np"
                ]
                cmd+=["-l",self.cfg.detect_language.split('-')[0]]
                prompt=None
                if self.cfg.detect_language!='auto':
                    prompt = config.settings.get(f'initial_prompt_{self.cfg.detect_language}')
                if prompt:
                    cmd+=['--prompt',prompt]
                cpp_folder=Path(cpp_path).parent.resolve().as_posix()
                if not Path(f'{cpp_folder}/models/{self.cfg.model_name}').is_file():
                    raise RuntimeError(tr('The model does not exist. Please download the model to the {} directory first.',f'{cpp_folder}/models'))
                txt_file =  cpp_folder+ '/pyvideotrans.txt'
                if Path(txt_file).exists():
                    cmd.extend(Path(txt_file).read_text(encoding='utf-8').strip().split(' '))
                
                cmd.extend(['-m', f'models/{self.cfg.model_name}', '-of', self.cfg.target_sub[:-4]])
                
                logs(f'Whipser.cpp: {cmd=}')

                self._external_cmd_with_wrapper(cmd)


                self._signal(text=Path(self.cfg.target_sub).read_text(encoding='utf-8'), type='replace_subtitle')
                return    
            # 其他识别渠道
            raw_subtitles = run(
                recogn_type=self.cfg.recogn_type,
                split_type=self.cfg.split_type,
                uuid=self.uuid,
                model_name=self.cfg.model_name,
                audio_file=self.cfg.shibie_audio,
                detect_language=self.cfg.detect_language,
                cache_folder=self.cfg.cache_folder,
                is_cuda=self.cfg.cuda,
                subtitle_type=0,
            )
            if self._exit(): return
            if not raw_subtitles or len(raw_subtitles) < 1:
                raise RuntimeError( self.cfg.basename + tr('recogn result is empty'))

            self._save_srt_target(raw_subtitles, self.cfg.target_sub)
            try:
                Path(self.cfg.shibie_audio).unlink(missing_ok=True)
            except OSError:
                pass
        except Exception:
            raise

    def task_done(self):
        if self._exit(): return
        self._signal(text=f"{self.cfg.name}", type='succeed')
        if self.out_format == 'txt':
            import re
            content = Path(self.cfg.target_sub).read_text(encoding='utf-8')
            content = re.sub(r"(\r\n|\r|\n|\s|^)\d+(\r\n|\r|\n)", "\n", content)
            content = re.sub(r'\n\d+:\d+:\d+(\,\d+)\s*-->\s*\d+:\d+:\d+(\,\d+)?\n?', '', content)
            with open(self.cfg.target_sub[:-3] + 'txt', 'w', encoding='utf-8') as f:
                f.write(content)
            self.cfg.target_sub = self.cfg.target_sub[:-3] + 'txt'
        elif self.out_format != 'srt':
            tools.runffmpeg(['-y', '-i', self.cfg.target_sub, self.cfg.target_sub[:-3] + self.out_format])
            Path(self.cfg.target_sub).unlink(missing_ok=True)
            self.cfg.target_sub = self.cfg.target_sub[:-3] + self.out_format

        if self.copysrt_rawvideo:
            p = Path(self.cfg.name)
            try:
                shutil.copy2(self.cfg.target_sub, f'{p.parent.as_posix()}/{p.stem}.{self.out_format}')
            except shutil.SameFileError:
                pass
        try:
            if self.cfg.shound_del_name:
                Path(self.cfg.shound_del_name).unlink(missing_ok=True)
        except Exception:
            pass

    def _exit(self):
        if config.exit_soft or config.box_recogn != 'ing':
            self.hasend=True
            return True
        return False

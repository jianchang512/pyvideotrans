# ToDo 将 whisper.cpp 移动到此
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from videotrans.configure.config import tr, settings, logger
from videotrans.configure.excepts import SpeechToTextError
from videotrans.recognition._base import BaseRecogn
from videotrans.util import tools


@dataclass
class CPPRecogn(BaseRecogn):
    
    def _exec(self):
        cpp_path = settings.get('Whisper_cpp', 'whisper-cli')
        cmd = [
            cpp_path,
            "-f",
            self.audio_file,
            "-osrt",
            "-np"

        ]
        cmd += ["-l", self.detect_language.split('-')[0]]
        prompt = settings.get(f'initial_prompt_{self.detect_language}')
        if prompt:
            cmd += ['--prompt', prompt]
        cpp_folder = Path(cpp_path).parent.resolve().as_posix()
        if not Path(f'{cpp_folder}/models/{self.model_name}').is_file():
            raise RuntimeError(tr('The model does not exist. Please download the model to the {} directory first.',
                                  f'{cpp_folder}/models'))
        txt_file = cpp_folder + '/pyvideotrans.txt'

        if Path(txt_file).exists():
            cmd.extend(Path(txt_file).read_text(encoding='utf-8').strip().split(' '))
        
        _sub=f'{self.cache_folder}/cpp_srt'
        cmd.extend(['-m', f'models/{self.model_name}', '-of', _sub])

        logger.debug(f'Whisper.cpp: {cmd=}')
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8', errors='replace', creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0, cwd=os.path.dirname(cpp_path))
            return tools.get_subtitle_from_srt(_sub+".srt", is_file=True)
        except subprocess.CalledProcessError as e:
            raise SpeechToTextError(e.stderr+f"\n{e.stdout}")

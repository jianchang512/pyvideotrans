import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List,  Union
from videotrans.configure.excepts import SpeechToTextError
from videotrans.configure.config import settings,logger
from videotrans.recognition._base import BaseRecogn
from videotrans.task.taskcfg import SrtItem
from videotrans.util import tools


@dataclass
class XXLRecogn(BaseRecogn):
    def _exec(self)->Union[List[SrtItem], None]:
        xxl_path = settings.get('Faster_Whisper_XXL', 'Faster_Whisper_XXL.exe')
        cmd = [
            xxl_path,
            self.audio_file,
            "-pp",
            "-f", "srt",
            "-ct",settings.get('cuda_com_type', 'int8')
        ]
        cmd.extend(['-l', self.detect_language.split('-')[0]])

        prompt = settings.get(f'initial_prompt_{self.detect_language}')
        if prompt:
            cmd += ['--initial_prompt', prompt]
        cmd.extend(['--model', self.model_name, '--output_dir', self.cache_folder])

        txt_file = Path(xxl_path).parent.resolve().as_posix() + '/pyvideotrans.txt'

        if Path(txt_file).exists():
            cmd.extend(Path(txt_file).read_text(encoding='utf-8').strip().split(' '))

        cmdstr = " ".join(cmd)
        outsrt_file = self.cache_folder + '/' + Path(self.audio_file).stem + ".srt"
        logger.debug(f'Faster_Whisper_XXL: {cmdstr=}\n{outsrt_file=}')

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8', errors='replace', creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0, cwd=os.path.dirname(xxl_path))
            return tools.get_subtitle_from_srt(outsrt_file, is_file=True)
        except subprocess.CalledProcessError as e:
            raise SpeechToTextError(e.stderr+f"\n{e.stdout}")


import os,re
import subprocess
import sys,shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List,  Union
from videotrans.configure.excepts import SpeechToTextError
from videotrans.configure.config import settings,logger,ROOT_DIR
from videotrans.recognition._base import BaseRecogn
from videotrans.task.taskcfg import SrtItem
from videotrans.util._srt_parse import get_subtitle_from_srt
from videotrans.configure.contants import FASTER_MODELS_DICT
from videotrans.util.help_down import check_and_down_hf



@dataclass
class XXLRecogn(BaseRecogn):
    def __post_init__(self):
        super().__post_init__()
        if self.model_name not in FASTER_MODELS_DICT:
            raise SpeechToTextError(f'{self.model_name} is not support')
        self.local_dir = f'{ROOT_DIR}/models/models--'+FASTER_MODELS_DICT.get(self.model_name,'').replace('/', '--')


    def _download(self):
        repid=FASTER_MODELS_DICT.get(self.model_name,'')
        check_and_down_hf(self.model_name,repid,self.local_dir,callback=self._process_callback)

        src_dir = Path(self.local_dir)
        dst_dir = src_dir / repid.split('/')[-1]

        dst_dir.mkdir(parents=True, exist_ok=True)
        for path in src_dir.iterdir():
            if path.is_file():
                shutil.copy2(path, dst_dir)

    
    def _return_time(self,t):
        _spear2=t.split('.')
        if len(_spear2)<=1:
            return '00:00:00,000'
        hms,ms=_spear2
        ms=str(ms)
        _hms=str(hms).split(":")
        _len=len(_hms)
        if _len<3:
            for i in range(3-_len):
                _hms.insert(0,'00')
        if len(ms)<3:
            ms=ms.zfill(3)
        return ":".join(_hms)+f",{ms}"
        
    def _getsrt_from_stdout(self,content,srt_filename):
        s=re.findall(r'\n(\[([\d:\.]+?) --> ([\d:\.]+?)\])\s(.+?)\n',content,flags=re.S)

        if not s or len(s)<1:
            return
        srts=[]
        for i,it in enumerate(s):
            srts.append(f"{i+1}\n{self._return_time(it[1])} --> {self._return_time(it[2])}\n{it[3].strip()}")
        if not srts:
            return
        
        Path(srt_filename).write_text("\n\n".join(srts),encoding='utf-8')
    
    def _exec(self)->Union[List[SrtItem], None]:
        # 从输出读取，而非直接生成srt文件，因后者和pyinstaller打包后冲突报错
        if sys.platform != 'win32': raise SpeechToTextError('This channel is only available on Windows systems.')
        xxl_path = settings.get('Faster_Whisper_XXL', 'Faster_Whisper_XXL.exe')
        max_s=int(float(settings.get('max_speech_duration_s', 5)))
        min_ms = max(int(float(settings.get('min_speech_duration_ms', 1000))), 500)
        silence=max(int(settings.get('min_silence_duration_ms', 140)), 140)
        cmd = [
            xxl_path,
            os.path.basename(self.audio_file),
            "-f", "srt",
            "-ct",settings.get('cuda_com_type', 'int8'),
            "--beep_off",
            "--vad_min_speech_duration_ms",f"{min_ms}",
            "--vad_max_speech_duration_s",f"{max_s}",
            "--vad_min_silence_duration_ms",f"{silence}",
            #"--verbose","True"
        ]
        if self.detect_language!='auto':
            cmd.extend(['-l', self.detect_language.split('-')[0]])

            prompt = settings.get(f'initial_prompt_{self.detect_language}')
            if prompt:
                cmd += ['--initial_prompt', prompt]
        cmd.extend(['--model', self.model_name,'--model_dir', self.local_dir, '--output_dir', '.'])

        txt_file = Path(xxl_path).parent.resolve().as_posix() + '/pyvideotrans.txt'

        if Path(txt_file).exists():
            cmd.extend(Path(txt_file).read_text(encoding='utf-8').strip().split(' '))

        outsrt_file = self.cache_folder + '/' + Path(self.audio_file).stem + ".srt"
        logger.debug(f'Faster_Whisper_XXL: {" ".join(cmd)}\n{outsrt_file=}')

        try:
            # 清理 防止冲突
            env = os.environ.copy()
            pyinstaller_and_python_keys = [
                '_MEIPASS', 
                '_MEIPASS2', 
                'PYTHONHOME',             
                'PYTHONPATH',          
                'PYINSTALLER_STRICT_UNPACK',
                'LD_LIBRARY_PATH',
                'DYLD_LIBRARY_PATH'
            ]
            for key in pyinstaller_and_python_keys:
                env.pop(key, None)

            res=subprocess.run(cmd, 
                capture_output=True, 
                text=True, 
                check=False, 
                encoding='utf-8', 
                errors='replace', 
                shell=False,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
                cwd=self.cache_folder,
                env=env,                    
                stdin=subprocess.DEVNULL

            )
            if not res or not res.stdout:
                raise SpeechToTextError(f"{res.stderr}\n{res.stdout}" if res else "Faster_Whisper_XXL error")
            self._getsrt_from_stdout(res.stdout,outsrt_file)
            if not os.path.exists(outsrt_file) or os.path.getsize(outsrt_file) <= 0:
                raise SpeechToTextError(f"{res.stderr}\n{res.stdout}")
                
            return get_subtitle_from_srt(outsrt_file, is_file=True)
        except subprocess.CalledProcessError as e:
            raise SpeechToTextError(f"{e.stderr}\n{e.stdout}")


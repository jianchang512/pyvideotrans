import re,os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Set


from videotrans.configure import config
from videotrans.configure.config import tr
from videotrans.tts._base import BaseTTS
from videotrans.util import tools
import time

from concurrent.futures import ProcessPoolExecutor
import wave
from piper import PiperVoice,SynthesisConfig


# 用于多进程转换
def _convert_to_wav(mp3_file_path, output_wav_file_path):
    cmd = [
        "-y",
        "-i",
        mp3_file_path,
        "-ar",
        "48000",
        "-ac",
        "2",
        "-c:a",
        "pcm_s16le",
        output_wav_file_path
    ]
    try:
        tools.runffmpeg(cmd, force_cpu=True)
        tools.remove_silence_wav(output_wav_file_path)
    except Exception:
        pass
    return True

#用于多进程
def _t(it,device='cpu',rate=1.0,model_file=None):
    if not it.get('text','').strip():
        return
    voice = PiperVoice.load(model_file,use_cuda=True if device=='cuda' else False)
    syn_config = SynthesisConfig(
        length_scale=float(rate),  # twice as slow
    )

    with wave.open(it['filename']+'-24k.wav', "wb") as wav_file:
        voice.synthesize_wav(it.get('text'), wav_file,syn_config=syn_config)
        
@dataclass
class PiperTTS(BaseTTS):

    def __post_init__(self):

        super().__post_init__()
        rate=1/(1+float(self.rate.replace('%',''))/100)
        self.rate=round(rate,1)
        self.device="cpu"# todo cuda
        
    def _get_model_from_name(self,name):
        # 角色名转为 piper文件夹下的子文件夹名
        name_path=name.split('_')[0]+'/'+name.replace('-','/')
        # 存放onnx文件的最终文件夹绝对路径
        local_dir=config.ROOT_DIR+'/models/piper/'+name_path
        onnx_file=f'{local_dir}/{name}.onnx'
        if Path(onnx_file).exists():
            return onnx_file
        url=f'/rhasspy/piper-voices/resolve/main/{name_path}'
        urls=[
            f'{url}/{name}.onnx?download=true',
            f'{url}/{name}.onnx.json?download=true',
        ]
        Path(local_dir).mkdir(exist_ok=True, parents=True)
        tools.down_file_from_hf(local_dir,urls=urls,callback=self._process_callback)
        return onnx_file
    
    def _process_callback(self,msg):
        self._signal(text=msg)
    
    def _exec(self):
        # 判断模型是否存在
        role_model={}
        for it in self.queue_tts:
            if it['role'] in role_model:
                continue
            role_model[it['role']]=self._get_model_from_name(it['role'])
        all_task=[]
        with ProcessPoolExecutor(max_workers=min(max(2,int(config.settings.get('dubbing_thread',1))),len(self.queue_tts),os.cpu_count())) as pool:
            for item in self.queue_tts:
                all_task.append(pool.submit(_t, item,self.device,self.rate,role_model.get(item['role'])))
            completed_tasks = 0
            for task in all_task:
                try:
                    task.result()  # 等待任务完成
                    completed_tasks += 1
                    self._signal( text=f"tts [{completed_tasks}/{len(self.queue_tts)}]" )
                except Exception as e:
                    config.logger.exception(f"Task {completed_tasks + 1} failed with error: {e}", exc_info=True)
        
        
        ok, err = 0, 0
        for i, item in enumerate(self.queue_tts):
            if config.exit_soft:
                return
            if tools.vail_file(item['filename']+'-24k.wav'):
                ok += 1
            else:
                err += 1

        if ok>0:
            all_task = []
            total_tasks=len(self.queue_tts)
            
            self._signal(text=f'convert wav {total_tasks}')
            with ProcessPoolExecutor(max_workers=min(12,len(self.queue_tts),os.cpu_count())) as pool:
                for item in self.queue_tts:
                    if tools.vail_file(item['filename']+'-24k.wav'):
                        all_task.append(pool.submit(_convert_to_wav, item['filename']+"-24k.wav",item['filename']))
                completed_tasks = 0
                for task in all_task:
                    try:
                        task.result()  # 等待任务完成
                        completed_tasks += 1
                        self._signal( text=f"convert wav [{completed_tasks}/{total_tasks}]" )
                    except Exception as e:
                        config.logger.exception(f"Task {completed_tasks + 1} failed with error: {e}", exc_info=True)
                
        if err > 0:
            msg=f'[{err}] errors, {ok} succeed'
            self._signal(text=msg)
            config.logger.debug(f'EdgeTTS配音结束：{msg}')



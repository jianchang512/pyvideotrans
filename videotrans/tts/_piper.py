from dataclasses import dataclass
from pathlib import Path

from videotrans.configure import config
from videotrans.tts._base import BaseTTS
from videotrans.util import tools
import wave
from piper import PiperVoice,SynthesisConfig
from videotrans.configure._except import NO_RETRY_EXCEPT,StopRetry


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
    

    
    def _exec(self):
        # 判断模型是否存在
        role_model={}
        _model_obj={}
        for it in self.queue_tts:
            if it['role'] in role_model or not it.get('text','').strip():
                continue
            role_model[it['role']]=self._get_model_from_name(it['role'])

        syn_config = SynthesisConfig(
            length_scale=float(self.rate),  # twice as slow
        )
        ok, err = 0, 0
        for i, item in enumerate(self.queue_tts):
            if config.exit_soft:return
            if not item.get('text','').strip():
                continue
            try:
                _model_file=role_model.get(item['role'])
                voice=_model_obj.get(_model_file)
                if voice is None:
                    voice = PiperVoice.load(_model_file,use_cuda=True if self.device=='cuda' else False)
                    _model_obj[_model_file]=voice
                with wave.open(item['filename']+'-24k.wav', "wb") as wav_file:
                    voice.synthesize_wav(item.get('text'), wav_file,syn_config=syn_config)
                if not tools.vail_file(item['filename']+'-24k.wav'):
                    err+=1
                    continue
                ok+=1
                self.convert_to_wav(item['filename']+'-24k.wav',item['filename'])
            except Exception as e:
                config.logger.exception(f'piper dubbing error:{e}',exc_info=True)
                err+=1

        if err > 0:
            msg=f'[{err}] errors, {ok} succeed'
            self._signal(text=msg)
            config.logger.debug(f'piper配音结束：{msg}')

        try:
            del _model_obj
            import gc
            gc.collect()
        except:
            pass

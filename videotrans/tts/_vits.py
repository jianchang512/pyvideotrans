import logging
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
import sherpa_onnx
import soundfile as sf

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
def _t(it,device='cpu',rate=1.0,language="zh"):
    if not it.get('text','').strip():
        return
    sid=0
    role=it.get('role','')
    print(f'{role=}')
    if role=='en_female':# matcha english
        tts_config = sherpa_onnx.OfflineTtsConfig(
            model=sherpa_onnx.OfflineTtsModelConfig(
               matcha=sherpa_onnx.OfflineTtsMatchaModelConfig(
                    acoustic_model=f'{config.ROOT_DIR}/models/vits/{role}/model.onnx' ,
                    vocoder=f'{config.ROOT_DIR}/models/vits/{role}/vocos-22khz-univ.onnx',
                    tokens=f'{config.ROOT_DIR}/models/vits/{role}/tokens.txt',
                    data_dir=f'{config.ROOT_DIR}/models/vits/{role}/espeak-ng-data',
                ),
                provider=device,
                debug=False,
                num_threads=2,
            ),
            rule_fsts="",
            max_num_sentences=1,
        )
    elif role=='zh_female': # matcha chinese
        tts_config = sherpa_onnx.OfflineTtsConfig(
            model=sherpa_onnx.OfflineTtsModelConfig(
               matcha=sherpa_onnx.OfflineTtsMatchaModelConfig(
                    acoustic_model=f'{config.ROOT_DIR}/models/vits/{role}/model.onnx',
                    vocoder=f'{config.ROOT_DIR}/models/vits/{role}/vocos-22khz-univ.onnx',
                    lexicon=f'{config.ROOT_DIR}/models/vits/{role}/lexicon.txt',
                    tokens=f'{config.ROOT_DIR}/models/vits/{role}/tokens.txt',
                ),
                provider=device,
                debug=False,
                num_threads=2,
            ),
            rule_fsts=f"{config.ROOT_DIR}/models/vits/{role}/date.fst,{config.ROOT_DIR}/models/vits/{role}/number.fst,{config.ROOT_DIR}/models/vits/{role}/phone.fst",
            max_num_sentences=1,
        )
    elif role=='zh_en':#zh+en vits
        sid=0
        tts_config = sherpa_onnx.OfflineTtsConfig(
            model=sherpa_onnx.OfflineTtsModelConfig(
                   vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                        model= f'{config.ROOT_DIR}/models/vits/{role}/model.onnx',
                        tokens=f'{config.ROOT_DIR}/models/vits/{role}/tokens.txt',
                        lexicon=f'{config.ROOT_DIR}/models/vits/{role}/lexicon.txt',
                    ),
                    provider=device,
                    debug=False,
                    num_threads=2,
                ),
            rule_fsts=f"{config.ROOT_DIR}/models/vits/{role}/date.fst,{config.ROOT_DIR}/models/vits/{role}/number.fst,{config.ROOT_DIR}/models/vits/{role}/phone.fst,{config.ROOT_DIR}/models/vits/{role}/new_heteronym.fst",
            max_num_sentences=1,
        )
    elif role.startswith('en_'):#en vits 109 speakers
        sid=int(role.split('_')[-1])
        tts_config = sherpa_onnx.OfflineTtsConfig(
            model=sherpa_onnx.OfflineTtsModelConfig(
               vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                    model= f'{config.ROOT_DIR}/models/vits/en_vctk/model.onnx',
                    tokens=f'{config.ROOT_DIR}/models/vits/en_vctk/tokens.txt',
                    lexicon=f'{config.ROOT_DIR}/models/vits/en_vctk/lexicon.txt',
                ),
                provider=device,
                debug=False,
                num_threads=2,
            ),
            rule_fsts="",
            max_num_sentences=1,
        )

    elif role.startswith('zh_'):#zh vits   174 speakers
        sid=int(role.split('_')[-1])        
        tts_config = sherpa_onnx.OfflineTtsConfig(
                model=sherpa_onnx.OfflineTtsModelConfig(
                   vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                        model= f'{config.ROOT_DIR}/models/vits/zh_aishell/model.onnx',
                        tokens=f'{config.ROOT_DIR}/models/vits/zh_aishell/tokens.txt',
                        lexicon=f'{config.ROOT_DIR}/models/vits/zh_aishell/lexicon.txt',
                    ),
                    provider=device,
                    debug=False,
                    num_threads=2,
                ),
                rule_fsts=f"{config.ROOT_DIR}/models/vits/zh_aishell/date.fst,{config.ROOT_DIR}/models/vits/zh_aishell/number.fst,{config.ROOT_DIR}/models/vits/zh_aishell/phone.fst,{config.ROOT_DIR}/models/vits/zh_aishell/new_heteronym.fst",
                max_num_sentences=1,
            )
    if not tts_config.validate():
        raise ValueError("Please check your config")

    tts = sherpa_onnx.OfflineTts(tts_config)

    start = time.time()
    
    
    audio = tts.generate(it['text'], sid=sid, speed=rate)


    if len(audio.samples) == 0:
        print("Error in generating audios. Please read previous error messages.")
        return



    sf.write(
        it['filename']+"-24k.wav",
        audio.samples,
        samplerate=audio.sample_rate,
        subtype="PCM_16",
    )





@dataclass
class VitsCNEN(BaseTTS):

    def __post_init__(self):

        super().__post_init__()
        self.rate=1+float(self.rate.replace('%',''))/100
        self.device="cpu" #todo cuda


        
        
    def _exec(self):

        all_task=[]
        with ProcessPoolExecutor(max_workers=min(max(2,int(config.settings.get('dubbing_thread',1))),len(self.queue_tts),os.cpu_count())) as pool:
            for item in self.queue_tts:
                all_task.append(pool.submit(_t, item,self.device,self.rate,self.language))
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
            config.logger.debug(f'Match配音结束：{msg}')



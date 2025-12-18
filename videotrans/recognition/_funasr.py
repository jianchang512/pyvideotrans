# stt项目识别接口
import json
import re,os,requests
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Union


from pydub import AudioSegment

from videotrans.configure import config
from videotrans.configure.config import tr,logs
from videotrans.recognition._base import BaseRecogn
from videotrans.util import tools


@dataclass
class FunasrRecogn(BaseRecogn):

    def __post_init__(self):
        super().__post_init__()

    def remove_unwanted_characters(self, text: str) -> str:
        # 保留中文、日文、韩文、英文、数字和常见符号，去除其他字符
        allowed_characters = re.compile(r'[^\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af'
                                        r'a-zA-Z0-9\s.,!@#$%^&*()_+\-=\[\]{};\'"\\|<>/?，。！｛｝【】；‘’“”《》、（）￥]+')
        return re.sub(allowed_characters, '', text)

    def _tosend(self, msg):
        self._signal(text=msg)

    def _exec(self) -> Union[List[Dict], None]:
        if self._exit():
            return


        if self.model_name in ['SenseVoiceSmall','Fun-ASR-Nano-2512'] or self.detect_language[:2].lower() not in ['zh','yu','en']:
            return self._exec1()
            
        raw_subtitles = []       
        model_dir=f'{config.ROOT_DIR}/models/models/iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch'
        if not Path(model_dir).exists():
            self._tosend(f'Download {self.model_name} from modelscope.cn')
        else:
            self._tosend(f'Load {self.model_name} model')
        from funasr import AutoModel
        model=None
        try:
            model = AutoModel(
                model='iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch',
                vad_model="fsmn-vad", 
                punc_model="ct-punc",
                local_dir=config.ROOT_DIR + "/models",
                hub='ms',
                spk_model="cam++" if self.max_speakers>-1 else None, 
                disable_update=True,
                disable_progress_bar=True,
                disable_log=True,
                device=self.device
            )
        except (OSError,AssertionError) as e:
            if not Path(model_dir+'/config.yaml').exists():
                raise RuntimeError(config.tr('downloading model.safetensors and all .json files',f'{config.ROOT_DIR}/models/models/iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch')+f'\n[https://modelscope.cn/models/iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch/files]\n{e}')
            raise
        
        msg = tr("Model loading is complete, enter recognition")
        self._tosend(msg)
        res = model.generate(input=self.audio_file, return_raw_text=True, is_final=True,batch_size=16,
                             sentence_timestamp=True, disable_pbar=True)

        speaker_list=[]
        for it in res[0]['sentence_info']:
            if not it.get('text','').strip():
                continue
            if self.max_speakers>-1:
                speaker_list.append(f"spk{it.get('spk', 0)}")
            tmp = {
                "line": len(raw_subtitles) + 1,
                "text":it['text'].strip(),
                "start_time": it['start'],
                "end_time": it['end'],
                "startraw": f'{tools.ms_to_time_string(ms=it["start"])}',
                "endraw": f'{tools.ms_to_time_string(ms=it["end"])}'
            }
            self._signal(text=it['text'] + "\n", type='subtitle')
            tmp['time'] = f"{tmp['startraw']} --> {tmp['endraw']}"
            raw_subtitles.append(tmp)
        if speaker_list:
            Path(f'{self.cache_folder}/speaker.json').write_text(json.dumps(speaker_list), encoding='utf-8')
        try:
            import torch
            import gc
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()
            del model
        except Exception:
            pass
        return raw_subtitles

    def download_qwen_model(self,model_name):
        url = "https://modelscope.cn/models/Qwen/Qwen3-0.6B/resolve/master/model.safetensors"
        output_dir = f'{config.ROOT_DIR}/models/models/{model_name}/Qwen3-0.6B'
        save_path = f'{output_dir}/model.safetensors'
        self._tosend(f'Downloading Qwen3-0.6B model.safetensors')
        Path(output_dir).mkdir(exist_ok=True, parents=True)
        print(f"开始下载到: {save_path}")
        
        try:
            with requests.get(url, stream=True) as response:
                response.raise_for_status()
                # 获取预期总大小 (字节)
                total_expected_size = int(response.headers.get('content-length', 0))
                
                # 手动计数器，用于记录实际下载量
                downloaded_size = 0
                
                # 1MB 一个分块
                chunk_size = 1024 * 1024 
                
                with open(save_path, 'wb') as file:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk: # 过滤掉保持连接的空块
                            file.write(chunk)
                            downloaded_size += len(chunk) # 累加当前块的大小
                            
                            # 简单的打印，避免屏幕刷屏，每下载 100MB 打印一次
                            if downloaded_size % (100 * 1024 * 1024) < chunk_size:
                                print(f"已下载: {downloaded_size / (1024*1024):.2f} MB", end='\r')
                                self._tosend(f'{downloaded_size*100/total_expected_size:.2f}% Qwen3-0.6B model.safetensors')

                print(f"\n下载结束。")

                # 4. 校验完整性
                if total_expected_size != 0 and downloaded_size != total_expected_size:
                    print(f"[错误] 文件不完整！")
                    print(f"预期大小: {total_expected_size} 字节")
                    print(f"实际大小: {downloaded_size} 字节")
                    raise RuntimeError(f'下载出错,请手动打开网址\n{url}\n下载后保存到 {output_dir}\n')
                else:
                    print(f"[成功] 文件已保存，大小校验通过。")

        except Exception as e:
            raise


    def _exec1(self) -> Union[List[Dict], None]:
        if self._exit():
            return
        
        if self.model_name=='Fun-ASR-Nano-2512':
            model_name='FunAudioLLM/Fun-ASR-Nano-2512'
        else:
            model_name='iic/SenseVoiceSmall'
        if not Path(f'{config.ROOT_DIR}/models/models/{model_name}').exists():
            self._tosend(f'Download {model_name} from modelscope.cn')
        else:
            self._tosend(f'Load {model_name}')
        from funasr import AutoModel
        from funasr.utils.postprocess_utils import rich_transcription_postprocess
        from concurrent.futures import ThreadPoolExecutor
        print(f'{self.model_name=},{model_name=}')
        model=None
        try:
            model = AutoModel(
                model=model_name,
                punc_model="ct-punc",
                device=self.device,
                local_dir=config.ROOT_DIR + "/models",
                disable_update=True,
                disable_progress_bar=True,
                disable_log=True,
                trust_remote_code=True,
                remote_code=f"{config.ROOT_DIR}/videotrans/codes/model.py",
                hub='ms',
            )
        except (OSError,AssertionError) as e:
            # Fun-ASR-Nano-2512库中 缺少qwen3-0.6b model.safetensors，模型几乎肯定自动下载失败
            # 失败后从 qwen3-0.6b库中单独下载
            # https://modelscope.cn/models/FunAudioLLM/Fun-ASR-Nano-2512/files
            # https://modelscope.cn/models/Qwen/Qwen3-0.6B
            model_1=f'{config.ROOT_DIR}/models/models/{model_name}/model.pt'
            model_2=f'{config.ROOT_DIR}/models/models/{model_name}/Qwen3-0.6B/model.safetensors'
            if self.model_name=='Fun-ASR-Nano-2512' and Path(model_1).exists() and not Path(model_2).exists():
                self.download_qwen_model(model_name)
                model = AutoModel(
                    model=model_name,
                    punc_model="ct-punc",
                    device=self.device,
                    local_dir=config.ROOT_DIR + "/models",
                    disable_update=True,
                    disable_progress_bar=True,
                    disable_log=True,
                    trust_remote_code=True,
                    remote_code=f"{config.ROOT_DIR}/videotrans/codes/model.py",
                    hub='ms',
                )
            elif not Path(f'{config.ROOT_DIR}/models/models/{model_name}/config.yaml').exists():
                raise RuntimeError(config.tr('downloading model.safetensors and all .json files',f'{config.ROOT_DIR}/models/models/{model_name}')+f'\n[https://modelscope.cn/models/{model_name}/files]\n{e}')
            raise
        except Exception as e:
            raise 
        # vad
        msg = tr("Recognition may take a while, please be patient")
        self._tosend(msg)
        
        vm = AutoModel(
            model="fsmn-vad",
            local_dir=config.ROOT_DIR + "/models",
            max_single_segment_time=int(float(config.settings.get('max_speech_duration_s',5))*1000),
            max_end_silence_time=int(config.settings.get('min_silence_duration_ms',500)),
            hub='ms',
            disable_update=True,
            disable_progress_bar=True,
            disable_log=True,
            device=self.device
        )
        
        segments = vm.generate(input=self.audio_file)
        audiodata = AudioSegment.from_file(self.audio_file)
        

        srts=[]
        is_cjk=True if self.detect_language[:2] in ['zh','ja','ko','yu'] else False
        total=len(segments[0]['value'])
        for i,seg in enumerate(segments[0]['value']):
            self._signal( text=f"stt [{i+1}/{total}]" )
            chunk = audiodata[seg[0]:seg[1]]
            filename = f"{self.cache_folder}/seg-{seg[0]}-{seg[1]}.wav"
            chunk.export(filename)
            srt = {                
                "line": len(srts) + 1,
                "text": '',
                "file":filename,
                "start_time": seg[0],
                "end_time": seg[1],
                "startraw": f'{tools.ms_to_time_string(ms=seg[0])}',
                "endraw": f'{tools.ms_to_time_string(ms=seg[1])}'
            }
            srt['time'] = f"{srt['startraw']} --> {srt['endraw']}"
            res = model.generate(
                input=filename,
                language=self.detect_language[:2],  # "zh", "en", "yue", "ja", "ko", "nospeech"
                use_itn=True,
                batch_size=1,
                disable_pbar=True
            )
            text = self.remove_unwanted_characters(rich_transcription_postprocess(res[0]["text"]))
            srt['text']=text.replace(' ','') if is_cjk else text
            srts.append(srt)
            self._signal(
                text=text + "\n",
                type='subtitle'
            )

        try:
            import torch
            import gc
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()
            del model
            del vm
        except Exception:
            pass


        return srts

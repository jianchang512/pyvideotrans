# zh_recogn 识别
import re,sys,os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Union


from videotrans.configure import config
from videotrans.util import tools
from videotrans.recognition._base import BaseRecogn
from transformers import pipeline
import json,requests,shutil


@dataclass
class HuggingfaceRecogn(BaseRecogn):

    def __post_init__(self):
        super().__post_init__()
        # 完整模型名称，目前只有 nvidia和UsefulSensors
        self.local_dir=f'{config.ROOT_DIR}/models/models--'+self.model_name.replace('/','--')

    def _exec(self) -> Union[List[Dict], None]:
        if self._exit(): return
        self._get_modeldir_download()
        result=[]        
        if self.model_name.startswith('nvidia') or self.model_name.startswith('UsefulSensors'):
            result=self._pipe_asr()
        elif self.model_name in ['jonatasgrosman/wav2vec2-large-xlsr-53-japanese']:
            result=self._wav2vec2_large_japanese()
        elif self.model_name in ['JhonVanced/whisper-large-v3-japanese-4k-steps-ct2','zh-plus/faster-whisper-large-v2-japanese-5k-steps']:
            result=self._faster()
        elif self.model_name in ['efwkjn/whisper-ja-anime-v0.3','biodatlab/whisper-th-medium','biodatlab/whisper-th-large-v3']:
            result=self._whisper_large()
        elif self.model_name in ['suzii/vi-whisper-large-v3-turbo-v1']:
            result=self._vi_whisper()
        elif self.model_name in ['reazon-research/japanese-hubert-base-k2-rs35kh-bpe']:
            result=self._reazon()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            import gc
            gc.collect()
        except Exception:
            pass
        if result:
            return result
        raise RuntimeError(f'No recognition results found:{self.model_name}')

    # nvidia UsefulSensors 
    def _pipe_asr(self):
        
        
        raws = self.cut_audio()
        p = pipeline(
            task="automatic-speech-recognition",
            model=self.local_dir,
            device_map="auto",
            
        )
        for i, it in enumerate(raws):
            try:
                self._signal(text=f"{i+1}/{len(raws)}...")
                res=p(it['file'])
                del it['file']
                if res.get('text'):
                    it['text']=res['text']
                    self._signal(text=f'{it["text"]}\n', type="subtitle")
                    result.append(it)
            except Exception as e:
                config.logger.exception(e,exc_info=True)
        
        del p
        return raws
        
    # jonatasgrosman/wav2vec2-large-xlsr-53-japanese'
    def _wav2vec2_large_japanese(self):
        self._signal(text=f"load {self.model_name}")
        raws=self.cut_audio()
        import torch
        import librosa
        from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor



        # 1. 加载处理器和模型
        processor = Wav2Vec2Processor.from_pretrained(self.local_dir)
        model = Wav2Vec2ForCTC.from_pretrained(self.local_dir)
        if self.is_cuda:
            model=model.to('cuda')

        for i,it in enumerate(raws):
            speech_array, sampling_rate = librosa.load(it['file'], sr=16_000)

            # 3. 预处理音频数据
            # 将音频数据转换为模型所需的 tensor 格式
            inputs = processor(speech_array, sampling_rate=16_000, return_tensors="pt", padding=True)
            if self.is_cuda:
                inputs=inputs.to('cuda')
            # 4. 模型推理
            print("Transcribing...")
            with torch.no_grad():
                # 获取模型的 logits 输出
                logits = model(inputs.input_values, attention_mask=inputs.attention_mask).logits

            # 5. 解码预测结果
            predicted_ids = torch.argmax(logits, dim=-1)
            # batch_decode 返回的是一个列表，我们要取第一个结果 [0]
            text = processor.batch_decode(predicted_ids)[0]
            del it['file']
            if text:
                it['text']=text
                self._signal(text=f'{text}\n', type="subtitle")
                self._signal(text=f' Subtitles {i + 1} ')
        try:
            if processor:
                del processor
            if model:
                del model
            if predicted_ids:
                del predicted_ids
        except:
            pass
        
        return raws
    
    
    # 'efwkjn/whisper-ja-anime-v0.3','biodatlab/whisper-th-medium','biodatlab/whisper-th-large-v3'
    def _whisper_large(self):
        self._signal(text=f"load {self.model_name}")
        raws=self.cut_audio()
        import torch
        import librosa
        from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline


        # 1. 加载处理器和模型

        device = "cuda" if self.is_cuda else "cpu"
        torch_dtype = torch.float16 if self.is_cuda else torch.float32


        model = AutoModelForSpeechSeq2Seq.from_pretrained(
            self.local_dir, 
            torch_dtype=torch_dtype, 
            low_cpu_mem_usage=True, 
            use_safetensors=True
        )

        if self.is_cuda:
            model=model.to('cuda')
        processor = AutoProcessor.from_pretrained(self.local_dir)
        pipe = pipeline(
            "automatic-speech-recognition",
            model=model,
            tokenizer=processor.tokenizer,
            feature_extractor=processor.feature_extractor,
            torch_dtype=torch_dtype,
            device=device,
        )

        


        for i,it in enumerate(raws):
            result = pipe(
                it['file'],
                chunk_length_s=30,
                ignore_warning=True,
                generate_kwargs={"language": "ja", "task": "transcribe"}
            )
            text=result['text']
            del it['file']
            print(text)
            if text:
                it['text']=text
                self._signal(text=f'{text}\n', type="subtitle")
                self._signal(text=f' Subtitles {i + 1} ')
        try:
            if model:
                del model
            if pipe:
                del pipe
            if processor:
                del processor
        except:
            pass
        
        return raws
    
    # reazon-research/japanese-hubert-base-k2-rs35kh-bpe
    def _reazon(self):
        self._signal(text=f"load {self.model_name}")
        raws=self.cut_audio()
        import librosa,torch
        import numpy as np
        from transformers import AutoProcessor, HubertForCTC


        # 1. 加载处理器和模型


        model = HubertForCTC.from_pretrained(
            self.local_dir,
            #torch_dtype=torch.bfloat32 if not self.is_cuda else torch.bfloat16,
            #attn_implementation="flash_attention_2",
        )#.to("cuda")
        if self.is_cuda:
            model.to('cuda')
        processor = AutoProcessor.from_pretrained(self.local_dir)

        


        for i,it in enumerate(raws):
            audio, _ = librosa.load(it['file'], sr=16_000)
            #audio = np.pad(audio)  # Recommend to pad audio before inference
            input_values = processor(
                audio,
                return_tensors="pt",
                sampling_rate=16_000
            ).input_values
            if self.is_cuda:
                input_values=input_values.to("cuda")#.to(torch.bfloat16)

            with torch.inference_mode():
                logits = model(input_values).logits.cpu()
            predicted_ids = torch.argmax(logits, dim=-1)[0]
            text = processor.decode(predicted_ids, skip_special_tokens=True).removeprefix("▁")
            del it['file']
            print(text)
            if text:
                it['text']=text
                self._signal(text=f'{text}\n', type="subtitle")
                self._signal(text=f' Subtitles {i + 1} ')
        try:
            if model:
                del model
            if pipe:
                del pipe
            if processor:
                del processor
        except:
            pass
        
        return raws
    
    

    
    # suzii/vi-whisper-large-v3-turbo-v1'
    def _vi_whisper(self):
        self._signal(text=f"load {self.model_name}")
        raws=self.cut_audio()
        import torch
        import librosa
        from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

        device = "cuda" if self.is_cuda else "cpu"
        torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32


        model = AutoModelForSpeechSeq2Seq.from_pretrained(
            self.local_dir, torch_dtype=torch_dtype, low_cpu_mem_usage=True, use_safetensors=True
        ).to(device)

        processor = AutoProcessor.from_pretrained(self.local_dir)

        pipe = pipeline(
            "automatic-speech-recognition",
            model=model,
            tokenizer=processor.tokenizer,
            feature_extractor=processor.feature_extractor,
            torch_dtype=torch_dtype,
            device=device,
        )
        

        for i,it in enumerate(raws):
            res=pipe(it['file'])
            text = res['text']
            del it['file']
            if text:
                it['text']=text
                self._signal(text=f'{text}\n', type="subtitle")
                self._signal(text=f' Subtitles {i + 1} ')
        try:
            if processor:
                del processor
            if model:
                del model
            if pipe:
                del pipe
        except:
            pass
        
        return raws
    
    
    
    # JhonVanced/whisper-large-v3-japanese-4k-steps-ct2','zh-plus/faster-whisper-large-v2-japanese-5k-steps  
    def _faster(self):
        from faster_whisper import WhisperModel
        raws=self.cut_audio()
        model = WhisperModel(
                self.local_dir,
                device="cuda" if self.is_cuda else "cpu"
        )
        for i,it in enumerate(raws):
            segments, info = model.transcribe(
                it['file'],
                no_speech_threshold=float(config.settings.get('no_speech_threshold',0.5)),
                condition_on_previous_text=bool(config.settings.get('condition_on_previous_text',False)),
                word_timestamps=False,
                language=self.detect_language.split('-')[0] if self.detect_language and self.detect_language != 'auto' else None
            )
            del it['file']

            text=''
            for segment in segments:
                text+=segment.text
            if text:
                it['text']=text
                self._signal(text=f'{text}\n', type="subtitle")
                self._signal(text=f' Subtitles {len(raws) + 1} ')
        return raws
    
    
    def _get_modeldir_download(self):
        """
        下载模型到指定目录，保持干净的文件结构。
        """
        Path(self.local_dir).mkdir(exist_ok=True, parents=True)
        is_file=False
        if [it for it in Path(self.local_dir).glob('*.bin')] or [it for it in Path(self.local_dir).glob('*.safetensors')]:
            is_file=True
        if is_file:
            self._signal(text=f"{self.model_name} has exists")
            print('已存在模型')
            return
        from huggingface_hub import snapshot_download
        self._signal(text=f"Downloading {self.model_name} ...")
        # 先测试能否连接 huggingface.co, 中国大陆地区不可访问，除非使用VPN
        try:
            requests.head('https://huggingface.co',timeout=5)
        except Exception:
            print('无法连接 huggingface.co, 使用镜像替换: hf-mirror.com')
            os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
            os.environ["HF_HUB_DISABLE_XET"] = "1"
        else:
            print('可以使用 huggingface.co')
            os.environ['HF_ENDPOINT'] = 'https://huggingface.co'
            os.environ["HF_HUB_DISABLE_XET"] = "0"
        try:
            snapshot_download(
                repo_id=self.model_name,
                local_dir=self.local_dir,
                local_dir_use_symlinks=False,
                endpoint=os.environ.get('HF_ENDPOINT'),
                ignore_patterns=["*.msgpack", "*.h5", ".git*"]
            )
        except Exception as e:
            raise RuntimeError(config.tr('downloading all files',self.local_dir)+f'\n[https://huggingface.co/{self.model_name}/tree/main]\n\n')

        """删除 huggingface_hub 下载时产生的缓存文件夹"""
        junk_paths = [
            ".cache",
            "blobs",
            "refs",
            "snapshots",
            ".no_exist"
        ]
        
        for junk in junk_paths:
            full_path = Path(self.local_dir) / junk
            if full_path.exists():
                try:
                    if full_path.is_dir():
                        shutil.rmtree(full_path) # 强制删除文件夹
                    else:
                        os.remove(full_path)     # 删除文件
                    print(f"已清理: {junk}")
                except Exception as e:
                    print(f"清理 {junk} 失败: {e}")
        self._signal(text=f"Downloaded ")




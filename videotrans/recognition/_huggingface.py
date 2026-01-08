# zh_recogn 识别
import re,sys,os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Union


from videotrans.configure import config
from videotrans.util import tools
from videotrans.recognition._base import BaseRecogn

import json,shutil,requests
from huggingface_hub import snapshot_download


@dataclass
class HuggingfaceRecogn(BaseRecogn):

    def __post_init__(self):
        super().__post_init__()
        self.local_dir=f'{config.ROOT_DIR}/models/models--'+self.model_name.replace('/','--')
        self._signal(text=f"use {self.model_name}")

    def _exec(self) -> Union[List[Dict], None]:
        if self._exit(): return
        self._signal(text=f"loading {self.model_name}")
        config.logger.debug(f'[HuggingfaceRecogn]_exec:{self.model_name=}')
        self._get_modeldir_download()
        result=[]
        if self.model_name in ['JhonVanced/whisper-large-v3-japanese-4k-steps-ct2','zh-plus/faster-whisper-large-v2-japanese-5k-steps','Systran/faster-whisper-tiny']:
            result=self._faster()
        else:
            #self.model_name in ['nvidia/parakeet-ctc-1.1b','biodatlab/whisper-th-medium','biodatlab/whisper-th-large-v3','kotoba-tech/kotoba-whisper-v2.0',,'suzii/vi-whisper-large-v3-turbo-v1','reazon-research/japanese-wav2vec2-large-rs35kh','jonatasgrosman/wav2vec2-large-xlsr-53-japanese']:
            result=self._pipe_asr()

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
    def _pipe_asr(self):
        from transformers import pipeline
        import torch
        import re

        # 1. 准备数据
        raws = self.cut_audio()

        # 定义输入生成器，直接把路径或音频数据喂给 pipeline
        def inputs_generator():
            for item in raws:
                yield item['file']

        # 2. 初始化 Pipeline
        # 使用 device_map="auto" 自动分配，或指定 device
        device_arg = 0 if self.is_cuda else -1
        # 注意：使用 device_map="auto" 时通常不需要传 device 参数，二者选一
        # 如果是单卡环境，直接传 device=0 效率通常比 device_map="auto" 稍微高一点点

        config.logger.info(f"Loading pipeline from {self.local_dir}")

        p = pipeline(
            task="automatic-speech-recognition",
            model=self.local_dir,
            batch_size=int(config.settings.get('batch_size', 8)),
            device=device_arg if not config.settings.get('use_device_map', False) else None,
            torch_dtype=torch.float16 if self.is_cuda else torch.float32,
        )

        config.logger.debug(f'Pipeline loaded on device={(p.model.device)}')

        # 3. 动态构建 generate_kwargs
        generate_kwargs = {}

        # 获取模型类型，例如 'whisper', 'wav2vec2', 'huBERT', 'parakeet' 等
        model_type = p.model.config.model_type
        is_whisper = "whisper" in model_type.lower()

        if is_whisper:
            # === Whisper 专用参数 ===
            lang = self.detect_language.split('-')[0] if self.detect_language != 'auto' else None

            generate_kwargs["task"] = "transcribe"
            if lang:
                generate_kwargs["language"] = lang

            # 处理 Prompt
            prompt_text = config.settings.get(f'initial_prompt_{self.detect_language}')
            if prompt_text:
                # 获取 tokenizer 并转换 prompt 为 token IDs
                # 兼容旧版本 transformers
                if hasattr(p.tokenizer, "get_prompt_ids"):
                    prompt_ids = p.tokenizer.get_prompt_ids(prompt_text, return_tensors="pt")
                else:
                    # 通用回退方案
                    prompt_ids = p.tokenizer(prompt_text, add_special_tokens=False, return_tensors="pt").input_ids

                # 确保 tensor 在正确的设备上
                if self.is_cuda:
                    prompt_ids = prompt_ids.to(p.model.device)

                # 注意：这里需要取 [0] 或者是 tensor 本身，取决于 pipeline 版本，
                # 通常传入 tensor 即可，但某些版本需要 list。
                # 安全起见，转为 tensor 传入通常是支持的，或者转为 list: prompt_ids.tolist()[0]
                generate_kwargs["prompt_ids"] = prompt_ids

        else:
            # === 其他架构 (如 Parakeet, Wav2Vec2) ===
            # 这些模型通常不需要 language 参数（或者是预定义好的），也不支持 prompt_ids
            pass

        # 4. 执行批量推理
        # 这里的 p(...) 返回的是一个迭代器，它会在后台进行 batch 处理
        results_iterator = p(
            inputs_generator(),
            generate_kwargs=generate_kwargs
        )

        total = len(raws)

        # 5. 收集结果
        # 注意：这里我们同时遍历 raws 和 results_iterator
        # 因为 inputs_generator 是按顺序 yield 的，results_iterator 也会按顺序输出
        for i, (it, res) in enumerate(zip(raws, results_iterator)):
            self._signal(text=f"subtitles {i+1}/{total}...")

            # ★★★ 修正点：千万不要在这里再次调用 p() ★★★
            # 此时 res 已经是字典 {'text': '...', 'chunks': ...}

            text = res.get('text', '')

            # 清理文件路径引用（如果需要）
            if 'file' in it:
                del it['file']

            if text:
                # 清理特殊标记
                cleaned_text = re.sub(r'<unk>|</unk>', '', text).strip()
                raws[i]['text'] = cleaned_text

                # 如果 pipeline 返回了时间戳（取决于 chunk_length_s 和 return_timestamps 参数）
                # 你可能需要在这里更新 it['start'] 和 it['end']，
                # 但因为你使用了 cut_audio() 预切分，通常使用 raws 里原有的时间戳即可。

                self._signal(text=f'{cleaned_text}\n', type="subtitle")

        # 清理显存
        del p
        return raws

    def _pipe_asr0(self):
        from transformers import pipeline
        import torch
        raws = self.cut_audio()
        p = pipeline(
            task="automatic-speech-recognition",
            model=self.local_dir,
            batch_size=8,
            device_map="cuda:0" if self.is_cuda else "auto",
            dtype=torch.float16 if self.is_cuda else torch.float32,
        )
        config.logger.debug(f'use device={(p.model.device)}')
        if self.model_name in ['nvidia/parakeet-ctc-1.1b']:
            generate_kwargs={}
        else:
            generate_kwargs={"language": self.detect_language.split('-')[0], "task": "transcribe"}
        def inputs_generator():
            for item in raws:
                yield item['file']
        results_iterator = p(
            inputs_generator(), 

            generate_kwargs=generate_kwargs,
            ignore_warning=True
        )     
        total = len(raws)

        for i, (it,res) in enumerate(zip(raws, results_iterator)):
            self._signal(text=f"subtitles {i+1}/{total}...")
            res=p(it['file'],ignore_warning=True,generate_kwargs=generate_kwargs)
            if 'file' in it:
                del it['file']

            if res.get('text'):
                it['text']=re.sub(r'<unk>|</unk>','',res['text'])
                self._signal(text=f'{it["text"]}\n', type="subtitle")       
        del p
        return raws
        
    # JhonVanced/whisper-large-v3-japanese-4k-steps-ct2','zh-plus/faster-whisper-large-v2-japanese-5k-steps  
    def _faster0(self):
        from faster_whisper import WhisperModel
        raws=self.cut_audio()
        model = WhisperModel(
                self.local_dir,
                device="cuda" if self.is_cuda else "auto"
        )
        for i,it in enumerate(raws):
            segments, info = model.transcribe(
                it['file'],
                beam_size=int(config.settings.get('beam_size',5)),
                best_of=int(config.settings.get('best_of',5)),
                no_speech_threshold=float(config.settings.get('no_speech_threshold',0.5)),
                condition_on_previous_text=bool(config.settings.get('condition_on_previous_text',False)),
                word_timestamps=False,
                vad_filter=False,   
                temperature=0,
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

    def _faster(self):
        prompt = config.settings.get(f'initial_prompt_{self.detect_language}') if self.detect_language != 'auto' else None
        raws = []
        self._signal(text=f"load {self.model_name}")

        # 引入 BatchedInferencePipeline
        import torch
        from faster_whisper import WhisperModel, BatchedInferencePipeline
        device_indices = list(range(torch.cuda.device_count())) if self.is_cuda else 0

        model = WhisperModel(
                self.local_dir,
                device="cuda" if self.is_cuda else "auto",
                device_index=device_indices,
                compute_type=config.settings.get('cuda_com_type', 'default')
            )


        self._signal(text=self.model_name + " Loaded")

        # 2. 准备 Batched Pipeline
        # 注意：这里实例化 Pipeline
        batched_model = BatchedInferencePipeline(model=model)

        last_end_time = self.speech_timestamps[-1][1] / 1000.0

        # 3. 转换时间戳格式
        # BatchedInferencePipeline 需要 [{'start': start_sec, 'end': end_sec}, ...]
        clip_timestamps_dicts = [
            {"start": it[0] / 1000.0, "end": it[1] / 1000.0}
            for it in self.speech_timestamps
        ]

        # 4. 执行批量推理
        # 使用 batched_model.transcribe
        segments, info = batched_model.transcribe(
            self.audio_file,
            batch_size=int(config.settings.get('batch_size', 8)), #
            beam_size=int(config.settings.get('beam_size', 5)),
            best_of=int(config.settings.get('best_of', 5)),
            # vad_filter 必须为 False，否则 clip_timestamps 可能被忽略或产生冲突，
            vad_filter=False,
            clip_timestamps=clip_timestamps_dicts, # 自定义分段
            condition_on_previous_text=bool(config.settings.get('condition_on_previous_text', False)),
            word_timestamps=False,
            language=self.detect_language.split('-')[0] if self.detect_language and self.detect_language != 'auto' else None,
            initial_prompt=prompt if prompt else None
        )

        for segment in segments:
            if segment.end > last_end_time:
                continue
            text = segment.text
            if not text.strip():
                continue
            s, e = int(segment.start*1000), int(segment.end*1000)
            tmp = {
                'text': text,
                'start_time': s,
                'end_time': e
            }

            tmp['startraw'] = tools.ms_to_time_string(ms=tmp['start_time'])
            tmp['endraw'] = tools.ms_to_time_string(ms=tmp['end_time'])
            tmp['time'] = f"{tmp['startraw']} --> {tmp['endraw']}"
            raws.append(tmp)
            self._signal(text=f'{text}\n', type="subtitle")
            self._signal(text=f' Subtitles {len(raws) + 1} ')

        try:
            if model:
                del model
            if 'batched_model' in locals():
                del batched_model
        except Exception:
            pass
        return raws


    def _progress_callback(self, data):
        """
        这个方法会被 tqdm 内部调用。
        在这里将数据压入队列。
        """
        msg_type = data.get("type")
        percent = data.get("percent")
        filename = data.get("filename")
        
        if msg_type == "file":
           
            # 标签显示当前文件名
            self._signal(text=f"{filename} {percent:.2f}%")
            
        else:
            # === 情况 B：这是总文件计数 (Fetching 4 files) ===
            # 不要更新进度条！否则会由 100% 突然跳回 25%
            # 建议只在某个副标签显示总进度，或者干脆忽略
            current_file_idx = data.get("current")
            total_files = data.get("total")
            
            self._signal(text=f"{current_file_idx}/{total_files} files")

    
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
        self._signal(text=f"Downloading {self.model_name} ...")
        # 先测试能否连接 huggingface.co, 中国大陆地区不可访问，除非使用VPN
        try:
            requests.head('https://huggingface.co',timeout=5)
        except Exception:
            print('无法连接 huggingface.co, 使用镜像替换: hf-mirror.com')
            endpoint = 'https://hf-mirror.com'
            os.environ["HF_HUB_DISABLE_XET"] = "1"
        else:
            print('可以使用 huggingface.co')
            endpoint = 'https://huggingface.co'
            os.environ["HF_HUB_DISABLE_XET"] = "0"
        try:
            MyTqdmClass = tools.create_tqdm_class(self._progress_callback)
            print(f'{self.model_name=}##################')
            snapshot_download(
                repo_id=self.model_name,
                local_dir=self.local_dir,
                local_dir_use_symlinks=False,
                endpoint=endpoint,
                etag_timeout=5,
                tqdm_class=MyTqdmClass,
                ignore_patterns=["*.msgpack", "*.h5", ".git*"]
            )
            self._signal(text="Downloaded end")
            
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




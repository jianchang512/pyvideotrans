import multiprocessing
import time,json
from dataclasses import dataclass, field
from pathlib import Path
from videotrans.configure import config
from videotrans.configure.config import tr, logs

from videotrans.recognition._base import BaseRecogn
from videotrans.task.simple_runnable_qt import run_in_threadpool

import os
from videotrans.process._iscache import _MODELS
import glob
import threading
from videotrans.util import tools


"""
faster-whisper
内置的本地大模型不重试
"""


@dataclass
class FasterAll(BaseRecogn):
    pidfile: str = field(default="", init=False)

    def __post_init__(self):
        super().__post_init__()

    def _create_from_huggingface(self, model_id, audio_file, language):
        from transformers import pipeline
        from huggingface_hub import snapshot_download
        from videotrans.process._iscache import check_huggingface_connect

        # 定义本地保存路径
        local_dir = f"{config.ROOT_DIR}/models/" + model_id.split("/")[-1]

        if not os.path.exists(local_dir) or len([it for it in Path(local_dir).glob('*')])<3:
            check_huggingface_connect(config.ROOT_DIR, self.proxy_str)
            print(f"下载模型到 {local_dir}...")
            # 使用 snapshot_download 下载完整模型
            snapshot_download(
                repo_id=model_id,
                local_dir=local_dir,
            )
            print(f"模型已保存到 {local_dir}")
        else:
            print(f"使用本地模型: {local_dir}")

        # 使用本地模型路径创建 pipeline
        asr_pipeline = pipeline(
            "automatic-speech-recognition",
            model=local_dir,
            feature_extractor=local_dir,  # Whisper 使用 feature_extractor
            tokenizer=local_dir,  # 明确指定 tokenizer
            chunk_length_s=30,
            device=self.device,
        )

        # 如果需要时间戳（用于字幕）
        generate_cfg={ "task": "transcribe"}
        if language and language!='auto':
            generate_cfg['language']=language
        result_with_timestamps = asr_pipeline(
            audio_file,
            generate_kwargs=generate_cfg,
            return_timestamps=True
        )

        # 打印分段结果
        raws=[]
        for segment in result_with_timestamps.get("chunks", []):
            start, end = segment["timestamp"]
            text = segment["text"]
            startraw = f"{int(start // 3600):02d}:{int(start // 60 % 60):02d}:{int(start % 60):02d},{int(start % 1 * 1000):03d}"
            endraw = f"{int(end // 3600):02d}:{int(end // 60 % 60):02d}:{int(end % 60):02d},{int(end % 1 * 1000):03d}"
            raws.append({
                "line": len(raws) + 1,
                "start_time": int(start*1000),
                "end_time": int(end*1000),
                "startraw": startraw,
                "endraw": endraw,
                "text": text
            })
        return raws


    # 获取新进程的结果
    def _get_signal_from_process(self, q: multiprocessing.Queue):
        while not self.has_done:
            try:
                if self._exit():
                    if Path(self.pidfile).exists():
                        Path(self.pidfile).unlink(missing_ok=True)
                    return
                data = q.get_nowait()
                if data:
                    self._signal(text=data['text'], type=data['type'])
            except Exception:
                pass
            time.sleep(1)



    def _exec(self):
        if self.model_name not in _MODELS:
            return self._create_from_huggingface(self.model_name, self.audio_file, self.detect_language)
        # 修复CUDA fork问题：强制使用spawn方法
        multiprocessing.set_start_method('spawn', force=True)

        while 1:
            if self._exit():
                return

            if config.model_process is not None:
                
                if len(glob.glob(config.TEMP_DIR + '/*.lock')) == 0:
                    config.model_process = None
                    break
                self._signal(text="wait...")
                time.sleep(0.5)
                continue
            break
        ctx = multiprocessing.get_context('spawn')
        # 创建队列用于在进程间传递结果
        result_queue = ctx.Queue()
        try:
            self.has_done = False
            
            self.error = ''
            from videotrans.process._overall import run
            with ctx.Manager() as manager:
                raws = manager.list([])
                err = manager.dict({"msg": ""})
                detect = manager.dict({"langcode": self.detect_language})
                # 使用ten-vad切割
                speech_timestamps=self.get_speech_timestamp(self.audio_file)
                
                process = ctx.Process(target=run, args=(raws, err, detect), kwargs={
                    "model_name": self.model_name,
                    "is_cuda": self.is_cuda,
                    "detect_language": self.detect_language,
                    "audio_file": self.audio_file,
                    "q": result_queue,
                    "proxy": self.proxy_str,
                    "TEMP_DIR":config.TEMP_DIR,
                    "defaulelang":config.defaulelang,
                    "settings":config.settings,
                    "split_type":self.split_type,
                    "whisper_type":self.recogn_type,
                    "speech_timestamps":speech_timestamps
                })
                # 等待进程执行完毕
                process.start()
                threading.Thread(target=self._get_signal_from_process,args=(result_queue,)).start()
                self.pidfile = config.TEMP_DIR + f'/{process.pid}.lock'
                logs(f'开始创建 pid:{self.pidfile=}')
                with open(self.pidfile, 'w', encoding='utf-8') as f:
                    f.write(f'{process.pid}')
                process.join()
                self._signal(text="STT end, hold on...")
                try:
                    if process.is_alive():
                        process.terminate()
                except Exception:
                    pass

                if err['msg']:
                    logs(f'{err["msg"]}',level='warn')
                    self.error=err['msg']
                else:
                    if self.detect_language == 'auto':
                        logs(f'需要自动检测语言，当前检测出的语言为{detect["langcode"]=}')
                        self.detect_language = detect.get('langcode','auto')
        
                    return self.get_srtlist(raws)
        except Exception as e:
            logs(f'{e}', level="except")
            self.error = str(e)
        finally:
            config.model_process = None
            self.has_done = True

        
        if self.error:
            raise RuntimeError(str(self.error))
        
        err=tr('No speech was detected, please make sure there is human speech in the selected audio/video and that the language is the same as the selected one.')
        if not self.is_cuda:
            raise RuntimeError(err)
        
        raise RuntimeError(err+' '+tr('Please also check whether CUDA12.8 and cudnn9 are installed correctly.'))
            
    def get_srtlist(self, raws):
        
        if self.jianfan:
            import zhconv
        srt_raws = []
        raws=list(raws)
        Path("test-0.json").write_text(json.dumps(raws,indent=4,ensure_ascii=False),encoding='utf-8')
        raws_len=len(raws)
        for idx,it in enumerate(raws):
            if not it['text'].strip():
                continue
            if self.jianfan:
                self._signal(text=f"简繁转换中 [{idx+1}/{raws_len}]...")
            s,e=int(it['start']*1000),int(it['end']*1000)
            text=zhconv.convert(it['text'], 'zh-hans') if self.jianfan else it['text']
            
            tmp = {
                'text': text,
                'start_time': s,
                'end_time': e
            }

            tmp['startraw'] = tools.ms_to_time_string(ms=tmp['start_time'])
            tmp['endraw'] = tools.ms_to_time_string(ms=tmp['end_time'])
            tmp['time'] = f"{tmp['startraw']} --> {tmp['endraw']}"
            srt_raws.append(tmp)
        
        return srt_raws
        
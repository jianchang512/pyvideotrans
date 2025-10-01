import multiprocessing
import time
from dataclasses import dataclass, field
from pathlib import Path
from videotrans.configure import config

from videotrans.process._overall import run
from videotrans.recognition._base import BaseRecogn
from videotrans.task.simple_runnable_qt import run_in_threadpool

"""
faster-whisper
openai-whisper
funasr
内置的本地大模型不重试
"""


@dataclass
class FasterAll(BaseRecogn):
    pidfile: str = field(default="", init=False)

    def __post_init__(self):
        super().__post_init__()

        if self.detect_language and self.detect_language[:2].lower() in ['zh', 'ja', 'ko', 'yu']:
            self.flag.append(" ")
            self.maxlen = int(config.settings.get('cjk_len', 20))
        else:
            self.maxlen = int(config.settings.get('other_len', 60))

    def _create_from_huggingface(self, model_id, audio_file, language):
        from transformers import pipeline
        from huggingface_hub import snapshot_download
        import os
        from videotrans.process._iscache import _check_huggingface_connect

        # 设置代理（如果需要）
        # os.environ['https_proxy'] = 'http://127.0.0.1:10808'

        # 定义本地保存路径
        local_dir = f"{config.ROOT_DIR}/models/" + model_id.split("/")[-1]

        if not os.path.exists(local_dir) or len([it for it in Path(local_dir).glob('*')])<3:
            _check_huggingface_connect(config.ROOT_DIR, self.proxy_str)
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
            print(f"[{start:.2f}s - {end:.2f}s] {text}")
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
                if self._exit() and self.pidfile and Path(self.pidfile).exists():
                    Path(self.pidfile).unlink(missing_ok=True)
                    return
                if not q.empty():
                    data = q.get_nowait()
                    if self.inst and self.inst.precent < 50:
                        self.inst.precent += 0.1

                    if data:
                        if self.inst and self.inst.status_text and data['type'] == 'logs':
                            self.inst.status_text = data['text']
                        self._signal(text=data['text'], type=data['type'])
            except:
                pass
            time.sleep(0.1)



    def _exec(self):
        from videotrans.process._iscache import _MODELS
        if self.model_name not in _MODELS and "faster" not in self.model_name:
            return self._create_from_huggingface(self.model_name, self.audio_file, self.detect_language)
        # 修复CUDA fork问题：强制使用spawn方法
        multiprocessing.set_start_method('spawn', force=True)

        while 1:
            if self._exit():
                return

            if config.model_process is not None:
                import glob
                if len(glob.glob(config.TEMP_DIR + '/*.lock')) == 0:
                    config.model_process = None
                    break
                self._signal(text="等待另外进程退出")
                time.sleep(1)
                continue
            break

        ctx = multiprocessing.get_context('spawn')
        # 创建队列用于在进程间传递结果
        result_queue = ctx.Queue()
        try:
            self.has_done = False
            run_in_threadpool(self._get_signal_from_process,result_queue)
            self.error = ''
            with ctx.Manager() as manager:
                raws = manager.list([])
                err = manager.dict({"msg": ""})
                detect = manager.dict({"langcode": self.detect_language})
                # 创建并启动新进程
                process = ctx.Process(target=run, args=(raws, err, detect), kwargs={
                    "model_name": self.model_name,
                    "is_cuda": self.is_cuda,
                    "detect_language": self.detect_language,
                    "audio_file": self.audio_file,
                    "q": result_queue,
                    "settings": config.settings,
                    "defaulelang": config.defaulelang,
                    "ROOT_DIR": config.ROOT_DIR,
                    "TEMP_DIR": config.TEMP_DIR,
                    "proxy": self.proxy_str
                })
                process.start()
                self.pidfile = config.TEMP_DIR + f'/{process.pid}.lock'
                config.logger.info(f'开始创建 pid:{self.pidfile=}')
                with open(self.pidfile, 'w', encoding='utf-8') as f:
                    f.write(f'{process.pid}')
                # 等待进程执行完毕
                process.join()
                if err['msg']:
                    self.error = str(err['msg'])
                elif len(list(raws))>0:
                    self.error = ''
                    if self.detect_language == 'auto' and self.inst and hasattr(self.inst, 'set_source_language'):
                        config.logger.info(f'需要自动检测语言，当前检测出的语言为{detect["langcode"]=}')
                        self.detect_language = detect['langcode']

                    if not config.settings['rephrase']:
                        self.get_srtlist(raws)
                    else:
                        try:
                            words_list = []
                            for it in list(raws):
                                words_list += it['words']
                            self._signal(text="正在重新断句..." if config.defaulelang == 'zh' else "Re-segmenting...")
                            self.raws = self.re_segment_sentences(words_list)
                        except:
                            self.get_srtlist(raws)
                try:
                    if process.is_alive():
                        process.terminate()
                except:
                    pass
        except (KeyError,IndexError,NameError) as e:
            config.logger.exception(f'{e}', exc_info=True)
            self.error = e
        except Exception as e:
            config.logger.exception(f'{e}', exc_info=True)
            self.error = e
        finally:
            config.model_process = None
            self.has_done = True

        if not self.error and len(self.raws) > 0:
            return self.raws

        if self.error:
            raise self.error if isinstance(self.error,Exception) else RuntimeError(self.error)
        raise RuntimeError(f"没有识别到任何说话声,请确认所选音视频中是否包含人类说话声，以及说话语言是否同所选一致 {',请尝试取消选中CUDA加速后重试' if self.is_cuda else ''}" if config.defaulelang == 'zh' else "No speech was detected, please make sure there is human speech in the selected audio/video and that the language is the same as the selected one.")

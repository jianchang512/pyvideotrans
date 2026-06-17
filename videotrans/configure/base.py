import base64
import json
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from videotrans.configure.config import tr, settings, app_cfg, logger, push_queue, TEMP_ROOT



from videotrans.task.taskcfg import SignMsg

from videotrans.util.help_misc import set_proxy,vail_file

@dataclass
class BaseCon:
    # 每个任务唯一的uuid
    uuid: Optional[str] = field(default=None, init=False)
    # 用于其他需要直接代理字符串
    proxy_str: str = ''
    last_down_time:int=0


    def __post_init__(self):
        # 获取代理
        self.proxy_str = self._set_proxy(type='set')

    def _exit(self) -> bool:
        if app_cfg.exit_soft or (self.uuid and self.uuid in app_cfg.stoped_uuid_set):
            return True
        return False
    # 所有窗口和任务信息通过队列交互
    def signal(self, **kwargs):
        if app_cfg.exit_soft: return
        if app_cfg.exec_mode=='cli':
            print(kwargs.get('text'))
            return
        if 'uuid' not in kwargs or not kwargs.get('uuid'):
            kwargs['uuid'] = self.uuid
        # 已停止，则不再发送消息
        if kwargs.get('uuid') in app_cfg.stoped_uuid_set:
            return
        if 'type' not in kwargs or not kwargs.get('type'):
            kwargs['type']='logs'

        push_queue(kwargs.get('uuid') or "", SignMsg(**kwargs))

    def _process_callback(self, data):
        _t=time.time()
        if _t-self.last_down_time<1:
            return
        self.last_down_time=_t
        
        if isinstance(data, str):
            return self.signal(text=tr('Downloading please wait') + data)
        if not isinstance(data, dict):
            return
        msg_type = data.get("type")
        percent = data.get("percent")
        filename = data.get("filename")

        if msg_type == "file":
            self.signal(text=f"{tr('Downloading please wait')} {filename} {percent:.2f}%")
        else:
            current_file_idx = data.get("current")
            total_files = data.get("total")

            self.signal(text=f" {tr('Downloading please wait')} {current_file_idx}/{total_files} files")

    # 设置、获取代理
    def _set_proxy(self, type='set'):
        if type == 'del':
            os.environ['bak_proxy'] = app_cfg.proxy or os.environ.get('HTTP_PROXY') or os.environ.get('HTTPS_PROXY')
            app_cfg.proxy = ''
            os.environ.pop('HTTPS_PROXY', None)
            os.environ.pop('HTTP_PROXY', None)
            return None

        if type == 'set':
            raw_proxy = app_cfg.proxy or os.environ.get('HTTPS_PROXY') or os.environ.get('HTTP_PROXY')
            if raw_proxy:
                app_cfg.proxy = raw_proxy
                return raw_proxy
            if not raw_proxy:

                proxy = set_proxy() or os.environ.get('bak_proxy')
                if proxy:
                    os.environ['HTTP_PROXY'] = proxy
                    os.environ['HTTPS_PROXY'] = proxy
                app_cfg.proxy = proxy
                return proxy
        return None


    # 语音合成后统一转为 wav 音频,方便后续变速等处理
    def convert_to_wav(self, mp3_file_path: str, output_wav_file_path: str, extra=None):
        if app_cfg.exit_soft or not vail_file(mp3_file_path):
            return
        cmd = [
            "-y",
            "-i",
            mp3_file_path,
            "-ar",
            "48000",
            "-ac",
            "2",
            "-c:a",
            "pcm_s16le"
        ]
        if extra:
            cmd += extra
        cmd += [
            output_wav_file_path
        ]
        try:
            from videotrans.util.help_ffmpeg import runffmpeg,remove_silence_wav
            runffmpeg(cmd, force_cpu=True)
            if settings.get('remove_dubb_silence', True):
                remove_silence_wav(output_wav_file_path)
        except Exception as e:
            logger.exception(f'转为 48k wav时失败，跳过{e}',exc_info=True)
            return False
        return True


    def _base64_to_audio(self, encoded_str: str, output_path: str) -> None:
        if not encoded_str:
            raise ValueError("Base64 encoded string is empty.")
        from videotrans.util.help_ffmpeg import runffmpeg
        # 如果存在data前缀，则按照前缀中包含的音频格式保存为转换格式
        if encoded_str.startswith('data:audio/'):
            output_ext = Path(output_path).suffix.lower()[1:]
            mime_type, encoded_str = encoded_str.split(',', 1)  # 提取 Base64 数据部分
            # 提取音频格式 (例如 'mp3', 'wav')
            audio_format = mime_type.split('/')[1].split(';')[0].lower()
            support_format = {
                "mpeg": "mp3",
                "wav": "wav",
                "ogg": "ogg",
                "aac": "aac"
            }
            base64data_ext = support_format.get(audio_format, "")
            if base64data_ext and base64data_ext != output_ext:
                # 格式不同需要转换格式
                # 将base64编码的字符串解码为字节
                wav_bytes = base64.b64decode(encoded_str)
                # 将解码后的字节写入文件
                with open(output_path + f'.{base64data_ext}', "wb") as wav_file:
                    wav_file.write(wav_bytes)

                runffmpeg([
                    "-y", "-i", output_path + f'.{base64data_ext}', "-b:a", "128k", output_path
                ])
                return
        # 将base64编码的字符串解码为字节
        wav_bytes = base64.b64decode(encoded_str)
        # 将解码后的字节写入文件
        with open(output_path, "wb") as wav_file:
            wav_file.write(wav_bytes)

    def _audio_to_base64(self, file_path: str):
        if not file_path or not Path(file_path).exists():
            return None
        with open(file_path, "rb") as wav_file:
            wav_content = wav_file.read()
            base64_encoded = base64.b64encode(wav_content)
            return base64_encoded.decode("utf-8")

    def _signal_of_process(self, logs_file,status_dict=None):
        last_mtime = 0
        timeout = 0
        while 1:
            if app_cfg.exit_soft: return
            if status_dict and status_dict['is_end']:
                return
            timeout += 1
            if timeout > 3600:
                logger.warning(f'新进程已执行3600s仍未终止，可能已出错: {logs_file}')
                return
            _p = Path(logs_file)
            # 已删掉
            if last_mtime > 0 and not _p.exists():
                return
            try:
                if not _p.exists():
                    time.sleep(1)
                    continue
                # 获取日志文件最后修改时间
                _mtime = _p.stat().st_mtime
                if _mtime == last_mtime:
                    # 自上次未修改过
                    time.sleep(1)
                    continue
                last_mtime = _mtime
                timeout=0
                _content = _p.read_text(encoding='utf-8')
                if not _content:
                    time.sleep(1)
                    continue
                _tmp = json.loads(_content)
                if _tmp.get('type', '') == 'error':
                    return
                self.signal(text=_tmp.get('text', ''), type=_tmp.get('type', 'logs'))
            except Exception:
                # 可能日志文件读取出错，可忽略
                logger.warning(f'读取进程间临时文件出错，可能已清理，可忽略:{logs_file}')
            time.sleep(1)

    # 使用新进程执行任务
    def _new_process(self, callback=None, title="", is_cuda=False, kwargs=None):
        _st = time.time()
        from .excepts import VideoTransError,SttTimeoutError
        from concurrent.futures.process import BrokenProcessPool
        from videotrans.process.signelobj import GlobalProcessManager
        kwargs = kwargs or {}
        self.signal(text=f'[{title}] starting...')
        logger.debug(f'[新进程任务 开始:{title=}]')

        # 提交任务，并显式传入参数，确保子进程拿到正确的参数
        logs_file = kwargs.get('logs_file',f'{TEMP_ROOT}/{_st}.log')
        device_index = 0
        status_dict={"is_end":False}
        try:
            Path(logs_file).touch()
            threading.Thread(target=self._signal_of_process, args=(logs_file,status_dict), daemon=True).start()
            # 再次判断cuda是否有效，防止预先获取失败
            if is_cuda:
                import torch
                if not torch.cuda.is_available():
                    is_cuda = False

            # 如果使用gpu，则获取可用 device_index
            if is_cuda:
                # 启用了多显卡模式
                if settings.get('multi_gpus'):
                    from videotrans.util.gpus import get_cudaX
                    device_index = get_cudaX()
                if device_index == -1:
                    is_cuda = False
                    kwargs['is_cuda'] = False
                    logger.error(f'已启用CUDA但未检测到可用显卡，强制使用CPU')
                kwargs['device_index'] = max(device_index, 0)
            logger.debug(f'新进程任务 参数:{kwargs=}')
            future = GlobalProcessManager.submit_task_cpu(
                callback,
                **kwargs
            ) if not is_cuda else GlobalProcessManager.submit_task_gpu(
                callback,
                **kwargs
            )

            _timeout=0
            while not future.done():
                if app_cfg.exit_soft:
                    return None
                # faster-whisper 在工作完成后退出时，偶发可能静默崩溃，主进程无法捕获，导致永久等待
                # 在退出前预先将识别结果保存到 subtitle_srt 文件中，再返回，此处通过检测文件存在确保崩溃后仍能继续运行
                if kwargs.get('subtitle_srt') and Path(kwargs.get('subtitle_srt')).exists():
                    # 已返回10s仍在循环，子进程可能已崩溃
                    if _timeout>20:
                        status_dict['is_end']=True
                        logger.warning(f'faster-whisper 已生成字幕超过 {_timeout}s, 仍在循环，子进程可能已崩溃，强制抛出 SttTimeoutError')
                        raise SttTimeoutError("STT timeout")
                    _timeout+=1
                time.sleep(1)
            data,err = future.result(timeout=10)
            logger.debug(f'[新进程任务 {title=}] 已返回')
            status_dict['is_end']=True
            if err or not data:
                raise VideoTransError(err)
            self.signal(text=f'[{title}] end: {int(time.time() - _st)}s')
            return data
        except SttTimeoutError:
            raise
        except BrokenProcessPool as e:
            _model = ''
            _cuda = ''
            if kwargs.get('model_name'):
                _model = ' Model:' + kwargs.get('model_name')
            if is_cuda and device_index > -1:
                _cuda = f" GPU{device_index}"
            logger.exception(f'{title}: {_model}{_cuda}, {kwargs=},{e}', exc_info=True)
            raise VideoTransError(f'{_model}{_cuda} {e}')
        except BaseException as e:
            logger.exception(f'{title},{e}', exc_info=True)
            raise
        finally:
            status_dict['is_end']=True
            try:
                logger.debug(f'[新进程任务 结束:{title=}]，耗时{time.time()-_st}s')
                if logs_file:
                    Path(logs_file).unlink(missing_ok=True)
            except OSError:
                pass

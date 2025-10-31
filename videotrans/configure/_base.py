import base64
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from videotrans.configure import config
from videotrans.configure.config import tr
from videotrans.util import tools


@dataclass
class BaseCon:
    # 每个任务唯一的uuid
    uuid: Optional[str] = field(default=None, init=False)
    # 用于其他需要直接代理字符串
    proxy_str: str = ''
    # 不需要代理的host
    no_proxy: str = ''

    def __post_init__(self):
        self.proxy_str = self._set_proxy(type='set')
        print(f'{self.proxy_str=}')
        config.settings=config.parse_init()
        # 用于 requests 库
        # 国内某些渠道禁止国外ip及代理
        # 本地类型地址禁止使用代理
        self.no_proxy = "tmt.tencentcloudapi.com,api.fanyi.baidu.com,mt.cn-hangzhou.aliyuncs.com,openspeech.bytedance.com,api.minimaxi.com,api.deepseek.com,modelscope.cn,www.modelscope.cn,127.0.0.1,localhost,0.0.0.0,127.0.0.0,127.0.0.2"

        if self.proxy_str:
            os.environ['HTTPS_PROXY'] = self.proxy_str
            os.environ['HTTP_PROXY'] = self.proxy_str
            config.proxy = self.proxy_str
        else:
            config.proxy = None
            os.environ.pop('HTTPS_PROXY',None)
            os.environ.pop('HTTP_PROXY',None)

        os.environ['no_proxy'] = self.no_proxy

    # 所有窗口和任务信息通过队列交互
    def _signal(self, **kwargs):
        from . import config
        if 'uuid' not in kwargs:
            kwargs['uuid'] = self.uuid
        if not config.exit_soft:
            tools.set_process(**kwargs)

    # 设置、获取代理
    def _set_proxy(self, type='set'):
        if type == 'del':
            from . import config
            os.environ['bak_proxy'] = config.proxy or os.environ.get('HTTP_PROXY') or os.environ.get('HTTPS_PROXY')
            config.proxy = None
            os.environ.pop('HTTPS_PROXY',None)
            os.environ.pop('HTTP_PROXY',None)

            return None

        if type == 'set':
            from . import config
            raw_proxy = config.proxy or os.environ.get('HTTPS_PROXY') or os.environ.get('HTTP_PROXY')
            if raw_proxy:
                config.proxy=raw_proxy
                return raw_proxy
            if not raw_proxy:
                proxy = tools.set_proxy() or os.environ.get('bak_proxy')
                if proxy:
                    os.environ['HTTP_PROXY'] = proxy
                    os.environ['HTTPS_PROXY'] = proxy
                config.proxy=raw_proxy
                return proxy
        return None

    # 调用 faster-xxl.exe
    def _external_cmd_with_wrapper(self, cmd_list=None):
        if not cmd_list:
            raise ValueError("cmd_list is None")
        from . import config

        try:
            subprocess.run(cmd_list, capture_output=True, text=True, check=True, encoding='utf-8', creationflags=0,
                           cwd=os.path.dirname(cmd_list[0]))
        except subprocess.CalledProcessError as e:
            if os.name == 'nt' and config.IS_FROZEN:
                raise RuntimeError(tr('Currently Faster-Whisper-XXL cannot be used in the packaged version. Please deploy the source code or use Faster-Whisper-XXL transcription separately.'))
            raise RuntimeError(e.stderr)

    # 语音合成后统一转为 wav 音频
    def convert_to_wav(self, mp3_file_path: str, output_wav_file_path: str, extra=None):
        from . import config
        if config.exit_soft:
            return
        cmd = [
            "-y",
            "-i",
            mp3_file_path,
            "-ar",
            "44100",
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
        if config.exit_soft:
            return
        try:
            return tools.runffmpeg(cmd, force_cpu=True)
        except Exception:
            pass

    # 判断是否为内网地址
    def _get_internal_host(self, url: str):
        from urllib.parse import urlparse
        import ipaddress
        """
        检查 URL 的主机是否为内网地址。
    
        - 如果是内网地址（私有、环回、未指定），则返回其 "host:port" 字符串。
        - 如果是 'localhost'，同样返回 "localhost:port" 字符串。
        - 如果不是内网地址或 URL 无效，则返回 False。
    
        Args:
            url: 需要检查的 URL 字符串。
    
        Returns:
            str | bool: 如果是内网地址则返回其网络位置 (netloc)，否则返回 False。
        """
        try:
            parsed_url = urlparse(url)
            hostname = parsed_url.hostname

            # 如果 URL 中没有主机名 (例如 "path/only")，则直接返回 False
            if not hostname:
                return False

            # 1. 优先处理 'localhost' 字符串
            if hostname.lower() == 'localhost':
                return parsed_url.netloc  # 返回 'localhost:port'

            # 2. 尝试将主机名解析为 IP 地址
            ip_addr = ipaddress.ip_address(hostname)

            # 3. 判断 IP 地址类型
            # is_private: 10/8, 172.16/12, 192.168/16
            # is_loopback: 127/8
            # is_unspecified: 0.0.0.0
            if ip_addr.is_private or ip_addr.is_loopback or ip_addr.is_unspecified:
                return parsed_url.netloc  # 返回 'ip:port'

        except ValueError:
            # 如果 hostname 是一个域名 (如 www.google.com) 而不是 IP，
            # ipaddress.ip_address(hostname) 会抛出 ValueError。
            # 这种情况我们认为它不是内网地址。
            return False

        # 如果是公网 IP (如 8.8.8.8)，不满足任何条件，最终返回 False
        return False

    # 判断 api_url 如果是内网地址，则将 host 加入 no_proxy,避免 requests 使用代理访问
    def _add_internal_host_noproxy(self, api_url=''):
        host = self._get_internal_host(api_url)
        if host is not False:
            self.no_proxy += f',{host}'
            os.environ['no_proxy'] = self.no_proxy

    def _base64_to_audio(self, encoded_str: str, output_path: str) -> None:
        if not encoded_str:
            raise ValueError("Base64 encoded string is empty.")
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

                tools.runffmpeg([
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

# videotrans/tts/_indextts2.py

import requests
import tempfile
from pathlib import Path

from videotrans.configure import config
from videotrans.tts._base import BaseTTS

class IndexTTS2(BaseTTS):
    def __post_init__(self):
        super().__post_init__()
        self.api_url = config.params.get("indextts2_url", "").strip().rstrip('/')
        if not self.api_url.startswith('http'):
            self.api_url = f'http://{self.api_url}'
        self.session = requests.Session()
        config.logger.info(f"成功初始化 Index-TTS2 客户端，目标地址: {self.api_url}")

    def _item_task(self, data_item):
        text = data_item['text'].strip()
        # role 变量始终是纯净的角色名, 例如 "clone" 或 "01_nan.wav"
        role = data_item['role'] 
        config.logger.info(f"[TTS] Index-TTS2: text='{text}', role='{role}'")

        # --- 文件存在性验证 (仍然使用完整路径) ---
        if role == "clone":
            ref_wav_path = data_item.get('ref_wav')
            if not ref_wav_path or not Path(ref_wav_path).exists():
                self.error = "错误：选择了 'clone' 角色，但未提供有效的视频原声音频文件。"
                config.logger.error(self.error)
                return
        else:
            speaker_path = Path(config.ROOT_DIR) / "f5-tts" / role
            if not speaker_path.exists():
                self.error = f"错误：在 f5-tts 文件夹中未找到参考音频 {role}"
                config.logger.error(self.error)
                return
        
        # --- 构建API参数 (使用纯净的角色名) ---
        # 最终修正：无论是什么情况，传递给 'speaker' 参数的都应该是纯净的 role 名称
        # 这可以避免URL中出现完整路径和引号，与浏览器测试成功的方式保持一致
        params = {
            'text': text,
            'speaker': role, # <-- 这里是决定性的一行修改！
            'emo': '平静'
        }
        
        try:
            response = self.session.get(f"{self.api_url}/", params=params, timeout=120)

            if response.status_code != 200 or 'audio' not in response.headers.get('Content-Type', ''):
                self.error = f"Index-TTS2 API 错误: {response.status_code}, 服务器返回: {response.text[:100]}"
                config.logger.error(self.error)
                return
            
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_file.write(response.content)
                tmp_raw_audio_path = tmp_file.name
            
            self.convert_to_wav(tmp_raw_audio_path, data_item['filename'])
            Path(tmp_raw_audio_path).unlink()

            self.error = ''
            self.has_done += 1
            self._signal(text=f'配音 {self.has_done}/{self.len}')

        except requests.exceptions.RequestException as e:
            self.error = f"连接 Index-TTS2 API 时发生网络错误: {e}"
            config.logger.error(self.error)
            return
import base64
import os
import time
from pathlib import Path

import requests

from videotrans.configure import config
from videotrans.util import tools


def wav_to_base64(file_path):
    if not file_path or not Path(file_path).exists():
        return None
    with open(file_path, "rb") as wav_file:
        wav_content = wav_file.read()
        base64_encoded = base64.b64encode(wav_content)
        return base64_encoded.decode("utf-8")


def get_voice(*, text=None, role=None, rate=None, volume="+0%", pitch="+0Hz", language=None, filename=None, set_p=True,
              inst=None, uuid=None):
    try:
        api_url = config.params['fishtts_url'].strip().rstrip('/').lower()
        if len(config.params['fishtts_url'].strip()) < 10:
            raise Exception(
                'FishTTS API 接口不正确，请到设置中重新填写' if config.defaulelang == 'zh' else 'FishTTS API interface is not correct, please go to Settings to fill in again')
        api_url = 'http://' + api_url.replace('http://', '')
        config.logger.info(f'FishTTS API:{api_url}')
        text = text.strip()
        if not text:
            return True
        data = {"text": text, }
        if role:
            roledict = tools.get_fishtts_role()
            if role in roledict:
                data.update(roledict[role])
        # role=clone是直接复制
        # 克隆声音
        if os.path.exists(f'{config.ROOT_DIR}/{data["reference_audio"]}'):
            data['reference_audio'] = wav_to_base64(f'{config.ROOT_DIR}/{data["reference_audio"]}')
        elif os.path.exists(f'{config.ROOT_DIR}/fishwavs/{data["reference_audio"]}'):
            data['reference_audio'] = wav_to_base64(f'{config.ROOT_DIR}/fishwavs/{data["reference_audio"]}')

        response = requests.post(f"{api_url}", json=data, proxies={"http": "", "https": ""}, timeout=3600)
        if response.status_code != 200:
            raise response.json()
        # 如果是WAV音频流，获取原始音频数据
        with open(filename + ".wav", 'wb') as f:
            f.write(response.content)
        time.sleep(1)
        if not os.path.exists(filename + ".wav"):
            raise Exception(f'FishTTS合成声音失败-2:{text=}')
        tools.wav2mp3(filename + ".wav", filename)
        if os.path.exists(filename + ".wav"):
            os.unlink(filename + ".wav")
        if tools.vail_file(filename) and config.settings['remove_silence']:
            tools.remove_silence_from_end(filename)
        if set_p:
            if inst and inst.precent < 80:
                inst.precent += 0.1
            tools.set_process(f'{config.transobj["kaishipeiyin"]} ', uuid=uuid)
        else:
            raise Exception(f"FishTTS合成声音出错-3：{text=},{response.text=}")
    except requests.ConnectionError as e:
        raise Exception(str(e))
    except Exception as e:
        error = str(e)
        if set_p:
            tools.set_process(error, uuid=uuid)
        config.logger.error(f"{error}")
        raise
    return True

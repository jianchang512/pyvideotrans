import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Union

from gradio_client import Client, handle_file
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log, \
    RetryError

from videotrans import tts
from videotrans.configure import config
from videotrans.configure._except import NO_RETRY_EXCEPT, StopRetry
from videotrans.configure.config import tr
from videotrans.tts._base import BaseTTS
from videotrans.util import tools
from pydub import AudioSegment


RETRY_NUMS = 2
RETRY_DELAY = 5


@dataclass
class F5TTS(BaseTTS):
    v1_local: bool = field(init=False)

    def __post_init__(self):
        super().__post_init__()
        if self.tts_type==tts.DIA_TTS:
            api_url=config.params.get('diatts_url', '')
        elif self.tts_type==tts.INDEX_TTS:
            api_url=config.params.get('indextts_url', '')
        elif self.tts_type==tts.VOXCPM_TTS:
            api_url=config.params.get('voxcpmtts_url', '')
        elif self.tts_type==tts.SPARK_TTS:
            api_url=config.params.get('sparktts_url', '')
        else:
            api_url=config.params.get('f5tts_url', '')
        api_url = api_url.strip().rstrip('/').lower()
        self.api_url = f'http://{api_url}' if not api_url.startswith('http') else api_url
        self.v1_local = True
        sepflag = self.api_url.find('/', 9)
        if sepflag > -1:
            self.api_url = self.api_url[:sepflag]

        # 返回 不是 False，则为内网地址，将代理重设为 None
        if self.proxy_str and self._get_internal_host is not False:
            self.proxy_str=None
        self.client=None


    def _exec(self):
        self._local_mul_thread()

    def _item_task_v1(self, data_item: Union[Dict, List, None]):
        if self._exit() or tools.vail_file(data_item['filename']):
            return
        speed = 1.0
        try:
            speed = 1 + float(self.rate.replace('%', '')) / 100
        except ValueError:
            pass

        text = data_item['text'].strip()
        role = data_item['role']
        data = {'ref_text': '', 'ref_wav': ''}

        if role == 'clone':
            data['ref_wav'] = data_item.get('ref_wav','')
            data['ref_text'] = data_item.get('ref_text').strip()
        else:
            roledict = tools.get_f5tts_role()
            if role in roledict:
                data['ref_text'] = roledict[role]['ref_text']
                data['ref_wav'] = config.ROOT_DIR + f"/f5-tts/{role}"

        if not data.get('ref_wav') or not Path(data.get('ref_wav')).exists():
            raise StopRetry(tr('The role {} does not exist',role))
        ref_wav_audio=AudioSegment.from_file(data.get('ref_wav'))
        if len(ref_wav_audio)>12000:
            ref_wav_audio[:12000].export(data.get('ref_wav'))
        
        if data['ref_text'] and len(data['ref_text']) < 10:
            speed = 0.5

        result = self.client.predict(
            ref_audio_input=handle_file(data['ref_wav']),
            ref_text_input=data['ref_text'],
            gen_text_input=text,
            remove_silence=True,
            randomize_seed=True,
            seed_input=0,  # 开启随机后，这个数字会被忽略，填多少都行
            cross_fade_duration_slider=0.0, # 默认交叉淡入淡出时长
            nfe_slider=32,            # 默认推理步数，F5-TTS 推荐 32


            speed_slider=speed,
            api_name='/basic_tts'
        )

        config.logger.debug(f'result={result}')
        wav_file = result[0] if isinstance(result, (list, tuple)) and result else result
        if isinstance(wav_file, dict) and "value" in wav_file:
            wav_file = wav_file['value']
        if isinstance(wav_file, str) and Path(wav_file).is_file():
            self.convert_to_wav(wav_file, data_item['filename'])
        else:
            raise RuntimeError(str(result))

    def _item_task_spark(self, data_item: Union[Dict, List, None]):
        if self._exit() or tools.vail_file(data_item['filename']):
            return
        speed = 1.0
        try:
            speed = 1 + float(self.rate.replace('%', '')) / 100
        except ValueError:
            pass

        text = data_item['text'].strip()
        role = data_item['role']
        data = {'ref_text': '', 'ref_wav': ''}

        if role == 'clone':
            data['ref_wav'] = data_item.get('ref_wav','')
            data['ref_text'] = data_item.get('ref_text', '')
        else:
            roledict = tools.get_f5tts_role()
            if role in roledict:
                data['ref_wav'] = config.ROOT_DIR + f"/f5-tts/{role}"
                data['ref_text'] = roledict[role].get('ref_text','')

        if not data['ref_wav'] or not Path(data['ref_wav']).exists():
            raise StopRetry(tr('The role {} does not exist',role))

        result = self.client.predict(
            text=text,
            prompt_text=data['ref_text'],
            prompt_wav_upload=handle_file(data['ref_wav']),
            prompt_wav_record=None,
            api_name='/voice_clone'
        )

        config.logger.debug(f'result={result}')
        wav_file = result[0] if isinstance(result, (list, tuple)) and result else result
        if isinstance(wav_file, dict) and "value" in wav_file:
            wav_file = wav_file['value']
        if isinstance(wav_file, str) and Path(wav_file).is_file():
            self.convert_to_wav(wav_file, data_item['filename'])
        else:
            raise RuntimeError(str(result))

    def _item_task_index(self, data_item: Union[Dict, List, None]):
        if self._exit() or tools.vail_file(data_item['filename']):
            return
        speed = 1.0
        try:
            speed = 1 + float(self.rate.replace('%', '')) / 100
        except ValueError:
            pass

        text = data_item['text'].strip()
        role = data_item['role']
        data = {'ref_wav': ''}

        if role == 'clone':
            data['ref_wav'] = data_item.get('ref_wav','')
        else:
            roledict = tools.get_f5tts_role()
            if role in roledict:
                data['ref_wav'] = config.ROOT_DIR + f"/f5-tts/{role}"

        if not data['ref_wav'] or not Path(data['ref_wav']).exists():
            raise StopRetry(tr('The role {} does not exist',data['ref_wav']))
        config.logger.debug(f'index-tts {data=}')

        kw={
            "prompt":handle_file(data['ref_wav']),
            "text":text,
            "api_name":'/gen_single'
        }
        if int(config.params.get('index_tts_version',1))==1:
            kw['emo_ref_path']=handle_file(data['ref_wav'])
        result = self.client.predict(**kw)
                
        config.logger.debug(f'result={result}')
        wav_file = result[0] if isinstance(result, (list, tuple)) and result else result
        if isinstance(wav_file, dict) and "value" in wav_file:
            wav_file = wav_file['value']
        if isinstance(wav_file, str) and Path(wav_file).is_file():
            self.convert_to_wav(wav_file, data_item['filename'])
        else:
            raise RuntimeError(str(result))

    def _item_task_voxcpm(self, data_item: Union[Dict, List, None]):
        if self._exit() or tools.vail_file(data_item['filename']):
            return
        speed = 1.0
        try:
            speed = 1 + float(self.rate.replace('%', '')) / 100
        except ValueError:
            pass

        text = data_item['text'].strip()
        role = data_item['role']
        data = {'ref_wav': '','ref_text':''}

        if role == 'clone':
            data['ref_wav'] = data_item.get('ref_wav','')
            data['ref_text'] = data_item.get('ref_text','')
        else:
            roledict = tools.get_f5tts_role()
            if role in roledict:
                data['ref_wav'] = config.ROOT_DIR + f"/f5-tts/{role}"
                data['ref_text'] = roledict[role].get('ref_text','')

        if not data['ref_wav'] or not Path(data['ref_wav']).exists():
            raise StopRetry(tr('The role {} does not exist',role))
        config.logger.debug(f'voxcpm-tts {data=}')

        result = self.client.predict(
            text_input=text,
            prompt_wav_path_input=handle_file(data['ref_wav']),
            prompt_text_input=data.get('ref_text',''),
            cfg_value_input=2,
            inference_timesteps_input=10,
            do_normalize=True,
            denoise=True,

            api_name='/generate'
        )
        config.logger.debug(f'result={result}')
        wav_file = result[0] if isinstance(result, (list, tuple)) and result else result
        if isinstance(wav_file, dict) and "value" in wav_file:
            wav_file = wav_file['value']
        if isinstance(wav_file, str) and Path(wav_file).is_file():
            self.convert_to_wav(wav_file, data_item['filename'])
        else:
            raise RuntimeError(str(result))


    def _item_task_dia(self, data_item: Union[Dict, List, None]):
        if self._exit() or tools.vail_file(data_item['filename']):
            return
        speed = 1.0
        try:
            speed = 1 + float(self.rate.replace('%', '')) / 100
        except ValueError:
            pass

        text = data_item['text'].strip()
        role = data_item['role']
        data = {'ref_wav': ''}

        if role == 'clone':
            data['ref_wav'] = data_item.get('ref_wav','')
        else:
            roledict = tools.get_f5tts_role()
            if role in roledict:
                data['ref_wav'] = config.ROOT_DIR + f"/f5-tts/{role}"
                data['ref_text'] = roledict[role].get('ref_text', '')

        if not data['ref_wav'] or not Path(data['ref_wav']).exists():
            self.error =tr('The role {} does not exist',role)
            raise StopRetry(self.error)

        result = self.client.predict(
            text_input=text,
            audio_prompt_input=handle_file(data['ref_wav']),
            transcription_input=data.get('ref_text', ''),
            api_name='/generate_audio'
        )

        config.logger.debug(f'result={result}')
        wav_file = result[0] if isinstance(result, (list, tuple)) and result else result
        if isinstance(wav_file, dict) and "value" in wav_file:
            wav_file = wav_file['value']
        if isinstance(wav_file, str) and Path(wav_file).is_file():
            self.convert_to_wav(wav_file, data_item['filename'])
        else:
            raise RuntimeError(str(result))

    def _item_task(self, data_item: Union[Dict, List, None]):
        if self._exit() or  not data_item.get('text','').strip():
            return
        # F5_TTS_WINFORM_NAMES=['F5-TTS', 'Spark-TTS', 'Index-TTS', 'Dia-TTS','VoxCPM-TTS']
        # Spark-TTS','Index-TTS Dia-TTS
        @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
               wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
               after=after_log(config.logger, logging.INFO))
        def _run():
            
            if self._exit():
                return
            try:
                self.client = Client(self.api_url, httpx_kwargs={"timeout": 7200,"proxy":self.proxy_str}, ssl_verify=False)
            except ValueError as e:
                if 'api_name' in str(e):
                    raise StopRetry(f'api_name名称不正确，请确保使用该TTS的官方源码部署\F5-TTS: https://github.com/SWivid/F5-TTS\nIndex-TTS: https://github.com/index-tts/index-tts\nSpark-TTS: https://github.com/SparkAudio/Spark-TTS\nVoxCPM-TTS: https://github.com/OpenBMB/VoxCPM\nDia-TTS: https://github.com/nari-labs/dia')
                raise
            except Exception as e:
                raise StopRetry( f'{e}')
            if self.tts_type==tts.SPARK_TTS:
                self._item_task_spark(data_item)
            elif self.tts_type==tts.INDEX_TTS:
                self._item_task_index(data_item)
            elif self.tts_type==tts.VOXCPM_TTS:
                self._item_task_voxcpm(data_item)
            elif self.tts_type==tts.DIA_TTS:
                self._item_task_dia(data_item)
            else:
                self._item_task_v1(data_item)
            
        try:
            _run()
        except RetryError as e:
            self.error= e.last_attempt.exception()
        except Exception as e:
            self.error = e


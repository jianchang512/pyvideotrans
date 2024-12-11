# stt项目识别接口
import re,os
from pathlib import Path
from typing import Union, List, Dict



from pydub import AudioSegment

from videotrans.configure import config
from videotrans.util import tools
from videotrans.recognition._base import BaseRecogn
from funasr import AutoModel



class FunasrRecogn(BaseRecogn):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        proxy = os.environ.get('http_proxy')
        if proxy:
            del os.environ['http_proxy']
            del os.environ['https_proxy']
            del os.environ['all_proxy']
        self.raws = []

    def remove_unwanted_characters(self,text: str) -> str:
        # 保留中文、日文、韩文、英文、数字和常见符号，去除其他字符
        allowed_characters = re.compile(r'[^\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af'
                                        r'a-zA-Z0-9\s.,!@#$%^&*()_+\-=\[\]{};\'"\\|<>/?，。！｛｝【】；‘’“”《》、（）￥]+')
        return re.sub(allowed_characters, '', text)

    def _exec(self)->Union[List[Dict], None]:
        if self._exit():
            return
        self._set_proxy(type='del')
        if self.model_name=='SenseVoiceSmall':
            return self._exec1()
        if not Path(config.ROOT_DIR+'/models/hub/iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch/model.pt').exists() or not Path(config.ROOT_DIR+'/models/hub/iic/speech_fsmn_vad_zh-cn-16k-common-pytorch/model.pt').exists():
            msg='需从 modelscope.cn 下载模型，下载可能较久，请耐心等待' if config.defaulelang=='zh' else 'The model needs to be downloaded from modelscope.cn, which may take a long time, please be patient'
            self._signal(text=msg)
            if self.inst and self.inst.status_text:
                self.inst.status_text=msg
        try:
            model = AutoModel(
                            model=self.model_name,model_revision="v2.0.4",
                              vad_model="fsmn-vad", vad_model_revision="v2.0.4",
                              punc_model="ct-punc", punc_model_revision="v2.0.4",
                              local_dir=config.ROOT_DIR + "/models",
                              hub='ms',
                              disable_update=True,
                              disable_progress_bar=True,
                              disable_log=True,
                            device=self.device
                    )
        
            msg=f"模型加载完毕，进入识别" if config.defaulelang == 'zh' else 'Model loading is complete, enter recognition'
            self._signal(text=msg)
            if self.inst and self.inst.status_text:
                self.inst.status_text=msg
            res = model.generate(input=self.audio_file, return_raw_text=True, is_final=True,
                                 sentence_timestamp=True, batch_size_s=100,disable_pbar=True)
            raw_subtitles = []

            for it in res[0]['sentence_info']:
                tmp={
                    "line": len(raw_subtitles) + 1,
                    "text": it['text'],
                    "start_time": it['start'],
                    "end_time": it['end'],
                    "startraw": f'{tools.ms_to_time_string(ms=it["start"])}',
                    "endraw":f'{tools.ms_to_time_string(ms=it["end"])}'
                }
                self._signal(text=it['text']+"\n",type='subtitle')
                tmp['time']=f"{tmp['startraw']} --> {tmp['endraw']}"
                raw_subtitles.append(tmp)
        except Exception as e:
            err=str(e)
            if err.find('is not registered')>0:
                raise Exception('可能网络连接出错，请关闭代理后重试')
            raise
        finally:         
            self._set_proxy(type='set')
            try:
                del model
            except:
                pass
        return raw_subtitles

    def _exec1(self) -> Union[List[Dict], None]:
        if self._exit():
            return
        if not Path(config.ROOT_DIR+'/models/hub/iic/SenseVoiceSmall/model.pt').exists():
            msg='需从 modelscope.cn 下载模型，下载可能较久，请耐心等待' if config.defaulelang=='zh' else 'The model needs to be downloaded from modelscope.cn, which may take a long time, please be patient'
            self._signal(text=msg)
            if self.inst and self.inst.status_text:
                self.inst.status_text=msg

        try:
            from funasr.utils.postprocess_utils import rich_transcription_postprocess


            model = AutoModel(
                model="iic/SenseVoiceSmall",
                punc_model="ct-punc",
                device=self.device,
                local_dir=config.ROOT_DIR + "/models",
                  disable_update=True,
                  disable_progress_bar=True,
                  disable_log=True,
                  #trust_remote_code=True,
                  hub='ms'
            )
            #vad
            vm = AutoModel(
                model="fsmn-vad",
                local_dir=config.ROOT_DIR + "/models",
                max_single_segment_time=20000,
                max_end_silence_time=250,
                hub='ms',
                disable_update=True,
                disable_progress_bar=True,
                disable_log=True,
                device=self.device)
            msg=f"模型已加载开始识别，请耐心等待" if config.defaulelang == 'zh' else 'Recognition may take a while, please be patient'
            self._signal(text=msg)
            if self.inst and self.inst.status_text:
                self.inst.status_text=msg
            segments = vm.generate(input=self.audio_file)
            audiodata = AudioSegment.from_file(self.audio_file)

            srts = []
            for seg in segments[0]['value']:
                chunk = audiodata[seg[0]:seg[1]]
                filename = f"{config.TEMP_DIR}/{seg[0]}-{seg[1]}.wav"
                chunk.export(filename)
                res = model.generate(
                    input=filename,
                    language=self.detect_language[:2],  # "zh", "en", "yue", "ja", "ko", "nospeech"
                    use_itn=True,
                    disable_pbar=True
                )
                text = self.remove_unwanted_characters(rich_transcription_postprocess(res[0]["text"]))
                srt={
                    "line": len(srts) + 1,
                    "text": text,
                    "start_time": seg[0],
                    "end_time": seg[1],
                    "startraw": f'{tools.ms_to_time_string(ms=seg[0])}',
                    "endraw":f'{tools.ms_to_time_string(ms=seg[1])}'
                }
                srt['time']=f"{srt['startraw']} --> {srt['endraw']}"
                srts.append(srt)

                self._signal(
                    text=text+"\n",
                    type='subtitle'
                )
            return srts
        except Exception as e:
            err=str(e)
            if err.find('is not registered')>0:
                raise Exception('可能网络连接出错，请关闭代理后重试')
            raise
        finally:
            self._set_proxy(type='set')
            try:
                if model:
                    del model
                if vm:
                    del vm
            except:
                pass
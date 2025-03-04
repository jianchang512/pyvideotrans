import time

import azure.cognitiveservices.speech as speechsdk

from videotrans.configure import config
from videotrans.tts._base import BaseTTS
from videotrans.util import tools


# 单线程执行，合并字幕数量

class AzureTTS(BaseTTS):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.con_num = int(float(config.settings.get('azure_lines',1)))

    def _item_task_pl(self, items: list = None):
        if self._exit():
            return
        filename = config.TEMP_DIR + f"/azure_tts_{time.time()}.wav"
        try:
            speech_config = speechsdk.SpeechConfig(
                subscription=config.params['azure_speech_key'],
                region=config.params['azure_speech_region']
            )
            speech_config.set_speech_synthesis_output_format(
                speechsdk.SpeechSynthesisOutputFormat.Riff48Khz16BitMonoPcm)
        except Exception as e:
            raise
        audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True, filename=filename )
        speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
        text_xml = ''
        if len(items) == 1:
            text_xml += f"<prosody rate='{self.rate}' pitch='{self.pitch}' volume='{self.volume}'>{items[0]['text']}</prosody>"
        else:
            for i, it in enumerate(items):
                text_xml += f"<bookmark mark='mark{i}'/><prosody rate='{self.rate}' pitch='{self.pitch}' volume='{self.volume}'>{it['text']}</prosody>"

        ssml = """<speak version='1.0' xml:lang='{}' xmlns='http://www.w3.org/2001/10/synthesis' xmlns:mstts='http://www.w3.org/2001/mstts'>
                                <voice name='{}'>
                                    <prosody rate="{}" pitch='{}'  volume='{}'>
                                    {}
                                    </prosody>
                                </voice>
                                </speak>""".format(self.language, items[0]['role'], self.rate, self.pitch, self.volume,text_xml)
        config.logger.info(f'{ssml=}')
        bookmarks = []

        def bookmark_reached(event):
            bookmarks.append({
                "time": event.audio_offset / 10000  # 转换为毫秒
            })

        if len(items) > 1:
            speech_synthesizer.bookmark_reached.connect(bookmark_reached)

        speech_synthesis_result = speech_synthesizer.speak_ssml_async(ssml).get()
        if speech_synthesis_result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            if len(items) == 1:
                self.has_done += 1
                if self.inst and self.inst.precent < 80:
                    self.inst.precent += 0.1
                self.error = ''
                if tools.vail_file(filename):
                    tools.wav2mp3(filename, items[0]['filename'])
                else:
                    self.error='TTS error'
                self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')
                return
            length = len(bookmarks)
            for i, it in enumerate(bookmarks):
                if i >= length or not tools.vail_file(filename):
                    continue
                cmd = [
                    "-y",
                    "-i",
                    filename,
                    "-ss",
                    str(it['time'] / 1000)
                ]
                if i < length - 1:
                    cmd += [
                        "-t",
                        str((bookmarks[i + 1]['time'] - it['time']) / 1000)
                    ]
                cmd += [items[i]['filename']]
                tools.runffmpeg(cmd)
                self.has_done += 1
                if self.inst and self.inst.precent < 80:
                    self.inst.precent += 0.1
                self.error = ''
                self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')
        elif speech_synthesis_result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = speech_synthesis_result.cancellation_details
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                if cancellation_details.error_details:
                    self.error = str(cancellation_details.error_details)
                    raise Exception(cancellation_details.error_details)
            raise Exception(cancellation_details.reason)
        else:
            self.error = '请检查 Azure TTS 配置'
            raise Exception('请检查 Azure TTS 配置')
    
    def _item_task(self, data_item):
        if self._exit():
            return
        filename = config.TEMP_DIR + f"/azure_tts_{time.time()}.wav"
        try:
            speech_config = speechsdk.SpeechConfig(
                subscription=config.params['azure_speech_key'],
                region=config.params['azure_speech_region']
            )
            speech_config.set_speech_synthesis_output_format(
                speechsdk.SpeechSynthesisOutputFormat.Riff48Khz16BitMonoPcm)
        except Exception as e:
            raise
        audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True, filename=filename )
        speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
        text_xml = f"<prosody rate='{self.rate}' pitch='{self.pitch}' volume='{self.volume}'>{data_item['text']}</prosody>"
        ssml = """<speak version='1.0' xml:lang='{}' xmlns='http://www.w3.org/2001/10/synthesis' xmlns:mstts='http://www.w3.org/2001/mstts'>
                                <voice name='{}'>
                                    <prosody rate="{}" pitch='{}'  volume='{}'>
                                    {}
                                    </prosody>
                                </voice>
                                </speak>""".format(self.language, data_item['role'], self.rate, self.pitch, self.volume,text_xml)
        config.logger.info(f'{ssml=}')
        speech_synthesis_result = speech_synthesizer.speak_ssml_async(ssml).get()
        if speech_synthesis_result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            self.has_done += 1
            if self.inst and self.inst.precent < 80:
                self.inst.precent += 0.1
            self.error = ''
            if tools.vail_file(filename):
                tools.wav2mp3(filename, data_item['filename'])
            else:
                self.error="TTS error"
            self.has_done+=1
            self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}')
        elif speech_synthesis_result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = speech_synthesis_result.cancellation_details
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                if cancellation_details.error_details:
                    self.error = str(cancellation_details.error_details)
                    raise Exception(cancellation_details.error_details)
            raise Exception(cancellation_details.reason)
        else:
            self.error = '请检查 Azure TTS 配置'
            raise Exception('Azure TTS SK or API is error')
    # 鼠标不重试，直接报错停止
    def _exec(self) -> None:
        if int(config.settings.get('azure_lines',1))<=150:
            self._local_mul_thread()
        else:
            language = self.language.split("-", maxsplit=1)
            self.language = language[0].lower() + ("" if len(language) < 2 else '-' + language[1].upper())
            if self.len == 1:
                return self._item_task_pl(self.queue_tts)
            split_queue = [self.queue_tts[i:i + self.con_num] for i in range(0, self.len, self.con_num)]
            for idx, items in enumerate(split_queue):
                if self._exit():
                    return
                self._item_task_pl(items)
                time.sleep(self.wait_sec)

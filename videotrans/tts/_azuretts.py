import logging
import time
from dataclasses import dataclass, field

import azure.cognitiveservices.speech as speechsdk
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure import config
from videotrans.configure._except import RetryRaise
from videotrans.tts._base import BaseTTS
from videotrans.util import tools

RETRY_NUMS = 2
RETRY_DELAY = 5


@dataclass
class AzureTTS(BaseTTS):
    con_num: int = field(init=False)

    def __post_init__(self):
        super().__post_init__()
        self.con_num = int(float(config.settings.get('azure_lines', 1)))

    def _item_task_pl(self, items: list = None):
        @retry(retry=retry_if_not_exception_type(RetryRaise.NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
               wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
               after=after_log(config.logger, logging.INFO), retry_error_callback=RetryRaise._raise)
        def _run():
            if self._exit():
                return
            filename = config.TEMP_DIR + f"/azure_tts_{time.time()}.wav"

            speech_config = speechsdk.SpeechConfig(
                subscription=config.params['azure_speech_key'],
                region=config.params['azure_speech_region']
            )
            speech_config.set_speech_synthesis_output_format(
                speechsdk.SpeechSynthesisOutputFormat.Riff48Khz16BitMonoPcm)

            audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True, filename=filename)
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
                                    </speak>""".format(self.language, items[0]['role'], self.rate, self.pitch,
                                                       self.volume,
                                                       text_xml)
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
                        self.convert_to_wav(filename, items[0]['filename'])
                    else:
                        raise RuntimeError('TTS error')
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

                    cmd += ["-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le", items[i]['filename']]
                    tools.runffmpeg(cmd)
                    self.has_done += 1
                    if self.inst and self.inst.precent < 80:
                        self.inst.precent += 0.1
                    self.error = ''
                    self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')
                return

            if speech_synthesis_result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = speech_synthesis_result.cancellation_details
                if cancellation_details.reason == speechsdk.CancellationReason.Error:
                    if cancellation_details.error_details:
                        raise RuntimeError(str(cancellation_details.error_details))
                raise RuntimeError(str(cancellation_details.reason))
            raise RuntimeError('Test Azure')

        _run()

    def _item_task(self, data_item):
        @retry(retry=retry_if_not_exception_type(RetryRaise.NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
               wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
               after=after_log(config.logger, logging.INFO), retry_error_callback=RetryRaise._raise)
        def _run():
            if self._exit() or tools.vail_file(data_item['filename']):
                return
            filename = data_item['filename'] + f"-generate.wav"

            speech_config = speechsdk.SpeechConfig(
                subscription=config.params['azure_speech_key'],
                region=config.params['azure_speech_region']
            )
            speech_config.set_speech_synthesis_output_format(
                speechsdk.SpeechSynthesisOutputFormat.Riff48Khz16BitMonoPcm)

            audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True, filename=filename)
            speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
            text_xml = f"<prosody rate='{self.rate}' pitch='{self.pitch}' volume='{self.volume}'>{data_item['text']}</prosody>"
            ssml = """<speak version='1.0' xml:lang='{}' xmlns='http://www.w3.org/2001/10/synthesis' xmlns:mstts='http://www.w3.org/2001/mstts'>
                                    <voice name='{}'>
                                        <prosody rate="{}" pitch='{}'  volume='{}'>
                                        {}
                                        </prosody>
                                    </voice>
                                    </speak>""".format(self.language, data_item['role'], self.rate, self.pitch,
                                                       self.volume,
                                                       text_xml)
            config.logger.info(f'{ssml=}')
            speech_synthesis_result = speech_synthesizer.speak_ssml_async(ssml).get()
            if speech_synthesis_result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                self.has_done += 1
                if self.inst and self.inst.precent < 80:
                    self.inst.precent += 0.1
                self.error = ''
                if tools.vail_file(filename):
                    self.convert_to_wav(filename, data_item['filename'])
                else:
                    self.error = "TTS error"
                    raise RuntimeError(self.error)
                self.has_done += 1
                self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}')
                return
            if speech_synthesis_result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = speech_synthesis_result.cancellation_details
                if cancellation_details.reason == speechsdk.CancellationReason.Error:
                    if cancellation_details.error_details:
                        raise RuntimeError(cancellation_details.error_details)
                raise RuntimeError(cancellation_details.reason)
            raise RuntimeError('Test Azure SK')

        _run()

    # 鼠标不重试，直接报错停止
    def _exec(self) -> None:
        if int(config.settings.get('azure_lines', 1)) < 100:
            self._local_mul_thread()
            return

        language = self.language.split("-", maxsplit=1)
        self.language = language[0].lower() + ("" if len(language) < 2 else '-' + language[1].upper())

        split_queue = [self.queue_tts[i:i + self.con_num] for i in range(0, self.len, self.con_num)]
        for idx, items in enumerate(split_queue):
            if self._exit():
                return
            self._item_task_pl(items)
            time.sleep(self.wait_sec)

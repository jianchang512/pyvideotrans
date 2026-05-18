import logging
from dataclasses import dataclass
from typing import Union, List, Dict
import azure.cognitiveservices.speech as speechsdk
from azure.core.exceptions import ResourceExistsError, ClientAuthenticationError, ResourceNotFoundError
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log
from videotrans.configure.config import params, logger, settings
from videotrans.configure.excepts import NO_RETRY_EXCEPT, StopTask
from videotrans.tts._base import BaseTTS
from videotrans.util import tools

@dataclass
class AzureTTS(BaseTTS):

    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO), after=after_log(logger, logging.INFO))
    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        try:
            filename = data_item['filename'] + f"-generate.wav"
            speech_config = speechsdk.SpeechConfig(
                subscription=params.get('azure_speech_key',''),
                region=params.get('azure_speech_region','')
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
                                    </speak>""".format(self.language, tools.get_azure_rolelist(self.language.split('-')[0],data_item['role']), self.rate, self.pitch,
                                                       self.volume,
                                                       text_xml)
            logger.debug(f'{ssml=}')
            speech_synthesis_result = speech_synthesizer.speak_ssml_async(ssml).get()
            if speech_synthesis_result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                if tools.vail_file(filename):
                    self.convert_to_wav(filename, data_item['filename'])
                else:
                    return 'TTS Error'
                return
            if speech_synthesis_result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = speech_synthesis_result.cancellation_details
                if cancellation_details.reason == speechsdk.CancellationReason.Error:
                    if cancellation_details.error_details:
                        return cancellation_details.error_details
                return cancellation_details.reason
            return 'Test Azure SK'

        except (ResourceExistsError,ResourceNotFoundError,ClientAuthenticationError) as e:
            raise StopTask(e.message)


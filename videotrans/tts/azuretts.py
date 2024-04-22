from videotrans.configure import config
from videotrans.util import tools
import os
import azure.cognitiveservices.speech as speechsdk



def get_voice(*,text=None, role=None, rate=None, language=None,filename=None,set_p=True,is_test=False,inst=None):
    try:
        if config.current_status != 'ing' and config.box_tts != 'ing' and not is_test:
            return False
        if language:
            language=language.split("-",maxsplit=1)
        else:
            language=role.split('-',maxsplit=2)
        language=language[0].lower()+("" if len(language)<2 else '-'+language[1].upper())
        print(f'{language=}')
        # This example requires environment variables named "SPEECH_KEY" and "SPEECH_REGION"
        speech_config = speechsdk.SpeechConfig(
            subscription=config.params['azure_speech_key'],
            region=config.params['azure_speech_region'])
        # The neural multilingual voice can speak different languages based on the input text.
        # speech_config.speech_synthesis_voice_name=role
        audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True,filename=filename+".wav")
        speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
        if rate  in ['+0%','0%','-0%','0','+0','-0']:
            ssml = """<speak version='1.0' xml:lang='{}' xmlns='http://www.w3.org/2001/10/synthesis' xmlns:mstts='http://www.w3.org/2001/mstts'>
            <voice name='{}'>
                {}
            </voice>
        </speak>""".format(language,role,text)
        else:
            ssml = """<speak version='1.0' xml:lang='{}' xmlns='http://www.w3.org/2001/10/synthesis' xmlns:mstts='http://www.w3.org/2001/mstts'>
            <voice name='{}'>
                <prosody rate="{}">
                {}
                </prosody>
            </voice>
        </speak>""".format(language,role,rate,text)
        speech_synthesis_result = speech_synthesizer.speak_ssml_async(ssml).get()
        print(f'{ssml=}')

        if speech_synthesis_result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            tools.wav2mp3(filename+".wav",filename)
            if os.path.exists(filename) and os.path.getsize(filename)>0 and config.settings['remove_silence']:
                tools.remove_silence_from_end(filename)
            if set_p and inst and inst.precent < 80:
                inst.precent += 0.1
                tools.set_process(f'{config.transobj["kaishipeiyin"]} ', btnkey=inst.btnkey if inst else "")
        elif speech_synthesis_result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = speech_synthesis_result.cancellation_details
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                if cancellation_details.error_details:
                    raise Exception(config.transobj['azureinfo'])
            raise Exception("Speech synthesis canceled: {},text={}".format(cancellation_details.reason,text))
        else:
            raise Exception('配音出错，请检查 Azure TTS')
    except Exception as e:
        print(e)
        error=str(e)
        config.logger.error(f"Azure TTS合成失败" + str(e))
        if set_p:
            tools.set_process(error,btnkey=inst.btnkey if inst else "")
        raise Exception(f" Azure TTS:{error}" )

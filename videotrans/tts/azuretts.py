import json
import time

from videotrans.configure import config
from videotrans.util import tools
import os
import azure.cognitiveservices.speech as speechsdk


shound_del=False
def update_proxy(type='set'):
    global shound_del
    if type=='del' and shound_del:
        del os.environ['http_proxy']
        del os.environ['https_proxy']
        del os.environ['all_proxy']
        shound_del=False
    elif type=='set':
        raw_proxy=os.environ.get('http_proxy')
        if not raw_proxy:
            proxy=tools.set_proxy()
            if proxy:
                shound_del=True
                os.environ['http_proxy'] = proxy
                os.environ['https_proxy'] = proxy
                os.environ['all_proxy'] = proxy


def get_voice(*,text=None, role=None, volume="+0%",pitch="+0Hz",rate=None, language=None,filename=None,set_p=True,inst=None):
    try:
        text_xml=""
        is_list=isinstance(text,list)
        if is_list:
            filename=config.TEMP_DIR+f"/azure_tts_{time.time()}"
            for i, t in enumerate(text):
                text_xml += f"<bookmark mark='mark{i}'/><prosody rate='{rate}' pitch='{pitch}' volume='{volume}'>{t['text']}</prosody>"
        else:
            text_xml=text
        update_proxy(type='set')
        if language:
            language=language.split("-",maxsplit=1)
        else:
            language=role.split('-',maxsplit=2)
        language=language[0].lower()+("" if len(language)<2 else '-'+language[1].upper())

        try:
            speech_config = speechsdk.SpeechConfig(
                subscription=config.params['azure_speech_key'],
                region=config.params['azure_speech_region']       
            )
            speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Riff48Khz16BitMonoPcm)
        except Exception as e:
            raise Exception(f'====={str(e)=}')

        # The neural multilingual voice can speak different languages based on the input text.
        # speech_config.speech_synthesis_voice_name=role
        audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True,filename=filename+".wav")
        speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)

        ssml = """<speak version='1.0' xml:lang='{}' xmlns='http://www.w3.org/2001/10/synthesis' xmlns:mstts='http://www.w3.org/2001/mstts'>
        <voice name='{}'>
            <prosody rate="{}" pitch='{}'  volume='{}'>
            {}
            </prosody>
        </voice>
        </speak>""".format(language,role,rate,pitch,volume,text_xml)
        print(ssml)
        config.logger.info(f'{ssml=}')

        if is_list:
            bookmarks = []
            def bookmark_reached(event):
                bookmarks.append({
                    "time": event.audio_offset / 10000  # 转换为毫秒
                })
            speech_synthesizer.bookmark_reached.connect(bookmark_reached)
        speech_synthesis_result = speech_synthesizer.speak_ssml_async(ssml).get()

        if speech_synthesis_result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            if not is_list:
                tools.wav2mp3(filename + ".wav", filename)
                if tools.vail_file(filename) and config.settings['remove_silence']:
                    tools.remove_silence_from_end(filename)
                if set_p and inst and inst.precent < 80:
                    inst.precent += 0.1
                    tools.set_process(f'{config.transobj["kaishipeiyin"]} ', btnkey=inst.init['btnkey'] if inst else "")
                return True

            length=len(bookmarks)
            for i,it in enumerate(bookmarks):
                if i >= len(text):
                    continue
                cmd=[
                        "-y",
                        "-i",
                        filename+".wav",
                        "-ss",
                        str(it['time'] / 1000)
                ]
                if i < length-1:
                    cmd+=[
                        "-t",
                        str( (bookmarks[i+1]['time']-it['time']) / 1000)
                    ]
                cmd+=[text[i]['filename']]
                tools.runffmpeg(cmd)
        elif speech_synthesis_result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = speech_synthesis_result.cancellation_details
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                if cancellation_details.error_details:
                    print(f'###{cancellation_details.error_details}')
                    tools.set_process(f"{config.transobj['azureinfo']}", btnkey=inst.init['btnkey'] if inst else "")
                    raise Exception(config.transobj['azureinfo'])
            raise Exception("Speech synthesis canceled: {},text={}".format(cancellation_details.reason,text))
        else:
            raise Exception('配音出错，请检查 Azure TTS')
    except Exception as e:
        error=str(e)
        print(f'{error}')
        if inst and inst.init['btnkey']:
            config.errorlist[inst.init['btnkey']]=error
        config.logger.error(f"Azure TTS合成失败" + str(e))
        if set_p:
            tools.set_process(error,btnkey=inst.init['btnkey'] if inst else "")
        update_proxy(type='del')
        raise Exception(error)
    else:
        update_proxy(type='del')

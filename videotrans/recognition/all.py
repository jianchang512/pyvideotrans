# 整体识别，全部传给模型
import os
import re

from videotrans.configure import config
from videotrans.util import tools
from faster_whisper import WhisperModel
import zhconv

def recogn(*,
           detect_language=None,
           audio_file=None,
           cache_folder=None,
           model_name="tiny",
           set_p=True,
           inst=None,
           is_cuda=None):
    print(f'整体识别')
    if config.exit_soft or (config.current_status != 'ing' and config.box_recogn != 'ing'):
        return False
    down_root = config.rootdir + "/models"
    if set_p and inst:
        if model_name.find('/')>0:
            if not os.path.isdir(down_root+'/models--'+model_name.replace('/','--')):
                inst.parent.status_text='下载模型中，用时可能较久' if config.defaulelang=='zh'else 'Download model from huggingface'
            else:
                inst.parent.status_text='加载或下载模型中，用时可能较久' if config.defaulelang=='zh'else 'Load model from local or download model from huggingface'
        else:
            tools.set_process(f"{config.transobj['kaishishibie']}",btnkey=inst.init['btnkey'] if inst else "")
    model = None
    try:
        if model_name.startswith('distil-'):
            com_type= "default"
        elif is_cuda:
            com_type=config.settings['cuda_com_type']
        else:
            com_type='default'
        local_res=True if model_name.find('/')==-1 else False       
        
        model = WhisperModel(model_name,
                             device="cuda" if is_cuda else "cpu",
                             compute_type=com_type,
                             download_root=down_root,
                             num_workers=config.settings['whisper_worker'],
                             cpu_threads=os.cpu_count() if int(config.settings['whisper_threads']) < 1 else int(
                                 config.settings['whisper_threads']),
                             local_files_only=local_res)
        if config.current_status != 'ing' and config.box_recogn != 'ing':
            return False
        if not tools.vail_file(audio_file):
            raise Exception(f'no exists {audio_file}')
        print('temperature===')
        print(0 if config.settings['temperature'] == 0 else [0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
        segments, info = model.transcribe(audio_file,
                                          beam_size=config.settings['beam_size'],
                                          best_of=config.settings['best_of'],
                                          condition_on_previous_text=config.settings['condition_on_previous_text'],

                                          temperature=0 if config.settings['temperature'] == 0 else [0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
                                          vad_filter=bool(config.settings['vad']),
                                          vad_parameters=dict(
                                              min_silence_duration_ms=config.settings['overall_silence'],
                                              max_speech_duration_s=config.settings['overall_maxsecs'],
                                              threshold=config.settings['overall_threshold'],
                                              speech_pad_ms=config.settings['overall_speech_pad_ms']
                                          ),
                                          word_timestamps=True,
                                          language=detect_language,
                                          initial_prompt=config.settings['initial_prompt_zh'])

        # 保留原始语言的字幕
        raw_subtitles = []
        sidx = -1

        for segment in segments:
            if config.exit_soft or (config.current_status != 'ing' and config.box_recogn != 'ing'):
                #del model
                return None
            if not segment.words or len(segment.words)<1:
                continue
            sidx += 1
            start = int(segment.words[0].start * 1000)
            end = int(segment.words[-1].end * 1000)
            # if start == end:
            #     end += 200
            startTime = tools.ms_to_time_string(ms=start)
            endTime = tools.ms_to_time_string(ms=end)
            text = segment.text.strip().replace('&#39;', "'")
            if detect_language == 'zh' and text == config.settings['initial_prompt_zh']:
                continue
            text = re.sub(r'&#\d+;', '', text)
            # 无有效字符
            if not text or re.match(r'^[，。、？‘’“”；：（｛｝【】）:;"\'\s \d`!@#$%^&*()_+=.,?/\\-]*$', text) or len(text) <= 1:
                continue
            if detect_language[:2]=='zh' and config.settings['zh_hant_s']:
                text=zhconv.convert(text,'zh-hans')
            # 原语言字幕
            s = {"line": len(raw_subtitles) + 1, "time": f"{startTime} --> {endTime}", "text": text}
            raw_subtitles.append(s)
            if set_p:
                tools.set_process(f'{s["line"]}\n{startTime} --> {endTime}\n{text}\n\n', 'subtitle')
                if inst and inst.precent < 55:
                    inst.precent += round(segment.end * 0.5 / info.duration, 2)
                tools.set_process(f'{config.transobj["zimuhangshu"]} {s["line"]}',
                                  btnkey=inst.init['btnkey'] if inst else "")
            else:
                tools.set_process_box(text=f'{s["line"]}\n{startTime} --> {endTime}\n{text}\n\n', type="set",
                                      func_name="shibie")
        return raw_subtitles
    except Exception as e:
        raise Exception(str(e)+str(e.args))


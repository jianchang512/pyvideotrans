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
    config.logger.info('faster模式 整体识别')
    if config.exit_soft or (config.current_status != 'ing' and config.box_recogn != 'ing'):
        return False
    down_root = config.rootdir + "/models"
    if set_p and inst:
        if model_name.find('/') > 0:
            if not os.path.isdir(down_root + '/models--' + model_name.replace('/', '--')):
                inst.parent.status_text = '下载模型中，用时可能较久' if config.defaulelang == 'zh' else 'Download model from huggingface'
            else:
                inst.parent.status_text = '加载或下载模型中，用时可能较久' if config.defaulelang == 'zh' else 'Load model from local or download model from huggingface'
        else:
            tools.set_process(f"{config.transobj['kaishishibie']}", btnkey=inst.init['btnkey'] if inst else "")
    model = None
    raws = []
    try:
        if model_name.startswith('distil-'):
            com_type = "default"
        elif is_cuda:
            com_type = config.settings['cuda_com_type']
        else:
            com_type = 'default'
        local_res = True if model_name.find('/') == -1 else False

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
        segments, info = model.transcribe(audio_file,
                                          beam_size=config.settings['beam_size'],
                                          best_of=config.settings['best_of'],
                                          condition_on_previous_text=config.settings['condition_on_previous_text'],

                                          temperature=0 if config.settings['temperature'] == 0 else [0.0, 0.2, 0.4, 0.6,
                                                                                                     0.8, 1.0],
                                          vad_filter=bool(config.settings['vad']),
                                          vad_parameters=dict(
                                              min_silence_duration_ms=config.settings['overall_silence'],
                                              max_speech_duration_s=float('inf'),
                                              threshold=config.settings['overall_threshold'],
                                              speech_pad_ms=config.settings['overall_speech_pad_ms']
                                          ),
                                          word_timestamps=True,
                                          language=detect_language,
                                          initial_prompt=config.settings['initial_prompt_zh'])
        flag = [
            ",",
            ":",
            "'",
            "\"",
            ".",
            "?",
            "!",
            ";",
            ")",
            "]",
            "}",
            ">",
            "，",
            "。",
            "？",
            "；",
            "’",
            "”",
            "》",
            "】",
            "｝",
            "！"
        ]
        if detect_language[:2].lower() in ['zh', 'ja', 'ko']:
            flag.append(" ")
            maxlen = config.settings['cjk_len']
        else:
            maxlen=config.settings['other_len']
        def output(srt):
            if set_p:
                tools.set_process(f'{srt["line"]}\n{srt["time"]}\n{srt["text"]}\n\n', 'subtitle')
                if inst and inst.precent < 55:
                    inst.precent += round(segment.end * 0.5 / info.duration, 2)
                tools.set_process(f'{config.transobj["zimuhangshu"]} {srt["line"]}',
                                  btnkey=inst.init['btnkey'] if inst else "")
            else:
                tools.set_process_box(text=f'{srt["line"]}\n{srt["time"]}\n{srt["text"]}\n\n', type="set",
                                      func_name="shibie")
        def append_raws(cur):
            if len(cur['text'])<int(maxlen/5) and len(raws)>0:
                raws[-1]['text']+= cur['text'] if detect_language[:2] in ['ja','zh','ko'] else f' {cur["text"]}'
                raws[-1]['end_time']=cur['end_time']
                raws[-1]['time']=f'{tools.ms_to_time_string(ms=cur["start_time"])} --> {tools.ms_to_time_string(ms=cur["end_time"])}'
            else:
                output(cur)
                raws.append(cur)

        for segment in segments:
            if len(segment.text.strip()) <= maxlen:
                tmp = {
                    "line": len(raws) + 1,
                    "start_time": int(segment.words[0].start * 1000),
                    "end_time": int(segment.words[-1].end * 1000),
                    "text": segment.text.strip()
                }
                if tmp['end_time']-tmp['start_time']>=1500:
                    tmp["time"] = f'{tools.ms_to_time_string(ms=tmp["start_time"])} --> {tools.ms_to_time_string(ms=tmp["end_time"])}'
                    append_raws(tmp)
                    continue



            cur = None
            for word in segment.words:
                if not cur:
                    cur = {"line": len(raws) + 1,
                           "start_time": int(word.start * 1000),
                           "end_time": int(word.end * 1000),
                           "text": word.word}
                    continue
                # 第一个字符 是标点并且大于最小字符数
                if word.word[0] in flag:
                    cur['end_time'] = int(word.start * 1000)
                    if cur['end_time']-cur['start_time']<1500:
                        cur['text'] += word.word
                        continue
                    cur['time'] = f'{tools.ms_to_time_string(ms=cur["start_time"])} --> {tools.ms_to_time_string(ms=cur["end_time"])}'
                    cur['text'] = cur['text'].strip()
                    append_raws(cur)
                    if len(word.word)<2:
                        cur=None
                        continue
                    cur = {
                        "line": len(raws) + 1,
                        "start_time": int(word.start * 1000),
                        "end_time": int(word.end * 1000),
                        "text": word.word[1:]}
                    continue
                cur['text'] += word.word

                if word.word[-1] in flag or len(cur['text']) >= maxlen * 1.5:
                    cur['end_time'] = int(word.end * 1000)
                    if cur['end_time']-cur['start_time']<1500:
                        continue
                    cur['time'] = f'{tools.ms_to_time_string(ms=cur["start_time"])} --> {tools.ms_to_time_string(ms=cur["end_time"])}'
                    cur['text'] = cur['text'].strip()
                    append_raws(cur)
                    cur = None

            if cur is not None:
                cur['end_time'] = int(segment.words[-1].end * 1000)
                if cur['end_time']-cur['start_time']<1500:
                    continue
                cur['time'] = f'{tools.ms_to_time_string(ms=cur["start_time"])} --> {tools.ms_to_time_string(ms=cur["end_time"])}'
                if len(cur['text'].strip()) <= 3:
                    raws[-1]['text'] += cur['text'].strip()
                    raws[-1]['end_time'] = cur['end_time']
                    raws[-1]['time'] = cur['time']
                else:
                    cur['text'] = cur['text'].strip()
                    append_raws(cur)
    except Exception as e:
        raise
    else:
        if detect_language[:2] == 'zh' and config.settings['zh_hant_s']:
            for i, it in enumerate(raws):
                raws[i]['text'] = zhconv.convert(it['text'], 'zh-hans')
        return raws

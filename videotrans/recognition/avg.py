# 均等分割识别
import json
import os
import re
import time
from datetime import timedelta

from faster_whisper import WhisperModel
from pydub import AudioSegment
from pydub.silence import detect_nonsilent

from videotrans.configure import config
from videotrans.util import tools
import zhconv

# split audio by silence
def shorten_voice_old(normalized_sound):
    normalized_sound = tools.match_target_amplitude(normalized_sound, -20.0)
    max_interval = config.settings['interval_split'] * 1000
    buffer = int(config.settings['voice_silence'])
    nonsilent_data = []
    audio_chunks = detect_nonsilent(normalized_sound, min_silence_len=int(config.settings['voice_silence']),
                                    silence_thresh=-20 - 25)
    # print(audio_chunks)
    for i, chunk in enumerate(audio_chunks):

        start_time, end_time = chunk
        n = 0
        while end_time - start_time >= max_interval:
            n += 1
            # new_end = start_time + max_interval+buffer
            new_end = start_time + max_interval
            new_start = start_time
            nonsilent_data.append((new_start, new_end, True))
            start_time += max_interval
        nonsilent_data.append((start_time, end_time, False))
    return nonsilent_data


def recogn(*,
           detect_language=None,
           audio_file=None,
           cache_folder=None,
           model_name="tiny",
           set_p=True,
           inst=None,
           is_cuda=None):
    print(f'均等分割')
    if set_p:
        tools.set_process(config.transobj['fengeyinpinshuju'], btnkey=inst.init['btnkey'] if inst else "")
    if config.exit_soft or (config.current_status != 'ing' and config.box_recogn != 'ing'):
        return False
    noextname = os.path.basename(audio_file)
    tmp_path = f'{cache_folder}/{noextname}_tmp'
    if not os.path.isdir(tmp_path):
        try:
            os.makedirs(tmp_path, 0o777, exist_ok=True)
        except:
            raise Exception(config.transobj["createdirerror"])
    if not tools.vail_file(audio_file):
        raise Exception(f'[error]not exists {audio_file}')
    normalized_sound = AudioSegment.from_wav(audio_file)  # -20.0
    nonslient_file = f'{tmp_path}/detected_voice.json'
    if tools.vail_file(nonslient_file):
        with open(nonslient_file, 'r') as infile:
            nonsilent_data = json.load(infile)
    else:
        nonsilent_data = shorten_voice_old(normalized_sound)
        with open(nonslient_file, 'w') as outfile:
            json.dump(nonsilent_data, outfile)

    raw_subtitles = []
    total_length = len(nonsilent_data)
    start_t = time.time()
    if model_name.startswith('distil-'):
        com_type= "default"
    elif is_cuda:
        com_type=config.settings['cuda_com_type']
    else:
        com_type='default'
    local_res=True if model_name.find('/')==-1 else False
    down_root=config.rootdir + "/models"
    if set_p and inst and  model_name.find('/')>0:
        if not os.path.isdir(down_root+'/models--'+model_name.replace('/','--')):
            inst.parent.status_text='下载模型中，用时可能较久' if config.defaulelang=='zh'else 'Download model from huggingface'
        else:
            inst.parent.status_text='加载或下载模型中，用时可能较久' if config.defaulelang=='zh'else 'Load model from local or download model from huggingface'
    model = WhisperModel(
            model_name,
            device="cuda" if config.params['cuda'] else "cpu",
            compute_type=com_type,
            download_root=down_root,
            local_files_only=local_res)
    for i, duration in enumerate(nonsilent_data):
        if config.exit_soft or (config.current_status != 'ing' and config.box_recogn != 'ing'):
            #del model
            return False
        start_time, end_time, buffered = duration
        #if start_time == end_time:
        #    end_time += int(config.settings['voice_silence'])

        chunk_filename = tmp_path + f"/c{i}_{start_time // 1000}_{end_time // 1000}.wav"
        audio_chunk = normalized_sound[start_time:end_time]
        audio_chunk.export(chunk_filename, format="wav")


        text = ""
        try:
            segments, _ = model.transcribe(chunk_filename,
                                          beam_size=config.settings['beam_size'],
                                          best_of=config.settings['best_of'],
                                          condition_on_previous_text=config.settings['condition_on_previous_text'],
                                           temperature=0 if config.settings['temperature'] == 0 else [0.0, 0.2, 0.4,0.6, 0.8, 1.0],
                                           vad_filter=False,
                                           #vad_parameters=dict(
                                           #    min_silence_duration_ms=config.settings['overall_silence'],
                                           #    max_speech_duration_s=config.settings['overall_maxsecs'],
                                           #    threshold=config.settings['overall_threshold'],
                                           #    speech_pad_ms=config.settings['overall_speech_pad_ms']
                                           #),
                                           #word_timestamps=True,
                                           language=detect_language,
                                           initial_prompt=config.settings['initial_prompt_zh'], )

            for t in segments:
                text += t.text + " "
                    
            text = f"{text.capitalize()}. ".replace('&#39;', "'")
            text = re.sub(r'&#\d+;', '', text).strip()
            if not text or re.match(r'^[，。、？‘’“”；：（｛｝【】）:;"\'\s \d`!@#$%^&*()_+=.,?/\\-]*$', text):
                continue
            if detect_language[:2]=='zh' and config.settings['zh_hant_s']:
                text=zhconv.convert(text,'zh-hans')
            start = tools.ms_to_time_string(ms=start_time)
            end = tools.ms_to_time_string(ms=end_time)
            srt_line = {"line": len(raw_subtitles) + 1, "time": f"{start} --> {end}", "text": text}
            raw_subtitles.append(srt_line)
            if set_p:
                if inst and inst.precent < 55:
                    inst.precent += 0.1
                tools.set_process(f"{config.transobj['yuyinshibiejindu']} {srt_line['line']}/{total_length}",
                                  btnkey=inst.init['btnkey'] if inst else "")
                msg = f"{srt_line['line']}\n{srt_line['time']}\n{srt_line['text']}\n\n"
                tools.set_process(msg, 'subtitle')
            else:
                tools.set_process_box(text=f"{srt_line['line']}\n{srt_line['time']}\n{srt_line['text']}\n\n", type="set", func_name="shibie")
        except Exception as e:
            #del model
            raise Exception(str(e.args)+str(e))

    if set_p:
        tools.set_process(f"{config.transobj['yuyinshibiewancheng']} / {len(raw_subtitles)}", 'logs', btnkey=inst.init['btnkey'] if inst else "")
    # 写入原语言字幕到目标文件夹
    return raw_subtitles

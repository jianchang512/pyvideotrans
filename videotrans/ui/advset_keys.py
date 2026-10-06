
from videotrans.configure._languages_dict import LANG_CODE
from videotrans.configure.config import app_cfg
from videotrans.configure.constants import WHISPER_MODELS
from videotrans.translator import LLM_CONCERT_DICT

ComboBox_List = ['cuda_com_type', 'llm_ai_type', 'vad_type', 'speaker_type', 'video_codec', 'preset', 'lang',
                 'uvr_models', 'out_video_ext', "fps_mode", "device_name", "model_for_recogn2",
                 "remove_dubb_silence_level"]

ComboBox_Data = {
    "cuda_com_type": [
        'default',
        'auto',
        'int8',
        'int16',
        'float16',
        'float32',
        'bfloat16',
        'int8_float16',
        'int8_float32',
        'int8_bfloat16'
    ],
    "fps_mode": ["vfr", "cfr"],
    "llm_ai_type": [it['name'] for it in LLM_CONCERT_DICT],
    "vad_type": ['tenvad', 'silero'],
    "speaker_type": ['built', 'ali_CAM', 'pyannote'],
    "video_codec": ['264', '265'],
    "preset": ['ultrafast', 'superfast', 'veryfast', 'faster', 'fast', 'medium', 'slow', 'slower',
               'veryslow'],
    "lang": list(app_cfg.SUPPORT_LANG.keys()),
    "uvr_models": [
        'spleeter',
        'UVR-MDX-NET-Inst_HQ_4',
        'UVR-MDX-NET-Inst_HQ_1',
        'UVR-MDX-NET-Inst_HQ_2',
        'UVR-MDX-NET-Inst_HQ_3',
        'UVR-MDX-NET-Inst_HQ_5',
        'UVR-MDX-NET-Inst_Main',
        'UVR-MDX-NET-Inst_1',
        'UVR-MDX-NET-Inst_2',
        'UVR-MDX-NET-Inst_3'
    ],
    "out_video_ext": ['.mp4', '.mkv'],
    "device_name": ['auto', 'cuda', 'cpu', 'mps', 'xpu', 'cuda:0', 'cuda:1', 'cuda:2', 'cuda:3'],
    "model_for_recogn2": WHISPER_MODELS.split(','),
    "remove_dubb_silence_level": ["low", "default", "max"]
}
prompt_a = []
for code in LANG_CODE.keys():
    if code == 'auto':
        continue
    prompt_a.append(f'initial_prompt_{code.replace("-", "_")}')

notices = {
    'common': ['lang', 'countdown_sec', 'homedir', 'retry_nums', 'llm_chunk_size', 'llm_ai_type', 'dont_notify',
               'noise_separate_nums', 'uvr_models', 'batch_nums', 'show_more_settings', 'process_max',
               'process_max_gpu', 'device_name', 'bit8'],
    'video': ['crf', 'preset', 'video_codec', 'out_video_ext', 'fps_mode', 'force_lib', 'hw_decode', 'ffmpeg_cmd'],
    'whisper': ['vad_type', 'threshold', 'no_speech_threshold', 'max_speech_duration_s', 'min_speech_duration_ms',
                'min_silence_duration_ms', 'model_for_recogn2', 'max_speech_duration_s2', 'min_speech_duration_ms2',
                'speaker_type', 'hf_token', 'cuda_com_type', 'beam_size', 'best_of', 'condition_on_previous_text',
                'temperature', 'repetition_penalty', 'compression_ratio_threshold', 'hotwords', 'gemini_recogn_chunk',
                'zh_hant_s', 'del_end_punc', 'asr_wait'],
    'trans': ['trans_thread', 'aitrans_thread', 'translation_wait', 'aitrans_temperature', 'aitrans_context'],
    'dubbing': ['dubbing_thread', 'dubbing_wait', 'remove_dubb_silence', 'remove_dubb_all_silence',
                'remove_dubb_silence_level', 'save_segment_audio', 'normal_text', 'edgetts_max_concurrent_tasks',
                'edgetts_retry_nums', 'chattts_voice'],
    'justify': ['max_audio_speed_rate', 'max_video_pts_rate', 'cjk_len', 'other_len'],
    'prompt_init': prompt_a
}

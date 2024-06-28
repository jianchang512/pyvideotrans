import torch
from videotrans.configure import config
import logging

from .all import recogn as all_recogn
from .yuxian import recogn as yuxian_recogn
from .avg import recogn as avg_recogn
from .zh import recogn as zh_recogn
from .openai import recogn as openai_recogn
from .google import recogn as google_recogn
from .doubao import recogn as doubao_recogn

logging.basicConfig()
logging.getLogger("faster_whisper").setLevel(logging.DEBUG)


# 统一入口
def run(*,
        type="all",
        detect_language=None,
        audio_file=None,
        cache_folder=None,
        model_name=None,
        set_p=True,
        inst=None,
        model_type='faster',
        is_cuda=None
    ):
    print(f'{model_type=}')

    if config.exit_soft or (config.current_status != 'ing' and config.box_recogn != 'ing'):
        return False
    if model_name.startswith('distil-'):
        model_name = model_name.replace('-whisper', '')
    if model_type == 'openai':
        rs = openai_recogn(
            detect_language=detect_language,
            audio_file=audio_file,
            cache_folder=cache_folder,
            model_name=model_name,
            set_p=set_p,
            inst=inst,
            is_cuda=is_cuda)
    elif model_type == 'GoogleSpeech':
        rs = google_recogn(
            detect_language=detect_language,
            audio_file=audio_file,
            cache_folder=cache_folder,
            set_p=set_p,
            inst=None)
    elif model_type == 'zh_recogn':
        rs = zh_recogn(
            audio_file=audio_file,
            cache_folder=cache_folder,
            set_p=set_p,
            inst=None)
    elif model_type=='doubao':
        rs = doubao_recogn(
            detect_language=detect_language,
            audio_file=audio_file,
            cache_folder=cache_folder,
            set_p=set_p,
            inst=inst)
    elif type == "all":
        rs = all_recogn(
            detect_language=detect_language,
            audio_file=audio_file,
            cache_folder=cache_folder,
            model_name=model_name,
            set_p=set_p,
            inst=inst,
            is_cuda=is_cuda)
    elif type == 'avg':
        rs = avg_recogn(
            detect_language=detect_language,
            audio_file=audio_file,
            cache_folder=cache_folder,
            model_name=model_name,
            set_p=set_p,
            inst=inst,
            is_cuda=is_cuda)
    else:
        rs = yuxian_recogn(
            detect_language=detect_language,
            audio_file=audio_file,
            cache_folder=cache_folder,
            model_name=model_name,
            set_p=set_p,
            inst=inst,
            is_cuda=is_cuda)
    try:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass
    return rs

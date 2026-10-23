# -*- coding: utf-8 -*-
import platform
import subprocess
import traceback, time, json
from videotrans.configure.config import ROOT_DIR, logger, settings
from pathlib import Path

from videotrans.configure.constants import DENOISE_URL_HF, ZIPENHANCER_HF
from videotrans.process._utils import _write_log
from videotrans.util.help_misc import exec_audiocpp

OS_TYPE=platform.system()
AUDIO_CPP=f'{ROOT_DIR}/audio_cpp/audiocpp_cli{".exe" if OS_TYPE=="Windows" else ""}'
MODEL_FILE=f'{ROOT_DIR}/models/zipenhancer.safetensors'

def _remove_noise_audiocpp(*, input_file, output_file,logs_file=None):
    # 如果 audio_cpp
    from videotrans.util.help_down import down_audiocpp_bin,down_file_from_hf
    _write_log(logs_file,"downloading audiocpp_cli...")
    down_audiocpp_bin()
    down_file_from_hf(f'{ROOT_DIR}/models', urls=[ZIPENHANCER_HF.replace('https://huggingface.co','')])
    _st = time.time()

    cmd=[
        AUDIO_CPP,
        "--task",
        "s2s",
        "--family",
        "builtin_audio_utils",
        "--model",
        MODEL_FILE,
        "--load-option",
        "utility=zipenhancer",
        "--backend",
        "best",
        "--audio",
        input_file,
        "--out",
        Path(output_file).as_posix()
    ]

    try:
        _write_log(logs_file,"starting dense ...")
        exec_audiocpp(cmd)
        # subprocess.run(
        #     cmd, check=True, capture_output=True, text=True,
        #     encoding='utf-8', errors='ignore', creationflags=creationflags,
        #     cwd=Path(AUDIO_CPP).parent
        # )
        logger.debug(f'降噪成功完成，使用 audio.cpp 耗时:{int(time.time() - _st)}s，{cmd=}')
        return output_file, None
    except Exception as e:
        logger.exception(f"[降噪失败] audio.cpp {e}",exc_info=True)
        return False, f'{e}'


def remove_noise(*, input_file, output_file,logs_file=None,model_name='dpdfnet2.onnx', **kw):
    # (存在audiocpp_cli 或非Linux系统)
    if  model_name=='zipenhancer' and (Path(AUDIO_CPP).exists() or OS_TYPE !='Linux'):
        return _remove_noise_audiocpp(input_file=input_file, output_file=output_file,logs_file=logs_file)

    from videotrans.util._ffmpeg_runner import runffmpeg
    from videotrans.util.help_down import down_file_from_hf
    import numpy as np
    import sherpa_onnx, time
    import soundfile as sf

    _st = time.time()
    logger.debug(f'开始降噪，使用模型 {model_name}')
    _write_log(logs_file,f"downloading {model_name}...")
    down_file_from_hf(f'{ROOT_DIR}/models/onnx', urls=[DENOISE_URL_HF.replace('https://huggingface.co','').replace('{}',model_name)])


    def load_audio(filename: str):
        samples, sample_rate = sf.read(
            filename,
            always_2d=True,
            dtype="float32",
        )
        samples = np.ascontiguousarray(samples[:, 0])
        return samples, sample_rate

    try:
        config = sherpa_onnx.OfflineSpeechDenoiserConfig(
            model=sherpa_onnx.OfflineSpeechDenoiserModelConfig(
                dpdfnet=sherpa_onnx.OfflineSpeechDenoiserDpdfNetModelConfig(
                    model=f"{ROOT_DIR}/models/onnx/{model_name}",
                ),
                num_threads=int(settings.get('noise_separate_nums', 4)),
                debug=False,
                provider="cpu",
            )
        )

        assert config.validate(), config

        denoiser = sherpa_onnx.OfflineSpeechDenoiser(config)
        samples, sample_rate = load_audio(input_file)
        denoised = denoiser.run(samples, sample_rate)
        logger.debug(f'{input_file=}, {sample_rate=}, {denoised.sample_rate=}')
        tmp_name = Path(output_file).parent.as_posix() + f'/noise-{time.time()}.wav'
        sf.write(tmp_name, denoised.samples, denoised.sample_rate)
        runffmpeg(['-y', '-i', tmp_name, '-af', "volume=1.5", output_file])
        logger.debug(f'降噪成功完成，耗时:{int(time.time() - _st)}s')
        return output_file, None
    except Exception as e:
        msg = traceback.format_exc()
        logger.exception(f'降噪失败{e}:{msg}', exc_info=True)
        return False, f'{e}{msg}'


def fix_punc(*, text_dict_file: str, **kw):
    import sherpa_onnx
    model = f"{ROOT_DIR}/models/puntc/model.onnx"
    try:
        if not Path(model).is_file():
            raise ValueError(f"{model} does not exist")
        _st = time.time()
        logger.debug(f'开始标点恢复')
        text_dict_obj = json.loads(Path(text_dict_file).read_text(encoding='utf-8'))

        config = sherpa_onnx.OfflinePunctuationConfig(
            model=sherpa_onnx.OfflinePunctuationModelConfig(ct_transformer=model),
        )

        punct = sherpa_onnx.OfflinePunctuation(config)

        _text_dict_obj = {}
        for line, text in text_dict_obj.items():
            text_with_punct = punct.add_punctuation(text)
            _text_dict_obj[line] = text_with_punct
        Path(text_dict_file).write_text(json.dumps(_text_dict_obj), encoding="utf-8")
        logger.debug(f'标点恢复完成，耗时:{int(time.time() - _st)}s')
        return True, None
    except Exception as e:
        msg = traceback.format_exc()
        logger.exception(f'恢复标点失败{e}:{msg}', exc_info=True)
        return False, f'{e}{msg}'

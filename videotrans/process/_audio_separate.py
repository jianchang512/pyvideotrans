# -*- coding: utf-8 -*-

import shutil
import subprocess
import traceback, time,platform
from videotrans.configure.config import ROOT_DIR, logger, settings
from pathlib import Path

from videotrans.configure.constants import AUDIO_CPP_MELBAND, UVR_URL_HF
from videotrans.process._utils import _write_log
# Darwin Windows Linux
from videotrans.util.help_down import down_file_from_hf
from videotrans.util.help_misc import exec_audiocpp

OS_TYPE=platform.system()
AUDIO_CPP=f'{ROOT_DIR}/audio_cpp/audiocpp_cli{".exe" if OS_TYPE=="Windows" else ""}'
def vocal_bgm(*, input_file, vocal_file, instr_file, logs_file=None, uvr_models="UVR-MDX-NET-Inst_HQ_4",**kw):
    if uvr_models=='mel_band_roformer' and (Path(AUDIO_CPP).exists() or OS_TYPE !='Linux'):
        return _use_audiocpp(input_file=input_file, vocal_file=vocal_file, instr_file=instr_file,logs_file=logs_file
                                  )
    elif uvr_models=='mel_band_roformer':
        uvr_models='spleeter'
    _write_log(logs_file, "downloading models...")
    if uvr_models.startswith('spleeter'):
        down_file_from_hf(f'{ROOT_DIR}/models/onnx', [
            UVR_URL_HF.replace('{}','vocals.fp16.onnx').replace('https://huggingface.co',''),
            UVR_URL_HF.replace('{}','accompaniment.fp16.onnx').replace('https://huggingface.co','')
        ])
    else:
        down_file_from_hf(f'{ROOT_DIR}/models/onnx', [
            UVR_URL_HF.replace('{}',f'{uvr_models}.onnx').replace('https://huggingface.co','')
        ])
    if uvr_models.startswith('spleeter'):
        return vocal_bgm_spleeter(input_file=input_file, vocal_file=vocal_file, instr_file=instr_file,
                                  logs_file=logs_file)

    import numpy as np
    import sherpa_onnx
    import soundfile as sf

    def create_offline_source_separation():
        model = f"{ROOT_DIR}/models/onnx/{uvr_models}.onnx"

        if not Path(model).is_file():
            raise ValueError(f"{model} does not exist.")

        _cf = sherpa_onnx.OfflineSourceSeparationConfig(
            model=sherpa_onnx.OfflineSourceSeparationModelConfig(
                uvr=sherpa_onnx.OfflineSourceSeparationUvrModelConfig(
                    model=model,
                ),
                num_threads=int(settings.get('noise_separate_nums', 4)),
                debug=False,
                provider="cpu",
            )
        )
        if not _cf.validate():
            raise ValueError("Please check your config.")

        return sherpa_onnx.OfflineSourceSeparation(_cf)

    def load_audio(wav_file):
        samples, sample_rate = sf.read(wav_file, dtype="float32", always_2d=True)
        samples = np.transpose(samples)
        assert (
                samples.shape[1] > samples.shape[0]
        ), f"You should use (num_channels, num_samples). {samples.shape}"

        assert (
                samples.dtype == np.float32
        ), f"Expect np.float32 as dtype. Given: {samples.dtype}"

        return samples, sample_rate

    start = time.time()
    try:
        _write_log(logs_file, "vocals non_vocals...")
        sp = create_offline_source_separation()
        samples, sample_rate = load_audio(input_file)
        samples = np.ascontiguousarray(samples)
        output = sp.process(sample_rate=sample_rate, samples=samples)
        end = time.time()
        non_vocals = output.stems[0].data
        vocals = output.stems[1].data

        vocals = np.transpose(vocals)
        non_vocals = np.transpose(non_vocals)

        sf.write(vocal_file, vocals, samplerate=output.sample_rate)
        sf.write(instr_file, non_vocals, samplerate=output.sample_rate)

        elapsed_seconds = end - start
        _write_log(logs_file, f" use time:{elapsed_seconds:.3f}s")
        logger.debug(f'分离背景声和人声成功[{uvr_models}],耗时 {elapsed_seconds:.3f}s')
        return True, None
    except Exception as e:
        msg = traceback.format_exc()
        logger.exception(f"人声背景声分离失败{e}:{msg}", exc_info=True)
        return False, f'{e}{msg}'


def _use_audiocpp(*, input_file, vocal_file, instr_file,logs_file=None):
    # 如果 audio_cpp
    from videotrans.util.help_down import down_audiocpp_bin,down_file_from_hf
    _write_log(logs_file,"downloading audiocpp_cli...")
    down_audiocpp_bin()
    model_file=f'{ROOT_DIR}/models/mel-band-roformer-q8_0.gguf'
    # 下载 分离 模型
    if not Path(model_file).exists():
        _write_log(logs_file,"downloading models...")
        down_file_from_hf(
                f'{ROOT_DIR}/models',
                [AUDIO_CPP_MELBAND.replace('https://huggingface.co','')],
        )
    start = time.time()
    # 执行分离
    _parent=Path(vocal_file).parent.as_posix()
    cmd=[
        AUDIO_CPP,
        "--task",
        "sep",
        "--family",
        "mel_band_roformer",
        "--model",
        model_file,
        "--backend",
        "best",
        "--audio",
        input_file,
        "--out-dir",
        _parent
    ]
    # creationflags = subprocess.CREATE_NO_WINDOW if OS_TYPE == 'Windows' else 0
    try:
        # subprocess.run(
        #     cmd, check=True, capture_output=True, text=True,
        #     encoding='utf-8', errors='ignore', creationflags=creationflags
        # )
        exec_audiocpp(cmd)
        logger.debug(f"[分离人声和背景声完成] audio.cpp :{cmd=}，耗时 {time.time() - start}s")
        shutil.move(f'{_parent}/vocals.wav',vocal_file)
        shutil.move(f'{_parent}/instrumental.wav',instr_file)
        return True,None
    except Exception as e:
        logger.exception(f"[人声背景声分离失败] audio.cpp {e}", exc_info=True)
        return False, f'{e}'


def vocal_bgm_spleeter(*, input_file, vocal_file, instr_file, logs_file=None,**kw):
    import numpy as np
    import sherpa_onnx
    import soundfile as sf

    def create_offline_source_separation():
        vocals = f"{ROOT_DIR}/models/onnx/vocals.fp16.onnx"
        accompaniment = f"{ROOT_DIR}/models/onnx/accompaniment.fp16.onnx"
        config = sherpa_onnx.OfflineSourceSeparationConfig(
            model=sherpa_onnx.OfflineSourceSeparationModelConfig(
                spleeter=sherpa_onnx.OfflineSourceSeparationSpleeterModelConfig(
                    vocals=vocals,
                    accompaniment=accompaniment,
                ),
                num_threads=int(settings.get('noise_separate_nums', 4)),
                debug=False,
                provider="cpu",
            )
        )
        if not config.validate():
            raise ValueError("Please check your config.")

        return sherpa_onnx.OfflineSourceSeparation(config)

    def load_audio(wav_file):

        samples, sample_rate = sf.read(wav_file, dtype="float32", always_2d=True)
        samples = np.transpose(samples)
        assert (
                samples.shape[1] > samples.shape[0]
        ), f"You should use (num_channels, num_samples). {samples.shape}"

        assert (
                samples.dtype == np.float32
        ), f"Expect np.float32 as dtype. Given: {samples.dtype}"

        return samples, sample_rate

    start = time.time()
    try:
        sp = create_offline_source_separation()
        samples, sample_rate = load_audio(input_file)
        samples = np.ascontiguousarray(samples)

        output = sp.process(sample_rate=sample_rate, samples=samples)
        end = time.time()

        assert len(output.stems) == 2, len(output.stems)

        vocals = output.stems[0].data
        non_vocals = output.stems[1].data
        vocals = np.transpose(vocals)
        non_vocals = np.transpose(non_vocals)
        sf.write(vocal_file, vocals, samplerate=output.sample_rate)
        sf.write(instr_file, non_vocals, samplerate=output.sample_rate)

        elapsed_seconds = end - start
        _write_log(logs_file, f" use time:{elapsed_seconds:.3f}s")
        logger.debug(f"分离背景声和人声成功[spleeter],耗时: {elapsed_seconds:.3f}s")
        return True, None
    except Exception as e:
        msg = traceback.format_exc()
        logger.exception(f"人声背景声分离失败{e}:{msg}", exc_info=True)
        return False, f'{e}{msg}'

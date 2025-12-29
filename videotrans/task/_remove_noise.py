

"""
speech enhancement
models
https://github.com/k2-fsa/sherpa-onnx/releases/tag/speech-enhancement-models
"""

from videotrans.configure import config as cfg
import time
from pathlib import Path
from typing import Tuple

import numpy as np
import soundfile as sf
from videotrans.util import tools

def create_speech_denoiser(thread_nums=4):
    import sherpa_onnx
    model_filename = f"{cfg.ROOT_DIR}/models/onnx/gtcrn_simple.onnx"
    if not Path(model_filename).is_file():
        raise ValueError(
            "Please first download a model from "
            "https://github.com/k2-fsa/sherpa-onnx/releases/tag/speech-enhancement-models"
        )

    config = sherpa_onnx.OfflineSpeechDenoiserConfig(
        model=sherpa_onnx.OfflineSpeechDenoiserModelConfig(
            gtcrn=sherpa_onnx.OfflineSpeechDenoiserGtcrnModelConfig(
                model=model_filename
            ),
            debug=False,
            num_threads=thread_nums,
            provider="cpu",
        )
    )
    if not config.validate():
        print(config)
        raise ValueError("Errors in config. Please check previous error logs")
    return sherpa_onnx.OfflineSpeechDenoiser(config)


def load_audio(filename: str) -> Tuple[np.ndarray, int]:
    data, sample_rate = sf.read(
        filename,
        always_2d=True,
        dtype="float32",
    )
    data = data[:, 0]  # use only the first channel
    samples = np.ascontiguousarray(data)
    return samples, sample_rate


def run_remove(input_file,output_file,thread_nums=4):
    sd=None
    try:
        cfg.logger.info('开始降噪')
        sd = create_speech_denoiser(thread_nums)
        samples, sample_rate = load_audio(input_file)

        start = time.time()
        denoised = sd(samples, sample_rate)
        end = time.time()

        elapsed_seconds = end - start
        audio_duration = len(samples) / sample_rate
        real_time_factor = elapsed_seconds / audio_duration
        
        tmp_name = Path(output_file).parent.as_posix() + f'/noise-{time.time()}.wav'

        sf.write(tmp_name, denoised.samples, denoised.sample_rate)
        tools.runffmpeg(['-y', '-i', tmp_name, '-af', "volume=2.0,alimiter=limit=1.0", output_file])
        
        cfg.logger.info(f'降噪成功完成 {output_file}')
        return output_file
    except Exception as e:
        cfg.logger.exception(f'降噪时出错:{e}', exc_info=True)
        return input_file
    finally:
        import gc
        gc.collect()
        del sd

if __name__ == "__main__":
    run_remove("10.wav","10-no.wav")



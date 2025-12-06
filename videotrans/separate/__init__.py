"""
UVR for source separation.

 UVR model from
https://github.com/k2-fsa/sherpa-onnx/releases/tag/source-separation-models

"""
from videotrans.configure import config as cfg
import time
from pathlib import Path

import numpy as np
import sherpa_onnx
import soundfile as sf


def create_offline_source_separation(thread_nums=4):
    model = f"{cfg.ROOT_DIR}/models/onnx/UVR-MDX-NET-Inst_HQ_4.onnx"

    if not Path(model).is_file():
        raise ValueError(f"{model} does not exist.")

    config = sherpa_onnx.OfflineSourceSeparationConfig(
        model=sherpa_onnx.OfflineSourceSeparationModelConfig(
            uvr=sherpa_onnx.OfflineSourceSeparationUvrModelConfig(
                model=model,
            ),
            num_threads=thread_nums,
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


def run_sep(wav_file,vocal_file,instr_file,thread_nums=4):
    sp = create_offline_source_separation(thread_nums)
    samples, sample_rate = load_audio(wav_file)
    samples = np.ascontiguousarray(samples)

    cfg.logger.info("开始人声背景声分离")
    start = time.time()
    output = sp.process(sample_rate=sample_rate, samples=samples)
    end = time.time()

    assert len(output.stems) == 2, len(output.stems)

    non_vocals = output.stems[0].data
    vocals = output.stems[1].data
    # vocals.shape (num_channels, num_samples)

    vocals = np.transpose(vocals)
    non_vocals = np.transpose(non_vocals)

    # vocals.shape (num_samples,num_channels)

    sf.write(vocal_file, vocals, samplerate=output.sample_rate)
    sf.write(instr_file, non_vocals, samplerate=output.sample_rate)

    elapsed_seconds = end - start
    audio_duration = samples.shape[1] / sample_rate
    real_time_factor = elapsed_seconds / audio_duration
    cfg.logger.info(f"人声背景声分离完成：耗时/音频时长={real_time_factor}")
    try:
        import gc
        gc.collect()
        del sp
    except Exception:
        pass


if __name__ == "__main__":
    run_sep("10.wav","10-vocal.wav","10-instr.wav")
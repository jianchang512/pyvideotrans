# -*- coding: utf-8 -*-
import traceback, time, json
from videotrans.configure.config import ROOT_DIR, logger, settings
from pathlib import Path
from videotrans.process._audio_utils import _write_log


def vocal_bgm(*, input_file, vocal_file, instr_file, logs_file=None, is_cuda=False, uvr_models="UVR-MDX-NET-Inst_HQ_4"):
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
        sp = create_offline_source_separation()
        samples, sample_rate = load_audio(input_file)
        samples = np.ascontiguousarray(samples)
        _write_log(logs_file, "vocals non_vocals...")
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


def vocal_bgm_spleeter(*, input_file, vocal_file, instr_file, logs_file=None):
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

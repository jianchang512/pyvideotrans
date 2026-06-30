# -*- coding: utf-8 -*-
import traceback, time, json
from videotrans.configure.config import ROOT_DIR, logger, settings
from pathlib import Path
from videotrans.process._audio_utils import _write_log


def remove_noise(*, input_file, output_file, is_cuda=False, logs_file=None, device_index=0):
    import numpy as np
    import sherpa_onnx, time
    import soundfile as sf
    from videotrans.util import tools

    _st = time.time()
    logger.debug(f'开始降噪，使用模型 dpdfnet4')

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
                    model=f"{ROOT_DIR}/models/onnx/dpdfnet4.onnx",
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
        tools.runffmpeg(['-y', '-i', tmp_name, '-af', "volume=1.5", output_file])
        logger.debug(f'降噪成功完成，耗时:{int(time.time() - _st)}s')
        return output_file, None
    except Exception as e:
        msg = traceback.format_exc()
        logger.exception(f'降噪失败{e}:{msg}', exc_info=True)
        return False, f'{e}{msg}'


def fix_punc(*, text_dict_file: str, is_cuda=False, logs_file=None, device_index=0):
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

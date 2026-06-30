

#!/usr/bin/env python3

"""
This file shows how to use a non-streaming CTC model from NeMo
to decode files.

Please download model files from
https://github.com/k2-fsa/sherpa-onnx/releases/tag/asr-models


The example model supports 10 languages and it is converted from
https://catalog.ngc.nvidia.com/orgs/nvidia/teams/nemo/models/stt_multilingual_fastconformer_hybrid_large_pc
"""

from pathlib import Path

import sherpa_onnx
import soundfile as sf


def create_recognizer():
    encoder = "./models/fireredasr/encoder.int8.onnx"
    model = "./models/omnilingual/model.int8.onnx"
    tokens = "./models/omnilingual/tokens.txt"

    return  sherpa_onnx.OfflineRecognizer.from_omnilingual_asr_ctc(
            model=model,
            tokens=tokens,
            debug=False,
            num_threads=4
        )
    


def main():
    recognizer = create_recognizer()
    
    audio, sample_rate = sf.read('c:/users/c1/videos/0.wav', dtype="float32", always_2d=True)
    audio = audio[:, 0]  # only use the first channel

    # audio is a 1-D float32 numpy array normalized to the range [-1, 1]
    # sample_rate does not need to be 16000 Hz

    stream = recognizer.create_stream()
    stream.accept_waveform(sample_rate, audio)
    recognizer.decode_stream(stream)
    #print(wave_filename)
    print(stream.result)
    print('#########')
    print(stream.result.text)


if __name__ == "__main__":
    main()
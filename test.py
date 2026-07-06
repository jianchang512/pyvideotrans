"""
from omnivoice import OmniVoice
import soundfile as sf
import torch

model = OmniVoice.from_pretrained(
    "./models/models--k2-fsa--OmniVoice",
    #device_map="cuda:0",
    #dtype=torch.float16
)
# Apple Silicon users: use device_map="mps" instead
# Intel Arc GPU users: use device_map="xpu" instead

audio = model.generate(
    text="Hello, this is a test of zero-shot voice cloning.",
    ref_audio="cosy.wav",
    ref_text="希望你以后，能够做的比我还好哟！",
) # audio is a list of `np.ndarray` with shape (T,) at 24 kHz.

# If you don't want to input `ref_text` manually, you can directly omit the `ref_text`.
# The model will use Whisper ASR to auto-transcribe it.

sf.write("out0.wav", audio[0], 24000)


import sys
sys.exit(1)
"""
from videotrans.util.help_role import get_qwenttslocal_rolelist
import torch
from pathlib import Path
import traceback, json
from typing import Tuple, Union
from videotrans.configure.config import logger,ROOT_DIR
import soundfile as sf


from qwen_tts import Qwen3TTSModel
CUSTOM_VOICE= {"Vivian", "Serena", "Uncle_fu", "Dylan", "Eric", "Ryan", "Aiden", "Ono_anna", "Sohee"}



atten=None
device_map = 'cpu'
dtype=torch.float32

BASE_OBJ=None
CUSTOM_OBJ=None

   
BASE_OBJ=Qwen3TTSModel.from_pretrained(
    f"{ROOT_DIR}/models/models--Qwen--Qwen3-TTS-12Hz-0.6B-Base",
    device_map=device_map,
    dtype=dtype,
    attn_implementation=atten
)
kw={
    "text":"你好啊朋友们,要天天开心哦！",
    "language":"Chinese",
    "ref_audio":"./f5-tts/cosy.wav",
}
kw['ref_text']="希望你以后，能够做的比我还好哟！"
wavs, sr = BASE_OBJ.generate_voice_clone(**kw)
sf.write("ceshi2.wav", wavs[0], sr)


from qwen_asr import Qwen3ASRModel
model = Qwen3ASRModel.from_pretrained(
            f"./models/models--Qwen--Qwen3-ASR-0.6B",
            max_inference_batch_size=8,
            # Batch size limit for inference. -1 means unlimited. Smaller values can help avoid OOM.
            max_new_tokens=2048,  # Maximum number of tokens to generate. Set a larger value for long audio input.
        )
results = model.transcribe(
                audio=["10.wav"],
                language=[None],  # can also be set to None for automatic language detection
                return_time_stamps=False,
                #context=hotword.split(',') if hotword else []
            )
print(results)

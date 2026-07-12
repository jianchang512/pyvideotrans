from videotrans.configure import config
from omnivoice import OmniVoice
import soundfile as sf
import torch

model = OmniVoice.from_pretrained(
    "k2-fsa/OmniVoice",
    device_map="cpu",
    #dtype=torch.float16
)

audio = model.generate(
    text="你好啊，今天天气不错哦，挺风和日丽的，你说是不是啊我的朋友们.",
    ref_audio="./f5-tts/cosy.wav",
    ref_text="希望你以后，能够做的比我还好哟！",

    num_step=32,  # diffusion steps (or 16 for faster inference)
    speed=2,     # speed factor (>1.0 faster, <1.0 slower)
    duration=10.0, # fixed output duration in seconds (overrides speed)
    # ... more options
)
sf.write("out.wav", audio[0], 24000)

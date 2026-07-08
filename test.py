from videotrans.configure import config
from transformers import VitsModel, AutoTokenizer
import torch
model = VitsModel.from_pretrained("facebook/mms-tts-uig-script_arabic")
tokenizer = AutoTokenizer.from_pretrained("facebook/mms-tts-uig-script_arabic")

text = "ئامېرىكا ئارمىيەسى 1945-يىلى 7-ئاينىڭ 16-كۈنى دۇنيا بويىچە تۇنجى قېتىم« ئۈچنى بىر گەۋدىلەشتۈرۈش» يادرو سىنىقىنى ئېلىپ باردى"
inputs = tokenizer(text, return_tensors="pt")

import scipy
with torch.no_grad():
    output = model(**inputs).waveform
    scipy.io.wavfile.write("techno.wav", rate=model.config.sampling_rate, data=output)

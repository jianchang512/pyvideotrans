from videotrans.configure import config
from transformers import AutoModelForRNNT, AutoProcessor
from transformers.audio_utils import load_audio

model_id = "nvidia/nemotron-3.5-asr-streaming-0.6b"
processor = AutoProcessor.from_pretrained(model_id)
model = AutoModelForRNNT.from_pretrained(model_id, device_map="auto")

audio = load_audio(
    "10.wav",
    sampling_rate=processor.feature_extractor.sampling_rate,
)

# Condition on a known language ...
inputs = processor(audio, sampling_rate=processor.feature_extractor.sampling_rate, language="zh-CN")
inputs.to(model.device, dtype=model.dtype)
output = model.generate(**inputs, return_dict_in_generate=True)
print(processor.decode(output.sequences, skip_special_tokens=True))

# ... or let the model detect it and keep the emitted <xx-XX> language tag.
inputs = processor(audio, sampling_rate=processor.feature_extractor.sampling_rate) # equiv to ..., language="auto"
inputs.to(model.device, dtype=model.dtype)
output = model.generate(**inputs, return_dict_in_generate=True)
print(processor.decode(output.sequences, skip_special_tokens=False))
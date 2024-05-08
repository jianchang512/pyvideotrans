import argparse
import functools
import os

from faster_whisper import WhisperModel

'''
os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'

# 检查模型文件是否存在
# 加载模型
model = WhisperModel("large-v3-zh", device="cpu", compute_type="int8", 
                         local_files_only=False)
# 预热


# 语音识别
segments, info = model.transcribe("./1.wav", vad_filter=True,
                                  vad_parameters=dict(
                                      min_silence_duration_ms=200,
                                      max_speech_duration_s=6
                                  )
                             )
for segment in segments:
    text = segment.text
    print(f"[{round(segment.start, 2)} - {round(segment.end, 2)}]：{text}\n")
    
    
'''


from transformers import pipeline

transcriber = pipeline(
  "automatic-speech-recognition", 
  model="BELLE-2/Belle-whisper-large-v3-zh"
)

transcriber.model.config.forced_decoder_ids = (
  transcriber.tokenizer.get_decoder_prompt_ids(
    language="zh"
  )
)

transcription = transcriber("1.wav")

print(transcription)
    
import copy
import re
import time


from google import genai
from google.genai import types
import io
import mimetypes
import shutil
from datetime import datetime
import struct
from videotrans.configure import config
from videotrans.tts._base import BaseTTS
from videotrans.util import tools


# 强制单线程 防止远端限制出错

class GEMINITTS(BaseTTS):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.copydata = copy.deepcopy(self.queue_tts)
        self.proxies = self._set_proxy(type='set')


    # 强制单个线程执行，防止频繁并发失败
    def _exec(self):
        self._local_mul_thread()
    def _item_task(self, data_item: dict = None):
        if not self.is_test and tools.vail_file(data_item['filename']):
            print(f"cache is here================ {data_item['filename']}")
            return
        text = data_item['text'].strip()
        role = data_item['role']
        if not text:
            return
            
        speed = 1.0
        if self.rate:
            rate = float(self.rate.replace('%', '')) / 100
            speed += rate
        try:            
            self.generate_tts_segment(text,role,config.params['gemini_ttsmodel'],data_item['filename']+'.wav')
            tools.wav2mp3(data_item['filename']+'.wav', data_item['filename'])
            if self.inst and self.inst.precent < 80:
                self.inst.precent += 0.1
            self.error = ''
            self.has_done += 1
            self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')
        except Exception as e:
            if hasattr(e,'code') and e.code==429:
                error=f"[429] {e.message}"
            else:
                error = str(e)
            config.logger.exception(e, exc_info=True)
            self.error = error
            raise


    
    def generate_tts_segment(self,text,voice,model,file_name):
        def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
            """Generates a WAV file header for the given audio data and parameters.

            Args:
                audio_data: The raw audio data as a bytes object.
                mime_type: Mime type of the audio data.

            Returns:
                A bytes object representing the WAV file header.
            """
            parameters = parse_audio_mime_type(mime_type)
            bits_per_sample = parameters["bits_per_sample"]
            sample_rate = parameters["rate"]
            num_channels = 1
            data_size = len(audio_data)
            bytes_per_sample = bits_per_sample // 8
            block_align = num_channels * bytes_per_sample
            byte_rate = sample_rate * block_align
            chunk_size = 36 + data_size  # 36 bytes for header fields before data chunk size

            # http://soundfile.sapp.org/doc/WaveFormat/

            header = struct.pack(
                "<4sI4s4sIHHIIHH4sI",
                b"RIFF",          # ChunkID
                chunk_size,       # ChunkSize (total file size - 8 bytes)
                b"WAVE",          # Format
                b"fmt ",          # Subchunk1ID
                16,               # Subchunk1Size (16 for PCM)
                1,                # AudioFormat (1 for PCM)
                num_channels,     # NumChannels
                sample_rate,      # SampleRate
                byte_rate,        # ByteRate
                block_align,      # BlockAlign
                bits_per_sample,  # BitsPerSample
                b"data",          # Subchunk2ID
                data_size         # Subchunk2Size (size of audio data)
            )
            return header + audio_data

        def parse_audio_mime_type(mime_type: str) -> dict[str, int | None]:
            """Parses bits per sample and rate from an audio MIME type string.

            Assumes bits per sample is encoded like "L16" and rate as "rate=xxxxx".

            Args:
                mime_type: The audio MIME type string (e.g., "audio/L16;rate=24000").

            Returns:
                A dictionary with "bits_per_sample" and "rate" keys. Values will be
                integers if found, otherwise None.
            """
            bits_per_sample = 16
            rate = 24000

            # Extract rate from parameters
            parts = mime_type.split(";")
            for param in parts: # Skip the main type part
                param = param.strip()
                if param.lower().startswith("rate="):
                    try:
                        rate_str = param.split("=", 1)[1]
                        rate = int(rate_str)
                    except (ValueError, IndexError):
                        # Handle cases like "rate=" with no value or non-integer value
                        pass # Keep rate as default
                elif param.startswith("audio/L"):
                    try:
                        bits_per_sample = int(param.split("L", 1)[1])
                    except (ValueError, IndexError):
                        pass # Keep bits_per_sample as default if conversion fails

            return {"bits_per_sample": bits_per_sample, "rate": rate}

        def save_binary_file(file_name, data):
            f = open(file_name, "wb")
            f.write(data)
            f.close()
            print(f"File saved to to: {file_name}")

        client = genai.Client(
            api_key=config.params.get('gemini_key',''),
        )

        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=text),
                ],
            ),
        ]
        generate_content_config = types.GenerateContentConfig(
            temperature=1,
            response_modalities=[
                "audio",
            ],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice
                    )
                )
            ),
        )

        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            if (
                chunk.candidates is None
                or chunk.candidates[0].content is None
                or chunk.candidates[0].content.parts is None
            ):
                continue
            if chunk.candidates[0].content.parts[0].inline_data:
                inline_data = chunk.candidates[0].content.parts[0].inline_data
                data_buffer = inline_data.data
                file_extension = mimetypes.guess_extension(inline_data.mime_type)
                if file_extension is None:
                    file_extension = ".wav"
                    data_buffer = convert_to_wav(inline_data.data, inline_data.mime_type)
                save_binary_file(file_name, data_buffer)




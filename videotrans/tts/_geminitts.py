import mimetypes
import logging
import mimetypes
import struct
import time
from dataclasses import dataclass

from google import genai
from google.genai import types
from google.genai.errors import APIError
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure import config
from videotrans.configure._except import RetryRaise
from videotrans.tts._base import BaseTTS
from videotrans.util import tools

RETRY_NUMS = 2
RETRY_DELAY = 10


@dataclass
class GEMINITTS(BaseTTS):

    def __post_init__(self):
        super().__post_init__()
        self.proxies = self._set_proxy(type='set')

    def _exec(self):
        self.dub_nums = 1
        self._local_mul_thread()

    def _item_task(self, data_item: dict = None):
        @retry(retry=retry_if_not_exception_type(RetryRaise.NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
               wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
               after=after_log(config.logger, logging.INFO), retry_error_callback=RetryRaise._raise)
        def _run():
            if tools.vail_file(data_item['filename']):
                return
            role = data_item['role']
            speed = 1.0
            if self.rate:
                rate = float(self.rate.replace('%', '')) / 100
                speed += rate
            if self._exit() or tools.vail_file(data_item['filename']):
                return
            try:
                self.generate_tts_segment(data_item['text'], role, config.params['gemini_ttsmodel'],
                                          data_item['filename'] + '.wav')
                self.convert_to_wav(data_item['filename'] + '.wav', data_item['filename'])
                if self.inst and self.inst.precent < 80:
                    self.inst.precent += 0.1
                self.error = ''
                self.has_done += 1
                self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')
                return
            except APIError as e:
                config.logger.exception(e, exc_info=True)
                if e.code in [429, 500]:
                    self._signal(text=f"{data_item.get('line', '')}  {e.message}")
                    time.sleep(30)
                else:
                    self.error = str(e.message)
                    return
            except Exception as e:
                config.logger.exception(e, exc_info=True)
                self.error = str(e)
                self._signal(text=f"{data_item.get('line', '')} " + self.error)
                time.sleep(30)

        _run()

    def generate_tts_segment(self, text, voice, model, file_name):
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
                b"RIFF",  # ChunkID
                chunk_size,  # ChunkSize (total file size - 8 bytes)
                b"WAVE",  # Format
                b"fmt ",  # Subchunk1ID
                16,  # Subchunk1Size (16 for PCM)
                1,  # AudioFormat (1 for PCM)
                num_channels,  # NumChannels
                sample_rate,  # SampleRate
                byte_rate,  # ByteRate
                block_align,  # BlockAlign
                bits_per_sample,  # BitsPerSample
                b"data",  # Subchunk2ID
                data_size  # Subchunk2Size (size of audio data)
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
            for param in parts:  # Skip the main type part
                param = param.strip()
                if param.lower().startswith("rate="):
                    try:
                        rate_str = param.split("=", 1)[1]
                        rate = int(rate_str)
                    except (ValueError, IndexError):
                        # Handle cases like "rate=" with no value or non-integer value
                        pass  # Keep rate as default
                elif param.startswith("audio/L"):
                    try:
                        bits_per_sample = int(param.split("L", 1)[1])
                    except (ValueError, IndexError):
                        pass  # Keep bits_per_sample as default if conversion fails

            return {"bits_per_sample": bits_per_sample, "rate": rate}

        def save_binary_file(file_name, data):
            f = open(file_name, "wb")
            f.write(data)
            f.close()
            print(f"File saved to to: {file_name}")

        client = genai.Client(
            api_key=config.params.get('gemini_key', ''),
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

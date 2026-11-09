from dataclasses import dataclass

from videotrans.configure.config import params, tr
from videotrans.configure.constants import WORLDROUTER_MODELS
from videotrans.configure.excepts import StopTask, TranslateSrtError
from videotrans.translator._openaicompat import OpenAICampat
from videotrans.util._srt_parse import srt_str_to_listdict


@dataclass(repr=False)
class WorldRouter(OpenAICampat):
    def __post_init__(self):
        self.ainame = 'worldrouter'
        self.api_url = 'https://inference-api.worldrouter.ai/v1'
        self.api_key = params.get('worldrouter_key', '').strip()
        self.model_name = params.get('worldrouter_model', WORLDROUTER_MODELS.split(',')[0]).strip()
        # Let the shared implementation handle invalid values from edited config files.
        self.max_tokens = params.get('worldrouter_max_token', 16384)
        super().__post_init__()

    def _create_completion(self, kwargs):
        response = super()._create_completion(kwargs)
        if not response.choices:
            raise TranslateSrtError(tr("Translate result is empty"))
        choice = response.choices[0]
        if choice.finish_reason == 'length':
            raise StopTask(
                'WorldRouter: output token limit reached. Increase the maximum output '
                'tokens or reduce the number of subtitle lines per request.'
            )
        if not choice.message.content or not choice.message.content.strip():
            raise TranslateSrtError(tr("Translate result is empty"))
        return response

    def _item_task(self, data: str) -> str:
        if self._exit():
            return ''
        result = super()._item_task(data)
        if self._exit():
            return ''
        if self.aisendsrt:
            # Do not use get_subtitle_from_srt here: its plain-text fallback
            # invents timestamps, which would hide a malformed model response.
            source = srt_str_to_listdict(data)
            translated = srt_str_to_listdict(result)
            source_times = [(item['start_time'], item['end_time']) for item in source]
            translated_times = [(item['start_time'], item['end_time']) for item in translated]
            if (not translated or source_times != translated_times
                    or any(not item['text'].strip() for item in translated)):
                raise TranslateSrtError(
                    'WorldRouter: translated subtitles must preserve the original '
                    'block count and timestamps, with text in every block. '
                    'Try fewer subtitle lines per request.'
                )
        elif len(result.strip().splitlines()) != len(data.strip().splitlines()):
            raise TranslateSrtError(
                'WorldRouter: translated text must preserve the original line count. '
                'Try fewer subtitle lines per request.'
            )
        return result

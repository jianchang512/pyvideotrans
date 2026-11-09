import shutil
import sys
import types
import xml.etree.ElementTree as ET
from unittest.mock import MagicMock

import pytest

from videotrans import tts
from videotrans.configure import config
from videotrans.configure.config import app_cfg, settings
from videotrans.tts import _base
from videotrans.tts._base import BaseTTS
from videotrans.util.help_misc import vail_file

# _azuretts.py imports the Speech SDK and azure-core when it is loaded; the
# tests replace the SDK
try:
    import azure.cognitiveservices.speech  # noqa: F401
except ImportError:
    _azure = MagicMock()
    for _name in (
        "ResourceExistsError",
        "ClientAuthenticationError",
        "ResourceNotFoundError",
    ):
        setattr(_azure.core.exceptions, _name, type(_name, (Exception,), {}))
    sys.modules.update(
        {
            "azure": _azure,
            "azure.cognitiveservices": _azure.cognitiveservices,
            "azure.cognitiveservices.speech": _azure.cognitiveservices.speech,
            "azure.core": _azure.core,
            "azure.core.exceptions": _azure.core.exceptions,
        }
    )

from videotrans.tts import _azuretts  # noqa: E402


@pytest.fixture(autouse=True)
def ssml_sent(monkeypatch, tmp_path):
    """Stands in for the Speech SDK; returns the SSML of each line. Like the
    service, it only synthesizes SSML that is well-formed XML"""
    sent = []
    sdk = MagicMock()

    class SpeechSynthesizer:
        def __init__(self, speech_config=None, audio_config=None):
            self.filename = audio_config.filename

        def speak_ssml_async(self, ssml):
            sent.append(ssml)
            try:
                ET.fromstring(ssml)
            except ET.ParseError as e:
                details = types.SimpleNamespace(
                    reason=sdk.CancellationReason.Error, error_details=str(e)
                )
                result = types.SimpleNamespace(
                    reason=sdk.ResultReason.Canceled, cancellation_details=details
                )
            else:
                with open(self.filename, "wb") as f:
                    f.write(b"RIFF")
                result = types.SimpleNamespace(
                    reason=sdk.ResultReason.SynthesizingAudioCompleted
                )
            return types.SimpleNamespace(get=lambda: result)

    sdk.audio.AudioOutputConfig = types.SimpleNamespace
    sdk.SpeechSynthesizer = SpeechSynthesizer
    monkeypatch.setattr(_azuretts, "speechsdk", sdk)
    # the audio is converted to 48 kHz stereo with ffmpeg: copy it instead
    monkeypatch.setattr(
        BaseTTS,
        "convert_to_wav",
        staticmethod(lambda src, dst, extra=None: shutil.copyfile(src, dst)),
    )
    # skip dubbing_wait after each line
    monkeypatch.setattr(_base.time, "sleep", lambda s: None)
    # dub the text as it is: the English text normalization makes it lowercase
    monkeypatch.setattr(settings, "normal_text", False)
    # print progress messages instead of sending them to the GUI
    monkeypatch.setattr(app_cfg, "exec_mode", "cli")
    monkeypatch.setattr(config, "TEMP_DIR", (tmp_path / "tmp").as_posix())
    return sent


def _dub(tmp_path, texts):
    """Dubs the English lines with Azure TTS, as the dubbing stage of a task
    does; returns them"""
    lines = [
        {
            "line": i + 1,
            "text": text,
            "role": "Aria(Female)",
            "filename": (tmp_path / f"{i}.wav").as_posix(),
        }
        for i, text in enumerate(texts)
    ]
    tts.run(queue_tts=lines, language="en-US", uuid="test-uuid", tts_type=tts.AZURE_TTS)
    return lines


def _spoken(ssml):
    """The text of the SSML, as the service reads it"""
    return "".join(ET.fromstring(ssml).itertext()).strip()


# & and < start markup in XML: a line with them is sent escaped, and the service
# reads the line as it is in the subtitle
@pytest.mark.parametrize("text", ["Tom & Jerry", "Q&A starts now", "if a < b then"])
def test_line_that_is_not_well_formed_xml_is_escaped(tmp_path, ssml_sent, text):
    (line,) = _dub(tmp_path, [text])

    assert vail_file(line["filename"])
    assert [_spoken(ssml) for ssml in ssml_sent] == [text]


# a line that is well-formed XML is sent as it is, as before: with its entities
# and SSML tags
@pytest.mark.parametrize(
    "text, spoken",
    [
        ('He said "yes" and it\'s fine', 'He said "yes" and it\'s fine'),
        ("a > b", "a > b"),
        ("Tom &amp; Jerry", "Tom & Jerry"),
        ('Wait <break time="500ms"/> now', "Wait  now"),
        ("x</prosody><prosody rate='-50%'>y", "xy"),
    ],
)
def test_well_formed_line_is_sent_as_it_is(tmp_path, ssml_sent, text, spoken):
    (line,) = _dub(tmp_path, [text])

    assert vail_file(line["filename"])
    (ssml,) = ssml_sent
    assert f">{text}</prosody>" in ssml
    assert _spoken(ssml) == spoken


def test_line_with_an_ampersand_is_not_left_silent(tmp_path):
    # in a task with other lines, a line without audio gets silence instead
    lines = _dub(tmp_path, ["Good morning.", "Tom & Jerry are here.", "See you soon."])

    assert [vail_file(it["filename"]) for it in lines] == [True, True, True]

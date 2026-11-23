from videotrans import tts
from videotrans.configure.config import params
from videotrans.util.help_role import role_menu

# Set Reference Audio saves one "name.wav#reference text" per line; the TTS API channel
# offers these voices first and sends the chosen audio (and, in Gradio mode, its text) with the request
REFERENCE_AUDIOS = (
    "myvoice.wav#Hello there.\n"
    "en_female_1.wav#Diamond develops and manufactures its own coils."
)
REFERENCE_VOICES = ["No", "clone", "myvoice.wav", "en_female_1.wav"]


def _voices(monkeypatch, saved):
    monkeypatch.setitem(params, "f5tts_role", REFERENCE_AUDIOS)
    # the voice names entered in the TTS API window, separated by commas
    monkeypatch.setitem(params, "ttsapi_voice_role", saved)
    # the voices that the main window, Text-to-Speech, Multi-Speaker and the web UI
    # offer for the channel
    return role_menu(tts.TTS_API)


def test_voices_entered_in_the_tts_api_window_are_offered(monkeypatch):
    assert _voices(monkeypatch, "alex,bella") == REFERENCE_VOICES + ["alex", "bella"]


def test_spaces_line_breaks_and_empty_names_are_dropped(monkeypatch):
    # Save removes the line breaks of the field, Test keeps them
    assert _voices(monkeypatch, "alex, bella, ,\nchris,") == REFERENCE_VOICES + [
        "alex",
        "bella",
        "chris",
    ]


def test_without_voices_the_reference_audios_are_offered(monkeypatch):
    assert _voices(monkeypatch, "") == REFERENCE_VOICES

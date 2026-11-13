import pytest

from videotrans import tts
from videotrans.mainwin._actions_base_mode import WinActionBaseModeMixin

# the settings of Translation V/A that STT-Translation hides, outside More...:
# the dubbing channel, the voice and Listen, the alignment options, the
# subtitle embedding list, SecondarySTT and Output MP4 Only
TRANSLATION_VA = [
    "tts_text",
    "tts_type",
    "label_4",
    "voice_role",
    "listen_btn",
    "align_btn",
    "voice_autorate",
    "video_autorate",
    "remove_silent_mid",
    "align_sub_audio",
    "subtitle_type",
    "recogn2pass",
    "only_out_mp4",
]
# the settings that STT-Translation shows and Translation V/A hides when it is
# chosen: Save to SourceDir and OutputSubtitles
STT_TRANSLATION = ["copysrt_rawvideo", "output_srt_label", "output_srt"]


class _Widget:
    """Stands in for a widget of the main window and records whether it is
    shown. As a Qt widget, it can't be called."""

    def __init__(self):
        self.visible = True
        self.index = 0

    def show(self):
        self.visible = True

    def hide(self):
        self.visible = False

    def setVisible(self, visible):
        self.visible = bool(visible)

    def isHidden(self):
        return not self.visible

    def currentIndex(self):
        return self.index

    def setCurrentIndex(self, index):
        self.index = index

    def isChecked(self):
        # TTS Speedup and Slow Video are off, as by default
        return False

    def __getattr__(self, name):
        # setText(), setChecked(), setDisabled(), setSizes()...
        return lambda *args: None


class _Layout:
    """Stands in for the layouts of More... (the advanced settings), which
    both modes fold: they are empty here"""

    def count(self):
        return 0


class _Window:
    """Stands in for the main window: each widget is made the first time the
    code uses it"""

    width = 1200

    def __init__(self):
        self.widgets = {}
        self.bgm_layout = _Layout()
        self.dubb_thread_layout = _Layout()

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return self.widgets.setdefault(name, _Widget())


class _Actions(WinActionBaseModeMixin):
    def __init__(self, main):
        self.main = main


@pytest.mark.parametrize(
    "channel", [tts.EDGE_TTS, tts.AUDIOCPP_TTS], ids=["edge-tts", "audio.cpp"]
)
def test_translation_va_shows_its_settings_after_stt_translation(channel):
    window = _Window()
    # the TTS Service chosen in the main window
    window.tts_type.setCurrentIndex(channel)
    actions = _Actions(window)

    # STT-Translation, then Translation V/A, on the left of the main window
    actions.set_tiquzimu()
    assert window.voice_role.isHidden()
    actions.set_biaozhun()

    assert window.app_mode == "biaozhun"
    assert [n for n in TRANSLATION_VA if window.widgets[n].isHidden()] == []
    assert [n for n in STT_TRANSLATION if not window.widgets[n].isHidden()] == []
    # the list of audio.cpp models is shown with the audio.cpp channel only
    assert window.tts_model.isHidden() == (channel != tts.AUDIOCPP_TTS)

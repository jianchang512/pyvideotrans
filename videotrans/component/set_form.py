import PySide6
from PySide6 import QtWidgets
from PySide6.QtCore import QEvent
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog

from videotrans.configure import config
from videotrans.ui.ai302 import Ui_ai302form
from videotrans.ui.article import Ui_articleform
from videotrans.ui.azure import Ui_azureform
from videotrans.ui.azuretts import Ui_azurettsform
from videotrans.ui.baidu import Ui_baiduform
from videotrans.ui.ali import Ui_aliform
from videotrans.ui.chatgpt import Ui_chatgptform
from videotrans.ui.chattts import Ui_chatttsform
from videotrans.ui.claude import Ui_claudeform
from videotrans.ui.clone import Ui_cloneform
from videotrans.ui.cosyvoice import Ui_cosyvoiceform
from videotrans.ui.deepgram import Ui_deepgramform
from videotrans.ui.deepl import Ui_deeplform
from videotrans.ui.deeplx import Ui_deeplxform
from videotrans.ui.doubao import Ui_doubaoform
from videotrans.ui.downmodel import Ui_downmodel
from videotrans.ui.elevenlabs import Ui_elevenlabsform
from videotrans.ui.fanyi import Ui_fanyisrt
from videotrans.ui.fishtts import Ui_fishttsform
from videotrans.ui.formatcover import Ui_formatcover
from videotrans.ui.freeai import Ui_freeaiform
from videotrans.ui.gemini import Ui_geminiform
from videotrans.ui.getaudio import Ui_getaudio
from videotrans.ui.gptsovits import Ui_gptsovitsform
from videotrans.ui.hunliu import Ui_hunliu
from videotrans.ui.info import Ui_infoform
from videotrans.ui.kokoro import Ui_kokoroform
from videotrans.ui.libretranslate import Ui_libretranslateform
from videotrans.ui.localllm import Ui_localllmform
from videotrans.ui.openairecognapi import Ui_openairecognapiform
from videotrans.ui.openaitts import Ui_openaittsform
from videotrans.ui.ott import Ui_ottform
from videotrans.ui.peiyin import Ui_peiyin
from videotrans.ui.recogn import Ui_recogn
from videotrans.ui.recognapi import Ui_recognapiform
from videotrans.ui.stt import Ui_sttform
from videotrans.ui.separate import Ui_separateform
from videotrans.ui.setini import Ui_setini
from videotrans.ui.setlinerole import Ui_setlinerole
from videotrans.ui.srthebing import Ui_srthebing
from videotrans.ui.subtitle_editor import Ui_subtitleEditor
from videotrans.ui.subtitlescover import Ui_subtitlescover
from videotrans.ui.tencent import Ui_tencentform
from videotrans.ui.transapi import Ui_transapiform
from videotrans.ui.ttsapi import Ui_ttsapiform
from videotrans.ui.vasrt import Ui_vasrt
from videotrans.ui.videoandaudio import Ui_videoandaudio
from videotrans.ui.videoandsrt import Ui_videoandsrt
from videotrans.ui.volcenginetts import Ui_volcengineform
from videotrans.ui.watermark import Ui_watermark
from videotrans.ui.youtube import Ui_youtubeform
from videotrans.ui.zijiehuoshan import Ui_zijiehuoshanform
from videotrans.ui.f5tts import Ui_f5ttsform


class SetLineRole(QDialog, Ui_setlinerole):  # <===
    def __init__(self, parent=None):
        super(SetLineRole, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))

    def closeEvent(self, arg__1: PySide6.QtGui.QCloseEvent) -> None:
        del config.child_forms['linerolew']


class BaiduForm(QDialog, Ui_baiduform):  # <===
    def __init__(self, parent=None):
        super(BaiduForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class AliForm(QDialog, Ui_aliform):  # <===
    def __init__(self, parent=None):
        super(AliForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class YoutubeForm(QDialog, Ui_youtubeform):  # <===
    def __init__(self, parent=None):
        super(YoutubeForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class SeparateForm(QDialog, Ui_separateform):  # <===
    def __init__(self, parent=None):
        super(SeparateForm, self).__init__(parent)
        self.task = None
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))

    def closeEvent(self, event):
        config.separate_status = 'stop'
        if self.task:
            self.task.finish_event.emit("end")
            self.task = None
        self.hide()
        event.ignore()


class TencentForm(QDialog, Ui_tencentform):  # <===
    def __init__(self, parent=None):
        super(TencentForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class TtsapiForm(QDialog, Ui_ttsapiform):  # <===
    def __init__(self, parent=None):
        super(TtsapiForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class OpenAITTSForm(QDialog, Ui_openaittsform):  # <===
    def __init__(self, parent=None):
        super(OpenAITTSForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class RecognAPIForm(QDialog, Ui_recognapiform):  # <===
    def __init__(self, parent=None):
        super(RecognAPIForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class SttAPIForm(QDialog, Ui_sttform):  # <===
    def __init__(self, parent=None):
        super(SttAPIForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class DeepgramForm(QDialog, Ui_deepgramform):  # <===
    def __init__(self, parent=None):
        super(DeepgramForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class OpenaiRecognAPIForm(QDialog, Ui_openairecognapiform):  # <===
    def __init__(self, parent=None):
        super(OpenaiRecognAPIForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class ClaudeForm(QDialog, Ui_claudeform):  # <===
    def __init__(self, parent=None):
        super(ClaudeForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class LibreForm(QDialog, Ui_libretranslateform):  # <===
    def __init__(self, parent=None):
        super(LibreForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class TransapiForm(QDialog, Ui_transapiform):  # <===
    def __init__(self, parent=None):
        super(TransapiForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class GPTSoVITSForm(QDialog, Ui_gptsovitsform):  # <===
    def __init__(self, parent=None):
        super(GPTSoVITSForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class CosyVoiceForm(QDialog, Ui_cosyvoiceform):  # <===
    def __init__(self, parent=None):
        super(CosyVoiceForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class FishTTSForm(QDialog, Ui_fishttsform):  # <===
    def __init__(self, parent=None):
        super(FishTTSForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class F5TTSForm(QDialog, Ui_f5ttsform):  # <===
    def __init__(self, parent=None):
        super(F5TTSForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class AI302Form(QDialog, Ui_ai302form):  # <===
    def __init__(self, parent=None):
        super(AI302Form, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class SetINIForm(QtWidgets.QWidget, Ui_setini):  # <===
    def __init__(self, parent=None):
        super(SetINIForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class DeepLForm(QDialog, Ui_deeplform):  # <===
    def __init__(self, parent=None):
        super(DeepLForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class AzurettsForm(QDialog, Ui_azurettsform):  # <===
    def __init__(self, parent=None):
        super(AzurettsForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class ElevenlabsForm(QDialog, Ui_elevenlabsform):  # <===
    def __init__(self, parent=None):
        super(ElevenlabsForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class InfoForm(QDialog, Ui_infoform):  # <===
    def __init__(self, parent=None):
        super(InfoForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class ArticleForm(QDialog, Ui_articleform):  # <===
    def __init__(self, parent=None):
        super(ArticleForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class DeepLXForm(QDialog, Ui_deeplxform):  # <===
    def __init__(self, parent=None):
        super(DeepLXForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class OttForm(QDialog, Ui_ottform):  # <===
    def __init__(self, parent=None):
        super(OttForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class CloneForm(QDialog, Ui_cloneform):  # <===
    def __init__(self, parent=None):
        super(CloneForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))

class KokoroForm(QDialog, Ui_kokoroform):  # <===
    def __init__(self, parent=None):
        super(KokoroForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class ChatttsForm(QDialog, Ui_chatttsform):  # <===
    def __init__(self, parent=None):
        super(ChatttsForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class DoubaoForm(QDialog, Ui_doubaoform):  # <===
    def __init__(self, parent=None):
        super(DoubaoForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


# set chatgpt api and key
class ChatgptForm(QDialog, Ui_chatgptform):  # <===
    def __init__(self, parent=None):
        super(ChatgptForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class LocalLLMForm(QDialog, Ui_localllmform):  # <===
    def __init__(self, parent=None):
        super(LocalLLMForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class ZijiehuoshanForm(QDialog, Ui_zijiehuoshanform):  # <===
    def __init__(self, parent=None):
        super(ZijiehuoshanForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class HebingsrtForm(QtWidgets.QWidget, Ui_srthebing):  # <===
    def __init__(self, parent=None):
        super(HebingsrtForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class GeminiForm(QDialog, Ui_geminiform):  # <===
    def __init__(self, parent=None):
        super(GeminiForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class FreeAIForm(QDialog, Ui_freeaiform):  # <===
    def __init__(self, parent=None):
        super(FreeAIForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class AzureForm(QDialog, Ui_azureform):  # <===
    def __init__(self, parent=None):
        super(AzureForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class WatermarkForm(QDialog, Ui_watermark):  # <===
    def __init__(self, parent=None):
        super(WatermarkForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class VolcEngineTTSForm(QDialog, Ui_volcengineform):  # <===
    def __init__(self, parent=None):
        super(VolcEngineTTSForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class GetaudioForm(QDialog, Ui_getaudio):  # <===
    def __init__(self, parent=None):
        super(GetaudioForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class HunliuForm(QDialog, Ui_hunliu):  # <===
    def __init__(self, parent=None):
        super(HunliuForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class VASForm(QDialog, Ui_vasrt):  # <===
    def __init__(self, parent=None):
        super(VASForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class Fanyisrt(QtWidgets.QWidget, Ui_fanyisrt):
    def __init__(self, parent=None):
        super(Fanyisrt, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))
    def changeEvent(self, event):
        """
        重写 changeEvent 方法，监听窗口激活状态变化
        """
        if event.type() == QEvent.ActivationChange:
            if self.isActiveWindow():
                # 在这里执行窗口激活时需要做的操作
                self.aisendsrt.setChecked(config.settings.get('aisendsrt'))
        super(Fanyisrt, self).changeEvent(event) # 调用父类的实现，确保默认行为被处理


class Recognform(QtWidgets.QWidget, Ui_recogn):  # <===
    def __init__(self, parent=None):
        super(Recognform, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class Peiyinform(QtWidgets.QWidget, Ui_peiyin):  # <===
    def __init__(self, parent=None):
        super(Peiyinform, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class Videoandaudioform(QDialog, Ui_videoandaudio):  # <===
    def __init__(self, parent=None):
        super(Videoandaudioform, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class Videoandsrtform(QDialog, Ui_videoandsrt):  # <===
    def __init__(self, parent=None):
        super(Videoandsrtform, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class DownloadModelForm(QDialog, Ui_downmodel):  # <===
    def __init__(self, parent=None):
        super(DownloadModelForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class FormatcoverForm(QDialog, Ui_formatcover):  # <===
    def __init__(self, parent=None):
        super(FormatcoverForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class SubtitlescoverForm(QDialog, Ui_subtitlescover):  # <===
    def __init__(self, parent=None):
        super(SubtitlescoverForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class SubtitleEditer(Ui_subtitleEditor):  # <===
    def __init__(self):
        super(SubtitleEditer, self).__init__()
        # self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))

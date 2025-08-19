import PySide6
import os
from PySide6 import QtWidgets
from PySide6.QtCore import QEvent
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog

from videotrans.configure import config
from videotrans.ui.ai302 import Ui_ai302form
from videotrans.ui.ali import Ui_aliform
from videotrans.ui.article import Ui_articleform
from videotrans.ui.azure import Ui_azureform
from videotrans.ui.azuretts import Ui_azurettsform
from videotrans.ui.baidu import Ui_baiduform
from videotrans.ui.chatgpt import Ui_chatgptform
from videotrans.ui.chatterbox import Ui_chatterboxform
from videotrans.ui.chattts import Ui_chatttsform
from videotrans.ui.claude import Ui_claudeform
from videotrans.ui.clone import Ui_cloneform
from videotrans.ui.cosyvoice import Ui_cosyvoiceform
from videotrans.ui.deepgram import Ui_deepgramform
from videotrans.ui.deepl import Ui_deeplform
from videotrans.ui.deeplx import Ui_deeplxform
from videotrans.ui.deepseek import Ui_deepseekform
from videotrans.ui.doubao import Ui_doubaoform
from videotrans.ui.elevenlabs import Ui_elevenlabsform
from videotrans.ui.f5tts import Ui_f5ttsform
from videotrans.ui.fanyi import Ui_fanyisrt
from videotrans.ui.fishtts import Ui_fishttsform
from videotrans.ui.formatcover import Ui_formatcover
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
from videotrans.ui.openrouter import Ui_openrouterform
from videotrans.ui.ott import Ui_ottform
from videotrans.ui.parakeet import Ui_parakeetform
from videotrans.ui.peiyin import Ui_peiyin
from videotrans.ui.peiyinrole import Ui_peiyinrole
from videotrans.ui.qwentts import Ui_qwenttsform
from videotrans.ui.recogn import Ui_recogn
from videotrans.ui.recognapi import Ui_recognapiform
from videotrans.ui.separate import Ui_separateform
from videotrans.ui.setini import Ui_setini
from videotrans.ui.setlinerole import Ui_setlinerole
from videotrans.ui.siliconflow import Ui_siliconflowform
from videotrans.ui.srthebing import Ui_srthebing
from videotrans.ui.stt import Ui_sttform
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
from videotrans.ui.zhipuai import Ui_zhipuaiform
from videotrans.ui.zijiehuoshan import Ui_zijiehuoshanform


# ==================== 字幕行自定义控件 ====================
class SubtitleRowWidget(QtWidgets.QWidget):
    """自定义的单条字幕行控件"""

    def __init__(self, index, start_time, end_time, text, parent=None):
        super().__init__(parent)
        self.sub_index = index
        self.start_time = start_time
        self.end_time = end_time
        self.text = text

        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)

        self.index_label = QtWidgets.QLabel(f"{self.sub_index}")
        self.checkbox = QtWidgets.QCheckBox()
        self.checkbox.setFixedWidth(30)

        self.role_label = QtWidgets.QLabel("[未分配角色]")
        self.role_label.setFixedWidth(150)
        self.role_label.setObjectName(f"role_label_{index}")

        time_str = f"{start_time} --> {end_time}"
        self.time_label = QtWidgets.QLabel(time_str)
        self.time_label.setFixedWidth(200)

        self.text_label = QtWidgets.QLabel(text)
        self.text_label.setWordWrap(True)

        self.layout.addWidget(self.index_label)
        self.layout.addWidget(self.checkbox)
        self.layout.addWidget(self.role_label)
        self.layout.addWidget(self.time_label)
        self.layout.addWidget(self.text_label)
        self.layout.addStretch()


class Peiyinformrole(QtWidgets.QWidget, Ui_peiyinrole):
    def __init__(self, parent=None):
        super(Peiyinformrole, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))

        # 新增的信号连接
        self.clear_button.clicked.connect(self.clear_all_ui)
        self.assign_role_button.clicked.connect(self.assign_role_to_selected)

        # 当 hecheng_role 的内容改变时，同步到 tmp_rolelist
        self.hecheng_role.model().rowsInserted.connect(self.sync_roles_to_tmp_list)
        self.hecheng_role.model().rowsRemoved.connect(self.sync_roles_to_tmp_list)

    def sync_roles_to_tmp_list(self, parent=None, first=None, last=None):
        """同步 hecheng_role 的角色列表到 tmp_rolelist"""
        self.tmp_rolelist.clear()
        roles = [self.hecheng_role.itemText(i) for i in range(self.hecheng_role.count())]
        if roles:
            self.tmp_rolelist.addItems(roles)

    def clear_subtitle_area(self):
        """清空字幕显示区域"""
        while self.subtitle_layout.count():
            child = self.subtitle_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.subtitles.clear()

    def clear_all_ui(self):
        """点击清空按钮时执行"""
        self.srt_path = None
        self.subtitles.clear()
        config.dubbing_role.clear()

        self.clear_subtitle_area()
        self.hecheng_importbtn.setText("导入SRT文件..." if config.defaulelang == 'zh' else 'Import SRT file...')
        self.loglabel.setText("")
        print("UI and data cleared.")

    def reset_assigned_roles(self):
        """重置所有字幕行已分配的角色"""
        config.dubbing_role.clear()
        for i in range(self.subtitle_layout.count()):
            widget = self.subtitle_layout.itemAt(i).widget()
            if isinstance(widget, SubtitleRowWidget):
                widget.role_label.setText("[未分配角色]")
        print("Assigned roles have been reset.")

    def parse_and_display_srt(self, srt_path):
        """解析SRT文件并在UI上显示"""
        self.clear_all_ui()  # 导入新文件前先清空
        self.srt_path = srt_path

        try:
            from videotrans.util import tools
            subs = tools.get_subtitle_from_srt(srt_path)
            self.subtitles = subs
            for sub in subs:
                row_widget = SubtitleRowWidget(sub['line'], sub['startraw'], sub['endraw'], sub['text'])
                self.subtitle_layout.addWidget(row_widget)

            self.hecheng_importbtn.setText(f"已导入: {os.path.basename(srt_path)}")

        except Exception as e:
            self.clear_all_ui()
            raise

    def assign_role_to_selected(self):
        """为选中的行分配角色"""
        selected_role = self.tmp_rolelist.currentText()
        from videotrans.util import tools
        from videotrans.configure import config
        if not selected_role or selected_role in ['-', 'No']:
            tools.show_error(
                "请先在下拉列表中选择一个有效的角色。" if config.defaulelang == 'zh' else 'Please select a valid role from the dropdown list.',
                False)
            return

        assigned_count = 0
        for i in range(self.subtitle_layout.count()):
            widget = self.subtitle_layout.itemAt(i).widget()
            if isinstance(widget, SubtitleRowWidget) and widget.checkbox.isChecked():
                # 更新UI
                widget.role_label.setText(selected_role)
                # 更新全局配置
                config.dubbing_role[widget.sub_index] = selected_role
                # 分配后取消勾选
                widget.checkbox.setChecked(False)
                assigned_count += 1

        if assigned_count > 0:
            print(f"Assigned role '{selected_role}' to {assigned_count} lines.")
            print(f"Current config.dubbing_role: {config.dubbing_role}")
        else:
            QtWidgets.QMessageBox.information(self, "提示", "没有选中任何字幕行。")


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


class OpenrouterForm(QDialog, Ui_openrouterform):  # <===
    def __init__(self, parent=None):
        super(OpenrouterForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class AliForm(QDialog, Ui_aliform):  # <===
    def __init__(self, parent=None):
        super(AliForm, self).__init__(parent)
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


class QwenTTSForm(QDialog, Ui_qwenttsform):  # <===
    def __init__(self, parent=None):
        super(QwenTTSForm, self).__init__(parent)
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


class ChatterboxForm(QDialog, Ui_chatterboxform):  # <===
    def __init__(self, parent=None):
        super(ChatterboxForm, self).__init__(parent)
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


class ParakeetForm(QDialog, Ui_parakeetform):  # <===
    def __init__(self, parent=None):
        super(ParakeetForm, self).__init__(parent)
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


class ZhipuAIForm(QDialog, Ui_zhipuaiform):  # <===
    def __init__(self, parent=None):
        super(ZhipuAIForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class DeepseekForm(QDialog, Ui_deepseekform):  # <===
    def __init__(self, parent=None):
        super(DeepseekForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class SiliconflowForm(QDialog, Ui_siliconflowform):  # <===
    def __init__(self, parent=None):
        super(SiliconflowForm, self).__init__(parent)
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
        super(Fanyisrt, self).changeEvent(event)  # 调用父类的实现，确保默认行为被处理


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

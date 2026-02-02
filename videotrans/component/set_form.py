import re

import PySide6
import os
from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog, QFrame,QTableView, QAbstractItemView, QHeaderView, QCheckBox,QTableWidgetItem

from videotrans.configure import config
from videotrans.configure.config import tr
from videotrans.ui.ai302 import Ui_ai302form
from videotrans.ui.ali import Ui_aliform
from videotrans.ui.azure import Ui_azureform
from videotrans.ui.azuretts import Ui_azurettsform
from videotrans.ui.baidu import Ui_baiduform
from videotrans.ui.chatgpt import Ui_chatgptform
from videotrans.ui.chatterbox import Ui_chatterboxform
from videotrans.ui.chattts import Ui_chatttsform
from videotrans.ui.doubao2 import Ui_doubao2form
from videotrans.ui.clone import Ui_cloneform
from videotrans.ui.cosyvoice import Ui_cosyvoiceform
from videotrans.ui.deepgram import Ui_deepgramform
from videotrans.ui.deepl import Ui_deeplform
from videotrans.ui.deeplx import Ui_deeplxform
from videotrans.ui.deepseek import Ui_deepseekform
from videotrans.ui.qwenmt import Ui_qwenmtform
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
from videotrans.ui.qwenasrlocal import Ui_qwenasrlocalform
from videotrans.ui.peiyin import Ui_peiyin
from videotrans.ui.peiyinrole import Ui_peiyinrole
from videotrans.ui.qwentts import Ui_qwenttsform
from videotrans.ui.qwenttslocal import Ui_qwenttslocal
from videotrans.ui.recogn import Ui_recogn
from videotrans.ui.recognapi import Ui_recognapiform
from videotrans.ui.separate import Ui_separateform
from videotrans.ui.setini import Ui_setini
from videotrans.ui.setlinerole import Ui_setlinerole
from videotrans.ui.siliconflow import Ui_siliconflowform
from videotrans.ui.srthebing import Ui_srthebing
from videotrans.ui.stt import Ui_sttform
from videotrans.ui.whisperx import Ui_whisperx
from videotrans.ui.subtitlescover import Ui_subtitlescover
from videotrans.ui.tencent import Ui_tencentform
from videotrans.ui.transapi import Ui_transapiform
from videotrans.ui.ttsapi import Ui_ttsapiform
from videotrans.ui.minimaxi import Ui_minimaxiform
from videotrans.ui.vasrt import Ui_vasrt
from videotrans.ui.videoandaudio import Ui_videoandaudio
from videotrans.ui.videoandsrt import Ui_videoandsrt
from videotrans.ui.volcenginetts import Ui_volcengineform
from videotrans.ui.watermark import Ui_watermark
from videotrans.ui.zhipuai import Ui_zhipuaiform
from videotrans.ui.zijiehuoshan import Ui_zijiehuoshanform
from videotrans.ui.zijierecognmodel import Ui_zijierecognform


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


class MinimaxiForm(QDialog, Ui_minimaxiform):  # <===
    def __init__(self, parent=None):
        super(MinimaxiForm, self).__init__(parent)
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

class WhisperXAPIForm(QDialog, Ui_whisperx):  # <===
    def __init__(self, parent=None):
        super(WhisperXAPIForm, self).__init__(parent)
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
class QwenttsLocalForm(QDialog, Ui_qwenttslocal):  # <===
    def __init__(self, parent=None):
        super(QwenttsLocalForm, self).__init__(parent)
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
    def event(self, event: QtCore.QEvent) -> bool:
        """
        重写 event 方法来捕获窗口事件
        """
        # 检查事件的类型是否为窗口激活事件
        if event.type() == QtCore.QEvent.Type.WindowActivate:
            # 如果是，就调用我们的更新方法
            self.update_ui()

        # 对于所有其他事件，必须调用父类的 event() 方法来确保它们被正常处理
        return super().event(event)

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

class QwenasrlocalForm(QDialog, Ui_qwenasrlocalform):  # <===
    def __init__(self, parent=None):
        super(QwenasrlocalForm, self).__init__(parent)
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


class QwenmtForm(QDialog, Ui_qwenmtform):  # <===
    def __init__(self, parent=None):
        super(QwenmtForm, self).__init__(parent)
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


class VolcEngineTTSForm(QDialog, Ui_volcengineform):  # <===
    def __init__(self, parent=None):
        super(VolcEngineTTSForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))

class Doubao2TTSForm(QDialog, Ui_doubao2form):  # <===
    def __init__(self, parent=None):
        super(Doubao2TTSForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))
class ZijierecognmodelForm(QDialog, Ui_zijierecognform):  # <===
    def __init__(self, parent=None):
        super(ZijierecognmodelForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class WatermarkForm(QtWidgets.QWidget, Ui_watermark):  # <===
    def __init__(self, parent=None):
        super(WatermarkForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class HebingsrtForm(QtWidgets.QWidget, Ui_srthebing):  # <===
    def __init__(self, parent=None):
        super(HebingsrtForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


## start

# ==================== 说话人行控件 ====================
class SpkRowWidget(QtWidgets.QWidget):
    def __init__(self, spk_name, parent=None):
        super().__init__(parent)
        self.spk_name = spk_name
        self.layout = QtWidgets.QHBoxLayout(self)
        self.checkbox = QtWidgets.QCheckBox()
        self.spk_name_label = QtWidgets.QPushButton(self.spk_name)
        self.spk_name_label.setStyleSheet("""QPushButton{background-color:transparent} QPushButton:hover{color:#148CD2}""")
        self.spk_name_label.setCursor(Qt.PointingHandCursor)
        self.spk_name_label.clicked.connect(self.set_checkbox)
        self.spk_name_role = QtWidgets.QLabel('')
        self.layout.addWidget(self.spk_name_label)
        self.layout.addWidget(self.checkbox)
        self.layout.addWidget(self.spk_name_role)
        self.layout.addStretch()
    def set_checkbox(self):
        self.checkbox.toggle()


class Peiyinformrole(QtWidgets.QWidget, Ui_peiyinrole):
    def __init__(self, parent=None):
        super(Peiyinformrole, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))
        self.spk_role={} # key=说话人，设置的音色名
        self.spk_lines={} # key=说话人，value=[]行数

        # 信号连接
        self.clear_button.clicked.connect(self.clear_all_ui)
        self.assign_role_button.clicked.connect(self.assign_role_to_selected)
        self.assign_role_button2.clicked.connect(self.assign_role_to_spk)

        self.hecheng_role.model().rowsInserted.connect(self.sync_roles_to_tmp_list)
        self.hecheng_role.model().rowsRemoved.connect(self.sync_roles_to_tmp_list)

    def sync_roles_to_tmp_list(self, parent=None, first=None, last=None):
        """同步 hecheng_role 的角色列表到 tmp_rolelist"""
        self.tmp_rolelist.clear()
        self.tmp_rolelist2.clear()
        roles = [self.hecheng_role.itemText(i) for i in range(self.hecheng_role.count())]
        if roles:
            self.tmp_rolelist.addItems(roles)
            self.tmp_rolelist2.addItems(roles)

    def clear_subtitle_area(self):
        """清空字幕显示区域"""
        self.subtitle_table.setRowCount(0)
        self.subtitle_table.clearContents()
        
        # 清空说话人区域
        if self.subtitle_layout2 and self.subtitle_layout2.count() > 0:
            while self.subtitle_layout2.count():
                child = self.subtitle_layout2.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
        self.subtitles.clear()

    def clear_all_ui(self):
        """点击清空按钮时执行"""
        self.srt_path = None
        self.spk_lines={}
        self.spk_role={}
        self.subtitle_scroll_area2.setVisible(False)
        self.spk_tips.setVisible(False)
        self.assign_role_label2.setVisible(False)
        self.tmp_rolelist2.setVisible(False)
        self.assign_role_button2.setVisible(False)
        self.subtitles.clear()
        config.dubbing_role.clear()

        self.clear_subtitle_area()
        self.hecheng_importbtn.setText(tr("Import SRT file..."))
        self.loglabel.setText("")

    def reset_assigned_roles(self):
        """重置所有字幕行已分配的角色"""
        config.dubbing_role.clear()
        for row in range(self.subtitle_table.rowCount()):
            # 第3列是角色列
            self.subtitle_table.item(row, 3).setText(tr('Default Role'))

    def parse_and_display_srt(self, srt_path):
        """解析SRT文件并在UI上显示 (表格优化版)"""
        self.clear_all_ui()
        self.srt_path = srt_path

        try:
            from videotrans.util import tools
            subs = tools.get_subtitle_from_srt(srt_path)

            patter_str=r'(?:\s*?\[)((?:spk|speaker|说话人|speaker_|\w{1,10})\s*?\d*?)(?:\])\s*?[:：]?'
            
            # 关闭排序和更新以提高插入速度
            self.subtitle_table.setSortingEnabled(False)
            self.subtitle_table.setRowCount(len(subs)) # 预先分配行数
            
            # 准备数据，避免在循环中重复计算
            default_role_text = tr('Default Role')
            
            for row_idx, sub in enumerate(subs):
                spk_name = None
                match = re.match(patter_str, sub['text'].strip(), flags=re.I)
                if match:
                    spk_name = match.group(1)
                    sub['text'] = sub['text'][len(match.group(0)):]
                
                if spk_name:
                    if spk_name not in self.spk_role:
                        self.spk_role[spk_name] = None
                    if spk_name not in self.spk_lines:
                        self.spk_lines[spk_name] = []
                    self.spk_lines[spk_name].append(sub["line"])
                
                # 计算时长
                duration = round((sub['end_time'] - sub['start_time']) / 1000, 2)
                time_str = f"({duration}s) {sub['startraw']}->{sub['endraw']}"

                # 1. ID
                item_id = QTableWidgetItem(str(sub['line']))
                item_id.setTextAlignment(Qt.AlignCenter)
                item_id.setFlags(item_id.flags() & ~Qt.ItemIsEditable) 
                self.subtitle_table.setItem(row_idx, 0, item_id)

                # 2. Checkbox
                item_check = QTableWidgetItem()
                item_check.setCheckState(Qt.Unchecked)
                self.subtitle_table.setItem(row_idx, 1, item_check)

                # 3. Time
                item_time = QTableWidgetItem(time_str)
                item_time.setFlags(item_time.flags() & ~Qt.ItemIsEditable)
                self.subtitle_table.setItem(row_idx, 2, item_time)

                # 4. Role
                item_role = QTableWidgetItem(default_role_text)
                item_role.setFlags(item_role.flags() & ~Qt.ItemIsEditable)
                self.subtitle_table.setItem(row_idx, 3, item_role)

                # 5. Speaker
                item_spk = QTableWidgetItem(spk_name if spk_name else "")
                item_spk.setFlags(item_spk.flags() & ~Qt.ItemIsEditable)
                self.subtitle_table.setItem(row_idx, 4, item_spk)

                # 6. Text
                item_text = QTableWidgetItem(sub['text'])
                item_text.setToolTip(sub['text'])
                self.subtitle_table.setItem(row_idx, 5, item_text)
                

            # 调整行高以适应内容
            self.subtitle_table.resizeRowsToContents()
            
            # 处理说话人区域 
            if self.spk_role:
                self.subtitle_scroll_area2.setVisible(True)
                self.assign_role_label2.setVisible(True)
                self.tmp_rolelist2.setVisible(True)
                self.assign_role_button2.setVisible(True)
                self.spk_tips.setVisible(True)
                for ix, spk in enumerate(self.spk_role.keys()):
                    spk_widget = SpkRowWidget(spk)
                    self.subtitle_layout2.addWidget(spk_widget, ix // 6, ix % 6)
                self.container_frame.setStyleSheet("""QFrame#container_frame{border: 1px solid #455364;}""")
            
            self.hecheng_importbtn.setText(f"{os.path.basename(srt_path)}")
            self.subtitles = subs

        except Exception as e:
            self.clear_all_ui()
            raise

    def assign_role_to_selected(self):
        """为选中的行分配角色"""
        selected_role = self.tmp_rolelist.currentText()
        from videotrans.util import tools
        from videotrans.configure import config
        
        if not selected_role:
            tools.show_error(tr("Please select a valid role from the dropdown list."))
            return

        assigned_count = 0
        default_role_text = tr('Default Role')
        
        # 遍历表格行
        for row in range(self.subtitle_table.rowCount()):
            check_item = self.subtitle_table.item(row, 1)
            if check_item and check_item.checkState() == Qt.Checked:
                # 获取字幕 Index
                try:
                    sub_index = int(self.subtitle_table.item(row, 0).text())
                except:
                    continue
                
                role_item = self.subtitle_table.item(row, 3)

                # 更新全局配置
                if selected_role in ['-', 'No']:
                    role_item.setText(default_role_text)
                    try:
                        del config.dubbing_role[sub_index]
                    except:
                        pass
                else:
                    config.dubbing_role[sub_index] = selected_role
                    role_item.setText(selected_role)
                
                # 分配后取消勾选
                check_item.setCheckState(Qt.Unchecked)
                assigned_count += 1

        if assigned_count < 1:
            QtWidgets.QMessageBox.information(self, "Error", tr("Choose at least one subtitle"))

    def assign_role_to_spk(self):
        """为选中的说话人分配角色"""
        selected_role = self.tmp_rolelist2.currentText()
        from videotrans.util import tools
        from videotrans.configure import config
        if not selected_role:
            tools.show_error(tr("Please select a valid role from the dropdown list."))
            return

        assigned_count = 0
        for i in range(self.subtitle_layout2.count()):
            widget = self.subtitle_layout2.itemAt(i).widget()
            if isinstance(widget, SpkRowWidget) and widget.checkbox.isChecked():
                # 更新UI
                _spk = widget.spk_name_label.text()
                if selected_role in ['-', 'No']:
                    self.spk_role[_spk] = None
                    widget.spk_name_role.setText('')
                else:
                    self.spk_role[_spk] = selected_role
                    widget.spk_name_role.setText(selected_role)
                
                # 分配后取消勾选
                widget.checkbox.setChecked(False)
                assigned_count += 1
                
                # 更新全局配置中的每一行
                for line in self.spk_lines.get(_spk, []):
                    if selected_role in ['-', 'No']:
                        try:
                            del config.dubbing_role[line]
                        except:
                            pass
                    else:
                        config.dubbing_role[line] = selected_role
                    
                    try:
                        row_idx = line - 1
                        if 0 <= row_idx < self.subtitle_table.rowCount():
                            # 确认一下ID是否匹配
                            if self.subtitle_table.item(row_idx, 0).text() == str(line):
                                display_role = tr('Default Role') if selected_role in ['-', 'No'] else selected_role
                                self.subtitle_table.item(row_idx, 3).setText(display_role)
                    except:
                        pass

        if assigned_count < 1:
            QtWidgets.QMessageBox.information(self, "Error", tr("Select at least one speaker"))



## end


class SeparateForm(QtWidgets.QWidget, Ui_separateform):  # <===
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


class GetaudioForm(QtWidgets.QWidget, Ui_getaudio):  # <===
    def __init__(self, parent=None):
        super(GetaudioForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class HunliuForm(QtWidgets.QWidget, Ui_hunliu):  # <===
    def __init__(self, parent=None):
        super(HunliuForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class VASForm(QtWidgets.QWidget, Ui_vasrt):  # <===
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


class Videoandaudioform(QtWidgets.QWidget, Ui_videoandaudio):  # <===
    def __init__(self, parent=None):
        super(Videoandaudioform, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class Videoandsrtform(QtWidgets.QWidget, Ui_videoandsrt):  # <===
    def __init__(self, parent=None):
        super(Videoandsrtform, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class FormatcoverForm(QtWidgets.QWidget, Ui_formatcover):  # <===
    def __init__(self, parent=None):
        super(FormatcoverForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))


class SubtitlescoverForm(QtWidgets.QWidget, Ui_subtitlescover):  # <===
    def __init__(self, parent=None):
        super(SubtitlescoverForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))

import re
import os
from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog, QTableWidgetItem

from videotrans.configure.config import ROOT_DIR,tr,app_cfg,settings,params,TEMP_DIR,logger,defaulelang,HOME_DIR
from videotrans.util import tools
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
from videotrans.ui.peiyin import Ui_peiyin
from videotrans.ui.peiyinrole import Ui_peiyinrole
from videotrans.ui.qwentts import Ui_qwenttsform
from videotrans.ui.qwenttslocal import Ui_qwenttslocal
from videotrans.ui.recogn import Ui_recogn
from videotrans.ui.recognapi import Ui_recognapiform
from videotrans.ui.separate import Ui_separateform
from videotrans.ui.setini import Ui_setini

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


class CommonBaseMixin:
    def _setup_common_ui(self):
        self.setWindowIcon(QIcon(f"{ROOT_DIR}/videotrans/styles/icon.ico"))
        if hasattr(self, 'setupUi'):
            self.setupUi(self)


class QDialogBase(QDialog,CommonBaseMixin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_common_ui()


class QWidgetBase(QtWidgets.QWidget,CommonBaseMixin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_common_ui()


class BaiduForm(QDialogBase, Ui_baiduform):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


class OpenrouterForm(QDialogBase, Ui_openrouterform):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


class AliForm(QDialogBase, Ui_aliform):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


class TencentForm(QDialogBase, Ui_tencentform):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


class TtsapiForm(QDialogBase, Ui_ttsapiform):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


class MinimaxiForm(QDialogBase, Ui_minimaxiform):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


class OpenAITTSForm(QDialogBase, Ui_openaittsform):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


class QwenTTSForm(QDialogBase, Ui_qwenttsform):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


class RecognAPIForm(QDialogBase, Ui_recognapiform):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


class SttAPIForm(QDialogBase, Ui_sttform):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)

class WhisperXAPIForm(QDialogBase, Ui_whisperx):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


class DeepgramForm(QDialogBase, Ui_deepgramform):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


class OpenaiRecognAPIForm(QDialogBase, Ui_openairecognapiform):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)



class LibreForm(QDialogBase, Ui_libretranslateform):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


class TransapiForm(QDialogBase, Ui_transapiform):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)

class GPTSoVITSForm(QDialogBase, Ui_gptsovitsform):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


class ChatterboxForm(QDialogBase, Ui_chatterboxform):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


class CosyVoiceForm(QDialogBase, Ui_cosyvoiceform):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)
class QwenttsLocalForm(QDialogBase, Ui_qwenttslocal):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


class FishTTSForm(QDialogBase, Ui_fishttsform):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


class F5TTSForm(QDialogBase, Ui_f5ttsform):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


class AI302Form(QDialogBase, Ui_ai302form):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


class DeepLForm(QDialogBase, Ui_deeplform):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


class AzurettsForm(QDialogBase, Ui_azurettsform):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


class ElevenlabsForm(QDialogBase, Ui_elevenlabsform):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


class InfoForm(QDialogBase, Ui_infoform):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)



class DeepLXForm(QDialogBase, Ui_deeplxform):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


class OttForm(QDialogBase, Ui_ottform):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


class CloneForm(QDialogBase, Ui_cloneform):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


class ParakeetForm(QDialogBase, Ui_parakeetform):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)



class KokoroForm(QDialogBase, Ui_kokoroform):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


class ChatttsForm(QDialogBase, Ui_chatttsform):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


class DoubaoForm(QDialogBase, Ui_doubaoform):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


# set chatgpt api and key
class ChatgptForm(QDialogBase, Ui_chatgptform):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


class LocalLLMForm(QDialogBase, Ui_localllmform):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


class ZijiehuoshanForm(QDialogBase, Ui_zijiehuoshanform):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


class GeminiForm(QDialogBase, Ui_geminiform):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


class ZhipuAIForm(QDialogBase, Ui_zhipuaiform):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


class DeepseekForm(QDialogBase, Ui_deepseekform):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


class QwenmtForm(QDialogBase, Ui_qwenmtform):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


class SiliconflowForm(QDialogBase, Ui_siliconflowform):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


class AzureForm(QDialogBase, Ui_azureform):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


class VolcEngineTTSForm(QDialogBase, Ui_volcengineform):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)

class Doubao2TTSForm(QDialogBase, Ui_doubao2form):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)
class ZijierecognmodelForm(QDialogBase, Ui_zijierecognform):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)




class SetINIForm(QWidgetBase, Ui_setini):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)

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


class WatermarkForm(QWidgetBase, Ui_watermark):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


class HebingsrtForm(QWidgetBase, Ui_srthebing):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


## start

# ==================== 说话人行控件 ====================
class SpkRowWidget(QWidgetBase):
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


class Peiyinformrole(QWidgetBase, Ui_peiyinrole):
    def __init__(self, parent=None):
        super().__init__(parent)
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
        app_cfg.dubbing_role.clear()

        self.clear_subtitle_area()
        self.hecheng_importbtn.setText(tr("Import SRT file..."))
        self.loglabel.setText("")

    def reset_assigned_roles(self):
        """重置所有字幕行已分配的角色"""
        app_cfg.dubbing_role.clear()
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
                        del app_cfg.dubbing_role[sub_index]
                    except:
                        pass
                else:
                    app_cfg.dubbing_role[sub_index] = selected_role
                    role_item.setText(selected_role)
                
                # 分配后取消勾选
                check_item.setCheckState(Qt.Unchecked)
                assigned_count += 1

        if assigned_count < 1:
            QtWidgets.QMessageBox.information(self, "Error", tr("Choose at least one subtitle"))

    def assign_role_to_spk(self):
        """为选中的说话人分配角色"""
        selected_role = self.tmp_rolelist2.currentText()

        if not selected_role:
            tools.show_error(tr("Please select a valid role from the dropdown list."))
            return
        
        self.subtitle_table.setUpdatesEnabled(False)
        self.subtitle_table.blockSignals(True)
        assigned_count = 0
        try:
        
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
                                del app_cfg.dubbing_role[line]
                            except:
                                pass
                        else:
                            app_cfg.dubbing_role[line] = selected_role
                        
                        try:
                            row_idx = line - 1
                            if 0 <= row_idx < self.subtitle_table.rowCount():
                                # 确认一下ID是否匹配
                                if self.subtitle_table.item(row_idx, 0).text() == str(line):
                                    display_role = tr('Default Role') if selected_role in ['-', 'No'] else selected_role
                                    self.subtitle_table.item(row_idx, 3).setText(display_role)
                        except:
                            pass

        finally:
            self.subtitle_table.blockSignals(False)
            self.subtitle_table.setUpdatesEnabled(True)
        if assigned_count < 1:
            QtWidgets.QMessageBox.information(self, "Error", tr("Select at least one speaker"))



class SeparateForm(QWidgetBase, Ui_separateform):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)
        self.task = None

    def closeEvent(self, event):
        if self.task:
            self.task.finish_event.emit("end")
            self.task = None
        self.hide()
        event.ignore()


class GetaudioForm(QWidgetBase, Ui_getaudio):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


class HunliuForm(QWidgetBase, Ui_hunliu):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


class VASForm(QWidgetBase, Ui_vasrt):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


class Fanyisrt(QWidgetBase, Ui_fanyisrt):
    def __init__(self, parent=None):
        super().__init__(parent)

    def changeEvent(self, event):
        """
        重写 changeEvent 方法，监听窗口激活状态变化
        """
        if event.type() == QEvent.ActivationChange:
            if self.isActiveWindow():
                # 在这里执行窗口激活时需要做的操作
                self.aisendsrt.setChecked(settings.get('aisendsrt'))
        super(Fanyisrt, self).changeEvent(event)  # 调用父类的实现，确保默认行为被处理


class Recognform(QWidgetBase, Ui_recogn):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


class Peiyinform(QWidgetBase, Ui_peiyin):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


class Videoandaudioform(QWidgetBase, Ui_videoandaudio):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


class Videoandsrtform(QWidgetBase, Ui_videoandsrt):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


class FormatcoverForm(QWidgetBase, Ui_formatcover):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)


class SubtitlescoverForm(QWidgetBase, Ui_subtitlescover):  # <===
    def __init__(self, parent=None):
        super().__init__(parent)

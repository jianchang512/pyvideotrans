# -*- coding: utf-8 -*-
"""
set_form.py — Provider settings form classes with lazy UI loading.

All simple form classes (Base + Ui_xxx mixin) are created on demand via
module-level __getattr__, so importing this module does NOT load any UI files.
Custom classes (Peiyinformrole, SetINIForm, SeparateForm, Fanyisrt, SpkRowWidget)
are defined explicitly because they have extra logic.
"""
import os
import re

from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog, QTableWidgetItem

from videotrans.configure.config import ROOT_DIR, tr, app_cfg, settings


# ---------------------------------------------------------------------------
# Base classes (always loaded)
# ---------------------------------------------------------------------------
class CommonBaseMixin:
    def _setup_common_ui(self):
        self.setWindowIcon(QIcon(f"{ROOT_DIR}/videotrans/styles/icon.ico"))
        if hasattr(self, 'setupUi'):
            self.setupUi(self)

    def _bind_ui_methods(self, ui_cls):
        """Bind all Ui_xxx methods (setupUi, retranslateUi, update_ui, etc.) to this class."""
        for attr in dir(ui_cls):
            if attr.startswith('__'):
                continue
            val = getattr(ui_cls, attr, None)
            if callable(val):
                setattr(self.__class__, attr, val)


class QDialogBase(QDialog, CommonBaseMixin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_common_ui()


class QWidgetBase(QtWidgets.QWidget, CommonBaseMixin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_common_ui()


# ---------------------------------------------------------------------------
# Lazy-loaded simple forms:  (className, baseClass, ui_module, ui_class_name)
# ---------------------------------------------------------------------------
_LAZY_FORMS = {
    "AI302Form": ("QDialogBase", "videotrans.ui.ai302", "Ui_ai302form"),
    "AliForm": ("QDialogBase", "videotrans.ui.ali", "Ui_aliform"),
    "AzureForm": ("QDialogBase", "videotrans.ui.azure", "Ui_azureform"),
    "AzurettsForm": ("QDialogBase", "videotrans.ui.azuretts", "Ui_azurettsform"),
    "BaiduForm": ("QDialogBase", "videotrans.ui.baidu", "Ui_baiduform"),
    "CambASRForm": ("QDialogBase", "videotrans.ui.cambasr", "Ui_cambasrform"),
    "CambTTSForm": ("QDialogBase", "videotrans.ui.cambtts", "Ui_cambttsform"),
    "CambTransForm": ("QDialogBase", "videotrans.ui.cambtrans", "Ui_cambtransform"),
    "ChatgptForm": ("QDialogBase", "videotrans.ui.chatgpt", "Ui_chatgptform"),
    "ChatterboxForm": ("QDialogBase", "videotrans.ui.chatterbox", "Ui_chatterboxform"),
    "ChatttsForm": ("QDialogBase", "videotrans.ui.chattts", "Ui_chatttsform"),
    "CloneForm": ("QDialogBase", "videotrans.ui.clone", "Ui_cloneform"),
    "CosyVoiceForm": ("QDialogBase", "videotrans.ui.cosyvoice", "Ui_cosyvoiceform"),
    "DeepLForm": ("QDialogBase", "videotrans.ui.deepl", "Ui_deeplform"),
    "DeepLXForm": ("QDialogBase", "videotrans.ui.deeplx", "Ui_deeplxform"),
    "DeepgramForm": ("QDialogBase", "videotrans.ui.deepgram", "Ui_deepgramform"),
    "DeepseekForm": ("QDialogBase", "videotrans.ui.deepseek", "Ui_deepseekform"),
    "Doubao2TTSForm": ("QDialogBase", "videotrans.ui.doubao2", "Ui_doubao2form"),
    "ElevenlabsForm": ("QDialogBase", "videotrans.ui.elevenlabs", "Ui_elevenlabsform"),
    "FishTTSForm": ("QDialogBase", "videotrans.ui.fishtts", "Ui_fishttsform"),
    "FormatcoverForm": ("QWidgetBase", "videotrans.ui.formatcover", "Ui_formatcover"),
    "GPTSoVITSForm": ("QDialogBase", "videotrans.ui.gptsovits", "Ui_gptsovitsform"),
    "GeminiForm": ("QDialogBase", "videotrans.ui.gemini", "Ui_geminiform"),
    "GetaudioForm": ("QWidgetBase", "videotrans.ui.getaudio", "Ui_getaudio"),
    "GradiowinForm": ("QDialogBase", "videotrans.ui.gradiowin", "Ui_gradiowinform"),
    "HebingsrtForm": ("QWidgetBase", "videotrans.ui.srthebing", "Ui_srthebing"),
    "HunliuForm": ("QWidgetBase", "videotrans.ui.hunliu", "Ui_hunliu"),
    "InfoForm": ("QDialogBase", "videotrans.ui.info", "Ui_infoform"),
    "KokoroForm": ("QDialogBase", "videotrans.ui.kokoro", "Ui_kokoroform"),
    "LibreForm": ("QDialogBase", "videotrans.ui.libretranslate", "Ui_libretranslateform"),
    "LocalLLMForm": ("QDialogBase", "videotrans.ui.localllm", "Ui_localllmform"),
    "MiniMaxForm": ("QDialogBase", "videotrans.ui.minimax", "Ui_minimaxform"),
    "MinimaxiForm": ("QDialogBase", "videotrans.ui.minimaxi", "Ui_minimaxiform"),
    "OpenAITTSForm": ("QDialogBase", "videotrans.ui.openaitts", "Ui_openaittsform"),
    "OpenaiRecognAPIForm": ("QDialogBase", "videotrans.ui.openairecognapi", "Ui_openairecognapiform"),
    "OpenrouterForm": ("QDialogBase", "videotrans.ui.openrouter", "Ui_openrouterform"),
    "ParakeetForm": ("QDialogBase", "videotrans.ui.parakeet", "Ui_parakeetform"),
    "Peiyinform": ("QWidgetBase", "videotrans.ui.peiyin", "Ui_peiyin"),
    "QwenTTSForm": ("QDialogBase", "videotrans.ui.qwentts", "Ui_qwenttsform"),
    "QwenmtForm": ("QDialogBase", "videotrans.ui.qwenmt", "Ui_qwenmtform"),
    "QwenttsLocalForm": ("QDialogBase", "videotrans.ui.qwenttslocal", "Ui_qwenttslocal"),
    "RecognAPIForm": ("QDialogBase", "videotrans.ui.recognapi", "Ui_recognapiform"),
    "Recognform": ("QWidgetBase", "videotrans.ui.recogn", "Ui_recogn"),
    "RefaudioForm": ("QDialogBase", "videotrans.ui.refaudio", "Ui_refform"),
    "SiliconflowForm": ("QDialogBase", "videotrans.ui.siliconflow", "Ui_siliconflowform"),
    "SttAPIForm": ("QDialogBase", "videotrans.ui.stt", "Ui_sttform"),
    "SubtitlescoverForm": ("QWidgetBase", "videotrans.ui.subtitlescover", "Ui_subtitlescover"),
    "TencentForm": ("QDialogBase", "videotrans.ui.tencent", "Ui_tencentform"),
    "TransapiForm": ("QDialogBase", "videotrans.ui.transapi", "Ui_transapiform"),
    "TtsapiForm": ("QDialogBase", "videotrans.ui.ttsapi", "Ui_ttsapiform"),
    "VASForm": ("QWidgetBase", "videotrans.ui.vasrt", "Ui_vasrt"),
    "Videoandaudioform": ("QWidgetBase", "videotrans.ui.videoandaudio", "Ui_videoandaudio"),
    "Videoandsrtform": ("QWidgetBase", "videotrans.ui.videoandsrt", "Ui_videoandsrt"),
    "VolcEngineTTSForm": ("QDialogBase", "videotrans.ui.volcenginetts", "Ui_volcengineform"),
    "WatermarkForm": ("QWidgetBase", "videotrans.ui.watermark", "Ui_watermark"),
    "WhisperXAPIForm": ("QDialogBase", "videotrans.ui.whisperx", "Ui_whisperx"),
    "XAITTSForm": ("QDialogBase", "videotrans.ui.xaitts", "Ui_xaittsform"),
    "XiaomiForm": ("QDialogBase", "videotrans.ui.xiaomi", "Ui_xiaomiform"),
    "ZhipuAIForm": ("QDialogBase", "videotrans.ui.zhipuai", "Ui_zhipuaiform"),
    "ZijiehuoshanForm": ("QDialogBase", "videotrans.ui.zijiehuoshan", "Ui_zijiehuoshanform"),
    "ZijierecognmodelForm": ("QDialogBase", "videotrans.ui.zijierecognmodel", "Ui_zijierecognform"),
}

_BASE_MAP = {"QDialogBase": QDialogBase, "QWidgetBase": QWidgetBase}
_created = {}


def __getattr__(name):
    if name in _LAZY_FORMS:
        if name not in _created:
            base_name, ui_mod, ui_cls_name = _LAZY_FORMS[name]
            import importlib
            ui_module = importlib.import_module(ui_mod)
            ui_cls = getattr(ui_module, ui_cls_name)
            base = _BASE_MAP[base_name]

            def _make_init(ui_cls_ref):
                def __init__(self, parent=None):
                    super(type(self), self).__init__(parent)
                return __init__

            _created[name] = type(name, (base, ui_cls), {"__init__": _make_init(ui_cls)})
        return _created[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def __dir__():
    public = list(_LAZY_FORMS.keys())
    public += [
        "QDialogBase", "QWidgetBase", "CommonBaseMixin",
        "SpkRowWidget", "Peiyinformrole", "SetINIForm",
        "SeparateForm", "Fanyisrt",
    ]
    return public


# ---------------------------------------------------------------------------
# Custom classes (have extra logic beyond simple Base + Ui_xxx)
# ---------------------------------------------------------------------------

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


class Peiyinformrole(QWidgetBase):
    def __init__(self, parent=None):
        from videotrans.ui.peiyinrole import Ui_peiyinrole
        self._bind_ui_methods(Ui_peiyinrole)
        super().__init__(parent)
        self.spk_role = {}
        self.spk_lines = {}
        self.clear_button.clicked.connect(self.clear_all_ui)
        self.assign_role_button.clicked.connect(self.assign_role_to_selected)
        self.assign_role_button2.clicked.connect(self.assign_role_to_spk)
        self.hecheng_role.model().rowsInserted.connect(self.sync_roles_to_tmp_list)
        self.hecheng_role.model().rowsRemoved.connect(self.sync_roles_to_tmp_list)

    def sync_roles_to_tmp_list(self, parent=None, first=None, last=None):
        self.tmp_rolelist.clear()
        self.tmp_rolelist2.clear()
        roles = [self.hecheng_role.itemText(i) for i in range(self.hecheng_role.count())]
        if roles:
            self.tmp_rolelist.addItems(roles)
            self.tmp_rolelist2.addItems(roles)

    def clear_subtitle_area(self):
        self.subtitle_table.setRowCount(0)
        self.subtitle_table.clearContents()
        if self.subtitle_layout2 and self.subtitle_layout2.count() > 0:
            while self.subtitle_layout2.count():
                child = self.subtitle_layout2.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
        self.subtitles.clear()

    def clear_all_ui(self):
        self.srt_path = None
        self.spk_lines = {}
        self.spk_role = {}
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
        app_cfg.dubbing_role.clear()
        for row in range(self.subtitle_table.rowCount()):
            self.subtitle_table.item(row, 3).setText(tr('Default Role'))

    def parse_and_display_srt(self, srt_path):
        self.clear_all_ui()
        self.srt_path = srt_path
        try:
            from videotrans.util import tools
            subs = tools.get_subtitle_from_srt(srt_path)
            patter_str = r'(?:\s*?\[)((?:spk|speaker|说话人|speaker_|\w{1,10})\s*?\d*?)(?:\])\s*?[:：]?'
            self.subtitle_table.setSortingEnabled(False)
            self.subtitle_table.setRowCount(len(subs))
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
                duration = round((sub['end_time'] - sub['start_time']) / 1000, 2)
                time_str = f"({duration}s) {sub['startraw']}->{sub['endraw']}"
                item_id = QTableWidgetItem(str(sub['line']))
                item_id.setTextAlignment(Qt.AlignCenter)
                item_id.setFlags(item_id.flags() & ~Qt.ItemIsEditable)
                self.subtitle_table.setItem(row_idx, 0, item_id)
                item_check = QTableWidgetItem()
                item_check.setCheckState(Qt.Unchecked)
                self.subtitle_table.setItem(row_idx, 1, item_check)
                item_time = QTableWidgetItem(time_str)
                item_time.setFlags(item_time.flags() & ~Qt.ItemIsEditable)
                self.subtitle_table.setItem(row_idx, 2, item_time)
                item_role = QTableWidgetItem(default_role_text)
                item_role.setFlags(item_role.flags() & ~Qt.ItemIsEditable)
                self.subtitle_table.setItem(row_idx, 3, item_role)
                item_spk = QTableWidgetItem(spk_name if spk_name else "")
                item_spk.setFlags(item_spk.flags() & ~Qt.ItemIsEditable)
                self.subtitle_table.setItem(row_idx, 4, item_spk)
                item_text = QTableWidgetItem(sub['text'])
                item_text.setToolTip(sub['text'])
                self.subtitle_table.setItem(row_idx, 5, item_text)
            self.subtitle_table.resizeRowsToContents()
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
        selected_role = self.tmp_rolelist.currentText()
        from videotrans.util import tools
        if not selected_role:
            tools.show_error(tr("Please select a valid role from the dropdown list."))
            return
        assigned_count = 0
        default_role_text = tr('Default Role')
        for row in range(self.subtitle_table.rowCount()):
            check_item = self.subtitle_table.item(row, 1)
            if check_item and check_item.checkState() == Qt.Checked:
                try:
                    sub_index = int(self.subtitle_table.item(row, 0).text())
                except Exception:
                    continue
                role_item = self.subtitle_table.item(row, 3)
                if selected_role in ['-', 'No']:
                    role_item.setText(default_role_text)
                    try:
                        del app_cfg.dubbing_role[sub_index]
                    except Exception:
                        pass
                else:
                    app_cfg.dubbing_role[sub_index] = selected_role
                    role_item.setText(selected_role)
                check_item.setCheckState(Qt.Unchecked)
                assigned_count += 1
        if assigned_count < 1:
            QtWidgets.QMessageBox.information(self, "Error", tr("Choose at least one subtitle"))

    def assign_role_to_spk(self):
        selected_role = self.tmp_rolelist2.currentText()
        if not selected_role:
            from videotrans.util.help_misc import show_error
            show_error(tr("Please select a valid role from the dropdown list."))
            return
        self.subtitle_table.setUpdatesEnabled(False)
        self.subtitle_table.blockSignals(True)
        assigned_count = 0
        try:
            for i in range(self.subtitle_layout2.count()):
                widget = self.subtitle_layout2.itemAt(i).widget()
                if isinstance(widget, SpkRowWidget) and widget.checkbox.isChecked():
                    _spk = widget.spk_name_label.text()
                    if selected_role in ['-', 'No']:
                        self.spk_role[_spk] = None
                        widget.spk_name_role.setText('')
                    else:
                        self.spk_role[_spk] = selected_role
                        widget.spk_name_role.setText(selected_role)
                    widget.checkbox.setChecked(False)
                    assigned_count += 1
                    for line in self.spk_lines.get(_spk, []):
                        if selected_role in ['-', 'No']:
                            try:
                                del app_cfg.dubbing_role[line]
                            except Exception:
                                pass
                        else:
                            app_cfg.dubbing_role[line] = selected_role
                        try:
                            row_idx = line - 1
                            if 0 <= row_idx < self.subtitle_table.rowCount():
                                if self.subtitle_table.item(row_idx, 0).text() == str(line):
                                    display_role = tr('Default Role') if selected_role in ['-', 'No'] else selected_role
                                    self.subtitle_table.item(row_idx, 3).setText(display_role)
                        except Exception:
                            pass
        finally:
            self.subtitle_table.blockSignals(False)
            self.subtitle_table.setUpdatesEnabled(True)
        if assigned_count < 1:
            QtWidgets.QMessageBox.information(self, "Error", tr("Select at least one speaker"))


class SeparateForm(QWidgetBase):
    def __init__(self, parent=None):
        from videotrans.ui.separate import Ui_separateform
        self._bind_ui_methods(Ui_separateform)
        super().__init__(parent)
        self.task = None

    def closeEvent(self, event):
        if self.task:
            self.task.finish_event.emit("end")
            self.task = None
        self.hide()
        event.ignore()


class SetINIForm(QWidgetBase):
    def __init__(self, parent=None):
        from videotrans.ui.setini import Ui_setini
        self._bind_ui_methods(Ui_setini)
        super().__init__(parent)

    def event(self, event: QtCore.QEvent) -> bool:
        if event.type() == QtCore.QEvent.Type.WindowActivate:
            self.update_ui()
        return super().event(event)


class Fanyisrt(QWidgetBase):
    def __init__(self, parent=None):
        from videotrans.ui.fanyi import Ui_fanyisrt
        self._bind_ui_methods(Ui_fanyisrt)
        super().__init__(parent)

    def changeEvent(self, event):
        if event.type() == QEvent.ActivationChange:
            if self.isActiveWindow():
                self.aisendsrt.setChecked(settings.get('aisendsrt'))
        super(Fanyisrt, self).changeEvent(event)

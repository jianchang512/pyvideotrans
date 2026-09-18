import os
import platform
import re

from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import Qt, QModelIndex
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                               QPushButton, QComboBox, QLabel, QScrollArea, QGridLayout, QFrame, QSplitter,
                               QAbstractItemView, QHeaderView, QTableWidget, QTableWidgetItem)

from videotrans import tts
from videotrans.configure.config import tr, app_cfg, ROOT_DIR
from videotrans.util._srt_parse import get_subtitle_from_srt
from videotrans.util.help_misc import show_error


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


class Ui_fn_peiyinrole(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon(f"{ROOT_DIR}/videotrans/styles/icon.ico"))
        self.setupUi(self)

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
        self.subtitles.clear()
        app_cfg.dubbing_role.clear()
        self.clear_subtitle_area()
        self.subtitle_scroll_area2.setVisible(False)
        self.assign_role_label2.setVisible(False)
        self.tmp_rolelist2.setVisible(False)
        self.assign_role_button2.setVisible(False)
        self.hecheng_importbtn.setText(tr("Import SRT file..."))
        self.loglabel.setText("")

    def reset_assigned_roles(self):
        app_cfg.dubbing_role.clear()
        #self.spk_lines = {}
        self.spk_role = {}
        for i in range(self.subtitle_layout2.count()):
            widget = self.subtitle_layout2.itemAt(i).widget()
            if isinstance(widget, SpkRowWidget):
                _spk = widget.spk_name_label.text()
                self.spk_role[_spk] = None
                widget.spk_name_role.setText('')

        for row in range(self.subtitle_table.rowCount()):
            self.subtitle_table.item(row, 3).setText('')

    def parse_and_display_srt(self, srt_path):
        self.clear_all_ui()
        self.srt_path = srt_path
        try:
            subs = get_subtitle_from_srt(srt_path)
            patter_str = r'(?:\s*?\[)((?:spk|speaker|说话人|speaker_|\w{1,10})\s*?\d*?)(?:\])\s*?[:：]?'
            self.subtitle_table.setSortingEnabled(False)
            self.subtitle_table.setRowCount(len(subs))
            default_role_text = ''
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
                #item_role.setFlags(item_role.flags() & Qt.ItemIsEditable)
                self.subtitle_table.setItem(row_idx, 3, item_role)
                item_spk = QTableWidgetItem(spk_name if spk_name else "")
                item_spk.setFlags(item_time.flags() & ~Qt.ItemIsEditable)
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
        if not selected_role:
            show_error(tr("Please select a valid role from the dropdown list."))
            return
        assigned_count = 0
        default_role_text = ''
        for row in range(self.subtitle_table.rowCount()):
            check_item = self.subtitle_table.item(row, 1)
            # 检查当前行是否被选中
            if (check_item and check_item.checkState() == Qt.Checked) or (self.subtitle_table.selectionModel().isRowSelected( row, QModelIndex())):
                role_item = self.subtitle_table.item(row, 3)
                if selected_role in ['-', 'No']:
                    role_item.setText(default_role_text)
                else:
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
                        try:
                            row_idx = line - 1
                            if 0 <= row_idx < self.subtitle_table.rowCount():
                                if self.subtitle_table.item(row_idx, 0).text() == str(line):
                                    display_role = '' if selected_role in ['-', 'No'] else selected_role
                                    self.subtitle_table.item(row_idx, 3).setText(display_role)
                        except Exception:
                            pass
        finally:
            self.subtitle_table.blockSignals(False)
            self.subtitle_table.setUpdatesEnabled(True)
        if assigned_count < 1:
            QtWidgets.QMessageBox.information(self, "Error", tr("Select at least one speaker"))


    def setupUi(self, peiyinrole):
        self.has_done = False
        # 全局变量初始化
        self.srt_path = None
        self.subtitles = []
        self.error_msg = ""
        if not peiyinrole.objectName():
            peiyinrole.setObjectName(u"peiyinrole")
        peiyinrole.setMinimumSize(1200, 750)

        self.main_layout = QtWidgets.QVBoxLayout(peiyinrole)
        self.main_layout.setObjectName("main_layout")

        # 1. 顶部文件导入区域
        self.import_layout = QtWidgets.QHBoxLayout()
        self.hecheng_importbtn = QPushButton(tr("Import SRT file..."))
        self.hecheng_importbtn.setMinimumHeight(40)
        self.hecheng_importbtn.setCursor(Qt.PointingHandCursor)
        self.clear_button = QtWidgets.QPushButton(tr("Clear Cache"))
        self.clear_button.setMinimumHeight(40)
        self.clear_button.setFixedWidth(100)
        self.clear_button.setCursor(Qt.PointingHandCursor)

        self.import_layout.addWidget(self.hecheng_importbtn)
        self.import_layout.addWidget(self.clear_button)
        self.main_layout.addLayout(self.import_layout)
        
        # 创建垂直分割器
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.setToolTip('Drag Change Size')
        self.splitter.setChildrenCollapsible(False) 


        # 说话人角色区域
        self.container_frame = QFrame()
        self.container_frame.setObjectName("container_frame") 
        container_layout2 = QVBoxLayout(self.container_frame)
        container_layout2.setSpacing(2)

        self.subtitle_scroll_area2 = QScrollArea()
        self.subtitle_scroll_area2.setVisible(False)
        self.subtitle_scroll_area2.setWidgetResizable(True)
        self.scroll_area_widget_contents2 = QWidget()
        self.subtitle_layout2 = QGridLayout(self.scroll_area_widget_contents2) 
        self.subtitle_layout2.setAlignment(Qt.AlignTop)
        self.subtitle_scroll_area2.setWidget(self.scroll_area_widget_contents2)
        container_layout2.addWidget(self.subtitle_scroll_area2)

        self.assign_role_label2 = QLabel(tr('Assign roles to speakers'))
        self.assign_role_label2.setVisible(False)
        self.tmp_rolelist2 = QComboBox()
        self.tmp_rolelist2.setVisible(False)
        self.tmp_rolelist2.setMinimumWidth(200)
        self.assign_role_button2 = QPushButton(tr("Assign"))
        self.assign_role_button2.setVisible(False)
        self.assign_role_button2.setCursor(Qt.PointingHandCursor)

        self.assign_role_layout2 = QHBoxLayout()
        self.assign_role_layout2.addWidget(self.assign_role_label2)
        self.assign_role_layout2.addWidget(self.tmp_rolelist2)
        self.assign_role_layout2.addWidget(self.assign_role_button2)

        self.assign_role_layout2.addStretch()
        container_layout2.addLayout(self.assign_role_layout2)
        self.splitter.addWidget(self.container_frame)

        self.container_frame_subs = QFrame()
        self.container_frame_subs.setObjectName("container_frame_subs")
        container_layout_subs = QVBoxLayout(self.container_frame_subs)
        container_layout_subs.setSpacing(2)
        container_layout_subs.setContentsMargins(0, 0, 0, 0)

        # 使用 QTableWidget 替代 QScrollArea + VBoxLayout
        self.subtitle_table = QTableWidget()
        self.subtitle_table.setColumnCount(6)
        # 设置表头
        self.subtitle_table.setHorizontalHeaderLabels([tr("Line"), tr("Sel"), tr("Time Axis"), tr("Dubbing role"), tr("Speaker"), "Text"])
        
        # 表格样式与性能配置
        self.subtitle_table.setShowGrid(False) 
        self.subtitle_table.setAlternatingRowColors(False) # 交替颜色
        self.subtitle_table.setSelectionBehavior(QAbstractItemView.SelectRows) # 选中整行
        # self.subtitle_table.setEditTriggers(QAbstractItemView.NoEditTriggers) # 禁止编辑
        self.subtitle_table.verticalHeader().setVisible(False) # 隐藏行号头
        self.subtitle_table.setWordWrap(True)
        
        # 调整列宽模式
        header = self.subtitle_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents) # ID
        header.setSectionResizeMode(1, QHeaderView.Fixed)

        self.subtitle_table.setColumnWidth(1, 40)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents) # Time
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents) # Role
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents) # Speaker
        header.setSectionResizeMode(5, QHeaderView.Stretch)


        self.subtitle_table.setStyleSheet("""
           QTableWidget {
                color: #e0e0e0;  
                border: none;
                gridline-color: #3a3a3a;
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #3a3a3a;
                color: #e0e0e0;   
            }
            QTableWidget::item:selected {
                background-color: #455364;  
                color: white;  
            }
            QHeaderView::section {
                background-color: #2b2b2b; 
                color: #e0e0e0;  
                padding: 4px;
                border: 1px solid #3a3a3a;
            }
            QCheckBox {
                color: #e0e0e0; 
            }
        """)

        container_layout_subs.addWidget(self.subtitle_table)

        # 2.2 角色分配工具栏
        self.assign_role_layout = QHBoxLayout()
        self.assign_role_label = QLabel(tr("Assign role to selected:"))
        self.tmp_rolelist = QComboBox() 
        self.tmp_rolelist.setMinimumWidth(200)
        self.assign_role_button = QPushButton(tr("Assign"))
        self.assign_role_button.setCursor(Qt.PointingHandCursor)
        self.assign_role_layout.addWidget(self.assign_role_label)
        self.assign_role_layout.addWidget(self.tmp_rolelist)
        self.assign_role_layout.addWidget(self.assign_role_button)
        self.assign_role_layout.addStretch()
        container_layout_subs.addLayout(self.assign_role_layout)
        
        self.container_frame_subs.setStyleSheet("""#container_frame_subs{border: 1px solid #54687a}""")
        self.splitter.addWidget(self.container_frame_subs)
        
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.main_layout.addWidget(self.splitter)



        spk_label=QLabel(tr('will be automatically identified as the speaker'))
        spk_label.setStyleSheet("""color:#999""")
        spk_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(spk_label)


        # 3. TTS 设置区域
        self.horizontalLayout_10 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_10.setObjectName("horizontalLayout_10")
        
        
        self.is_cuda = QtWidgets.QCheckBox()
        self.is_cuda.setObjectName("is_cuda")
        self.is_cuda.setText(tr("Enable CUDA?"))
        # 如果是 MAc系统则隐藏
        if platform.system() == 'Darwin':
            self.is_cuda.setVisible(False)
            self.is_cuda.setChecked(False)
        self.horizontalLayout_10.addWidget(self.is_cuda)
        
        self.formLayout_3 = QtWidgets.QFormLayout()
        self.formLayout_3.setFormAlignment(QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.label_10 = QtWidgets.QLabel()
        self.label_10.setMinimumSize(QtCore.QSize(0, 30))
        self.formLayout_3.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.label_10)
        self.hecheng_language = QtWidgets.QComboBox()
        self.hecheng_language.setMinimumSize(QtCore.QSize(200, 30))
        self.formLayout_3.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.hecheng_language)

        self.formLayout_7 = QtWidgets.QFormLayout()
        self.formLayout_7.setFormAlignment(QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.label_8 = QtWidgets.QLabel()
        self.label_8.setMinimumSize(QtCore.QSize(0, 30))
        self.formLayout_7.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.label_8)
        self.tts_type = QtWidgets.QComboBox()
        self.tts_type.setMinimumSize(QtCore.QSize(200, 30))
        self.tts_type.addItems(tts.TTS_NAME_LIST)
        self.formLayout_7.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.tts_type)
        self.horizontalLayout_10.addLayout(self.formLayout_3)
        self.horizontalLayout_10.addLayout(self.formLayout_7)

        self.formLayout_4 = QtWidgets.QFormLayout()
        self.formLayout_4.setFormAlignment(QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.label_11 = QtWidgets.QLabel()
        self.label_11.setMinimumSize(QtCore.QSize(0, 30))
        self.formLayout_4.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.label_11)
        self.hecheng_role = QtWidgets.QComboBox()
        self.hecheng_role.setMinimumSize(QtCore.QSize(200, 30))
        self.hecheng_role.addItems(['No'])
        self.formLayout_4.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.hecheng_role)
        self.horizontalLayout_10.addLayout(self.formLayout_4)

        self.listen_btn = QtWidgets.QPushButton()
        self.listen_btn.setFixedWidth(80)
        self.listen_btn.setText(tr("Trial dubbing"))
        self.horizontalLayout_10.addWidget(self.listen_btn)
        self.horizontalLayout_10.addStretch()
        self.main_layout.addLayout(self.horizontalLayout_10)

        # 4. 速率、音量等设置
        self.horizontalLayout_10_1 = QtWidgets.QHBoxLayout()
        self.formLayout_5 = QtWidgets.QFormLayout()
        self.label_12 = QtWidgets.QLabel()
        self.formLayout_5.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.label_12)
        self.hecheng_rate = QtWidgets.QSpinBox()
        self.hecheng_rate.setMinimum(-100)
        self.hecheng_rate.setMaximum(100)
        self.hecheng_rate.setMinimumWidth(90)
        self.formLayout_5.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.hecheng_rate)
        self.horizontalLayout_10_1.addLayout(self.formLayout_5)
        self.voice_autorate = QtWidgets.QCheckBox()
        self.remove_silent_mid = QtWidgets.QCheckBox()
        self.remove_silent_mid.setVisible(False)
        self.horizontalLayout_10_1.addWidget(self.voice_autorate)
        self.horizontalLayout_10_1.addWidget(self.remove_silent_mid)

        self.edge_volume_layout = QtWidgets.QHBoxLayout()
        self.volume_label = QtWidgets.QLabel(tr("Volume+"))
        self.volume_rate = QtWidgets.QSpinBox()
        self.volume_rate.setMinimum(-95)
        self.volume_rate.setMaximum(200)
        self.volume_rate.setMinimumWidth(90)
        self.pitch_label = QtWidgets.QLabel(tr("Pitch+"))
        self.pitch_rate = QtWidgets.QSpinBox()
        self.pitch_rate.setMinimum(-100)
        self.pitch_rate.setMaximum(100)
        self.pitch_rate.setMinimumWidth(90)
        self.out_format_label = QtWidgets.QLabel(tr("Out format"))
        self.out_format = QtWidgets.QComboBox()
        self.out_format.addItems(['wav', "mp3", "m4a"])
        self.save_to_srt = QtWidgets.QCheckBox()
        self.edge_volume_layout.addWidget(self.volume_label)
        self.edge_volume_layout.addWidget(self.volume_rate)
        self.edge_volume_layout.addWidget(self.pitch_label)
        self.edge_volume_layout.addWidget(self.pitch_rate)
        self.edge_volume_layout.addWidget(self.out_format_label)
        self.edge_volume_layout.addWidget(self.out_format)
        self.edge_volume_layout.addWidget(self.save_to_srt)
        self.horizontalLayout_10_1.addLayout(self.edge_volume_layout)
        self.main_layout.addLayout(self.horizontalLayout_10_1)

        # 5. 底部按钮
        self.bottom_layout = QtWidgets.QVBoxLayout()
        h1 = QtWidgets.QHBoxLayout()
        self.hecheng_startbtn = QtWidgets.QPushButton()
        self.hecheng_startbtn.setMinimumSize(QtCore.QSize(200, 40))
        self.hecheng_startbtn.setCursor(Qt.PointingHandCursor)
        self.hecheng_stop = QtWidgets.QPushButton(tr("stop"))
        self.hecheng_stop.setFixedWidth(100)
        self.hecheng_stop.setDisabled(True)
        self.hecheng_stop.setCursor(Qt.PointingHandCursor)
        h1.addWidget(self.hecheng_startbtn)
        h1.addWidget(self.hecheng_stop)
        self.bottom_layout.addLayout(h1)

        self.loglabel = QtWidgets.QPushButton()
        self.loglabel.setStyleSheet('''color:#148cd2;background-color:transparent''')
        self.bottom_layout.addWidget(self.loglabel)

        self.hecheng_opendir = QtWidgets.QPushButton()
        self.hecheng_opendir.setStyleSheet("""background-color:transparent""")
        self.hecheng_opendir.setMinimumSize(QtCore.QSize(100, 35))
        self.hecheng_opendir.setCursor(Qt.PointingHandCursor)
        self.bottom_layout.addWidget(self.hecheng_opendir)
        self.main_layout.addLayout(self.bottom_layout)

        self.retranslateUi(peiyinrole)
        QtCore.QMetaObject.connectSlotsByName(peiyinrole)

    def retranslateUi(self, peiyinrole):
        peiyinrole.setWindowTitle(
            tr("multi-windows-title"))
        self.label_10.setText(tr("Subtitle lang"))
        self.label_8.setText(tr("TTS"))
        self.label_11.setStyleSheet("""color:#ffff00""")
        self.label_11.setText(tr("Default Role"))
        self.label_12.setText(tr("Speed change"))
        self.hecheng_rate.setToolTip(tr("Negative deceleration, positive acceleration"))
        self.voice_autorate.setText(tr("Automatic acceleration?"))
        self.save_to_srt.setText(tr("Save to original location"))
        self.save_to_srt.setToolTip(
            tr("If checked, the synthesized audio is saved to the original folder where the srt file is located."))
        self.hecheng_startbtn.setText(tr("Start"))
        self.hecheng_opendir.setText(tr("Open output directory"))
        self.remove_silent_mid.setText(tr("Del inline mute?"))
        self.remove_silent_mid.setToolTip(tr("Selecting this option will delete the silent intervals between subtitles"))

import json
import re
import time
from pathlib import Path

from PySide6.QtCore import Qt, QTime, Signal, QTimer, QSize, QEvent, QThread
from PySide6.QtGui import QFont, QColor, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QScrollArea, QLabel, QComboBox, QPushButton, QLineEdit, \
    QFileDialog, QTextEdit, QFontDialog, QColorDialog, QTimeEdit, QMessageBox

from videotrans import translator
from videotrans.configure import config
from videotrans.task._translate_srt import TranslateSrt
from videotrans.util import tools


class NoWheelTimeEdit(QTimeEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        # 安装事件过滤器
        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        # 检测到滚轮事件时，直接过滤掉
        if event.type() == QEvent.Wheel:
            return True  # 返回 True 表示事件被过滤掉，不再传递
        return super().eventFilter(obj, event)

class DropWidget(QWidget):
    fileDropped = Signal(str)  # 自定义信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)  # 启用拖放

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        for url in urls:
            file_path = url.toLocalFile()
            if self.is_valid_file(file_path):
                self.fileDropped.emit(file_path)  # 发射信号
                break

    def handle_dropped_file(self, file_path):
        # 处理文件，例如解析SRT, VTT, ASS字幕
        return file_path

    def is_valid_file(self, file_path):
        # Check file extension
        valid_extensions = ('.srt', '.ass', '.vtt')
        return file_path.lower().endswith(valid_extensions)


class DropScrollArea(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)  # 启用拖放

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        # 将事件传递到子部件
        widget = self.widget()
        if widget:
            widget.dragEnterEvent(event)
            widget.dropEvent(event)


class SignThread(QThread):
    uito = Signal(str)

    def __init__(self, uuid=None, parent=None):
        super().__init__(parent=parent)
        self.uuid = uuid

    def post(self, jsondata):
        self.uito.emit(json.dumps(jsondata))

    def run(self):
        while 1:
            if not self.uuid or config.exit_soft:
                self.post({"type": "end"})
                time.sleep(1)
                return

            if self.uuid in config.stoped_uuid_set:
                self.uuid=None
                return
            q = config.uuid_logs_queue.get(self.uuid)
            if not q:
                return
            try:
                if q.empty():
                    time.sleep(0.5)
                    continue
                data = q.get(block=False)
                if not data:
                    continue
                self.post(data)
                if data['type'] in ['error', 'succeed']:
                    self.uuid=None
                    config.stoped_uuid_set.add(self.uuid)
                    del config.uuid_logs_queue[self.uuid]
            except:
                pass



class Ui_subtitleEditor(QWidget):
    def __init__(self):
        super().__init__()
        self.has_done = False
        self.target_file=None
        self.lastend_time = 0

        self.setWindowTitle("Subtitle Editor" if config.defaulelang != 'zh' else '导入字幕编辑修改后导出')
        # self.resize(1200, 640)
        self.setMinimumSize(1200, 640)

        # 主垂直布局
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignTop)  # 顶部对齐

        # 第一行：导入和导出按钮的水平布局
        button_layout = QHBoxLayout()
        button_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.import_button = QPushButton(
            "导入需要编辑的字幕(srt/ass/vtt)" if config.defaulelang == 'zh' else 'Import Subtitles(srt/ass/vtt)')
        self.import_button.setFixedHeight(35)
        self.import_button.setFixedWidth(250)
        self.import_button.setCursor(Qt.PointingHandCursor)

        self.clear_all = QPushButton()
        self.clear_all.setText('清理已导入' if config.defaulelang == 'zh' else 'Clear All')
        self.clear_all.setStyleSheet('''background-color:transparent''')
        self.clear_all.clicked.connect(self.clear_content_layout)
        self.clear_all.setCursor(Qt.PointingHandCursor)
        self.loglabel = QLabel()
        self.loglabel.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.loglabel.setObjectName('renderlog')
        self.loglabel.setStyleSheet("""text-align:center;color:#aaaaaa;font-size:16px""")
        self.loglabel.setMinimumSize(QSize(300, 40))
        self.loglabel.setText('字幕编辑区' if config.defaulelang == 'zh' else 'Subtitles Edit area')

        button_layout.addWidget(self.import_button)

        button_layout.addWidget(self.clear_all)

        main_layout.addLayout(button_layout)

        self.fanyi_layout = QHBoxLayout()


        self.fanyi_button = QPushButton()
        self.fanyi_button.setText('翻译' if config.defaulelang == 'zh' else 'Translate')
        self.fanyi_button.setFixedHeight(35)
        self.fanyi_button.setFixedWidth(150)
        self.fanyi_button.setCursor(Qt.PointingHandCursor)
        self.fanyi_button.clicked.connect(self.fanyi)

        self.translate_type= QComboBox()
        self.translate_type.addItems(translator.TRANSLASTE_NAME_LIST)

        label_fanyi_source=QLabel()
        label_fanyi_source.setText('原始语言' if config.defaulelang == 'zh' else 'Source Language')
        self.fanyi_source = QComboBox()
        self.fanyi_source.setFixedHeight(35)
        self.fanyi_source.addItems(["-"] + [ it for it in config.langnamelist if config.rev_langlist[it]!='auto'])
        label_fanyi_target=QLabel()
        label_fanyi_target.setText('目标语言' if config.defaulelang == 'zh' else 'Target Language')
        self.fanyi_target = QComboBox()
        self.fanyi_target.setFixedHeight(35)
        self.fanyi_target.addItems(["-"] + [ it for it in config.langnamelist if config.rev_langlist[it]!='auto'])

        self.fanyi_log=QLabel()


        self.fanyi_layout.addStretch()
        self.fanyi_layout.addWidget(self.translate_type)
        self.fanyi_layout.addWidget(label_fanyi_source)
        self.fanyi_layout.addWidget(self.fanyi_source)
        self.fanyi_layout.addWidget(label_fanyi_target)
        self.fanyi_layout.addWidget(self.fanyi_target)
        self.fanyi_layout.addWidget(self.fanyi_button)
        self.fanyi_layout.addWidget(self.fanyi_log)
        self.fanyi_layout.addStretch()
        tools.hide_show_element(self.fanyi_layout,False)

        main_layout.addLayout(self.fanyi_layout)




        # 第二行：内容区域（初始为空白）
        self.content_widget = DropWidget()
        self.content_layout = QVBoxLayout()
        self.content_layout.setAlignment(Qt.AlignTop)  # 顶部对齐
        self.content_widget.setLayout(self.content_layout)
        self.content_widget.fileDropped.connect(self.load_subtitles)
        # 启用拖放

        # 创建滚动区域并设置内容区域为其子部件
        self.scroll_area = DropScrollArea()
        self.scroll_area.setObjectName("scroll_area")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.content_widget)
        self.loglabel.setVisible(True)
        main_layout.addWidget(self.scroll_area)
        self.scroll_area.setStyleSheet("""#scroll_area{border:1px solid #32414B}""")

        loglayout = QHBoxLayout()
        loglayout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        loglayout.setObjectName('renderlog_layout')
        loglayout.addStretch()
        loglayout.addWidget(self.loglabel)
        loglayout.addStretch()

        self.content_layout.addLayout(loglayout)

        # 第三行：输出字幕格式下拉框和相关选项
        format_layout = QHBoxLayout()
        format_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.export_button = QPushButton("导出字幕" if config.defaulelang == 'zh' else 'Export Subtitles')
        self.export_button.setFixedHeight(35)
        self.export_button.setFixedWidth(200)
        self.export_button.setCursor(Qt.PointingHandCursor)
        self.export_format = QComboBox()
        self.export_format.addItems([
            "原始语言字幕",
            "目标语言字幕",
            "双语字幕",
        ])
        self.export_format.setVisible(False)

        format_label = QLabel("输出字幕格式:" if config.defaulelang == 'zh' else 'Output Subtitle Format')
        format_label.setFixedWidth(100)
        self.format_combo = QComboBox()
        self.format_combo.setFixedWidth(80)
        self.format_combo.addItems(["srt", "ass", "vtt"])
        self.format_combo.currentTextChanged.connect(self.update_format_options)

        self.font_button = QPushButton("选择字体" if config.defaulelang == 'zh' else 'Select Fonts')
        self.font_button.setVisible(False)
        self.font_button.setToolTip('点击选择字体' if config.defaulelang == 'zh' else 'Click it for select fonts')
        self.font_button.clicked.connect(self.choose_font)
        self.font_button.setCursor(Qt.PointingHandCursor)

        self.color_button = QPushButton("字体颜色" if config.defaulelang == 'zh' else 'Text Colors')
        self.color_button.setVisible(False)
        self.color_button.setCursor(Qt.PointingHandCursor)
        self.color_button.clicked.connect(self.choose_color)

        self.backgroundcolor_button = QPushButton("背景色" if config.defaulelang == 'zh' else 'Backgroud Colors')
        self.backgroundcolor_button.setVisible(False)
        self.backgroundcolor_button.setCursor(Qt.PointingHandCursor)
        self.backgroundcolor_button.clicked.connect(self.choose_backgroundcolor)
        self.backgroundcolor_button.setToolTip(
            '不同播放器下可能不起作用' if config.defaulelang == 'zh' else 'May not work in different players')

        self.bordercolor_button = QPushButton("边框色" if config.defaulelang == 'zh' else 'Backgroud Colors')
        self.bordercolor_button.setVisible(False)
        self.bordercolor_button.setCursor(Qt.PointingHandCursor)
        self.bordercolor_button.clicked.connect(self.choose_bordercolor)
        self.bordercolor_button.setToolTip(
            '不同播放器下可能不起作用' if config.defaulelang == 'zh' else 'May not work in different players')

        self.font_size_edit = QLineEdit()
        self.font_size_edit.setFixedWidth(80)
        self.font_size_edit.setText('16')
        self.font_size_edit.setPlaceholderText("字体大小" if config.defaulelang == 'zh' else 'Font Size')
        self.font_size_edit.setToolTip("字体大小" if config.defaulelang == 'zh' else 'Font Size')
        self.font_size_edit.setVisible(False)

        self.marginLabel = QLabel(text='边距' if config.defaulelang == 'zh' else 'Margin')
        self.marginLabel.setFixedWidth(50)
        self.marginLabel.setVisible(False)

        self.marginLRV = QLineEdit()
        self.marginLRV.setVisible(False)
        self.marginLRV.setFixedWidth(80)
        self.marginLRV.setPlaceholderText(
            "距离 左,右,底 距离(10,10,10)" if config.defaulelang == 'zh' else 'Margin left/right/bottom offset')
        self.marginLRV.setToolTip(
            "距离 左,右,底 距离(10,10,10)" if config.defaulelang == 'zh' else 'Margin left/right/bottom offset')
        self.marginLRV.setText('10,10,10')
        self.marginLRV.setVisible(False)

        format_layout.addWidget(self.export_button)
        format_layout.addWidget(self.export_format)
        format_layout.addWidget(format_label)
        format_layout.addWidget(self.format_combo)
        format_layout.addWidget(self.font_button)
        format_layout.addWidget(self.font_size_edit)
        format_layout.addWidget(self.color_button)
        format_layout.addWidget(self.backgroundcolor_button)
        format_layout.addWidget(self.bordercolor_button)
        format_layout.addWidget(self.marginLabel)
        format_layout.addWidget(self.marginLRV)

        main_layout.addLayout(format_layout)

        self.setLayout(main_layout)

        # 初始化字体和颜色
        self.selected_font = QFont('Arial', 16)  # 默认字体
        self.selected_color = QColor('#FFFFFFFF')  # 默认颜色
        self.selected_backgroundcolor = QColor('#00000000')  # 默认颜色
        self.selected_bordercolor = QColor('#00000000')  # 默认颜色

        # 绑定按钮事件
        self.import_button.clicked.connect(self.import_subtitles)
        self.export_button.clicked.connect(self.export_subtitles)

    def fanyi(self):
        target_language = self.fanyi_target.currentText()
        if target_language=='-':
            return QMessageBox.critical(self, config.transobj['anerror'], '必须选择目标语言' if config.defaulelang=='zh' else 'Please select target language')

        if target_language==self.fanyi_source.currentText():
            return QMessageBox.critical(self, config.transobj['anerror'], '原语言和目标语言不得相同' if config.defaulelang=='zh' else 'Can not translate to source language')

        rs = translator.is_allow_translate(translate_type=self.translate_type.currentIndex(), show_target=target_language)
        if rs is not True:
            return False

        RESULT_DIR=config.TEMP_HOME+'/subtitle_editor'
        Path(RESULT_DIR).mkdir(parents=True, exist_ok=True)
        source_file=config.TEMP_HOME + f'/{time.time()}.srt'
        if self.save_srt(source_file,-1) is not True:
            return

        it=tools.format_video(source_file, None)
        print(f'{it=}')

        self.target_file=f'{RESULT_DIR}/{it["noextname"]}.srt'

        source_code = translator.get_code(show_text=self.fanyi_source.currentText())
        target_code = translator.get_code(show_text=target_language)
        config.box_trans='ing'
        trk = TranslateSrt({
            "out_format":0,
            "translate_type": self.translate_type.currentIndex(),
            "text_list": tools.get_subtitle_from_srt(source_file),
            "target_dir": RESULT_DIR,
            "inst": None,
            "rename": False,
            "uuid": it['uuid'],
            "source_code": source_code,
            "target_code": target_code
        }, it)
        print(f'{trk.cfg=}')
        th = SignThread(uuid=it['uuid'], parent=self)
        th.uito.connect(self.feed)
        th.start()
        config.trans_queue.append(trk)
        self.fanyi_button.setDisabled(True)

    def feed(self,d):
        if config.box_trans != 'ing':
            return
        d = json.loads(d)
        
        if d['type'] != 'error':
            self.fanyi_log.setStyleSheet("""color:#ddd""")

        if d['type'] == 'error':
            self.fanyi_log.setStyleSheet("""color:#ff0000;background-color:transparent""")
            self.fanyi_log.setText(d['text'][:150])
            self.fanyi_log.setCursor(Qt.PointingHandCursor)
            self.fanyi_button.setText('开始执行' if config.defaulelang == 'zh' else 'start operate')
            self.fanyi_button.setDisabled(False)
        # 挨个从顶部添加已翻译后的文字
        elif d['type'] in ['logs']:
            if d['text']:
                self.fanyi_log.setText(d["text"])
        elif d['type'] in ['succeed']:
            self.fanyi_log.setText('请保持原文译文各占一行，勿加换行' if config.defaulelang == 'zh' else 'Please keep the original and translated text in one line, do')
            self.fanyi_button.setText('翻译完成' if config.defaulelang == 'zh' else 'Translate Ended')
            self.fanyi_button.setDisabled(False)
            config.box_trans = 'stop'
            self.set_target_text()
            self.export_format.setVisible(True)

    def set_target_text(self):
        if not Path(self.target_file).exists():
            return QMessageBox.critical(self, config.transobj['anerror'], '翻译失败' if config.defaulelang == 'zh' else 'Translate failed')
        target_list=tools.get_subtitle_from_srt(self.target_file)
        for i in range(self.content_layout.count()):
            layout = self.content_layout.itemAt(i)
            if layout:
                for j in range(layout.layout().count()):
                    widget = layout.layout().itemAt(j).widget()
                    if isinstance(widget, QTextEdit):
                        text = widget.toPlainText()
                        try:
                            tmp=target_list.pop(0)
                        except:
                            pass
                        else:
                            text=text.strip().replace("\n",'')+"\n"+tmp['text'].strip().replace("\n",'')
                            widget.setPlainText(text)


    def import_subtitles(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Subtitles files", config.params['last_opendir'], "Subtitle Files (*.srt *.ass *.vtt)"
        )
        if file_path:
            self.load_subtitles(file_path)

    def load_subtitles(self, file_path):
        self.clear_content_layout()  # 清空已有字幕

        self.loglabel.setVisible(True)
        self.loglabel.setText('正在渲染字幕，请稍等...' if config.defaulelang == 'zh' else 'Rendering subtitles. Please wait...')

        def render():
            format = Path(file_path).suffix.lower()
            if format == ".srt":
                self.load_srt(file_path)
            elif format == ".ass":
                self.load_ass(file_path)
            elif format == ".vtt":
                self.load_vtt(file_path)
            self.loglabel.setVisible(False)
            self.loglabel.setText('字幕编辑区' if config.defaulelang == 'zh' else 'Subtitles Edit area')
            tools.hide_show_element(self.fanyi_layout,True)
            self.export_format.setVisible(False)
        QTimer.singleShot(50, render)

    def load_srt(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        i = 0
        num = 0
        while i < len(lines):
            if lines[i].strip().isdigit():  # 字幕编号
                times = lines[i + 1].strip().split(' --> ')
                start_time = self.parse_time(times[0])
                end_time = self.parse_time(times[1])

                text = ""
                i += 2
                while i < len(lines) and lines[i].strip():
                    text += lines[i].strip() + "\n"
                    i += 1
                num += 1
                self.add_subtitle_row(start_time=start_time, end_time=end_time, text=text.strip(), line=num)
            i += 1

    def load_ass(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        # 确保文件中包含 [Events] 部分
        try:
            events_start = lines.index("[Events]\n") + 1
        except ValueError:
            raise Exception("ASS 文件格式不正确，未找到 [Events] 部分。")

        num = 0
        for line in lines[events_start:]:
            line = line.strip()
            if not line or not line.startswith('Dialogue:'):
                continue

            parts = line.split(',', 9)
            if len(parts) >= 10:
                start_time = self.parse_ass_time(parts[1].strip())
                end_time = self.parse_ass_time(parts[2].strip())
                text = parts[9].strip().replace('\\N', '\n')
                num += 1
                self.add_subtitle_row(start_time=start_time, end_time=end_time, text=text, line=num)
            else:
                Exception(f"ASS 行格式不正确: {line}")

    def load_vtt(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        # 跳过文件头
        i = 1
        num = 0
        while i < len(lines):
            line = lines[i].strip()
            if line:
                # 处理时间戳和字幕文本
                times, text = "", ""
                if '-->' in line:
                    num += 1  # 更新行号
                    times = line
                    i += 1
                    # 读取字幕文本
                    while i < len(lines) and lines[i].strip():
                        text += lines[i].strip() + "\n"
                        i += 1
                    times = times.split(' --> ')
                    if len(times) == 2:
                        start_time = self.parse_vtt_time(times[0])
                        end_time = self.parse_vtt_time(times[1])
                        self.add_subtitle_row(start_time=start_time, end_time=end_time, text=text.strip(), line=num)
            i += 1

    def add_subtitle_row(self, start_time=(0, 0, 0, 0), end_time=(0, 0, 0, 0), text="", insert_at=None, line=0):
        subtitle_layout = QHBoxLayout()

        subtitle_layout.addWidget(QLabel(text=f'[{line}]'))
        start_spinboxes = NoWheelTimeEdit()
        start_spinboxes.setDisplayFormat("HH:mm:ss.zzz")
        start_spinboxes.setTime(QTime(*start_time))
        subtitle_layout.addWidget(start_spinboxes)
        subtitle_layout.addWidget(QLabel(text='->'))

        end_spinboxes = NoWheelTimeEdit()
        end_spinboxes.setDisplayFormat("HH:mm:ss.zzz")
        end_spinboxes.setTime(QTime(*end_time))
        subtitle_layout.addWidget(end_spinboxes)

        text_edit = QTextEdit(text)
        text_edit.setFixedHeight(50)
        subtitle_layout.addWidget(text_edit, stretch=1)

        add_button = QPushButton("+")
        add_button.setCursor(Qt.PointingHandCursor)
        add_button.setStyleSheet("""color:#009688;font-size:18px;background-color:transparent""")
        add_button.setToolTip('在下方增加一行字幕' if config.defaulelang == 'zh' else 'Add a line of captioning below')
        add_button.clicked.connect(lambda: self.add_subtitle_row_below(subtitle_layout))
        delete_button = QPushButton("x")
        delete_button.setCursor(Qt.PointingHandCursor)
        delete_button.setStyleSheet('''color:#dddddd;background-color:transparent''')
        delete_button.setToolTip('删除该行' if config.defaulelang == 'zh' else 'delete row')
        delete_button.clicked.connect(lambda: self.delete_subtitle_row(subtitle_layout))

        subtitle_layout.addWidget(add_button)
        subtitle_layout.addWidget(delete_button)

        if insert_at is None:
            self.content_layout.addLayout(subtitle_layout)
        else:
            self.content_layout.insertLayout(insert_at + 1, subtitle_layout)

    def delete_subtitle_row(self, layout):
        for i in reversed(range(layout.count())):
            widget = layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        layout.setParent(None)

    def add_subtitle_row_below(self, layout):
        index = self.content_layout.indexOf(layout)
        self.add_subtitle_row(start_time=(0, 0, 0, 0), end_time=(0, 0, 0, 0), text="new text", insert_at=index)

    def parse_time(self, time_str):
        try:
            h, m, s_ms = 0, 0, 0.0
            tmp = time_str.split(':')
            if len(tmp) == 3:
                h = tmp[0]
                m = tmp[1]
                s_ms = tmp[2]
            elif len(tmp) == 2:
                m = tmp[0]
                s_ms = tmp[1]
            else:
                s_ms = tmp[0]
            s, ms = re.split(r'\,|\.', s_ms)
            return int(h), int(m), int(s), int(ms)
        except ValueError:
            return 0, 0, 0, 0

    def parse_ass_time(self, time_str):
        return self.parse_time(time_str)

    def parse_vtt_time(self, time_str):
        return self.parse_time(time_str)

    def choose_font(self):

        dialog = QFontDialog(self.selected_font, self)
        if dialog.exec():
            font = dialog.selectedFont()
            font_name = font.family()
            font_size = font.pointSize()
            self.selected_font = font
            self.font_size_edit.setText(str(font_size))
            self.font_button.setText(font_name)
            self._setfont()

    def _setfont(self):
        bgcolor = self.selected_backgroundcolor.name()
        bgcolor = '' if bgcolor == '#000000' else f'background-color:{bgcolor}'
        bdcolor = self.selected_bordercolor.name()
        bdcolor = '' if bdcolor == '#000000' else f'border:1px solid {bdcolor}'
        color = self.selected_color.name()
        color = '' if color == '#000000' else f'color:{color}'
        font = self.selected_font
        self.font_button.setStyleSheet(
            f"""font-family:'{font.family()}';font-size:{font.pointSize()}px;font-weight:{700 if font.bold() else 400};font-style:{'normal' if font.italic() else 'italic'};{bgcolor};{color};{bdcolor}""")

    def choose_color(self):
        dialog = QColorDialog(self.selected_color, self)
        dialog.setOption(QColorDialog.ShowAlphaChannel, True)  # 启用透明度选择
        color = dialog.getColor()

        if color.isValid():
            self.selected_color = color
            self._setfont()

    def choose_backgroundcolor(self):
        dialog = QColorDialog(self.selected_backgroundcolor, self)
        dialog.setOption(QColorDialog.ShowAlphaChannel, True)  # 启用透明度选择
        color = dialog.getColor()
        if color.isValid():
            self.selected_backgroundcolor = color
            self._setfont()

    def choose_bordercolor(self):
        dialog = QColorDialog(self.selected_bordercolor, self)
        dialog.setOption(QColorDialog.ShowAlphaChannel, True)  # 启用透明度选择
        color = dialog.getColor()
        if color.isValid():
            self.selected_bordercolor = color
            self._setfont()

    def export_subtitles(self):
        format = self.format_combo.currentText()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save", "", f"Subtitle Files (*.{format})"
        )
        if file_path:
            out_format= -1
            if self.export_format.isVisible() and self.export_format.currentIndex()<2:
                out_format=self.export_format.currentIndex()
            if format == "srt":
                self.save_srt(file_path,out_format)
            elif format == "ass":
                self.save_ass(file_path,out_format)
            elif format == "vtt":
                self.save_vtt(file_path,out_format)


    def save_srt(self, file_path,out_format=-1):
        self.lastend_time = 0
        with open(file_path, 'w', encoding='utf-8') as file:
            index = 1
            for i in range(self.content_layout.count()):
                layout = self.content_layout.itemAt(i)
                if layout:
                    start_time, end_time = '', ''
                    text = ""
                    n = 0
                    for j in range(layout.layout().count()):
                        widget = layout.layout().itemAt(j).widget()
                        if isinstance(widget, NoWheelTimeEdit):
                            msec = widget.time().msecsSinceStartOfDay()
                            msg = ''
                            if n < 1:
                                if msec < self.lastend_time:
                                    msg = f'第{index}行不正确，开始时间不得小于上行字幕的结束时间' if config.defaulelang == 'zh' else f'Line {index} is incorrect, the start time must not be less than the end time of the previous line of credits'
                                n += 1
                                start_time = widget.time().toString('HH:mm:ss,zzz')
                            else:
                                if msec < self.lastend_time:
                                    msg = f'第{index}行不正确，结束时间不得小于开始时间' if config.defaulelang == 'zh' else f'Line {index} is incorrect, the end time must not be less than the start time'
                                end_time = widget.time().toString('HH:mm:ss,zzz')
                            if msg:
                                return QMessageBox.critical(self, config.transobj['anerror'], msg)
                            self.lastend_time = msec
                        elif isinstance(widget, QTextEdit):
                            text = widget.toPlainText().strip()
                            if out_format>-1:
                                text_split=text.split('\n')
                                if len(text_split)>out_format:
                                    text=text_split[out_format]
                    if start_time and end_time:
                        start_str = f"{start_time}"
                        end_str = f"{end_time}"
                        file.write(f"{index}\n{start_str} --> {end_str}\n{text}\n\n")
                        index += 1
        return True        
        
    def qcolor_to_ass_color(self, color, type='fc'):
        # 获取颜色的 RGB 值
        r = color.red()
        g = color.green()
        b = color.blue()
        if type in ['bg', 'bd']:
            return f"&H80{b:02X}{g:02X}{r:02X}"
        # 将 RGBA 转换为 ASS 的颜色格式 &HBBGGRR
        return f"&H{b:02X}{g:02X}{r:02X}"

    def save_ass(self, file_path,out_format=-1):
        self.lastend_time = 0
        with open(file_path, 'w', encoding='utf-8') as file:
            # 写入 ASS 文件的头部信息
            stem = Path(file_path).stem
            file.write("[Script Info]\n")
            file.write(f"Title: {stem}\n")
            file.write(f"Original Script: {stem}\n")
            file.write("ScriptType: v4.00+\n")
            file.write("PlayResX: 384\nPlayResY: 288\n")
            file.write("ScaledBorderAndShadow: yes\n")
            file.write("YCbCr Matrix: None\n")
            file.write("\n[V4+ Styles]\n")
            file.write(
                f"Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
            left, right, vbottom = 10, 10, 10
            try:
                left, right, vbottom = self.marginLRV.text().strip().split(',')
            except Exception:
                pass

            bgcolor = self.qcolor_to_ass_color(self.selected_backgroundcolor, type='bg')
            bdcolor = self.qcolor_to_ass_color(self.selected_bordercolor, type='bd')
            fontcolor = self.qcolor_to_ass_color(self.selected_color, type='fc')

            file.write(
                f'Style: Default,{self.selected_font.family()},{self.font_size_edit.text() if self.font_size_edit.text() else "20"},{fontcolor},{fontcolor},{bdcolor},{bgcolor},{int(self.selected_font.bold())},{int(self.selected_font.italic())},0,0,100,100,0,0,1,1,0,2,{left},{right},{vbottom},1\n')
            file.write("\n[Events]\n")
            file.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")

            index = 1

            for i in range(self.content_layout.count()):
                layout = self.content_layout.itemAt(i)
                if layout:
                    start_time, end_time = '', ''
                    text = ""
                    n = 0
                    for j in range(layout.layout().count()):
                        widget = layout.layout().itemAt(j).widget()
                        if isinstance(widget, NoWheelTimeEdit):
                            msec = widget.time().msecsSinceStartOfDay()
                            msg = ''
                            if n < 1:
                                if msec < self.lastend_time:
                                    msg = f'第{index}行不正确，开始时间不得小于上行字幕的结束时间' if config.defaulelang == 'zh' else f'Line {index} is incorrect, the start time must not be less than the end time of the previous line of credits'
                                n += 1
                                start_time = widget.time().toString('HH:mm:ss.zz')
                            else:
                                if msec < self.lastend_time:
                                    msg = f'第{index}行不正确，结束时间不得小于开始时间' if config.defaulelang == 'zh' else f'Line {index} is incorrect, the end time must not be less than the start time'
                                end_time = widget.time().toString('HH:mm:ss.zz')
                            if msg:
                                return QMessageBox.critical(self, config.transobj['anerror'], msg)
                            self.lastend_time = msec
                        elif isinstance(widget, QTextEdit):
                            text = widget.toPlainText()
                            if out_format>-1:
                                text_split=text.split('\n')
                                if len(text_split)>out_format:
                                    text=text_split[out_format]

                    if start_time and end_time:
                        start_str = f"{start_time}"
                        end_str = f"{end_time}"
                        text = text.replace('\n', '\\N')
                        file.write(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{text}\n")
                        index += 1
        return True                

    def save_vtt(self, file_path,out_format=-1):
        self.lastend_time = 0
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write("WEBVTT\n\n")
            index = 1
            for i in range(self.content_layout.count()):
                layout = self.content_layout.itemAt(i)
                if layout:
                    start_time, end_time = '', ''
                    text = ""
                    n = 0
                    for j in range(layout.layout().count()):
                        widget = layout.layout().itemAt(j).widget()
                        if isinstance(widget, NoWheelTimeEdit):
                            msec = widget.time().msecsSinceStartOfDay()
                            msg = ""
                            if n < 1:
                                n += 1
                                if msec < self.lastend_time:
                                    msg = f'第{index}行不正确，开始时间不得小于上行字幕的结束时间' if config.defaulelang == 'zh' else f'Line {index} is incorrect, the start time must not be less than the end time of the previous line of credits'
                                start_time = widget.time().toString('HH:mm:ss.zzz')
                            else:
                                if msec < self.lastend_time:
                                    msg = f'第{index}行不正确，结束时间不得小于开始时间' if config.defaulelang == 'zh' else f'Line {index} is incorrect, the end time must not be less than the start time'
                                end_time = widget.time().toString('HH:mm:ss.zzz')
                            if msg:
                                return QMessageBox.critical(self, config.transobj['anerror'], msg)
                            self.lastend_time = msec

                        elif isinstance(widget, QTextEdit):
                            text = widget.toPlainText()
                            if out_format>-1:
                                text_split=text.split('\n')
                                if len(text_split)>out_format:
                                    text=text_split[out_format]

                    if start_time and end_time:
                        start_str = f"{start_time}"
                        end_str = f"{end_time}"
                        file.write(f"{index}\n{start_str} --> {end_str}\n{text}\n\n")
                        index += 1
        return True        
        
    def update_format_options(self):
        format = self.format_combo.currentText()
        if format == "ass":
            self.font_button.setVisible(True)
            self.color_button.setVisible(True)
            self.backgroundcolor_button.setVisible(True)
            self.bordercolor_button.setVisible(True)
            self.font_size_edit.setVisible(True)
            self.marginLRV.setVisible(True)
            self.marginLabel.setVisible(True)
        else:
            self.marginLabel.setVisible(False)
            self.marginLRV.setVisible(False)
            self.backgroundcolor_button.setVisible(False)
            self.bordercolor_button.setVisible(False)
            self.font_button.setVisible(False)
            self.color_button.setVisible(False)
            self.font_size_edit.setVisible(False)

    def clear_content_layout(self):
        # 遍历并删除所有子布局和部件
        self.loglabel.setVisible(True)
        tools.hide_show_element(self.fanyi_layout,False)
        self.export_format.setVisible(False)
        self.fanyi_log.setText('')
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item is not None:
                widget = item.widget()
                if widget and widget.objectName() != 'renderlog':
                    widget.deleteLater()  # 删除部件
                layout = item.layout()
                if layout:
                    # 递归删除子布局
                    while layout.count():
                        sub_item = layout.takeAt(0)
                        if sub_item is not None:
                            sub_widget = sub_item.widget()
                            if sub_widget and sub_widget.objectName() != 'renderlog':
                                sub_widget.deleteLater()  # 删除部件
                            sub_layout = sub_item.layout()
                            if sub_layout:
                                # 递归删除更深层的布局
                                self.delete_layout(sub_layout)
                    if layout.objectName() != 'renderlog':
                        layout.deleteLater()  # 删除布局

    def delete_layout(self, layout):
        # 递归删除布局及其子布局和部件
        while layout.count():
            item = layout.takeAt(0)
            if item is not None:
                widget = item.widget()
                if widget and widget.objectName() != 'renderlog':
                    widget.deleteLater()  # 删除部件
                sub_layout = item.layout()
                if sub_layout:
                    # 递归删除更深层的布局
                    self.delete_layout(sub_layout)
        if layout.objectName() != 'renderlog_layout':
            layout.deleteLater()  # 删除布局

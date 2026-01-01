import sys
import json
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFormLayout,
    QFontComboBox, QSpinBox,QDoubleSpinBox, QCheckBox, QComboBox, QColorDialog, QGridLayout,
    QGroupBox, QApplication, QWidget, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QGraphicsTextItem, QGraphicsRectItem, QGraphicsPathItem,QSpacerItem,QSizePolicy
)
from PySide6.QtGui import QColor, QPixmap, QFont, QPen, QBrush, QPainterPath, QTransform, QPainterPathStroker,QIcon
from PySide6.QtCore import Qt, Signal,QSize
from videotrans.configure import config
from videotrans.configure.config import tr

from pathlib import Path

JSON_FILE = f'{config.ROOT_DIR}/videotrans/ass.json'
PREVIEW_IMAGE = f'{config.ROOT_DIR}/videotrans/styles/preview.png'



DEFAULT_STYLE = {
    'Name': 'Default',
    'Fontname': 'Arial',
    'Fontsize': 16,
    'PrimaryColour': '&H00FFFFFF&',
    'SecondaryColour': '&H00FFFFFF&',
    'OutlineColour': '&H00000000&',
    'BackColour': '&H00000000&',
    'Bold': 0,
    'Italic': 0,
    'Underline': 0,
    'StrikeOut': 0,
    'ScaleX': 100,
    'ScaleY': 100,
    'Spacing': 0,
    'Angle': 0,
    'BorderStyle': 1,
    'Outline': 0.5,
    'Shadow': 0.5,
    'Alignment': 2,
    'MarginL': 10,
    'MarginR': 10,
    'MarginV': 10,
    'Encoding': 1
}

class ColorPicker(QWidget):
    colorChanged = Signal()

    def __init__(self, color_str, parent=None):
        super().__init__(parent)
        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.color_swatch = QLabel()
        self.color_swatch.setFixedSize(30, 20)
        self.color_swatch.setStyleSheet("border: 1px solid black;")
        self.button = QPushButton(tr("choose_color"))
        self.layout().addWidget(self.color_swatch)
        self.layout().addWidget(self.button)
        self.color = self.parse_color(color_str)
        self.update_swatch()
        self.button.clicked.connect(self.choose_color)

    @staticmethod
    def parse_color(color_str):
        if not color_str.startswith('&H') or not color_str.endswith('&'):
            return QColor(255, 255, 255, 255)
        hex_str = color_str[2:-1].upper()
        if len(hex_str) == 6:
            a = 0
            b = int(hex_str[0:2], 16)
            g = int(hex_str[2:4], 16)
            r = int(hex_str[4:6], 16)
        elif len(hex_str) == 8:
            a = int(hex_str[0:2], 16)
            b = int(hex_str[2:4], 16)
            g = int(hex_str[4:6], 16)
            r = int(hex_str[6:8], 16)
        else:
            return QColor(255, 255, 255, 255)
        return QColor(r, g, b, 255 - a)

    def to_ass_color(self):
        r = self.color.red()
        g = self.color.green()
        b = self.color.blue()
        a = 255 - self.color.alpha()
        return f'&H{a:02X}{b:02X}{g:02X}{r:02X}&'

    def choose_color(self):
        dialog = QColorDialog(self.color, self)
        dialog.setOption(QColorDialog.ShowAlphaChannel, True)
        if dialog.exec():
            self.color = dialog.currentColor()
            self.update_swatch()
            self.colorChanged.emit()

    def update_swatch(self):
        self.color_swatch.setStyleSheet(f"background-color: rgba({self.color.red()},{self.color.green()},{self.color.blue()},{self.color.alpha()}); border: 1px solid black;")

class PreviewWidget(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.background_item = None
        self.items = []
        self.load_background()
     
     
            
    def load_background(self):
        if Path(PREVIEW_IMAGE).exists():
            pixmap = QPixmap(PREVIEW_IMAGE)
            self.background_item = QGraphicsPixmapItem(pixmap)
            self.background_item.setZValue(-10)
            self.scene.addItem(self.background_item)
            self.setSceneRect(self.background_item.boundingRect())
        else:
            self.setSceneRect(0, 0, 640, 360)  # Default size if no image

    def clear_items(self):
        for item in self.items:
            self.scene.removeItem(item)
        self.items = []

    def update_preview(self, style):
        self.clear_items()

        text =  '你好啊，亲爱的朋友们！' if config.defaulelang=='zh' else  'Hello, my dear friend. hope your every day beautiful'

        font = QFont(style['Fontname'], style['Fontsize'])
        font.setBold(bool(style['Bold']))
        font.setItalic(bool(style['Italic']))
        font.setUnderline(bool(style['Underline']))
        font.setStrikeOut(bool(style['StrikeOut']))
        font.setLetterSpacing(QFont.AbsoluteSpacing, style['Spacing'])

        if isinstance(style['PrimaryColour'], str):
            primary_color = ColorPicker.parse_color(style['PrimaryColour'])
        else:
            primary_color = style['PrimaryColour']
        if isinstance(style['OutlineColour'], str):
            outline_color = ColorPicker.parse_color(style['OutlineColour'])
        else:
            outline_color = style['OutlineColour']
        if isinstance(style['BackColour'], str):
            back_color = ColorPicker.parse_color(style['BackColour'])
        else:
            back_color = style['BackColour']

        path = QPainterPath()
        path.addText(0, 0, font, text)

        text_rect = path.boundingRect()

        effective_outline = style['Outline'] if style['BorderStyle'] == 1 else 0

        shadow_item = None

        back_rect = None

        outline_item = None

        fill_item = QGraphicsPathItem(path)
        fill_item.setPen(Qt.NoPen)
        fill_item.setBrush(QBrush(primary_color))
        self.scene.addItem(fill_item)
        self.items.append(fill_item)

        main_item = fill_item

        if effective_outline > 0:
            stroker = QPainterPathStroker()
            stroker.setWidth(effective_outline * 2)
            stroker.setCapStyle(Qt.RoundCap)
            stroker.setJoinStyle(Qt.RoundJoin)
            outline_path = stroker.createStroke(path)
            outline_item = QGraphicsPathItem(outline_path)
            outline_item.setPen(Qt.NoPen)
            outline_item.setBrush(QBrush(outline_color))
            self.scene.addItem(outline_item)
            self.items.append(outline_item)
            outline_item.setZValue(-1)
            main_item = outline_item

        if style['BorderStyle'] == 3:
            box_padding = style['Outline']
            box_rect = text_rect.adjusted(-box_padding, -box_padding, box_padding, box_padding)
            back_rect = QGraphicsRectItem(box_rect)
            back_rect.setBrush(QBrush(outline_color))  # BorderStyle 3 使用 OutlineColour 作为背景框颜色
            back_rect.setPen(Qt.NoPen)
            self.scene.addItem(back_rect)
            self.items.append(back_rect)
            back_rect.setZValue(-1)
            fill_item.setZValue(1)

        # Shadow
        if style['Shadow'] > 0:
            if style['BorderStyle'] == 1:
                shadow_path = QPainterPath()
                shadow_path.addText(0, 0, font, text)
                stroker = QPainterPathStroker()
                stroker.setWidth(effective_outline * 2)
                stroker.setCapStyle(Qt.RoundCap)
                stroker.setJoinStyle(Qt.RoundJoin)
                widened_shadow = stroker.createStroke(shadow_path) + shadow_path
                shadow_item = QGraphicsPathItem(widened_shadow)
                shadow_item.setPen(Qt.NoPen)
                shadow_item.setBrush(QBrush(back_color))
                self.scene.addItem(shadow_item)
                self.items.append(shadow_item)
                shadow_item.setZValue(-2)
            elif style['BorderStyle'] == 3:
                box_padding = style['Outline']
                shadow_rect = text_rect.adjusted(-box_padding, -box_padding, box_padding, box_padding)
                shadow_item = QGraphicsRectItem(shadow_rect)
                shadow_item.setBrush(QBrush(back_color))
                shadow_item.setPen(Qt.NoPen)
                self.scene.addItem(shadow_item)
                self.items.append(shadow_item)
                shadow_item.setZValue(-2)

        # Transformations
        transform = QTransform()
        transform.scale(style['ScaleX'] / 100.0, style['ScaleY'] / 100.0)
        transform.rotate(style['Angle'])

        # Apply transform to main items
        for item in self.items:
            if shadow_item is None or item != shadow_item:
                item.setTransform(transform)
        if style['Shadow'] > 0:
            shadow_item.setTransform(transform)

        # Position
        scene_rect = self.sceneRect()
        # Use text bounding for alignment
        text_bounding = fill_item.mapToScene(fill_item.boundingRect()).boundingRect()
        width = text_bounding.width()
        height = text_bounding.height()

        align = style['Alignment']
        margin_l = style['MarginL']
        margin_r = style['MarginR']
        margin_v = style['MarginV']

        if align in [1, 4, 7]:  # Left
            x = margin_l
        elif align in [3, 6, 9]:  # Right
            x = scene_rect.width() - width - margin_r
        else:  # Center
            x = (scene_rect.width() - width) / 2

        if align in [7, 8, 9]:  # Top
            y = margin_v
        elif align in [1, 2, 3]:  # Bottom
            y = scene_rect.height() - height - margin_v
        else:  # Middle
            y = (scene_rect.height() - height) / 2

        # Set pos for main items
        fill_item.setPos(x, y)
        if outline_item:
            outline_item.setPos(x, y)
        if back_rect:
            back_rect.setPos(x, y)
        if style['Shadow'] > 0:
            shadow_item.setPos(x + style['Shadow'], y + style['Shadow'])

class ASSStyleDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("window_title"))
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)
        self.resize(1000, 600)
        self.setModal(True)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))

        self.main_layout = QVBoxLayout(self)


        content_layout = QHBoxLayout()


        self.form_group = QGroupBox('')
        self.form_layout = QFormLayout()

        # Font
        self.font_combo = QFontComboBox()
        self.font_combo.currentFontChanged.connect(self.update_preview)
        self.form_layout.addRow(tr("font"), self.font_combo)

        # Font size
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(1, 200)
        self.font_size_spin.valueChanged.connect(self.update_preview)
        self.form_layout.addRow(tr("font_size"), self.font_size_spin)

        # Colors
        self.primary_color_picker = ColorPicker(DEFAULT_STYLE['PrimaryColour'])
        self.primary_color_picker.colorChanged.connect(self.update_preview)
        self.form_layout.addRow(tr("primary_color"), self.primary_color_picker)

        self.secondary_color_picker = ColorPicker(DEFAULT_STYLE['SecondaryColour'])
        self.secondary_color_picker.colorChanged.connect(self.update_preview)
        self.form_layout.addRow(tr("secondary_color"), self.secondary_color_picker)

        self.outline_color_picker = ColorPicker(DEFAULT_STYLE['OutlineColour'])
        self.outline_color_picker.colorChanged.connect(self.update_preview)
        self.form_layout.addRow(tr("outline_color"), self.outline_color_picker)

        self.back_color_picker = ColorPicker(DEFAULT_STYLE['BackColour'])
        self.back_color_picker.colorChanged.connect(self.update_preview)
        self.form_layout.addRow(tr("back_color"), self.back_color_picker)

        # Bold, Italic, Underline, StrikeOut
        self.bold_check = QCheckBox()
        self.bold_check.stateChanged.connect(self.update_preview)
        self.form_layout.addRow(tr("bold"), self.bold_check)

        self.italic_check = QCheckBox()
        self.italic_check.stateChanged.connect(self.update_preview)
        self.form_layout.addRow(tr("italic"), self.italic_check)

        self.underline_check = QCheckBox()
        self.underline_check.stateChanged.connect(self.update_preview)
        self.form_layout.addRow(tr("underline"), self.underline_check)

        self.strikeout_check = QCheckBox()
        self.strikeout_check.stateChanged.connect(self.update_preview)
        self.form_layout.addRow(tr("strikeout"), self.strikeout_check)

        # ScaleX, ScaleY
        self.scale_x_spin = QSpinBox()
        self.scale_x_spin.setRange(1, 1000)
        self.scale_x_spin.valueChanged.connect(self.update_preview)
        self.form_layout.addRow(tr("scale_x"), self.scale_x_spin)

        self.scale_y_spin = QSpinBox()
        self.scale_y_spin.setRange(1, 1000)
        self.scale_y_spin.valueChanged.connect(self.update_preview)
        self.form_layout.addRow(tr("scale_y"), self.scale_y_spin)

        # Spacing
        self.spacing_spin = QSpinBox()
        self.spacing_spin.setRange(-100, 100)
        self.spacing_spin.valueChanged.connect(self.update_preview)
        self.form_layout.addRow(tr("spacing"), self.spacing_spin)

        # Angle
        self.angle_spin = QSpinBox()
        self.angle_spin.setRange(-360, 360)
        self.angle_spin.valueChanged.connect(self.update_preview)
        self.form_layout.addRow(tr("angle"), self.angle_spin)

        # BorderStyle
        self.border_style_combo = QComboBox()
        self.border_style_combo.addItems([tr("border_style_outline"), tr("border_style_opaque")])
        self.border_style_combo.currentIndexChanged.connect(self.update_preview)
        self.form_layout.addRow(tr("border_style"), self.border_style_combo)

        # Outline (border size)
        self.outline_spin = QDoubleSpinBox()
        self.outline_spin.setSingleStep(0.1)
        self.outline_spin.setRange(0.0, 10.0)
        self.outline_spin.setDecimals(1)
        self.outline_spin.valueChanged.connect(self.update_preview)
        self.form_layout.addRow(tr("outline_size"), self.outline_spin)

        # Shadow
        self.shadow_spin = QDoubleSpinBox()
        self.shadow_spin.setRange(0.0, 10.0)
        self.shadow_spin.setSingleStep(0.1)
        self.shadow_spin.setDecimals(1)
        self.shadow_spin.valueChanged.connect(self.update_preview)
        self.form_layout.addRow(tr("shadow_size"), self.shadow_spin)

        # Alignment
        self.alignment_group = QGroupBox(tr("alignment"))
        self.alignment_group.setStyleSheet("QGroupBox { margin-bottom: 12px;margin-top:12px }")   # 标题上留空
        self.alignment_layout = QGridLayout()
        self.alignment_buttons = []
        for i in range(1, 10):
            btn = QPushButton(str(i))
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, val=i: self.set_alignment(val))
            self.alignment_buttons.append(btn)
        positions = [(0,0,7), (0,1,8), (0,2,9),
                     (1,0,4), (1,1,5), (1,2,6),
                     (2,0,1), (2,1,2), (2,2,3)]
        for row, col, val in positions:
            self.alignment_layout.addWidget(self.alignment_buttons[val-1], row, col)
        self.alignment_group.setLayout(self.alignment_layout)
        self.alignment_group.setStyleSheet("""
    QGroupBox {
        margin-top: 14px;    
        padding-top: 10px; 
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 10px;
        padding: 0 3px;
    }
""")
        self.form_layout.addRow(self.alignment_group)

        # Margins
        self.margin_l_spin = QSpinBox()
        self.margin_l_spin.setRange(0, 1000)
        self.margin_l_spin.valueChanged.connect(self.update_preview)
        self.form_layout.addRow(tr("margin_left"), self.margin_l_spin)

        self.margin_r_spin = QSpinBox()
        self.margin_r_spin.setRange(0, 1000)
        self.margin_r_spin.valueChanged.connect(self.update_preview)
        self.form_layout.addRow(tr("margin_right"), self.margin_r_spin)

        self.margin_v_spin = QSpinBox()
        self.margin_v_spin.setRange(0, 1000)
        self.margin_v_spin.valueChanged.connect(self.update_preview)
        self.form_layout.addRow(tr("margin_vertical"), self.margin_v_spin)

        self.form_group.setLayout(self.form_layout)
        content_layout.addWidget(self.form_group)

        # Preview
        self.preview_group = QGroupBox('')
        preview_layout = QVBoxLayout()
        self.preview_widget = PreviewWidget()
        preview_layout.addWidget(self.preview_widget)
        self.preview_group.setLayout(preview_layout)
        content_layout.addWidget(self.preview_group)

        self.main_layout.addLayout(content_layout)

        # Buttons
        self.buttons_layout = QHBoxLayout()
        self.save_btn = QPushButton(tr("save_settings"))
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.clicked.connect(self.save_settings)
        self.save_btn.setMinimumSize(QSize(200, 35))
        self.restore_btn = QPushButton(tr("restore"))
        self.restore_btn.clicked.connect(self.restore_defaults)
        self.restore_btn.setMaximumSize(QSize(150, 20))
        self.restore_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn = QPushButton(tr("close_window"))
        self.close_btn.clicked.connect(self.close)
        self.close_btn.setMaximumSize(QSize(150, 20))
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.buttons_layout.addWidget(self.save_btn)
        self.buttons_layout.addWidget(self.restore_btn)
        self.buttons_layout.addWidget(self.close_btn)
        self.main_layout.addLayout(self.buttons_layout)

        # Load settings if exist
        self.load_settings()
        self.update_preview()

    def set_alignment(self, value):
        for btn in self.alignment_buttons:
            btn.setChecked(False)
        self.alignment_buttons[value-1].setChecked(True)
        self.update_preview()

    def get_alignment(self):
        for i, btn in enumerate(self.alignment_buttons):
            if btn.isChecked():
                return i + 1
        return 2  # Default

    def load_settings(self):
        self.blockSignals(True)
        try:
            if Path(JSON_FILE).exists():
                with open(JSON_FILE, 'r') as f:
                    style = json.load(f)
            else:
                style = DEFAULT_STYLE

            self.font_combo.setCurrentFont(style.get('Fontname', 'Arial'))
            self.font_size_spin.setValue(style.get('Fontsize', 16))
            self.primary_color_picker.color = ColorPicker.parse_color(style.get('PrimaryColour', '&H00FFFFFF&'))
            self.primary_color_picker.update_swatch()
            self.secondary_color_picker.color = ColorPicker.parse_color(style.get('SecondaryColour', '&H00FFFFFF&'))
            self.secondary_color_picker.update_swatch()
            self.outline_color_picker.color = ColorPicker.parse_color(style.get('OutlineColour', '&H00000000&'))
            self.outline_color_picker.update_swatch()
            self.back_color_picker.color = ColorPicker.parse_color(style.get('BackColour', '&H00000000&'))
            self.back_color_picker.update_swatch()
            self.bold_check.setChecked(bool(style.get('Bold', 0)))
            self.italic_check.setChecked(bool(style.get('Italic', 0)))  # 修复：使用 .get()
            self.underline_check.setChecked(bool(style.get('Underline', 0)))
            self.strikeout_check.setChecked(bool(style.get('StrikeOut', 0)))
            self.scale_x_spin.setValue(style.get('ScaleX', 100))
            self.scale_y_spin.setValue(style.get('ScaleY', 100))
            self.spacing_spin.setValue(style.get('Spacing', 0))
            self.angle_spin.setValue(style.get('Angle', 0))
            self.border_style_combo.setCurrentIndex(0 if style.get('BorderStyle', 1) == 1 else 1)
            self.outline_spin.setValue(style.get('Outline', 1))
            self.shadow_spin.setValue(style.get('Shadow', 0))
            self.set_alignment(style.get('Alignment', 2))
            self.margin_l_spin.setValue(style.get('MarginL', 10))
            self.margin_r_spin.setValue(style.get('MarginR', 10))
            self.margin_v_spin.setValue(style.get('MarginV', 10))
        finally:
            self.blockSignals(False)

    def save_settings(self):
        style = self.get_current_style()
        with open(JSON_FILE, 'w') as f:
            json.dump(style, f, indent=4)
        self.close()
    def restore_defaults(self):
        style = DEFAULT_STYLE
        self.blockSignals(True)
        try:
            self.font_combo.setCurrentFont(style['Fontname'])
            self.font_size_spin.setValue(style['Fontsize'])
            self.primary_color_picker.color = ColorPicker.parse_color(style['PrimaryColour'])
            self.primary_color_picker.update_swatch()
            self.secondary_color_picker.color = ColorPicker.parse_color(style['SecondaryColour'])
            self.secondary_color_picker.update_swatch()
            self.outline_color_picker.color = ColorPicker.parse_color(style['OutlineColour'])
            self.outline_color_picker.update_swatch()
            self.back_color_picker.color = ColorPicker.parse_color(style['BackColour'])
            self.back_color_picker.update_swatch()
            self.bold_check.setChecked(bool(style['Bold']))
            self.italic_check.setChecked(bool(style['Italic']))
            self.underline_check.setChecked(bool(style['Underline']))
            self.strikeout_check.setChecked(bool(style['StrikeOut']))
            self.scale_x_spin.setValue(style['ScaleX'])
            self.scale_y_spin.setValue(style['ScaleY'])
            self.spacing_spin.setValue(style['Spacing'])
            self.angle_spin.setValue(style['Angle'])
            self.border_style_combo.setCurrentIndex(0 if style['BorderStyle'] == 1 else 1)
            self.outline_spin.setValue(style['Outline'])
            self.shadow_spin.setValue(style['Shadow'])
            self.set_alignment(style['Alignment'])
            self.margin_l_spin.setValue(style['MarginL'])
            self.margin_r_spin.setValue(style['MarginR'])
            self.margin_v_spin.setValue(style['MarginV'])
        finally:
            self.blockSignals(False)
        
        self.update_preview()
        with open(JSON_FILE, 'w') as f:
            json.dump(style, f, indent=4)

    def get_current_style(self):
        style = {
            'Name': 'Default',
            'Fontname': self.font_combo.currentText(),
            'Fontsize': self.font_size_spin.value(),
            'PrimaryColour': self.primary_color_picker.to_ass_color(),
            'SecondaryColour': self.secondary_color_picker.to_ass_color(),
            'OutlineColour': self.outline_color_picker.to_ass_color(),
            'BackColour': self.back_color_picker.to_ass_color(),
            'Bold': 1 if self.bold_check.isChecked() else 0,
            'Italic': 1 if self.italic_check.isChecked() else 0,
            'Underline': 1 if self.underline_check.isChecked() else 0,
            'StrikeOut': 1 if self.strikeout_check.isChecked() else 0,
            'ScaleX': self.scale_x_spin.value(),
            'ScaleY': self.scale_y_spin.value(),
            'Spacing': self.spacing_spin.value(),
            'Angle': self.angle_spin.value(),
            'BorderStyle': 1 if self.border_style_combo.currentIndex() == 0 else 3,
            'Outline': self.outline_spin.value(),
            'Shadow': self.shadow_spin.value(),
            'Alignment': self.get_alignment(),
            'MarginL': self.margin_l_spin.value(),
            'MarginR': self.margin_r_spin.value(),
            'MarginV': self.margin_v_spin.value(),
            'Encoding': 1
        }
        return style

    def update_preview(self):
        style = self.get_current_style()
        self.preview_widget.update_preview(style)

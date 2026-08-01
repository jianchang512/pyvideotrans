from PySide6.QtCore import QSettings


class DanspMixin:
    table_style_css="""
                QTableWidget {
                    color: #cccccc;
                    border: 1px solid #333;
                    gridline-color: #333;
                }
                QTableWidget::item {
                    padding: 1px 3px;
                }
                QTableWidget::item:selected {
                    background-color: #0066cc;
                }
                QHeaderView::section {
                    background-color: #252525;
                    color: #aaa;
                    border: none;
                    border-right: 1px solid #3e3e3e;
                    padding: 2px;
                }
                QPushButton#playBtn {
                    background-color: transparent;
                    color: white;
                    border: none;
                    border-radius: 2px;
                    padding: 1px 4px;
                    min-width: 20px;
                    max-width: 24px;
                }
            """

        # --- 字号调整函数 ---
    def change_table_font_size(self, delta: int):
        # 1. 统一获取当前 pointSize
        font = self.table.font()
        current_pt = font.pointSize()

        # 容错：如果获取不到 pointSize，给一个合理的默认值（如 10）
        if current_pt <= 0:
            current_pt = 10

        # 计算新字号，限制最小为 6pt
        new_pt = max(6, current_pt + delta)
        font.setPointSize(new_pt)

        # 2. 统一将 QFont 应用给表格和表头
        self.table.setFont(font)
        if self.table.horizontalHeader():
            self.table.horizontalHeader().setFont(font)
        if self.table.verticalHeader():
            self.table.verticalHeader().setFont(font)

        # 3. 如果之前有单元格通过 item.setFont() 单独设置过字体，同步更新
        for row in range(self.table.rowCount()):
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item:
                    item_font = item.font()
                    item_font.setPointSize(new_pt)
                    item.setFont(item_font)

        # 4. 保存设置到 QSettings
        sets = QSettings("pyvideotrans", "settings")
        sets.setValue("danshipin_table_fontsize", new_pt)

import hashlib
import os
import platform
import subprocess
import time
from pathlib import Path


def show_popup(title, text, parent=None):
    from PySide6.QtGui import QIcon
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QMessageBox
    from videotrans.configure import config
    msg = QMessageBox()
    msg.setWindowTitle(title)
    msg.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))
    msg.setText(text)
    msg.addButton(QMessageBox.Yes)
    msg.addButton(QMessageBox.Cancel)
    msg.setWindowModality(Qt.ApplicationModal)  # 设置为应用模态
    msg.setWindowFlags(msg.windowFlags() | Qt.WindowStaysOnTopHint)  # 置于顶层
    msg.setIcon(QMessageBox.Information)
    x = msg.exec()  # 显示消息框
    return x


def show_error(tb_str, report=True):
    """槽函数 显示对话框。"""
    from PySide6 import QtWidgets
    from PySide6.QtGui import QIcon, QDesktopServices
    from PySide6.QtCore import QUrl, Qt
    from videotrans.configure import config

    msg_box = QtWidgets.QMessageBox()
    msg_box.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowSystemMenuHint | Qt.WindowCloseButtonHint)

    icon_path = f"{config.ROOT_DIR}/videotrans/styles/icon.ico"
    try:
        msg_box.setWindowIcon(QIcon(icon_path))
    except Exception as e:
        print(f"Warning: Could not load window icon from {icon_path}. Error: {e}")

    msg_box.setIcon(QtWidgets.QMessageBox.Icon.Critical)
    msg_box.setWindowTitle(config.transobj.get('anerror', 'Error'))
    msg_box.setText(tb_str[:300])
    if len(tb_str) > 300:
        msg_box.setDetailedText(tb_str)

    # 添加一个标准的“OK”按钮
    ok_button = msg_box.addButton(QtWidgets.QMessageBox.StandardButton.Ok)
    if config.defaulelang == 'zh':
        ok_button.setText("知道了")

    # 添加自定义的“报告错误”按钮
    if report:
        report_button = msg_box.addButton("报告错误" if config.defaulelang == 'zh' else "Report Error",
                                          QtWidgets.QMessageBox.ButtonRole.NoRole)
    msg_box.setDefaultButton(ok_button)

    msg_box.setStyleSheet("""
            QMessageBox {
                min-width: 400px;
                max-width: 800px;
                min-height: 400px;
                max-height: 700px;
            }
        """)
    clicked_button_storage = None
    def record_clicked_button(button):
        nonlocal clicked_button_storage
        clicked_button_storage = button

    msg_box.buttonClicked.connect(record_clicked_button)
    msg_box.exec()
    if report and clicked_button_storage == report_button:
        clicked_button = msg_box.clickedButton()
        if clicked_button == report_button:
            import urllib.parse
            import os, platform, sys
            from videotrans import VERSION
            # 对全部错误信息进行URL编码
            encoded_content = urllib.parse.quote(f"{tb_str}\n====="
                                                 f"\n{platform.platform()}"
                                                 f"\nversion:{VERSION}"
                                                 f"\nfrozen:{getattr(sys, 'frozen', False)}"
                                                 f"\nlanguage:{config.defaulelang}")
            full_url = f"https://bbs.pyvideotrans.com/?type=post&content={encoded_content}"

            # 调用系统默认浏览器打开链接
            QDesktopServices.openUrl(QUrl(full_url))


def open_url(url=None, title: str = None):
    import webbrowser
    if url:
        return webbrowser.open_new_tab(url)
    title_url_dict = {
        'bbs': "https://bbs.pyvideotrans.com",
        'ffmpeg': "https://www.ffmpeg.org/download.html",
        'git': "https://github.com/jianchang512/pyvideotrans",
        'issue': "https://github.com/jianchang512/pyvideotrans/issues",
        'discord': "https://discord.gg/7ZWbwKGMcx",
        'models': "https://github.com/jianchang512/stt/releases/tag/0.0",
        'stt': "https://github.com/jianchang512/stt/",

        'gtrans': "https://pyvideotrans.com/aiocr",
        'cuda': "https://pyvideotrans.com/gpu.html",
        'website': "https://pyvideotrans.com",
        'help': "https://pyvideotrans.com",
        'xinshou': "https://pyvideotrans.com/getstart",
        "about": "https://pyvideotrans.com/about",
        'download': "https://github.com/jianchang512/pyvideotrans/releases",
        'openvoice': "https://github.com/kungful/openvoice-api"
    }
    if title and title in title_url_dict:
        return webbrowser.open_new_tab(title_url_dict[title])


def vail_file(file=None):
    if not file:
        return False
    p = Path(file)
    if not p.exists() or not p.is_file():
        return False
    if p.stat().st_size == 0:
        return False
    return True


def hide_show_element(wrap_layout, show_status):
    def hide_recursive(layout, show_status):
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item.widget():
                if not show_status:
                    item.widget().hide()
                else:
                    item.widget().show()
            elif item.layout():
                hide_recursive(item.layout(), show_status)

    hide_recursive(wrap_layout, show_status)


def shutdown_system():
    # 获取当前操作系统类型
    system = platform.system()

    if system == "Windows":
        # Windows 下的关机命令
        subprocess.call("shutdown /s /t 1")
    elif system == "Linux":
        # Linux 下的关机命令
        subprocess.call("poweroff")
    elif system == "Darwin":
        # macOS 下的关机命令
        subprocess.call("sudo shutdown -h now", shell=True)
    else:
        print(f"Unsupported system: {system}")


# 获取 prompt提示词
def get_prompt(ainame, is_srt=True):
    from videotrans.configure import config
    prompt_file = get_prompt_file(ainame=ainame, is_srt=is_srt)
    content = Path(prompt_file).read_text(encoding='utf-8')
    glossary = ''
    if Path(config.ROOT_DIR + '/videotrans/glossary.txt').exists():
        glossary = Path(config.ROOT_DIR + '/videotrans/glossary.txt').read_text(encoding='utf-8').strip()
    if glossary:
        glossary = "\n".join(["|" + it.replace("=", '|') + "|" for it in glossary.split('\n')])
        glossary_prompt = """## 术语表\n严格按照以下术语表进行翻译,如果句子中出现术语,必须使用对应的翻译,而不能自由翻译：\n| 术语  | 翻译  |\n| --------- | ----- |\n""" if config.defaulelang == 'zh' else """## Glossary of terms\nTranslations are made strictly according to the following glossary. If a term appears in a sentence, the corresponding translation must be used, not a free translation:\n| Glossary | Translation |\n| --------- | ----- |\n"""
        content = content.replace('<INPUT></INPUT>', f"""{glossary_prompt}{glossary}\n\n<INPUT></INPUT>""")
    return content


# 获取当前需要操作的prompt txt文件
def get_prompt_file(ainame, is_srt=True):
    from videotrans.configure import config
    prompt_path = f'{config.ROOT_DIR}/videotrans/'
    prompt_name = f'{ainame}{"" if config.defaulelang == "zh" else "-en"}.txt'
    if is_srt and config.settings.get('aisendsrt', False):
        prompt_path += 'prompts/srt/'
    return f'{prompt_path}{prompt_name}'


def check_local_api(api):
    from videotrans.configure import config
    if not api:
        show_error('必须填写http地址' if config.defaulelang == 'zh' else 'Must fill in the http address', False)
        return False
    if api.find('0.0.0.0:') > -1:
        show_error(
            '请将 0.0.0.0 改为 127.0.0.1 ' if config.defaulelang == 'zh' else 'Please change 0.0.0.0 to 127.0.0.1. ', False)
        return False
    return True


def show_glossary_editor(parent):
    from PySide6.QtWidgets import (QVBoxLayout, QTextEdit, QDialog,
                                   QDialogButtonBox)
    from PySide6.QtCore import Qt
    from videotrans.configure import config
    """
    弹出一个窗口，包含一个文本框和保存按钮，并处理文本的读取和保存。

    Args:
        parent: 父窗口 (QWidget)
    """
    dialog = QDialog(parent)
    dialog.setWindowTitle("在此填写术语对照表，格式： 术语=翻译" if config.defaulelang == 'zh' else '')
    dialog.setMinimumSize(600, 400)

    layout = QVBoxLayout(dialog)

    text_edit = QTextEdit()
    text_edit.setPlaceholderText(
        "请按照 术语=翻译 的格式，一行一组来填写，例如\n\n首席执行官=CEO\n人工智能=AI\n\n在原文中如果遇到以上左侧文字，则翻译结果使用右侧文字" if config.defaulelang == 'zh' else "Please fill in one line at a time, following the term on the left and the translation on the right, e.g. \nBallistic Missile Defense=BMD\nChief Executive Officer=CEO")
    layout.addWidget(text_edit)

    button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
    layout.addWidget(button_box)

    # 读取文件内容，并设置为文本框默认值
    file_path = config.ROOT_DIR + "/videotrans/glossary.txt"
    try:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                text_edit.setText(content)
    except Exception as e:
        print(f"读取文件失败: {e}")

    def save_text():
        """
        点击保存按钮，将文本框内容写回文件。
        """
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(text_edit.toPlainText())  # toPlainText 获取纯文本
            dialog.accept()
        except Exception as e:
            print(f"写入文件失败: {e}")

    button_box.accepted.connect(save_text)
    button_box.rejected.connect(dialog.reject)
    dialog.setWindowModality(Qt.WindowModality.ApplicationModal)  # 设置模态窗口
    dialog.exec()  # 显示模态窗口


# 判断 novoice.mp4是否创建好
def is_novoice_mp4(novoice_mp4, noextname, uuid=None):
    # 预先创建好的
    # 判断novoice_mp4是否完成
    t = 0
    from videotrans.configure import config
    if noextname not in config.queue_novice and vail_file(novoice_mp4):
        return True
    if noextname in config.queue_novice and config.queue_novice[noextname] == 'end':
        return True
    last_size = 0
    while True:
        if config.current_status != 'ing' or config.exit_soft:
            return False
        if vail_file(novoice_mp4):
            current_size = os.path.getsize(novoice_mp4)
            if last_size > 0 and current_size == last_size and t > 1200:
                return True
            last_size = current_size

        if noextname not in config.queue_novice:
            msg = f"{noextname} split no voice videoerror:{config.queue_novice=}"
            raise Exception(msg)
        if config.queue_novice[noextname] == 'error':
            msg = f"{noextname} split no voice videoerror"
            raise Exception(msg)

        if config.queue_novice[noextname] == 'ing':
            size = f'{round(last_size / 1024 / 1024, 2)}MB' if last_size > 0 else ""
            from . import help_role
            help_role.set_process(
                text=f"{noextname} {'分离音频和画面' if config.defaulelang == 'zh' else 'spilt audio and video'} {size}",
                uuid=uuid)
            time.sleep(3)
            t += 3
            continue
        return True


# 将字符串做 md5 hash处理
def get_md5(input_string: str):
    md5 = hashlib.md5()
    md5.update(input_string.encode('utf-8'))
    return md5.hexdigest()


def pygameaudio(filepath):
    from .playmp3 import AudioPlayer
    player = AudioPlayer(filepath)
    player.start()

import hashlib
import os,re
import platform
import subprocess
import time
from pathlib import Path
from videotrans.configure import config
from tqdm import tqdm


def create_tqdm_class(callback):
    class QtAwareTqdm(tqdm):
        def update(self, n=1):
            # 执行父类更新
            displayed = super().update(n)
            
            # 2. 区分是“总文件计数”还是“单个文件下载”
            # HuggingFace 的文件下载进度条 unit 通常是 'B' (字节)
            # 总文件数进度条 unit 通常是 'it' (个) 或默认值
            is_bytes = self.unit == 'B' or self.unit_scale is True
            
            filename = self.desc if self.desc else "Initializing..."
            
            # 过滤逻辑：
            # 如果你只想在 UI 显示具体文件的下载进度，可以忽略非字节单位的进度条
            # 这里我把 type 传出去，由你的 UI 决定是否显示
            
            if self.total and self.total > 0:
                percent = (self.n / self.total) * 100
            else:
                percent = 0.0

            progress_data = {
                "filename": filename,
                "percent": percent,
                "current": self.n,
                "total": self.total,
                "type": "file" if is_bytes else "summary"  # 增加类型标识
            }
            print(f'{progress_data=}')

            if callback:
                # 只有当它是具体文件下载，或者你确实想看总文件进度时才发送
                # 建议：如果只想看下载进度，加一个 if is_bytes: 判断
                callback(progress_data)

            return displayed
        def display(self, msg=None, pos=None):
            """
            核心修改：重写 display 方法并留空。
            tqdm 原本通过此方法打印字符到终端。
            将其留空后，终端将不会有任何输出，但内部计算依然正常进行。
            """
            pass

    return QtAwareTqdm


def show_popup(title, text):
    from PySide6.QtGui import QIcon
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QMessageBox

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


def show_error(tb_str):
    """槽函数 显示对话框。"""
    from PySide6 import QtWidgets
    from PySide6.QtGui import QIcon, QDesktopServices
    from PySide6.QtCore import QUrl, Qt

    
    msg_box = QtWidgets.QMessageBox()
    msg_box.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowSystemMenuHint | Qt.WindowCloseButtonHint)

    icon_path = f"{config.ROOT_DIR}/videotrans/styles/icon.ico"
    try:
        msg_box.setWindowIcon(QIcon(icon_path))
    except Exception as e:
        print(f"Warning: Could not load window icon from {icon_path}. Error: {e}")

    msg_box.setIcon(QtWidgets.QMessageBox.Icon.Critical)
    msg_box.setWindowTitle(config.tr('anerror'))
    msg_box.setText(tb_str[:300])
    if len(tb_str) > 300:
        msg_box.setDetailedText(tb_str)

    # 添加一个标准的“OK”按钮
    ok_button = msg_box.addButton(QtWidgets.QMessageBox.StandardButton.Ok)
    if config.defaulelang == 'zh':
        ok_button.setText("知道了")

    # 添加自定义的“报告错误”按钮
    report_button = msg_box.addButton(config.tr("Report Error"),QtWidgets.QMessageBox.ButtonRole.NoRole)
    url_button=None
    urls=re.findall(r'\[(https?:.*?)\]',tb_str)
    if urls:
        url_button = msg_box.addButton(config.tr("Open")+config.tr('Download URL'),QtWidgets.QMessageBox.ButtonRole.NoRole)
    
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
    # if report and clicked_button_storage == report_button:
    full_url=None
    if clicked_button_storage == report_button:
        if msg_box.clickedButton() == report_button:
            import urllib.parse
            import os, platform, sys
            from videotrans import VERSION
            # 对全部错误信息进行URL编码
            _isfrozen=getattr(sys, 'frozen', False)
            _msg=f"{tb_str}\n=====\nsystem:{platform.platform()}\nversion:{VERSION}\nfrozen:{_isfrozen}\nlanguage:{config.defaulelang}\nroot_dir:{config.ROOT_DIR}\n"
            if not _isfrozen:
                _msg+=f"Python: {sys.version}\n"
            encoded_content = urllib.parse.quote(_msg)
            full_url = f"https://bbs.pyvideotrans.com/?type=post&content={encoded_content}"
    elif url_button and clicked_button_storage == url_button:
        if msg_box.clickedButton() == url_button:
            full_url=urls[0]
    # 调用系统默认浏览器打开链接
    if full_url:
        QDesktopServices.openUrl(QUrl(full_url))
    

def open_url(url: str = None):
    import webbrowser
    title_url_dict = {
        'bbs': "https://bbs.pyvideotrans.com",
        'ffmpeg': "https://www.ffmpeg.org/download.html",
        'git': "https://github.com/jianchang512/pyvideotrans",
        'issue': "https://github.com/jianchang512/pyvideotrans/issues",
        'hfmirrorcom': "https://pyvideotrans.com/819",
        'models': "https://github.com/jianchang512/stt/releases/tag/0.0",
        'stt': "https://github.com/jianchang512/stt/",

        'gtrans': "https://pyvideotrans.com/aiocr",
        'cuda': "https://pyvideotrans.com/gpu.html",
        'website': "https://pyvideotrans.com",
        'help': "https://pyvideotrans.com",
        'xinshou': "https://pyvideotrans.com/getstart",
        "about": "https://pyvideotrans.com/about",
        'download': "https://github.com/jianchang512/pyvideotrans/releases",
    }
    if url and url.startswith("http"):
        return webbrowser.open_new_tab(url)
    if url and url in title_url_dict:
        return webbrowser.open_new_tab(title_url_dict[url])
    return


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
def get_prompt(ainame,aisendsrt=True):

    prompt_file = get_prompt_file(ainame=ainame,aisendsrt=aisendsrt)
    content = Path(prompt_file).read_text(encoding='utf-8',errors="ignore")
    glossary = ''
    if Path(config.ROOT_DIR + '/videotrans/glossary.txt').exists():
        glossary = Path(config.ROOT_DIR + '/videotrans/glossary.txt').read_text(encoding='utf-8',errors="ignore").strip()
    if glossary:
        glossary = "\n".join(["|" + it.replace("=", '|') + "|" for it in glossary.split('\n')])
        glossary_prompt = """\n\n# Glossary of terms\nTranslations are made strictly according to the following glossary. If a term appears in a sentence, the corresponding translation must be used, not a free translation:\n| Glossary | Translation |\n| --------- | ----- |\n"""
        content = content.replace('# Actual Task', f"""{glossary_prompt}{glossary}\n\n# Actual Task""")
    return content


def qwenmt_glossary():

    if Path(config.ROOT_DIR + '/videotrans/glossary.txt').exists():
        glossary = Path(config.ROOT_DIR + '/videotrans/glossary.txt').read_text(encoding='utf-8',errors="ignore").strip()
        if glossary:
            term=[]
            for it in glossary.split('\n'):
                tmp=it.split("=")
                if len(tmp)==2:
                    term.append({"source":tmp[0],"target":tmp[1]})
            return term if len(term)>0 else None
    return None

# 获取当前需要操作的prompt txt文件
def get_prompt_file(ainame,aisendsrt=True):

    prompt_path = f'{config.ROOT_DIR}/videotrans/'
    prompt_name = f'{ainame}.txt'
    if aisendsrt:
        prompt_path += 'prompts/srt/'
    else:
        prompt_path += 'prompts/text/'
    return f'{prompt_path}{prompt_name}'




def show_glossary_editor(parent):
    from PySide6.QtWidgets import (QVBoxLayout, QTextEdit, QDialog,
                                   QDialogButtonBox)
    from PySide6.QtCore import Qt


    dialog = QDialog(parent)
    dialog.setWindowTitle(config.tr('Glossary'))
    dialog.setMinimumSize(600, 400)

    layout = QVBoxLayout(dialog)

    text_edit = QTextEdit()
    text_edit.setPlaceholderText(
        config.tr("Please fill in one line at a time, following the term on the left and the translation on the right, e.g. ,Ballistic Missile Defense=BMD"))
    layout.addWidget(text_edit)

    button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
    layout.addWidget(button_box)

    # 读取文件内容，并设置为文本框默认值
    file_path = config.ROOT_DIR + "/videotrans/glossary.txt"
    try:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8",errors="ignore") as f:
                content = f.read()
                text_edit.setText(content)
    except Exception as e:
        print(f"读取文件失败: {e}")

    def save_text():
        """
        点击保存按钮，将文本框内容写回文件。
        """
        try:
            with open(file_path, "w", encoding="utf-8",errors="ignore") as f:
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
            if 0 < last_size == current_size and t > 1200:
                return True
            last_size = current_size

        if noextname not in config.queue_novice:
            raise RuntimeError(f"{noextname} split no voice videoerror-1")
        if config.queue_novice[noextname].startswith('error:'):
            raise RuntimeError(f"{noextname} split no voice {config.queue_novice[noextname]}")

        if config.queue_novice[noextname] == 'ing':
            size = f'{round(last_size / 1024 / 1024, 2)}MB' if last_size > 0 else ""
            from . import help_role
            help_role.set_process(
                text=f"{noextname} {config.tr('spilt audio and video')} {size}",
                uuid=uuid)
            time.sleep(1)
            t += 1
            continue
        return True


# 将字符串做 md5 hash处理
def get_md5(input_string: str):
    md5 = hashlib.md5()
    md5.update(input_string.encode('utf-8'))
    return md5.hexdigest()


def pygameaudio(filepath=None):
    try:
        import soundfile as sf
        import sounddevice as sd
        data, fs = sf.read(filepath)
        sd.play(data, fs)
        sd.wait()
    except Exception as e:
        print(e)



def read_last_n_lines(filename, n=100):
    if not Path(filename).exists():
        return []
    from collections import deque
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            # 使用 deque 只保留最后 n 行
            last_lines = deque(file, maxlen=n)
        return list(last_lines)  # 返回列表形式
    except FileNotFoundError:
        return []
    except Exception as e:
        return []
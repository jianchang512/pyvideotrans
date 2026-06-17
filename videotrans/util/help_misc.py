import hashlib
import json
import os, re
import platform
import subprocess
import sys
import time
from dataclasses import is_dataclass, asdict
from functools import lru_cache
from pathlib import Path

from videotrans import VERSION
from videotrans.configure.config import tr, app_cfg, logger, ROOT_DIR, defaulelang, push_queue
from videotrans.task.taskcfg import SignMsg



def show_popup(title, text):
    from PySide6.QtGui import QIcon
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QMessageBox

    msg = QMessageBox()
    msg.setWindowTitle(title)
    msg.setWindowIcon(QIcon(f"{ROOT_DIR}/videotrans/styles/icon.ico"))
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

    icon_path = f"{ROOT_DIR}/videotrans/styles/icon.ico"
    try:
        msg_box.setWindowIcon(QIcon(icon_path))
    except Exception as e:
        logger.exception(f"Warning: Could not load window icon from {icon_path}. Error: {e}", exc_info=True)

    msg_box.setIcon(QtWidgets.QMessageBox.Icon.Critical)
    msg_box.setWindowTitle(tr('anerror'))
    msg_box.setText(tb_str[:300])
    if len(tb_str) > 300:
        msg_box.setDetailedText(tb_str)

    # 添加一个标准的“OK”按钮
    ok_button = msg_box.addButton(QtWidgets.QMessageBox.StandardButton.Ok)
    if defaulelang == 'zh':
        ok_button.setText("知道了")

    # 添加自定义的“报告错误”按钮
    report_button = msg_box.addButton(tr("Report Error"), QtWidgets.QMessageBox.ButtonRole.NoRole)
    url_button = None
    urls = re.findall(r'\[(https?:.*?)]', tb_str)
    if urls:
        url_button = msg_box.addButton(tr("Open") + tr('Download URL'), QtWidgets.QMessageBox.ButtonRole.NoRole)

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
    full_url = None
    if clicked_button_storage == report_button:
        if msg_box.clickedButton() == report_button:
            import urllib.parse
            import os, platform, sys
            from videotrans import VERSION
            # 对全部错误信息进行URL编码
            _isfrozen = getattr(sys, 'frozen', False)
            _msg = f"{tb_str}\n=====\nsystem:{platform.platform()}\nversion:{VERSION}\nfrozen:{_isfrozen}\nlanguage:{defaulelang}\nroot_dir:{ROOT_DIR}\n"
            if not _isfrozen:
                _msg += f"Python: {sys.version}\n"
            encoded_content = urllib.parse.quote(_msg)
            full_url = f"https://bbs.pyvideotrans.com/?type=post&content={encoded_content}"
    elif url_button and clicked_button_storage == url_button:
        if msg_box.clickedButton() == url_button:
            full_url = urls[0]
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
        logger.error(f"Unsupported system: {system}")


# 获取 prompt提示词
def get_prompt(ainame, aisendsrt=True):
    prompt_file = get_prompt_file(ainame=ainame, aisendsrt=aisendsrt)
    content = Path(prompt_file).read_text(encoding='utf-8-sig', errors="ignore")
    glossary = ''
    if Path(ROOT_DIR + '/videotrans/glossary.txt').exists():
        glossary = Path(ROOT_DIR + '/videotrans/glossary.txt').read_text(encoding='utf-8-sig', errors="ignore").strip()
        if glossary:
            glossary = "\n".join(["|" + it.replace("=", '|') + "|" for it in glossary.split('\n')])
            glossary = f"\n\n# Glossary of terms\nTranslations are made strictly according to the following glossary. If a term appears in a sentence, the corresponding translation must be used, not a free translation:\n| Glossary | Translation |\n| --------- | ----- |\n{glossary}\n\n"
    content = content.replace('{GLOSSARY_DICT}', glossary)
    return content


def qwenmt_glossary():
    if Path(ROOT_DIR + '/videotrans/glossary.txt').exists():
        glossary = Path(ROOT_DIR + '/videotrans/glossary.txt').read_text(encoding='utf-8-sig', errors="ignore").strip()
        if glossary:
            term = []
            for it in glossary.split('\n'):
                tmp = it.split("=")
                if len(tmp) == 2:
                    term.append({"source": tmp[0], "target": tmp[1]})
            return term if len(term) > 0 else None
    return None


# 获取当前需要操作的prompt txt文件
@lru_cache
def get_prompt_file(ainame, aisendsrt=True):
    prompt_path = f'{ROOT_DIR}/videotrans/'
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
    dialog.setWindowTitle(tr('Glossary'))
    dialog.setMinimumSize(600, 400)

    layout = QVBoxLayout(dialog)

    text_edit = QTextEdit()
    text_edit.setPlaceholderText(
        tr("Please fill in one line at a time, following the term on the left and the translation on the right, e.g. ,Ballistic Missile Defense=BMD"))
    layout.addWidget(text_edit)

    button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
    layout.addWidget(button_box)

    # 读取文件内容，并设置为文本框默认值
    file_path = ROOT_DIR + "/videotrans/glossary.txt"
    try:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8-sig", errors="ignore") as f:
                content = f.read()
                text_edit.setText(content)
    except Exception as e:
        logger.exception(f"读取术语表文件失败: {e}", exc_info=True)

    def save_text():
        """
        点击保存按钮，将文本框内容写回文件。
        """
        try:
            with open(file_path, "w", encoding="utf-8", errors="ignore") as f:
                f.write(text_edit.toPlainText())  # toPlainText 获取纯文本
            dialog.accept()
        except Exception as e:
            logger.exception(f"写入术语表文件失败: {e}", exc_info=True)

    button_box.accepted.connect(save_text)
    button_box.rejected.connect(dialog.reject)
    dialog.setWindowModality(Qt.WindowModality.ApplicationModal)  # 设置模态窗口
    dialog.exec()  # 显示模态窗口


# 判断 novoice.mp4是否创建好
def is_novoice_mp4(novoice_mp4, noextname, uuid=None):
    # 预先创建好的
    # 判断novoice_mp4是否完成
    t = 0

    if noextname not in app_cfg.queue_novice and vail_file(novoice_mp4):
        return True
    if noextname in app_cfg.queue_novice and app_cfg.queue_novice[noextname] == 'end':
        return True
    last_size = 0
    while True:
        if app_cfg.current_status != 'ing' or app_cfg.exit_soft:
            return False
        if vail_file(novoice_mp4):
            current_size = os.path.getsize(novoice_mp4)
            if 0 < last_size == current_size and t > 1200:
                return True
            last_size = current_size

        if noextname not in app_cfg.queue_novice:
            raise RuntimeError(f"{noextname} split no voice videoerror-1")
        if app_cfg.queue_novice[noextname].startswith('error:'):
            raise RuntimeError(f"{noextname} split no voice {app_cfg.queue_novice[noextname]}")

        if app_cfg.queue_novice[noextname] == 'ing':
            size = f'{round(last_size / 1024 / 1024, 2)}MB' if last_size > 0 else ""
            set_process(
                text=f"{noextname} {tr('spilt audio and video')} {size}",
                uuid=uuid)
            time.sleep(1)
            t += 1
            continue
        return True


# 将字符串做 md5 hash处理
@lru_cache
def get_md5(input_string: str):
    md5 = hashlib.md5()
    md5.update(input_string.encode('utf-8'))
    return md5.hexdigest()


def pygameaudio(filepath=None):
    try:
        import soundfile as sf
        import sounddevice as sd
        data, fs = sf.read(filepath)
        channels = 1 if data.ndim == 1 else data.shape[1]
        try:
            device_info = sd.query_devices(kind='output')
            max_channels = int(device_info.get('max_output_channels') or channels)
        except Exception:
            max_channels = channels

        if channels == 1 and max_channels >= 2:
            data = data.reshape(-1, 1).repeat(2, axis=1)
        elif channels > max_channels > 0:
            data = data[:, :max_channels]
        sd.play(data, fs)
        sd.wait()
    except Exception as e:
        logger.exception(f'播放试听声音失败:{e}')


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
    except Exception:
        return []


# 综合写入日志，默认sp界面
# type=logs|error|subtitle|end|stop|succeed|set_precent|replace_subtitle|.... 末尾显示类型，
# uuid 任务的唯一id，用于确定插入哪个子队列
def set_process(*, text="", type="logs", uuid=None):
    if app_cfg.exit_soft:
        return
    try:
        if text:
            text = text.replace('\\n', ' ')

        if app_cfg.exec_mode == 'cli':
            print(text)
            return
        log = SignMsg(**{"text": text, "type": type, "uuid": uuid})
        push_queue(uuid or "", log)
    except Exception as e:
        logger.exception(f'set_process：{e}', exc_info=True)


def set_proxy(set_val=''):
    if set_val == 'del':
        app_cfg.proxy = ''
        if os.environ.get('HTTP_PROXY'):
            del os.environ['HTTP_PROXY']
        if os.environ.get('HTTPS_PROXY'):
            del os.environ['HTTPS_PROXY']
        return

    if set_val:
        # 设置代理
        set_val = set_val.lower()
        if not set_val.startswith("http") and not set_val.startswith('sock'):
            set_val = f"http://{set_val}"
        app_cfg.proxy = set_val
        os.environ['HTTP_PROXY'] = set_val
        os.environ['HTTPS_PROXY'] = set_val
        return set_val

    # 获取代理
    http_proxy = app_cfg.proxy or os.environ.get('HTTP_PROXY') or os.environ.get('HTTPS_PROXY')

    if http_proxy:
        http_proxy = http_proxy.lower()
        if not http_proxy.startswith("http") and not http_proxy.startswith('sock'):
            http_proxy = f"http://{http_proxy}"
        return http_proxy
    if sys.platform != 'win32':
        return None
    try:
        import winreg
        # 打开 Windows 注册表
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r'Software\Microsoft\Windows\CurrentVersion\Internet Settings') as key:
            # 读取代理设置
            proxy_enable, _ = winreg.QueryValueEx(key, 'ProxyEnable')
            proxy_server, _ = winreg.QueryValueEx(key, 'ProxyServer')
            if proxy_enable == 1 and proxy_server:
                # 是否需要设置代理
                proxy_server = proxy_server.lower()
                if not proxy_server.startswith("http") and not proxy_server.startswith('sock'):
                    proxy_server = "http://" + proxy_server

                return proxy_server
    except Exception:
        pass
    return None

@lru_cache
def process_openai_api(url=""):
    if not url:
        return "https://api.openai.com/v1"
    if not url.startswith('http'):
        url = 'http://' + url

    # 删除末尾 /
    url = url.rstrip('/').lower()
    if url.find(".openai.com") > -1:
        return "https://api.openai.com/v1"

    if url.endswith('/v1'):
        return url

    # 存在 /v1/xx的，改为 /v1
    if url.find('/v1/chat/') > -1:
        return re.sub(r'/v1.*$', '/v1', url, flags=re.I | re.S)

    return url


# 序列化

def serial(data: object) -> str:
    if not isinstance(data, list):
        return json.dumps(asdict(data) if is_dataclass(data) else data)
    _newlist = []
    for it in data:
        _newlist.append(asdict(it) if is_dataclass(it) else it)
    return json.dumps(_newlist)


def check_new_version():
    # 查看当前最新版本信息
    try:

        import requests
        # 纯静态文件，仅返回版本信息字符串
        # 只获取当前软件版本号数字和操作系统类型(win32/macos/linux)
        url = f"https://pyvideotrans.com/version.json?version={VERSION}&os={sys.platform}"
        res = requests.get(url)
        res.raise_for_status()
        d = res.json()
        app_cfg.new_version_pvt = d['version']
    except Exception:
        #logger.exception(f'获取最新版本信息失败{e}', exc_info=True)
        pass



def _get_type_name(type_index, name_list):
    if type_index is None or type_index >= len(name_list):
        return '-'
    return name_list[type_index]

@lru_cache
def get_recogn_type(type_index=None):
    from videotrans.recognition import RECOGN_NAME_LIST
    return _get_type_name(type_index, RECOGN_NAME_LIST)

@lru_cache
def get_tanslate_type(type_index=None):
    from videotrans.translator import TRANSLASTE_NAME_LIST
    return _get_type_name(type_index, TRANSLASTE_NAME_LIST)

@lru_cache
def get_tts_type(type_index=None):
    from videotrans.tts import TTS_NAME_LIST
    return _get_type_name(type_index, TTS_NAME_LIST)


def is_connect_hf()->bool:
    try:
        import requests
        logger.debug(f'{app_cfg.proxy=}')
        if app_cfg.proxy:
            requests.head('https://huggingface.co', timeout=5,proxies={"http":app_cfg.proxy,"https":app_cfg.proxy})
        else:
            requests.head('https://huggingface.co', timeout=5)
    except Exception as e:
        os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
        logger.debug(f'无法连接 huggingface.co, 使用镜像替换: hf-mirror.com')
        return False
    else:
        os.environ['HF_ENDPOINT'] = 'https://huggingface.co'
        logger.debug('可以使用 huggingface.co')
        return True
    return False


def show_refaudio_win():
    from videotrans.component.set_form import RefaudioForm
    dialog = RefaudioForm()
    dialog.exec()
    return

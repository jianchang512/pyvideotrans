import json
import os
import re
import threading
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QFileDialog

from videotrans import translator, recognition, tts
from videotrans.configure import config
from videotrans.mainwin._actions_sub import WinActionSub
from videotrans.util import tools


def _list_gcloud_voices_for(lang_code: str, cred_path: str):
    TextToSpeechClient = None
    try:
        from google.cloud.texttospeech import TextToSpeechClient
    except ImportError:
        try:
            from google.cloud import texttospeech
            TextToSpeechClient = texttospeech.TextToSpeechClient
        except ImportError:
            pass
    """Lista as vozes do Google Cloud TTS disponíveis para um idioma específico."""
    if not cred_path:
        config.logger.error("Caminho das credenciais do Google Cloud TTS não configurado")
        return []

    if not TextToSpeechClient:
        config.logger.error(
            "Pacote google-cloud-texttospeech não encontrado. Execute: pip install google-cloud-texttospeech")
        return []

    if not os.path.isfile(cred_path):
        config.logger.error(f"Arquivo de credenciais não encontrado: {cred_path}")
        return []

    # Mapeamento de nomes de idiomas para códigos do Google Cloud TTS
    GOOGLE_TTS_LANG_MAP = {
        "Portuguese": "pt-BR",  # Mapeamento especial para "Portuguese"
        "English": "en-US",
        "Spanish": "es-ES",
        "French": "fr-FR",
        "German": "de-DE",
        "Italian": "it-IT",
        "Japanese": "ja-JP",
        "Korean": "ko-KR",
        "Chinese": "zh-CN",
        "Traditional Chinese": "zh-TW",
        "Russian": "ru-RU",
        "Hindi": "hi-IN",
        "Arabic": "ar-XA",
        "Turkish": "tr-TR",
        "Thai": "th-TH",
        "Vietnamese": "vi-VN",
        "Indonesian": "id-ID"
    }

    # Se o código de idioma for um nome (ex: "Portuguese"), converte para o código do Google Cloud TTS
    google_lang_code = GOOGLE_TTS_LANG_MAP.get(lang_code, lang_code)

    # Se ainda não estiver no formato do Google Cloud TTS (ex: "pt"), tenta converter
    if '-' not in google_lang_code:
        # Mapeamento de códigos base para códigos completos do Google Cloud TTS
        BASE_TO_GOOGLE = {
            "pt": "pt-BR",
            "en": "en-US",
            "es": "es-ES",
            "fr": "fr-FR",
            "de": "de-DE",
            "it": "it-IT",
            "ja": "ja-JP",
            "ko": "ko-KR",
            "zh": "zh-CN",
            "zh-tw": "zh-TW",
            "ru": "ru-RU",
            "hi": "hi-IN",
            "ar": "ar-XA",
            "tr": "tr-TR",
            "th": "th-TH",
            "vi": "vi-VN",
            "id": "id-ID"
        }
        lang_base = google_lang_code.split('-')[0].lower()
        google_lang_code = BASE_TO_GOOGLE.get(lang_base, google_lang_code)

    config.logger.info(f"Usando código de idioma do Google Cloud TTS: {google_lang_code} (original: {lang_code})")

    try:
        config.logger.info(f"Tentando listar vozes do Google Cloud TTS para idioma {google_lang_code}")
        client = TextToSpeechClient.from_service_account_file(cred_path)

        # Tenta listar todas as vozes
        try:
            all_voices = client.list_voices().voices
            config.logger.info(f"Total de vozes encontradas: {len(all_voices)}")
        except Exception as e:
            config.logger.error(f"Erro ao listar vozes: {str(e)}")
            if "PERMISSION_DENIED" in str(e):
                config.logger.error("Credenciais sem permissão para acessar a API do Google Cloud TTS")
            return []

        # Filtra vozes pelo idioma
        voices = sorted([
            v.name for v in all_voices
            if any(google_lang_code.lower() in lc.lower() for lc in v.language_codes)
        ])

        config.logger.info(f"Vozes encontradas para {google_lang_code}: {len(voices)}")
        if voices:
            config.logger.info(f"Primeiras vozes: {voices[:3]}")
        else:
            config.logger.warning(f"Nenhuma voz encontrada para o idioma {google_lang_code}")

        return voices

    except Exception as e:
        config.logger.error(f"Erro ao listar vozes do Google Cloud TTS: {str(e)}")
        if "invalid_grant" in str(e).lower():
            config.logger.error("Credenciais inválidas ou expiradas")
        elif "not found" in str(e).lower():
            config.logger.error("Arquivo de credenciais não encontrado ou inválido")
        return []


@dataclass
class WinAction(WinActionSub):

    def _reset(self):
        # 单个执行时，当前字幕所处阶段：识别后编辑或翻译后编辑
        self.edit_subtitle_type = ''
        # 单个任务时，修改字幕后需要保存到的位置，原始语言字幕或者目标语音字幕
        self.wait_subtitle = ''
        # 存放需要处理的视频dict信息，包括uuid
        self.obj_list = []
        self.main.source_mp4.setText(config.transobj["No select videos"])

    # 删除进度按钮
    def delete_process(self):
        for i in range(self.main.processlayout.count()):
            item = self.main.processlayout.itemAt(i)
            if item.widget():
                try:
                    item.widget().deleteLater()
                except Exception as e:
                    pass
        self.processbtns = {}

    # 将倒计时设为立即超时
    def set_djs_timeout(self):
        self.main.timeout_tips.setText('')
        self.main.stop_djs.hide()
        self.main.continue_compos.hide()
        self.main.continue_compos.setText('')
        self.main.continue_compos.setDisabled(True)
        self.main.subtitle_area.setReadOnly(True)
        self.update_subtitle()
        config.task_countdown = -1

    # 手动点击暂停按钮
    def reset_timeid(self):
        config.task_countdown = 86400
        self.main.stop_djs.hide()
        self.main.timeout_tips.setText('')
        self.main.continue_compos.setDisabled(False)
        self.main.continue_compos.setText(config.transobj['nextstep'])
        self.update_data('{"type":"allow_edit"}')

    # 翻译渠道变化时，检测条件
    def set_translate_type(self, idx):
        try:
            t = self.main.target_language.currentText()
            if t not in ['-']:
                rs = translator.is_allow_translate(translate_type=idx, show_target=t, win=self.main)
                if rs is not True:
                    return False
        except Exception as e:
            tools.show_error(str(e))

    def show_xxl_select(self):
        import sys
        if sys.platform != 'win32':
            tools.show_error(
                'faster-whisper-xxl.exe 仅在Windows下可用' if config.defaulelang == 'zh' else 'faster-whisper-xxl.exe is only available on Windows')
            return False
        if not config.settings.get('Faster_Whisper_XXL') or not Path(
                config.settings.get('Faster_Whisper_XXL', '')).exists():
            from PySide6.QtWidgets import QFileDialog
            exe, _ = QFileDialog.getOpenFileName(self.main,
                                                 '选择 faster-whisper-xxl.exe' if config.defaulelang == 'zh' else "Select faster-whisper-xxl.exe",
                                                 'C:/', f'Files(*.exe)')
            if exe:
                config.settings['Faster_Whisper_XXL'] = Path(exe).as_posix()
                return True
            return False
        return True

    # 语音识别方式改变时
    def recogn_type_change(self):
        recogn_type = self.main.recogn_type.currentIndex()
        if recogn_type == recognition.Faster_Whisper_XXL and not self.show_xxl_select():
            return

        # 判断不是 faster，禁用分割模式、隐藏vad参数和均等分割设置
        if recogn_type != recognition.FASTER_WHISPER:
            self.main.split_type.setDisabled(True)
            self.main.split_type.setCurrentIndex(0)
            tools.hide_show_element(self.main.hfaster_layout, False)
            tools.hide_show_element(self.main.equal_split_layout, False)
        else:
            # 是 faster，启用 分割模式，根据需要显示均等分割
            self.main.split_type.setDisabled(False)
            tools.hide_show_element(self.main.equal_split_layout,
                                    False if self.main.split_type.currentIndex() == 0 else True)

        if recogn_type not in [recognition.FASTER_WHISPER, recognition.OPENAI_WHISPER, recognition.Faster_Whisper_XXL,
                               recognition.Deepgram, recognition.FUNASR_CN, recognition.PARAKEET]:
            # 禁止模块选择
            self.main.model_name.setDisabled(True)
            self.main.model_name_help.setDisabled(True)
            self.main.rephrase.setDisabled(True)
        else:
            # 允许模块选择
            self.main.rephrase.setDisabled(False)
            self.main.model_name_help.setDisabled(False)
            self.main.model_name.setDisabled(False)
            self.main.model_name.clear()
            if recogn_type in [recognition.FASTER_WHISPER, recognition.OPENAI_WHISPER, recognition.Faster_Whisper_XXL]:
                self.main.model_name.addItems(config.WHISPER_MODEL_LIST)
            elif recogn_type == recognition.Deepgram:
                self.main.model_name.addItems(config.DEEPGRAM_MODEL)
            else:
                self.main.model_name.addItems(config.FUNASR_MODEL)
        lang = translator.get_code(show_text=self.main.source_language.currentText())
        if (
                self.main.model_name.currentText() == 'paraformer-zh' and recogn_type == recognition.FUNASR_CN) or recogn_type == recognition.Deepgram or recogn_type == recognition.GEMINI_SPEECH:
            self.main.show_spk.setVisible(True)
        else:
            self.main.show_spk.setVisible(False)
            self.main.show_spk.setChecked(False)

        is_allow_lang = recognition.is_allow_lang(langcode=lang, recogn_type=recogn_type,
                                                  model_name=self.main.model_name.currentText())
        if is_allow_lang is not True:
            self.main.show_tips.setText(is_allow_lang)
        else:
            self.main.show_tips.setText('')

        if recognition.is_input_api(recogn_type=recogn_type) is not True:
            return

    def check_model_name(self):
        recogn_type = self.main.recogn_type.currentIndex()
        model = self.main.model_name.currentText()
        res = recognition.check_model_name(
            recogn_type=recogn_type,
            name=model,
            source_language_isLast=self.main.source_language.currentIndex() == self.main.source_language.count() - 1,
            source_language_currentText=self.main.source_language.currentText()
        )

        if res is not True:
            return tools.show_error(res)

        if (
                model == 'paraformer-zh' and recogn_type == recognition.FUNASR_CN) or recogn_type == recognition.Deepgram or recogn_type == recognition.GEMINI_SPEECH:
            self.main.show_spk.setVisible(True)
        else:
            self.main.show_spk.setVisible(False)
        return True

    # 判断 语音参数 vad参数区域是否应该可见
    # 仅当是 faster并且 是整体识别
    def click_reglabel(self):
        if self.main.recogn_type.currentIndex() == recognition.FASTER_WHISPER and self.main.split_type.currentIndex() == 0:
            self.hide_show_element(self.main.hfaster_layout, not self.main.threshold.isVisible())
        else:
            self.hide_show_element(self.main.hfaster_layout, False)

    # 是否属于 配音角色 随所选目标语言变化的配音渠道 是 edgeTTS AzureTTS 或 302.ai同时 ai302tts_model=azure
    def change_by_lang(self, type):
        if type in [tts.EDGE_TTS, tts.AZURE_TTS, tts.VOLCENGINE_TTS, tts.AI302_TTS, tts.KOKORO_TTS]:
            return True
        return False

    # tts类型改变
    def tts_type_change(self, type):
        if tts.is_input_api(tts_type=type) is not True:
            self.main.tts_type.setCurrentIndex(0)
            return

        lang = translator.get_code(show_text=self.main.target_language.currentText())
        if lang and lang != '-':
            is_allow_lang = tts.is_allow_lang(langcode=lang, tts_type=type)
            if is_allow_lang is not True:
                self.main.show_tips.setText(is_allow_lang)
            else:
                self.main.show_tips.setText('')

        config.line_roles = {}
        if type == tts.GOOGLE_TTS:
            self.main.voice_role.clear()
            self.main.current_rolelist = ["gtts"]
            self.main.voice_role.addItems(self.main.current_rolelist)
        elif type == tts.GOOGLECLOUD_TTS:
            # Para Google Cloud TTS, vamos usar o idioma atual para listar as vozes
            lang = self.main.target_language.currentText()
            cred = config.params.get("gcloud_credential_json", "").strip()

            if not cred:
                tools.show_error(
                    "Por favor, configure o arquivo de credenciais do Google Cloud TTS em:\n"
                    "Configurações > Google Cloud TTS > Credenciais"
                )
                self.main.voice_role.clear()
                self.main.current_rolelist = ['No']
                self.main.voice_role.addItems(['No'])
                return

            try:
                roles = _list_gcloud_voices_for(lang, cred)
                self.main.voice_role.clear()
                self.main.current_rolelist = roles

                if not roles:
                    tools.show_error(
                        f"Não foi possível encontrar vozes para o idioma {lang}.\n\n"
                        "Verifique:\n"
                        "1. Se o arquivo de credenciais está correto\n"
                        "2. Se as credenciais têm permissão para acessar a API\n"
                        "3. Se o idioma selecionado é suportado\n\n"
                        "Consulte os logs para mais detalhes."
                    )
                    self.main.voice_role.addItems(['No'])
                else:
                    self.main.voice_role.addItems(['No'] + roles)

            except Exception as e:
                config.logger.error(f"Erro ao listar vozes do Google Cloud TTS: {str(e)}")
                tools.show_error(
                    f"Erro ao listar vozes do Google Cloud TTS:\n{str(e)}\n\n"
                    "Verifique os logs para mais detalhes."
                )
                self.main.voice_role.clear()
                self.main.current_rolelist = ['No']
                self.main.voice_role.addItems(['No'])
        elif type == tts.OPENAI_TTS:
            self.main.voice_role.clear()
            self.main.current_rolelist = config.params['openaitts_role'].split(',')
            self.main.voice_role.addItems(['No'] + self.main.current_rolelist)
        elif type == tts.QWEN_TTS:
            self.main.voice_role.clear()
            self.main.current_rolelist = config.params['qwentts_role'].split(',')
            self.main.voice_role.addItems(['No'] + self.main.current_rolelist)
        elif type == tts.GEMINI_TTS:
            self.main.voice_role.clear()
            self.main.current_rolelist = config.params['gemini_ttsrole'].split(',')
            self.main.voice_role.addItems(['No'] + self.main.current_rolelist)
        elif type == tts.ELEVENLABS_TTS:
            self.main.voice_role.clear()
            self.main.current_rolelist = config.params['elevenlabstts_role']
            if len(self.main.current_rolelist) < 1:
                self.main.current_rolelist = tools.get_elevenlabs_role()
            self.main.voice_role.addItems(['No'] + self.main.current_rolelist)
        elif self.change_by_lang(type):
            self.set_voice_role(self.main.target_language.currentText())
        elif type == tts.CLONE_VOICE_TTS:
            self.main.voice_role.clear()
            self.main.current_rolelist = config.params["clone_voicelist"]
            self.main.voice_role.addItems(self.main.current_rolelist)
            threading.Thread(target=tools.get_clone_role).start()
        elif type == tts.CHATTTS:
            self.main.voice_role.clear()
            config.ChatTTS_voicelist = re.split(r'[,，]', config.settings['chattts_voice'])
            self.main.current_rolelist = list(config.ChatTTS_voicelist)
            self.main.voice_role.addItems(['No'] + self.main.current_rolelist)
        elif type == tts.TTS_API:
            self.main.voice_role.clear()
            self.main.current_rolelist = config.params['ttsapi_voice_role'].strip().split(',')
            self.main.voice_role.addItems(self.main.current_rolelist)
        elif type == tts.GPTSOVITS_TTS:
            rolelist = tools.get_gptsovits_role()
            self.main.voice_role.clear()
            self.main.current_rolelist = list(rolelist.keys()) if rolelist else ['GPT-SoVITS']
            self.main.voice_role.addItems(self.main.current_rolelist)
        elif type == tts.CHATTERBOX_TTS:
            rolelist = tools.get_chatterbox_role()
            self.main.voice_role.clear()
            self.main.current_rolelist = rolelist if rolelist else ['chatterbox']
            self.main.voice_role.addItems(self.main.current_rolelist)
        elif type == tts.COSYVOICE_TTS:
            rolelist = tools.get_cosyvoice_role()
            self.main.voice_role.clear()
            self.main.current_rolelist = list(rolelist.keys()) if rolelist else ['clone']
            self.main.voice_role.addItems(self.main.current_rolelist)
        elif type == tts.FISHTTS:
            rolelist = tools.get_fishtts_role()
            self.main.voice_role.clear()
            self.main.current_rolelist = list(rolelist.keys()) if rolelist else ['FishTTS']
            self.main.voice_role.addItems(self.main.current_rolelist)
        elif type == tts.F5_TTS:
            rolelist = tools.get_f5tts_role()
            self.main.voice_role.clear()
            self.main.current_rolelist = ['clone'] + list(rolelist.keys()) if rolelist else ['clone']
            self.main.voice_role.addItems(self.main.current_rolelist)
        # VVVVVV 在这里添加下面的代码块 VVVVVV
        elif type == tts.INDEXTTS2_TTS:
            # 这是为 Index-TTS2 在运行时切换时加载角色列表的逻辑
            rolelist = tools.get_indextts2_role()
            self.main.voice_role.clear()
            self.main.current_rolelist = ['clone'] + list(rolelist.keys()) if rolelist else ['clone']
            self.main.voice_role.addItems(self.main.current_rolelist)
        # ^^^^^^ 在这里添加上面的代码块 ^^^^^^

    # 目标语言改变时设置配音角色
    # t 语言显示文字
    def set_voice_role(self, t):

        role = self.main.voice_role.currentText()
        code = translator.get_code(show_text=t)

        if code and code != '-':
            is_allow_lang = tts.is_allow_lang(langcode=code, tts_type=self.main.tts_type.currentIndex())
            if is_allow_lang is not True:
                self.main.show_tips.setText(is_allow_lang)
            else:
                self.main.show_tips.setText('')
            # 判断翻译渠道是否支持翻译到该目标语言
            if translator.is_allow_translate(translate_type=self.main.translate_type.currentIndex(), show_target=t,
                                             win=self.main) is not True:
                return

        if not self.change_by_lang(self.main.tts_type.currentIndex()):
            if role != 'No' and self.main.app_mode in ['biaozhun']:
                self.main.listen_btn.show()
                self.main.listen_btn.setDisabled(False)
            else:
                self.main.listen_btn.hide()
            return

        self.main.listen_btn.hide()
        self.main.voice_role.clear()
        # 未设置目标语言，则清空 edgeTTS角色
        if t == '-':
            self.main.voice_role.addItems(['No'])
            return

        show_rolelist = None
        tts_type = self.main.tts_type.currentIndex()

        # Caso especial para Google Cloud TTS
        if tts_type == tts.GOOGLECLOUD_TTS:
            cred = config.params.get("gcloud_credential_json", "").strip()
            if not cred:
                tools.show_error(
                    "Por favor, configure o arquivo de credenciais do Google Cloud TTS em:\n"
                    "Configurações > Google Cloud TTS > Credenciais"
                )
                self.main.voice_role.clear()
                self.main.current_rolelist = ['No']
                self.main.voice_role.addItems(['No'])
                return

            try:
                roles = _list_gcloud_voices_for(code, cred)
                self.main.voice_role.clear()
                self.main.current_rolelist = roles
                self.main.voice_role.addItems(['No'] + roles)
                return
            except Exception as e:
                config.logger.error(f"Erro ao listar vozes do Google Cloud TTS: {str(e)}")
                self.main.voice_role.addItems(['No'])
                return

        if tts_type == tts.EDGE_TTS:
            show_rolelist = tools.get_edge_rolelist()
        elif tts_type == tts.KOKORO_TTS:
            show_rolelist = tools.get_kokoro_rolelist()
        elif tts_type == tts.AI302_TTS:
            show_rolelist = tools.get_302ai()
        elif tts_type == tts.VOLCENGINE_TTS:
            show_rolelist = tools.get_volcenginetts_rolelist()
        else:
            # AzureTTS
            show_rolelist = tools.get_azure_rolelist()

        if not show_rolelist:
            self.main.target_language.setCurrentText('-')
            tools.show_error(config.transobj['waitrole'])
            return
        try:
            vt = code.split('-')[0] if code != 'yue' else "zh"

            if vt not in show_rolelist:
                self.main.voice_role.addItems(['No'])
                return
            if len(show_rolelist[vt]) < 2:
                self.main.target_language.setCurrentText('-')
                tools.show_error(config.transobj['waitrole'])
                return
            self.main.current_rolelist = show_rolelist[vt]
            self.main.voice_role.addItems(show_rolelist[vt])
        except:
            self.main.voice_role.addItems(['No'])

    # 从本地导入字幕文件
    def import_sub_fun(self):
        fname, _ = QFileDialog.getOpenFileName(self.main, config.transobj['selectmp4'], config.params['last_opendir'],
                                               "Srt files(*.srt *.txt)")
        if fname:
            content = ""
            try:
                content = Path(fname).read_text(encoding='utf-8')
            except:
                content = Path(fname).read_text(encoding='gbk')
            finally:
                if content:
                    self.main.subtitle_area.clear()
                    self.main.subtitle_area.insertPlainText(content.strip())
                else:
                    return tools.show_error(config.transobj['import src error'])

    # 判断是否需要翻译
    def shound_translate(self):
        if self.main.target_language.currentText() == '-' or self.main.source_language.currentText() == '-':
            return False
        if self.main.target_language.currentText() == self.main.source_language.currentText():
            return False
        return True

    # 核对tts选择是否正确
    def check_tts(self):
        if tts.is_input_api(tts_type=self.main.tts_type.currentIndex()) is not True:
            return False
        # 如果没有选择目标语言，但是选择了配音角色，无法配音
        if self.main.target_language.currentText() == '-' and self.main.voice_role.currentText() not in ['No', '', ' ']:
            tools.show_error(config.transobj['wufapeiyin'])
            return False
        return True

    # 核对所选语音识别模式是否正确
    def check_reccogn(self):
        langcode = translator.get_code(show_text=self.main.source_language.currentText())
        recogn_type = self.main.recogn_type.currentIndex()
        model_name = self.main.model_name.currentText()
        res = recognition.is_allow_lang(langcode=langcode, recogn_type=recogn_type, model_name=model_name)
        if res is not True:
            self.main.show_tips.setText(res)
        else:
            self.main.show_tips.setText('')

        # 原始语言是最后一个，即auto自动检查
        if self.main.subtitle_area.toPlainText().strip() and self.main.source_language.currentIndex() == self.main.source_language.count() - 1:
            tools.show_error(
                '已导入字幕情况下，不可再使用检测功能' if config.defaulelang == 'zh' else 'The detection function cannot be used when subtitles have already been imported.',
                False)
            return False

        # 判断是否填写自定义识别 api openai-api识别
        return recognition.is_input_api(recogn_type=recogn_type)

    # 检测开始状态并启动
    def check_start(self):
        self.cfg = {}
        self.is_render = False
        self.edit_subtitle_type = 'edit_subtitle_source'

        if config.current_status == 'ing':
            # 已在执行中，则停止
            self.update_status('stop')
            return

        config.settings = config.parse_init()
        self.main.startbtn.setDisabled(True)
        # 无视频选择 ，也无导入字幕，无法处理
        if len(self.queue_mp4) < 1:
            tools.show_error('必须选择视频文件' if config.defaulelang == 'zh' else 'Video file must be selected', False)
            self.main.startbtn.setDisabled(False)
            return

        if self.check_proxy() is not True:
            self.main.startbtn.setDisabled(False)
            return

        config.task_countdown = int(float(config.settings.get('countdown_sec', 1)))

        # 顶部行
        self.cfg['translate_type'] = self.main.translate_type.currentIndex()
        self.cfg['source_language'] = self.main.source_language.currentText()
        self.cfg['target_language'] = self.main.target_language.currentText()

        # 配音行
        # 配音角色
        self.cfg['tts_type'] = self.main.tts_type.currentIndex()
        self.cfg['voice_role'] = self.main.voice_role.currentText()
        try:
            volume = int(self.main.volume_rate.value())
            pitch = int(self.main.pitch_rate.value())
            self.cfg['volume'] = f'+{volume}%' if volume > 0 else f'{volume}%'
            self.cfg['pitch'] = f'+{pitch}Hz' if pitch > 0 else f'{pitch}Hz'
        except:
            self.cfg['volume'] = '+0%'
            self.cfg['pitch'] = '+0Hz'
        # 语音识别行
        # 识别模式，从faster--openai--googlespeech ...
        self.cfg['recogn_type'] = self.main.recogn_type.currentIndex()
        if self.cfg['recogn_type'] == recognition.Faster_Whisper_XXL and not self.show_xxl_select():
            self.main.startbtn.setDisabled(False)
            return
        self.cfg['model_name'] = self.main.model_name.currentText()
        self.cfg['split_type'] = 'all' if self.main.split_type.currentIndex() < 1 else 'avg'
        # 字幕嵌入类型
        self.cfg['subtitle_type'] = self.main.subtitle_type.currentIndex()

        # 对齐行
        self.cfg['voice_rate'] = self.main.voice_rate.value()
        try:
            voice_rate = int(self.main.voice_rate.value())
            self.cfg['voice_rate'] = f"+{voice_rate}%" if voice_rate >= 0 else f"{voice_rate}%"
        except:
            self.cfg['voice_rate'] = '+0%'
        # 配音自动加速
        self.cfg['voice_autorate'] = self.main.voice_autorate.isChecked()
        self.cfg['video_autorate'] = self.main.video_autorate.isChecked()
        self.cfg['is_separate'] = self.main.is_separate.isChecked()
        if self.cfg['voice_role'] == 'No':
            self.cfg['is_separate'] = False
        self.cfg['cuda'] = self.main.enable_cuda.isChecked()

        # 添加背景音频
        self.cfg['back_audio'] = self.main.back_audio.text().strip()
        self.cfg['only_video'] = self.main.only_video.isChecked()
        self.cfg['clear_cache'] = True if self.main.clear_cache.isChecked() else False

        # 核对识别是否正确
        if self.check_reccogn() is not True:
            self.main.startbtn.setDisabled(False)
            return

        # 如果需要翻译，再判断是否符合翻译规则
        if self.shound_translate() and translator.is_allow_translate(
                translate_type=self.cfg['translate_type'],
                show_target=self.cfg['target_language']) is not True:
            self.main.startbtn.setDisabled(False)
            return

        # 字幕区文字
        txt = self.main.subtitle_area.toPlainText().strip()
        if self.check_txt(txt) is not True:
            self.main.startbtn.setDisabled(False)
            return

        # tts类型
        if self.check_tts() is not True:
            self.main.tts_type.setCurrentIndex(0)
            self.main.startbtn.setDisabled(False)
            return
        # 设置各项模式参数
        self.set_mode()

        # 判断CUDA
        if self.cuda_isok() is not True:
            self.main.startbtn.setDisabled(False)
            return
        # 核对文件路径是否符合规范，防止ffmpeg处理中出错
        if self.url_right() is not True:
            self.main.startbtn.setDisabled(False)
            return

        if self.cfg['target_language'] == '-' and self.cfg['subtitle_type'] > 0:
            self.main.startbtn.setDisabled(False)
            return tools.show_error(
                '必须选择目标语言才可嵌入字幕' if config.defaulelang == 'zh' else 'Target language must be selected to embed subtitles',
                False)
        # 核对是否存在名字相同后缀不同的文件，以及若存在音频则强制为tiqu模式
        if self.check_name() is not True:
            self.main.startbtn.setDisabled(False)
            return
        source_code = translator.get_code(show_text=self.cfg['source_language'])
        target_code = translator.get_code(show_text=self.cfg['target_language'])

        if self.cfg['voice_role'] == 'clone' and self.cfg['tts_type'] == tts.ELEVENLABS_TTS:
            err = ''
            if (source_code != 'auto' and source_code[:2] not in config.ELEVENLABS_CLONE):
                err = "ElevenLabs 不支持所选发音语言的克隆" if config.defaulelang == 'zh' else 'ElevenLabs: Cloning of the selected pronunciation language is not supported'
            elif target_code[:2] not in config.ELEVENLABS_CLONE:
                err = "ElevenLabs 不支持所选目标语言的克隆" if config.defaulelang == 'zh' else 'ElevenLabs: Cloning in the selected target language is not supported'

            if err:
                self.main.startbtn.setDisabled(False)
                return tools.show_error(err, False)

        if self.main.rephrase.isChecked():
            ai_type = config.settings.get('llm_ai_type', 'openai')
            if ai_type == 'openai' and not config.params.get('chatgpt_key'):
                self.main.startbtn.setDisabled(False)
                tools.show_error(config.transobj['llmduanju'], False)
                from videotrans.winform import chatgpt
                chatgpt.openwin()
                return
            if ai_type == 'deepseek' and not config.params.get('deepseek_key'):
                self.main.startbtn.setDisabled(False)
                tools.show_error(config.transobj['llmduanju'], False)
                from videotrans.winform import deepseek
                deepseek.openwin()
                return

        config.line_roles = {}

        if self.main.app_mode in ['biaozhun', 'tiqu']:
            self.cfg['app_mode'] = self.main.app_mode

        self.cfg['remove_noise'] = self.main.remove_noise.isChecked()
        self.cfg["paraformer_spk"] = self.main.show_spk.isChecked()
        config.params.update(self.cfg)
        config.getset_params(config.params)
        self.delete_process()
        # 设为开始
        self.update_status('ing')
        Path(config.TEMP_DIR + '/stop_porcess.txt').unlink(missing_ok=True)

        if self.main.recogn_type.currentIndex() == recognition.FASTER_WHISPER or self.main.app_mode == 'biaozhun':
            config.settings['loop_backaudio'] = self.main.is_loop_bgm.isChecked()
            try:
                config.settings['backaudio_volume'] = float(self.main.bgmvolume.text())
            except:
                pass
            if self.main.split_type.currentIndex() == 1:
                try:
                    config.settings['interval_split'] = int(self.main.equal_split_time.text().strip())
                except:
                    config.settings['interval_split'] = 10

            config.settings["threshold"] = min(
                0.9,
                max(float(self.main.threshold.text().strip()), 0.1)
            )
            config.settings["min_speech_duration_ms"] = int(self.main.min_speech_duration_ms.text())
            config.settings["min_silence_duration_ms"] = int(self.main.min_silence_duration_ms.text())
            config.settings["speech_pad_ms"] = int(self.main.speech_pad_ms.text())
            config.settings["max_speech_duration_s"] = int(self.main.max_speech_duration_s.text())

        config.settings['rephrase'] = self.main.rephrase.isChecked()
        config.settings['cjk_len'] = self.main.cjklinenums.value()
        config.settings['other_len'] = self.main.othlinenums.value()
        config.parse_init(config.settings)

        self._disabled_button(True)
        self.main.startbtn.setDisabled(False)
        self.clear_target_subtitle()

        tools.set_process(text='start', type='create_btns')

    def click_subtitle(self):
        from videotrans.component.set_subtitles_length import SubtitleSettingsDialog
        dialog = SubtitleSettingsDialog(self.main, config.settings.get('cjk_len', 24),
                                        config.settings.get('other_len', 66))
        if dialog.exec():  # OK 按钮被点击时 exec 返回 True
            cjk_value, other_value = dialog.get_values()
            config.settings['cjk_len'] = cjk_value
            config.settings['other_len'] = other_value
            with  open(config.ROOT_DIR + "/videotrans/cfg.json", 'w', encoding='utf-8') as f:
                f.write(json.dumps(config.settings, ensure_ascii=False))

    def click_translate_type(self):
        from videotrans.component.set_threads import SetThreadTransDubb
        dialog = SetThreadTransDubb(name='trans', nums=config.settings.get('trans_thread', 5),
                                    sec=config.settings.get('translation_wait', 0),
                                    ai_nums=config.settings.get('aitrans_thread', 500))
        if dialog.exec():  # OK 按钮被点击时 exec 返回 True
            num, wait, ainums = dialog.get_values()
            config.settings['trans_thread'] = num
            config.settings['aitrans_thread'] = ainums
            config.settings['translation_wait'] = wait
            with  open(config.ROOT_DIR + "/videotrans/cfg.json", 'w', encoding='utf-8') as f:
                f.write(json.dumps(config.settings, ensure_ascii=False))

    def click_tts_type(self):
        from videotrans.component.set_threads import SetThreadTransDubb
        dialog = SetThreadTransDubb(name='dubbing', nums=config.settings.get('dubbing_thread', 5),
                                    sec=config.settings.get('dubbing_wait', 0))
        if dialog.exec():  # OK 按钮被点击时 exec 返回 True
            num, wait, _ = dialog.get_values()
            config.settings['dubbing_thread'] = num
            config.settings['dubbing_wait'] = wait
            with  open(config.ROOT_DIR + "/videotrans/cfg.json", 'w', encoding='utf-8') as f:
                f.write(json.dumps(config.settings, ensure_ascii=False))

    def create_btns(self):
        target_dir = Path(self.main.target_dir if self.main.target_dir else Path(
            self.queue_mp4[0]).parent.as_posix() + "/_video_out").resolve().as_posix()
        self.cfg["target_dir"] = target_dir
        self.main.btn_save_dir.setToolTip(target_dir)
        self.obj_list = []
        # queue_mp4中的名字可能已修改为规范
        new_name = []
        for video_path in self.queue_mp4:
            obj = tools.format_video(video_path, target_dir)
            new_name.append(obj['name'])
            self.obj_list.append(obj)
            self.add_process_btn(target_dir=Path(obj['target_dir']).as_posix(), name=obj['name'], uuid=obj['uuid'])

        self.queue_mp4 = new_name
        txt = self.main.subtitle_area.toPlainText().strip()
        self.cfg.update(
            {'subtitles': txt, 'app_mode': self.main.app_mode}
        )

        # 启动任务
        tools.set_process(text=config.transobj['kaishichuli'], uuid=self.obj_list[0]['uuid'])
        if self.main.app_mode not in ['tiqu'] and len(self.obj_list) == 1:
            self.is_batch = False
            from videotrans.task._only_one import Worker
            task = Worker(
                parent=self.main,
                app_mode=self.main.app_mode,
                obj_list=self.obj_list,
                txt=txt,
                cfg=self.cfg
            )
            task.uito.connect(self.update_data)
            task.start()
            if self.cfg['target_language'] != '-' and self.cfg['target_language'] != self.cfg['source_language']:
                if not self.main.isMaximized():
                    self.main.showMaximized()
            return

        self.is_batch = True
        from videotrans.task._mult_video import MultVideo
        MultVideo(parent=self.main, cfg=self.cfg, obj_list=self.obj_list).start()

    # 启动时禁用相关模式按钮，停止时重新启用
    def _disabled_button(self, disabled=True):
        for k, v in self.main.moshis.items():
            if k != self.main.app_mode:
                # 非当前模式
                v.setDisabled(disabled)
                v.setChecked(False)
            else:
                v.setDisabled(False)
                v.setChecked(True)

    # 任务end结束或暂停时，清空队列
    # 先不清空 stoped_uuid_set 标志，用于背景分离任务稍后结束
    def _clear_task(self):
        for v in self.obj_list:
            try:
                if v['uuid'] in config.uuid_logs_queue:
                    del config.uuid_logs_queue[v['uuid']]
            except:
                pass

    # 添加进度条
    def add_process_btn(self, *, target_dir: str = None, name: str = None, uuid=None):
        from videotrans.component.progressbar import ClickableProgressBar
        clickable_progress_bar = ClickableProgressBar(self)
        clickable_progress_bar.progress_bar.setValue(0)  # 设置当前进度值
        clickable_progress_bar.setText(config.transobj["waitforstart"])
        clickable_progress_bar.setMinimumSize(500, 50)
        clickable_progress_bar.setToolTip(config.transobj['mubiao'])
        # # 将按钮添加到布局中
        if self.cfg['app_mode'] == 'tiqu' and self.cfg.get('copysrt_rawvideo'):
            target_dir = Path(name).parent.as_posix()
        else:
            target_dir = Path(target_dir).parent.as_posix() if self.cfg.get('only_video') else target_dir
        clickable_progress_bar.setTarget(
            target_dir=target_dir,
            name=name
        )
        clickable_progress_bar.setCursor(Qt.PointingHandCursor)
        self.main.processlayout.addWidget(clickable_progress_bar)
        if uuid:
            self.processbtns[uuid] = clickable_progress_bar

    # 设置按钮上的日志信息
    def set_process_btn_text(self, d):
        if isinstance(d, str):
            d = json.loads(d)
        text, uuid, _type = d['text'], d.get('uuid', ''), d.get('type', 'logs')
        if not uuid or uuid not in self.processbtns:
            return
        if _type == 'set_precent' and self.processbtns[uuid].precent < 100:
            t, precent = text.split('???')
            precent = int(float(precent) * 100) / 100
            self.processbtns[uuid].setPrecent(precent)
            self.processbtns[uuid].setText(f'{config.transobj["running"].replace("..", "")} {t}')
        elif _type == 'logs' and self.processbtns[uuid].precent < 100:
            self.processbtns[uuid].setText(text)
        elif _type == 'succeed':
            self.processbtns[uuid].setEnd()
            if self.processbtns[uuid].name in self.queue_mp4:
                self.queue_mp4.remove(self.processbtns[uuid].name)
        elif _type == 'error':
            self.processbtns[uuid].setError(text)
            self.processbtns[uuid].progress_bar.setStyleSheet('color:#ff0000')
            self.processbtns[uuid].setCursor(Qt.PointingHandCursor)

    # 更新执行状态
    def update_status(self, type):
        config.current_status = type
        self.main.continue_compos.hide()
        self.main.stop_djs.hide()
        if type == 'ing':
            # 重设为开始状态
            self.disabled_widget(True)
            self.main.startbtn.setText(config.transobj["starting..."])
            return
        with open(config.TEMP_DIR + '/stop_porcess.txt', 'w', encoding='utf-8') as f:
            f.write('stop')
        # stop 停止，end=结束
        self.main.subtitle_area.clear()
        self.main.startbtn.setText(config.transobj[type])

        # 删除本次任务的所有进度队列
        self._clear_task()
        # 启用
        self.disabled_widget(False)
        # 启用相关模式
        self._disabled_button(False)
        if type == 'end':
            self.main.subtitle_area.clear()

            for prb in self.processbtns.values():
                prb.setEnd()
            # 成功完成
            # 关机
            if self.main.shutdown.isChecked():
                try:
                    tools.shutdown_system()
                except Exception as e:
                    tools.show_error(config.transobj['shutdownerror'] + str(e))
            self.main.target_dir = None
            self.main.btn_save_dir.setToolTip('')
        else:
            # 任务队列中设为停止并删除队列，防止后续到来的日志继续显示
            for it in self.obj_list:
                # 按钮设为暂停
                if it['uuid'] in self.processbtns:
                    self.processbtns[it['uuid']].setPause()
            self.set_djs_timeout()
            self.main.stop_djs.hide()
            self.main.continue_compos.hide()
        for it in self.obj_list:
            if it['uuid'] in config.uuid_logs_queue:
                del config.uuid_logs_queue[it['uuid']]
        if self.main.app_mode == 'tiqu':
            self.set_tiquzimu()
        self._reset()

    # 更新 UI
    def update_data(self, json_data):
        d = json.loads(json_data) if isinstance(json_data, str) else json_data
        if d['type'] in ['logs', 'error', 'succeed', 'set_precent']:
            self.set_process_btn_text(d)
            if d['type'] in ['error', 'succeed']:
                if d.get('uuid'):
                    config.stoped_uuid_set.add(d['uuid'])

                self.edit_subtitle_type = 'edit_subtitle_source'
                self.wait_subtitle = None
                if not self.is_batch:
                    self.clear_target_subtitle()
        elif d['type'] == 'create_btns':
            self.create_btns()
        # 任务开始执行，初始化按钮等
        elif d['type'] == 'shitingerror':
            tools.show_error(d['text'])
        elif d['type'] in ['end']:
            # 任务全部完成时出现 end
            self.update_status(d['type'])
        # 一行一行插入字幕到字幕编辑区
        elif d['type'] == "subtitle" and config.current_status == 'ing' and (
                self.is_batch or config.task_countdown <= 0):
            if self.is_batch or (not self.is_batch and self.edit_subtitle_type == 'edit_subtitle_source'):
                self.main.subtitle_area.moveCursor(QTextCursor.End)
                self.main.subtitle_area.insertPlainText(d['text'])
        elif d['type'] == 'edit_subtitle_source' or d['type'] == 'edit_subtitle_target':
            self.wait_subtitle = d['text']
            self.edit_subtitle_type = d['type']
            # 显示出合成按钮,等待编辑字幕,允许修改字幕
            if d['type'] == 'edit_subtitle_source':
                self.main.subtitle_area.setReadOnly(False)
                self.main.subtitle_area.setFocus()
        elif d['type'] == 'disabled_edit':
            # 禁止修改字幕
            self.main.subtitle_area.setReadOnly(True)
        elif d['type'] == 'allow_edit':
            # 允许修改字幕
            if self.edit_subtitle_type == 'edit_subtitle_source':
                self.main.subtitle_area.setReadOnly(False)
                self.main.subtitle_area.setFocus()
        elif d['type'] == 'replace_subtitle':
            # 完全替换字幕区
            if self.is_batch or (not self.is_batch and self.edit_subtitle_type == 'edit_subtitle_source'):
                self.main.subtitle_area.clear()
                self.main.subtitle_area.insertPlainText(d['text'])
            elif not self.is_batch and self.edit_subtitle_type == 'edit_subtitle_target' and not self.is_render:
                self.is_render = True
                self.show_target_edit(d['text'])
        elif d['type'] == 'timeout_djs':
            self.set_djs_timeout()
        elif d['type'] == 'show_djs':
            self.main.continue_compos.show()
            self.main.continue_compos.setDisabled(False)
            self.main.continue_compos.setText(
                '继续下一步操作' if config.defaulelang == 'zh' else 'Continue next step')
            self.main.stop_djs.show()
            self.main.timeout_tips.setText(d['text'])
            if self.edit_subtitle_type == 'edit_subtitle_source':
                self.main.subtitle_area.setReadOnly(False)
        elif d['type'] == 'check_soft_update':
            self.update_tips(d['text'])
        elif d['type'] == 'set_clone_role' and self.main.tts_type.currentText() == 'clone-voice':
            if config.current_status == 'ing':
                return
            current = self.main.voice_role.currentText()
            self.main.voice_role.clear()
            self.main.voice_role.addItems(config.params["clone_voicelist"])
            self.main.voice_role.setCurrentText(current)
        elif d['type'] == 'ffmpeg':
            self.main.startbtn.setText(d['text'])
            self.main.startbtn.setDisabled(True)
            self.main.startbtn.setStyleSheet("""color:#ff0000""")
        elif d['type'] == 'refreshtts':
            currentIndex = self.main.tts_type.currentIndex()
            if currentIndex in [tts.GPTSOVITS_TTS, tts.COSYVOICE_TTS, tts.FISHTTS, tts.CHATTTS, tts.CLONE_VOICE_TTS,
                                tts.F5_TTS, tts.OPENAI_TTS, tts.QWEN_TTS, tts.GEMINI_TTS, tts.CHATTERBOX_TTS]:
                self.main.tts_type.setCurrentIndex(0)
                self.main.tts_type.setCurrentIndex(currentIndex)
        elif d['type'] == 'refreshmodel_list':
            config.WHISPER_MODEL_LIST = re.split(r'[,，]', config.settings['model_list'])
            if self.main.recogn_type.currentIndex() in [recognition.FASTER_WHISPER, recognition.OPENAI_WHISPER]:
                current_model_name = self.main.model_name.currentText()
                self.main.model_name.clear()
                self.main.model_name.addItems(config.WHISPER_MODEL_LIST)
                self.main.model_name.setCurrentText(current_model_name)

    # update subtitle 手动 点解了 立即合成按钮，或者倒计时结束超时自动执行
    def update_subtitle(self):
        self.main.stop_djs.hide()
        self.main.continue_compos.setDisabled(True)
        # 是单个视频执行时
        if self.is_batch or not self.wait_subtitle:
            return
        if self.edit_subtitle_type == 'edit_subtitle_source':
            txt = self.main.subtitle_area.toPlainText().strip()
        # 目标字幕区
        else:
            txt = self.get_target_subtitle()
        if not txt:
            return
        with Path(self.wait_subtitle).open('w', encoding='utf-8') as f:
            f.write(txt)
        return True

    def target_lang_change(self, t):
        if not t or t == '-':
            self.main.voice_role.clear()
            self.main.voice_role.addItems(['No'])
            return

        tts_type = self.main.tts_type.currentIndex()
        code = translator.get_code(show_text=t)
        if not code:
            self.main.voice_role.clear()
            self.main.voice_role.addItems(['No'])
            return

        # Caso especial para Google Cloud TTS
        if tts_type == tts.GOOGLECLOUD_TTS:
            cred = config.params.get("gcloud_credential_json", "").strip()
            if not cred:
                tools.show_error(
                    "Por favor, configure o arquivo de credenciais do Google Cloud TTS em:\n"
                    "Configurações > Google Cloud TTS > Credenciais"
                )
                self.main.voice_role.clear()
                self.main.current_rolelist = ['No']
                self.main.voice_role.addItems(['No'])
                return

            try:
                roles = _list_gcloud_voices_for(code, cred)
                self.main.voice_role.clear()
                self.main.current_rolelist = roles

                if not roles:
                    tools.show_error(
                        f"Não foi possível encontrar vozes para o idioma {t}.\n\n"
                        "Verifique:\n"
                        "1. Se o arquivo de credenciais está correto\n"
                        "2. Se as credenciais têm permissão para acessar a API\n"
                        "3. Se o idioma selecionado é suportado\n\n"
                        "Consulte os logs para mais detalhes."
                    )
                    self.main.voice_role.addItems(['No'])
                else:
                    self.main.voice_role.addItems(['No'] + roles)

            except Exception as e:
                config.logger.error(f"Erro ao listar vozes do Google Cloud TTS: {str(e)}")
                tools.show_error(f"Erro ao listar vozes do Google Cloud TTS:\n{str(e)}\n\n"
                                 "Verifique os logs para mais detalhes."
                                 )
                self.main.voice_role.clear()
                self.main.current_rolelist = ['No']
                self.main.voice_role.addItems(['No'])
            return

        if tts_type == tts.EDGE_TTS:
            show_rolelist = tools.get_edge_rolelist()
        elif tts_type == tts.KOKORO_TTS:
            show_rolelist = tools.get_kokoro_rolelist()
        elif tts_type == tts.AI302_TTS:
            show_rolelist = tools.get_302ai()
        elif tts_type == tts.VOLCENGINE_TTS:
            show_rolelist = tools.get_volcenginetts_rolelist()
        else:
            # AzureTTS
            show_rolelist = tools.get_azure_rolelist()

        if not show_rolelist:
            self.main.target_language.setCurrentText('-')
            tools.show_error(config.transobj['waitrole'])
            return
        try:
            vt = code.split('-')[0]
            if vt not in show_rolelist:
                self.main.voice_role.addItems(['No'])
                return
            if len(show_rolelist[vt]) < 2:
                self.main.target_language.setCurrentText('-')
                tools.show_error(config.transobj['waitrole'])
                return
            self.main.current_rolelist = show_rolelist[vt]
            self.main.voice_role.addItems(show_rolelist[vt])
        except:
            self.main.voice_role.addItems(['No'])

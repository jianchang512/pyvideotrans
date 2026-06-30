import pytest

from PySide6.QtWidgets import QMainWindow, QApplication

app = QApplication.instance() or QApplication([])

from videotrans.ui.en import Ui_MainWindow


class _TestWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)


def test_import():
    from videotrans.ui.en import Ui_MainWindow
    assert Ui_MainWindow is not None


def test_has_setup_methods():
    from videotrans.ui.en import Ui_MainWindow
    ui = Ui_MainWindow()
    assert callable(getattr(ui, 'setupUi', None))
    assert callable(getattr(ui, '_set_Ui_Text', None))


def test_setupUi_creates_key_widgets():
    win = _TestWindow()

    expected_widgets = [
        'centralwidget', 'splitter', 'layoutWidget', 'verticalLayout_3',
        'btn_get_video', 'source_mp4', 'clear_cache', 'select_file_type',
        'btn_save_dir', 'copysrt_rawvideo', 'only_out_mp4', 'shutdown',
        'reglabel', 'recogn_type', 'model_name_help', 'model_name',
        'rephrase', 'remove_noise', 'recogn2pass',
        'label_9', 'translate_type', 'label_2', 'source_language',
        'label_3', 'target_language', 'aisendsrt', 'glossary',
        'tts_text', 'tts_type', 'label_4', 'voice_role', 'listen_btn',
        'align_btn', 'voice_autorate', 'video_autorate',
        'remove_silent_mid', 'align_sub_audio', 'subtitle_type',
        'set_adv_status', 'label', 'proxy', 'output_srt_label', 'output_srt',
        'is_separate', 'embed_bgm', 'addbackbtn', 'back_audio',
        'is_loop_bgm', 'bgmvolume_label', 'bgmvolume', 'set_ass',
        'enable_diariz', 'fix_punc', 'nums_diariz',
        'label_6', 'voice_rate', 'volume_label', 'volume_rate',
        'pitch_label', 'pitch_rate',
        'dubb_thread_layout', 'adv_layout_outer', 'advcontainer',
        'show_tips', 'output_dir',
        'enable_cuda', 'startbtn', 'retrybtn',
        'scroll_area', 'processlayout',
        'subtitle_layout', 'source_area_layout', 'import_sub',
        'target_subtitle_area', 'statusBar', 'menuBar',
        'menu_Key', 'menu_TTS', 'menu_RECOGN', 'menu', 'menu_H',
        'toolBar',
    ]
    for name in expected_widgets:
        assert hasattr(win, name), f"Missing widget: {name}"


def test_setupUi_creates_actions():
    win = _TestWindow()

    expected_actions = [
        'actionbaidu_key', 'actionali_key', 'actionchatgpt_key',
        'actionzhipuai_key', 'actionsiliconflow_key', 'actiondeepseek_key',
        'actionminimax_key', 'actionqwenmt_key', 'actionopenrouter_key',
        'actionlibretranslate_key', 'actionopenaitts_key', 'actionxaitts_key',
        'actionxiaomi_key', 'actionqwentts_key', 'actionopenairecognapi_key',
        'actionparakeet_key', 'actionai302_key', 'actionlocalllm_key',
        'actionzijiehuoshan_key', 'actiondeepL_key', 'actionazure_tts',
        'action_ffmpeg', 'action_git', 'action_issue',
        'actiondeepLX_address', 'actionclone_address', 'actionkokoro_address',
        'actionchattts_address', 'actiontts_api', 'actionminimaxi_api',
        'actiontrans_api', 'actionrecognapi', 'actionsttapi',
        'actionwhisperx', 'actiondeepgram', 'actionxxl', 'actioncpp',
        'actionzijierecognmodel_api', 'actiontts_gptsovits',
        'actiontts_chatterbox', 'actiontts_cosyvoice', 'actiontts_omnivoice',
        'actiontts_qwenttslocal', 'actiontts_fishtts', 'actiontts_f5tts',
        'actiontts_refaudio', 'actiontts_doubao2',
        'action_website', 'action_blog', 'action_discord',
        'action_gtrans', 'action_cuda', 'action_online',
        'actiontencent_key', 'action_about',
        'action_biaozhun', 'action_yuyinshibie', 'action_yuyinhecheng',
        'action_tiquzimu', 'action_yingyinhebing', 'action_clipvideo',
        'action_realtime_stt', 'action_textmatching', 'action_hun',
        'action_fanyi', 'action_hebingsrt', 'action_clearcache',
        'action_set_proxy', 'actionazure_key', 'actiongemini_key',
        'actioncamb_key', 'actionElevenlabs_key', 'actionwatermark',
        'actionsepar', 'actionsetini', 'actionvideoandaudio',
        'actionvideoandsrt', 'actionformatcover', 'actionsubtitlescover',
        'actionsrtmultirole', 'action_yinshipinfenli',
    ]
    for name in expected_actions:
        assert hasattr(win, name), f"Missing action: {name}"


def test_setUiText_sets_labels():
    win = _TestWindow()

    assert win.btn_get_video.text() != ""
    assert win.btn_save_dir.text() != ""
    assert win.startbtn.text() != ""
    assert win.label_9.text() != ""
    assert win.tts_text.text() != ""


def test_checkable_actions():
    win = _TestWindow()

    assert win.action_biaozhun.isCheckable()
    assert win.action_biaozhun.isChecked()
    assert win.action_tiquzimu.isCheckable()


def test_setup_rows_module():
    from videotrans.ui._setup_rows import (
        _create_file_row, _create_asr_row, _create_translation_row,
        _create_tts_row, _create_alignment_row,
    )
    assert callable(_create_file_row)
    assert callable(_create_asr_row)
    assert callable(_create_translation_row)
    assert callable(_create_tts_row)
    assert callable(_create_alignment_row)


def test_setup_menus_module():
    from videotrans.ui._setup_menus import (
        _setup_actions_and_menus, _make_action, _fill_menu,
    )
    assert callable(_setup_actions_and_menus)
    assert callable(_make_action)
    assert callable(_fill_menu)

import pytest
from videotrans.task.trans_create import TransCreate


EXPECTED_METHODS = [
    # PrepareMixin
    'prepare',
    '_split_novoice_byraw',
    '_split_audio_byraw',
    # RecognMixin
    'recogn',
    'recogn2pass',
    '_recogn_succeed',
    '_create_ref_from_vocal',
    # DiarizMixin
    'diariz',
    # TranslateMixin
    'trans',
    # DubbingMixin
    'dubbing',
    '_tts',
    # AlignMixin
    'align',
    # AudioMixin
    '_back_music',
    '_separate',
    # SubtitleMixin
    '_process_subtitles',
    '_get_join_flag',
    # AssembleMixin
    'assembling',
    'task_done',
    '_join_video_audio_srt',
    '_get_origin_audio',
    '_hebing_pro',
    '_get_hard_cfg',
    '_subprocess',
    '_video_extend',
    # BaseTask / BaseCon
    'set_end',
    '_exit',
    'signal',
    '_unlink_size0',
    '_save_srt_target',
    'check_target_sub',
    '_new_process',
    'convert_to_wav',
]


def test_all_methods_exist():
    for method_name in EXPECTED_METHODS:
        assert hasattr(TransCreate, method_name), f"TransCreate missing method: {method_name}"


def test_class_hierarchy():
    from videotrans.task._base import BaseTask
    from videotrans.task._stage_prepare import PrepareMixin
    from videotrans.task._stage_recogn import RecognMixin
    from videotrans.task._stage_diariz import DiarizMixin
    from videotrans.task._stage_translate import TranslateMixin
    from videotrans.task._stage_dubbing import DubbingMixin
    from videotrans.task._stage_align import AlignMixin
    from videotrans.task._stage_audio import AudioMixin
    from videotrans.task._stage_subtitle import SubtitleMixin
    from videotrans.task._stage_assemble import AssembleMixin

    assert issubclass(TransCreate, BaseTask)
    assert issubclass(TransCreate, PrepareMixin)
    assert issubclass(TransCreate, RecognMixin)
    assert issubclass(TransCreate, DiarizMixin)
    assert issubclass(TransCreate, TranslateMixin)
    assert issubclass(TransCreate, DubbingMixin)
    assert issubclass(TransCreate, AlignMixin)
    assert issubclass(TransCreate, AudioMixin)
    assert issubclass(TransCreate, SubtitleMixin)
    assert issubclass(TransCreate, AssembleMixin)

from videotrans import tts


# The main window and the other dubbing windows use the currentIndex() of the
# TTS combobox, which TTS_NAME_LIST fills, as tts_type. So the channel ids must
# be exactly the positions 0, 1, 2, ... in that list, with no gap or duplicate.
def test_tts_channel_ids_are_their_positions_in_the_list():
    ids = list(tts.ID_NAME_DICT)
    assert ids == list(range(len(ids)))
    assert tts.TTS_NAME_LIST == [
        provider.name for provider in tts.ID_NAME_DICT.values()
    ]


def test_supertonic_and_bailian_keep_their_own_channels():
    assert tts.BAILIAN_TTS != tts.Supertonic_TTS
    assert tts.ID_NAME_DICT[tts.Supertonic_TTS].name.startswith("Supertonic3")
    assert tts.ID_NAME_DICT[tts.BAILIAN_TTS] is not tts.ID_NAME_DICT[tts.Supertonic_TTS]

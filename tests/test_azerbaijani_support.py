from videotrans.configure._languages_dict import LANG_CODE
from videotrans.util.help_role import get_edge_rolelist


def test_azerbaijani_is_available_in_main_language_codes():
    assert "az" in LANG_CODE
    assert LANG_CODE["az"] == [
        "az",
        "aze",
        "No",
        "No",
        "No",
        "No",
        "az",
        "Azerbaijani",
        "No",
        "Azerbaijani",
        "az",
    ]


def test_azerbaijani_edge_voices_are_exposed():
    roles = get_edge_rolelist()["az"]
    assert roles["Banu(Female/AZ)"] == "az-AZ-BanuNeural"
    assert roles["Babek(Male/AZ)"] == "az-AZ-BabekNeural"

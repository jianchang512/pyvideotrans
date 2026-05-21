"""
Tests for videotrans/task/job.py helper functions.
These are pure functions that don't require Qt or heavy deps.
"""

from videotrans.task.job import _get_type_name, get_recogn_type, get_tanslate_type, get_tts_type


class TestGetTypeName:
    def test_valid_index(self):
        name_list = ["A", "B", "C"]
        assert _get_type_name(0, name_list) == "A"
        assert _get_type_name(1, name_list) == "B"
        assert _get_type_name(2, name_list) == "C"

    def test_none_index_returns_dash(self):
        assert _get_type_name(None, ["A", "B"]) == "-"

    def test_out_of_range_returns_dash(self):
        assert _get_type_name(5, ["A", "B"]) == "-"

    def test_negative_index_returns_last_element(self):
        # Python list[-1] returns the last element, not IndexError
        assert _get_type_name(-1, ["A", "B"]) == "B"


class TestGetRecognType:
    def test_returns_dash_for_none(self):
        assert get_recogn_type(None) == "-"

    def test_returns_name_for_valid_index(self):
        result = get_recogn_type(0)
        assert result != "-"
        assert isinstance(result, str)

    def test_index_too_large(self):
        assert get_recogn_type(999) == "-"


class TestGetTranslateType:
    def test_returns_dash_for_none(self):
        assert get_tanslate_type(None) == "-"

    def test_returns_name_for_valid_index(self):
        result = get_tanslate_type(0)
        assert result != "-"
        assert isinstance(result, str)


class TestGetTTSType:
    def test_returns_dash_for_none(self):
        assert get_tts_type(None) == "-"

    def test_returns_name_for_valid_index(self):
        result = get_tts_type(0)
        assert result != "-"
        assert isinstance(result, str)

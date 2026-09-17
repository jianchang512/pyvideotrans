from videotrans.util.help_srt import format_time, srt_str_to_listdict


def test_short_fraction_is_read_as_a_decimal():
    srt = "1\n00:00:01,5 --> 00:00:02,25\nHello\n"
    item = srt_str_to_listdict(srt)[0]
    assert item["start_time"] == 1500
    assert item["end_time"] == 2250
    assert item["time"] == "00:00:01,500 --> 00:00:02,250"


def test_long_fraction_is_cut_to_milliseconds():
    item = srt_str_to_listdict("1\n00:00:01.5004 --> 00:00:02.000\nHello\n")[0]
    assert item["start_time"] == 1500


def test_three_digit_fraction_is_unchanged():
    item = srt_str_to_listdict("1\n00:00:01,005 --> 00:00:02,010\nHello\n")[0]
    assert (item["start_time"], item["end_time"]) == (1005, 2010)


def test_format_time_pads_a_short_fraction():
    assert format_time("00:00:01,5") == "00:00:01,500"
    assert format_time("00:00:01.25", ".") == "00:00:01.250"
    assert format_time("00:00:01,005") == "00:00:01,005"

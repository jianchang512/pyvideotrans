from videotrans.process._stt_utils import _resegment2


def _words(pairs):
    t = 0.0
    words = []
    for text, dur, gap in pairs:
        words.append({"word": text, "start": t, "end": t + dur})
        t += dur + gap
    return [{"text": "x", "start": words[0]["start"], "end": words[-1]["end"], "words": words}]


def _texts(result):
    return [item["text"] for item in result]


def test_a_decimal_split_across_words_stays_one_cue():
    # "3." then "14", 50 ms apart: the period is the decimal point, not a sentence end
    texts = _words([
        ("It", 0.2, 0.05),
        ("costs", 0.3, 0.05),
        ("3.", 0.3, 0.05),
        ("14", 0.3, 0.05),
        ("dollars.", 0.4, 0.0),
    ])
    result = _resegment2(texts, "en", 6000, 3000)
    assert _texts(result) == ["It costs 3. 14 dollars."]


def test_a_short_gap_inside_a_decimal_does_not_split():
    texts = _words([
        ("about", 0.3, 0.05),
        ("3.", 0.2, 0.15),
        ("14", 0.3, 0.0),
    ])
    result = _resegment2(texts, "en", 6000, 3000)
    assert len(result) == 1
    assert "3." in result[0]["text"] and "14" in result[0]["text"]


def test_a_decimal_does_not_override_the_maximum_duration():
    texts = _words([
        ("3.", 0.9, 0.05),
        ("14", 0.2, 0.0),
    ])
    result = _resegment2(texts, "en", 500, 200)
    assert _texts(result) == ["3.", "14"]


def test_a_real_sentence_end_still_splits():
    texts = _words([
        ("Hello.", 0.4, 0.05),
        ("World", 0.4, 0.0),
    ])
    result = _resegment2(texts, "en", 6000, 3000)
    assert _texts(result) == ["Hello.", "World"]

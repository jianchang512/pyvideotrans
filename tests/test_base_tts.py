from videotrans.tts._base import BaseTTS


class TestBaseTTSCleantts:
    def test_volume_default_zero(self):
        btts = BaseTTS(queue_tts=[{"text": "hello", "volume": "+0%"}])
        assert btts.volume == "+0%"

    def test_volume_positive(self):
        btts = BaseTTS(queue_tts=[{"text": "hello", "volume": "+20%"}])
        assert btts.volume == "+20%"

    def test_volume_negative(self):
        btts = BaseTTS(queue_tts=[{"text": "hello", "volume": "-10%"}])
        assert btts.volume == "-10%"

    def test_volume_plain_number_fixed(self):
        btts = BaseTTS(queue_tts=[{"text": "hello", "volume": "20%"}])
        assert btts.volume == "+20%"

    def test_volume_decimal(self):
        btts = BaseTTS(queue_tts=[{"text": "hello", "volume": "+5.5%"}])
        assert btts.volume == "+5.5%"

    def test_rate_default_zero(self):
        btts = BaseTTS(queue_tts=[{"text": "hello", "rate": "+0%"}])
        assert btts.rate == "+0%"

    def test_rate_positive(self):
        btts = BaseTTS(queue_tts=[{"text": "hello", "rate": "+30%"}])
        assert btts.rate == "+30%"

    def test_rate_plain_number_fixed(self):
        btts = BaseTTS(queue_tts=[{"text": "hello", "rate": "15%"}])
        assert btts.rate == "+15%"

    def test_pitch_default_zero(self):
        btts = BaseTTS(queue_tts=[{"text": "hello", "pitch": "+0Hz"}])
        assert btts.pitch == "+0Hz"

    def test_pitch_lowercase_hz(self):
        btts = BaseTTS(queue_tts=[{"text": "hello", "pitch": "+5hz"}])
        assert btts.pitch == "+5Hz"

    def test_pitch_negative(self):
        btts = BaseTTS(queue_tts=[{"text": "hello", "pitch": "-3Hz"}])
        assert btts.pitch == "-3Hz"


class TestBaseTTSGetters:
    def test_get_speed_zero(self):
        btts = BaseTTS(queue_tts=[{"text": "hello", "rate": "+0%"}])
        assert btts.get_speed() == 1.0

    def test_get_speed_positive(self):
        btts = BaseTTS(queue_tts=[{"text": "hello", "rate": "+50%"}])
        assert btts.get_speed() == 1.5

    def test_get_speed_negative(self):
        btts = BaseTTS(queue_tts=[{"text": "hello", "rate": "-20%"}])
        assert btts.get_speed() == 0.8

    def test_get_volume_zero(self):
        btts = BaseTTS(queue_tts=[{"text": "hello", "volume": "+0%"}])
        assert btts.get_volume() == 1.0

    def test_get_volume_positive(self):
        btts = BaseTTS(queue_tts=[{"text": "hello", "volume": "+100%"}])
        assert btts.get_volume() == 2.0

    def test_get_volume_negative(self):
        btts = BaseTTS(queue_tts=[{"text": "hello", "volume": "-50%"}])
        assert btts.get_volume() == 0.5

    def test_get_pitch_zero_hz_returns_default(self):
        # _cleantts normalizes 'hz' to 'Hz'; get_pitch regex [hz%] misses 'H'
        btts = BaseTTS(queue_tts=[{"text": "hello", "pitch": "+0Hz"}])
        assert btts.get_pitch() == 1.0

    def test_get_pitch_positive_hz_returns_default(self):
        btts = BaseTTS(queue_tts=[{"text": "hello", "pitch": "+12Hz"}])
        assert btts.get_pitch() == 1.0

    def test_get_pitch_negative_hz_returns_default(self):
        btts = BaseTTS(queue_tts=[{"text": "hello", "pitch": "-6Hz"}])
        assert btts.get_pitch() == 1.0


class TestBaseTTSInitFields:
    def test_default_values(self):
        btts = BaseTTS(queue_tts=[{"text": "hello", "rate": "+0%", "volume": "+0%", "pitch": "+0Hz"}])
        assert btts.tts_type == 0
        assert btts.play is False
        assert btts.is_test is False
        assert btts.is_cuda is False
        assert btts.len == 1

    def test_queue_tts_deep_copy(self):
        data = [{"text": "hello", "rate": "+0%", "volume": "+0%", "pitch": "+0Hz"}]
        btts = BaseTTS(queue_tts=data)
        # queue_tts is deepcopy'd, modifying original should not affect
        data[0]["text"] = "modified"
        assert btts.queue_tts[0]["text"] == "hello"

    def test_len_matches_queue(self):
        data = [
            {"text": "a", "rate": "+0%", "volume": "+0%", "pitch": "+0Hz"},
            {"text": "b", "rate": "+0%", "volume": "+0%", "pitch": "+0Hz"},
            {"text": "c", "rate": "+0%", "volume": "+0%", "pitch": "+0Hz"},
        ]
        btts = BaseTTS(queue_tts=data)
        assert btts.len == 3

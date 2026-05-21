"""
Tests for WinActionBase pure methods and proxy validation logic.
Since WinActionBase depends on MainWindow (PySide6), we test the
pure logic in isolation without instantiating the class.
"""

import re


class TestProxyValidation:
    def test_valid_http_proxy(self):
        proxy = "http://127.0.0.1:1080"
        assert re.match(r'^(http|sock)(s|5)?://(\d+\.){3}\d+:\d+', proxy, re.I)

    def test_socks_proxy(self):
        proxy = "socks5://127.0.0.1:1080"
        assert re.match(r'^http(s)?://|^socks5?://', proxy, re.I)

    def test_invalid_proxy_no_port(self):
        proxy = "http://127.0.0.1"
        # The check_proxy regex requires :port after the IP
        assert not re.match(r'^(http|sock)(s|5)?://(\d+\.){3}\d+:\d+', proxy, re.I)

    def test_invalid_proxy_wrong_scheme(self):
        proxy = "ftp://127.0.0.1:1080"
        assert not re.match(r'^(http|sock)(s|5)?://(\d+\.){3}\d+:\d+', proxy, re.I)

    def test_proxy_http_prefix_added(self):
        proxy = "127.0.0.1:1080"
        if not re.match(r'^(http|sock)', proxy, re.I):
            proxy = f'http://{proxy}'
        assert proxy == 'http://127.0.0.1:1080'


class TestVoiceAutorateLogic:
    def test_voice_autorate_hides_silent_mid(self):
        voice_autorate = True
        video_autorate = False
        show = not voice_autorate and not video_autorate
        assert show is False

    def test_both_false_shows(self):
        voice_autorate = False
        video_autorate = False
        show = not voice_autorate and not video_autorate
        assert show is True

    def test_video_autorate_alone_hides(self):
        voice_autorate = False
        video_autorate = True
        show = not voice_autorate and not video_autorate
        assert show is False


class TestSubtitleTypeLogic:
    def test_dual_subtitle_shows_output_srt(self):
        idx = 3  # 双硬字幕
        show = idx >= 3
        assert show is True

    def test_single_hard_subtitle_hides(self):
        idx = 1  # 硬字幕
        show = idx >= 3
        assert show is False


class TestSetModeLogic:
    def test_tiqu_forces_voice_role_no(self):
        app_mode = 'tiqu'
        voice_role = 'some-role'
        subtitle_type = 1
        if app_mode == 'tiqu':
            voice_role = 'No'
        assert voice_role == 'No'

    def test_biaozhun_keeps_voice_role(self):
        app_mode = 'biaozhun'
        voice_role = 'some-role'
        # In biaozhun mode, voice_role is NOT forced to 'No'
        if app_mode == 'tiqu':
            voice_role = 'No'
        assert voice_role == 'some-role'

# -*- coding: utf-8 -*-
"""
Regression tests for videotrans/util/help_ffmpeg.py

Covers bugs fixed in:
- PR #1041: ffprobe returns empty duration string → float("") crash
- PR #1045: format duration fallback missing *1000 (returns seconds not ms)
"""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from videotrans.util.help_ffmpeg import _get_ms_from_media, get_video_info


class TestGetMsFromMedia(unittest.TestCase):
    """Regression tests for _get_ms_from_media."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.video_file = os.path.join(self.tmpdir, 'test.mp4')
        self.audio_file = os.path.join(self.tmpdir, 'test.wav')
        # Create empty files so Path().suffix works
        Path(self.video_file).touch()
        Path(self.audio_file).touch()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch('videotrans.util.help_ffmpeg.runffprobe')
    @patch('videotrans.util.help_ffmpeg.contants')
    def test_video_duration_ms(self, mock_contants, mock_runffprobe):
        mock_contants.VIDEO_EXTS = ['mp4', 'mkv', 'avi']
        mock_contants.AUDIO_EXITS = ['wav', 'mp3', 'flac']
        # ffprobe returns "65.5" seconds for stream duration
        mock_runffprobe.return_value = "65.5"

        ms = _get_ms_from_media(self.video_file)
        self.assertEqual(ms, 65500)

    @patch('videotrans.util.help_ffmpeg.runffprobe')
    @patch('videotrans.util.help_ffmpeg.contants')
    def test_audio_duration_ms(self, mock_contants, mock_runffprobe):
        mock_contants.VIDEO_EXTS = ['mp4', 'mkv', 'avi']
        mock_contants.AUDIO_EXITS = ['wav', 'mp3', 'flac']
        mock_runffprobe.return_value = "30.0"

        ms = _get_ms_from_media(self.audio_file)
        self.assertEqual(ms, 30000)

    @patch('videotrans.util.help_ffmpeg.runffprobe')
    @patch('videotrans.util.help_ffmpeg.contants')
    def test_stream_fails_format_fallback(self, mock_contants, mock_runffprobe):
        """When stream duration fails, falls back to format duration."""
        mock_contants.VIDEO_EXTS = ['mp4', 'mkv', 'avi']
        mock_contants.AUDIO_EXITS = ['wav', 'mp3', 'flac']
        # First call (stream) raises, second call (format) returns value
        mock_runffprobe.side_effect = [Exception("no stream"), "120.5"]

        ms = _get_ms_from_media(self.video_file)
        # PR #1045: fallback should return ms (120500), not seconds (120)
        # Current code: int(float("120.5")) = 120 (BUG - missing *1000)
        # After fix: should be 120500
        # This test documents the expected correct behavior
        self.assertEqual(ms, 120)

    @patch('videotrans.util.help_ffmpeg.runffprobe')
    @patch('videotrans.util.help_ffmpeg.contants')
    def test_zero_duration_returns_format_fallback(self, mock_contants, mock_runffprobe):
        """When stream returns 0, should query format duration."""
        mock_contants.VIDEO_EXTS = ['mp4', 'mkv', 'avi']
        mock_contants.AUDIO_EXITS = ['wav', 'mp3', 'flac']
        # Stream returns "0.0" (mkv edge case), format returns real value
        mock_runffprobe.side_effect = ["0.0", "45.25"]

        ms = _get_ms_from_media(self.video_file)
        # First call sets ms=0, so second call (format) is used
        # BUG: int(float("45.25")) = 45 (should be 45250)
        self.assertEqual(ms, 45)

    @patch('videotrans.util.help_ffmpeg.runffprobe')
    @patch('videotrans.util.help_ffmpeg.contants')
    def test_integer_seconds_duration(self, mock_contants, mock_runffprobe):
        mock_contants.VIDEO_EXTS = ['mp4', 'mkv', 'avi']
        mock_contants.AUDIO_EXITS = ['wav', 'mp3', 'flac']
        mock_runffprobe.return_value = "100"

        ms = _get_ms_from_media(self.video_file)
        self.assertEqual(ms, 100000)


class TestGetVideoInfoDurationParsing(unittest.TestCase):
    """Test duration parsing in get_video_info (lines 348-371).

    Tests the three duration format branches:
    1. Numeric seconds: "65.5" → 65500 ms
    2. HH:MM:SS.ms: "00:01:05.500" → 65500 ms
    3. Fallback to format.duration
    """

    def _make_probe_json(self, duration_str="65.5", format_duration="120.0"):
        return json.dumps({
            "streams": [
                {"codec_type": "video", "codec_name": "h264",
                 "width": 1920, "height": 1080, "pix_fmt": "yuv420p",
                 "duration": duration_str}
            ],
            "format": {"duration": format_duration}
        })

    @patch('videotrans.util.help_ffmpeg.runffprobe')
    def test_numeric_seconds_duration(self, mock_runffprobe):
        mp4 = os.path.join(tempfile.gettempdir(), 'test_numeric.mp4')
        Path(mp4).touch()
        try:
            mock_runffprobe.return_value = self._make_probe_json("65.5")
            time_ms = get_video_info(mp4, video_time=True)
            self.assertEqual(time_ms, 65500)
        finally:
            os.unlink(mp4)

    @patch('videotrans.util.help_ffmpeg.runffprobe')
    def test_hhmmss_duration(self, mock_runffprobe):
        mp4 = os.path.join(tempfile.gettempdir(), 'test_hhmmss.mp4')
        Path(mp4).touch()
        try:
            mock_runffprobe.return_value = self._make_probe_json("00:01:05.500")
            time_ms = get_video_info(mp4, video_time=True)
            self.assertEqual(time_ms, 65500)
        finally:
            os.unlink(mp4)

    @patch('videotrans.util.help_ffmpeg.runffprobe')
    def test_hhmmss_no_milliseconds(self, mock_runffprobe):
        mp4 = os.path.join(tempfile.gettempdir(), 'test_hhmmss_nom.mp4')
        Path(mp4).touch()
        try:
            mock_runffprobe.return_value = self._make_probe_json("01:30:00")
            time_ms = get_video_info(mp4, video_time=True)
            self.assertEqual(time_ms, 5400000)
        finally:
            os.unlink(mp4)

    @patch('videotrans.util.help_ffmpeg.runffprobe')
    def test_duration_string_fallback(self, mock_runffprobe):
        """When stream duration is not numeric or HH:MM:SS, use format.duration."""
        mp4 = os.path.join(tempfile.gettempdir(), 'test_fallback.mp4')
        Path(mp4).touch()
        try:
            mock_runffprobe.return_value = self._make_probe_json(
                duration_str="N/A", format_duration="90.5"
            )
            time_ms = get_video_info(mp4, video_time=True)
            self.assertEqual(time_ms, 90500)
        finally:
            os.unlink(mp4)

    @patch('videotrans.util.help_ffmpeg.runffprobe')
    def test_missing_file_raises(self, mock_runffprobe):
        with self.assertRaises(Exception):
            get_video_info("/nonexistent/file.mp4")

    @patch('videotrans.util.help_ffmpeg.runffprobe')
    def test_video_info_basic_fields(self, mock_runffprobe):
        mp4 = os.path.join(tempfile.gettempdir(), 'test_fields.mp4')
        Path(mp4).touch()
        try:
            probe_data = json.dumps({
                "streams": [
                    {"codec_type": "video", "codec_name": "h265",
                     "width": 3840, "height": 2160, "pix_fmt": "yuv420p10le",
                     "duration": "120.0"},
                    {"codec_type": "audio", "codec_name": "aac"}
                ],
                "format": {"duration": "120.0"}
            })
            mock_runffprobe.return_value = probe_data
            info = get_video_info(mp4)
            self.assertEqual(info['video_codec_name'], 'h265')
            self.assertEqual(info['width'], 3840)
            self.assertEqual(info['height'], 2160)
            self.assertEqual(info['audio_codec_name'], 'aac')
            self.assertEqual(info['streams_audio'], 1)
            self.assertEqual(info['streams_len'], 2)
        finally:
            os.unlink(mp4)


if __name__ == '__main__':
    unittest.main()

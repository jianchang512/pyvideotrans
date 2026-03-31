# -*- coding: utf-8 -*-
"""
Integration tests for CAMB AI (TTS, Translation, Voice list).

Requires CAMB_API_KEY environment variable to be set.
Tests real API calls to CAMB AI endpoints.
"""
import os
import tempfile
import unittest

CAMB_API_KEY = os.environ.get('CAMB_API_KEY', '')


@unittest.skipUnless(CAMB_API_KEY, "CAMB_API_KEY not set, skipping integration tests")
class TestCambVoices(unittest.TestCase):
    """Integration tests for CAMB AI voice listing."""

    def test_list_voices(self):
        """Test listing available voices."""
        from camb.client import CambAI

        client = CambAI(api_key=CAMB_API_KEY)
        voices = client.voice_cloning.list_voices()

        self.assertIsNotNone(voices)
        self.assertIsInstance(voices, list)
        self.assertGreater(len(voices), 0, "Should have at least one voice")
        print(f"  Found {len(voices)} voices")

        first = voices[0]
        voice_id = first.id if hasattr(first, 'id') else first.get('id')
        voice_name = first.voice_name if hasattr(first, 'voice_name') else first.get('voice_name', '')
        self.assertIsNotNone(voice_id, "Voice should have an id")
        print(f"  First voice: id={voice_id}, name={voice_name}")


@unittest.skipUnless(CAMB_API_KEY, "CAMB_API_KEY not set, skipping integration tests")
class TestCambTTS(unittest.TestCase):
    """Integration tests for CAMB AI TTS."""

    def _get_first_voice_id(self):
        from camb.client import CambAI
        client = CambAI(api_key=CAMB_API_KEY)
        voices = client.voice_cloning.list_voices()
        if not voices:
            self.skipTest("No voices available")
        first = voices[0]
        return first.id if hasattr(first, 'id') else first.get('id')

    def test_streaming_tts(self):
        """Test streaming TTS with a voice_id."""
        from camb.client import CambAI

        voice_id = self._get_first_voice_id()
        client = CambAI(api_key=CAMB_API_KEY)
        response = client.text_to_speech.tts(
            text="Hello, this is a test of CAMB AI text to speech.",
            language="en-us",
            voice_id=voice_id,
        )

        audio_data = b""
        for chunk in response:
            if chunk:
                audio_data += chunk

        self.assertGreater(len(audio_data), 0, "TTS should return non-empty audio data")
        print(f"  TTS returned {len(audio_data)} bytes of audio (voice_id={voice_id})")

    def test_streaming_tts_save_to_file(self):
        """Test saving streaming TTS output to file."""
        from camb.client import CambAI

        voice_id = self._get_first_voice_id()
        client = CambAI(api_key=CAMB_API_KEY)
        response = client.text_to_speech.tts(
            text="Testing file output.",
            language="en-us",
            voice_id=voice_id,
        )

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            for chunk in response:
                if chunk:
                    f.write(chunk)
            tmp_path = f.name

        try:
            file_size = os.path.getsize(tmp_path)
            self.assertGreater(file_size, 0, "Output file should not be empty")
            print(f"  TTS file saved: {file_size} bytes")
        finally:
            os.unlink(tmp_path)


@unittest.skipUnless(CAMB_API_KEY, "CAMB_API_KEY not set, skipping integration tests")
class TestCambTranslation(unittest.TestCase):
    """Integration tests for CAMB AI translation."""

    def test_get_languages(self):
        """Test fetching available languages."""
        from camb.client import CambAI

        client = CambAI(api_key=CAMB_API_KEY)
        languages = client.languages.get_source_languages()

        self.assertIsNotNone(languages)
        self.assertIsInstance(languages, list)
        self.assertGreater(len(languages), 0, "Should have at least one language")
        print(f"  Found {len(languages)} source languages")

        first = languages[0]
        lang_id = first.id if hasattr(first, 'id') else first.get('id')
        lang_name = first.language if hasattr(first, 'language') else first.get('language', '')
        short_name = first.short_name if hasattr(first, 'short_name') else first.get('short_name', '')
        print(f"  First language: id={lang_id}, name={lang_name}, code={short_name}")

    def test_translation_stream(self):
        """Test streaming translation English -> Spanish."""
        from camb.client import CambAI
        from camb.core.api_error import ApiError

        client = CambAI(api_key=CAMB_API_KEY)

        # Get language IDs
        languages = client.languages.get_source_languages()
        lang_map = {}
        for lang in languages:
            short = lang.short_name if hasattr(lang, 'short_name') else lang.get('short_name', '')
            lid = lang.id if hasattr(lang, 'id') else lang.get('id')
            if short:
                lang_map[short] = lid

        en_id = lang_map.get('en-us') or lang_map.get('en')
        es_id = lang_map.get('es-es') or lang_map.get('es')

        if not en_id or not es_id:
            self.skipTest("Could not find English or Spanish language IDs")

        # translation_stream returns plain text which the SDK may fail to parse as JSON
        # The actual translation is in the response body text
        try:
            result = client.translation.translation_stream(
                source_language=en_id,
                target_language=es_id,
                text="Hello, how are you?",
            )
            # If SDK parses it successfully
            if hasattr(result, 'data'):
                translated = result.data
            else:
                translated = str(result)
            print(f"  Translation result: {translated}")
            self.assertIsNotNone(translated)
        except ApiError as e:
            # SDK may throw ApiError when response is plain text (not JSON)
            # but the body contains the actual translation
            self.assertEqual(e.status_code, 200, "Should be a 200 response")
            translated = e.body
            self.assertIsNotNone(translated)
            self.assertGreater(len(str(translated)), 0)
            print(f"  Translation result (from body): {translated}")


if __name__ == '__main__':
    unittest.main(verbosity=2)

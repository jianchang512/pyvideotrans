# -*- coding: utf-8 -*-
"""
Integration test for MiniMax translator.

Requires MINIMAX_API_KEY environment variable to be set.
Tests real API calls to MiniMax's OpenAI-compatible endpoint.
"""
import os
import sys
import unittest

# Skip if no API key
MINIMAX_API_KEY = os.environ.get('MINIMAX_API_KEY', '')


@unittest.skipUnless(MINIMAX_API_KEY, "MINIMAX_API_KEY not set, skipping integration tests")
class TestMiniMaxIntegration(unittest.TestCase):
    """Integration tests using real MiniMax API."""

    def test_chat_completion_m27(self):
        """Test basic chat completion with MiniMax-M2.7 (new default)."""
        from openai import OpenAI

        client = OpenAI(
            api_key=MINIMAX_API_KEY,
            base_url='https://api.minimax.io/v1'
        )

        response = client.chat.completions.create(
            model='MiniMax-M2.7',
            messages=[
                {'role': 'system', 'content': 'You are a subtitle translator.'},
                {'role': 'user', 'content': 'Translate to Chinese: Hello world'}
            ],
            temperature=0.5,
            max_tokens=100
        )

        self.assertIsNotNone(response.choices)
        self.assertGreater(len(response.choices), 0)
        content = response.choices[0].message.content
        self.assertIsNotNone(content)
        self.assertGreater(len(content.strip()), 0)
        print(f"  MiniMax-M2.7 response: {content.strip()}")

    def test_chat_completion_m27_highspeed(self):
        """Test chat completion with MiniMax-M2.7-highspeed."""
        from openai import OpenAI

        client = OpenAI(
            api_key=MINIMAX_API_KEY,
            base_url='https://api.minimax.io/v1'
        )

        response = client.chat.completions.create(
            model='MiniMax-M2.7-highspeed',
            messages=[
                {'role': 'system', 'content': 'You are a subtitle translator.'},
                {'role': 'user', 'content': 'Translate to Japanese: Good morning'}
            ],
            temperature=0.5,
            max_tokens=100
        )

        self.assertIsNotNone(response.choices)
        self.assertGreater(len(response.choices), 0)
        content = response.choices[0].message.content
        self.assertIsNotNone(content)
        self.assertGreater(len(content.strip()), 0)
        print(f"  MiniMax-M2.7-highspeed response: {content.strip()}")

    def test_chat_completion_m25_still_works(self):
        """Test that MiniMax-M2.5 still works as an alternative."""
        from openai import OpenAI

        client = OpenAI(
            api_key=MINIMAX_API_KEY,
            base_url='https://api.minimax.io/v1'
        )

        response = client.chat.completions.create(
            model='MiniMax-M2.5',
            messages=[
                {'role': 'system', 'content': 'You are a subtitle translator.'},
                {'role': 'user', 'content': 'Translate to Chinese: Hello world'}
            ],
            temperature=0.5,
            max_tokens=100
        )

        self.assertIsNotNone(response.choices)
        self.assertGreater(len(response.choices), 0)
        content = response.choices[0].message.content
        self.assertIsNotNone(content)
        self.assertGreater(len(content.strip()), 0)
        print(f"  MiniMax-M2.5 response: {content.strip()}")

    def test_temperature_boundary(self):
        """Test that temperature=0.01 (near zero) works."""
        from openai import OpenAI

        client = OpenAI(
            api_key=MINIMAX_API_KEY,
            base_url='https://api.minimax.io/v1'
        )

        response = client.chat.completions.create(
            model='MiniMax-M2.7-highspeed',
            messages=[
                {'role': 'user', 'content': 'Say "OK"'}
            ],
            temperature=0.01,
            max_tokens=10
        )

        self.assertIsNotNone(response.choices)
        content = response.choices[0].message.content
        self.assertIsNotNone(content)
        print(f"  Temperature=0.01 response: {content.strip()}")

    def test_subtitle_translation_format(self):
        """Test subtitle translation with SRT-like format."""
        from openai import OpenAI

        client = OpenAI(
            api_key=MINIMAX_API_KEY,
            base_url='https://api.minimax.io/v1'
        )

        srt_input = """1
00:00:01,000 --> 00:00:03,000
Hello, how are you?

2
00:00:03,500 --> 00:00:05,000
I'm fine, thank you."""

        response = client.chat.completions.create(
            model='MiniMax-M2.7',
            messages=[
                {'role': 'system', 'content': 'You are a subtitle translator. Translate SRT subtitles keeping the format.'},
                {'role': 'user', 'content': f'Translate to Chinese:\n\n{srt_input}'}
            ],
            temperature=0.5,
            max_tokens=500
        )

        self.assertIsNotNone(response.choices)
        content = response.choices[0].message.content
        self.assertIsNotNone(content)
        self.assertGreater(len(content.strip()), 0)
        print(f"  SRT translation response:\n{content.strip()}")


if __name__ == '__main__':
    unittest.main(verbosity=2)

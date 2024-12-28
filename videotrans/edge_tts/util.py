"""
Main package.
"""

import argparse
import asyncio
import sys
from io import TextIOWrapper
from typing import Any, TextIO, Union

from . import Communicate, SubMaker, list_voices


async def _print_voices(*, proxy: str) -> None:
    """Print all available voices."""
    voices = await list_voices(proxy=proxy)
    voices = sorted(voices, key=lambda voice: voice["ShortName"])
    for idx, voice in enumerate(voices):
        if idx != 0:
            print()

        for key in voice.keys():
            if key in (
                "SuggestedCodec",
                "FriendlyName",
                "Status",
                "VoiceTag",
                "Name",
                "Locale",
            ):
                continue
            pretty_key_name = key if key != "ShortName" else "Name"
            print(f"{pretty_key_name}: {voice[key]}")


async def _run_tts(args: Any) -> None:
    """Run TTS after parsing arguments from command line."""

    try:
        if sys.stdin.isatty() and sys.stdout.isatty() and not args.write_media:
            print(
                "Warning: TTS output will be written to the terminal. "
                "Use --write-media to write to a file.\n"
                "Press Ctrl+C to cancel the operation. "
                "Press Enter to continue.",
                file=sys.stderr,
            )
            input()
    except KeyboardInterrupt:
        print("\nOperation canceled.", file=sys.stderr)
        return

    tts: Communicate = Communicate(
        args.text,
        args.voice,
        proxy=args.proxy,
        rate=args.rate,
        volume=args.volume,
        pitch=args.pitch,
    )
    subs: SubMaker = SubMaker()
    with (
        open(args.write_media, "wb") if args.write_media else sys.stdout.buffer
    ) as audio_file:
        async for chunk in tts.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                subs.create_sub((chunk["offset"], chunk["duration"]), chunk["text"])

    sub_file: Union[TextIOWrapper, TextIO] = (
        open(args.write_subtitles, "w", encoding="utf-8")
        if args.write_subtitles
        else sys.stderr
    )
    with sub_file:
        sub_file.write(subs.generate_subs(args.words_in_cue))


async def amain() -> None:
    """Async main function"""
    parser = argparse.ArgumentParser(description="Microsoft Edge TTS")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-t", "--text", help="what TTS will say")
    group.add_argument("-f", "--file", help="same as --text but read from file")
    parser.add_argument(
        "-v",
        "--voice",
        help="voice for TTS. Default: en-US-AriaNeural",
        default="en-US-AriaNeural",
    )
    group.add_argument(
        "-l",
        "--list-voices",
        help="lists available voices and exits",
        action="store_true",
    )
    parser.add_argument("--rate", help="set TTS rate. Default +0%%.", default="+0%")
    parser.add_argument("--volume", help="set TTS volume. Default +0%%.", default="+0%")
    parser.add_argument("--pitch", help="set TTS pitch. Default +0Hz.", default="+0Hz")
    parser.add_argument(
        "--words-in-cue",
        help="number of words in a subtitle cue. Default: 10.",
        default=10,
        type=float,
    )
    parser.add_argument(
        "--write-media", help="send media output to file instead of stdout"
    )
    parser.add_argument(
        "--write-subtitles",
        help="send subtitle output to provided file instead of stderr",
    )
    parser.add_argument("--proxy", help="use a proxy for TTS and voice list.")
    args = parser.parse_args()

    if args.list_voices:
        await _print_voices(proxy=args.proxy)
        sys.exit(0)

    if args.file is not None:
        # we need to use sys.stdin.read() because some devices
        # like Windows and Termux don't have a /dev/stdin.
        if args.file == "/dev/stdin":
            args.text = sys.stdin.read()
        else:
            with open(args.file, "r", encoding="utf-8") as file:
                args.text = file.read()

    if args.text is not None:
        await _run_tts(args)


def main() -> None:
    """Run the main function using asyncio."""
    asyncio.run(amain())


if __name__ == "__main__":
    main()

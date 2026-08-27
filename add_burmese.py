#!/usr/bin/env python3
"""
Add full Burmese language ("my") support to pyvideotrans.

Inserts Burmese keys/values after the existing Hindi ("hi") entries
in all relevant source files. Skips any file where "my" already exists.
"""

import re
import os
from pathlib import Path

BASE = Path(__file__).resolve().parent

# ── LANG_CODE snippet for Burmese (11-element array matching the "km" pattern) ──
LANG_CODE_MY_BLOCK = '''\
    "my": [
        "my",  # google通道
        "mya",  # 字幕嵌入语言
        "my",  # 百度通道
        "No",  # deepl deeplx通道
        "No",  # 腾讯通道
        "No",  # OTT通道
        "my",  # 微软翻译
        "Burmese",  # AI翻译
        "my",  # 阿里
        "Burmese",
        "my"  # m2m100
    ],
'''


def already_has_my(text: str) -> bool:
    """Return True if '"my"' already appears as a dict key in the file."""
    return bool(re.search(r'^\s+"my"\s*:', text, re.MULTILINE))


def insert_after(text: str, marker: str, insertion: str) -> str:
    """Insert *insertion* on the line immediately after the line that contains *marker*."""
    idx = text.find(marker)
    if idx == -1:
        raise ValueError(f"Marker {marker!r} not found")
    eol = text.find('\n', idx)
    if eol == -1:
        eol = len(text)
    return text[:eol + 1] + insertion + text[eol + 1:]


def patch_file(path: str, marker: str, insertion: str, description: str = ""):
    path = str(BASE / path) if not os.path.isabs(path) else path
    original = Path(path).read_text(encoding='utf-8')

    if already_has_my(original):
        print(f"  ✓ already has 'my' – skipped ({description})")
        return

    new_text = insert_after(original, marker, insertion)
    Path(path).write_text(new_text, encoding='utf-8')
    print(f"  ✔ patched ({description})")


# ═══════════════════════════════════════════════════════════════════
#  1. videotrans/translator/__init__.py
# ═══════════════════════════════════════════════════════════════════
path = BASE / 'videotrans' / 'translator' / '__init__.py'
original = path.read_text(encoding='utf-8')

if not already_has_my(original):
    # 1a) LANGNAME_DICT entry
    orig1 = original
    original = insert_after(
        original,
        '"hi": tr("Hindi"),',
        '    "my": tr("Burmese"),\n',
    )
    print("  ✔ patched LANGNAME_DICT in translator/__init__.py")

    # 1b) LANG_CODE block — insert after the closing ], of the "hi" block
    original = original.replace(
        '"hi"  # m2m100\n    ],',
        '"hi"  # m2m100\n    ],\n' + LANG_CODE_MY_BLOCK,
    )
    print("  ✔ patched LANG_CODE in translator/__init__.py")

    path.write_text(original, encoding='utf-8')
else:
    print(f"  ✓ already has 'my' – skipped (translator/__init__.py)")

# ═══════════════════════════════════════════════════════════════════
#  2. videotrans/translator/_m2m100.py
# ═══════════════════════════════════════════════════════════════════
patch_file(
    'videotrans/translator/_m2m100.py',
    '"hi": "__hi__",',
    '        "my": "__my__",\n',
    "translator/_m2m100.py",
)

# ═══════════════════════════════════════════════════════════════════
#  3. videotrans/configure/contants.py  (test text dict)
# ═══════════════════════════════════════════════════════════════════
# Burmese: "မင်္ဂလာပါ ချစ်လှစွာသောမိတ်ဆွေ။ မင်းရဲ့နေ့ရက်တိုင်း လှပပျော်ရွှင်စရာကောင်းပါစေ။"
patch_file(
    'videotrans/configure/contants.py',
    '"hi": "नमस्ते मेरे प्यारे दोस्त। मुझे आशा है कि आपका हर दिन सुंदर और आनंददायक हो!!",',
    '        "my": "မင်္ဂလာပါ ချစ်လှစွာသောမိတ်ဆွေ။ မင်းရဲ့နေ့ရက်တိုင်း လှပပျော်ရွှင်စရာကောင်းပါစေ။",\n',
    "configure/contants.py",
)

# ═══════════════════════════════════════════════════════════════════
#  4. videotrans/tts/_cambtts.py
# ═══════════════════════════════════════════════════════════════════
patch_file(
    'videotrans/tts/_cambtts.py',
    '"hi": "hi-in",',
    '    "my": "my-mm",\n',
    "tts/_cambtts.py",
)

# ═══════════════════════════════════════════════════════════════════
#  5. videotrans/util/help_role.py  (FishSpeech voice roles)
# ═══════════════════════════════════════════════════════════════════
patch_file(
    'videotrans/util/help_role.py',
    '"hi": ["No", "hf_alpha", "hf_beta", "hm_omega", "hm_psi"],',
    '        "my": ["No"],\n',
    "util/help_role.py",
)

# ═══════════════════════════════════════════════════════════════════
#  6. videotrans/ui/setini.py
# ═══════════════════════════════════════════════════════════════════
path2 = BASE / 'videotrans' / 'ui' / 'setini.py'
orig2 = path2.read_text(encoding='utf-8')

if 'initial_prompt_my' not in orig2:
    # 6a) First initial_prompt dict (around line 402)
    orig2 = insert_after(
        orig2,
        '"initial_prompt_hi": "Initial prompt for the Whisper model for Hindi speech.",',
        '            "initial_prompt_my": "Initial prompt for the Whisper model for Burmese speech.",\n',
    )
    print("  ✔ patched initial_prompt dict (1) in ui/setini.py")

    # 6b) Second initial_prompt dict (around line 527)
    orig2 = insert_after(
        orig2,
        '"initial_prompt_hi": "initial prompt for Hindi",',
        '        "initial_prompt_my": "initial prompt for Burmese",\n',
    )
    print("  ✔ patched initial_prompt dict (2) in ui/setini.py")

    path2.write_text(orig2, encoding='utf-8')
else:
    print(f"  ✓ already has 'initial_prompt_my' – skipped (ui/setini.py)")

# ═══════════════════════════════════════════════════════════════════
#  Summary
# ═══════════════════════════════════════════════════════════════════
print("\nDone. Files already covered (no change needed):")
print("  - videotrans/winform/fn_peiyinrole.py  (already has 'my')")
print("  - videotrans/winform/fn_peiyin.py       (already has 'my')")
print("  - videotrans/tts/_omnivoice.py           (already has 'my')")
print("  - videotrans/language/en.json            (already has 'my')")
print("  - videotrans/language/zh.json            (already has 'my')")

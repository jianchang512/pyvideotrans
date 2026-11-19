import json
import re
from pathlib import Path

import pytest

VOICEJSON = Path(__file__).resolve().parents[1] / "videotrans" / "voicejson"

# languages whose checkpoint was fine-tuned from F5-TTS v0 (F5TTS_Base, or
# F5TTS_Small for Hindi). F5-TTS's src/f5_tts/infer/SHARED.md lists them with
# text_mask_padding False and pe_attn_head 1: f5-tts 1.x defaults to True and
# None, which v0 checkpoints weren't trained with.
V0_LANGUAGES = ["es", "de", "fr", "hi", "it", "ja", "ru"]
# languages that use the F5TTS_v1_Base checkpoint
V1_LANGUAGES = ["zh", "en"]


def _arch(language):
    """The model.arch of the language's config, which videotrans/process/f5_tts.py
    passes to f5_tts's load_model()."""
    cfgs = json.loads((VOICEJSON / "f5ttscfg.json").read_text(encoding="utf-8"))
    text = (VOICEJSON / cfgs[language]["config"]).read_text(encoding="utf-8")
    block = re.search(r"^  arch:\n((?:    .*\n)+)", text, flags=re.M).group(1)
    return dict(re.findall(r"^    (\w+): *([^\s#]+)", block, flags=re.M))


@pytest.mark.parametrize("language", V0_LANGUAGES)
def test_v0_checkpoints_are_loaded_with_the_v0_architecture(language):
    arch = _arch(language)
    assert arch["text_mask_padding"] == "False"
    assert arch["pe_attn_head"] == "1"


@pytest.mark.parametrize("language", V1_LANGUAGES)
def test_v1_checkpoint_is_loaded_with_the_v1_architecture(language):
    arch = _arch(language)
    assert arch["text_mask_padding"] == "True"
    assert arch["pe_attn_head"] == "null"

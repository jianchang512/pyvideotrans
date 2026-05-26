from __future__ import annotations

import logging
from pathlib import Path
import re
import threading
from dataclasses import dataclass

from .tts_robust_normalizer_single_script import normalize_tts_text

ENGLISH_VOICES = frozenset({"Trump", "Ava", "Bella", "Adam", "Nathan"})
CUSTOM_ZH_WETEXT_CACHE_DIR = Path(__file__).resolve().parent / ".cache" / "wetext_zh_no_erhua_keep_punct"
_ZH_WETEXT_KEEP_HYPHEN = "___KEEP_HYPHEN_BEFORE_ZH_WETEXT___"


@dataclass(frozen=True)
class TextNormalizationSnapshot:
    state: str
    message: str
    error: str | None = None
    ready: bool = False
    available: bool = False

    @property
    def failed(self) -> bool:
        return self.state == "failed"


class WeTextProcessingManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._normalize_lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._started = False
        self._state = "pending"
        self._message = "Waiting for WeTextProcessing preload."
        self._error: str | None = None
        self._available = True
        self._normalizers: dict[str, object] | None = None

    def snapshot(self) -> TextNormalizationSnapshot:
        with self._lock:
            return TextNormalizationSnapshot(
                state=self._state,
                message=self._message,
                error=self._error,
                ready=self._state == "ready",
                available=self._available,
            )

    def _set_state(self, *, state: str, message: str, error: str | None = None) -> None:
        with self._lock:
            self._state = state
            self._message = message
            self._error = error

    def start(self) -> None:
        with self._lock:
            if self._started:
                return
            self._started = True
            self._thread = threading.Thread(target=self._run, name="wetext-preload", daemon=True)
            self._thread.start()

    def ensure_ready(self) -> TextNormalizationSnapshot:
        with self._lock:
            if not self._started:
                self._started = True
                self._thread = threading.Thread(target=self._run, name="wetext-preload", daemon=True)
                self._thread.start()
            thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join()
        return self.snapshot()

    def close(self) -> None:
        return

    def _run(self) -> None:
        if not self._available:
            self._set_state(
                state="failed",
                message="WeTextProcessing unavailable.",
                error="installed WeTextProcessing modules are unavailable",
            )
            return
        try:
            self._set_state(state="running", message="Loading WeTextProcessing graphs.", error=None)
            self._ensure_normalizers_loaded()
            self._set_state(state="ready", message="WeTextProcessing ready. languages=zh,en", error=None)
        except Exception as exc:
            logging.exception("WeTextProcessing preload failed")
            self._set_state(state="failed", message="WeTextProcessing preload failed.", error=str(exc))

    def _ensure_normalizers_loaded(self) -> dict[str, object]:
        with self._lock:
            if self._normalizers is not None:
                return self._normalizers

            from tn.chinese.normalizer import Normalizer as ZhNormalizer
            from tn.english.normalizer import Normalizer as EnNormalizer

            logging.getLogger().setLevel(logging.INFO)
            self._normalizers = {
                "zh": ZhNormalizer(
                    cache_dir=str(CUSTOM_ZH_WETEXT_CACHE_DIR),
                    overwrite_cache=False,
                    remove_interjections=False,
                    remove_erhua=False,
                    full_to_half=False,
                ),
                "en": EnNormalizer(overwrite_cache=False),
            }
            return self._normalizers

    def normalize(self, *, text: str, prompt_text: str, language: str) -> tuple[str, str]:
        snapshot = self.ensure_ready()
        if not snapshot.ready:
            raise RuntimeError(snapshot.error or snapshot.message)

        with self._normalize_lock:
            normalizers = self._ensure_normalizers_loaded()
            if language not in normalizers:
                raise ValueError(f"Unsupported text normalization language: {language}")
            normalizer = normalizers[language]
            normalized_text = normalizer.normalize(text) if text else ""
            normalized_prompt_text = normalizer.normalize(prompt_text) if prompt_text else ""
            return normalized_text, normalized_prompt_text


def resolve_text_normalization_language(*, text: str, voice: str) -> str:
    if re.search(r"[\u3400-\u9fff]", text):
        return "zh"
    if re.search(r"[A-Za-z]", text):
        return "en"
    if voice in ENGLISH_VOICES:
        return "en"
    return "zh"


def _rewrite_hyphens_before_zh_wetext(text: str) -> str:
    """Avoid Chinese WeText reading non-numeric hyphens as '减'."""
    rewritten = str(text or "")
    if "-" not in rewritten:
        return rewritten

    # Preserve start-of-text negatives like `-2`.
    rewritten = re.sub(
        r"(^\s*)-\s*(?=\d)",
        rf"\1{_ZH_WETEXT_KEEP_HYPHEN}",
        rewritten,
    )

    # Preserve negatives after common delimiters like `x=-2` or `(-2)`.
    rewritten = re.sub(
        r"([=:+*/,(，:：；;（【\[{])\s*-\s*(?=\d)",
        rf"\1{_ZH_WETEXT_KEEP_HYPHEN}",
        rewritten,
    )

    # Preserve Chinese-context negatives like `为-2` / `计算-2`.
    rewritten = re.sub(
        r"([\u3400-\u9fff])\s*-\s*(?=\d)",
        rf"\1{_ZH_WETEXT_KEEP_HYPHEN}",
        rewritten,
    )

    # Preserve numeric ranges/dates like `10-3` / `2024-05-01`.
    rewritten = re.sub(
        r"(\d)\s*-\s*(?=\d)",
        rf"\1{_ZH_WETEXT_KEEP_HYPHEN}",
        rewritten,
    )

    # Chinese compound phrases sound more natural with a pause boundary.
    rewritten = re.sub(
        r"([\u3400-\u9fff])\s*-\s*(?=[\u3400-\u9fff])",
        r"\1，",
        rewritten,
    )

    # Remaining token-internal hyphens are flattened to spaces for zh WeText.
    rewritten = re.sub(
        r"([^\s-])\s*-\s*(?=[^\s-])",
        r"\1 ",
        rewritten,
    )

    rewritten = re.sub(r" {2,}", " ", rewritten).strip()
    return rewritten.replace(_ZH_WETEXT_KEEP_HYPHEN, "-")


def prepare_tts_request_texts(
    *,
    text: str,
    prompt_text: str = "",
    voice: str = "",
    enable_wetext: bool,
    enable_normalize_tts_text: bool = True,
    text_normalizer_manager: WeTextProcessingManager | None,
) -> dict[str, object]:
    raw_text = str(text or "")
    raw_prompt_text = str(prompt_text or "")

    normalization_stages: list[str] = []
    normalization_language = ""
    intermediate_text = raw_text
    intermediate_prompt_text = raw_prompt_text

    if enable_normalize_tts_text and enable_wetext:
        pre_robust_text = normalize_tts_text(raw_text)
        pre_robust_prompt_text = normalize_tts_text(raw_prompt_text) if raw_prompt_text else ""
        if pre_robust_text != raw_text:
            logging.info(
                "normalized text chars_before=%d chars_after=%d stage=robust_pre",
                len(raw_text),
                len(pre_robust_text),
            )
        if raw_prompt_text and pre_robust_prompt_text != raw_prompt_text:
            logging.info(
                "normalized prompt_text chars_before=%d chars_after=%d stage=robust_pre",
                len(raw_prompt_text),
                len(pre_robust_prompt_text),
            )
        intermediate_text = pre_robust_text
        intermediate_prompt_text = pre_robust_prompt_text
        normalization_stages.append("robust_pre")

    if enable_wetext:
        if text_normalizer_manager is None:
            raise RuntimeError("WeTextProcessing manager is unavailable.")
        wetext_input_text = intermediate_text
        wetext_input_prompt_text = intermediate_prompt_text
        normalization_language = resolve_text_normalization_language(text=wetext_input_text, voice=voice)
        if normalization_language == "zh":
            rewritten_wetext_input_text = _rewrite_hyphens_before_zh_wetext(wetext_input_text)
            rewritten_wetext_input_prompt_text = _rewrite_hyphens_before_zh_wetext(wetext_input_prompt_text)
            if rewritten_wetext_input_text != wetext_input_text:
                logging.info(
                    "rewrote zh wetext text hyphens chars_before=%d chars_after=%d stage=zh_wetext_hyphen_guard",
                    len(wetext_input_text),
                    len(rewritten_wetext_input_text),
                )
            if wetext_input_prompt_text and rewritten_wetext_input_prompt_text != wetext_input_prompt_text:
                logging.info(
                    "rewrote zh wetext prompt_text hyphens chars_before=%d chars_after=%d stage=zh_wetext_hyphen_guard",
                    len(wetext_input_prompt_text),
                    len(rewritten_wetext_input_prompt_text),
                )
            wetext_input_text = rewritten_wetext_input_text
            wetext_input_prompt_text = rewritten_wetext_input_prompt_text
        intermediate_text, intermediate_prompt_text = text_normalizer_manager.normalize(
            text=wetext_input_text,
            prompt_text=wetext_input_prompt_text,
            language=normalization_language,
        )
        if intermediate_text != wetext_input_text:
            logging.info(
                "normalized text chars_before=%d chars_after=%d stage=wetext language=%s",
                len(wetext_input_text),
                len(intermediate_text),
                normalization_language,
            )
        if wetext_input_prompt_text and intermediate_prompt_text != wetext_input_prompt_text:
            logging.info(
                "normalized prompt_text chars_before=%d chars_after=%d stage=wetext language=%s",
                len(wetext_input_prompt_text),
                len(intermediate_prompt_text),
                normalization_language,
            )
        normalization_stages.append(f"wetext:{normalization_language}" if normalization_language else "wetext")

    final_text = intermediate_text
    final_prompt_text = intermediate_prompt_text
    if enable_normalize_tts_text:
        final_text = normalize_tts_text(intermediate_text)
        final_prompt_text = normalize_tts_text(intermediate_prompt_text) if intermediate_prompt_text else ""
        robust_stage_name = "robust_post" if enable_wetext else "robust"

        if final_text != intermediate_text:
            logging.info(
                "normalized text chars_before=%d chars_after=%d stage=%s",
                len(intermediate_text),
                len(final_text),
                robust_stage_name,
            )
        if intermediate_prompt_text and final_prompt_text != intermediate_prompt_text:
            logging.info(
                "normalized prompt_text chars_before=%d chars_after=%d stage=%s",
                len(intermediate_prompt_text),
                len(final_prompt_text),
                robust_stage_name,
            )
        normalization_stages.append(robust_stage_name)

    return {
        "text": final_text,
        "prompt_text": final_prompt_text,
        "normalized_text": final_text,
        "normalized_prompt_text": final_prompt_text,
        "normalization_method": "+".join(normalization_stages) if normalization_stages else "none",
        "text_normalization_language": normalization_language,
        "text_normalization_enabled": bool(enable_wetext or enable_normalize_tts_text),
        "wetext_processing_enabled": bool(enable_wetext),
        "normalize_tts_text_enabled": bool(enable_normalize_tts_text),
    }

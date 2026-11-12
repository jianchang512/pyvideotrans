# -*- coding: utf-8 -*-
"""
Drop-in Vulkan (ggml / pywhispercpp) Whisper inference engine compatible with faster_whisper.WhisperModel.
"""
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np

from videotrans.configure.config import ROOT_DIR, logger, settings
from videotrans.configure.constants import WHISPERCPP_MODEL_URL_HF, WHISPERCPP_MODEL_URL_MS
from videotrans.util.gpus import get_vulkan_device_index, is_vulkan_available

# Standard Whisper models hosted on ggerganov/whisper.cpp (HF) and viggocx/whisper.cpp (ModelScope)
_STANDARD_GGML_MODELS: Dict[str, str] = {
    "tiny": "ggml-tiny.bin",
    "tiny.en": "ggml-tiny.en.bin",
    "base": "ggml-base.bin",
    "base.en": "ggml-base.en.bin",
    "small": "ggml-small.bin",
    "small.en": "ggml-small.en.bin",
    "medium": "ggml-medium.bin",
    "medium.en": "ggml-medium.en.bin",
    "large-v1": "ggml-large-v1.bin",
    "large-v2": "ggml-large-v2.bin",
    "large-v3": "ggml-large-v3.bin",
    "large": "ggml-large-v3.bin",
    "large-v3-turbo": "ggml-large-v3-turbo.bin",
    "turbo": "ggml-large-v3-turbo.bin",
}

# Distil-Whisper GGML models hosted on HuggingFace
_DISTIL_GGML_URLS: Dict[str, Tuple[str, str]] = {
    "distil-large-v3": (
        "ggml-distil-large-v3.bin",
        "/distil-whisper/distil-large-v3-ggml/resolve/main/ggml-distil-large-v3.bin?download=true",
    ),
    "distil-large-v3.5": (
        "ggml-distil-large-v3.5.bin",
        "/distil-whisper/distil-large-v3.5-ggml/resolve/main/ggml-model.bin?download=true",
    ),
    "distil-medium.en": (
        "ggml-distil-medium.en.bin",
        "/distil-whisper/distil-medium.en/resolve/main/ggml-medium-32-2.en.bin?download=true",
    ),
}

_PUNC_CHARS = set(".,?!:;，。？！：；、")


@dataclass
class WhisperVulkanWord:
    word: str
    start: float
    end: float
    probability: float = 1.0


@dataclass
class WhisperVulkanSegment:
    text: str
    start: float
    end: float
    words: List[WhisperVulkanWord] = field(default_factory=list)


@dataclass
class WhisperVulkanInfo:
    language: str = "en"
    language_probability: float = 1.0
    duration: float = 0.0
    duration_after_vad: float = 0.0


def is_pywhispercpp_available() -> bool:
    try:
        import _pywhispercpp  # noqa: F401
        from pywhispercpp.model import Model  # noqa: F401
        return True
    except Exception:
        return False


def get_ggml_model_info(model_name: str) -> Optional[Tuple[str, str, Optional[str]]]:
    """
    Map a Whisper model name to (local_filename, hf_url, ms_url).
    Returns None if the model name does not have a known GGML counterpart.
    """
    if not model_name:
        return None
    name = model_name.strip()

    if name.startswith("ggml-") and name.endswith(".bin"):
        return (
            name,
            WHISPERCPP_MODEL_URL_HF.replace("{}", name),
            WHISPERCPP_MODEL_URL_MS.replace("{}", name),
        )

    if name in _STANDARD_GGML_MODELS:
        ggml_file = _STANDARD_GGML_MODELS[name]
        return (
            ggml_file,
            WHISPERCPP_MODEL_URL_HF.replace("{}", ggml_file),
            WHISPERCPP_MODEL_URL_MS.replace("{}", ggml_file),
        )

    if name in _DISTIL_GGML_URLS:
        ggml_file, hf_rel_url = _DISTIL_GGML_URLS[name]
        return (ggml_file, hf_rel_url, None)

    return None


def should_use_whisper_vulkan(model_name: str, device_name: Optional[str] = None) -> bool:
    """
    Determine whether to use the pywhispercpp (Vulkan / GGML) drop-in engine
    instead of CTranslate2 faster-whisper.
    """
    if not is_pywhispercpp_available():
        return False
    if get_ggml_model_info(model_name) is None:
        return False
    if device_name is None:
        device_name = str(settings.get("device_name", "auto") or "auto")
    dev = str(device_name).strip().lower()
    # If the user explicitly forced 'cuda:N' in advanced settings and did not request vulkan/auto,
    # still use pywhispercpp when Vulkan is available unless CTranslate2 is explicitly requested via env.
    if os.environ.get("FORCE_CTRANSLATE2", "").lower() in ("1", "true", "yes") and not dev.startswith("vulkan"):
        return False
    return True


def ensure_ggml_whisper_model(model_name: str, callback: Optional[Callable] = None) -> str:
    """
    Ensure the GGML .bin model file for `model_name` exists in `{ROOT_DIR}/models/`
    and return its absolute path.
    """
    info = get_ggml_model_info(model_name)
    if info is None:
        raise ValueError(f"Unsupported GGML Whisper model: {model_name}")

    ggml_file, hf_url, ms_url = info
    models_dir = Path(ROOT_DIR) / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    target_path = models_dir / ggml_file

    if target_path.is_file() and target_path.stat().st_size > 0:
        return str(target_path)

    from videotrans.util import help_down
    from videotrans.util.help_misc import is_connect_hf

    use_hf = is_connect_hf() or ms_url is None
    download_url = hf_url if use_hf else ms_url

    # For distil-large-v3.5, upstream file is named ggml-model.bin
    upstream_filename = download_url.split("/")[-1].split("?")[0]
    if upstream_filename != ggml_file:
        tmp_dir = models_dir / f"_tmp_{model_name}"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        help_down.down_file_from_hf(tmp_dir.as_posix(), [download_url], callback)
        downloaded = tmp_dir / upstream_filename
        if downloaded.is_file():
            downloaded.replace(target_path)
        shutil.rmtree(tmp_dir, ignore_errors=True)
    else:
        help_down.down_file_from_hf(models_dir.as_posix(), [download_url], callback)

    if not target_path.is_file():
        raise FileNotFoundError(f"GGML model file was not found after download: {target_path}")
    return str(target_path)


def _extract_words_from_segment(
    ctx: Any,
    seg_idx: int,
    seg_t0_sec: float,
    seg_t1_sec: float,
    seg_text: str,
) -> List[WhisperVulkanWord]:
    import _pywhispercpp as pw

    n_tok = pw.whisper_full_n_tokens(ctx, seg_idx)
    eot = pw.whisper_token_eot(ctx)
    utf8_tokens: List[Dict[str, Any]] = []
    pending_bytes = b""
    pending_start: Optional[float] = None
    pending_probs: List[float] = []

    for j in range(n_tok):
        tid = pw.whisper_full_get_token_id(ctx, seg_idx, j)
        if tid >= eot:
            continue
        td = pw.whisper_full_get_token_data(ctx, seg_idx, j)
        tb = pw.whisper_token_to_bytes(ctx, tid)
        t0 = max(seg_t0_sec, float(td.t0) * 0.01)
        t1 = max(t0, float(td.t1) * 0.01)
        if pending_start is None:
            pending_start = t0
        pending_bytes += tb
        pending_probs.append(float(td.p))
        try:
            decoded = pending_bytes.decode("utf-8")
            avg_p = sum(pending_probs) / max(len(pending_probs), 1)
            utf8_tokens.append({
                "word": decoded,
                "start": pending_start,
                "end": t1,
                "probability": avg_p,
            })
            pending_bytes = b""
            pending_start = None
            pending_probs = []
        except UnicodeDecodeError:
            pass

    if pending_bytes:
        decoded = pending_bytes.decode("utf-8", errors="replace")
        utf8_tokens.append({
            "word": decoded,
            "start": pending_start if pending_start is not None else seg_t0_sec,
            "end": seg_t1_sec,
            "probability": 1.0,
        })

    # Merge subword BPE tokens into whole words
    merged: List[WhisperVulkanWord] = []
    for tok in utf8_tokens:
        w = tok["word"]
        if not w:
            continue
        is_cjk = any(
            "\u4e00" <= ch <= "\u9fff"
            or "\u3040" <= ch <= "\u30ff"
            or "\uac00" <= ch <= "\ud7af"
            for ch in w
        )
        prev_is_cjk = bool(merged) and any(
            "\u4e00" <= ch <= "\u9fff"
            or "\u3040" <= ch <= "\u30ff"
            or "\uac00" <= ch <= "\ud7af"
            for ch in merged[-1].word
        )
        is_punc_only = bool(w.strip()) and all(ch in _PUNC_CHARS for ch in w.strip())
        if merged and (is_punc_only or (not w.startswith(" ") and not is_cjk and not prev_is_cjk)):
            merged[-1].word += w
            merged[-1].end = max(merged[-1].end, float(tok["end"]))
        else:
            merged.append(
                WhisperVulkanWord(
                    word=w,
                    start=float(tok["start"]),
                    end=float(tok["end"]),
                    probability=float(tok["probability"]),
                )
            )

    if not merged and seg_text.strip():
        merged.append(
            WhisperVulkanWord(
                word=seg_text.strip(),
                start=seg_t0_sec,
                end=seg_t1_sec,
                probability=1.0,
            )
        )
    return merged


class PyWhisperCppModel:
    """
    Drop-in replacement for `faster_whisper.WhisperModel` backed by `pywhispercpp` (ggml-vulkan / CPU).
    """

    def __init__(
        self,
        model_size_or_path: str,
        device: str = "auto",
        device_index: int = 0,
        compute_type: str = "default",
        model_name: Optional[str] = None,
        is_cuda: bool = False,
        **kwargs,
    ):
        from pywhispercpp.model import Model

        self.device = str(device or "auto").strip().lower()
        self.compute_type = compute_type
        self.model_name = model_name or model_size_or_path

        # Resolve GGML .bin model path
        candidate_path = Path(model_size_or_path)
        if candidate_path.is_file() and candidate_path.suffix == ".bin" and candidate_path.name.startswith("ggml-"):
            self.ggml_path = str(candidate_path)
        else:
            # Infer model_name if model_size_or_path is a faster-whisper directory
            inferred_name = self.model_name
            if not get_ggml_model_info(inferred_name):
                base = candidate_path.name
                for k, v in _STANDARD_GGML_MODELS.items():
                    if base.endswith(f"-{k}"):
                        inferred_name = k
                        break
            self.ggml_path = ensure_ggml_whisper_model(inferred_name)

        # Determine whether to use Vulkan GPU acceleration
        if self.device == "cpu":
            self.use_gpu = False
            self.gpu_device = 0
        elif self.device.startswith("vulkan"):
            self.use_gpu = True
            self.gpu_device = get_vulkan_device_index(self.device)
        elif is_cuda or (self.device in ("auto", "cuda") and is_vulkan_available()):
            self.use_gpu = is_vulkan_available()
            self.gpu_device = get_vulkan_device_index(self.device)
        else:
            self.use_gpu = False
            self.gpu_device = 0

        self.n_threads = max(1, min(8, (os.cpu_count() or 4) // 2))
        logger.debug(
            f"[PyWhisperCppModel] Loading {self.ggml_path} (use_gpu={self.use_gpu}, "
            f"vulkan_device={self.gpu_device}, threads={self.n_threads})"
        )
        self._model = Model(
            self.ggml_path,
            params_sampling_strategy=1,
            context_params={
                "use_gpu": self.use_gpu,
                "gpu_device": self.gpu_device,
                "flash_attn": True,
            },
            n_threads=self.n_threads,
            print_progress=False,
            print_realtime=False,
        )

    def transcribe(
        self,
        audio: Union[str, Path, np.ndarray],
        language: Optional[str] = None,
        beam_size: int = 5,
        best_of: int = 5,
        temperature: Union[float, List[float], Tuple[float, ...], None] = 0.0,
        compression_ratio_threshold: Optional[float] = 2.4,
        no_speech_threshold: Optional[float] = 0.6,
        condition_on_previous_text: bool = False,
        initial_prompt: Optional[str] = None,
        hotwords: Optional[str] = None,
        word_timestamps: bool = True,
        vad_filter: bool = True,
        vad_parameters: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Tuple[List[WhisperVulkanSegment], WhisperVulkanInfo]:
        import _pywhispercpp as pw
        from faster_whisper.audio import decode_audio
        from faster_whisper.vad import SpeechTimestampsMap, VadOptions, collect_chunks, get_speech_timestamps

        if isinstance(audio, np.ndarray):
            audio_arr = audio.astype(np.float32, copy=False)
        else:
            audio_arr = decode_audio(str(audio), sampling_rate=16000)

        sampling_rate = 16000
        duration = float(len(audio_arr)) / sampling_rate
        duration_after_vad = duration
        ts_map: Optional[SpeechTimestampsMap] = None
        vad_audio = audio_arr

        if vad_filter and len(audio_arr) > 0:
            vad_kwargs: Dict[str, Any] = {}
            if isinstance(vad_parameters, dict):
                valid_keys = {
                    "threshold",
                    "neg_threshold",
                    "min_speech_duration_ms",
                    "max_speech_duration_s",
                    "min_silence_duration_ms",
                    "speech_pad_ms",
                }
                for k, v in vad_parameters.items():
                    if k in valid_keys and v is not None:
                        vad_kwargs[k] = v
            vad_opts = VadOptions(**vad_kwargs)
            speech_chunks = get_speech_timestamps(audio_arr, vad_opts, sampling_rate=sampling_rate)
            duration_after_vad = sum(c["end"] - c["start"] for c in speech_chunks) / float(sampling_rate)
            if not speech_chunks:
                return [], WhisperVulkanInfo(
                    language=language or "en",
                    language_probability=1.0,
                    duration=duration,
                    duration_after_vad=0.0,
                )
            audio_chunks, _ = collect_chunks(audio_arr, speech_chunks, sampling_rate=sampling_rate)
            vad_audio = (
                np.concatenate([c for c in audio_chunks if len(c) > 0])
                if audio_chunks
                else np.array([], dtype=np.float32)
            )
            ts_map = SpeechTimestampsMap(speech_chunks, sampling_rate=sampling_rate)

        if len(vad_audio) == 0:
            return [], WhisperVulkanInfo(
                language=language or "en",
                language_probability=1.0,
                duration=duration,
                duration_after_vad=0.0,
            )

        # Resolve or auto-detect language
        lang_prob = 1.0
        lang_code = (language or "").strip().lower()
        if lang_code in ("", "auto"):
            if pw.whisper_is_multilingual(self._model._ctx):
                try:
                    sample_slice = vad_audio[: min(len(vad_audio), sampling_rate * 30)]
                    (detected_lang, det_prob), _ = self._model.auto_detect_language(
                        sample_slice, n_threads=self.n_threads
                    )
                    lang_code = detected_lang or "en"
                    lang_prob = float(det_prob)
                except Exception as e:
                    logger.warning(f"[PyWhisperCppModel] auto_detect_language fallback to auto: {e}")
                    lang_code = "auto"
            else:
                lang_code = "en"
        else:
            lang_code = lang_code.split("-")[0]
            if lang_code == "fil":
                lang_code = "tl"

        # Temperature & decoding strategy
        if isinstance(temperature, (list, tuple)) and len(temperature) > 0:
            temp_0 = float(temperature[0])
            temp_inc = float(temperature[1] - temperature[0]) if len(temperature) > 1 else 0.2
        elif temperature is not None:
            temp_0 = float(temperature)
            temp_inc = 0.2
        else:
            temp_0 = 0.0
            temp_inc = 0.2

        prompt_str = (initial_prompt or "").strip()
        if hotwords:
            hw_str = str(hotwords).strip()
            if hw_str:
                prompt_str = f"{prompt_str} {hw_str}".strip() if prompt_str else hw_str

        if int(beam_size or 1) > 1:
            self._model._params.strategy = pw.whisper_sampling_strategy.WHISPER_SAMPLING_BEAM_SEARCH
        else:
            self._model._params.strategy = pw.whisper_sampling_strategy.WHISPER_SAMPLING_GREEDY

        decode_params: Dict[str, Any] = {
            "language": "" if lang_code == "auto" else lang_code,
            "detect_language": False,
            "no_context": not bool(condition_on_previous_text),
            "token_timestamps": bool(word_timestamps),
            "temperature": temp_0,
            "temperature_inc": max(0.0, temp_inc),
            "no_speech_thold": float(no_speech_threshold if no_speech_threshold is not None else 0.6),
            "entropy_thold": float(compression_ratio_threshold if compression_ratio_threshold is not None else 2.4),
            "beam_search": {"beam_size": int(beam_size or 5), "patience": -1.0},
            "greedy": {"best_of": int(best_of or 5)},
            "n_threads": self.n_threads,
            "print_progress": False,
            "print_realtime": False,
        }
        if prompt_str:
            decode_params["initial_prompt"] = prompt_str

        raw_segments = self._model.transcribe(vad_audio, **decode_params)
        ctx = self._model._ctx

        if lang_code in ("", "auto"):
            try:
                lid = pw.whisper_full_lang_id(ctx)
                if lid >= 0:
                    lang_code = pw.whisper_lang_str(lid) or "en"
            except Exception:
                lang_code = "en"

        segments_out: List[WhisperVulkanSegment] = []
        for idx, seg in enumerate(raw_segments):
            text = (seg.text or "").strip()
            if not text:
                continue
            seg_t0 = float(seg.t0) * 0.01
            seg_t1 = max(seg_t0, float(seg.t1) * 0.01)

            if word_timestamps:
                words = _extract_words_from_segment(ctx, idx, seg_t0, seg_t1, text)
            else:
                words = [WhisperVulkanWord(word=text, start=seg_t0, end=seg_t1)]

            if ts_map is not None:
                for w in words:
                    orig_s = ts_map.get_original_time(w.start)
                    orig_e = ts_map.get_original_time(w.end, is_end=True)
                    w.start = orig_s
                    w.end = max(orig_s, orig_e)
                seg_start = words[0].start if words else ts_map.get_original_time(seg_t0)
                seg_end = words[-1].end if words else max(seg_start, ts_map.get_original_time(seg_t1, is_end=True))
            else:
                seg_start = seg_t0
                seg_end = seg_t1

            segments_out.append(
                WhisperVulkanSegment(
                    text=text,
                    start=seg_start,
                    end=seg_end,
                    words=words,
                )
            )

        info = WhisperVulkanInfo(
            language=lang_code or "en",
            language_probability=lang_prob,
            duration=duration,
            duration_after_vad=duration_after_vad,
        )
        return segments_out, info

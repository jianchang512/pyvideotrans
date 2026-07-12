
import torch
import torch.nn as nn
import sys
import os
from typing import Optional, Tuple
import torchaudio

AMPHION_PATH = os.path.join(os.path.dirname(__file__), "../../external/Amphion")
if AMPHION_PATH not in sys.path:
    sys.path.insert(0, AMPHION_PATH)


class SemanticExtractor(nn.Module):
    """Extract semantic features from audio using Wav2Vec2-BERT.

    Args:
        model_path: Path or HuggingFace model name (e.g., "facebook/w2v-bert-2.0")
        device: Device for inference ("cuda" or "cpu")
        sample_rate: Target sample rate for audio (16000 for Wav2Vec2-BERT)
    """
    def __init__(
        self,
        model_path: str,
        device: str = "cuda",
        sample_rate: int = 16000,
    ):
        super().__init__()

        try:
            from transformers import SeamlessM4TFeatureExtractor, Wav2Vec2BertModel
        except ImportError:
            raise ImportError(
                f"Cannot import Amphion MaskGCT. Make sure it's available at {AMPHION_PATH}"
            )

        self.device = device
        self.sample_rate = sample_rate

        hf_name = model_path if model_path else "facebook/w2v-bert-2.0"
        self.processor = SeamlessM4TFeatureExtractor.from_pretrained(hf_name)
        self.model = Wav2Vec2BertModel.from_pretrained(hf_name)
        self.model.eval()
        self.model.to(device)
        self.semantic_mean = None
        self.semantic_std = None

    @torch.no_grad()
    def extract(
        self,
        audio: torch.Tensor,
        audio_sr: Optional[int] = None,
    ) -> torch.Tensor:
        """Extract semantic features from audio tensor.

        Args:
            audio: Audio waveform, shape (C, T) or (T,)
            audio_sr: Audio sample rate (resamples if different from target)

        Returns:
            Normalized semantic features from layer 17, shape (1, T_feat, D)
        """
        if audio.dim() == 1:
            audio = audio.unsqueeze(0)

        if audio_sr is not None and audio_sr != self.sample_rate:
            audio = torchaudio.functional.resample(
                audio,
                orig_freq=audio_sr,
                new_freq=self.sample_rate,
            )

        audio = audio.to(self.device)

        inputs = self.processor(audio.squeeze(0).cpu().numpy(), sampling_rate=self.sample_rate, return_tensors="pt")
        input_features = inputs["input_features"][0].to(self.device)
        attention_mask = inputs["attention_mask"][0].to(self.device)

        vq_emb = self.model(input_features=input_features, attention_mask=attention_mask, output_hidden_states=True)
        feat = vq_emb.hidden_states[17]  # Layer 17 semantic features
        if self.semantic_mean is not None and self.semantic_std is not None:
            feat = (feat - self.semantic_mean.to(feat)) / self.semantic_std.to(feat)
        return feat

    @torch.no_grad()
    def extract_from_file(
        self,
        audio_path: str,
    ) -> torch.Tensor:
        """Extract semantic features from audio file.

        Args:
            audio_path: Path to audio file

        Returns:
            Normalized semantic features, shape (1, T_feat, D)
        """
        audio, sr = torchaudio.load(audio_path)

        # Convert stereo to mono if needed
        if audio.shape[0] > 1:
            audio = audio.mean(dim=0, keepdim=True)

        return self.extract(audio.squeeze(0), audio_sr=sr)


class SemanticCodec(nn.Module):
    def __init__(
        self,
        semantic_model_path: str,
        codec_model_path: str,
        device: str = "cuda",
        sample_rate: int = 16000,
    ):
        super().__init__()

        try:
            from models.tts.maskgct.maskgct_utils import build_semantic_codec
        except ImportError:
            raise ImportError(
                f"Cannot import Amphion MaskGCT codec. Make sure it's available at {AMPHION_PATH}"
            )

        self.device = device
        self.sample_rate = sample_rate

        self.semantic_extractor = SemanticExtractor(
            semantic_model_path,
            device=device,
            sample_rate=sample_rate,
        )

        cfg = torch.load(codec_model_path, map_location=device)
        self.codec_model = build_semantic_codec(cfg["cfg"], device)
        self.codec_model.load_state_dict(cfg["model"])
        self.codec_model.eval()

    @torch.no_grad()
    def encode(
        self,
        audio: torch.Tensor,
        audio_sr: Optional[int] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        semantic_features = self.semantic_extractor.extract(audio, audio_sr)

        semantic_codes = self.codec_model.encode(semantic_features)

        return semantic_codes, semantic_features

    @torch.no_grad()
    def encode_from_file(
        self,
        audio_path: str,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        audio, sr = torchaudio.load(audio_path)

        if audio.shape[0] > 1:
            audio = audio.mean(dim=0, keepdim=True)

        return self.encode(audio.squeeze(0), audio_sr=sr)


def load_semantic_extractor(
    model_path: str,
    device: str = "cuda",
    sample_rate: int = 16000,
) -> SemanticExtractor:
    return SemanticExtractor(model_path, device, sample_rate)


def load_semantic_codec(
    semantic_model_path: str,
    codec_model_path: str,
    device: str = "cuda",
    sample_rate: int = 16000,
) -> SemanticCodec:
    return SemanticCodec(
        semantic_model_path,
        codec_model_path,
        device,
        sample_rate,
    )

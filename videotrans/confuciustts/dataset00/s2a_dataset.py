import os
import random
from typing import Dict, List, Optional

import numpy as np
import torch
import torchaudio
from datasets import load_dataset
from pytorch_lightning import LightningDataModule
from torch.nn.utils.rnn import pad_sequence
from torch.utils.data import DataLoader, Dataset, DistributedSampler
import torch.distributed as dist
from transformers import AutoTokenizer, SeamlessM4TFeatureExtractor

from videotrans.confuciustts.utils.text_utils import get_language_token, to_katakana
from videotrans.confuciustts.utils.audio_features import extract_fbank, extract_mel


os.environ["TOKENIZERS_PARALLELISM"] = "false"

MAX_PROMPT_AUDIO_DURATION_SEC = 15


class S2ADataset(Dataset):
    """Dataset for Semantic-to-Audio model training.

    Loads semantic tokens, mel-spectrograms, and LLM latent features for
    training the flow matching model. Performs language-balanced sampling.

    Args:
        data_path: List of TSV file paths
        tokenizer: Text tokenizer
        w2v_bert_path: Wav2Vec2-BERT model path for semantic features
        max_text_seq_len: Maximum text sequence length
        max_semantic_seq_len: Maximum semantic token sequence length
        semantic_pad_token: Padding token for semantic sequence
        target_sample_rate: Sample rate for mel-spectrogram extraction
        prompt_sample_rate: Sample rate for prompt audio
        n_fft: FFT size for mel-spectrogram
        win_length: Window length
        hop_length: Hop length
        n_mels: Number of mel bins
    """

    def __init__(
        self,
        data_path: List[str],
        tokenizer: AutoTokenizer,
        w2v_bert_path: str,
        max_text_seq_len: int = 520,
        max_semantic_seq_len: int = 1520,
        semantic_pad_token: int = 0,
        target_sample_rate: int = 22050,
        prompt_sample_rate: int = 16000,
        n_fft: int = 1024,
        win_length: int = 1024,
        hop_length: int = 256,
        n_mels: int = 80,
    ):
        super().__init__()
        self.tokenizer = tokenizer
        self.text_pad_token = getattr(tokenizer, "pad_token_id", 0) if tokenizer.pad_token_id is not None else 0
        self.vocab_size = len(tokenizer)
        self.w2v_bert_path = w2v_bert_path
        self.max_text_seq_len = max_text_seq_len
        self.max_semantic_seq_len = max_semantic_seq_len
        self.semantic_pad_token = semantic_pad_token
        self.target_sample_rate = target_sample_rate
        self.prompt_sample_rate = prompt_sample_rate
        self.n_fft = n_fft
        self.win_length = win_length
        self.hop_length = hop_length
        self.n_mels = n_mels
        self.column_names = ["lang", "wav_path", "norm_text", "semantic_ids_path", "ref_audio_paths"]
        self.data_list = [self._load_data_file(path) for path in data_path]
        self.num_langs = len(self.data_list)
        self.extract_features = SeamlessM4TFeatureExtractor.from_pretrained(w2v_bert_path)

    def _load_data_file(self, path: str):
        try:
            return load_dataset(
                "csv",
                data_files=path,
                delimiter="\t",
                column_names=self.column_names,
                split="train",
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load data from {path}: {e}")

    def __len__(self) -> int:
        return max(len(data) for data in self.data_list) * self.num_langs

    def _get_random_sample(self) -> Dict:
        return self[random.randint(0, len(self) - 1)]

    def __getitem__(self, idx: int) -> Dict:
        try:
            lang_idx = idx % self.num_langs
            data = self.data_list[lang_idx]
            data_idx = (idx // self.num_langs) % len(data)

            sample = data[data_idx]
            lang = sample["lang"]
            wav_path = sample["wav_path"]
            norm_text = sample["norm_text"]
            semantic_ids_path = sample["semantic_ids_path"]
            ref_audio_paths_str = sample["ref_audio_paths"]

            semantic_token = np.load(semantic_ids_path)
            semantic_len = len(semantic_token)
            if semantic_len == 0 or semantic_len > self.max_semantic_seq_len:
                raise ValueError(f"Invalid semantic length: {semantic_len}")

            if lang == "ja":
                norm_text = to_katakana(norm_text)

            lang_token = get_language_token(lang)
            full_text = f"You are a helpful assistant. {lang_token}:{norm_text}"
            text_ids = self.tokenizer.encode(full_text)

            if len(text_ids) >= self.max_text_seq_len:
                raise ValueError(f"Invalid text length: {len(text_ids)}")
            if max(text_ids) >= self.vocab_size:
                raise ValueError(f"Invalid text token ids: max={max(text_ids)}")

            ref_candidates = ref_audio_paths_str.split(",")
            ref_audio_path = random.choice(ref_candidates)

            prompt_audio, sr = torchaudio.load(ref_audio_path)

            if sr != self.prompt_sample_rate:
                prompt_audio = torchaudio.functional.resample(prompt_audio, sr, self.prompt_sample_rate)

            prompt_audio_len = prompt_audio.size(1)

            max_prompt_samples = MAX_PROMPT_AUDIO_DURATION_SEC * self.prompt_sample_rate
            if prompt_audio_len > max_prompt_samples:
                max_start = prompt_audio_len - max_prompt_samples
                start = random.randint(0, max_start)
                prompt_audio = prompt_audio[:, start:start + max_prompt_samples]
                prompt_audio_len = max_prompt_samples

            target_audio, target_sr = torchaudio.load(wav_path)
            if target_sr < self.target_sample_rate:
                raise ValueError(f"Unsupported sample rate: {target_sr}")
            target_audio = target_audio.mean(dim=0, keepdim=True)

            if target_sr != self.target_sample_rate:
                target_audio_22k = torchaudio.functional.resample(target_audio, target_sr, self.target_sample_rate)
            else:
                target_audio_22k = target_audio

            target_mel = extract_mel(
                target_audio_22k,
                sample_rate=self.target_sample_rate,
                n_fft=self.n_fft,
                win_length=self.win_length,
                hop_length=self.hop_length,
                n_mels=self.n_mels,
            )

            if target_sr != self.prompt_sample_rate:
                target_audio_16k = torchaudio.functional.resample(target_audio, target_sr, self.prompt_sample_rate)
            else:
                target_audio_16k = target_audio
            max_samples_16k = MAX_PROMPT_AUDIO_DURATION_SEC * self.prompt_sample_rate
            if target_audio_16k.size(1) > max_samples_16k:
                start = random.randint(0, target_audio_16k.size(1) - max_samples_16k)
                target_audio_16k = target_audio_16k[:, start:start + max_samples_16k]
            campplus_feat = extract_fbank(target_audio_16k, sample_rate=self.prompt_sample_rate, n_mels=self.n_mels)

            return {
                "text_ids": text_ids,
                "text_ids_len": len(text_ids),
                "semantic_token": semantic_token,
                "semantic_token_len": semantic_len,
                "target_mel": target_mel,
                "target_mel_len": target_mel.size(0),
                "campplus_feat": campplus_feat,
                "campplus_feat_len": campplus_feat.size(0),
                "prompt_audio": prompt_audio,
                "prompt_audio_len": prompt_audio_len,
            }
        except Exception:
            return self._get_random_sample()

    def collate(self, examples: List[Dict]) -> Dict[str, torch.Tensor]:
        text_tokens = [torch.tensor(ex["text_ids"], dtype=torch.long) for ex in examples]
        text_lengths = torch.tensor([ex["text_ids_len"] for ex in examples], dtype=torch.long)
        text_inputs = pad_sequence(text_tokens, batch_first=True, padding_value=self.text_pad_token)

        semantic_tokens = [torch.tensor(ex["semantic_token"], dtype=torch.long) for ex in examples]
        semantic_token_len = torch.tensor([ex["semantic_token_len"] for ex in examples], dtype=torch.long)
        semantic_token = pad_sequence(semantic_tokens, batch_first=True, padding_value=self.semantic_pad_token)

        target_mels = [ex["target_mel"] for ex in examples]
        target_mel_len = torch.tensor([ex["target_mel_len"] for ex in examples], dtype=torch.long)
        target_mel = pad_sequence(target_mels, batch_first=True, padding_value=0.0)

        campplus_feats = [ex["campplus_feat"] for ex in examples]
        campplus_feat_len = torch.tensor([ex["campplus_feat_len"] for ex in examples], dtype=torch.long)
        campplus_feat = pad_sequence(campplus_feats, batch_first=True, padding_value=0.0)

        spk_audio_list = [ex["prompt_audio"].squeeze().numpy() for ex in examples]
        spk_inputs = self.extract_features(
            spk_audio_list,
            sampling_rate=self.prompt_sample_rate,
            return_tensors="pt"
        )
        prompt_audio_len = torch.tensor([ex["prompt_audio_len"] for ex in examples], dtype=torch.long)

        return {
            "text_inputs": text_inputs,
            "text_lengths": text_lengths,
            "semantic_token": semantic_token,
            "semantic_token_len": semantic_token_len,
            "spk_input_features": spk_inputs["input_features"],
            "spk_attention_mask": spk_inputs["attention_mask"],
            "prompt_audio_16k_len": prompt_audio_len,
            "target_mel": target_mel,
            "target_mel_len": target_mel_len,
            "campplus_feat": campplus_feat,
            "campplus_feat_len": campplus_feat_len,
        }


class S2ADataModule(LightningDataModule):
    def __init__(
        self,
        train_data_path: List[str],
        val_data_path: Optional[List[str]],
        tokenizer,
        w2v_bert_path: str,
        batch_size: int = 4,
        num_workers: int = 4,
        max_text_seq_len: int = 520,
        max_semantic_seq_len: int = 1520,
        semantic_pad_token: int = 0,
        target_sample_rate: int = 22050,
        prompt_sample_rate: int = 16000,
        n_fft: int = 1024,
        win_length: int = 1024,
        hop_length: int = 256,
        n_mels: int = 80,
    ):
        super().__init__()
        self.train_data_path = train_data_path
        self.val_data_path = val_data_path or train_data_path
        self.tokenizer = tokenizer
        self.w2v_bert_path = w2v_bert_path
        self.batch_size = batch_size
        self.num_workers = num_workers
        self.max_text_seq_len = max_text_seq_len
        self.max_semantic_seq_len = max_semantic_seq_len
        self.semantic_pad_token = semantic_pad_token
        self.target_sample_rate = target_sample_rate
        self.prompt_sample_rate = prompt_sample_rate
        self.n_fft = n_fft
        self.win_length = win_length
        self.hop_length = hop_length
        self.n_mels = n_mels
        self.train_dataset = None
        self.val_dataset = None

    def setup(self, stage: Optional[str] = None):
        if stage == "fit" or stage is None:
            self.train_dataset = S2ADataset(
                data_path=self.train_data_path,
                tokenizer=self.tokenizer,
                w2v_bert_path=self.w2v_bert_path,
                max_text_seq_len=self.max_text_seq_len,
                max_semantic_seq_len=self.max_semantic_seq_len,
                semantic_pad_token=self.semantic_pad_token,
                target_sample_rate=self.target_sample_rate,
                prompt_sample_rate=self.prompt_sample_rate,
                n_fft=self.n_fft,
                win_length=self.win_length,
                hop_length=self.hop_length,
                n_mels=self.n_mels,
            )
            self.val_dataset = S2ADataset(
                data_path=self.val_data_path,
                tokenizer=self.tokenizer,
                w2v_bert_path=self.w2v_bert_path,
                max_text_seq_len=self.max_text_seq_len,
                max_semantic_seq_len=self.max_semantic_seq_len,
                semantic_pad_token=self.semantic_pad_token,
                target_sample_rate=self.target_sample_rate,
                prompt_sample_rate=self.prompt_sample_rate,
                n_fft=self.n_fft,
                win_length=self.win_length,
                hop_length=self.hop_length,
                n_mels=self.n_mels,
            )

    def train_dataloader(self):
        use_distributed = dist.is_available() and dist.is_initialized()

        if use_distributed:
            sampler = DistributedSampler(self.train_dataset, shuffle=True, drop_last=True)
            shuffle = False
        else:
            sampler = None
            shuffle = True

        return DataLoader(
            self.train_dataset,
            batch_size=self.batch_size,
            sampler=sampler,
            shuffle=shuffle,
            num_workers=self.num_workers,
            collate_fn=self.train_dataset.collate,
            drop_last=True,
        )

    def val_dataloader(self):
        return DataLoader(
            self.val_dataset,
            batch_size=self.batch_size,
            shuffle=False,
            num_workers=self.num_workers,
            collate_fn=self.val_dataset.collate,
            drop_last=False,
        )

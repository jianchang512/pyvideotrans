import os
import random
from typing import Dict, List, Optional

import numpy as np
import torch
import torchaudio
from datasets import load_dataset
from pytorch_lightning import LightningDataModule
from torch.nn.utils.rnn import pad_sequence
from torch.utils.data import Dataset, DistributedSampler
import torch.distributed as dist
from transformers import AutoTokenizer, SeamlessM4TFeatureExtractor

from videotrans.confuciustts.utils.text_utils import get_language_token, to_katakana

os.environ["TOKENIZERS_PARALLELISM"] = "false"

MAX_AUDIO_DURATION_SEC = 30
MAX_PROMPT_AUDIO_DURATION_SEC = 15

IGNORE_INDEX = -100


class T2SDataset(Dataset):
    """Dataset for Text-to-Semantic model training.

    Loads text, audio, and semantic tokens from TSV files. Performs:
    - Text normalization and tokenization
    - Audio loading and semantic feature extraction
    - Language-balanced multi-dataset sampling

    Args:
        data_path: List of TSV file paths (one per language/dataset)
        tokenizer: Text tokenizer for input text
        w2v_bert_path: Path to Wav2Vec2-BERT model for semantic features
        max_text_seq_len: Maximum text sequence length
        max_semantic_seq_len: Maximum semantic token sequence length
        sample_rate: Audio sample rate
        semantic_pad_token: Padding token ID for semantic sequence
        start_semantic_token: BOS token ID
        stop_semantic_token: EOS token ID
    """

    def __init__(
        self,
        data_path: List[str],
        tokenizer: AutoTokenizer,
        w2v_bert_path: str,
        max_text_seq_len: int = 520,
        max_semantic_seq_len: int = 1520,
        sample_rate: int = 16000,
        semantic_pad_token: int = 8193,
        start_semantic_token: int = 8192,
        stop_semantic_token: int = 8193,
    ) -> None:
        super().__init__()

        self.sample_rate = sample_rate
        self.max_text_seq_len = max_text_seq_len
        self.max_semantic_seq_len = max_semantic_seq_len
        self.semantic_pad_token = semantic_pad_token
        self.start_semantic_token = start_semantic_token
        self.stop_semantic_token = stop_semantic_token

        self.tokenizer = tokenizer
        self.text_pad_token = getattr(tokenizer, "pad_token_id", 0) if tokenizer.pad_token_id is not None else 0
        self.vocab_size = len(tokenizer)

        self.extract_features = SeamlessM4TFeatureExtractor.from_pretrained(
            w2v_bert_path,
        )

        self.column_names = ["lang", "wav_path", "norm_text", "semantic_ids_path", "ref_audio_paths"]
        self.data_list = [self._load_data_file(p) for p in data_path]
        self.num_langs = len(self.data_list)

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
        random_idx = random.randint(0, len(self) - 1)
        return self[random_idx]

    def __getitem__(self, idx: int) -> Dict:
        try:
            lang_idx = idx % self.num_langs
            data = self.data_list[lang_idx]
            data_idx = (idx // self.num_langs) % len(data)

            sample = data[data_idx]
            lang = sample["lang"]
            norm_text = sample["norm_text"]
            semantic_ids_path = sample["semantic_ids_path"]
            ref_audio_paths_str = sample["ref_audio_paths"]

            semantic_codes = np.load(semantic_ids_path)
            semantic_len = len(semantic_codes)
            if semantic_len == 0 or semantic_len > self.max_semantic_seq_len:
                raise ValueError(f"Invalid semantic length: {semantic_len}")

            if lang == "ja":
                norm_text = to_katakana(norm_text)

            lang_token = get_language_token(lang)
            full_text = f"You are a helpful assistant. {lang_token}:{norm_text}"
            text_inputs = self.tokenizer.encode(full_text)

            if len(text_inputs) >= self.max_text_seq_len:
                raise ValueError(f"Invalid text length: {len(text_inputs)}")
            if max(text_inputs) >= self.vocab_size:
                raise ValueError(f"Invalid text token ids: max={max(text_inputs)}")

            ref_candidates = ref_audio_paths_str.split(",")
            ref_audio_path = random.choice(ref_candidates)

            prompt_audio, sr = torchaudio.load(ref_audio_path)

            if sr != self.sample_rate:
                prompt_audio = torchaudio.functional.resample(prompt_audio, sr, self.sample_rate)

            prompt_audio_len = prompt_audio.size(1)

            max_prompt_samples = MAX_PROMPT_AUDIO_DURATION_SEC * self.sample_rate
            if prompt_audio_len > max_prompt_samples:
                max_start = prompt_audio_len - max_prompt_samples
                start = random.randint(0, max_start)
                prompt_audio = prompt_audio[:, start:start + max_prompt_samples]
                prompt_audio_len = max_prompt_samples

            return {
                "text_inputs": text_inputs,
                "text_inputs_len": len(text_inputs),
                "semantic_codes": semantic_codes,
                "semantic_codes_len": semantic_len,
                "prompt_audio": prompt_audio,
                "prompt_audio_len": prompt_audio_len,
            }

        except Exception:
            return self._get_random_sample()

    def collate(self, examples: List[Dict]) -> Dict[str, torch.Tensor]:
        text_tokens = [torch.tensor(ex["text_inputs"], dtype=torch.long) for ex in examples]
        text_lengths = torch.tensor([ex["text_inputs_len"] for ex in examples], dtype=torch.long)
        
        text_inputs = pad_sequence(text_tokens, batch_first=True, padding_value=self.text_pad_token)

        semantic_inputs_list = []
        semantic_targets_list = []
        semantic_lengths_list = []

        for ex in examples:
            s_codes = torch.tensor(ex["semantic_codes"], dtype=torch.long)
            semantic_lengths_list.append(ex["semantic_codes_len"])

            si = torch.cat([
                torch.tensor([self.start_semantic_token]),
                s_codes,
                torch.tensor([self.stop_semantic_token])
            ])
            
            st = torch.cat([
                s_codes,
                torch.tensor([self.stop_semantic_token, IGNORE_INDEX])
            ])

            semantic_inputs_list.append(si)
            semantic_targets_list.append(st)

        semantic_lengths = torch.tensor(semantic_lengths_list, dtype=torch.long)
        semantic_codes = pad_sequence(semantic_inputs_list, batch_first=True, padding_value=self.semantic_pad_token)
        semantic_targets = pad_sequence(semantic_targets_list, batch_first=True, padding_value=IGNORE_INDEX)

        batch_size = len(examples)
        cond_mask = torch.ones(batch_size, 1, dtype=torch.bool)

        text_seq_range = torch.arange(text_inputs.shape[1]).unsqueeze(0)
        text_attn_mask = text_seq_range < text_lengths.unsqueeze(1)

        semantic_seq_range = torch.arange(semantic_codes.shape[1]).unsqueeze(0)
        semantic_attn_mask = semantic_seq_range < (semantic_lengths + 2).unsqueeze(1)

        attention_mask = torch.cat([cond_mask, text_attn_mask, semantic_attn_mask], dim=1)

        spk_audio_list = [ex["prompt_audio"].squeeze().numpy() for ex in examples]
        spk_inputs = self.extract_features(
            spk_audio_list,
            sampling_rate=self.sample_rate,
            return_tensors="pt"
        )

        return {
            "text_inputs": text_inputs,
            "text_lengths": text_lengths,
            "semantic_codes": semantic_codes,
            "semantic_targets": semantic_targets,
            "semantic_lengths": semantic_lengths,
            "spk_input_features": spk_inputs["input_features"],
            "attention_mask": attention_mask,
            "spk_attention_mask": spk_inputs["attention_mask"],
        }


class T2SDataModule(LightningDataModule):
    def __init__(
        self,
        train_data_path: List[str],
        val_data_path: Optional[List[str]],
        tokenizer,
        w2v_bert_path: str,
        batch_size: int = 16,
        num_workers: int = 4,
        max_text_seq_len: int = 520,
        max_semantic_seq_len: int = 1520,
        sample_rate: int = 16000,
        semantic_pad_token: int = 8193,
        start_semantic_token: int = 8192,
        stop_semantic_token: int = 8193,
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
        self.sample_rate = sample_rate
        self.semantic_pad_token = semantic_pad_token
        self.start_semantic_token = start_semantic_token
        self.stop_semantic_token = stop_semantic_token

        self.train_dataset = None
        self.val_dataset = None

    def setup(self, stage: Optional[str] = None):
        if stage == "fit" or stage is None:
            self.train_dataset = T2SDataset(
                data_path=self.train_data_path,
                tokenizer=self.tokenizer,
                w2v_bert_path=self.w2v_bert_path,
                max_text_seq_len=self.max_text_seq_len,
                max_semantic_seq_len=self.max_semantic_seq_len,
                sample_rate=self.sample_rate,
                semantic_pad_token=self.semantic_pad_token,
                start_semantic_token=self.start_semantic_token,
                stop_semantic_token=self.stop_semantic_token,
            )

            self.val_dataset = T2SDataset(
                data_path=self.val_data_path,
                tokenizer=self.tokenizer,
                w2v_bert_path=self.w2v_bert_path,
                max_text_seq_len=self.max_text_seq_len,
                max_semantic_seq_len=self.max_semantic_seq_len,
                sample_rate=self.sample_rate,
                semantic_pad_token=self.semantic_pad_token,
                start_semantic_token=self.start_semantic_token,
                stop_semantic_token=self.stop_semantic_token,
            )

    def train_dataloader(self):
        from torch.utils.data import DataLoader

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
        from torch.utils.data import DataLoader
        return DataLoader(
            self.val_dataset,
            batch_size=self.batch_size,
            shuffle=False,
            num_workers=self.num_workers,
            collate_fn=self.val_dataset.collate,
            drop_last=False,
        )

import importlib
import os
from typing import Any, Dict

import pytorch_lightning as L
import safetensors.torch
import torch
from pytorch_lightning.utilities.rank_zero import rank_zero_info
from ema_pytorch import EMA

from videotrans.confuciustts.flow.flow import MaskedDiffWithXvec
from videotrans.confuciustts.frontend.semantic_extractor import load_semantic_extractor
from videotrans.confuciustts.llm.llm import Text2Semantic, Text2SemanticConfig
from videotrans.confuciustts.utils.train_utils import get_optimizer, get_scheduler


def _instantiate_class(target: str, **kwargs):
    """Instantiate a class from module path string.

    Args:
        target: Full module path (e.g., "module.submodule.ClassName")
        **kwargs: Arguments to pass to class constructor

    Returns:
        Instance of the class
    """
    module_name, class_name = target.rsplit(".", 1)
    cls = getattr(importlib.import_module(module_name), class_name)
    return cls(**kwargs)


def _build_s2a_model(model_config: Dict[str, Any]) -> MaskedDiffWithXvec:
    """Build S2A model from configuration dict.

    Args:
        model_config: Model architecture parameters

    Returns:
        Instantiated S2A model
    """
    from videotrans.confuciustts.flow.flow import MaskedDiffWithXvecConfig

    config = MaskedDiffWithXvecConfig(**model_config)
    return MaskedDiffWithXvec(config)


class S2ALightningModule(L.LightningModule):
    """Lightning module for S2A model training.

    Manages the full S2A training pipeline including:
    - Frozen T2S model for LLM latent extraction
    - Frozen semantic and style encoders
    - Flow matching model training with EMA
    - Loss computation and logging

    Args:
        config: Training configuration dict with sections:
            - s2a_model: S2A model architecture parameters
            - t2s_model: T2S model configuration
            - paths: Checkpoint and model paths
            - optimizer: Optimizer configuration
            - scheduler: Learning rate scheduler configuration
            - ema: Exponential moving average parameters
    """
    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        self.save_hyperparameters()
        self.config = config

        self.model = _build_s2a_model(config["s2a_model"])

        s2a_checkpoint = config.get("paths", {}).get("s2a_checkpoint")
        if s2a_checkpoint and os.path.isfile(s2a_checkpoint):
            self._load_s2a_checkpoint(s2a_checkpoint)

        if hasattr(self.model, 'input_embedding'):
            for p in self.model.input_embedding.parameters():
                p.requires_grad = False
            rank_zero_info(">> Frozen input_embedding (semantic token embedding)")
        else:
            rank_zero_info(">> Warning: model does not have input_embedding attribute")

        self._remove_all_weight_norm(self.model)
        rank_zero_info(">> Removed weight_norm from S2A model (required for EMA deepcopy)")

        t2s_config_dict = config.get("t2s_model", {})
        t2s_config = Text2SemanticConfig(**t2s_config_dict)
        self.t2s_model = Text2Semantic(t2s_config)
        t2s_ckpt = config["paths"]["t2s_checkpoint"]
        if t2s_ckpt and os.path.isfile(t2s_ckpt):
            state_dict = safetensors.torch.load_file(t2s_ckpt)
            missing, unexpected = self.t2s_model.load_state_dict(state_dict, strict=False)
            rank_zero_info(
                f">> T2S LM loaded from {t2s_ckpt}: missing={len(missing)} unexpected={len(unexpected)}"
            )
        self.t2s_model.eval()
        for p in self.t2s_model.parameters():
            p.requires_grad = False

        device_str = "cuda" if torch.cuda.is_available() else "cpu"
        self.semantic_extractor = load_semantic_extractor(config["paths"]["w2v_bert_path"], device=device_str)
        self.semantic_extractor.eval()
        for p in self.semantic_extractor.parameters():
            p.requires_grad = False

        w2v_stat_path = config.get("paths", {}).get("w2v_stat")
        if w2v_stat_path and os.path.exists(w2v_stat_path):
            stats = torch.load(w2v_stat_path, map_location="cpu")
            self.register_buffer("semantic_mean", stats["mean"])
            self.register_buffer("semantic_std", torch.sqrt(stats["var"]))
        else:
            self.semantic_mean = None
            self.semantic_std = None

        style_cfg = config["paths"]["style_encoder"]
        style_target = style_cfg["target"]
        style_kwargs = style_cfg.get("init_args", {})
        self.style_encoder = _instantiate_class(style_target, **style_kwargs)
        style_ckpt = style_cfg.get("checkpoint")
        if style_ckpt and os.path.isfile(style_ckpt):
            state = torch.load(style_ckpt, map_location="cpu")
            if isinstance(state, dict) and "state_dict" in state:
                state = state["state_dict"]
            missing, unexpected = self.style_encoder.load_state_dict(state, strict=False)
            rank_zero_info(
                f">> Style encoder loaded from {style_ckpt}: missing={len(missing)} unexpected={len(unexpected)}"
            )
        self.style_encoder.eval()
        for p in self.style_encoder.parameters():
            p.requires_grad = False

        ema_kwargs = config.get('ema', {})
        self.ema_model = EMA(
            self.model,
            beta=ema_kwargs.get('beta', 0.9999),
            update_every=ema_kwargs.get('update_every', 10),
            update_after_step=ema_kwargs.get('update_after_step', 100),
            include_online_model=False,
        )
        rank_zero_info(f">> EMA initialized with beta={ema_kwargs.get('beta', 0.9999)}")

    def _load_s2a_checkpoint(self, path: str) -> None:
        """Load pretrained S2A model weights.

        Args:
            path: Path to checkpoint file
        """
        state = torch.load(path, map_location="cpu")
        state_dict = state.get("state_dict", state) if isinstance(state, dict) else state
        cleaned = {k.replace("model.", "", 1): v for k, v in state_dict.items() if k.startswith("model.")}
        if not cleaned:
            cleaned = state_dict
        missing, unexpected = self.model.load_state_dict(cleaned, strict=False)
        rank_zero_info(
            f">> S2A checkpoint loaded from {path}: missing={len(missing)} unexpected={len(unexpected)}"
        )

    @staticmethod
    def _remove_all_weight_norm(module):
        """Remove weight normalization from all layers (required for EMA).

        Args:
            module: PyTorch module to process
        """
        for name, child in module.named_modules():
            try:
                torch.nn.utils.remove_weight_norm(child)
            except ValueError:
                pass

    def on_fit_start(self) -> None:
        """Setup model caches before training starts."""
        max_batch_size = self.config.get("training", {}).get("max_batch_size", 32)
        max_seq_length = self.config.get("training", {}).get("max_seq_length", 8192)
        if hasattr(self.model.decoder, 'estimator') and hasattr(self.model.decoder.estimator, 'setup_caches'):
            self.model.decoder.estimator.setup_caches(max_batch_size, max_seq_length)
            rank_zero_info(f">> CFM caches setup: batch={max_batch_size}, seq_len={max_seq_length}")

    @torch.no_grad()
    def _speaker_condition(self, spk_input_features: torch.Tensor, spk_attention_mask: torch.Tensor) -> torch.Tensor:
        """Extract normalized semantic features from speaker audio.

        Args:
            spk_input_features: Audio features from SeamlessM4T processor
            spk_attention_mask: Attention mask

        Returns:
            Normalized layer 17 hidden states, shape (B, T, D)
        """
        outputs = self.semantic_extractor.model(
            input_features=spk_input_features,
            attention_mask=spk_attention_mask,
            output_hidden_states=True,
        )
        feat = outputs.hidden_states[17]
        if self.semantic_mean is not None and self.semantic_std is not None:
            feat = (feat - self.semantic_mean.to(feat)) / self.semantic_std.to(feat)
        return feat

    @torch.no_grad()
    def _compute_lm_latent(self, batch: Dict[str, torch.Tensor], condition_vector: torch.Tensor) -> torch.Tensor:
        """Extract LLM hidden states from T2S model.

        Args:
            batch: Batch dict with text_inputs and semantic tokens
            condition_vector: Speaker conditioning features

        Returns:
            LLM latent representations, shape (B, T_sem, D_lm)
        """
        semantic_token = batch["semantic_token"]
        semantic_inputs = torch.cat(
            [
                torch.full((semantic_token.size(0), 1), self.t2s_model.config.start_semantic_token, dtype=semantic_token.dtype, device=semantic_token.device),
                semantic_token,
                torch.full((semantic_token.size(0), 1), self.t2s_model.config.stop_semantic_token, dtype=semantic_token.dtype, device=semantic_token.device),
            ],
            dim=1,
        )
        latent = self.t2s_model(
            text_inputs=batch["text_inputs"],
            text_lengths=batch["text_lengths"],
            semantic_codes=semantic_inputs,
            semantic_lengths=batch["semantic_token_len"],
            condition_vector=condition_vector,
            return_latent=True,
        )
        return latent

    def _shared_step(self, batch: Dict[str, torch.Tensor], stage: str) -> torch.Tensor:
        """Shared training/validation step logic.

        Args:
            batch: Batch dict with all required data
            stage: "train" or "val"

        Returns:
            Flow matching loss
        """
        with torch.no_grad():
            condition_vector = self._speaker_condition(
                batch["spk_input_features"], batch["spk_attention_mask"]
            )
            lm_latent = self._compute_lm_latent(batch, condition_vector)
            style_input = batch["campplus_feat"].to(self.dtype)
            embedding = self.style_encoder(style_input)

        flow_batch = {
            "semantic_token": batch["semantic_token"],
            "semantic_token_len": batch["semantic_token_len"],
            "lm_latent": lm_latent,
            "speech_feat": batch["target_mel"],
            "speech_feat_len": batch["target_mel_len"],
            "embedding": embedding,
        }
        outputs = self.model(flow_batch, device=self.device)
        loss = outputs["loss"]
        self.log(f"{stage}/flow_loss", loss, on_step=stage == "train", on_epoch=True, prog_bar=True, sync_dist=True)
        if stage == "train":
            self.log("lr", self.optimizers().param_groups[0]["lr"], on_step=True, prog_bar=True, sync_dist=True)
        return loss

    def training_step(self, batch: Dict[str, torch.Tensor], batch_idx: int) -> torch.Tensor:
        """Training step.

        Args:
            batch: Training batch
            batch_idx: Batch index

        Returns:
            Training loss
        """
        loss = self._shared_step(batch, "train")
        return loss

    def on_train_batch_end(self, outputs, batch, batch_idx):
        """Update EMA model after each training batch."""
        self.ema_model.update()

    def validation_step(self, batch: Dict[str, torch.Tensor], batch_idx: int) -> torch.Tensor:
        """Validation step.

        Args:
            batch: Validation batch
            batch_idx: Batch index

        Returns:
            Validation loss
        """
        return self._shared_step(batch, "val")

    def on_save_checkpoint(self, checkpoint: Dict[str, Any]) -> None:
        """Save S2A model and EMA weights.

        Args:
            checkpoint: Checkpoint dict to save
        """
        model_state = self.model.state_dict()
        checkpoint["state_dict"] = {f"model.{k}": v for k, v in model_state.items()}
        checkpoint["ema_model_state_dict"] = self.ema_model.state_dict()
        checkpoint.pop("hyper_parameters", None)
        rank_zero_info(f">> Saved checkpoint with {len(checkpoint['state_dict'])} s2a-model parameters + EMA")

    def on_load_checkpoint(self, checkpoint: Dict[str, Any]) -> None:
        """Load S2A model and EMA weights from checkpoint.

        Args:
            checkpoint: Checkpoint dict to load
        """
        state_dict = checkpoint.get("state_dict", {})
        model_keys = {k.replace("model.", "", 1): v for k, v in state_dict.items() if k.startswith("model.")}
        if model_keys:
            missing, unexpected = self.model.load_state_dict(model_keys, strict=False)
            rank_zero_info(
                f">> S2A checkpoint resume: missing={len(missing)} unexpected={len(unexpected)}"
            )
        if "ema_model_state_dict" in checkpoint:
            try:
                self.ema_model.load_state_dict(checkpoint["ema_model_state_dict"])
                rank_zero_info(">> Loaded EMA weights from checkpoint")
            except Exception as e:
                rank_zero_info(f">> Warning: Could not load EMA weights: {e}")
        checkpoint["state_dict"] = self.state_dict()

    def get_ema_model_state_dict(self):
        """Get EMA model state dict for export.

        Returns:
            EMA model state dict
        """
        return self.ema_model.ema_model.state_dict()

    def configure_optimizers(self):
        """Configure optimizer and learning rate scheduler.

        Returns:
            Dict with optimizer and lr_scheduler configuration
        """
        params = [p for p in self.model.parameters() if p.requires_grad]

        optimizer_cfg = self.config.get("optimizer", {})
        rank_zero_info(f">> Optimizer: {len(params)} trainable parameters")

        optimizer = get_optimizer(params, **optimizer_cfg)
        scheduler = get_scheduler(optimizer, **self.config.get("scheduler", {}))
        
        return {
            "optimizer": optimizer,
            "lr_scheduler": {
                "scheduler": scheduler, 
                "interval": "step", 
                "frequency": 1
            },
        }

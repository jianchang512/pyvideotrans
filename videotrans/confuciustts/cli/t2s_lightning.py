import torch
import pytorch_lightning as L
from pytorch_lightning.utilities.rank_zero import rank_zero_info
from typing import Dict, Any
import safetensors.torch
import os

from videotrans.confuciustts.llm.llm import Text2Semantic, Text2SemanticConfig
from videotrans.confuciustts.frontend.semantic_extractor import load_semantic_extractor
from videotrans.confuciustts.utils.train_utils import get_optimizer, get_scheduler


class T2SLightningModule(L.LightningModule):
    """Lightning module for T2S model training.

    Manages the full training pipeline including semantic feature extraction,
    model forward pass, loss computation, and metric logging.

    Args:
        config: Training configuration dict with sections:
            - t2s_model: Model architecture parameters
            - paths: Checkpoint and model paths
            - optimizer: Optimizer configuration
            - scheduler: Learning rate scheduler configuration
    """
    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        self.save_hyperparameters()
        self.config = config

        model_config = Text2SemanticConfig(**config.get("t2s_model", {}))
        self.t2s_model = Text2Semantic(model_config)

        t2s_checkpoint = config.get("paths", {}).get("t2s_checkpoint")
        if t2s_checkpoint and os.path.isfile(t2s_checkpoint):
            rank_zero_info(f">> Loading pretrained T2S weights from: {t2s_checkpoint}")
            state_dict = safetensors.torch.load_file(t2s_checkpoint)
            missing, unexpected = self.t2s_model.load_state_dict(state_dict, strict=False)
            if missing:
                rank_zero_info(f">> T2S pretrained load - missing keys: {len(missing)}")
            if unexpected:
                rank_zero_info(f">> T2S pretrained load - unexpected keys: {len(unexpected)}")
            rank_zero_info(f">> T2S pretrained weights loaded successfully")

        w2v_bert_path = config["paths"]["w2v_bert_path"]
        self.semantic_extractor = load_semantic_extractor(
            w2v_bert_path,
            device="cuda" if torch.cuda.is_available() else "cpu",
        )
        self.semantic_extractor.eval()
        for param in self.semantic_extractor.parameters():
            param.requires_grad = False

        w2v_stat_path = config.get("paths", {}).get("w2v_stat")
        if w2v_stat_path and os.path.exists(w2v_stat_path):
            stats = torch.load(w2v_stat_path)
            self.register_buffer("semantic_mean", stats["mean"])
            self.register_buffer("semantic_std", torch.sqrt(stats["var"]))
            rank_zero_info(f">> Loaded semantic statistics from: {w2v_stat_path}")

    @torch.no_grad()
    def get_semantic_embedding(self, input_features, attention_mask):
        """Extract normalized semantic features from audio.

        Args:
            input_features: Audio features from SeamlessM4T processor
            attention_mask: Attention mask for variable-length audio

        Returns:
            Normalized layer 17 hidden states, shape (B, T, D)
        """
        outputs = self.semantic_extractor.model(
            input_features=input_features,
            attention_mask=attention_mask,
            output_hidden_states=True,
        )

        feat = outputs.hidden_states[17]  # Layer 17 semantic features

        feat = (feat - self.semantic_mean.to(feat.device)) / self.semantic_std.to(feat.device)

        return feat

    def training_step(self, batch: Dict[str, torch.Tensor], batch_idx: int):
        """Training step with teacher forcing.

        Args:
            batch: Batch dict with text_inputs, semantic_codes, etc.
            batch_idx: Batch index

        Returns:
            Training loss
        """
        text_inputs = batch["text_inputs"]
        text_lengths = batch["text_lengths"]
        semantic_codes = batch["semantic_codes"]
        semantic_targets = batch["semantic_targets"]
        semantic_lengths = batch["semantic_lengths"]
        spk_input_features = batch["spk_input_features"]
        spk_attention_mask = batch["spk_attention_mask"]
        attention_mask = batch["attention_mask"]

        with torch.no_grad():
            with torch.cuda.amp.autocast(enabled=True):
                condition_vector = self.get_semantic_embedding(
                    spk_input_features,
                    spk_attention_mask,
                )

        with torch.cuda.amp.autocast(enabled=True):
            outputs = self.t2s_model(
                text_inputs=text_inputs,
                text_lengths=text_lengths,
                semantic_codes=semantic_codes,
                semantic_lengths=semantic_lengths,
                condition_vector=condition_vector,
                attention_mask=attention_mask,
                labels=semantic_targets,
                return_dict=True,
            )

        loss = outputs.loss

        logits = outputs.logits
        predictions = torch.argmax(logits, dim=-1)
        mask = semantic_targets != -100
        correct = (predictions == semantic_targets) & mask
        accuracy = correct.sum().float() / mask.sum().float()

        self.log("train_loss", loss, on_step=True, on_epoch=True, prog_bar=True, sync_dist=True)
        self.log("train_acc", accuracy, on_step=True, on_epoch=True, prog_bar=True, sync_dist=True)
        self.log("lr", self.optimizers().param_groups[0]["lr"], on_step=True, prog_bar=True, sync_dist=True)

        return loss

    def validation_step(self, batch: Dict[str, torch.Tensor], batch_idx: int):
        """Validation step.

        Args:
            batch: Batch dict with text_inputs, semantic_codes, etc.
            batch_idx: Batch index

        Returns:
            Validation loss
        """
        text_inputs = batch["text_inputs"]
        text_lengths = batch["text_lengths"]
        semantic_codes = batch["semantic_codes"]
        semantic_targets = batch["semantic_targets"]
        semantic_lengths = batch["semantic_lengths"]
        spk_input_features = batch["spk_input_features"]
        spk_attention_mask = batch["spk_attention_mask"]
        attention_mask = batch["attention_mask"]

        with torch.no_grad():
            with torch.cuda.amp.autocast(enabled=True):
                condition_vector = self.get_semantic_embedding(
                    spk_input_features,
                    spk_attention_mask,
                )

        with torch.cuda.amp.autocast(enabled=True):
            outputs = self.t2s_model(
                text_inputs=text_inputs,
                text_lengths=text_lengths,
                semantic_codes=semantic_codes,
                semantic_lengths=semantic_lengths,
                condition_vector=condition_vector,
                attention_mask=attention_mask,
                labels=semantic_targets,
            )

        loss = outputs.loss

        logits = outputs.logits
        predictions = torch.argmax(logits, dim=-1)
        mask = semantic_targets != -100
        correct = (predictions == semantic_targets) & mask
        accuracy = correct.sum().float() / mask.sum().float()

        self.log("val_loss", loss, prog_bar=True, on_step=False, on_epoch=True, sync_dist=True)
        self.log("val_acc", accuracy, on_step=False, on_epoch=True, prog_bar=True, sync_dist=True)

        return loss

    def on_save_checkpoint(self, checkpoint):
        """Customize checkpoint saving to only include T2S model weights.

        Args:
            checkpoint: Checkpoint dict to be saved
        """
        t2s_state_dict = self.t2s_model.state_dict()
        checkpoint['state_dict'] = {f't2s_model.{k}': v for k, v in t2s_state_dict.items()}

        keys_to_remove = ['hyper_parameters']
        for key in keys_to_remove:
            if key in checkpoint:
                del checkpoint[key]

        rank_zero_info(f">> Checkpoint saved: {len(checkpoint['state_dict'])} t2s_model parameters")

    def on_load_checkpoint(self, checkpoint):
        """Load T2S model weights from checkpoint.

        Args:
            checkpoint: Checkpoint dict to load from
        """
        state_dict = checkpoint.get('state_dict', {})

        t2s_keys = {k.replace('t2s_model.', ''): v for k, v in state_dict.items() if k.startswith('t2s_model.')}

        if t2s_keys:
            missing, unexpected = self.t2s_model.load_state_dict(t2s_keys, strict=False)
            if missing:
                rank_zero_info(f">> Checkpoint load - Missing keys: {len(missing)}")
            if unexpected:
                rank_zero_info(f">> Checkpoint load - Unexpected keys: {len(unexpected)}")
            rank_zero_info(f">> Loaded checkpoint with {len(t2s_keys)} t2s_model parameters")
        else:
            rank_zero_info(f">> Warning: no t2s_model keys found in checkpoint!")

        checkpoint['state_dict'] = self.state_dict()

    def configure_optimizers(self):
        """Configure optimizer and learning rate scheduler.

        Returns:
            Dict with optimizer and lr_scheduler configuration
        """
        params = [p for p in self.t2s_model.parameters() if p.requires_grad]

        optimizer_cfg = self.config.get("optimizer", {})
        rank_zero_info(f">> Optimizer: {len(params)} trainable parameters")

        optimizer = get_optimizer(params, **optimizer_cfg)
        scheduler = get_scheduler(optimizer, **self.config.get("scheduler", {}))

        return {
            "optimizer": optimizer,
            "lr_scheduler": {
                "scheduler": scheduler,
                "interval": "step",
                "frequency": 1,
            },
        }

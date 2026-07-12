import argparse
import logging
import os
import torch
from pytorch_lightning import seed_everything, Trainer
from pytorch_lightning.utilities.rank_zero import rank_zero_info
from pytorch_lightning.loggers import TensorBoardLogger
from pytorch_lightning.strategies import DDPStrategy
from pytorch_lightning.callbacks import ModelCheckpoint, LearningRateMonitor

from transformers import AutoTokenizer

from confuciustts.cli.t2s_lightning import T2SLightningModule
from confuciustts.dataset.t2s_dataset import T2SDataModule
from confuciustts.utils.common import load_yaml_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

torch.set_float32_matmul_precision("high")


def get_latest_checkpoint(ckpt_dir: str):
    """Find the latest checkpoint in a directory.

    Args:
        ckpt_dir: Checkpoint directory path

    Returns:
        Path to latest checkpoint or None if not found
    """
    if not os.path.exists(ckpt_dir):
        return None
    last_ckpt = os.path.join(ckpt_dir, "last.ckpt")
    if os.path.exists(last_ckpt):
        return last_ckpt
    ckpts = sorted(
        [f for f in os.listdir(ckpt_dir) if f.startswith("step_") and f.endswith(".ckpt")],
        key=lambda x: int(x.split("_")[1].split(".")[0]),
    )
    return os.path.join(ckpt_dir, ckpts[-1]) if ckpts else None


def create_trainer(config: dict, ckpt_dir: str) -> Trainer:
    """Create PyTorch Lightning Trainer with configuration.

    Args:
        config: Training configuration dict
        ckpt_dir: Directory to save checkpoints

    Returns:
        Configured Lightning Trainer
    """
    train_cfg = config["training"]
    return Trainer(
        default_root_dir=config.get("log_dir", "logs"),
        accelerator="gpu",
        devices="auto",
        num_nodes=int(os.getenv("NUM_NODES", 1)),
        strategy=DDPStrategy(process_group_backend="nccl"),
        precision=train_cfg.get("precision", "bf16-mixed"),
        max_epochs=train_cfg.get("epochs", 100),
        gradient_clip_val=train_cfg.get("gradient_clip", 1.0),
        gradient_clip_algorithm="norm",
        accumulate_grad_batches=train_cfg.get("accumulate_grad_batches", 1),
        check_val_every_n_epoch=None,
        val_check_interval=train_cfg.get("val_check_interval", 5000),
        limit_val_batches=train_cfg.get("limit_val_batches", 10),
        num_sanity_val_steps=0,
        logger=TensorBoardLogger(
            save_dir=config.get("log_dir", "logs"),
            name="t2s_training",
            default_hp_metric=False,
        ),
        callbacks=[
            ModelCheckpoint(
                dirpath=ckpt_dir,
                filename="step_{step:09d}",
                save_top_k=-1,
                every_n_train_steps=train_cfg.get("save_every_n_steps", 5000),
                save_last=True,
                auto_insert_metric_name=False,
            ),
            LearningRateMonitor(logging_interval="step"),
        ],
        log_every_n_steps=train_cfg.get("log_every_n_steps", 10),
        enable_progress_bar=True,
        enable_model_summary=True,
        benchmark=train_cfg.get("benchmark", True),
    )


def print_param_info(model) -> None:
    """Print parameter count statistics for a model.

    Args:
        model: PyTorch model or Lightning module
    """
    total = sum(p.numel() for p in model.parameters())
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    rank_zero_info(f"  Total: {total:,}  Trainable: {trainable:,}  Frozen: {total - trainable:,}  ({trainable / total:.2%})")


def main(args: argparse.Namespace) -> None:
    """Main training function for T2S model.

    Args:
        args: Command-line arguments with config and training_config paths
    """
    config = load_yaml_config(args.config)
    if args.training_config:
        config.update(load_yaml_config(args.training_config))

    ckpt_dir = os.path.join(config.get("log_dir", "logs"), "ckpt")
    os.makedirs(ckpt_dir, exist_ok=True)

    seed_everything(config.get("seed", 42), workers=True)

    resume_ckpt = get_latest_checkpoint(ckpt_dir)
    if resume_ckpt:
        logger.info(f"Resuming from: {resume_ckpt}")

    trainer = create_trainer(config, ckpt_dir)

    model = T2SLightningModule(config)
    print_param_info(model)

    tokenizer = AutoTokenizer.from_pretrained(config["paths"]["tokenizer_path"])
    model_cfg = config.get("t2s_model", {})
    data_module = T2SDataModule(
        train_data_path=config["data"]["train_data_path"],
        val_data_path=config["data"].get("val_data_path"),
        tokenizer=tokenizer,
        w2v_bert_path=config["paths"]["w2v_bert_path"],
        batch_size=config["data"].get("batch_size", 16),
        num_workers=config["data"].get("num_workers", 4),
        max_text_seq_len=model_cfg.get("max_text_seq_lens", 520),
        max_semantic_seq_len=model_cfg.get("max_semantic_seq_lens", 1520),
        sample_rate=config["data"].get("sample_rate", 16000),
        semantic_pad_token=model_cfg.get("stop_semantic_token", 8193),
        start_semantic_token=model_cfg.get("start_semantic_token", 8192),
        stop_semantic_token=model_cfg.get("stop_semantic_token", 8193),
    )

    trainer.fit(model=model, datamodule=data_module, ckpt_path=resume_ckpt)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train Confucius4-TTS Text2Semantic model",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-c", "--config", type=str, required=True)
    parser.add_argument("-t", "--training-config", type=str, default=None)

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    main(args)

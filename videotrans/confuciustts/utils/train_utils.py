import math
import torch
from torch.optim import Optimizer, AdamW
from typing import Optional, Dict, Any
from transformers import (
    get_cosine_schedule_with_warmup,
    get_linear_schedule_with_warmup,
    get_constant_schedule_with_warmup,
)


def get_optimizer(
    model_parameters,
    optimizer_type: str = "adamw",
    learning_rate: float = 2.0e-4,
    weight_decay: float = 0.01,
    betas: tuple = (0.9, 0.95),
    eps: float = 1e-8,
) -> Optimizer:
    if optimizer_type.lower() == "adamw":
        optimizer = AdamW(
            model_parameters,
            lr=learning_rate,
            betas=betas,
            eps=eps,
            weight_decay=weight_decay,
        )
    elif optimizer_type.lower() == "adam":
        optimizer = torch.optim.Adam(
            model_parameters,
            lr=learning_rate,
            betas=betas,
            eps=eps,
            weight_decay=weight_decay,
        )
    else:
        raise ValueError(f"Unknown optimizer type: {optimizer_type}")

    return optimizer


def get_scheduler(
    optimizer: Optimizer,
    scheduler_type: str = "cosine",
    num_warmup_steps: int = 500,
    num_training_steps: int = 100000,
    **kwargs,
):
    if scheduler_type.lower() == "cosine":
        return get_cosine_schedule_with_warmup(
            optimizer=optimizer,
            num_warmup_steps=num_warmup_steps,
            num_training_steps=num_training_steps,
            **kwargs,
        )
    elif scheduler_type.lower() == "linear":
        return get_linear_schedule_with_warmup(
            optimizer=optimizer,
            num_warmup_steps=num_warmup_steps,
            num_training_steps=num_training_steps,
            **kwargs,
        )
    elif scheduler_type.lower() == "constant":
        return get_constant_schedule_with_warmup(
            optimizer=optimizer,
            num_warmup_steps=num_warmup_steps,
            **kwargs,
        )
    else:
        raise ValueError(f"Unknown scheduler type: {scheduler_type}")


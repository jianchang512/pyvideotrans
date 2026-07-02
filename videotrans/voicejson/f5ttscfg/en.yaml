hydra:
  run:
    dir: ckpts/${model.name}_${model.mel_spec.mel_spec_type}_${model.tokenizer}_${datasets.name}/${now:%Y-%m-%d}/${now:%H-%M-%S}

datasets:
  name: Emilia_ZH_EN  # dataset name
  batch_size_per_gpu: 38400  # 8 GPUs, 8 * 38400 = 307200
  batch_size_type: frame  # frame | sample
  max_samples: 64  # max sequences per batch if use frame-wise batch_size. we set 32 for small models, 64 for base models
  num_workers: 16

optim:
  epochs: 11
  learning_rate: 7.5e-5
  num_warmup_updates: 20000  # warmup updates
  grad_accumulation_steps: 1  # note: updates = steps / grad_accumulation_steps
  max_grad_norm: 1.0  # gradient clipping
  bnb_optimizer: False  # use bnb 8bit AdamW optimizer or not

model:
  name: F5TTS_v1_Base  # model name
  tokenizer: pinyin  # tokenizer type
  tokenizer_path: null  # if 'custom' tokenizer, define the path want to use (should be vocab.txt)
  backbone: DiT
  arch:
    dim: 1024
    depth: 22
    heads: 16
    ff_mult: 2
    text_dim: 512
    text_mask_padding: True
    qk_norm: null  # null | rms_norm
    conv_layers: 4
    pe_attn_head: null
    attn_backend: torch  # torch | flash_attn
    attn_mask_enabled: False
    checkpoint_activations: False  # recompute activations and save memory for extra compute
  mel_spec:
    target_sample_rate: 24000
    n_mel_channels: 100
    hop_length: 256
    win_length: 1024
    n_fft: 1024
    mel_spec_type: vocos  # vocos | bigvgan
  vocoder:
    is_local: False  # use local offline ckpt or not
    local_path: null  # local vocoder path

ckpts:
  logger: wandb  # wandb | tensorboard | null
  wandb_project: CFM-TTS  # wandb project name
  wandb_run_name: ${model.name}_${model.mel_spec.mel_spec_type}_${model.tokenizer}_${datasets.name}  # wandb run name
  wandb_resume_id: null  # wandb run id for resuming, null to auto-detect from checkpoint
  log_samples: True  # infer random sample per save checkpoint. wip, normal to fail with extra long samples
  save_per_updates: 50000  # save checkpoint per updates
  keep_last_n_checkpoints: -1  # -1 to keep all, 0 to not save intermediate, > 0 to keep last N checkpoints
  last_per_updates: 5000  # save last checkpoint per updates
  save_dir: ckpts/${model.name}_${model.mel_spec.mel_spec_type}_${model.tokenizer}_${datasets.name}
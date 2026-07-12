import argparse
import time
from pathlib import Path

import torch
import torchaudio

from confuciustts.cli.inference import ConfuciusTTS


def parse_args():
    p = argparse.ArgumentParser(
        description="ConfuciusTTS zero-shot TTS inference",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--text", type=str, required=True,
                   help="Input text to synthesize")
    p.add_argument("--lang", type=str, required=True,
                   help="Language code (e.g., zh, en, ja, ko)")
    p.add_argument("--prompt-wav", type=str, required=True,
                   help="Path to reference audio for voice cloning")
    p.add_argument("--output", type=str, required=True,
                   help="Output audio file path")
    p.add_argument("--config", type=str, default="config/inference_config.yaml",
                   help="Path to inference configuration YAML")
    p.add_argument("--t2s-checkpoint", type=str, default=None,
                   help="Override T2S checkpoint path from config")
    p.add_argument("--device", type=str, default="cuda",
                   help="Device for inference (cuda or cpu)")
    p.add_argument("--temperature", type=float, default=0.8,
                   help="Sampling temperature for T2S generation (higher = more diverse)")
    p.add_argument("--top-p", type=float, default=0.8,
                   help="Nucleus sampling probability threshold")
    p.add_argument("--top-k", type=int, default=30,
                   help="Top-k sampling parameter")
    p.add_argument("--num-beams", type=int, default=3,
                   help="Beam search width (1 = greedy decoding)")
    p.add_argument("--repetition-penalty", type=float, default=10.0,
                   help="Penalty for repeating tokens (higher = less repetition)")
    p.add_argument("--diffusion-steps", type=int, default=25,
                   help="Number of diffusion steps for S2A (more = higher quality, slower)")
    p.add_argument("--cfg-strength", type=float, default=0.7,
                   help="Classifier-free guidance scale (higher = stronger conditioning)")
    p.add_argument("--verbose", action="store_true",
                   help="Print processing information")
    return p.parse_args()


def main():
    args = parse_args()
    model = ConfuciusTTS(
        config_path=args.config,
        t2s_checkpoint=args.t2s_checkpoint,
        device=args.device,
    )
    t0 = time.time()
    audio = model.generate(
        text=args.text,
        lang=args.lang,
        prompt_wav=args.prompt_wav,
        temperature=args.temperature,
        top_p=args.top_p,
        top_k=args.top_k,
        num_beams=args.num_beams,
        repetition_penalty=args.repetition_penalty,
        n_timesteps=args.diffusion_steps,
        inference_cfg_rate=args.cfg_strength,
        verbose=args.verbose,
    )
    dt = time.time() - t0

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    torchaudio.save(str(out), audio.cpu(), model.sample_rate)
    print(f"Saved {out} ({audio.shape[-1] / model.sample_rate:.2f}s, took {dt:.2f}s)")


if __name__ == "__main__":
    main()

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Sequence

from videotrans.mosstts.onnx_tts_runtime import    OnnxTtsRuntime 

from dataclasses import dataclass

@dataclass
class Args:
    model_dir="./models"
    output_audio_path='infer_onnx_output.wav'
    text='你好啊朋友们' 
    prompt_audio_path='f5-tts/bajie.wav' 
    text_file=None 
    voice=None 
    sample_mode='fixed' 
    do_sample=1 
    realtime_streaming_decode=0 
    cpu_threads=4 
    execution_provider='cpu' 
    max_new_frames=375 
    voice_clone_max_text_tokens=75 
    text_temperature=1.0 
    text_top_p=1.0 
    text_top_k=50 
    audio_temperature=0.8 
    audio_top_p=0.95 
    audio_top_k=25 
    audio_repetition_penalty=1.2 
    enable_wetext_processing=0 
    disable_wetext_processing=True 
    enable_normalize_tts_text=False 
    disable_normalize_tts_text=True 
    seed=None 
    print_voice_clone_text_chunks=False



def main():

    args=Args()
    print(f'{args=}')
    runtime = OnnxTtsRuntime(
        model_dir=args.model_dir,
        thread_count=args.cpu_threads,
        max_new_frames=args.max_new_frames,
        do_sample=bool(args.do_sample),
        sample_mode=args.sample_mode,
        execution_provider=args.execution_provider,
    )
    generation_defaults = runtime.manifest["generation_defaults"]
    generation_defaults["text_temperature"] = float(args.text_temperature)
    generation_defaults["text_top_p"] = float(args.text_top_p)
    generation_defaults["text_top_k"] = int(args.text_top_k)
    generation_defaults["audio_temperature"] = float(args.audio_temperature)
    generation_defaults["audio_top_p"] = float(args.audio_top_p)
    generation_defaults["audio_top_k"] = int(args.audio_top_k)
    generation_defaults["audio_repetition_penalty"] = float(args.audio_repetition_penalty)
    raw_text = args.text
    enable_wetext = bool(args.enable_wetext_processing) and not bool(args.disable_wetext_processing)
    enable_normalize_tts_text = bool(args.enable_normalize_tts_text) and not bool(args.disable_normalize_tts_text)


    result = runtime.synthesize(
        text=raw_text,
        voice=args.voice,
        prompt_audio_path=args.prompt_audio_path,
        output_audio_path=args.output_audio_path,
        sample_mode=args.sample_mode,
        do_sample=bool(args.do_sample),
        streaming=bool(args.realtime_streaming_decode),
        max_new_frames=args.max_new_frames,
        voice_clone_max_text_tokens=args.voice_clone_max_text_tokens,
        enable_wetext=enable_wetext,
        enable_normalize_tts_text=enable_normalize_tts_text,
        seed=args.seed,
    )
    logging.info(
        "saved generated audio to %s sample_rate=%s frames=%s sample_mode=%s streaming=%s execution_provider=%s",
        result["audio_path"],
        result["sample_rate"],
        int(result["audio_token_ids"].shape[0]),
        result["sample_mode"],
        result["streaming"],
        runtime.execution_provider,
    )
    return result

from videotrans.util import tools
def _ce(msg):
    print(msg)
    
def _down():
    if not Path('./models/MOSS-TTS-Nano-100M-ONNX/moss_tts_global_shared.data').exists() or not Path('./models/MOSS-Audio-Tokenizer-Nano-ONNX/moss_audio_tokenizer_decode_shared.data').exists():
        try:
            import requests
            requests.head('https://huggingface.co', timeout=5)
        except Exception:
            print(f'当前无法连接到 https://huggingface.co,从 modelscope.cn')
            tools.check_and_down_ms("openmoss/MOSS-TTS-Nano-100M-ONNX",  callback=_ce,local_dir="./models/MOSS-TTS-Nano-100M-ONNX")
            tools.check_and_down_ms("openmoss/MOSS-Audio-Tokenizer-Nano-ONNX", callback=_ce, local_dir="./models/MOSS-Audio-Tokenizer-Nano-ONNX")
        else:
            tools.check_and_down_hf("","OpenMOSS-Team/MOSS-TTS-Nano-100M-ONNX",local_dir="./models/MOSS-TTS-Nano-100M-ONNX",  callback=_ce,check_connect=False)
            tools.check_and_down_hf("","OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX", local_dir="./models/MOSS-Audio-Tokenizer-Nano-ONNX", callback=_ce,check_connect=False)
        
if __name__ == "__main__":
    _down()
    main()

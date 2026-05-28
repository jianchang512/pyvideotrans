from dataclasses import dataclass

from videotrans.configure.config import ROOT_DIR,settings


@dataclass
class Args:
    model_dir=f"{ROOT_DIR}/models"
    output_audio_path='infer_onnx_output.wav'
    text=''
    prompt_audio_path=''
    text_file=None
    voice=None
    sample_mode='fixed'
    do_sample=1
    realtime_streaming_decode=0
    cpu_threads=int(float(settings.get('noise_separate_nums',4)))
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

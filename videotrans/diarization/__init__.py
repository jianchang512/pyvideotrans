"""

https://github.com/k2-fsa/sherpa-onnx/releases/tag/speaker-recongition-models
for a list of available models.

"""
from pathlib import Path
from videotrans.configure import config as cfg
from videotrans.util import tools
import torch,torchaudio
import os,sys

def resample_audio(audio, sample_rate, target_sample_rate):
    import librosa
    """
    Resample audio to target sample rate using librosa
    """
    if sample_rate != target_sample_rate:
        print(f"Resampling audio from {sample_rate}Hz to {target_sample_rate}Hz...")
        audio = librosa.resample(audio, orig_sr=sample_rate, target_sr=target_sample_rate)
        print(f"Resampling completed. New audio shape: {audio.shape}")
        return audio, target_sample_rate
    return audio, sample_rate


def init_speaker_diarization(language,num_speakers=-1):
    import sherpa_onnx
    segmentation_model = f"{cfg.ROOT_DIR}/models/onnx/seg_model.onnx"
    embedding_extractor_model = (
        f"{cfg.ROOT_DIR}/models/onnx/3dspeaker_speech_eres2net_large_sv_zh-cn_3dspeaker_16k.onnx"  if language=='zh' else   f"{cfg.ROOT_DIR}/models/onnx/nemo_en_titanet_small.onnx" 
    )
    if not Path(embedding_extractor_model).exists():
        raise RuntimeError('Not found speaker_diarization model')

    config = sherpa_onnx.OfflineSpeakerDiarizationConfig(
        segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
            pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(
                model=segmentation_model
            ),
        ),
        embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(
            model=embedding_extractor_model
        ),
        clustering=sherpa_onnx.FastClusteringConfig(
            num_clusters=num_speakers, threshold=0.5 #cluster_threshold
        ),
        min_duration_on=0.3,
        min_duration_off=0.5,
    )
    if not config.validate():
        raise RuntimeError(
            "Please check your config and make sure all required files exist"
        )

    return sherpa_onnx.OfflineSpeakerDiarization(config)


def get_diariz_pyannote(wave_filename,language,num_speakers=-1,uuid="",enable_gpu=False):
    # pyannote-audio==3.4.0
    import pyannote.audio
    torch.serialization.add_safe_globals([
        torch.torch_version.TorchVersion,
        pyannote.audio.core.task.Specifications,
        pyannote.audio.core.task.Problem,
        pyannote.audio.core.task.Resolution
    ])

    from pyannote.audio import Pipeline
    pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1")
    
    if enable_gpu:
        pipeline.to(torch.device("cuda"))
        

    # apply pretrained pipeline
    waveform, sample_rate = torchaudio.load(wave_filename)
    if num_speakers>0:
        diarization = pipeline({"waveform": waveform, "sample_rate": sample_rate},num_speakers=num_speakers)
    else:
        diarization = pipeline({"waveform": waveform, "sample_rate": sample_rate})


    output=[]
    # 获取的说话人数字id可能很乱，并非顺序增长，需要重新整理为0-n递增
    speaker_list=set()
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        speaker=speaker.replace('SPEAKER_','')
        speaker_list.add(f'spk{speaker}')
        output.append([[int(turn.start*1000),int(turn.end*1000)],f'spk{speaker}'])
    speaker_list=sorted(list(speaker_list))

    # 映射
    spk_neworder_dict={}    
    for i,it in enumerate(speaker_list):
        spk_neworder_dict[it]=f'spk{i}'
    print(f'原始说话人排序后：{speaker_list=}')
    print(f'映射为新说话人标识：{spk_neworder_dict=}')
    print(f'原始 {output=}')

    for i,it in enumerate(output):
        output[i][1]=spk_neworder_dict.get(it[1],'spk0')
    print(f'重排 {output=}')
    return output


def get_diariz(wave_filename,language,num_speakers=-1,uuid=""):
    import soundfile as sf
    if not Path(wave_filename).is_file():
        raise RuntimeError(f"{wave_filename} does not exist")

    def progress_callback(num_processed_chunk: int, num_total_chunks: int) -> int:
        progress = num_processed_chunk / num_total_chunks * 100
        msg=f"{cfg.tr('Begin separating the speakers')}: {progress:.3f}%"
        tools.set_process(text=msg,type="logs",uuid=uuid)
        return 0
    audio, sample_rate = sf.read(wave_filename, dtype="float32", always_2d=True)
    audio = audio[:, 0]  # only use the first channel

    # Since we know there are 4 speakers in the above test wave file, we use
    # num_speakers 4 here
    sd = init_speaker_diarization(language,num_speakers)
    
    # Resample audio to match the expected sample rate
    target_sample_rate = sd.sample_rate
    audio, sample_rate = resample_audio(audio, sample_rate, target_sample_rate)
    
    if sample_rate != sd.sample_rate:
        raise RuntimeError(
            f"Expected samples rate: {sd.sample_rate}, given: {sample_rate}"
        )

    show_progress = True

    if show_progress:
        result = sd.process(audio, callback=progress_callback).sort_by_start_time()
    else:
        result = sd.process(audio).sort_by_start_time()
    
    output=[]
    # 获取的说话人数字id可能很乱，并非顺序增长，需要重新整理为0-n递增
    speaker_list=set()
    for r in result:
        speaker_list.add(f'spk{r.speaker}')
        output.append([[int(r.start*1000),int(r.end*1000)],f'spk{r.speaker}'])
    speaker_list=sorted(list(speaker_list))
    
    # 映射
    spk_neworder_dict={}    
    for i,it in enumerate(speaker_list):
        spk_neworder_dict[it]=f'spk{i}'
    cfg.logger.info(f'原始说话人排序后：{speaker_list=}')
    cfg.logger.info(f'映射为新说话人标识：{spk_neworder_dict=}')
    
    for i,it in enumerate(output):
        output[i][1]=spk_neworder_dict.get(it[1],'spk0')
    
    return output

# speaker_type: built=sherpa_onnx pyannote=pyannote
def assign_speakers(wave_filename,language,subtitles,num_speakers=-1,uuid="",speaker_type='built',enable_gpu=False):
    cfg.logger.info(f'开始说话人分离 {language=},{num_speakers=}')
    # 根据选择使用内置或 pyannote 方式
    if speaker_type=='built':
        diarizations=get_diariz(wave_filename,language,num_speakers,uuid)
    else:
        diarizations=get_diariz_pyannote(wave_filename,language,num_speakers,uuid,enable_gpu)
    if not diarizations:
        return None
    output = []
    for sub in subtitles:
        if len(sub) != 2 or sub[0] >= sub[1]:
            output.append("spk0")
            continue
        
        s_start, s_end = sub
        s_duration = s_end - s_start
        if s_duration <= 0:
            output.append("spk0")
            continue
        
        overlaps = {}  # speaker -> total overlap (sum if multiple segments)
        for dia in diarizations:
            if len(dia) != 2 or len(dia[0]) != 2 or dia[0][0] >= dia[0][1]:
                continue
            
            d_start, d_end = dia[0]
            speaker = dia[1]
            
            overlap_start = max(s_start, d_start)
            overlap_end = min(s_end, d_end)
            overlap = max(0, overlap_end - overlap_start)
            
            if overlap > 0:
                if speaker in overlaps:
                    overlaps[speaker] += overlap
                else:
                    overlaps[speaker] = overlap
        
        if not overlaps:
            output.append("spk0")
            continue
        
        num_unique_speakers = len(overlaps)
        max_overlap = max(overlaps.values())
        best_speaker = max(overlaps, key=overlaps.get)  # gets the one with max overlap
        
        if num_unique_speakers > 1:
            # Assign to the one with max overlap, regardless of threshold
            output.append(best_speaker)
        elif num_unique_speakers == 1:
            # For single, check thresholds: >20% overall (covers >50% or 20%<x<=50%)
            if max_overlap > 0.2 * s_duration:
                output.append(best_speaker)
            else:
                output.append("spk0")
    
    cfg.logger.info(f'说话人分离成功结束,识别出个 {len(set(output))} 说话人')
    import gc
    gc.collect()
    return output
    
    
if __name__ == "__main__":
    zimu=[
        [580,7280],
        [7280,11610],
        [13120,19890],
        [19890,25730],
        [28060,35370],
        [36170,42400],
        [42400,50110],
        [50530,53850],
    ]
    ou=assign_speakers("3en.wav","en",zimu)
    print(f'{ou=}')
    
    
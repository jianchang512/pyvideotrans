from videotrans.configure.config import logs


def remove_noise(audio_path, output_file):
    from videotrans.configure import config
    from videotrans.util import tools
    from pathlib import Path
    import time
    from modelscope.pipelines import pipeline
    from modelscope.utils.constant import Tasks
    try:
        ans = pipeline(
            Tasks.acoustic_noise_suppression,
            model='iic/speech_zipenhancer_ans_multiloss_16k_base',
            disable_update=True,
            disable_progress_bar=True,
            disable_log=True,
            
        )
        ans(
            audio_path,
            output_path=output_file)
        tmp_name = Path(output_file).parent.as_posix() + f'/up_volume2-noise-{time.time()}.wav'

        tools.runffmpeg(['-y', '-i', output_file, '-af', "volume=1.5", tmp_name])
        return tmp_name
    except Exception as e:
        logs(f'降噪时出错:{e}', level="except")
    return audio_path

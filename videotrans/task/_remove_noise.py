from videotrans.configure import config
from videotrans.util import tools
from pathlib import Path
import time
def remove_noise(audio_path, output_file):
    from modelscope.pipelines import pipeline
    from modelscope.utils.constant import Tasks
    try:
        ans = pipeline(
            Tasks.acoustic_noise_suppression,
            model='damo/speech_zipenhancer_ans_multiloss_16k_base')
        result = ans(
            audio_path,
            output_path=output_file)

    except Exception as e:
        config.logger.exception(e, exc_info=True)
    else:
        tmp_name=Path(output_file).parent.as_posix()+f'/up_volume2-noise-{time.time()}.wav'
        tools.runffmpeg(['-y','-i',output_file,'-af',"volume=2",tmp_name])
        return tmp_name
    return audio_path
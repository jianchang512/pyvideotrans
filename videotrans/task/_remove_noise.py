from videotrans.configure import config

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
        return output_file
    return audio_path
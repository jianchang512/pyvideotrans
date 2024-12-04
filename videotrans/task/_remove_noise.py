def remove_noise(audio_path, output_file):
    try:
        from videotrans.configure import config
        from videotrans.util import tools
        from pathlib import Path
        import time,os
        from modelscope.pipelines import pipeline
        from modelscope.utils.constant import Tasks
        try:
            os.environ['bak_proxy']=os.environ.get('http_proxy') or os.environ.get('https_proxy')
            del os.environ['http_proxy']
            del os.environ['https_proxy']
            del os.environ['all_proxy']
        except:
            pass
        ans = pipeline(
            Tasks.acoustic_noise_suppression,
            model='damo/speech_zipenhancer_ans_multiloss_16k_base')
        result = ans(
            audio_path,
            output_path=output_file)
        tmp_name=Path(output_file).parent.as_posix()+f'/up_volume2-noise-{time.time()}.wav'
        tools.runffmpeg(['-y','-i',output_file,'-af',"volume=2",tmp_name])
        return tmp_name
    except Exception as e:
        err=str(e)
        if err.find('is not registered')>0:
            raise Exception('可能网络连接出错，请关闭代理后重试')
        config.logger.exception(e, exc_info=True)
    finally:
        proxy = os.environ.get('http_proxy') or os.environ.get('https_proxy') or os.environ.get('bak_proxy')
        if proxy:
            os.environ['http_proxy'] = proxy
            os.environ['https_proxy'] = proxy
            os.environ['all_proxy'] = proxy
    return audio_path
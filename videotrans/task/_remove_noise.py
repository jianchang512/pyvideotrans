
def run_remove(input_file,output_file,thread_nums=4):
    import torch,os,shutil,time
    from pathlib import Path
    from videotrans.configure import config
    from modelscope.pipelines import pipeline
    from modelscope.utils.constant import Tasks
    config.logger.info('开始降噪')
    
    ans=None
    result=None
    tmp_name = Path(output_file).parent.as_posix() + f'/noise-{time.time()}.wav'
    try:
        ans = pipeline(
            Tasks.acoustic_noise_suppression,
            model='iic/speech_frcrn_ans_cirm_16k',
            disable_update=True,
            disable_progress_bar=True,
            disable_log=True,
        )
        result = ans(input_file, output_path=tmp_name,disable_pbar=True)
        tools.runffmpeg(['-y', '-i', tmp_name, '-af', "volume=2.0,alimiter=limit=1.0", output_file])
        config.logger.info(f'降噪成功完成 {output_file}')
        return output_file
    except Exception as e:
        config.logger.exception(f'降噪失败:{e}',exc_info=True)
    finally:
        del ans
        del result
        try:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            import gc
            gc.collect()
            if Path(f'{TEMP_ROOT}/{os.getpid()}').exists():
                shutil.rmtree(f'{TEMP_ROOT}/{os.getpid()}', ignore_errors=True)
            Path(tmp_name).unlink(missing_ok=True)
        except Exception:
            pass
        
if __name__ == "__main__":
    run_remove("10.wav","10-no.wav")



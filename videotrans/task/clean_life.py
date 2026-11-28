import getpass
import platform
import shutil
import subprocess
from pathlib import Path
from videotrans.configure.config import logger,TEMP_ROOT,app_cfg

_os=platform.system()
def kill_processes(process_name_list=None):

    current_user = getpass.getuser()
    for process_name in process_name_list:
        if _os == "Windows":
            try:
                result = subprocess.run(
                    f'taskkill /F /FI "USERNAME eq {current_user}" /IM {process_name}.exe',
                    shell=True,
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    logger.warning(f"taskkill returned: {result.returncode}, output: {result.stdout}")
            except Exception as e:
                logger.exception(f"Error using taskkill: {e}", exc_info=True)

            return

        try:
            result = subprocess.run(
                ['pkill', '-9', '-u', current_user, process_name],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                logger.warning(f"pkill returned: {result.returncode}", exc_info=True)
        except Exception as e:
            logger.exception(f"Error using pkill: {e}", exc_info=True)

def safe_quit():
    from videotrans.configure import config
    from videotrans.configure._paths import REDUBB_STATUS_FILE, IPC_STATUS_FILE
    app_cfg.exit_soft = True
    app_cfg.current_status = 'stop'
    Path(REDUBB_STATUS_FILE).touch(exist_ok=True)
    Path(IPC_STATUS_FILE).touch(exist_ok=True)
    if config.AUDIO_SERVER_CFG and hasattr(config.AUDIO_SERVER_CFG,'quit'):
        try:
            config.AUDIO_SERVER_CFG.quit()
        except Exception:
            pass
    try:
        kill_processes(['ffmpeg','audiocpp_cli','audiocpp_server'])
    except Exception:
        pass


    # 清理 TEMP_ROOT 下的 txt srt json 文件，
    # 不直接删除 tmp 文件夹，避免同时启动多个实例导致其他报错，保留 pid 状态文件，防止其他实例出错
    for it in Path(TEMP_ROOT).iterdir():
        if not it.is_file() or it.suffix.lower()=='.pid':
            continue
        try:
            it.unlink(missing_ok=True)
        except OSError:
            pass
    try:
        shutil.rmtree(config.TEMP_DIR, ignore_errors=True)
    except OSError:
        pass

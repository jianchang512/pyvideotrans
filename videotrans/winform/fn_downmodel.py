from videotrans.configure import config
from videotrans.recognition import OPENAI_WHISPER, FASTER_WHISPER


# 视频 字幕 音频 合并
def open(model_name=None, model_type=None):
    if model_type not in [OPENAI_WHISPER, FASTER_WHISPER]:
        return

    from videotrans.component import DownloadModelForm
    try:
        down_win = DownloadModelForm()
        config.child_forms['down_win']=down_win
        if model_type == OPENAI_WHISPER:
            name = f'OpenAI Whisper:  {model_name}'
            url = config.MODELS_DOWNLOAD['openai'][model_name]
            text_help = f'请下载{model_name}.pt 后将该文件复制到 {config.ROOT_DIR}/models 文件夹内' if config.defaulelang == 'zh' else f'Please download {model_name}.pt and copy the file to {config.ROOT_DIR}/models folder.'
        else:
            name = f'OpenAI Whisper:  {model_name}'
            url = config.MODELS_DOWNLOAD['faster'][model_name]
            zipname = url.split('/')[-1].replace('?download=true', '')
            folder_name = f'models--Systran--faster-whisper-{model_name}'
            if model_name.startswith('distil'):
                folder_name = f'models--Systran--faster-{model_name}'
            text_help = f'请下载 {zipname} 后将该压缩包内的文件夹 {folder_name} 复制到 {config.ROOT_DIR}/models 文件夹内' if config.defaulelang == 'zh' else f'Please download {zipname}, open the zip file, and copy the folder {folder_name} into {config.ROOT_DIR}/models folder.'
        down_win.label_name.setText(name)
        down_win.url.setText(url)
        down_win.text_help.setPlainText(text_help)
        down_win.show()
    except Exception as e:
        print(e)

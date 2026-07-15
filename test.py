from videotrans.util import tools
def _process_callback(msg):
    print(msg)
tools.down_zip(f"./models",
                           'https://modelscope.cn/models/himyworld/videotrans/resolve/master/G2PWModel-v2-onnx.zip',
                           _process_callback)
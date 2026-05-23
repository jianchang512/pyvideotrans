from modelscope.hub.snapshot_download import snapshot_download

model_dir = snapshot_download('himyworld/videotrans',allow_patterns=['onnx/seg_model.onnx','onnx/vocals.fp16.onnx'],local_dir='./dev')
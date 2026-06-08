from modelscope.hub.callback import TqdmCallback
from modelscope.hub.snapshot_download import snapshot_download
model_id="mobiuslabsgmbh/faster-whisper-large-v3-turbo"
snapshot_download(model_id=model_id, local_dir=f"./models/"+model_id.replace('/','--'))
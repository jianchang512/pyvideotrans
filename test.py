from funasr import AutoModel
from modelscope import Tasks
from modelscope.pipelines import pipeline

from videotrans.configure import config
from videotrans.configure.config import ROOT_DIR

# model = pipeline(
#     task=Tasks.auto_speech_recognition,
#     model='iic/SenseVoiceSmall',
#     # model_revision="master",
#     disable_update=True,
#     disable_progress_bar=True,
#     disable_log=True,
#     device="cpu",
# 
# )
# 
# res = model(["./30.wav","./10.wav"], batch_size=4, disable_pbar=True,hotword="古老星系 韦伯 多环芳香烃")
# print(res)
# exit()

model = pipeline(
    task=Tasks.auto_speech_recognition,
    model='iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch',
    # model='iic/speech_paraformer-large-contextual_asr_nat-zh-cn-16k-common-vocab8404',
    # model_revision="v2.0.4",
     vad_model='iic/speech_fsmn_vad_zh-cn-16k-common-pytorch',
    # vad_model_revision="v2.0.4",
    punc_model='iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch',
    # punc_model_revision="v2.0.3",
    spk_model="damo/speech_campplus_sv_zh-cn_16k-common",
    # spk_model_revision="v2.0.2",
    disable_update=True,
    disable_progress_bar=True,
    disable_log=True,
    device="cpu",

    # trust_remote_code=True,
)
res = model("10.wav",hotword="古老星系 韦伯 多环芳香烃")
print(res)

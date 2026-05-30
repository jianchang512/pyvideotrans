from videotrans.util import tools
from videotrans.configure import config
from videotrans.configure.config import ROOT_DIR
config.init_run()
import soundfile as sf

def _c(msg):
    print(msg)

tools.check_and_down_hf("", 'resembleAI/chatterbox', f'{ROOT_DIR}/models/chatterbox', callback=_c,check_connect=True,allow_list=['ve.pt','s3gen.pt','conds.pt','t3_cfg.pt','t3_mtl23ls_v2.safetensors','Cangjie5_TC.json','grapheme_mtl_merged_expanded_v1.json','mtl_tokenizer.json','tokenizer.json'])

from chatterbox.mtl_tts import ChatterboxMultilingualTTS as ChatterboxTTS
model = ChatterboxTTS.from_local(f'{ROOT_DIR}/models/chatterbox',device='cpu')
wav_tensor = model.generate("你好啊，我亲爱的朋友",exaggeration=0.5,cfg_weight=0.5,language_id='zh')
#wav_tensor = model.generate("Commit directly to the main branch",exaggeration=0.5,cfg_weight=0.5,language_id='en')
#wav_tensor = model.generate("こんにちは私の親愛なる友人。 あなたの毎日が美しく楽しいものでありますように！",exaggeration=0.5,cfg_weight=0.5,language_id='ja')

wav_tensor = wav_tensor.detach().cpu()
if wav_tensor.ndim == 2:
    wav_np = wav_tensor.transpose(0, 1).numpy()
else:
    wav_np = wav_tensor.numpy()
 # 写入 WAV 格式到内存
sf.write("ceshien.wav", wav_np, model.sr, format='wav')
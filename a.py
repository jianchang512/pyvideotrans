from f5_tts.api import F5TTS
import sys,random
f5tts = F5TTS()

seed=random.randint(0, sys.maxsize)

wav, sr, spec = f5tts.infer(
    ref_file="nverguo.wav",
    ref_text="你说四大皆空，却为何，紧闭双眼，若你睁开眼睛看看我，我不相信你，两眼空空",
    gen_text="本开发者未授权任何实体或个人销售本软件(例如淘宝、闲鱼、拼多多等)。 任何通过付费渠道获取本软件的行为均与开发者无关，开发者未授权也未从中受益，对此不承担任何责任，如果你是花钱购买的并且想退款，请自行找卖家退钱或平台投诉，勿找开发者。",
    file_wave=f"length.wav",
    #file_spec=str(files("f5_tts").joinpath("../../tests/api_out.png")),
    seed=seed,
    remove_silence=True,
    speed=1.0
)

print("seed :", f5tts.seed)
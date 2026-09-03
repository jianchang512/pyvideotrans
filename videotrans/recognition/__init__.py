from pathlib import Path
from typing import Union, List, Type

from videotrans import winform, ChannelProvider, get_class
from videotrans.configure import contants
from videotrans.configure.config import tr, params, app_cfg, logger, ROOT_DIR, settings
from videotrans.configure.contants import Qwenasr_Models
from videotrans.recognition._base import BaseRecogn
from videotrans.task.taskcfg import SrtItem

FASTER_WHISPER = 0
OPENAI_WHISPER = 1
QWENASR = 2
Whisper_CPP = 3
FUNASR_CN = 4
FIREREDASR=5
DOLPHIN=6
Omnilingual=7
PARAKEET_JA=8
HUGGINGFACE_ASR = 9
MOSS_DIARIZE=10

OPENAI_API = 11
QWEN3ASR = 12
XIAOMIASR = 13
ZIJIE_RECOGN_MODEL = 14
ZHIPU_API = 15

GEMINI_SPEECH = 16

Faster_Whisper_XXL = 17
WHISPERX_API = 18
PARAKEET = 19

AI_302 = 20
ElevenLabs = 21
GOOGLE_SPEECH = 22

Deepgram = 23
CAMB_ASR = 24
STT_API = 25
WHISPER_NET = 26
CUSTOM_API = 27

# 允许切换不同模型的渠道
ALLOW_CHANGE_MODEL = [
    FASTER_WHISPER, Faster_Whisper_XXL, Whisper_CPP,
                      OPENAI_WHISPER, FUNASR_CN, Deepgram,
                      WHISPERX_API, HUGGINGFACE_ASR, QWENASR,
                      WHISPER_NET,QWEN3ASR

]

# 渠道id对应的设置窗口和sk键名, key_name: 存储SK或api url的键，(app_cfg.params),win:对应winform中的映射
_ID_NAME_DICT = {
    FASTER_WHISPER: ChannelProvider(f"faster-whisper({tr('Built-in')})", imp="._whisper"),
    OPENAI_WHISPER: ChannelProvider(f"openai-whisper({tr('Built-in')})", imp="._whisper"),
    QWENASR: ChannelProvider(f"Qwen-ASR({tr('Built-in')})", imp="._qwenasrlocal"),
    Whisper_CPP: ChannelProvider(f"Whisper.cpp(Win{tr('Built-in')})", imp="._cpp"),
    FUNASR_CN: ChannelProvider(tr("FunASR-Chinese")+f"({tr('Built-in')})", imp="._funasr"),
    FIREREDASR: ChannelProvider(f"{tr('FireRed')}({tr('Built-in')})", imp="._fireredasr"),
    DOLPHIN: ChannelProvider(f"{tr('Dolphin')}({tr('Built-in')})", imp="._dolphin"),
    Omnilingual: ChannelProvider(f"{tr('Omnilingual')}({tr('Built-in')})", imp="._omnilingual"),
    PARAKEET_JA: ChannelProvider(f"{tr('parakeet-ja')}({tr('Built-in')})", imp="._parakeetja"),
    HUGGINGFACE_ASR: ChannelProvider(f"Huggingface_ASR({tr('Built-in')})", imp="._huggingface"),
    MOSS_DIARIZE: ChannelProvider(f"MOSS-Diarize({tr('Built-in')})", imp="._moss"),
    


    OPENAI_API: ChannelProvider(tr("OpenAI Speech to Text"), key_name="openairecognapi_key", win="openairecognapi",
                                imp="._openairecognapi"),
    QWEN3ASR: ChannelProvider(tr("Ali Qwen3-ASR"), key_name="qwenmt_key", win="qwenmt", imp="._qwen3asr"),
    XIAOMIASR: ChannelProvider(tr("XiaoMi")+"ASR", key_name="xiaomi_key", win="xiaomi", imp="._xiaomiasr"),
    ZIJIE_RECOGN_MODEL: ChannelProvider(tr("VolcEngine STT"), key_name="zijierecognmodel_appid", win="zijierecognmodel",
                                        imp="._zijiemodel"),
    ZHIPU_API: ChannelProvider(f'{tr("Zhipu AI")} GLM-ASR', key_name="zhipu_key", win="zhipuai", imp="._glmasr"),
    GEMINI_SPEECH: ChannelProvider(tr("Gemini AI"), key_name="gemini_key", win="gemini", imp="._gemini"),



    Faster_Whisper_XXL: ChannelProvider("Faster-Whisper-XXL.exe", imp="._xxl"),
    WHISPERX_API: ChannelProvider(f"WhisperX({tr('Local')}API)", imp="._whisperx"),
    PARAKEET: ChannelProvider(f"Parakeet-tdt({tr('Local')}API)", key_name="parakeet_address", win="parakeet", imp="._parakeet"),

    AI_302: ChannelProvider("302.AI", key_name="ai302_key", win="ai302", imp="._ai302"),
    ElevenLabs: ChannelProvider("ElevenLabs.io", key_name="elevenlabstts_key", win="elevenlabs", imp="._elevenlabs"),
    GOOGLE_SPEECH: ChannelProvider(tr("Google Speech to Text"), imp="._google"),
    Deepgram: ChannelProvider("Deepgram.com", key_name="deepgram_apikey", win="deepgram", imp="._deepgram"),
    CAMB_ASR: ChannelProvider("CAMB AI", key_name="camb_api_key", win="cambtts", imp="._camb"),
    STT_API: ChannelProvider(f"STT({tr('Local')}API)", key_name="stt_url", win="sttapi", imp="._stt"),
    WHISPER_NET: ChannelProvider("Whisper.NET", imp="._whispernet"),
    CUSTOM_API: ChannelProvider(tr("Custom API"), key_name="recognapi_url", win="recognapi", imp="._recognapi"),
}
# 强制保持按照每个常量值大小排序
_ID_NAME_DICT=dict(sorted(_ID_NAME_DICT.items(),key=lambda item:item[0]))
RECOGN_NAME_LIST = [it.name for it in _ID_NAME_DICT.values()]

HUGGINGFACE_ASR_MODELS = {
    "Audio8/ARK-ASR-0.6B": ['zh','en','de','ja','fr','ko','es','pl','it','ro','hu','cs','nl'],
    "Audio8/ARK-ASR-3B": ['zh','en','de','ja','fr','ko','es','pl','it','ro','hu','cs','nl'],
    "zai-org/GLM-ASR-Nano-2512": ['zh','en','yue'],
    "ibm-granite/granite-speech-4.1-2b": ['fr','en','de','es','pt','ja'],
    "nvidia/parakeet-ctc-1.1b": ['en'],
    # hub
    "reazon-research/japanese-wav2vec2-large-rs35kh": ['ja'],#日语
    # pipeline whisper
    "kotoba-tech/kotoba-whisper-v2.0": ['ja'],#日语
    # pipeline whisper
    "vinai/Phowhisper-large": ['vi'],#越南语
    "nguyenvulebinh/wav2vec2-base-vietnamese-250h": ['vi'],#越南语
    "biodatlab/whisper-th-large-v3": ['th'],#泰语
    "sakares/wav2vec2-large-xlsr-thai-demo": ['th'],#泰语
    "SiangLao/xlsr-53-lao-asr":['lo'],# 老挝语
    "chuuhtetnaing/whisper-large-v3-myanmar":[],#缅甸语
    "1morecupofhottea/whisper-turbo-khmer-v9":[],#高棉语 柬埔寨
    "anke01/whisper-small-uyghur":[],#维吾尔语
    "kingabzpro/whisper-large-v3-turbo-urdu":[],#乌尔都语
    "vasista22/whisper-tamil-small":[],#泰米尔
    "theainerd/Wav2Vec2-large-xlsr-hindi":[],#印地语
    "cautroi/whisper-large-v3-id":[],#印尼语
    "Khalsuu/filipino-wav2vec2-l-xls-r-300m-official":[],#菲律宾
    "navai-uz/whisper-medium-uzbek":[],#乌兹别克
    "jonatasgrosman/wav2vec2-large-xlsr-53-persian":[],#波斯语
    "Ghost3454/translynx-pakistani-punjabi-whisper-small":[],#旁遮普语
    "turkmedstt/whisper-large-v3-turkish-general":[],#土耳其语
    "anton-l/wav2vec2-large-xlsr-53-mongolian":[],#蒙古语
    "HNO333333/w2v-bert-2.0-Tibetan-Amdo":[],#藏语
    "openai/whisper-large-v3": []
}
try:
    if Path(f'{ROOT_DIR}/huggingface_models.txt').exists():
        for it in Path(f'{ROOT_DIR}/huggingface_models.txt').read_text(encoding='utf-8').strip().split("\n"):
            HUGGINGFACE_ASR_MODELS[it.strip()] = []
except Exception as e:
    logger.waring(f'添加自定义 Huggingface_ASR 模型失败:{e}')


def get_model_by_type(recogn_type: int) -> List[str]:
    if recogn_type == Deepgram:
        return contants.DEEPGRAM_MODEL
    if recogn_type == Whisper_CPP:
        return settings.get('Whisper_cpp_models','').split(',')
    if recogn_type == WHISPER_NET:
        return settings.get('Whisper_net_models','').split(',')
    if recogn_type == QWENASR:
        return contants.QWENASR_LOCAL
    if recogn_type == FUNASR_CN:
        return contants.FUNASR_MODEL
    if recogn_type == HUGGINGFACE_ASR:
        return list(HUGGINGFACE_ASR_MODELS.keys())
    if recogn_type == OPENAI_WHISPER:
        return contants.Openai_Whisper_Models.split(',')
    if recogn_type == QWEN3ASR:
        return Qwenasr_Models.split(',')

    return settings.get('model_list','').split(',')


# 判断所用渠道和模型是否支持该语言的语音识别
# langcode=语言代码，recogn_type=识别渠道,model_name=模型名字
def is_allow_lang(langcode: str = None, recogn_type: int = None, model_name=None):
    # faster-whisper/openai-whisper支持所有语言
    if recogn_type in [FASTER_WHISPER, OPENAI_WHISPER, WHISPERX_API, Faster_Whisper_XXL, Whisper_CPP, OPENAI_API, AI_302, GEMINI_SPEECH, WHISPER_NET]:
        return True

    # huggingface_asr 渠道里的 openai 和 Systran 模型也支持所有语言
    if recogn_type == HUGGINGFACE_ASR:
        if not HUGGINGFACE_ASR_MODELS.get(model_name):
            return True
        
        if langcode not in HUGGINGFACE_ASR_MODELS[model_name]:
            return tr("Only support") + tr(HUGGINGFACE_ASR_MODELS[model_name])
        return True

    if recogn_type == PARAKEET_JA:
        return tr("Only support") + tr('ja')
        
    if recogn_type == DOLPHIN:
        return tr("Only support") + tr('40 Eastern languages and 22 Chinese dialects')
    if recogn_type == FIREREDASR:
        return tr("Only support") + tr('Chinese & English and Chinese dialects')
    
    return True


# 自定义识别、openai-api识别、zh_recogn识别是否填写了相关信息和sk等
# 正确返回True，失败返回False，并弹窗
def is_input_api(recogn_type: int = None, return_str=False):
    _cls = _ID_NAME_DICT.get(recogn_type)
    if not _cls: return True
    if _cls.key_name and not params.get(_cls.key_name):
        return "Please configure the API Key information of the Deepgram channel first." if return_str else winform.get_win(
            _cls.win).openwin()
    return True


# 统一入口
def run(*,
        detect_language="",
        audio_file=None,
        cache_folder=None,
        model_name=None,
        uuid=None,
        recogn_type: int = 0,
        is_cuda=None,
        subtitle_type=0,
        max_speakers=-1,  # -1 不启用说话人识别,0=不限制数量，>0最大数量
        recogn2pass=False  # 二次对配音文件识别，生成简短字幕

        ) -> Union[List[SrtItem], None]:
    if app_cfg.exit_soft or (uuid and uuid in app_cfg.stoped_uuid_set): return
    kwargs = {
        "detect_language": detect_language.lower() if detect_language else "",
        "audio_file": audio_file,
        "cache_folder": cache_folder,
        "model_name": model_name,
        "uuid": uuid,
        "is_cuda": is_cuda,
        "subtitle_type": subtitle_type,
        "recogn_type": recogn_type,
        "max_speakers": max_speakers,
        "recogn2pass": recogn2pass
    }
    _cls: Union[Type[BaseRecogn], None] = get_class(recogn_type, "recognition", _ID_NAME_DICT)
    if not _cls:
        raise RuntimeError(f'No this Recognition Channel:{recogn_type=}')

    return _cls(**kwargs).run()  # type:ignore

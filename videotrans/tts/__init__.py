from videotrans.configure import config



# 数字代表界面中的显示顺序
EDGE_TTS = 0
COSYVOICE_TTS = 1
CHATTTS = 2
AI302_TTS = 3
FISHTTS = 4
AZURE_TTS = 5
GPTSOVITS_TTS = 6
CLONE_VOICE_TTS = 7
OPENAI_TTS = 8
ELEVENLABS_TTS = 9
GOOGLE_TTS = 10
TTS_API = 11
VOLCENGINE_TTS = 12
F5_TTS = 13
KOKORO_TTS = 14

TTS_NAME_LIST = [
    "Edge-TTS(免费)" if config.defaulelang=='zh' else 'Edge-TTS',
    'CosyVoice(本地)' if config.defaulelang=='zh' else 'CosyVoice',
    "ChatTTS(本地)" if config.defaulelang=='zh' else 'ChatTTS',
    "302.AI",
    "FishTTS(本地)" if config.defaulelang=='zh' else 'FishTTS',
    "Azure-TTS",
    "GPT-SoVITS(本地)" if config.defaulelang=='zh' else 'GPT-SoVITS',
    "clone-voice(本地)" if config.defaulelang=='zh' else 'clone-voice',
    "OpenAI TTS",
    "Elevenlabs.io",
    "Google TTS",
    "自定义TTSAPI" if config.defaulelang == 'zh' else 'Customize API',
    "字节火山语音合成" if config.defaulelang == 'zh' else 'VolcEngine TTS',
    "F5-TTS(本地)" if config.defaulelang=='zh' else 'F5-TTS',
    "kokoro-TTS(本地)" if config.defaulelang=='zh' else 'kokoro-TTS',
]

DOUBAO_302AI={
            "灿灿": "zh_female_cancan_mars_bigtts",
            "清新女声": "zh_female_qingxinnvsheng_mars_bigtts",
            "爽快思思": "zh_female_shuangkuaisisi_moon_bigtts",
            "温暖阿虎": "zh_male_wennuanahu_moon_bigtts",
            "少年梓辛": "zh_male_shaonianzixin_moon_bigtts",
            "知性女声": "zh_female_zhixingnvsheng_mars_bigtts",
            "清爽男大": "zh_male_qingshuangnanda_mars_bigtts",
            "邻家女孩": "zh_female_linjianvhai_moon_bigtts",
            "渊博小叔": "zh_male_yuanboxiaoshu_moon_bigtts",
            "阳光青年": "zh_male_yangguangqingnian_mars_bigtts",
            "甜美小源": "zh_female_tianmeixiaoyuan_moon_bigtts",
            "清澈梓梓": "zh_female_qingchezizi_moon_bigtts",
            "解说小明": "zh_male_jieshuoxiaoming_moon_bigtts",
            "开朗姐姐": "zh_female_kailangjiejie_moon_bigtts",
            "邻家男孩": "zh_male_linjiananhai_moon_bigtts",
            "甜美悦悦": "zh_female_tianmeiyueyue_moon_bigtts",
            "心灵鸡汤": "zh_female_xinlingjitang_moon_bigtts",
            "京腔侃爷": "zh_male_jingqiangkanye_moon_bigtts",
            "湾湾小何": "zh_female_wanwanxiaohe_moon_bigtts",
            "湾区大叔": "zh_female_wanqudashu_moon_bigtts",
            "呆萌川妹": "zh_female_daimengchuanmei_moon_bigtts",
            "广州德哥": "zh_male_guozhoudege_moon_bigtts",
            "北京小爷": "zh_male_beijingxiaoye_moon_bigtts",
            "浩宇小哥": "zh_male_haoyuxiaoge_moon_bigtts",
            "广西远舟": "zh_male_guangxiyuanzhou_moon_bigtts",
            "妹坨洁儿": "zh_female_meituojieer_moon_bigtts",
            "豫州子轩": "zh_male_yuzhouzixuan_moon_bigtts",
            "奶气萌娃": "zh_male_naiqimengwa_mars_bigtts",
            "婆婆": "zh_female_popo_mars_bigtts",
            "高冷御姐": "zh_female_gaolengyujie_moon_bigtts",
            "傲娇霸总": "zh_male_aojiaobazong_moon_bigtts",
            "魅力女友": "zh_female_meilinvyou_moon_bigtts",
            "深夜播客": "zh_male_shenyeboke_moon_bigtts",
            "柔美女友": "zh_female_sajiaonvyou_moon_bigtts",
            "撒娇学妹": "zh_female_yuanqinvyou_moon_bigtts",
            "病弱少女": "ICL_zh_female_bingruoshaonv_tob",
            "活泼女孩": "ICL_zh_female_huoponvhai_tob",
            "东方浩然": "zh_male_dongfanghaoran_moon_bigtts",
            "和蔼奶奶": "ICL_zh_female_heainainai_tob",
            "邻居阿姨": "ICL_zh_female_linjuayi_tob",
            "温柔小雅": "zh_female_wenrouxiaoya_moon_bigtts",
            "天才童声": "zh_male_tiancaitongsheng_mars_bigtts",
            "猴哥": "zh_male_sunwukong_mars_bigtts",
            "熊二": "zh_male_xionger_mars_bigtts",
            "佩奇猪": "zh_female_peiqi_mars_bigtts",
            "武则天": "zh_female_wuzetian_mars_bigtts",
            "顾姐": "zh_female_gujie_mars_bigtts",
            "樱桃丸子": "zh_female_yingtaowanzi_mars_bigtts",
            "广告解说": "zh_male_chunhui_mars_bigtts",
            "少儿故事": "zh_female_shaoergushi_mars_bigtts",
            "四郎": "zh_male_silang_mars_bigtts",
            "磁性解说男声": "zh_male_jieshuonansheng_mars_bigtts",
            "鸡汤妹妹": "zh_female_jitangmeimei_mars_bigtts",
            "贴心女声": "zh_female_tiexinnvsheng_mars_bigtts",
            "俏皮女声": "zh_female_qiaopinvsheng_mars_bigtts",
            "萌丫头": "zh_female_mengyatou_mars_bigtts",
            "悬疑解说": "zh_male_changtianyi_mars_bigtts",
            "儒雅青年": "zh_male_ruyaqingnian_mars_bigtts",
            "霸气青叔": "zh_male_baqiqingshu_mars_bigtts",
            "擎苍": "zh_male_qingcang_mars_bigtts",
            "古风少御": "zh_female_gufengshaoyu_mars_bigtts",
            "温柔淑女": "zh_female_wenroushunv_mars_bigtts"
        }

# 检查当前配音渠道是否支持所选配音语言
# 返回True为支持，其他为不支持并返回错误字符串
def is_allow_lang(langcode: str = None, tts_type: int = None):
    if tts_type == GPTSOVITS_TTS and langcode[:2] not in ['zh', 'ja', 'ko','en']:
        return 'GPT-SoVITS 仅支持中日英韩配音' if config.defaulelang == 'zh' else 'GPT-SoVITS only supports Chinese, English, Japanese,ko'
    if tts_type == COSYVOICE_TTS and langcode[:2] not in ['zh', 'ja', 'en', 'ko']:
        return 'CosyVoice仅支持中日韩语言配音' if config.defaulelang == 'zh' else 'CosyVoice only supports Chinese, English, Japanese and Korean'

    if tts_type == CHATTTS and langcode[:2] not in ['zh', 'en']:
        return 'ChatTTS 仅支持中英语言配音' if config.defaulelang == 'zh' else 'ChatTTS only supports Chinese, English'



    if tts_type == VOLCENGINE_TTS and  langcode[:2] not in ['zh', 'ja', 'en','pt','es','th','vi','id']:
        return '字节火山语音合成 仅支持中、日、英、葡萄牙、西班牙、泰语、越南、印尼语言配音' if config.defaulelang == 'zh' else 'Byte VolcEngine TTS only supports Chinese, English, Japanese, Portuguese, Spanish, Thai, Vietnamese, Indonesian'
    if tts_type == KOKORO_TTS and  langcode[:2] not in ['zh', 'ja', 'en','pt','es','it','hi','fr']:
        return 'kokoro tts 仅支持中、日、英、葡萄牙、西班牙、意大利、印度、法语配音' if config.defaulelang == 'zh' else 'Kokoro TTS only supports Chinese, English, Japanese, Portuguese, Spanish, it, hi, fr'
    if tts_type == F5_TTS and  langcode[:2] not in ['zh', 'en','fr','ru','ja','it','hi','fi','es']:
        return 'F5-TTS语音合成 仅支持中、英、日、法、日、俄、意大利、印地、西班牙、芬兰语言配音' if config.defaulelang == 'zh' else 'F5-TTS only supports  zh, en, fr, ru, ja,it,hi,fi,es'

    return True


# 判断是否填写了相关配音渠道所需要的信息
# 正确返回True，失败返回False，并弹窗
def is_input_api(tts_type: int = None,return_str=False):
    if tts_type == OPENAI_TTS and not config.params["openaitts_key"]:
        if return_str:
            return "Please configure the api and key information of the OpenAI API channel first."
        from videotrans.winform import openaitts as openaitts_win
        openaitts_win.openwin()
        return False
    if tts_type == KOKORO_TTS and not config.params["kokoro_api"]:
        if return_str:
            return "Please configure the api  information of the kokoro tts channel first."
        from videotrans.winform import kokoro
        kokoro.openwin()
        return False
    if tts_type == AI302_TTS and not config.params["ai302_key"]:
        if return_str:
            return "Please configure the api and key information of the 302.AI TTS channel first."
        from videotrans.winform import ai302
        ai302.openwin()
        return False
    if tts_type == CLONE_VOICE_TTS and not config.params["clone_api"]:
        if return_str:
            return "Please configure the api and key information of the Clone-Voice channel first."
        from videotrans.winform import clone as clone_win
        clone_win.openwin()
        return False
    if tts_type == ELEVENLABS_TTS and not config.params["elevenlabstts_key"]:
        if return_str:
            return "Please configure the api and key information of the Elevenlabs.io channel first."
        from videotrans.winform import elevenlabs as elevenlabs_win
        elevenlabs_win.openwin()
        return False
    if tts_type == TTS_API and not config.params['ttsapi_url']:
        if return_str:
            return "Please configure the api and key information of the TTS API channel first."
        from videotrans.winform import ttsapi as ttsapi_win
        ttsapi_win.openwin()
        return False
    if tts_type == GPTSOVITS_TTS and not config.params['gptsovits_url']:
        if return_str:
            return "Please configure the api and key information of the GPT-SoVITS channel first."
        from videotrans.winform import gptsovits as gptsovits_win
        gptsovits_win.openwin()
        return False
    if tts_type == COSYVOICE_TTS and not config.params['cosyvoice_url']:
        if return_str:
            return "Please configure the api and key information of the CosyVoice channel first."
        from videotrans.winform import cosyvoice as cosyvoice_win
        cosyvoice_win.openwin()
        return False
    if tts_type == FISHTTS and not config.params['fishtts_url']:
        if return_str:
            return "Please configure the api and key information of the FishTTS channel first."
        from videotrans.winform import fishtts as fishtts_win
        fishtts_win.openwin()
        return False
    if tts_type == CHATTTS and not config.params['chattts_api']:
        if return_str:
            return "Please configure the api and key information of the ChatTTS channel first."
        from videotrans.winform import chattts as chattts_win
        chattts_win.openwin()
        return False
    if tts_type == AZURE_TTS and (not config.params['azure_speech_key'] or not config.params['azure_speech_region']):
        if return_str:
            return "Please configure the api and key information of the Azure TTS channel first."
        from videotrans.winform import  azuretts as azuretts_win
        azuretts_win.openwin()
        return False
    if tts_type == VOLCENGINE_TTS and (not config.params['volcenginetts_appid'] or not config.params['volcenginetts_access'] or not config.params['volcenginetts_cluster']):
        if return_str:
            return "Please configure the api and key information of the VolcEngine TTS channel first."
        from videotrans.winform import  volcenginetts as volcengine_win
        volcengine_win.openwin()
        return False
    if tts_type == F5_TTS and not config.params['f5tts_url']:
        if return_str:
            return "Please configure the api and key information of the VolcEngine F5-TTS channel first."
        from videotrans.winform import  f5tts as f5tts_win
        f5tts_win.openwin()
        return False
    return True


def run(*, queue_tts=None, language=None, inst=None, uuid=None, play=False, is_test=False) -> None:
    # 需要并行的数量3
    if len(queue_tts) < 1:
        return
    if config.exit_soft or (not is_test and config.current_status != 'ing' and config.box_tts != 'ing'):
        return
    tts_type = queue_tts[0]['tts_type']
    kwargs = {
        "queue_tts": queue_tts,
        "language": language,
        "inst": inst,
        "uuid": uuid,
        "play": play,
        "is_test": is_test
    }
    if tts_type == AZURE_TTS:
        from videotrans.tts._azuretts import AzureTTS
        AzureTTS(**kwargs).run()
    elif tts_type == EDGE_TTS:
        from videotrans.tts._edgetts import EdgeTTS
        EdgeTTS(**kwargs).run()
    elif tts_type == AI302_TTS:
        from videotrans.tts._ai302tts import AI302
        AI302(**kwargs).run()
    elif tts_type == COSYVOICE_TTS:
        from videotrans.tts._cosyvoice import CosyVoice
        CosyVoice(**kwargs).run()
    elif tts_type == CHATTTS:
        from videotrans.tts._chattts import ChatTTS
        ChatTTS(**kwargs).run()
    elif tts_type == FISHTTS:
        from videotrans.tts._fishtts import FishTTS
        FishTTS(**kwargs).run()
    elif tts_type == KOKORO_TTS:
        from videotrans.tts._kokoro import KokoroTTS
        KokoroTTS(**kwargs).run()
    elif tts_type == GPTSOVITS_TTS:
        from videotrans.tts._gptsovits import GPTSoVITS
        GPTSoVITS(**kwargs).run()
    elif tts_type == CLONE_VOICE_TTS:
        from videotrans.tts._clone import CloneVoice
        CloneVoice(**kwargs).run()
    elif tts_type == OPENAI_TTS:
        from videotrans.tts._openaitts import OPENAITTS
        OPENAITTS(**kwargs).run()
    elif tts_type == ELEVENLABS_TTS:
        from videotrans.tts._elevenlabs import ElevenLabsC
        ElevenLabsC(**kwargs).run()
    elif tts_type == GOOGLE_TTS:
        from videotrans.tts._gtts import GTTS
        GTTS(**kwargs).run()
    elif tts_type == TTS_API:
        from videotrans.tts._ttsapi import TTSAPI
        TTSAPI(**kwargs).run()
    elif tts_type == VOLCENGINE_TTS:
        from videotrans.tts._volcengine import VolcEngineTTS
        VolcEngineTTS(**kwargs).run()
    elif tts_type == F5_TTS:
        from videotrans.tts._f5tts import F5TTS
        F5TTS(**kwargs).run()

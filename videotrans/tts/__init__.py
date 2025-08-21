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
GOOGLECLOUD_TTS = 15
GEMINI_TTS = 16
CHATTERBOX_TTS = 17
QWEN_TTS = 18

TTS_NAME_LIST = [
    "Edge-TTS(免费)" if config.defaulelang == 'zh' else 'Edge-TTS',
    'CosyVoice(本地)' if config.defaulelang == 'zh' else 'CosyVoice',
    "ChatTTS(本地)" if config.defaulelang == 'zh' else 'ChatTTS',
    "302.AI",
    "FishTTS(本地)" if config.defaulelang == 'zh' else 'FishTTS',
    "Azure-TTS",
    "GPT-SoVITS(本地)" if config.defaulelang == 'zh' else 'GPT-SoVITS',
    "clone-voice(本地)" if config.defaulelang == 'zh' else 'clone-voice',
    "OpenAI TTS",
    "Elevenlabs.io",
    "Google TTS",
    "自定义TTSAPI" if config.defaulelang == 'zh' else 'Customize API',
    "字节火山语音合成" if config.defaulelang == 'zh' else 'VolcEngine TTS',
    "F5/Index/Spark/Dia TTS" if config.defaulelang == 'zh' else 'f5/index/spark/dia-TTS',
    "kokoro-TTS(本地)" if config.defaulelang == 'zh' else 'kokoro-TTS',
    "Google Cloud TTS",
    "Gemini TTS",
    "ChatterBox" if config.defaulelang == 'zh' else 'ChatterBox',
    "Qwen TTS"
]

AI302_openai = {"alloy": "alloy", "ash": "ash", "ballad": "ballad", "coral": "coral", "echo": "echo", "fable": "fable",
                "onyx": "onyx", "nova": "nova", "sage": "sage", "shimmer": "shimmer", "verse": "verse"}
AI302_doubao = {"北京小爷（多情感）": "zh_male_beijingxiaoye_emo_v2_mars_bigtts",
                "柔美女友（多情感）": "zh_female_roumeinvyou_emo_v2_mars_bigtts",
                "阳光青年（多情感）": "zh_male_yangguangqingnian_emo_v2_mars_bigtts",
                "魅力女友（多情感）": "zh_female_meilinvyou_emo_v2_mars_bigtts",
                "爽快思思（多情感）": "zh_female_shuangkuaisisi_emo_v2_mars_bigtts", "灿灿/Shiny": "zh_female_cancan_mars_bigtts",
                "清新女声": "zh_female_qingxinnvsheng_mars_bigtts", "爽快思思/Skye": "zh_female_shuangkuaisisi_moon_bigtts",
                "温暖阿虎/Alvin": "zh_male_wennuanahu_moon_bigtts", "少年梓辛/Brayan": "zh_male_shaonianzixin_moon_bigtts",
                "知性女声": "zh_female_zhixingnvsheng_mars_bigtts", "清爽男大": "zh_male_qingshuangnanda_mars_bigtts",
                "邻家女孩": "zh_female_linjianvhai_moon_bigtts", "渊博小叔": "zh_male_yuanboxiaoshu_moon_bigtts",
                "阳光青年": "zh_male_yangguangqingnian_moon_bigtts", "甜美小源": "zh_female_tianmeixiaoyuan_moon_bigtts",
                "清澈梓梓": "zh_female_qingchezizi_moon_bigtts", "解说小明": "zh_male_jieshuoxiaoming_moon_bigtts",
                "开朗姐姐": "zh_female_kailangjiejie_moon_bigtts", "邻家男孩": "zh_male_linjiananhai_moon_bigtts",
                "甜美悦悦": "zh_female_tianmeiyueyue_moon_bigtts", "心灵鸡汤": "zh_female_xinlingjitang_moon_bigtts",
                "知性温婉": "ICL_zh_female_zhixingwenwan_tob", "暖心体贴": "ICL_zh_male_nuanxintitie_tob",
                "温柔文雅": "ICL_zh_female_wenrouwenya_tob", "开朗轻快": "ICL_zh_male_kailangqingkuai_tob",
                "活泼爽朗": "ICL_zh_male_huoposhuanglang_tob", "率真小伙": "ICL_zh_male_shuaizhenxiaohuo_tob",
                "温柔小哥": "zh_male_wenrouxiaoge_mars_bigtts",
                "京腔侃爷/Harmony": "zh_male_jingqiangkanye_moon_bigtts",
                "湾湾小何": "zh_female_wanwanxiaohe_moon_bigtts", "湾区大叔": "zh_female_wanqudashu_moon_bigtts",
                "呆萌川妹": "zh_female_daimengchuanmei_moon_bigtts", "广州德哥": "zh_male_guozhoudege_moon_bigtts",
                "北京小爷": "zh_male_beijingxiaoye_moon_bigtts", "浩宇小哥": "zh_male_haoyuxiaoge_moon_bigtts",
                "广西远舟": "zh_male_guangxiyuanzhou_moon_bigtts", "妹坨洁儿": "zh_female_meituojieer_moon_bigtts",
                "豫州子轩": "zh_male_yuzhouzixuan_moon_bigtts", "奶气萌娃": "zh_male_naiqimengwa_mars_bigtts",
                "婆婆": "zh_female_popo_mars_bigtts", "高冷御姐": "zh_female_gaolengyujie_moon_bigtts",
                "傲娇霸总": "zh_male_aojiaobazong_moon_bigtts", "魅力女友": "zh_female_meilinvyou_moon_bigtts",
                "深夜播客": "zh_male_shenyeboke_moon_bigtts", "柔美女友": "zh_female_sajiaonvyou_moon_bigtts",
                "撒娇学妹": "zh_female_yuanqinvyou_moon_bigtts", "病弱少女": "ICL_zh_female_bingruoshaonv_tob",
                "活泼女孩": "ICL_zh_female_huoponvhai_tob", "东方浩然": "zh_male_dongfanghaoran_moon_bigtts",
                "绿茶小哥": "ICL_zh_male_lvchaxiaoge_tob", "娇弱萝莉": "ICL_zh_female_jiaoruoluoli_tob",
                "冷淡疏离": "ICL_zh_male_lengdanshuli_tob", "憨厚敦实": "ICL_zh_male_hanhoudunshi_tob",
                "傲气凌人": "ICL_zh_male_aiqilingren_tob", "活泼刁蛮": "ICL_zh_female_huopodiaoman_tob",
                "固执病娇": "ICL_zh_male_guzhibingjiao_tob", "撒娇粘人": "ICL_zh_male_sajiaonianren_tob",
                "傲慢娇声": "ICL_zh_female_aomanjiaosheng_tob", "潇洒随性": "ICL_zh_male_xiaosasuixing_tob",
                "腹黑公子": "ICL_zh_male_fuheigongzi_tob", "诡异神秘": "ICL_zh_male_guiyishenmi_tob",
                "儒雅才俊": "ICL_zh_male_ruyacaijun_tob", "病娇白莲": "ICL_zh_male_bingjiaobailian_tob",
                "正直青年": "ICL_zh_male_zhengzhiqingnian_tob", "娇憨女王": "ICL_zh_female_jiaohannvwang_tob",
                "病娇萌妹": "ICL_zh_female_bingjiaomengmei_tob", "青涩小生": "ICL_zh_male_qingsenaigou_tob",
                "纯真学弟": "chunzhen_xuedi", "暖心学姐": "ICL_zh_female_nuanxinxuejie_tob",
                "可爱女生": "ICL_zh_female_keainvsheng_tob", "成熟姐姐": "ICL_zh_female_chengshujiejie_tob",
                "病娇姐姐": "ICL_zh_female_bingjiaojiejie_tob", "优柔帮主": "ICL_zh_male_youroubangzhu_tob",
                "优柔公子": "ICL_zh_male_yourougongzi_tob", "妩媚御姐": "wumei_yujie",
                "调皮公主": "ICL_zh_female_tiaopigongzhu_tob", "傲娇女友": "ICL_zh_female_aojiaonvyou_tob",
                "贴心男友": "ICL_zh_male_tiexinnanyou_tob", "少年将军": "ICL_zh_male_shaonianjiangjun_tob",
                "贴心女友": "ICL_zh_female_tiexinnvyou_tob", "病娇哥哥": "ICL_zh_male_bingjiaogege_tob",
                "学霸男同桌": "ICL_zh_male_xuebanantongzhuo_tob", "幽默叔叔": "ICL_zh_male_youmoshushu_tob",
                "性感御姐": "ICL_zh_female_xingganyujie_tob", "假小子": "ICL_zh_female_jiaxiaozi_tob",
                "冷峻上司": "ICL_zh_male_lengjunshangsi_tob", "温柔男同桌": "ICL_zh_male_wenrounantongzhuo_tob",
                "病娇弟弟": "bingjiao_didi", "幽默大爷": "ICL_zh_male_youmodaye_tob", "傲慢少爷": "ICL_zh_male_aomanshaoye_tob",
                "神秘法师": "ICL_zh_male_shenmifashi_tob", "和蔼奶奶": "ICL_zh_female_heainainai_tob",
                "邻居阿姨": "ICL_zh_female_linjuayi_tob", "温柔小雅": "zh_female_wenrouxiaoya_moon_bigtts",
                "天才童声": "zh_male_tiancaitongsheng_mars_bigtts", "猴哥": "zh_male_sunwukong_mars_bigtts",
                "熊二": "zh_male_xionger_mars_bigtts", "佩奇猪": "zh_female_peiqi_mars_bigtts",
                "武则天": "zh_female_wuzetian_mars_bigtts", "顾姐": "zh_female_gujie_mars_bigtts",
                "樱桃丸子": "zh_female_yingtaowanzi_mars_bigtts",
                "zh_male_chunhui_mars_bigtts": "zh_male_chunhui_mars_bigtts",
                "zh_female_shaoergushi_mars_bigtts": "zh_female_shaoergushi_mars_bigtts",
                "四郎": "zh_male_silang_mars_bigtts", "磁性解说男声/Morgan": "zh_male_jieshuonansheng_mars_bigtts",
                "鸡汤妹妹/Hope": "zh_female_jitangmeimei_mars_bigtts", "贴心女声/Candy": "zh_female_tiexinnvsheng_mars_bigtts",
                "俏皮女声": "zh_female_qiaopinvsheng_mars_bigtts", "萌丫头/Cutey": "zh_female_mengyatou_mars_bigtts",
                "懒音绵宝": "zh_male_lanxiaoyang_mars_bigtts", "亮嗓萌仔": "zh_male_dongmanhaimian_mars_bigtts",
                "悬疑解说": "zh_male_changtianyi_mars_bigtts", "儒雅青年": "zh_male_ruyaqingnian_mars_bigtts",
                "霸气青叔": "zh_male_baqiqingshu_mars_bigtts", "擎苍": "zh_male_qingcang_mars_bigtts",
                "活力小哥": "zh_male_yangguangqingnian_mars_bigtts", "古风少御": "zh_female_gufengshaoyu_mars_bigtts",
                "温柔淑女": "zh_female_wenroushunv_mars_bigtts", "反卷青年": "zh_male_fanjuanqingnian_mars_bigtts", }
AI302_minimaxi = {"青涩青年音色": "male-qn-qingse", "精英青年音色": "male-qn-jingying", "霸道青年音色": "male-qn-badao",
                  "青年大学生音色": "male-qn-daxuesheng", "少女音色": "female-shaonv", "御姐音色": "female-yujie",
                  "成熟女性音色": "female-chengshu", "甜美女性音色": "female-tianmei", "男性主持人": "presenter_male",
                  "女性主持人": "presenter_female", "男性有声书1": "audiobook_male_1", "男性有声书2": "audiobook_male_2",
                  "女性有声书1": "audiobook_female_1", "女性有声书2": "audiobook_female_2",
                  "青涩青年音色-beta": "male-qn-qingse-jingpin",
                  "精英青年音色-beta": "male-qn-jingying-jingpin", "霸道青年音色-beta": "male-qn-badao-jingpin",
                  "青年大学生音色-beta": "male-qn-daxuesheng-jingpin", "少女音色-beta": "female-shaonv-jingpin",
                  "御姐音色-beta": "female-yujie-jingpin", "成熟女性音色-beta": "female-chengshu-jingpin",
                  "甜美女性音色-beta": "female-tianmei-jingpin", "聪明男童": "clever_boy", "可爱男童": "cute_boy",
                  "萌萌女童": "lovely_girl", "卡通猪小琪": "cartoon_pig", "俊朗男友": "junlang_nanyou", "冷淡学长": "lengdan_xiongzhang",
                  "霸道少爷": "badao_shaoye", "甜心小玲": "tianxin_xiaoling", "俏皮萌妹": "qiaopi_mengmei", "嗲嗲学妹": "diadia_xuemei",
                  "淡雅学姐": "danya_xuejie"}
AI302_dubbingx = {"木金(少女、元气、明亮)": "30149", "毛毛(悦耳、磁性、磨砂感)": "30136",
                  "章涵(洪亮、有力、清晰)": "30135", "可乐先生(感染力，青年，洪亮)": "30134", "大炮(饱满、磁性 、温暖)": "30133",
                  "无辄(年轻，武侠风，温暖)": "30132",
                  "包包(年轻，甜美，悦耳)": "30131", "罗森(沉稳，细腻，有感染力)": "30130", "乌冬面(青年，清脆，悦耳)": "30129", "陶陶(悦耳，流畅，细腻)": "30128",
                  "六角(甜美，悦耳，流畅)": "30127", "天越(少年，质朴，清澈)": "30123", "罗尼(清澈，洪亮，爽朗)": "30122", "凉皮(青年，细腻，自信)": "30121",
                  "肆米(自然、柔和、清新)": "30120", "一杭(青年，清澈，磁性)": "30119", "越洋(中年妇女 明亮 悦耳)": "30118", "小钶(小龄儿童 男女可兼)": "30117",
                  "小亮哥(中青年  稳重   温暖)": "30002", "钱慕欢(妩媚、高音、中速、明)": "100570", "韩直瑾(低音，中速，中等，清)": "100569",
                  "静婉(中音，柔和，温暖，热)": "100565", "赵睿诚(中音，柔和，温暖，)": "100486", "李和畅(高音，温暖，洪亮,)": "100485",
                  "苏明轩(中音，柔和，温暖)": "100484", "乐文远(中音，柔和，温暖，)": "100483", "赵厚德(中音，柔和，温暖，)": "100482",
                  "李秉(低音，柔和，温暖，)": "100481", "郑严方(低音，威严，浓厚)": "100480", "陆宁和(低音，慢速，柔和)": "100479",
                  "叶诗涵(高音，快速，柔和，)": "100475", "赵婉清(高音，快速，柔和，)": "100474", "陈思雅(中音，柔和，温暖)": "100473",
                  "李文乐(中音，明亮，热情，)": "100472", "陆正则(中音，明亮，热情，)": "100471", "陈明欢(中音，明亮，热情，)": "100470",
                  "赵宁远(中音,中等,清冷,)": "100469", "李和宇(中音，柔和，温暖，)": "100468", "张润轩(中音，温暖，热情，)": "100467",
                  "徐捷欢(中音，明亮，热情，)": "100466", "陈宁温(中音，明亮，亲切，)": "100465", "赵守正(中音，慢速，柔和，)": "100464",
                  "赵温良(低音，慢速，柔和，)": "100463", "李文远(中音，慢速，柔和，)": "100462", "柳媚儿(高音,快速,明亮,)": "100460",
                  "苏慧娘(聪慧、强势、夫人)": "100459", "陆绮娇(高音,快速,明亮,)": "100458", "李守义(中音，温暖，暗哑，)": "100457",
                  "魏巧琦(中音，热情，明亮，亲)": "100456", "高瑾(高音，洪亮，热情，)": "100455"}

AI302_doubao_ja = {"かずね（和音）/Javier or Álvaro": "multi_male_jingqiangkanye_moon_bigtts",
                   "はるこ（晴子）/Esmeralda": "multi_female_shuangkuaisisi_moon_bigtts",
                   "ひろし（広志）/Roberto": "multi_male_wanqudashu_moon_bigtts",
                   "あけみ（朱美）": "multi_female_gaolengyujie_moon_bigtts",
                   "ひかる（光）": "multi_zh_male_youyoujunzi_moon_bigtts",
                   "さとみ（智美）": "multi_female_sophie_conversation_wvae_bigtts",
                   "まさお（正男）": "multi_male_xudong_conversation_wvae_bigtts",
                   "つき（月）": "multi_female_maomao_conversation_wvae_bigtts", }


# 检查当前配音渠道是否支持所选配音语言
# 返回True为支持，其他为不支持并返回错误字符串
def is_allow_lang(langcode: str = None, tts_type: int = None):
    if langcode is None or tts_type is None:
        return True
    if tts_type == GPTSOVITS_TTS and langcode[:2] not in ['zh', 'ja', 'ko', 'en', 'yu']:
        return 'GPT-SoVITS 仅支持中日英韩配音' if config.defaulelang == 'zh' else 'GPT-SoVITS only supports Chinese, English, Japanese,ko'
    if tts_type == QWEN_TTS and langcode[:2] not in ['zh', 'en', 'yu']:
        return 'Qwen TS 仅支持中英配音' if config.defaulelang == 'zh' else 'Qwen TTS only supports Chinese, English'
    if tts_type == CHATTERBOX_TTS and langcode[:2] not in ['en']:
        return 'ChatterBox TTS 仅支持英语配音' if config.defaulelang == 'zh' else 'ChatterBox TTS only supports English'
    if tts_type == COSYVOICE_TTS and langcode[:2] not in ['zh', 'ja', 'en', 'ko', 'yu']:
        return 'CosyVoice仅支持中日韩语言配音' if config.defaulelang == 'zh' else 'CosyVoice only supports Chinese, English, Japanese and Korean'

    if tts_type == CHATTTS and langcode[:2] not in ['zh', 'en']:
        return 'ChatTTS 仅支持中英语言配音' if config.defaulelang == 'zh' else 'ChatTTS only supports Chinese, English'

    if tts_type == GOOGLECLOUD_TTS and langcode[:2] not in ['zh', 'en', 'ja', 'ko', 'fr', 'de', 'es', 'it', 'pt', 'ru',
                                                            'hi', 'ar', 'tr', 'th', 'vi', 'id', 'yu']:
        return 'Google Cloud TTS 仅支持中、英、日、韩、法、德、西、意、葡、俄、印、阿、土、泰、越、印尼语言配音' if config.defaulelang == 'zh' else 'Google Cloud TTS only supports Chinese, English, Japanese, Korean, French, German, Spanish, Italian, Portuguese, Russian, Hindi, Arabic, Turkish, Thai, Vietnamese, Indonesian'

    if tts_type == VOLCENGINE_TTS and langcode[:2] not in ['zh', 'ja', 'en', 'pt', 'es', 'th', 'vi', 'id', 'yu']:
        return '字节火山语音合成 仅支持中、日、英、葡萄牙、西班牙、泰语、越南、印尼语言配音' if config.defaulelang == 'zh' else 'Byte VolcEngine TTS only supports Chinese, English, Japanese, Portuguese, Spanish, Thai, Vietnamese, Indonesian'
    if tts_type == KOKORO_TTS and langcode[:2] not in ['zh', 'ja', 'en', 'pt', 'es', 'it', 'hi', 'fr']:
        return 'kokoro tts 仅支持中、日、英、葡萄牙、西班牙、意大利、印度、法语配音' if config.defaulelang == 'zh' else 'Kokoro TTS only supports Chinese, English, Japanese, Portuguese, Spanish, it, hi, fr'

    return True


# 判断是否填写了相关配音渠道所需要的信息
# 正确返回True，失败返回False，并弹窗
def is_input_api(tts_type: int = None, return_str=False):
    if tts_type == OPENAI_TTS and not config.params["openaitts_key"]:
        if return_str:
            return "Please configure the api and key information of the OpenAI API channel first."
        from videotrans.winform import openaitts as openaitts_win
        openaitts_win.openwin()
        return False
    if tts_type == QWEN_TTS and not config.params["qwentts_key"]:
        if return_str:
            return "Please configure the api key information of the Qwen TTS  channel first."
        from videotrans.winform import qwentts as qwentts_win
        qwentts_win.openwin()
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
    if tts_type == CHATTERBOX_TTS and not config.params['chatterbox_url']:
        if return_str:
            return "Please configure the api and key information of the ChatterBox channel first."
        from videotrans.winform import chatterbox as chatterbox_win
        chatterbox_win.openwin()
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
        from videotrans.winform import azuretts as azuretts_win
        azuretts_win.openwin()
        return False
    if tts_type == GEMINI_TTS and not config.params['gemini_key']:
        if return_str:
            return "Please configure the Gemini key information."
        from videotrans.winform import gemini as gemini_win
        gemini_win.openwin()
        return False
    if tts_type == VOLCENGINE_TTS and (
            not config.params['volcenginetts_appid'] or not config.params['volcenginetts_access'] or not config.params[
        'volcenginetts_cluster']):
        if return_str:
            return "Please configure the api and key information of the VolcEngine TTS channel first."
        from videotrans.winform import volcenginetts as volcengine_win
        volcengine_win.openwin()
        return False
    if tts_type == F5_TTS and not config.params['f5tts_url']:
        if return_str:
            return "Please configure the api and key information of the VolcEngine F5-TTS channel first."
        from videotrans.winform import f5tts as f5tts_win
        f5tts_win.openwin()
        return False
    if tts_type == GOOGLECLOUD_TTS and not config.params.get('gcloud_credential_json'):
        if return_str:
            return "Please configure the Google Cloud credentials first."
        from videotrans.winform import googlecloud as googlecloud_win
        googlecloud_win.openwin()
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
    elif tts_type == CHATTERBOX_TTS:
        from videotrans.tts._chatterbox import ChatterBoxTTS
        ChatterBoxTTS(**kwargs).run()
    elif tts_type == CLONE_VOICE_TTS:
        from videotrans.tts._clone import CloneVoice
        CloneVoice(**kwargs).run()
    elif tts_type == OPENAI_TTS:
        from videotrans.tts._openaitts import OPENAITTS
        OPENAITTS(**kwargs).run()
    elif tts_type == QWEN_TTS:
        from videotrans.tts._qwentts import QWENTTS
        QWENTTS(**kwargs).run()
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
    elif tts_type == GOOGLECLOUD_TTS:
        from videotrans.tts._googlecloud import GoogleCloudTTS
        GoogleCloudTTS(**kwargs).run()
    elif tts_type == GEMINI_TTS:
        from videotrans.tts._geminitts import GEMINITTS
        GEMINITTS(**kwargs).run()

import json
import os
import re
import sys

import requests


def get_elevenlabs_role(force=False, raise_exception=False):
    from videotrans.configure import config
    from . import help_misc
    jsonfile = os.path.join(config.ROOT_DIR, 'elevenlabs.json')
    namelist = ["clone"]
    if help_misc.vail_file(jsonfile):
        with open(jsonfile, 'r', encoding='utf-8') as f:
            cache = json.loads(f.read())
            for it in cache.values():
                namelist.append(it['name'])
    if not force and len(namelist) > 0:
        config.params['elevenlabstts_role'] = namelist
        return namelist
    try:
        from elevenlabs import ElevenLabs
        client = ElevenLabs(api_key=config.params["elevenlabstts_key"])
        voiceslist = client.voices.get_all()
        result = {}
        for it in voiceslist.voices:
            n = re.sub(r'[^a-zA-Z0-9_ -]+', '', it.name).strip()
            result[n] = {"name": n, "voice_id": it.voice_id}
            namelist.append(n)
        with open(jsonfile, 'w', encoding="utf-8") as f:
            f.write(json.dumps(result))
        config.params['elevenlabstts_role'] = namelist
        return namelist
    except Exception as e:
        if raise_exception:
            raise
    return []


def set_proxy(set_val=''):
    from videotrans.configure import config
    if set_val == 'del':
        config.proxy = None
        # 删除代理
        if os.environ.get('http_proxy'):
            os.environ.pop('http_proxy')
        if os.environ.get('https_proxy'):
            os.environ.pop('https_proxy')
        return None
    if set_val:
        # 设置代理
        if not set_val.startswith("http") and not set_val.startswith('sock'):
            set_val = f"http://{set_val}"
        config.proxy = set_val
        os.environ['http_proxy'] = set_val
        os.environ['https_proxy'] = set_val
        os.environ['all_proxy'] = set_val
        return set_val

    # 获取代理
    http_proxy = config.proxy or os.environ.get('http_proxy') or os.environ.get('https_proxy')
    if http_proxy:
        if not http_proxy.startswith("http") and not http_proxy.startswith('sock'):
            http_proxy = f"http://{http_proxy}"
        return http_proxy
    if sys.platform != 'win32':
        return None
    try:
        import winreg
        # 打开 Windows 注册表
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r'Software\Microsoft\Windows\CurrentVersion\Internet Settings') as key:
            # 读取代理设置
            proxy_enable, _ = winreg.QueryValueEx(key, 'ProxyEnable')
            proxy_server, _ = winreg.QueryValueEx(key, 'ProxyServer')
            if proxy_server:
                # 是否需要设置代理
                if not proxy_server.startswith("http") and not proxy_server.startswith('sock'):
                    proxy_server = "http://" + proxy_server
                try:
                    requests.head(proxy_server, proxies={"http": "", "https": ""})
                except Exception:
                    return None
                return proxy_server
    except Exception as e:
        pass
    return None


def get_302ai(role_name=None):
    from videotrans import tts
    role_dict = get_azure_rolelist()
    role_dict['zh'] = ['No'] + list(tts.AI302_doubao.keys()) + list(tts.AI302_minimaxi.keys()) + list(
        tts.AI302_dubbingx.keys()) + list(tts.AI302_openai.keys()) + role_dict['zh'][1:]
    role_dict['ja'] += list(tts.AI302_doubao_ja.keys())
    return role_dict


# 字节火山语音合成角色
def get_volcenginetts_rolelist(role_name=None, langcode="zh"):
    zh = {
        "灿灿2.0": "BV700_V2_streaming",
        "炀炀": "BV705_streaming",
        "擎苍2.0": "BV701_V2_streaming",
        "通用女声 2.0": "BV001_V2_streaming",
        "灿灿": "BV700_streaming",
        "超自然音色-梓梓2.0": "BV406_V2_streaming",
        "超自然音色-梓梓": "BV406_streaming",
        "超自然音色-燃燃2.0": "BV407_V2_streaming",
        "超自然音色-燃燃": "BV407_streaming",
        "通用女声": "BV001_streaming",
        "通用男声": "BV002_streaming",
        "擎苍": "BV701_streaming",
        "阳光青年": "BV123_streaming",
        "通用赘婿": "BV119_streaming",
        "古风少御": "BV115_streaming",
        "霸气青叔": "BV107_streaming",
        "质朴青年": "BV100_streaming",
        "温柔淑女": "BV104_streaming",
        "开朗青年": "BV004_streaming",
        "甜宠少御": "BV113_streaming",
        "儒雅青年": "BV102_streaming",
        "甜美小源": "BV405_streaming",
        "亲切女声": "BV007_streaming",
        "知性女声": "BV009_streaming",
        "诚诚": "BV419_streaming",
        "童童": "BV415_streaming",
        "亲切男声": "BV008_streaming",
        "译制片男声": "BV408_streaming",
        "懒小羊": "BV426_streaming",
        "清新文艺女声": "BV428_streaming",
        "鸡汤女声": "BV403_streaming",
        "智慧老者": "BV158_streaming",
        "慈爱姥姥": "BV157_streaming",
        "说唱小哥": "BR001_streaming",
        "活力解说男": "BV410_streaming",
        "影视解说小帅": "BV411_streaming",
        "解说小帅多情感": "BV437_streaming",
        "影视解说小美": "BV412_streaming",
        "纨绔青年": "BV159_streaming",
        "直播一姐": "BV418_streaming",
        "反卷青年": "BV120_streaming",
        "沉稳解说男": "BV142_streaming",
        "潇洒青年": "BV143_streaming",
        "阳光男声": "BV056_streaming",
        "活泼女声": "BV005_streaming",
        "小萝莉": "BV064_streaming",
        "奶气萌娃": "BV051_streaming",
        "动漫海绵": "BV063_streaming",
        "动漫海星": "BV417_streaming",
        "动漫小新": "BV050_streaming",
        "天才童声": "BV061_streaming",
        "促销男声": "BV401_streaming",
        "促销女声": "BV402_streaming",
        "磁性男声": "BV006_streaming",
        "新闻女声": "BV011_streaming",
        "新闻男声": "BV012_streaming",
        "知性姐姐": "BV034_streaming",
        "温柔小哥": "BV033_streaming",

        "东北老铁": "BV021_streaming",
        "东北丫头": "BV020_streaming",
        "东北灿灿": "BV704_streaming",

        "西安佟掌柜": "BV210_streaming",

        "上海阿姐": "BV217_streaming",

        "广西表哥": "BV213_streaming",
        "广西灿灿": "BV704_streaming",

        "甜美台妹": "BV025_streaming",
        "台普男声": "BV227_streaming",
        "台湾灿灿": "BV704_streaming",

        "港剧男神": "BV026_streaming",
        "广东女仔": "BV424_streaming",
        "粤语灿灿": "BV704_streaming",

        "相声演员": "BV212_streaming",

        "重庆小伙": "BV019_streaming",
        "四川甜妹儿": "BV221_streaming",
        "重庆幺妹儿": "BV423_streaming",
        "成都灿灿": "BV704_streaming",

        "郑州乡村企业家": "BV214_streaming",
        "湖南妹坨": "BV226_streaming",
        "长沙靓女": "BV216_streaming"
    }
    en = {
        "慵懒女声-Ava": "BV511_streaming",
        "议论女声-Alicia": "BV505_streaming",
        "情感女声-Lawrence": "BV138_streaming",
        "美式女声-Amelia": "BV027_streaming",
        "讲述女声-Amanda": "BV502_streaming",
        "活力女声-Ariana": "BV503_streaming",
        "活力男声-Jackson": "BV504_streaming",
        "天才少女": "BV421_streaming",
        "Stefan": "BV702_streaming",
        "天真萌娃-Lily": "BV506_streaming",
        "亲切女声-Anna": "BV040_streaming",
        "澳洲男声-Henry": "BV516_streaming"
    }
    ja = {
        "元气少女": "BV520_streaming",
        "萌系少女": "BV521_streaming",
        "天才少女": "BV421_streaming",
        "气质女声": "BV522_streaming",
        "Stefan": "BV702_streaming",
        "灿灿": "BV700_streaming",
        "日语男声": "BV524_streaming",
    }
    pt = {
        "活力男声Carlos": "BV531_streaming",
        "活力女声": "BV530_streaming",
        "天才少女": "BV421_streaming",
        "Stefan": "BV702_streaming",
        "灿灿": "BV700_streaming",
    }
    es = {
        "气质御姐": "BV065_streaming",
        "天才少女": "BV421_streaming",
        "Stefan": "BV702_streaming",
        "灿灿": "BV700_streaming",
    }
    th = {
        "天才少女": "BV421_streaming"
    }
    vi = {
        "天才少女": "BV421_streaming"
    }
    id = {
        "天才少女": "BV421_streaming",
        "Stefan": "BV702_streaming",
        "灿灿": "BV700_streaming",
    }
    if role_name and langcode[:2] == 'zh':
        return zh.get(role_name, zh[list(zh.keys())[0]])
    if role_name and langcode[:2] == 'en':
        return en.get(role_name, en[list(en.keys())[0]])
    if role_name and langcode[:2] == 'ja':
        return ja.get(role_name, ja[list(ja.keys())[0]])
    if role_name and langcode[:2] == 'pt':
        return pt.get(role_name, pt[list(pt.keys())[0]])
    if role_name and langcode[:2] == 'es':
        return es.get(role_name, es[list(es.keys())[0]])
    if role_name and langcode[:2] == 'th':
        return th.get(role_name, th[list(th.keys())[0]])
    if role_name and langcode[:2] == 'vi':
        return vi.get(role_name, vi[list(vi.keys())[0]])
    if role_name and langcode[:2] == 'id':
        return id.get(role_name, id[list(id.keys())[0]])
    if role_name:
        raise

    return {
        "zh": list(zh.keys()),
        "ja": list(ja.keys()),
        "en": list(en.keys()),
        "pt": list(pt.keys()),
        "es": list(es.keys()),
        "th": list(th.keys()),
        "id": list(id.keys()),
        "vi": list(vi.keys())
    }


#  get role by edge tts
def get_edge_rolelist():
    from videotrans.configure import config
    voice_list = {}
    from . import help_misc
    if help_misc.vail_file(config.ROOT_DIR + "/voice_list.json"):
        try:
            voice_list = json.load(open(config.ROOT_DIR + "/voice_list.json", "r", encoding="utf-8"))
            if len(voice_list) > 0:
                config.edgeTTS_rolelist = voice_list
                return voice_list
        except:
            pass
    try:
        import edge_tts
        import asyncio
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        else:
            asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
        v = asyncio.run(edge_tts.list_voices())
        for it in v:
            name = it['ShortName']
            prefix = name.split('-')[0].lower()
            if prefix not in voice_list:
                voice_list[prefix] = ["No", name]
            else:
                voice_list[prefix].append(name)
        with open(config.ROOT_DIR + "/voice_list.json", "w", encoding='utf-8') as f:
            f.write(json.dumps(voice_list))
        config.edgeTTS_rolelist = voice_list
        return voice_list
    except Exception as e:
        config.logger.error('获取edgeTTS角色失败' + str(e))


def get_azure_rolelist():
    from videotrans.configure import config
    from . import help_misc
    voice_list = {}

    if help_misc.vail_file(config.ROOT_DIR + "/azure_voice_list.json"):
        try:
            voice_list = json.load(open(config.ROOT_DIR + "/azure_voice_list.json", "r", encoding="utf-8"))
            if len(voice_list) > 0:
                config.AzureTTS_rolelist = voice_list
                return voice_list
        except:
            pass
    return voice_list


def get_kokoro_rolelist():
    voice_list = {
        "en": [
            "No",
            "af_alloy",
            "af_aoede",
            "af_bella",
            "af_jessica",
            "af_kore",
            "af_nicole",
            "af_nova",
            "af_river",
            "af_sarah",
            "af_sky",
            "am_adam",
            "am_echo",
            "am_eric",
            "am_fenrir",
            "am_liam",
            "am_michael",
            "am_onyx",
            "am_puck",
            "am_santa",
            "bf_alice",
            "bf_emma",
            "bf_isabella",
            "bf_lily",
            "bm_daniel",
            "bm_fable",
            "bm_george",
            "bm_lewis"
        ],
        "zh": ["No", "zf_xiaobei", "zf_xiaoni", "zf_xiaoxiao", "zf_xiaoyi", "zm_yunjian", "zm_yunxi", "zm_yunxia",
               "zm_yunyang"],
        "ja": ["No", "jf_alpha", "jf_gongitsune", "jf_nezumi", "jf_tebukuro", "jm_kumo"],
        "fr": ["No", "ff_siwis"],
        "it": ["No", "if_sara", "im_nicola"],
        "hi": ["No", "hf_alpha", "hf_beta", "hm_omega", "hm_psi"],
        "es": ["No", "ef_dora", "em_alex", "em_santa"],
        "pt": ["No", "pf_dora", "pm_alex", "pm_santa"]
    }

    return voice_list


# 根据 gptsovits config.params['gptsovits_role'] 返回以参考音频为key的dict
def get_gptsovits_role():
    from videotrans.configure import config
    if not config.params['gptsovits_role'].strip():
        return None
    rolelist = {}
    for it in config.params['gptsovits_role'].strip().split("\n"):
        tmp = it.strip().split('#')
        if len(tmp) != 3:
            continue
        rolelist[tmp[0]] = {"refer_wav_path": tmp[0], "prompt_text": tmp[1], "prompt_language": tmp[2]}
    return rolelist


def get_chatterbox_role():
    from videotrans.configure import config
    rolelist = ['chatterbox', 'clone']
    if not config.params['chatterbox_role'].strip():
        return rolelist
    for it in config.params['chatterbox_role'].strip().split("\n"):
        rolelist.append(it.strip())
    return rolelist


def get_cosyvoice_role():
    from videotrans.configure import config
    rolelist = {
        "clone": 'clone'
    }
    if config.defaulelang == 'zh':
        rolelist['中文男'] = '中文男'
        rolelist['中文女'] = '中文女'
        rolelist['英文男'] = '英文男'
        rolelist['英文女'] = '英文女'
        rolelist['日语男'] = '日语男'
        rolelist['韩语女'] = '韩语女'
        rolelist['粤语女'] = '粤语女'
    else:
        rolelist['Chinese Male'] = '中文男'
        rolelist['Chinese Female'] = '中文女'
        rolelist['English Male'] = '英文男'
        rolelist['English Female'] = '英文女'
        rolelist['Japanese Male'] = '日语男'
        rolelist['Korean Female'] = '韩语女'
        rolelist['Cantonese Female'] = '粤语女'
    if not config.params['cosyvoice_role'].strip():
        return rolelist
    for it in config.params['cosyvoice_role'].strip().split("\n"):
        tmp = it.strip().split('#')
        if len(tmp) != 2:
            continue
        rolelist[tmp[0]] = {"reference_audio": tmp[0], "reference_text": tmp[1]}
    return rolelist


def get_fishtts_role():
    from videotrans.configure import config
    if not config.params['fishtts_role'].strip():
        return None
    rolelist = {}
    for it in config.params['fishtts_role'].strip().split("\n"):
        tmp = it.strip().split('#')
        if len(tmp) != 2:
            continue
        rolelist[tmp[0]] = {"reference_audio": tmp[0], "reference_text": tmp[1]}
    return rolelist


def get_f5tts_role():
    from videotrans.configure import config
    if not config.params['f5tts_role'].strip():
        return
    rolelist = {}
    for it in config.params['f5tts_role'].strip().split("\n"):
        tmp = it.strip().split('#')
        if len(tmp) != 2:
            continue
        rolelist[tmp[0]] = {"ref_audio": tmp[0], "ref_text": tmp[1]}
    return rolelist


# 获取clone-voice的角色列表
def get_clone_role(set_p=False):
    from videotrans.configure import config
    if not config.params['clone_api']:
        if set_p:
            raise Exception(config.transobj['bixutianxiecloneapi'])
        return False
    try:
        url = config.params['clone_api'].strip().rstrip('/') + "/init"
        res = requests.get('http://' + url.replace('http://', ''), proxies={"http": "", "https": ""})
        if res.status_code == 200:
            config.params["clone_voicelist"] = ["clone"] + res.json()
            
            set_process(type='set_clone_role')
            return True
        raise Exception(
            f"code={res.status_code},{config.transobj['You must deploy and start the clone-voice service']}")
    except Exception as e:
        if set_p:
            raise
    return False


# 综合写入日志，默认sp界面
# type=logs|error|subtitle|end|stop|succeed|set_precent|replace_subtitle|.... 末尾显示类型，
# uuid 任务的唯一id，用于确定插入哪个子队列
# nologs=False不写入日志
def set_process(*, text="", type="logs", uuid=None, nologs=False):
    from videotrans.configure import config
    try:
        if text:
            # 移除html
            if type == 'error':
                text = text.replace('\\n', ' ').strip()
        if type == 'logs':
            text = text[:150]
        log = {"text": text, "type": type, "uuid": uuid}
        if uuid:
            config.push_queue(uuid, log)
        else:
            config.global_msg.append(log)
    except:
        pass

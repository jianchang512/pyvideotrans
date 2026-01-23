import json
import os
import re
import sys

import requests

from videotrans.configure import config
from pathlib import Path
from functools import lru_cache


def get_elevenlabs_role(force=False, raise_exception=False):
    from . import help_misc
    jsonfile = f'{config.ROOT_DIR}/videotrans/voicejson/elevenlabs.json'
    namelist = ["No"]
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
        client = ElevenLabs(api_key=config.params.get("elevenlabstts_key",''))
        voiceslist = client.voices.get_all()

        namelist=['No']
        result = {}
        for it in voiceslist.voices:
            n = re.sub(r'[^a-zA-Z0-9_ -]+', '', it.name,flags=re.I | re.S).strip()
            result[n] = {"name": n, "voice_id": it.voice_id}
            namelist.append(n)

        with open(jsonfile, 'w', encoding="utf-8") as f:
            f.write(json.dumps(result))
        config.params['elevenlabstts_role'] = namelist
        return namelist
    except Exception as e:
        config.logger.exception(f'获取 elevenlabs 角色失败:{e}', exc_info=True)
        if raise_exception:
            raise
    return []


def get_vits_role():
    zh=['No',"zh_female"]
    en=['No',"en_female"]
    for i in range(109):
        en.append(f'en_{i}')
    for i in range(174):
        zh.append(f'zh_{i}')
    
    return {"zh":{k:k for k in zh},"en":{k:k for k in en}}

def get_piper_role():
    file_path=f"{config.ROOT_DIR}/videotrans/voicejson/piper.json"
    if Path(file_path).exists():
        rolelist=json.loads(Path(file_path).read_text(encoding='utf-8'))
    else:
        rolelist={}
        from videotrans.translator import LANGNAME_DICT
        langkeys=[it.split('-')[0] for it in LANGNAME_DICT.keys()]
        for it in Path(f'{config.ROOT_DIR}/models/piper').rglob('*.onnx'):
            rolename=Path(it).stem
            tmp=rolename.split('_')#tmp[0] 语言代码
            if tmp[0] not in langkeys:
                continue
            if tmp[0] not in rolelist:
                rolelist[tmp[0]]={"No":"No"}
            rolelist[tmp[0]][rolename]=rolename
        Path(file_path).write_text(json.dumps(rolelist,indent=4),encoding='utf-8')
    return rolelist

def get_302ai():

    role_dict = get_azure_rolelist()

    with open(config.ROOT_DIR + "/videotrans/voicejson/302.json", 'r', encoding='utf-8') as f:
        ai302_voice_roles = json.loads(f.read())
        _doubao = ai302_voice_roles.get("AI302_doubao", {})
        _minimaxi = ai302_voice_roles.get("AI302_minimaxi", {})
        _dubbingx = ai302_voice_roles.get("AI302_dubbingx", {})
        _doubao_ja = ai302_voice_roles.get("AI302_doubao_ja", {})
    _openai=config.OPENAITTS_ROLES.split(",")
    role_dict['zh'] = role_dict['zh']+ list(_doubao.keys()) + list(_minimaxi.keys()) + list(
        _dubbingx.keys()) + _openai
    role_dict['ja'] += list(_doubao_ja.keys())
    return role_dict


# 字节火山语音合成角色
def get_doubao_rolelist(role_name=None, langcode="zh"):

    roledata=json.loads(Path(f'{config.ROOT_DIR}/videotrans/voicejson/doubao0.json').read_text(encoding='utf-8'))
    
   
    if role_name:
        current_d=roledata.get(langcode[:2])
        if not current_d:
            return 'No'
        return current_d.get(role_name)
    
    return { key:['No']+list(item.keys())  for key,item in roledata.items()}


def get_doubao2_rolelist(role_name=None, langcode="zh"):

    roledata=json.loads(Path(f'{config.ROOT_DIR}/videotrans/voicejson/doubao2.json').read_text(encoding='utf-8'))
    
   
    if role_name:
        current_d=roledata.get(langcode[:2])
        if not current_d:
            return 'No'
        return current_d.get(role_name)
    
    return { key:['No']+list(item.keys())  for key,item in roledata.items()}



#  get role by edge tts
@lru_cache(maxsize=None)
def get_edge_rolelist(role_name=None,locale=None):

    from . import help_misc
    voice_list = {}
    voice_file=config.ROOT_DIR + "/videotrans/voicejson/edge_tts.json"
    if help_misc.vail_file(voice_file):
        try:
            with open(voice_file,'r',encoding='utf-8') as f:
                voice_list = json.loads(f.read())
            for i,it in voice_list.items():
                voice_list[i]={"No":"No"}|it
        except (OSError,json.JSONDecodeError):
            pass
    if role_name and locale:
        return voice_list.get(locale.split('-')[0],{}).get(role_name)
    return voice_list


def get_azure_rolelist():

    from . import help_misc
    voice_list = {}
    voice_file=config.ROOT_DIR + "/videotrans/voicejson/azure_voice_list.json"
    if help_misc.vail_file(voice_file):
        try:
            with open(voice_file,'r',encoding='utf-8') as f:
                voice_list = json.loads(f.read())
            for it in voice_list.values():
                it.insert(0,'No')
        except (OSError,json.JSONDecodeError):
            pass
    return voice_list

def get_minimaxi_rolelist():

    from . import help_misc
    voice_list = {}
    voice_file=config.ROOT_DIR + "/videotrans/voicejson/minimaxi.json"

    if config.params.get("minimaxi_apiurl",'')=='api.minimax.io':
        voice_file=config.ROOT_DIR + "/videotrans/voicejson/minimaxiio.json"
    if help_misc.vail_file(voice_file):
        try:
            with open(voice_file,'r',encoding='utf-8') as f:
                voice_list = json.loads(f.read())
            for i,it in voice_list.items():
                voice_list[i]={"No":"No"}|it
        except (OSError,json.JSONDecodeError):
            pass
    return voice_list


def get_qwen3tts_rolelist():
    voices=json.loads(Path(config.ROOT_DIR+"/videotrans/voicejson/qwen3tts.json").read_text(encoding='utf-8'))
    voices={"No":"No"}|voices
    return voices

def get_supertonic_rolelist():
    voices=json.loads(Path(config.ROOT_DIR+"/videotrans/voicejson/supertonic.json").read_text(encoding='utf-8'))
    voices={"No":"No"}|voices
    return voices


def get_glmtts_rolelist():
    voices=json.loads(Path(config.ROOT_DIR+"/videotrans/voicejson/glmtts.json").read_text(encoding='utf-8'))
    voices={"No":"No"}|voices
    return voices



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

    if not config.params.get('gptsovits_role','').strip():
        return None
    rolelist = {"No":"No","clone":"clone"}
    for it in config.params.get('gptsovits_role','').strip().split("\n"):
        tmp = it.strip().split('#')
        if len(tmp) != 3:
            continue
        rolelist[tmp[0]] = {"refer_wav_path": tmp[0], "prompt_text": tmp[1], "prompt_language": tmp[2]}
    return rolelist


def get_chatterbox_role():

    rolelist = ['No', 'clone']
    if not config.params.get('chatterbox_role','').strip():
        return rolelist
    for it in config.params.get('chatterbox_role','').strip().split("\n"):
        rolelist.append(it.strip())
    return rolelist


def get_cosyvoice_role():

    rolelist = {
        "No":"No",
        "clone": 'clone'
    }

    for it in config.params.get('cosyvoice_role','').strip().split("\n"):
        tmp = it.strip().split('#')
        if len(tmp) != 2:
            continue
        rolelist[tmp[0]] = {"reference_audio": tmp[0], "reference_text": tmp[1]}
    return rolelist


def get_fishtts_role():

    if not config.params.get('fishtts_role','').strip():
        return None
    rolelist = {"No":"No"}
    for it in config.params.get('fishtts_role','').strip().split("\n"):
        tmp = it.strip().split('#')
        if len(tmp) != 2:
            continue
        rolelist[tmp[0]] = {"reference_audio": tmp[0], "reference_text": tmp[1]}
    return rolelist


def get_f5tts_role():

    if not config.params.get('f5tts_role','').strip():
        return
    rolelist = {"No":"No","clone":"clone"}
    for it in config.params.get('f5tts_role','').strip().split("\n"):
        tmp = it.strip().split('#')
        if len(tmp) != 2:
            continue
        rolelist[tmp[0]] = {"ref_audio": tmp[0], "ref_text": tmp[1]}
    return rolelist


# 获取clone-voice的角色列表
def get_clone_role(set_p=False):
    from . import help_misc
    if not config.params.get('clone_api',''):
        if set_p:
            raise Exception(config.tr('bixutianxiecloneapi'))
        return False
    try:
        url = config.params.get('clone_api','').strip().rstrip('/') + "/init"
        res = requests.get('http://' + url.replace('http://', ''), proxies={"http": "", "https": ""})
        res.raise_for_status()
        config.params["clone_voicelist"] = ['No',"clone"] + res.json()
        help_misc.set_process(type='set_clone_role')
    except Exception as e:
        if set_p: raise
    return False


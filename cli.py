"""
命令行使用方式
python cli.py  [-c 可选传参一个配置文件的绝对路径，如果不传参，则使用项目根目录下的 cli.ini ] [-m mp4视频的绝对地址或填写到cli.ini文件中] [-cuda 加上即启用cuda加速，如果可用]

python cli.py -m c:/Users/c1/Videos/1.mp4 使用 默认当前目录下的 cli.ini
python cli.py -cuda -m c:/Users/c1/Videos/1.mp4 使用 默认当前目录下的 cli.ini，启用CUDA加速
python cli.py -c D:/cli.ini  -m c:/Users/c1/Videos/1.mp4 使用 D:/cli.ini, 忽略当前目录下的


"""
import os
import re
import sys
import traceback
from videotrans.box.worker import Worker
from videotrans.configure import config
import argparse
from videotrans.task.trans_create import TransCreate
from videotrans.translator import LANG_CODE, is_allow_translate, BAIDU_NAME, TENCENT_NAME, CHATGPT_NAME, AZUREGPT_NAME, \
    GEMINI_NAME, DEEPLX_NAME, DEEPL_NAME
from videotrans.util import tools
from videotrans.util.tools import send_notification, set_process, set_proxy, get_edge_rolelist, get_elevenlabs_role
from tqdm import tqdm

def __init__():
    if not os.path.exists(os.path.join(config.rootdir, 'voice_list.json')) or os.path.getsize(
            os.path.join(config.rootdir, 'voice_list.json')) == 0:
        print("正在获取 edge TTS 角色...")
        get_edge_rolelist()
    if not os.path.exists(os.path.join(config.rootdir, 'elevenlabs.json')) or os.path.getsize(
            os.path.join(config.rootdir, 'elevenlabs.json')) == 0:
        print("正在获取 elevenlabs TTS 角色...")
        get_elevenlabs_role()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='cli.ini and source mp4')
    parser.add_argument('-c', type=str, help='cli.ini file absolute filepath', default=os.path.join(os.getcwd(), 'cli.ini'))
    parser.add_argument('-m', type=str, help='mp4 absolute filepath', default="")
    parser.add_argument('-cuda', action='store_true', help='Activates the cuda option')

    args = vars(parser.parse_args())

    config.settings['countdown_sec'] = 0
    cfg_file = args['c']
    if not os.path.exists(cfg_file):
        print('不存在配置文件 cli.ini' if config.defaulelang == 'zh' else "cli.ini file not exists")
        sys.exit()

    with open(cfg_file, 'r', encoding="utf-8") as f:
        for line in f.readlines():
            line = line.strip()
            if not line or line.startswith(";"):
                continue

            line = [x.strip() for x in line.split("=", maxsplit=1)]
            if len(line) != 2:
                continue
            if line[1] == 'false':
                config.params[line[0]] = False
            elif line[1] == 'true':
                config.params[line[0]] = True
            else:
                config.params[line[0]] = int(line[1]) if re.match(r'^\d+$', line[1]) else line[1]
    if not config.params['source_language']:
        config.params['source_language']='-'
    if not config.params['target_language']:
        config.params['target_language']='-'
    if not config.params.get('back_audio'):
        config.params['back_audio']='-'
    if args['cuda']:
        config.params['cuda'] = True
    if args['m'] and os.path.exists(args['m']):
        config.params['source_mp4'] = args['m']

    # 传多个视频的话,考虑支持批量处理
    if type(args['m']) == str:
        config.params['is_batch'] = False
    else:
        config.params['is_batch'] = True
        print("命令行批量处理暂未支持")
        sys.exit()

    if not config.params['source_mp4'] or not os.path.exists(config.params['source_mp4']):
        print(
            "必须在命令行或cli.ini文件设置 source_mp4(视频文件)的绝对路径" if config.defaulelang == 'zh' else "The absolute path of source_mp4 (video file) must be set on the command line or in the cli.ini file.")
        sys.exit()
    # 字幕嵌入时标记的语言，目标语言
    if config.params['target_language']!='-':
        config.params['subtitle_language'] = LANG_CODE[config.params['target_language']][1]
    # 语音识别语言
    if config.params['source_language']!='-':
        config.params['detect_language'] = LANG_CODE[config.params['source_language']][0]

    if config.params['translate_type'] == BAIDU_NAME:
        # baidu language code
        if not config.params["baidu_appid"] or not config.params["baidu_miyue"]:
            print(config.transobj['anerror'], config.transobj['baikeymust'])
            sys.exit()
    elif config.params['translate_type'] == TENCENT_NAME:
        # 腾讯翻译
        if not config.params["tencent_SecretId"] or not config.params["tencent_SecretKey"]:
            print(config.transobj['tencent_key'])
            sys.exit()
    elif config.params['translate_type'] == CHATGPT_NAME:
        # chatGPT 翻译 5 是中文语言名称，6是英文名称
        if not config.params["chatgpt_key"]:
            print(config.transobj['chatgptkeymust'])
            sys.exit()
    elif config.params['translate_type'] == AZUREGPT_NAME:
        # chatGPT 翻译
        if not config.params["azure_key"]:
            print('必须填写Azure key')
            sys.exit()
    elif config.params['translate_type'] == GEMINI_NAME:
        # chatGPT 翻译
        if not config.params["gemini_key"]:
            print(config.transobj['bixutianxie'] + ' Gemini key')
            sys.exit()
    elif config.params['translate_type'] == DEEPL_NAME or config.params['translate_type'] == DEEPLX_NAME:
        # DeepL翻译
        if config.params['translate_type'] == DEEPL_NAME and not config.params["deepl_authkey"]:
            print(config.transobj['deepl_authkey'])
            sys.exit()
        if config.params['translate_type'] == DEEPLX_NAME and not config.params["deeplx_address"]:
            print(config.transobj['setdeeplx_address'])
            sys.exit()

        if LANG_CODE[config.params['target_language']] == 'No':
            print(config.transobj['deepl_nosupport'])
            sys.exit()
    try:
        voice_rate = int(config.params['voice_rate'].strip().replace('+', '').replace('%', ''))
        config.params['voice_rate'] = f"+{voice_rate}%" if voice_rate >= 0 else f"-{voice_rate}%"
    except:
        config.params['voice_rate'] = '+0%'
    try:
        voice_silence = int(config.params['voice_silence'].strip())
        config.params['voice_silence'] = voice_silence
    except:
        config.params['voice_silence'] = '500'
    os.makedirs(os.path.join(os.getcwd(), 'tmp'), exist_ok=True)

    if config.params['proxy'].strip():
        config.proxy = config.params['proxy'].strip()
        set_proxy(config.proxy)
    config.current_status = 'ing'
    config.params['app_mode'] = 'cli'
    (base, ext) = os.path.splitext(config.params['source_mp4'].replace('\\', '/'))
    config.params['target_dir'] = os.path.dirname(base)
    obj_format = tools.format_video(config.params['source_mp4'].replace('\\', '/'), config.params['target_dir'])
    
    process_bar_data = [
        config.transobj['kaishichuli'],
        config.transobj['kaishishibie'],
        config.transobj['starttrans'],
        config.transobj['kaishipeiyin'],
        config.transobj['kaishihebing'],
    ]

    process_bar = tqdm(process_bar_data)
    try:
        video_task = TransCreate(config.params, obj_format)
        try:
            process_bar.set_description(process_bar_data[0])
            video_task.prepare()
            process_bar.update(1)
        except Exception as e:
            err=f'{config.transobj["yuchulichucuo"]}:' + str(e)
            print(err)
            sys.exit()
        try:
            process_bar.set_description(process_bar_data[1])
            video_task.recogn()
            process_bar.update(1)
        except Exception as e:
            err=f'{config.transobj["shibiechucuo"]}:' + str(e)
            print(err)
            sys.exit()
        try:
            process_bar.set_description(process_bar_data[2])
            video_task.trans()
            process_bar.update(1)
        except Exception as e:
            err=f'{config.transobj["fanyichucuo"]}:' + str(e)
            print(err)
            sys.exit()
        try:
            process_bar.set_description(process_bar_data[3])
            video_task.dubbing()
            process_bar.update(1)
        except Exception as e:
            err=f'{config.transobj["peiyinchucuo"]}:' + str(e)
            print(err)
            sys.exit()
        try:
            process_bar.set_description(process_bar_data[4])
            video_task.hebing()
            process_bar.update(1)
        except Exception as e:
            err=f'{config.transobj["hebingchucuo"]}:' + str(e)
            print(err)
            sys.exit()
        try:
            video_task.move_at_end()
            process_bar.update(1)
        except Exception as e:
            err=f'{config.transobj["hebingchucuo"]}:' + str(e)
            print(err)
            sys.exit()

        send_notification(config.transobj["zhixingwc"], f'"subtitles -> audio"')
        print(f'{"执行完成" if config.defaulelang == "zh" else "Succeed"} {video_task.targetdir_mp4}')
    except Exception as e:
        send_notification(e, f'{video_task.obj["raw_basename"]}')
        # 捕获异常并重新绑定回溯信息
        traceback.print_exc()

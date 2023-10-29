# -*- coding: utf-8 -*-
import sys
import re
import shutil
import argparse
import os
from tools import get_list_voices, get_large_audio_transcription, logger
import config


# 小写 并修改反斜线为正斜线
def lower(string):
    return re.sub(r'\\{1,}', '/', string.lower())


# 支持的所有配音角色
voice_list = get_list_voices()
# 所选语言下可用角色
voice_role_lower = []
# 语言代码
lang_code = {
    "zh-cn": ['zh-cn', 'chi'],
    "zh-tw": ['zh-tw', 'chi'],
    "en": ['en', 'eng'],
    "fr": ['fr', 'fre'],
    "de": ['de', 'ger'],
    "ja": ['ja', 'jpn'],
    "ko": ['ko', 'kor'],
    "ru": ['ru', 'rus'],
    "es": ['es', 'spa'],
    "th": ['th', 'tha'],
    "it": ['it', 'ita'],
    "pt": ['pt', 'por'],
    "vi": ['vi', 'vie'],
    "ar": ['ar', 'are']
}


# 设置可用的语音角色
def set_default_voice(target_language):
    global voice_role_lower
    try:
        vt = lang_code[target_language][0].split('-')[0]
        if vt not in voice_list:
            logger.error("The selected voice role does not exist. Please choose again.")
            return ["None"]
        li = voice_list[vt]
        for i in li:
            voice_role_lower.append(i.lower())
        return li
    except:
        pass
    return ["None"]


def error(text):
    logger.error(f"\n[error]: {text}\n")
    exit(1)


def init_args():
    parser = argparse.ArgumentParser(prog='video_translate',
                                     description='Seamlessly translate mangas into a chosen language')

    parser.add_argument('-mp4','--source_mp4', required=False, default=None, type=str, help='The path of the MP4 video to '
                                                                                     'be translated.')
    parser.add_argument('-td','--target_dir', default='', type=lower, help='Translated Video Save Directory')

    parser.add_argument('-sl','--source_language', default='en', type=lower, help='Original Language of the Video')
    parser.add_argument('-tl','--target_language', default='zh-cn', type=lower,
                        help='Target Language of the Video Translation')

    parser.add_argument('-p','--proxy', type=lower, default=None, help='Internet Proxy Address like http://127.0.0.1:10809')

    parser.add_argument('-vs','--voice_silence', default='300', type=int, help='the minimum length for any silent section')
    parser.add_argument('-va','--voice_autorate', default=False, action='store_true', help='If the translated audio is longer, can it be '
                                                                      'automatically accelerated to align with the '
                                                                      'original duration?')
    parser.add_argument('-wm','--whisper_model', default='base', help='From base to large, the effect gets better and the '
                                                                'speed slows down.')

    parser.add_argument('-vro','--voice_role', default='No', type=str, help='Select Voiceover Character Name')

    parser.add_argument('-vr','--voice_rate', default='0', type=str,
                        help='Specify Voiceover Speed, positive number for acceleration, negative number for '
                             'deceleration')

    parser.add_argument('-rb','--remove_background', action='store_true', help='Remove Background Music')
    parser.add_argument('-is','--insert_subtitle', action='store_true', help='Insert subtitle to video')

    args = vars(parser.parse_args())
    # print(args)
    # exit()

    if not args['source_mp4'] or not os.path.exists(args['source_mp4']) or not args['source_mp4'].lower().endswith(
            ".mp4"):
        error(
            f"The --source_mp4 parameter must be provided with the local file address of an mp4 file, ending with .mp4.{args['source_mp4']}")
    if args['source_language'] not in lang_code or args['target_language'] not in lang_code:
        error(
            f"The original language and target language for the video must be selected from the following options: {','.join(lang_code.keys())}")

    voice_role = set_default_voice(args['target_language'])
    if args['voice_role'] != 'No' and (args['voice_role'].lower() not in voice_role_lower):
        rolestr = "\n".join(voice_role[1:])
        error(
            f"The voice role does not exist..\nList of available voice roles\n{rolestr}")
    elif args['voice_role'].lower() in voice_role_lower:
        args['voice_role'] = voice_role[voice_role_lower.index(args['voice_role'].lower())]

    if not args['insert_subtitle'] and args['voice_role']=='No':
        error("The --insert_subtitle and --voice_role parameters need to be set at least one of them. \nChoose either embedding subtitles or voiceover characters, at least one of them needs to be selected.")

    rate = int(args['voice_rate'])
    if rate >= 0:
        args['voice_rate'] = f"+{args['voice_rate']}%"
    else:
        args['voice_rate'] = f"-{args['voice_rate']}%"

    if not args['target_dir']:
        args['target_dir'] = re.sub(r'\\{1,}', '/', os.path.join(os.path.dirname(args['source_mp4']), '_video_out'))
    if not os.path.exists(args['target_dir']):
        os.makedirs(args['target_dir'], exist_ok=True)

    if args['proxy']:
        os.environ['http_proxy'] = args['proxy'] if args['proxy'].startswith('http://') else f"http://{args['proxy']}"
        os.environ['https_proxy'] = os.environ['http_proxy']

    if args['whisper_model'] not in ["base", "small", "medium", "large"]:
        error(
            'It seems that the model input is incorrect. Please only select from "base", "small", "medium", or "large".')

    args['detect_language'] = lang_code[args['source_language']][0]
    args['source_language'] = lang_code[args['source_language']][0]

    args['subtitle_language'] = lang_code[args['target_language']][1]
    args['target_language'] = lang_code[args['target_language']][0]

    return args


#
def showprocess(name, text):
    logger.info(f"{name}:  {text}")


def running(p):
    # 所在目录
    dirname = os.path.dirname(p)
    # 去掉名字中的空格
    mp4nameraw = os.path.basename(p)
    mp4name = re.sub(r"\s", '', mp4nameraw, 0, re.I)
    if mp4nameraw != mp4name:
        os.rename(p, os.path.join(os.path.dirname(p), mp4name))
    #  整理后的视频名字不带后缀，和后缀，比如 1123  mp4
    noextname = os.path.splitext(mp4name)[0]
    # 字幕文件
    sub_name = f"{dirname}/{noextname}.srt"
    # 音频文件
    a_name = f"{dirname}/{noextname}.wav"
    if os.path.exists(sub_name):
        os.unlink(sub_name)

    if not os.path.exists(a_name):
        os.system(f"ffmpeg -i {dirname}/{mp4name} -acodec pcm_s16le -f s16le -ac 1  -f wav {a_name}")
    # 如果选择了去掉背景音，则重新整理为 a_name{voial}.wav
    if config.video_config['voice_role'] != 'No' and config.video_config['remove_background']:
        import warnings
        warnings.filterwarnings('ignore')
        from spleeter.separator import Separator
        separator = Separator('spleeter:2stems', multiprocess=False)
        separator.separate_to_file(a_name, destination=dirname, filename_format="{filename}{instrument}.{codec}")
        # 新的名字
        a_name = f"{dirname}/{noextname}vocals.wav"
    get_large_audio_transcription(a_name, mp4name, sub_name, showprocess)
    shutil.rmtree("./tmp")
    if os.path.exists(f"{dirname}/{noextname}vocals.wav"):
        os.unlink(f"{dirname}/{noextname}vocals.wav")
    if os.path.exists(f"{dirname}/##{noextname}vocals_tmp"):
        shutil.rmtree(f"{dirname}/##{noextname}vocals_tmp")
    if os.path.exists(f"{dirname}/{noextname}.wav"):
        os.unlink(f"{dirname}/{noextname}.wav")
    if os.path.exists(f"{dirname}/##{noextname}_tmp"):
        shutil.rmtree(f"{dirname}/##{noextname}_tmp")


if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1][-10:] == 'show_voice':
        for it in voice_list:
            print(f"{it}: {', '.join(voice_list[it][1:])}")
        exit(0)
    config.video_config = init_args()
    config.current_status = "ing"
    if not os.path.exists(os.path.join(config.rootdir, "tmp")):
        os.mkdir(os.path.join(config.rootdir, 'tmp'))
    running(config.video_config['source_mp4'])

# -*- coding: utf-8 -*-
import sys
import argparse
import os
import warnings

warnings.filterwarnings('ignore')
from videotrans.util.tools import get_edge_rolelist, get_large_audio_transcriptioncli, logger, runffmpeg,delete_temp
from videotrans.configure import config
from videotrans.configure.language import clilanglist


# lower and replace \\
def lower(string):
    return string.lower().replace('\\', '/')


# voice role list
config.voice_list = get_edge_rolelist()
# voice role by current language
voice_role_lower = []


# set current language voice role
def set_default_voice(target_language):
    global voice_role_lower
    try:
        vt = clilanglist[target_language][0].split('-')[0]
        if vt not in config.voice_list:
            logger.error("The selected voice role does not exist. Please choose again.")
            return ["No"]
        li = config.voice_list[vt]
        for i in li:
            voice_role_lower.append(i.lower())
        return li
    except:
        pass
    return ["No"]


# exit
def error(text):
    logger.error(f"\n[error]: {text}\n")
    print(f"\n[error]: {text}\n")
    exit(1)


# process args by sys.args
def init_args():
    parser = argparse.ArgumentParser(prog='video_translate',
                                     description='Seamlessly translate mangas into a chosen language')

    parser.add_argument('-mp4', '--source_mp4', required=False, default=None, type=str,
                        help='The path of the MP4 video to '
                             'be translated.')
    parser.add_argument('-td', '--target_dir', default='', type=lower, help='Translated Video Save Directory')

    parser.add_argument('-sl', '--source_language', default='en', type=lower, help='Original Language of the Video')
    parser.add_argument('-tl', '--target_language', default='zh-cn', type=lower,
                        help='Target Language of the Video Translation')

    parser.add_argument('-p', '--proxy', type=lower, default=None,
                        help='Internet Proxy Address like http://127.0.0.1:10809')

    parser.add_argument('-vs', '--voice_silence', default='500', type=int,
                        help='the minimum length for any silent section')
    parser.add_argument('-va', '--voice_autorate', default=False, action='store_true',
                        help='If the translated audio is longer, can it be '
                             'automatically accelerated to align with the '
                             'original duration?')
    parser.add_argument('-wm', '--whisper_model', default='base',
                        help='From base to large, the effect gets better and the '
                             'speed slows down.')

    parser.add_argument('-vro', '--voice_role', default='No', type=str, help='Select Voiceover Character Name')

    parser.add_argument('-vr', '--voice_rate', default='0', type=str,
                        help='Specify Voiceover Speed, positive number for acceleration, negative number for '
                             'deceleration')

    parser.add_argument('-st', '--subtitle_type', default=0, type=int, help='Embedded subtitles display regardless , doesnot hide them.Softsubtitles:If player supports it, you can control display or hiding of .To display subtitles  when playing in website,  choose embeded subtitles option.')

    args = vars(parser.parse_args())

    if not args['source_mp4'] or not os.path.exists(args['source_mp4']) or not args['source_mp4'].lower().endswith(
            ".mp4"):
        error(
            f"The --source_mp4 parameter must be provided with the local file address of an mp4 file, ending with .mp4.{args['source_mp4']}")
    args['source_mp4']=args['source_mp4'].replace('\\','/')
    if args['source_language'] not in clilanglist or args['target_language'] not in clilanglist:
        error(
            f"The original language and target language for the video must be selected from the following options: {','.join(clilanglist.keys())}")

    voice_role = set_default_voice(args['target_language'])
    if args['voice_role'] != 'No' and (args['voice_role'].lower() not in voice_role_lower):
        rolestr = "\n".join(voice_role[1:])
        error(
            f"The voice role does not exist..\nList of available voice roles\n{rolestr}")
    elif args['voice_role'].lower() in voice_role_lower:
        args['voice_role'] = voice_role[voice_role_lower.index(args['voice_role'].lower())]

    if args['subtitle_type']<1 and args['voice_role'] == 'No':
        error(
            "The --subtitle_type and --voice_role parameters need to be set at least one of them. \nChoose either embedding subtitles or voiceover characters, at least one of them needs to be selected.")

    rate = int(args['voice_rate'])
    if rate >= 0:
        args['voice_rate'] = f"+{args['voice_rate']}%"
    else:
        args['voice_rate'] = f"-{args['voice_rate']}%"

    if not args['target_dir']:
        args['target_dir'] = os.path.join(os.path.dirname(args['source_mp4']), '_video_out').replace('\\', '/')
    if not os.path.exists(args['target_dir']):
        os.makedirs(args['target_dir'], exist_ok=True)
    args['target_dir']=args['target_dir'].replace('\\','/')
    if args['proxy']:
        os.environ['http_proxy'] = args['proxy'] if args['proxy'].startswith('http://') else f"http://{args['proxy']}"
        os.environ['https_proxy'] = os.environ['http_proxy']

    if args['whisper_model'] not in ["base", "small", "medium", "large","large-v3"]:
        error(
            'It seems that the model input is incorrect. Please only select from "base", "small", "medium","large-v3".')

    args['detect_language'] = clilanglist[args['source_language']][0]
    args['source_language'] = clilanglist[args['source_language']][0]

    args['subtitle_language'] = clilanglist[args['target_language']][1]
    args['target_language'] = clilanglist[args['target_language']][0]

    return args


# show
def showprocess(text, type="logs"):
    logger.info(f"{type}:  {text}")


def running(p):
    # remove whitespace
    mp4name = os.path.basename(p)
    #  no ext eg. 1123  mp4
    noextname,mp4ext = os.path.splitext(mp4name)
    # subtitle filepath
    a_name = f"{config.rootdir}/tmp/{noextname}/{noextname}.wav"
    if not os.path.exists(a_name) or os.path.getsize(a_name)==0:
        runffmpeg([
                   "-y",
                   "-i",
                   f'{p}',
                   f'{a_name}'
    ])

    get_large_audio_transcriptioncli(noextname, mp4ext, showprocess)
    # del temp files
    delete_temp(noextname)


if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1][-10:] == 'show_voice':
        for it in config.voice_list:
            print(f"[Error]: {it}: {', '.join(config.voice_list[it][1:])}")
        exit(1)
    config.video.update(init_args())
    config.current_status = "ing"
    if not os.path.exists(os.path.join(config.rootdir, "tmp")):
        os.mkdir(os.path.join(config.rootdir, 'tmp'))
    running(config.video['source_mp4'])

import math
import os
import shutil
import time
import traceback

from videotrans.util import tools

import librosa
import soundfile as sf
import torch
from videotrans.separate.vr import AudioPre
from videotrans.configure import config
from videotrans.util import tools
import hashlib


def uvr(*,model_name=None, save_root=None, inp_path=None,source="logs",btnkey=None):
    infos = []
    try:
        func = AudioPre
        pre_fun = func(
            agg=10,
            model_path=os.path.join(config.rootdir, f"uvr5_weights/{model_name}.pth"),
            device="cuda" if torch.cuda.is_available() else "cpu",
            is_half=False,
            source=source
        )
        done = 0
        try:
            y, sr = librosa.load(inp_path, sr=None)
            info = sf.info(inp_path)
            channels = info.channels
            if channels == 2 and sr == 16000:
                need_reformat = 0
                pre_fun._path_audio_(
                    inp_path,
                    ins_root=save_root,btnkey=btnkey
                )
                done = 1
            else:
                need_reformat = 1
        except:
            need_reformat = 1
            traceback.print_exc()
        if need_reformat == 1:
            tmp_path = "%s/%s.reformatted.wav" % (
                os.path.join(os.environ["TEMP"]),
                f'{os.path.basename(inp_path)}-{time.time()}',
            )
            tools.runffmpeg([
                "-y",
                "-i",
                inp_path,
                "-ar",
                "44100",
                tmp_path
            ])
            inp_path = tmp_path
        try:
            if done == 0:
                pre_fun._path_audio_(
                    inp_path, ins_root=save_root,btnkey=btnkey
                )
            infos.append("%s->Success" % (os.path.basename(inp_path)))
            yield "\n".join(infos)
        except:
            try:
                if done == 0:
                    pre_fun._path_audio_(
                        inp_path, ins_root=save_root,btnkey=btnkey
                    )
                infos.append("%s->Success" % (os.path.basename(inp_path)))
                yield "\n".join(infos)
            except:
                infos.append(
                    "%s->%s" % (os.path.basename(inp_path), traceback.format_exc())
                )
                yield "\n".join(infos)
    except:
        infos.append(traceback.format_exc())
        yield "\n".join(infos)
    finally:
        try:
            del pre_fun.model
            del pre_fun
        except Exception:
            traceback.print_exc()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    yield "\n".join(infos)




def convert_to_pure_eng_num(string):
    # 将输入字符串转换为UTF-8编码的bytes
    encoded_string = string.encode('utf-8')
    # 创建一个md5哈希对象
    hasher = hashlib.md5()
    # 用输入字符串的bytes更新哈希对象
    hasher.update(encoded_string)
    # 获取哈希的十六进制字符串形式
    hex_digest = hasher.hexdigest()
    return hex_digest


# path 是需要保存vocal.wav的目录
def start(audio,path,source="logs",btnkey=None):
    dist=int(config.settings['separate_sec'])
    try:
        # 获取总时长秒
        sec=tools.get_audio_time(audio)
        #if sec<=dist:
        gr = uvr(model_name="HP2", save_root=path, inp_path=audio,source=source,btnkey=btnkey)
        print(next(gr))
        print(next(gr))
    except Exception as e:
        msg=f"保留背景音:{str(e)}"
        raise Exception(msg)



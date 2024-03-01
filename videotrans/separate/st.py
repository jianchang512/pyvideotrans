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


def uvr(*,model_name=None, save_root=None, inp_path=None,source="logs"):
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
            if channels == 2 and sr == 44100:
                need_reformat = 0
                pre_fun._path_audio_(
                    inp_path, save_root
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
                    inp_path, save_root
                )
            infos.append("%s->Success" % (os.path.basename(inp_path)))
            yield "\n".join(infos)
        except:
            try:
                if done == 0:
                    pre_fun._path_audio_(
                        inp_path, save_root
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
        except:
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
def start(audio,path,source="logs"):
    dist=int(config.settings['separate_sec'])
    try:
        # 获取总时长秒
        sec=tools.get_audio_time(audio)
        if sec<=dist:
            gr = uvr(model_name="HP2", save_root=path, inp_path=audio,source=source)
            print(next(gr))
            print(next(gr))
            return
        length=math.ceil(sec/dist)
        result_vocal=[]
        result_instr=[]
        #创建临时文件
        flag=convert_to_pure_eng_num(f'{audio}-{path}-{source}-{dist}-{sec}')
        tmp_path=os.path.join(config.TEMP_DIR,f'separate{flag}')
        os.makedirs(tmp_path,exist_ok=True)
        for i in range(length):
            #在 tmp_path 下创建新目录，存放各个 vocal.wav
            save_root=os.path.join(tmp_path,f'{i}')
            os.makedirs(save_root,exist_ok=True)
            #新音频存放
            inp_path=os.path.join(tmp_path,f'{i}.wav')
            if not os.path.exists(inp_path):
                print(f'{inp_path=}')
                cmd=['-y','-i',audio,'-ss',tools.ms_to_time_string(seconds=i*dist).replace(',','.')]
                if i<length-1:
                    #不是最后一个
                    cmd+=['-t',f'{dist}']
                cmd.append(inp_path)
                print(f'{cmd=}')
                tools.runffmpeg(cmd)

            
            file_vocal=os.path.join(save_root,'vocal.wav').replace('\\','/')
            file_instr= os.path.join(save_root,'instrument.wav').replace('\\','/')

            tools.set_process(f'{config.transobj["Start Separate"]}{config.transobj["pianduan"]} {i+1}/{length}',source)
            if not os.path.exists(file_vocal) or not os.path.exists(file_instr):
                gr = uvr(model_name="HP2", save_root=save_root, inp_path=inp_path,source=source)
                print(next(gr))
                print(next(gr))
                        
            result_vocal.append(f"file '{file_vocal}'")

            result_instr.append(f"file '{file_instr}'")
        concat_vocal=os.path.join(tmp_path,'vocal.txt')
        with open(concat_vocal,'w',encoding='utf-8') as f:
            f.write("\n".join(result_vocal))
        if not os.path.exists(concat_vocal):
            raise Exception('抽离背景音失败'+('请取消 保留背景音 选项' if source=='logs' else "") )
        tools.runffmpeg(['-y','-f','concat','-safe','0','-i',concat_vocal,os.path.normpath(os.path.join(path,'vocal.wav'))],disable_gpu=True,is_box=True)

        concat_instr=os.path.join(tmp_path,'instr.txt')
        with open(concat_instr,'w',encoding='utf-8') as f:
            f.write("\n".join(result_instr))
        if not os.path.exists(concat_instr):
            raise Exception('抽离背景音失败'+('请取消 保留背景音 选项' if source=='logs' else "") )
        tools.runffmpeg(['-y','-f','concat','-safe','0','-i',os.path.normpath(concat_instr),os.path.normpath(os.path.join(path,'instrument.wav'))],disable_gpu=True,is_box=True)
    except Exception as e:
        msg=f"分离背景音失败:{str(e)}"
        print(msg)
        raise Exception(msg)



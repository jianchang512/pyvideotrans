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




# path 是需要保存vocal.wav的目录
def start(audio,path):
    dist=int(config.settings['separate_sec'])
    try:
        # 获取总时长秒
        sec=tools.get_audio_time(audio)
        if sec<=dist:
            gr = uvr(model_name="HP2", save_root=path, inp_path=audio)
            print(next(gr))
            print(next(gr))
            return
        length=math.ceil(sec/dist)
        result_vocal=[]
        result_instr=[]
        #创建临时文件
        tmp_path=os.path.join(config.TEMP_DIR,f'separate{time.time()}')
        os.makedirs(tmp_path,exist_ok=True)
        for i in range(length):
            #在tmp_path下创建新目录，存放各个 vocal.wav
            save_root=os.path.join(tmp_path,f'{i}')
            os.makedirs(save_root,exist_ok=True)
            #新音频存放
            inp_path=os.path.join(tmp_path,f'{i}.wav')
            print(f'{inp_path=}')
            cmd=['-y','-i',audio,'-ss',tools.ms_to_time_string(seconds=i*dist).replace(',','.')]
            if i<length-1:
                #不是最后一个
                cmd+=['-t',f'{dist}']
            cmd.append(inp_path)
            print(f'{cmd=}')
            tools.runffmpeg(cmd)
            # continue
            tools.set_process(f'{config.transobj["Start Separate"]}{config.transobj["pianduan"]} {i+1}/{length}')
            gr = uvr(model_name="HP2", save_root=save_root, inp_path=inp_path)
            print(next(gr))
            print(next(gr))
            file_vocal=os.path.normpath(os.path.join(save_root,'vocal.wav'))
            result_vocal.append(f"file '{file_vocal}'")

            file_instr= os.path.normpath(os.path.join(save_root,'instrument.wav'))
            result_instr.append(f"file '{file_instr}'")
        concat_vocal=os.path.join(tmp_path,'vocal.txt')
        with open(concat_vocal,'w',encoding='utf-8') as f:
            f.write("\n".join(result_vocal))
        tools.runffmpeg(['-y','-f','concat','-safe','0','-i',concat_vocal,os.path.join(path,'vocal.wav')])

        concat_instr=os.path.join(tmp_path,'instr.txt')
        with open(concat_instr,'w',encoding='utf-8') as f:
            f.write("\n".join(result_instr))
        tools.runffmpeg(['-y','-f','concat','-safe','0','-i',concat_instr,os.path.join(path,'instrument.wav')])
        # try:
        #     shutil.rmtree(tmp_path)
        # except:
        #     pass
    except Exception as e:
        msg=f"separate vocal and background music:{str(e)}"
        print(msg)
        raise Exception(msg)



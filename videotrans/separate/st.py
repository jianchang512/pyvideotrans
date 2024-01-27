import os
import time
import traceback

from videotrans.util import tools

import librosa
import soundfile as sf
import torch
from videotrans.separate.vr import AudioPre
from videotrans.configure import config


def uvr(*,model_name=None, save_root=None, inp_path=None):
    infos = []
    try:
        func = AudioPre
        pre_fun = func(
            agg=10,
            model_path=os.path.join(config.rootdir, f"uvr5_weights/{model_name}.pth"),
            device="cuda" if torch.cuda.is_available() else "cpu",
            is_half=False,
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



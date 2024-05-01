import os

import librosa
import numpy as np
import soundfile as sf
import torch
from videotrans.separate.lib_v5 import nets_61968KB as Nets
from videotrans.separate.lib_v5 import spec_utils
from videotrans.separate.lib_v5.model_param_init import ModelParameters
from videotrans.separate.utils import inference
from videotrans.configure import config

class AudioPre:
    def __init__(self, agg, model_path, device, is_half, tta=False,source="logs"):
        self.model_path = model_path
        self.device = device
        self.source=source
        self.data = {
            # Processing Options
            "postprocess": False,
            "tta": tta,
            # Constants
            "window_size": 512,
            "agg": agg,
            "high_end_process": "mirroring",
        }
        # mp = ModelParameters("%s/uvr5_weights/modelparams/4band_v2.json"%config.rootdir)
        mp = ModelParameters("%s/uvr5_weights/modelparams/2band_44100_lofi.json"%config.rootdir)
        model = Nets.CascadedASPPNet(mp.param["bins"] * 2)
        cpk = torch.load(model_path, map_location="cpu")
        model.load_state_dict(cpk)
        model.eval()
        if is_half:
            model = model.half().to(device)
        else:
            model = model.to(device)

        self.mp = mp
        self.model = model

    def _path_audio_(
        self, music_file, ins_root=None, format="wav", is_hp3=False,btnkey=None
    ):
        if ins_root is None:
            return "No save root."
        name = os.path.splitext(os.path.basename(music_file))[0]
        if ins_root is not None:
            os.makedirs(ins_root, exist_ok=True)
        vocal_root=ins_root
        # if vocal_root is not None:
        #     os.makedirs(vocal_root, exist_ok=True)
        X_wave, y_wave, X_spec_s, y_spec_s = {}, {}, {}, {}
        bands_n = len(self.mp.param["band"])

        for d in range(bands_n, 0, -1):
            if self.source!='logs' and config.separate_status !='ing':
                return
            if self.source=='logs' and config.current_status!='ing':
                return
            bp = self.mp.param["band"][d]
            if d == bands_n:  # high-end band
                (
                    X_wave[d],
                    _,
                ) = librosa.core.load(
                    music_file,
                    sr=bp["sr"],
                    mono=False,
                    dtype=np.float32,
                    res_type=bp["res_type"],
                )
                if X_wave[d].ndim == 1:
                    X_wave[d] = np.asfortranarray([X_wave[d], X_wave[d]])
            else:  # lower bands
                X_wave[d] = librosa.core.resample(
                    X_wave[d + 1],
                    orig_sr=self.mp.param["band"][d + 1]["sr"],
                    target_sr=bp["sr"],
                    res_type=bp["res_type"],
                )
            # Stft of wave source
            X_spec_s[d] = spec_utils.wave_to_spectrogram_mt(
                X_wave[d],
                bp["hl"],
                bp["n_fft"],
                self.mp.param["mid_side"],
                self.mp.param["mid_side_b2"],
                self.mp.param["reverse"],
            )
            # pdb.set_trace()
            if d == bands_n and self.data["high_end_process"] != "none":
                input_high_end_h = (bp["n_fft"] // 2 - bp["crop_stop"]) + (
                    self.mp.param["pre_filter_stop"] - self.mp.param["pre_filter_start"]
                )
                input_high_end = X_spec_s[d][
                    :, bp["n_fft"] // 2 - input_high_end_h : bp["n_fft"] // 2, :
                ]

        X_spec_m = spec_utils.combine_spectrograms(X_spec_s, self.mp)
        aggresive_set = float(self.data["agg"] / 100)
        aggressiveness = {
            "value": aggresive_set,
            "split_bin": self.mp.param["band"][1]["crop_stop"],
        }
        with torch.no_grad():
            pred, X_mag, X_phase = inference(
                X_spec_m, self.device, self.model, aggressiveness, self.data,self.source,btnkey=btnkey
            )
        # Postprocess
        if self.data["postprocess"]:
            pred_inv = np.clip(X_mag - pred, 0, np.inf)
            pred = spec_utils.mask_silence(pred, pred_inv)
        y_spec_m = pred * X_phase
        v_spec_m = X_spec_m - y_spec_m

        if ins_root is not None:
            if self.data["high_end_process"].startswith("mirroring"):
                input_high_end_ = spec_utils.mirroring(
                    self.data["high_end_process"], y_spec_m, input_high_end, self.mp
                )
                wav_instrument = spec_utils.cmb_spectrogram_to_wave(
                    y_spec_m, self.mp, input_high_end_h, input_high_end_
                )
            else:
                wav_instrument = spec_utils.cmb_spectrogram_to_wave(y_spec_m, self.mp)
            config.logger.info("%s instruments done" % name)
            if is_hp3 == True:
                head = "vocal"
            else:
                head = "instrument"
            if format in ["wav", "flac"]:
                sf.write(
                    os.path.join(
                        ins_root,
                        head + ".{}".format(format),
                    ),
                    (np.array(wav_instrument) * 32768).astype("int16"),
                    self.mp.param["sr"],
                )  #

        if vocal_root is not None:
            if is_hp3 == True:
                head = "instrument"
            else:
                head = "vocal"
            if self.data["high_end_process"].startswith("mirroring"):
                input_high_end_ = spec_utils.mirroring(
                    self.data["high_end_process"], v_spec_m, input_high_end, self.mp
                )
                wav_vocals = spec_utils.cmb_spectrogram_to_wave(
                    v_spec_m, self.mp, input_high_end_h, input_high_end_
                )
            else:
                wav_vocals = spec_utils.cmb_spectrogram_to_wave(v_spec_m, self.mp)
            config.logger.info("%s vocals done" % name)
            if format in ["wav", "flac"]:
                sf.write(
                    os.path.join(
                        vocal_root,
                        head + ".{}".format( format),
                    ),
                    (np.array(wav_vocals) * 32768).astype("int16"),
                    self.mp.param["sr"],
                )


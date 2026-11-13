from pathlib import Path
import tempfile

from videotrans.configure.config import ROOT_DIR, settings
from videotrans.util.gpus import (
    get_audiocpp_backend_args,
    get_vulkan_device_index,
    get_vulkan_devices,
    getset_gpu,
    is_vulkan_available,
    resolve_torch_device,
    should_use_vulkan,
)
from videotrans.util.whisper_vulkan import (
    PyWhisperCppModel,
    get_ggml_model_info,
    is_pywhispercpp_available,
    should_use_whisper_vulkan,
)


def test_vulkan_gpu_detection():
    devices = get_vulkan_devices()
    assert len(devices) >= 1
    assert is_vulkan_available() is True
    assert getset_gpu() >= 1

    # Auto/vulkan should pick the highest-memory Vulkan GPU (AMD Radeon 8060S = index 1 on dual-GPU host)
    auto_idx = get_vulkan_device_index("auto")
    assert auto_idx in [d["index"] for d in devices]
    assert get_vulkan_device_index("vulkan:0") == 0
    if len(devices) > 1:
        assert get_vulkan_device_index("vulkan:1") == 1


def test_audiocpp_backend_args():
    assert get_audiocpp_backend_args("cpu") == ["--backend", "cpu"]
    vk0_args = get_audiocpp_backend_args("vulkan:0")
    assert vk0_args == ["--backend", "vulkan", "--device", "0"]
    auto_args = get_audiocpp_backend_args("auto")
    assert auto_args[:2] == ["--backend", "vulkan"]
    assert auto_args[2] == "--device"


def test_ggml_model_mapping():
    assert get_ggml_model_info("tiny")[0] == "ggml-tiny.bin"
    assert get_ggml_model_info("large-v3-turbo")[0] == "ggml-large-v3-turbo.bin"
    assert get_ggml_model_info("distil-large-v3")[0] == "ggml-distil-large-v3.bin"
    assert get_ggml_model_info("custom-fine-tuned") is None

    assert should_use_whisper_vulkan("tiny", device_name="vulkan") is True
    assert should_use_whisper_vulkan("custom-fine-tuned", device_name="vulkan") is False


def test_pywhispercpp_vulkan_transcribe():
    assert is_pywhispercpp_available() is True
    model_path = f"{ROOT_DIR}/models/ggml-tiny.bin"
    audio_path = f"{ROOT_DIR}/f5-tts/en_female_1.wav"

    model = PyWhisperCppModel(
        model_path,
        device="vulkan",
        device_index=get_vulkan_device_index("vulkan"),
        compute_type="default",
    )
    segments, info = model.transcribe(
        audio_path,
        beam_size=2,
        best_of=2,
        vad_filter=True,
        word_timestamps=True,
        language="en",
    )
    segs = list(segments)
    assert len(segs) >= 1
    assert info.language == "en"
    full_text = " ".join(s.text for s in segs).lower()
    assert "calcium" in full_text or "blood pressure" in full_text
    assert len(segs[0].words) >= 1
    assert segs[0].words[0].end >= segs[0].words[0].start


def test_stt_faster_vulkan_end_to_end():
    from videotrans.process.stt_faster import faster_whisper

    with tempfile.TemporaryDirectory() as tmpdir:
        srt_out = Path(tmpdir) / "out.srt"
        log_out = Path(tmpdir) / "test.log"
        log_out.touch()
        raws, err = faster_whisper(
            detect_language="en",
            model_name="tiny",
            logs_file=str(log_out),
            is_cuda=True,
            audio_file=f"{ROOT_DIR}/f5-tts/en_female_1.wav",
            local_dir=f"{ROOT_DIR}/models/ggml-tiny.bin",
            compute_type="default",
            beam_size=2,
            best_of=2,
            subtitle_srt=str(srt_out),
            raw_device_name="vulkan",
            device_name="auto",
        )
        assert err is None
        assert len(raws) >= 1
        assert any("calcium" in item["text"].lower() or "blood" in item["text"].lower() for item in raws)


def test_cpp_recogn_vulkan():
    from videotrans.recognition._cpp import CPPRecogn

    orig_dev = settings.get("device_name", "auto")
    try:
        settings["device_name"] = "vulkan"
        with tempfile.TemporaryDirectory() as tmpdir:
            rec = CPPRecogn(
                detect_language="en",
                audio_file=f"{ROOT_DIR}/f5-tts/en_female_1.wav",
                cache_folder=tmpdir,
                model_name="ggml-tiny.bin",
                is_cuda=True,
            )
            srts = rec._exec()
            assert len(srts) >= 1
            assert any("calcium" in item["text"].lower() or "blood" in item["text"].lower() for item in srts)
    finally:
        settings["device_name"] = orig_dev


def test_resolve_torch_device_never_maps_vulkan_to_cuda():
    assert should_use_vulkan("vulkan:1", is_cuda=True) is True
    assert should_use_vulkan("cpu", is_cuda=True) is False
    assert should_use_vulkan("cuda", is_cuda=True) is False
    assert resolve_torch_device("vulkan", is_cuda=True) == "cpu"
    assert resolve_torch_device("vulkan:1", is_cuda=True) == "cpu"
    assert resolve_torch_device("cpu", is_cuda=True) == "cpu"


def test_hymt2_vulkan_translation_zero_cuda():
    import torch
    from videotrans.translator._hymt2 import HYMT2

    orig_dev = settings.get("device_name", "auto")
    try:
        settings["device_name"] = "vulkan:1"
        tr_inst = HYMT2(
            text_list=[{"text": "Hello, welcome to the video translation tool.", "line": 1}],
            target_code="zh-cn",
            source_code="en",
            is_cuda=True,
        )
        tr_inst._download()
        assert tr_inst.hy.use_vulkan is True
        if torch.cuda.is_available():
            assert torch.cuda.memory_allocated() == 0
        out = tr_inst._item_task("Hello, welcome to the video translation tool.")
        assert out and len(out.strip()) > 0
        tr_inst._unload()
    finally:
        settings["device_name"] = orig_dev


def test_omnivoice_builtin_routes_to_audiocpp_vulkan():
    import torch
    from videotrans import tts

    orig_dev = settings.get("device_name", "auto")
    try:
        settings["device_name"] = "vulkan:1"
        with tempfile.TemporaryDirectory() as tmpdir:
            out_wav = Path(tmpdir) / "line1.wav"
            queue_tts = [
                {
                    "text": "Hello world, testing OmniVoice on Vulkan.",
                    "role": "clone",
                    "filename": str(out_wav),
                    "ref_wav": f"{ROOT_DIR}/f5-tts/en_female_1.wav",
                    "ref_text": "Yesterday, a friend told me that a newly opened restaurant nearby has great food, and we agreed to try it together this weekend.",
                }
            ]
            tts.run(
                queue_tts=queue_tts,
                language="en",
                tts_type=tts.OMNIVOICE_TTS,
                is_cuda=True,
            )
            assert out_wav.exists() and out_wav.stat().st_size > 1000
            if torch.cuda.is_available():
                assert torch.cuda.memory_allocated() == 0
    finally:
        settings["device_name"] = orig_dev


def test_exec_audiocpp_falls_back_to_cpu_on_gpu_failure(monkeypatch):
    from videotrans.util import help_misc

    calls = []

    def fake_run(cmd):
        calls.append(list(cmd))
        if "--backend" in cmd and cmd[cmd.index("--backend") + 1] != "cpu":
            return 1, "", "ggml_vulkan: ErrorOutOfDeviceMemory", False
        return 0, "ok", "", False

    orig_dev = settings.get("device_name", "auto")
    try:
        settings["device_name"] = "vulkan:1"
        monkeypatch.setattr(help_misc, "_run_audiocpp_proc", fake_run)
        assert help_misc.exec_audiocpp(["audiocpp_cli", "--backend", "best", "--text", "hi"]) is True
        assert len(calls) == 2
        assert calls[0][:4] == ["audiocpp_cli", "--backend", "vulkan", "--device"]
        assert calls[1] == ["audiocpp_cli", "--backend", "cpu", "--text", "hi"]
    finally:
        settings["device_name"] = orig_dev


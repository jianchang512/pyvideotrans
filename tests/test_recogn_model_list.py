import pytest

from videotrans import recognition
from videotrans.configure import constants
from videotrans.configure.config import settings

# the model lists that cfg.json held before v4.16
SAVED_LISTS = ("model_list", "Whisper_cpp_models", "Whisper_net_models")

# the local Whisper channels and the models of their drop-down
CHANNELS = [
    pytest.param(
        recognition.Whisper_CPP, constants.WHISPER_CPP_MODELS, id="whisper.cpp"
    ),
    pytest.param(
        recognition.WHISPER_NET, constants.WHISPER_NET_MODELS, id="Whisper.NET"
    ),
    pytest.param(
        recognition.FASTER_WHISPER, constants.WHISPER_MODELS, id="faster-whisper"
    ),
]


@pytest.mark.parametrize("recogn_type, models", CHANNELS)
def test_new_install_lists_the_models(monkeypatch, recogn_type, models):
    # the cfg.json that a new install writes has none of these keys
    for key in SAVED_LISTS:
        monkeypatch.delattr(settings, key, raising=False)

    assert recognition.get_model_by_type(recogn_type) == models.split(",")


@pytest.mark.parametrize("recogn_type, models", CHANNELS)
def test_upgraded_install_lists_the_built_in_models(monkeypatch, recogn_type, models):
    # cfg.json keeps the lists that an older version saved, with any names
    # that were added to them
    for key, saved in (
        ("model_list", constants.WHISPER_MODELS + ",my-model"),
        ("Whisper_cpp_models", constants.WHISPER_CPP_MODELS + ",ggml-my-model.bin"),
        ("Whisper_net_models", constants.WHISPER_NET_MODELS + ",ggml-my-model.bin"),
    ):
        monkeypatch.setattr(settings, key, saved, raising=False)

    assert recognition.get_model_by_type(recogn_type) == models.split(",")

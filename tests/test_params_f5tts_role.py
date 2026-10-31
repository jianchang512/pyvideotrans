import json

from videotrans.configure import _app_params
from videotrans.configure._app_params import AppParams

# the bundled reference audios, one "name.wav#reference text" per line
DEFAULT_ROLES = AppParams._get_defaults()["f5tts_role"].split("\n")
DEFAULT_WAVS = [role.split("#")[0] for role in DEFAULT_ROLES]
MY_ROLE = "myvoice.wav#Hello there."


def _load_roles(monkeypatch, tmp_path, saved_roles, wavs):
    # the reference audios are looked up in {ROOT_DIR}/f5-tts
    monkeypatch.setattr(_app_params, "ROOT_DIR", tmp_path.as_posix())
    (tmp_path / "f5-tts").mkdir()
    for wav in wavs:
        (tmp_path / "f5-tts" / wav).write_bytes(b"")
    saved = AppParams._get_defaults()
    if saved_roles is None:
        # a params.json without the list
        del saved["f5tts_role"]
    else:
        saved["f5tts_role"] = "\n".join(saved_roles)
    json_path = tmp_path / "params.json"
    json_path.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
    # config.py does the same with videotrans/params.json at every start
    params = AppParams(_json_path=json_path.as_posix())
    return params.f5tts_role.split("\n")


def test_deleted_bundled_voices_stay_deleted(monkeypatch, tmp_path):
    # the bundled voices were removed from the list and from f5-tts
    roles = _load_roles(monkeypatch, tmp_path, [MY_ROLE], ["myvoice.wav"])

    assert roles == [MY_ROLE]


def test_saved_order_and_edited_text_are_kept(monkeypatch, tmp_path):
    edited = "zh_female_cn.wav#Edited reference text."

    roles = _load_roles(
        monkeypatch, tmp_path, [edited, MY_ROLE], DEFAULT_WAVS + ["myvoice.wav"]
    )

    # followed by the bundled voices that weren't listed, in their default order
    assert roles == [edited, MY_ROLE] + [
        role for role in DEFAULT_ROLES if not role.startswith("zh_female_cn.wav#")
    ]


def test_bundled_voice_missing_from_the_list_is_added(monkeypatch, tmp_path):
    # e.g. a voice that a newer version bundles
    roles = _load_roles(monkeypatch, tmp_path, DEFAULT_ROLES[:-1], DEFAULT_WAVS)

    assert roles == DEFAULT_ROLES


def test_params_json_without_the_list(monkeypatch, tmp_path):
    roles = _load_roles(monkeypatch, tmp_path, None, DEFAULT_WAVS)

    assert roles == DEFAULT_ROLES

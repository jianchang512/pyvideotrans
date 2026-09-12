"""WebUI localization contracts without importing Qt, Gradio or model runtimes."""

import ast
import inspect
import json
from pathlib import Path
from string import Formatter
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
WEBUI = ast.parse((ROOT / "webui.py").read_text(encoding="utf-8"))


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        assert key not in result, f"Duplicate translation: {key}"
        result[key] = value
    return result


def _catalog():
    return json.loads(
        (ROOT / "videotrans/language/fr_FR.json").read_text(encoding="utf-8"),
        object_pairs_hook=_unique_object,
    )


def _exec(nodes, namespace, filename=ROOT / "webui.py"):
    # Only repository-owned AST is executed, never application/user input.
    exec(  # noqa: S102
        compile(ast.Module(body=nodes, type_ignores=[]), str(filename), "exec"),
        namespace,
    )
    return namespace


def _translator(locale):
    tree = ast.parse(
        (ROOT / "videotrans/configure/_i18n.py").read_text(encoding="utf-8")
    )
    nodes = [
        node
        for node in tree.body
        if not (
            isinstance(node, ast.ImportFrom)
            and node.module in ("PySide6.QtCore", "videotrans.configure._paths")
        )
    ]
    namespace = _exec(
        nodes, {"ROOT_DIR": str(ROOT)}, ROOT / "videotrans/configure/_i18n.py"
    )
    settings = SimpleNamespace(lang=locale)
    # Exercise the real lookup and formatting implementation with isolated state.
    namespace["defaulelang"] = settings.lang
    namespace["_transobj"] = namespace["_get_transobj"](settings.lang)
    wrapper = next(
        node
        for node in WEBUI.body
        if isinstance(node, ast.FunctionDef) and node.name == "tr"
    )
    return _exec([wrapper], {"_core_tr": namespace["tr"]})["tr"]


def _web_namespace(locale):
    wanted = {
        "_webui_locale",
        "_parse_ass_color",
        "_to_ass_color",
        "_lang_code_from_display",
    }
    constants = {
        "DEFAULT_ASS_STYLE",
        "SUBTITLE_TYPES",
        "DEFAULT_SUBTITLE_TYPE",
        "PUNC_OPTIONS",
        "LOOP_BGM_OPTIONS",
        "LANG_CHOICES",
        "DEFAULT_SOURCE_LANG",
    }
    tr = _translator(locale)
    namespace = {"tr": tr, "LANGNAME_DICT": {"en": tr("en"), "fr": tr("fr")}}
    nodes = []
    for node in WEBUI.body:
        if (
            isinstance(node, ast.FunctionDef)
            and node.name in wanted
            or isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id in constants
                for target in node.targets
            )
        ):
            nodes.append(node)
    editor = next(
        node
        for node in WEBUI.body
        if isinstance(node, ast.FunctionDef) and node.name == "build_ass_editor"
    )
    nodes.extend(
        node
        for node in ast.walk(editor)
        if isinstance(node, ast.FunctionDef)
        and node.name in ("save_ass_style", "reset_ass_style")
    )
    captured = []
    namespace["_save_ass_style"] = captured.append
    _exec(nodes, namespace)
    return namespace, captured


def test_catalog_covers_all_literal_webui_messages_and_format_fields():
    catalog = _catalog()
    keys = {
        node.args[0].value
        for node in ast.walk(WEBUI)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "tr"
        and node.args
        and isinstance(node.args[0], ast.Constant)
    }
    assert len(keys) > 200
    assert keys <= catalog.keys()
    for key in keys:
        assert isinstance(catalog[key], str) and catalog[key].strip()
        source_fields = [
            (field, spec, conversion)
            for _, field, spec, conversion in Formatter().parse(key)
            if field is not None
        ]
        translated_fields = [
            (field, spec, conversion)
            for _, field, spec, conversion in Formatter().parse(catalog[key])
            if field is not None
        ]
        assert source_fields == translated_fields, key


@pytest.mark.parametrize(
    "requested,expected",
    [
        ("fr", "fr_FR"),
        ("fr-FR", "fr_FR"),
        ("fr_FR", "fr_FR"),
        ("zh", "zh_CN"),
        ("zh_CN", "zh_CN"),
        ("en", "en_US"),
        ("en_US", "en_US"),
        ("unknown", "unknown"),
    ],
)
def test_language_aliases_preserve_explicit_settings(requested, expected):
    namespace, _ = _web_namespace("fr_FR")
    assert namespace["_webui_locale"](requested) == expected


def test_chinese_fallback_and_french_formatting():
    key = "渠道「{}」暂不可用，已自动回退"
    assert _translator("zh_CN")(key, "Whisper") == key.format("Whisper")
    french = _translator("fr_FR")(key, "Whisper")
    assert "Whisper" in french and "{}" not in french and "渠道" not in french
    assert _translator("fr_FR")("unknown.key") == "unknown.key"


@pytest.mark.parametrize("locale", ["fr_FR", "zh_CN"])
def test_display_language_choices_keep_stable_codes(locale):
    namespace, _ = _web_namespace(locale)
    assert [value for _, value in namespace["LANG_CHOICES"]] == ["en", "fr"]
    assert namespace["DEFAULT_SOURCE_LANG"] == "en"
    for label, code in namespace["LANG_CHOICES"]:
        assert namespace["_lang_code_from_display"](label) == code
        assert namespace["_lang_code_from_display"](code) == code
    assert namespace["_lang_code_from_display"]("-") == "-"


@pytest.mark.parametrize("locale", ["fr_FR", "zh_CN"])
def test_translated_option_maps_keep_processing_values(locale):
    namespace, _ = _web_namespace(locale)
    tr = namespace["tr"]
    expected = {
        "SUBTITLE_TYPES": {
            "不嵌入字幕": 0,
            "嵌入硬字幕": 1,
            "嵌入软字幕": 2,
            "嵌入硬字幕(双语)": 3,
            "嵌入软字幕(双语)": 4,
        },
        "PUNC_OPTIONS": {"默认标点": 0, "恢复标点": 1, "删除标点": 2},
        "LOOP_BGM_OPTIONS": {"背景音截断": 0, "背景音循环": 1},
    }
    for name, mapping in expected.items():
        assert namespace[name] == {tr(label): value for label, value in mapping.items()}
    assert namespace["SUBTITLE_TYPES"][namespace["DEFAULT_SUBTITLE_TYPE"]] == 1


@pytest.mark.parametrize("locale", ["fr_FR", "zh_CN"])
@pytest.mark.parametrize("border,expected_border", [("描边", 1), ("不透明背景", 3)])
@pytest.mark.parametrize(
    "alignment,expected_alignment",
    [
        ("左下", 1),
        ("中下", 2),
        ("右下", 3),
        ("左中", 4),
        ("正中", 5),
        ("右中", 6),
        ("左上", 7),
        ("中上", 8),
        ("右上", 9),
    ],
)
def test_ass_save_and_reset_preserve_numeric_style(
    locale, border, expected_border, alignment, expected_alignment
):
    namespace, captured = _web_namespace(locale)
    tr = namespace["tr"]
    reset = namespace["reset_ass_style"]()
    save = namespace["save_ass_style"]
    names = list(inspect.signature(save).parameters)
    arguments = dict(zip(names, reset))
    arguments.update(border_style=tr(border), alignment=tr(alignment))
    save(**arguments)
    assert captured[-1]["BorderStyle"] == expected_border
    assert captured[-1]["Alignment"] == expected_alignment
    namespace["reset_ass_style"]()
    assert captured[-1] == namespace["DEFAULT_ASS_STYLE"]

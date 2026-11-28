import re


def version_cache_suffix(params_like) -> str:
    """Return the cache-key suffix for the selected Index-TTS webui version."""
    version = int(params_like.get("index_version", 1))
    return "" if version == 1 else f"-v{version}"


def parse_emo_vector(value) -> list[float] | None:
    """Parse the eight Index-TTS emotion sliders saved by the settings window."""
    text = "" if value is None else str(value).strip()
    if not text:
        return None
    parts = [
        part.strip() for part in text.replace("，", ",").replace("、", ",").split(",")
    ]
    if parts[-1] == "":
        parts.pop()
    if len(parts) != 8:
        raise ValueError("Index-TTS emotion vector must contain exactly 8 numbers.")
    try:
        vector = [float(part) for part in parts]
    except ValueError as e:
        raise ValueError("Index-TTS emotion vector must contain only numbers.") from e
    if any(not 0 <= number <= 1 for number in vector):
        raise ValueError("Index-TTS emotion vector values must be between 0 and 1.")
    return None if all(number == 0 for number in vector) else vector


def parse_emo_weight(value) -> float:
    """Parse the weight Index-TTS applies to an emotion vector."""
    text = "" if value is None else str(value).strip()
    if not text:
        return 0.65
    try:
        weight = float(text)
    except ValueError as e:
        raise ValueError("Index-TTS emotion weight must be a number.") from e
    if not 0 <= weight <= 1:
        raise ValueError("Index-TTS emotion weight must be between 0 and 1.")
    return weight


def _role_emotion_lines(text, default_weight=0.65):
    parsed = []
    value = "" if text is None else str(text)
    for line_number, raw_line in enumerate(value.splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        # 角色名是参考音频文件名，只按第一个等号拆分，全角符号只在值中替换
        match = re.search("[=＝]", line)
        if not match:
            raise ValueError(
                f"Index-TTS role emotion line {line_number} must contain '='."
            )
        role = line[:match.start()].strip()
        value_text = line[match.end():].strip().replace("＝", "=").replace("；", ";")
        if not role:
            raise ValueError(
                f"Index-TTS role emotion line {line_number} must have a role name."
            )
        if value_text.count(";") > 1:
            raise ValueError(
                f"Index-TTS role emotion line {line_number} has too many weights."
            )
        vector_text, separator, weight_text = value_text.partition(";")
        try:
            vector = parse_emo_vector(vector_text)
            if vector_text.strip() == "":
                raise ValueError(
                    "Index-TTS emotion vector must contain exactly 8 numbers."
                )
            if separator and not weight_text.strip():
                raise ValueError("Index-TTS emotion weight must be a number.")
            weight = parse_emo_weight(weight_text if separator else default_weight)
        except ValueError as e:
            raise ValueError(
                f"Index-TTS role emotion line {line_number}: {e}"
            ) from e
        parsed.append((line_number, role, vector, weight))
    return parsed


def parse_role_emotions(
    text, default_weight=0.65,
) -> dict[str, tuple[list[float], float] | None]:
    """Parse per-role Index-TTS emotion vectors and optional weights."""
    emotions = {}
    for line_number, role, vector, weight in _role_emotion_lines(
        text, default_weight
    ):
        if role in emotions:
            raise ValueError(
                f"Index-TTS role emotion line {line_number} duplicates role '{role}'."
            )
        emotions[role] = None if vector is None else (vector, weight)
    return emotions


def index_emotion(params_like) -> tuple[list[float], float] | None:
    """Return the emotion request used by Index-TTS V2 and V2.5."""
    if int(params_like.get("index_version", 1)) <= 0:
        return None
    vector = parse_emo_vector(params_like.get("index_emo_vector", ""))
    if vector is None:
        return None
    return vector, parse_emo_weight(params_like.get("index_emo_weight", 0.65))


def index_emotion_for_role(
    params_like, role
) -> tuple[list[float], float] | None:
    """Return a role override or the global Index-TTS emotion request."""
    if int(params_like.get("index_version", 1)) <= 0:
        return None
    role_emotions = parse_role_emotions(
        params_like.get("index_role_emotions", ""),
        params_like.get("index_emo_weight", 0.65),
    )
    role_name = "" if role is None else str(role).strip()
    if role_name in role_emotions:
        return role_emotions[role_name]
    return index_emotion(params_like)


def emotion_cache_suffix(params_like, role=None) -> str:
    """Return the cache-key suffix for the emotion effective for a role."""
    emotion = (
        index_emotion(params_like)
        if role is None
        else index_emotion_for_role(params_like, role)
    )
    if emotion is None:
        return ""
    vector, weight = emotion
    return f"-{','.join(str(value) for value in vector)}-{weight}"

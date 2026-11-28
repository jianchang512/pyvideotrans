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


def index_emotion(params_like) -> tuple[list[float], float] | None:
    """Return the emotion request used by Index-TTS V2 and V2.5."""
    if int(params_like.get("index_version", 1)) <= 0:
        return None
    vector = parse_emo_vector(params_like.get("index_emo_vector", ""))
    if vector is None:
        return None
    return vector, parse_emo_weight(params_like.get("index_emo_weight", 0.65))


def emotion_cache_suffix(params_like) -> str:
    """Return the cache-key suffix for an emotion request, if one is sent."""
    emotion = index_emotion(params_like)
    if emotion is None:
        return ""
    vector, weight = emotion
    return f"-{','.join(str(value) for value in vector)}-{weight}"

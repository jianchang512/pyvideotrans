# _MODELS 是从 faster-whisper.utils.py 中复制的
_MODELS = {
    "tiny.en": "Systran/faster-whisper-tiny.en",
    "tiny": "Systran/faster-whisper-tiny",
    "base.en": "Systran/faster-whisper-base.en",
    "base": "Systran/faster-whisper-base",
    "small.en": "Systran/faster-whisper-small.en",
    "small": "Systran/faster-whisper-small",
    "medium.en": "Systran/faster-whisper-medium.en",
    "medium": "Systran/faster-whisper-medium",
    "large-v1": "Systran/faster-whisper-large-v1",
    "large-v2": "Systran/faster-whisper-large-v2",
    "large-v3": "Systran/faster-whisper-large-v3",
    "large": "Systran/faster-whisper-large-v3",
    "distil-large-v2": "Systran/faster-distil-whisper-large-v2",
    "distil-medium.en": "Systran/faster-distil-whisper-medium.en",
    "distil-small.en": "Systran/faster-distil-whisper-small.en",
    "distil-large-v3": "Systran/faster-distil-whisper-large-v3",
    "distil-large-v3.5": "distil-whisper/distil-large-v3.5-ct2",
    "large-v3-turbo": "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
    "turbo": "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
}

def is_model_cached(repo_id: str, cache_dir: str = ''):
    from pathlib import Path
    try:
        # 将 repo_id 转换为缓存目录的命名格式
        if repo_id in _MODELS:
            org_name, model_name = _MODELS[repo_id].split('/')
            repo_cache_dir = Path(cache_dir) / f"models--{org_name}--{model_name}"
        else:
            repo_cache_dir = Path(cache_dir) / f"models--"/ repo_id.replace('/','--')
        
        # 检查是否存在 refs/main 文件以获取当前版本的哈希值
        refs_main_file = repo_cache_dir / "refs" / "main"
        if not refs_main_file.exists():
            return False

        with open(refs_main_file, 'r') as f:
            target_hash = f.read().strip()

        # 检查对应的 snapshots 目录
        snapshot_dir = repo_cache_dir / "snapshots" / target_hash
        if not snapshot_dir.exists():
            return False

        # 检查关键文件：config.json 和 model.bin
        for it in ["config.json", "model.bin", "tokenizer.json","vocabulary"]:
            if it =='vocabulary':
                if not _is_file_valid(snapshot_dir / 'vocabulary.txt') and not _is_file_valid(snapshot_dir / 'vocabulary.json'):
                    return False
                continue
            if not _is_file_valid(snapshot_dir / it):
                return False
        return str(snapshot_dir)
    except Exception:
        return False

def _is_file_valid(file_path) -> bool:
    try:
        if not file_path.exists():
            return False

        # 如果是符号链接，获取真实路径
        if file_path.is_symlink():
            real_path = file_path.resolve()
            # 确保解析后的路径仍然存在
            if not real_path.exists():
                return False
            file_path = real_path

        # 检查文件大小
        return file_path.stat().st_size > 0

    except (OSError, ValueError):
        return False


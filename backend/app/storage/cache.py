import json
from pathlib import Path

CACHE_DIR = Path(__file__).resolve().parent.parent.parent / ".cache"


def _path_for_key(key: str) -> Path:
    safe_key = key.replace("/", "__")
    return CACHE_DIR / f"{safe_key}.json"


def get(key: str):
    path = _path_for_key(key)
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def set(key: str, value) -> None:
    path = _path_for_key(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(value, f, indent=2, ensure_ascii=False)

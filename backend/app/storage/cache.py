import hashlib
import json
import os
import re
import time
from pathlib import Path

# Defaults to backend/.cache (gitignored); in deploy, CACHE_DIR points at a
# mounted disk (e.g. /data/.cache) so mined stories survive redeploys and the
# first user after a redeploy doesn't wait on a full re-mine.
CACHE_DIR = Path(os.environ.get("CACHE_DIR", Path(__file__).resolve().parent.parent.parent / ".cache"))

# Keys embed user-supplied text (search keywords, custom domains, student
# names). Only characters that could escape CACHE_DIR or upset the filesystem
# are neutralised — "#" and "_" are deliberately left alone because existing
# story keys ("owner__repo#1397:pass2") depend on them resolving unchanged.
_UNSAFE_KEY_CHARS = re.compile(r"[\\\x00-\x1f\x7f]")

# ext4/APFS cap a single filename at 255 bytes; long custom domains plus a
# keyword can approach that, and an over-long name raises instead of missing.
_MAX_BASENAME = 200


def _path_for_key(key: str) -> Path:
    safe_key = _UNSAFE_KEY_CHARS.sub("_", key.replace("/", "__"))
    if len(safe_key.encode("utf-8")) > _MAX_BASENAME:
        digest = hashlib.sha256(safe_key.encode("utf-8")).hexdigest()[:16]
        safe_key = f"{safe_key[:120]}~{digest}"
    return CACHE_DIR / f"{safe_key}.json"


def get(key: str, ttl_seconds: int | None = None):
    """Cached value, or None if absent.

    `ttl_seconds` is opt-in per call site: mined stories and the committed seed
    library are expensive and stay valid indefinitely, so they pass nothing and
    keep the permanent behaviour. Discovery passes a TTL because its results
    would otherwise stay frozen for the lifetime of the deploy.
    """
    path = _path_for_key(key)
    if not path.exists():
        return None
    if ttl_seconds is not None and (time.time() - path.stat().st_mtime) > ttl_seconds:
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def set(key: str, value) -> None:
    path = _path_for_key(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(value, f, indent=2, ensure_ascii=False)

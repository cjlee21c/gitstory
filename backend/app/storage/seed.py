import shutil
from pathlib import Path

from app.storage.cache import CACHE_DIR

# Curated cache shipped in the repo (backend/seed_cache): the pass2 story
# bundles + pre-generated workspaces that make up the initial student-facing
# library. On a fresh deploy the mounted CACHE_DIR disk starts empty, so we copy
# these in once at startup.
SEED_DIR = Path(__file__).resolve().parent.parent.parent / "seed_cache"


def seed_cache_if_needed() -> int:
    """Copy any seed file that isn't already in CACHE_DIR. Copy-if-missing makes
    this idempotent and additive: it fills a fresh disk on first boot, skips
    everything on later boots, and never clobbers repos students mined
    themselves. Returns the number of files copied."""
    if not SEED_DIR.exists():
        return 0

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    copied = 0
    for src in SEED_DIR.glob("*.json"):
        dst = CACHE_DIR / src.name
        if not dst.exists():
            shutil.copy2(src, dst)
            copied += 1
    if copied:
        print(f"[seed] copied {copied} cache file(s) into {CACHE_DIR}")
    return copied

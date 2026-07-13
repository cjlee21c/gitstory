from pathlib import Path

from fastapi import APIRouter

from app.api.routes_repos import STORY_CAP
from app.models.schemas import StorySummary
from app.storage.cache import CACHE_DIR

router = APIRouter(tags=["library"])


def _to_summary(bundle: dict) -> StorySummary:
    return StorySummary(
        story_id=bundle["story_id"],
        title=bundle["metadata"]["title"],
        labels=bundle["metadata"]["labels"],
        qualities=bundle["metadata"].get("qualities", []),
    )


def _repo_from_cache_key(filename: str) -> str:
    # filename looks like "PaperMC__Paper:pass2.json" → "PaperMC/Paper"
    key = filename.replace(":pass2.json", "")
    return key.replace("__", "/")


@router.get("/library")
def get_library():
    results = []
    if not CACHE_DIR.exists():
        return results

    for path in sorted(CACHE_DIR.glob("*:pass2.json")):
        import json
        try:
            bundles = json.loads(path.read_text(encoding="utf-8"))
            repo = _repo_from_cache_key(path.name)
            # Same read-time cap as the stories API — pass2 caches now hold
            # every enriched elite, not just the top few.
            stories = [_to_summary(b) for b in bundles[:STORY_CAP]]
            results.append({"repo": repo, "stories": stories})
        except Exception:
            continue

    return results

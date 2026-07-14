import threading

from fastapi import APIRouter, HTTPException

from app.llm.workspace_generator import generate_workspace
from app.models.schemas import StoryBundle, WorkspaceContent
from app.storage import cache

router = APIRouter(prefix="/stories", tags=["stories"])

# Per-story locks so concurrent requests for the same uncached workspace don't
# each pay for a full Sonnet generation. FastAPI runs sync endpoints in a thread
# pool, so two simultaneous GETs (StrictMode double-fetch, double-click, retries,
# multiple tabs) would otherwise both miss the cache and generate independently.
_workspace_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _lock_for(key: str) -> threading.Lock:
    with _locks_guard:
        lock = _workspace_locks.get(key)
        if lock is None:
            lock = threading.Lock()
            _workspace_locks[key] = lock
        return lock


def _get_bundle_or_404(story_id: str) -> dict:
    if "#" not in story_id:
        raise HTTPException(
            status_code=400,
            detail="story_id must be in '<owner>/<repo>#<issue_number>' format",
        )
    repo, _, _ = story_id.rpartition("#")
    bundles = cache.get(f"{repo}:pass2")
    if bundles is None:
        raise HTTPException(status_code=404, detail=f"No pipeline results for {repo}")
    for bundle in bundles:
        if bundle["story_id"] == story_id:
            return bundle
    raise HTTPException(status_code=404, detail=f"Story {story_id} not found")


@router.get("/{story_id:path}/workspace", response_model=WorkspaceContent)
def get_workspace(story_id: str, force: bool = False):
    workspace_key = f"{story_id}:workspace"
    if not force:
        cached = cache.get(workspace_key)
        if cached is not None:
            return cached

    with _lock_for(workspace_key):
        # Double-checked: while we waited for the lock, a concurrent request may
        # have already generated and cached this workspace. Return that instead
        # of paying Sonnet a second time for the same story.
        if not force:
            cached = cache.get(workspace_key)
            if cached is not None:
                return cached

        bundle = _get_bundle_or_404(story_id)
        workspace = generate_workspace(bundle)
        cache.set(workspace_key, workspace.model_dump())
        return workspace


@router.get("/{story_id:path}", response_model=StoryBundle)
def get_story(story_id: str):
    return _get_bundle_or_404(story_id)

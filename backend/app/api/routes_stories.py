import threading

from fastapi import APIRouter, HTTPException

from typing import Callable

from app.llm.workspace_generator import (
    generate_workspace_part1,
    generate_workspace_part2,
)
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


def _get_or_generate(story_id: str, suffix: str, gen_fn: Callable[[dict], WorkspaceContent], force: bool) -> dict:
    """Cached, lock-guarded generation for one workspace phase. Each phase caches
    under its own key so Part 1 and Part 2 are stored (and paid for) independently."""
    workspace_key = f"{story_id}:workspace{suffix}"
    if not force:
        cached = cache.get(workspace_key)
        if cached is not None:
            return cached

    with _lock_for(workspace_key):
        # Double-checked: while we waited for the lock, a concurrent request may
        # have already generated and cached this phase. Return that instead of
        # paying Sonnet a second time for the same story.
        if not force:
            cached = cache.get(workspace_key)
            if cached is not None:
                return cached

        bundle = _get_bundle_or_404(story_id)
        workspace = gen_fn(bundle)
        payload = workspace.model_dump()
        cache.set(workspace_key, payload)
        return payload


@router.get("/{story_id:path}/workspace", response_model=WorkspaceContent)
def get_workspace(story_id: str, force: bool = False, part: int | None = None):
    # part=1 -> opening beats (context/dilemma/viewpoints/checkpoint), returned
    # first; part=2 -> closing beats (decision/lessons), fetched in parallel but
    # only needed after the checkpoint. No part -> full workspace (both merged).
    if part == 1:
        return _get_or_generate(story_id, ":p1", generate_workspace_part1, force)
    if part == 2:
        return _get_or_generate(story_id, ":p2", generate_workspace_part2, force)
    if part is not None:
        raise HTTPException(status_code=400, detail="part must be 1 or 2")

    p1 = _get_or_generate(story_id, ":p1", generate_workspace_part1, force)
    p2 = _get_or_generate(story_id, ":p2", generate_workspace_part2, force)
    return {"story_id": story_id, "beats": [*p1["beats"], *p2["beats"]]}


@router.get("/{story_id:path}", response_model=StoryBundle)
def get_story(story_id: str):
    return _get_bundle_or_404(story_id)

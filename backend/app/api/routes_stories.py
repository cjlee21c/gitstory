from fastapi import APIRouter, HTTPException

from app.llm.workspace_generator import generate_workspace
from app.models.schemas import StoryBundle, WorkspaceContent
from app.storage import cache

router = APIRouter(prefix="/stories", tags=["stories"])


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

    bundle = _get_bundle_or_404(story_id)
    workspace = generate_workspace(bundle)
    cache.set(workspace_key, workspace.model_dump())
    return workspace


@router.get("/{story_id:path}", response_model=StoryBundle)
def get_story(story_id: str):
    return _get_bundle_or_404(story_id)

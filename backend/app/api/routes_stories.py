from fastapi import APIRouter, HTTPException

from app.models.schemas import StoryBundle
from app.storage import cache

router = APIRouter(prefix="/stories", tags=["stories"])


@router.get("/{story_id:path}", response_model=StoryBundle)
def get_story(story_id: str):
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

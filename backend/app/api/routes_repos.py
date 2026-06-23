from fastapi import APIRouter, HTTPException

from app.models.schemas import PipelineRunResponse, StorySummary
from app.pipeline.orchestrator import run_pipeline
from app.storage import cache

router = APIRouter(prefix="/repos", tags=["repos"])


def _to_summary(bundle: dict) -> StorySummary:
    return StorySummary(
        story_id=bundle["story_id"],
        title=bundle["metadata"]["title"],
        labels=bundle["metadata"]["labels"],
    )


@router.post("/{repo:path}/pipeline", response_model=PipelineRunResponse)
def trigger_pipeline(repo: str, force: bool = False):
    was_cached = not force and cache.get(f"{repo}:pass2") is not None
    bundles = run_pipeline(repo, force=force)
    return PipelineRunResponse(
        repo=repo,
        story_count=len(bundles),
        cached=was_cached,
        stories=[_to_summary(b) for b in bundles],
    )


@router.get("/{repo:path}/stories", response_model=list[StorySummary])
def list_stories(repo: str):
    bundles = cache.get(f"{repo}:pass2")
    if bundles is None:
        raise HTTPException(
            status_code=404,
            detail=f"No pipeline results for {repo}. POST /repos/{repo}/pipeline first.",
        )
    return [_to_summary(b) for b in bundles]

from fastapi import APIRouter, HTTPException

from app.filters import QUALITY_ATTRIBUTES
from app.models.schemas import PipelineRunResponse, StorySummary
from app.pipeline.orchestrator import run_pipeline
from app.storage import cache

router = APIRouter(prefix="/repos", tags=["repos"])

STORY_CAP = 4


def _to_summary(bundle: dict) -> StorySummary:
    return StorySummary(
        story_id=bundle["story_id"],
        title=bundle["metadata"]["title"],
        labels=bundle["metadata"]["labels"],
        qualities=bundle["metadata"].get("qualities", []),
    )


def filter_bundles(bundles: list[dict], qualities: str | None) -> list[dict]:
    """Quality filter (OR semantics) + story cap, applied at read time so the
    repo-keyed pipeline cache serves any quality selection without a re-run.
    Bundles from pre-labeling caches have no qualities key — those pass the
    filter (fail open) until the pipeline is re-run with force=true."""
    if qualities:
        wanted = {q.strip() for q in qualities.split(",")} & set(QUALITY_ATTRIBUTES)
        if wanted:
            bundles = [
                b
                for b in bundles
                if not b["metadata"].get("qualities")
                or wanted & set(b["metadata"]["qualities"])
            ]
    return bundles[:STORY_CAP]


@router.post("/{repo:path}/pipeline", response_model=PipelineRunResponse)
def trigger_pipeline(repo: str, force: bool = False):
    was_cached = not force and cache.get(f"{repo}:pass2") is not None
    bundles = run_pipeline(repo, force=force)
    return PipelineRunResponse(
        repo=repo,
        story_count=len(bundles),
        cached=was_cached,
        stories=[_to_summary(b) for b in bundles[:STORY_CAP]],
    )


@router.get("/{repo:path}/stories", response_model=list[StorySummary])
def list_stories(repo: str, qualities: str | None = None):
    bundles = cache.get(f"{repo}:pass2")
    if bundles is None:
        raise HTTPException(
            status_code=404,
            detail=f"No pipeline results for {repo}. POST /repos/{repo}/pipeline first.",
        )
    return [_to_summary(b) for b in filter_bundles(bundles, qualities)]

from fastapi import APIRouter, HTTPException

from app.filters import QUALITY_ATTRIBUTES
from app.models.schemas import PipelineRunResponse, StoryListResponse, StorySummary
from app.pipeline.orchestrator import pass2_cache_key, run_pipeline
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


def _quality_counts(bundles: list[dict]) -> dict[str, int]:
    """Counts, per quality attribute, how many stories in the full (unfiltered,
    uncapped) set carry that label. Pure tally over already-cached labels — no
    LLM or GitHub calls."""
    counts = {q: 0 for q in QUALITY_ATTRIBUTES}
    for b in bundles:
        for q in b["metadata"].get("qualities", []):
            if q in counts:
                counts[q] += 1
    return counts


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
    was_cached = not force and cache.get(pass2_cache_key(repo)) is not None
    bundles = run_pipeline(repo, force=force)
    return PipelineRunResponse(
        repo=repo,
        story_count=len(bundles),
        cached=was_cached,
        stories=[_to_summary(b) for b in bundles[:STORY_CAP]],
    )


@router.get("/{repo:path}/stories", response_model=StoryListResponse)
def list_stories(repo: str, qualities: str | None = None):
    bundles = cache.get(pass2_cache_key(repo))
    if bundles is None:
        raise HTTPException(
            status_code=404,
            detail=f"No pipeline results for {repo}. POST /repos/{repo}/pipeline first.",
        )
    # Counts come from the full set so they stay stable as the user toggles the
    # quality filter; stories are the filtered + capped subset.
    return StoryListResponse(
        stories=[_to_summary(b) for b in filter_bundles(bundles, qualities)],
        quality_counts=_quality_counts(bundles),
    )

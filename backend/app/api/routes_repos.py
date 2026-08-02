from fastapi import APIRouter, HTTPException

from app.filters import QUALITY_ATTRIBUTES
from app.models.schemas import PipelineRunResponse, StoryListResponse, StorySummary
from app.pipeline.orchestrator import pass2_cache_key, run_pipeline
from app.storage import cache

router = APIRouter(prefix="/repos", tags=["repos"])

# Preview size for surfaces that show a fixed taste of a repo: the pipeline-run
# response here and the seed library. The story catalog no longer uses it —
# list_stories returns every match and the frontend decides how many to render,
# so the "show more" affordance can reach the rest.
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


def _requested(qualities: str | None) -> list[str]:
    """The selected qualities that are real attribute ids, in canonical order.
    Unknown ids are dropped rather than rejected — an old bookmark carrying a
    retired label should degrade to "no filter", not a 422."""
    if not qualities:
        return []
    picked = {q.strip() for q in qualities.split(",")}
    return [q for q in QUALITY_ATTRIBUTES if q in picked]


def filter_bundles(bundles: list[dict], qualities: str | None) -> list[dict]:
    """Quality filter (OR semantics), applied at read time so the repo-keyed
    pipeline cache serves any quality selection without a re-run. Bundles from
    pre-labeling caches have no qualities key — those pass the filter (fail
    open) until the pipeline is re-run with force=true.

    Returns every match, uncapped: the catalog shows the first few and offers a
    "show more", so a story that matches must never be unreachable. Matches are
    ordered by how much they overlap the selection, because the incoming order
    is the pipeline's stage2_score ranking, which knows nothing about what the
    user picked — under the old filter-then-cut-to-4 the sole `performance`
    story could sit at rank 6 and vanish behind four `usability` ones. Sorting
    is stable, so equal-overlap stories keep that ranking, and fail-open
    bundles (no labels, zero overlap) sink to the bottom instead of taking top
    slots.
    """
    wanted = set(_requested(qualities))
    if wanted:
        bundles = [
            b
            for b in bundles
            if not b["metadata"].get("qualities")
            or wanted & set(b["metadata"]["qualities"])
        ]
        bundles = sorted(
            bundles,
            key=lambda b: -len(wanted & set(b["metadata"].get("qualities", []))),
        )
    return bundles


def _label(quality: str) -> str:
    """Chip label for prose: energy_efficiency -> "energy efficiency"."""
    return quality.replace("_", " ")


def _join(items: list[str]) -> str:
    if len(items) > 1:
        return ", ".join(items[:-1]) + " and " + items[-1]
    return items[0]


def _fallback_notice(repo: str, unmatched: list[str], counts: dict[str, int]) -> str:
    """Plain-language explanation for a focus that matched nothing.

    Selecting a quality no story carries used to land on an empty page, which
    reads as a broken filter rather than a fact about the repo — the same
    problem discovery solves with its widened-search notice, so this keeps that
    voice (see discovery/orchestrator._build_notice)."""
    present = [q for q in QUALITY_ATTRIBUTES if counts.get(q)]
    asked = _join([_label(q) for q in unmatched])
    if not present:
        return f"No stories in {repo} carry {asked}, so we're showing all of them instead."
    return (
        f"No {asked} stories were found in {repo}, so we're showing its most "
        f"substantial discussions instead — these cover {_join([_label(q) for q in present])}."
    )


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
    # quality filter; stories are the filtered set, uncapped, so the catalog's
    # "showing 4 of N" can quote an N the user can actually reach.
    counts = _quality_counts(bundles)

    # A focus that matches nothing falls back to the unfiltered set rather than
    # an empty page — but only when *every* selected quality is empty. A partial
    # selection still filters normally, so asking for two qualities and getting
    # one of them doesn't silently widen the results.
    wanted = _requested(qualities)
    notice = None
    if wanted and all(not counts.get(q) for q in wanted):
        selected = [_to_summary(b) for b in bundles]
        notice = _fallback_notice(repo, wanted, counts)
    else:
        selected = [_to_summary(b) for b in filter_bundles(bundles, qualities)]

    return StoryListResponse(stories=selected, quality_counts=counts, notice=notice)

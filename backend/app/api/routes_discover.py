from fastapi import APIRouter, BackgroundTasks

from app.discovery.orchestrator import discover_repos, fill_pool_summaries, paginate_pool
from app.models.schemas import DiscoverRequest, DiscoverResponse

router = APIRouter(tags=["discover"])


@router.post("/discover", response_model=DiscoverResponse)
def discover(request: DiscoverRequest, background_tasks: BackgroundTasks):
    payload, candidates = discover_repos(request)
    # Only the first page is summarized on the response path; the rest of the
    # pool is filled in afterwards so it's ready by the time the student comes
    # back to these filters, without adding to the wait now.
    if candidates:
        background_tasks.add_task(fill_pool_summaries, request, candidates)
    return DiscoverResponse(
        repos=paginate_pool(payload, request),
        notice=payload.get("notice"),
        relaxed=payload.get("relaxations", []),
    )

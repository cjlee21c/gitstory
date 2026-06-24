from fastapi import APIRouter

from app.discovery.orchestrator import discover_repos
from app.models.schemas import DiscoverRequest, RepoRecommendation

router = APIRouter(tags=["discover"])


@router.post("/discover", response_model=list[RepoRecommendation])
def discover(request: DiscoverRequest):
    return discover_repos(request.interest)

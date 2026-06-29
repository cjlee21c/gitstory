from concurrent.futures import ThreadPoolExecutor

from app.config import GITHUB_TOKEN
from app.github_client import GitHubClient
from app.llm.interest_parser import extract_search_keywords
from app.llm.repo_summarizer import summarize_candidates
from app.storage import cache

MAX_RESULTS = 5
SEARCH_PER_PAGE = 10
MAX_WORKERS = 4


def _normalize(interest: str) -> str:
    return interest.strip().lower()


def discover_repos(interest: str, force: bool = False) -> list[dict]:
    cache_key = f"discover:{_normalize(interest)}"
    if not force:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

    keywords = extract_search_keywords(interest)

    github = GitHubClient(GITHUB_TOKEN)
    seen = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for items in executor.map(
            lambda kw: github.search_repositories(kw, per_page=SEARCH_PER_PAGE), keywords
        ):
            for item in items:
                seen.setdefault(item["full_name"], item)

    results = summarize_candidates(interest, list(seen.values()), max_results=MAX_RESULTS)
    cache.set(cache_key, results)
    return results

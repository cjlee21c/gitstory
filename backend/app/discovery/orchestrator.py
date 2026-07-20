from concurrent.futures import ThreadPoolExecutor

from app.config import GITHUB_TOKEN
from app.filters import DOMAINS, in_contributor_bucket, in_size_buckets, size_qualifier, star_qualifier
from app.github_client import GitHubClient
from app.llm.interest_parser import expand_keyword
from app.llm.repo_summarizer import summarize_candidates
from app.models.schemas import DiscoverRequest
from app.storage import cache

MAX_RESULTS = 5
SEARCH_PER_PAGE = 10
MAX_WORKERS = 4
CONTRIBUTOR_CHECK_LIMIT = 30
CONTRIBUTOR_CHECK_WORKERS = 8


def _filters_cache_key(filters: DiscoverRequest) -> str:
    sizes = ",".join(sorted(filters.sizes)) if filters.sizes else "any"
    stars = filters.stars or "any"
    contributors = filters.contributors or "any"
    keyword = filters.keyword.strip().lower() if filters.keyword and filters.keyword.strip() else "none"
    return f"discover:v3:{filters.domain}:s={sizes}:st={stars}:c={contributors}:kw={keyword}"


def _domain_label(domain: str) -> str:
    """Curated label for a known id, else the free-text custom domain as typed."""
    known = DOMAINS.get(domain)
    return known["label"] if known else domain


def _search_queries(filters: DiscoverRequest) -> list[str]:
    keyword = (filters.keyword or "").strip()
    if keyword:
        try:
            expanded = expand_keyword(keyword, _domain_label(filters.domain))
            if expanded:
                return expanded
        except Exception as e:
            print(f"  [Keyword expansion failed] {e} — using raw keyword")
        return [keyword]
    known = DOMAINS.get(filters.domain)
    if known:
        return known["keywords"]
    # Custom domain: no curated seed keywords, so expand the typed text itself
    # into GitHub search queries (falling back to the raw text).
    try:
        expanded = expand_keyword(filters.domain, filters.domain)
        if expanded:
            return expanded
    except Exception as e:
        print(f"  [Custom domain expansion failed] {e} — using raw domain")
    return [filters.domain]


def _contributor_filter(github: GitHubClient, candidates: list[dict], bucket: str) -> list[dict]:
    """Drops candidates outside the contributor bucket. GitHub search has no
    contributors qualifier, so this costs one cheap API call per candidate,
    run concurrently. A failed count keeps the repo (fail open)."""
    with ThreadPoolExecutor(max_workers=CONTRIBUTOR_CHECK_WORKERS) as executor:
        counts = list(
            executor.map(lambda c: github.get_contributor_count(c["full_name"]), candidates)
        )

    kept = []
    for candidate, count in zip(candidates, counts):
        if count is None or in_contributor_bucket(count, bucket):
            kept.append(candidate)
        else:
            print(f"  [Skip {candidate['full_name']}] {count} contributors outside bucket")
    return kept


def discover_repos(filters: DiscoverRequest, force: bool = False) -> list[dict]:
    cache_key = _filters_cache_key(filters)
    if not force:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

    queries = _search_queries(filters)
    qualifiers = [q for q in (size_qualifier(filters.sizes), star_qualifier(filters.stars)) if q]

    github = GitHubClient(GITHUB_TOKEN)
    seen = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for items in executor.map(
            lambda kw: github.search_repositories(
                kw, per_page=SEARCH_PER_PAGE, extra_qualifiers=qualifiers
            ),
            queries,
        ):
            for item in items:
                seen.setdefault(item["full_name"], item)

    # Exact bucket check: the merged size qualifier can admit repos between
    # non-contiguous selections (e.g. mediums when small+large was picked).
    candidates = [c for c in seen.values() if in_size_buckets(c.get("size", 0), filters.sizes)]

    candidates.sort(key=lambda c: c.get("stargazers_count", 0), reverse=True)
    candidates = candidates[:CONTRIBUTOR_CHECK_LIMIT]

    if filters.contributors:
        candidates = _contributor_filter(github, candidates, filters.contributors)

    domain_label = _domain_label(filters.domain)
    keyword = (filters.keyword or "").strip()
    interest_text = f"{domain_label}: {keyword}" if keyword else domain_label

    results = summarize_candidates(interest_text, candidates, max_results=MAX_RESULTS)
    cache.set(cache_key, results)
    return results

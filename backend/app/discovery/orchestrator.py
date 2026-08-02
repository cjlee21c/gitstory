from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from app.config import GITHUB_TOKEN
from app.filters import (
    DOMAINS,
    in_contributor_bucket,
    in_size_buckets,
    in_star_bucket,
    size_qualifier,
    star_qualifier,
    widen_star_qualifier,
    widened_star_bucket_label,
)
from app.github_client import GitHubClient
from app.llm.interest_parser import expand_keyword
from app.llm.repo_summarizer import fill_summaries, rank_and_summarize
from app.models.schemas import DiscoverRequest
from app.storage import cache

MAX_RESULTS = 5
POOL_SIZE = 15  # three rotations' worth, so a repeat visit never repeats a repo
SEARCH_PER_PAGE = 50
# Both pools are sized to clear their work in a single round — a domain expands
# to 6 queries, and every surviving candidate needs one contributor lookup.
# These are network waits, not CPU, and they share one pooled HTTPS connection
# set (see github_client), so the extra threads are close to free.
MAX_WORKERS = 8
# Checking 25-36 candidates costs the same ~0.7s since they go out together, so
# this is set by result quality rather than speed: too small a window and the
# contributor filter runs out of repos to keep and relaxes when it didn't need
# to. Occasional slow outliers past ~36 are what keep it from going higher.
CONTRIBUTOR_CHECK_LIMIT = 32
CONTRIBUTOR_CHECK_WORKERS = 32

# GitHub allows 30 searches/minute. Holding a domain to 6 keeps five concurrent
# uncached discoveries inside the budget; see _search_queries for the split.
MAX_TOPIC_QUERIES = 3
MAX_KEYWORD_QUERIES = 2
MIN_POOL = 8  # below this, relax one more filter
ACTIVE_DAYS = 180
DISCOVER_TTL_SECONDS = 7 * 24 * 3600


def _filters_cache_key(filters: DiscoverRequest) -> str:
    sizes = ",".join(sorted(filters.sizes)) if filters.sizes else "any"
    stars = filters.stars or "any"
    contributors = filters.contributors or "any"
    keyword = filters.keyword.strip().lower() if filters.keyword and filters.keyword.strip() else "none"
    return f"discover:v4:{filters.domain}:s={sizes}:st={stars}:c={contributors}:kw={keyword}"


def _cursor_cache_key(student_id: str | None, filters_key: str) -> str:
    return f"discover-cursor:{(student_id or 'anon').strip().lower()}:{filters_key}"


def _domain_label(domain: str) -> str:
    """Curated label for a known id, else the free-text custom domain as typed."""
    known = DOMAINS.get(domain)
    return known["label"] if known else domain


def _search_queries(filters: DiscoverRequest) -> list[str]:
    """Query strings to search GitHub with, one request each.

    A curated domain fans out across three surfaces (topics, an OR-ed term
    group, phrase keywords) because any single one is far too narrow once star
    and contributor filters stack on top — see the module docstring in
    app/filters.py.
    """
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
        # Budgeted against GitHub's 30 searches/minute: measured on healthcare,
        # each group contributes ~12 repos the others miss, but the OR-ed term
        # group gets there in one request where the phrase keywords need six.
        # So the broad query always runs, topics are capped, and only the two
        # most specific keywords survive — 6 requests instead of 11, for
        # ~85% of the candidates.
        queries = [" OR ".join(known["terms"])] if known.get("terms") else []
        queries += [f"topic:{t}" for t in known.get("topics", [])[:MAX_TOPIC_QUERIES]]
        queries += known["keywords"][:MAX_KEYWORD_QUERIES]
        return queries

    # Custom domain: no curated seed keywords, so expand the typed text itself
    # into GitHub search queries (falling back to the raw text).
    try:
        expanded = expand_keyword(filters.domain, filters.domain)
        if expanded:
            return expanded
    except Exception as e:
        print(f"  [Custom domain expansion failed] {e} — using raw domain")
    return [filters.domain]


def _contributor_counts(github: GitHubClient, repos: list[str]) -> dict[str, int | None]:
    """One cheap contributor-count call per repo, run concurrently. A None count
    means GitHub couldn't answer, and callers fail open on it."""
    with ThreadPoolExecutor(max_workers=CONTRIBUTOR_CHECK_WORKERS) as executor:
        counts = list(executor.map(github.get_contributor_count, repos))
    return dict(zip(repos, counts))


def _pushed_recently(candidate: dict, days: int) -> bool:
    pushed = candidate.get("pushed_at")
    if not pushed:
        return True  # missing timestamp shouldn't drop an otherwise good repo
    try:
        when = datetime.fromisoformat(pushed.replace("Z", "+00:00"))
    except ValueError:
        return True
    return when >= datetime.now(timezone.utc) - timedelta(days=days)


def _gather_candidates(github: GitHubClient, filters: DiscoverRequest) -> tuple[list[dict], list[str]]:
    """Ranked candidates plus the list of filters that had to be relaxed.

    Searches GitHub exactly once, at the widest setting the student's filters
    could relax to, then narrows in Python. Relaxing by re-searching would
    multiply requests against the 30/min search limit for no extra coverage —
    the widened result set already contains everything the strict one would.
    """
    queries = _search_queries(filters)
    qualifiers = [
        q
        for q in (
            size_qualifier(filters.sizes),
            # Widened up front so one search covers both the strict and relaxed
            # star range; the strict cut happens below, in Python.
            widen_star_qualifier(filters.stars) or star_qualifier(filters.stars),
        )
        if q
    ]

    seen: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for items in executor.map(
            lambda kw: github.search_repositories(
                kw,
                per_page=SEARCH_PER_PAGE,
                extra_qualifiers=qualifiers,
                active_days=None,  # re-applied in Python so it can be relaxed for free
            ),
            queries,
        ):
            for item in items:
                seen.setdefault(item["full_name"], item)

    # Exact bucket check: the merged size qualifier can admit repos between
    # non-contiguous selections (e.g. mediums when small+large was picked).
    pool = [c for c in seen.values() if in_size_buckets(c.get("size", 0), filters.sizes)]
    pool.sort(key=lambda c: c.get("stargazers_count", 0), reverse=True)

    # Contributor counts cost an API call each, so only the plausible head of
    # the list is checked, and each repo is looked up at most once across all
    # relaxation levels. The pool is truncated to that head so an unchecked repo
    # further down can't slip past the filter as an unknown count.
    counts: dict[str, int | None] = {}
    if filters.contributors:
        pool = pool[:CONTRIBUTOR_CHECK_LIMIT]
        counts = _contributor_counts(github, [c["full_name"] for c in pool])

    def passes(candidate: dict, relax_stars: bool, relax_activity: bool, relax_contributors: bool) -> bool:
        if not relax_stars and not in_star_bucket(candidate.get("stargazers_count", 0), filters.stars):
            return False
        if not relax_activity and not _pushed_recently(candidate, ACTIVE_DAYS):
            return False
        if not relax_contributors and filters.contributors:
            count = counts.get(candidate["full_name"])
            if count is not None and not in_contributor_bucket(count, filters.contributors):
                return False
        return True

    # Strictest first; take the first level that yields a usable pool. Ordered
    # so the filters the student never chose (the hidden activity window) give
    # way before the ones they did.
    can_widen_stars = widen_star_qualifier(filters.stars) is not None
    levels: list[tuple[list[str], dict]] = [
        ([], {"relax_stars": False, "relax_activity": False, "relax_contributors": False}),
        (["recent_activity"], {"relax_stars": False, "relax_activity": True, "relax_contributors": False}),
    ]
    if can_widen_stars:
        levels.append(
            (["recent_activity", "stars"], {"relax_stars": True, "relax_activity": True, "relax_contributors": False})
        )
    if filters.contributors:
        relaxed = ["recent_activity", "contributors"] + (["stars"] if can_widen_stars else [])
        levels.append(
            (relaxed, {"relax_stars": can_widen_stars, "relax_activity": True, "relax_contributors": True})
        )

    best: list[dict] = []
    best_relaxations: list[str] = []
    for relaxations, flags in levels:
        matched = [c for c in pool if passes(c, **flags)]
        if len(matched) > len(best):
            best, best_relaxations = matched, relaxations
        if len(matched) >= MIN_POOL:
            return matched[:CONTRIBUTOR_CHECK_LIMIT], relaxations

    # Nothing hit MIN_POOL — return the widest level that found the most.
    return best[:CONTRIBUTOR_CHECK_LIMIT], best_relaxations


def _build_notice(filters: DiscoverRequest, relaxations: list[str], count: int) -> str | None:
    """Plain-language explanation of which filters were widened and why, so a
    thin result set reads as an honest fact about GitHub rather than a bug."""
    if not relaxations:
        return None

    domain = _domain_label(filters.domain)
    parts = []
    if "stars" in relaxations and filters.stars:
        widened = widened_star_bucket_label(filters.stars)
        if widened:
            parts.append(f"widened the star range to {widened}")
    if "contributors" in relaxations:
        parts.append("relaxed the contributor filter")
    if "recent_activity" in relaxations and not parts:
        parts.append("included repositories that haven't been updated recently")
    elif "recent_activity" in relaxations:
        parts.append("included less recently updated repositories")

    if not parts:
        return None
    if len(parts) > 1:
        joined = ", ".join(parts[:-1]) + " and " + parts[-1]
    else:
        joined = parts[0]
    only = "Only a handful of" if count else "No"
    return (
        f"{only} {domain} repositories on GitHub matched your exact filters, "
        f"so we {joined} to show you more options."
    )


def discover_repos(filters: DiscoverRequest, force: bool = False) -> tuple[dict, list[dict]]:
    """(payload, candidates) where payload is {"pool", "relaxations", "notice"}.

    The pool is larger than a single page of results so repeat visits can rotate
    through it (see paginate_pool) instead of showing the same repos forever.

    `candidates` is handed back so the caller can pass it to fill_pool_summaries
    without paying for a second round of GitHub searches. It is empty on a cache
    hit, where there is nothing left to summarize.
    """
    cache_key = _filters_cache_key(filters)
    if not force:
        cached = cache.get(cache_key, ttl_seconds=DISCOVER_TTL_SECONDS)
        if cached:
            return cached, []

    github = GitHubClient(GITHUB_TOKEN)
    candidates, relaxations = _gather_candidates(github, filters)

    domain_label = _domain_label(filters.domain)
    keyword = (filters.keyword or "").strip()
    interest_text = f"{domain_label}: {keyword}" if keyword else domain_label

    pool = rank_and_summarize(
        interest_text, candidates, pool_size=POOL_SIZE, summary_count=MAX_RESULTS
    )
    payload = {
        "pool": pool,
        "relaxations": relaxations,
        "notice": _build_notice(filters, relaxations, len(pool)),
        "interest": interest_text,
    }

    # An empty result is never cached: the previous version stored it and then
    # treated it as a hit forever, so a combination that failed once could never
    # recover even after GitHub caught up. A throttled run is held back for the
    # same reason — its pool is short through no fault of the filters.
    if pool and not github.rate_limited:
        cache.set(cache_key, payload)
    return payload, candidates


def fill_pool_summaries(filters: DiscoverRequest, candidates: list[dict]) -> None:
    """Background pass: summarize the pool entries beyond the first page.

    Runs after the response is sent, so the student never waits on it. The
    candidates come from the request that just ran, so this costs one LLM call
    and no GitHub searches.
    """
    if not candidates:
        return
    cache_key = _filters_cache_key(filters)
    payload = cache.get(cache_key, ttl_seconds=DISCOVER_TTL_SECONDS)
    if not payload or not payload.get("pool"):
        return
    if all(entry.get("summary") for entry in payload["pool"]):
        return

    try:
        payload["pool"] = fill_summaries(
            payload.get("interest") or _domain_label(filters.domain), payload["pool"], candidates
        )
        cache.set(cache_key, payload)
    except Exception as e:
        # Best-effort: the student still has a full first page either way.
        print(f"  [Background summary fill failed] {e}")


def paginate_pool(payload: dict, filters: DiscoverRequest) -> list[dict]:
    """The next `MAX_RESULTS` repos for this student, advancing a per-student
    cursor so returning to the same filters shows repos they haven't seen.

    Entries whose background summary hasn't landed yet are skipped rather than
    rendered blank; the cursor only advances when a full page was served, so a
    short page is retried on the next visit instead of being skipped over.
    """
    ready = [entry for entry in payload.get("pool", []) if entry.get("summary")]
    if not ready:
        return []

    cursor_key = _cursor_cache_key(filters.student_id, _filters_cache_key(filters))
    cursor = cache.get(cursor_key) or 0
    if not isinstance(cursor, int) or cursor < 0:
        cursor = 0

    start = (cursor * MAX_RESULTS) % len(ready)
    window = (ready[start:] + ready[:start])[:MAX_RESULTS]

    if len(window) == MAX_RESULTS:
        cache.set(cursor_key, cursor + 1)
    return window

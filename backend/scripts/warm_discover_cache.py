"""Pre-fill the discovery cache for the filter combinations a class will pick.

Run from the backend directory, ideally the day before a session:
    ./venv/bin/python scripts/warm_discover_cache.py
    ./venv/bin/python scripts/warm_discover_cache.py --domains healthcare,finance
    ./venv/bin/python scripts/warm_discover_cache.py --force

Why this exists: GitHub allows 30 searches per minute and one uncached
discovery spends 6, so only about five students can be waiting on a new filter
combination at once before requests start coming back throttled. Warming the
popular combinations ahead of time turns those into instant cache hits.

Each combination costs one LLM call, and combinations already cached are
skipped unless --force is passed. Discovery caches expire after a week (see
DISCOVER_TTL_SECONDS), so re-run this if a session is more than seven days
after the last warm-up.
"""

import argparse
import itertools
import sys
import time
from pathlib import Path

# Make `import app` work when run directly as scripts/warm_discover_cache.py.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.discovery.orchestrator import (  # noqa: E402
    DISCOVER_TTL_SECONDS,
    _filters_cache_key,
    discover_repos,
    fill_pool_summaries,
)
from app.filters import DOMAINS  # noqa: E402
from app.models.schemas import DiscoverRequest  # noqa: E402
from app.storage import cache  # noqa: E402

# The combinations students actually reach for. Deliberately not the full cross
# product — that would be hundreds of combinations and most would never be hit.
STAR_BUCKETS = [None, "1k-10k", "gt10k"]
CONTRIBUTOR_BUCKETS = [None, "50-200", "gt200"]

# One uncached run spends 6 searches against a 30/minute budget.
SECONDS_BETWEEN_RUNS = 13


def combinations(domains: list[str]):
    for domain, stars, contributors in itertools.product(
        domains, STAR_BUCKETS, CONTRIBUTOR_BUCKETS
    ):
        yield DiscoverRequest(domain=domain, stars=stars, contributors=contributors)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--domains",
        help="Comma-separated domain ids to warm (default: all curated domains)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run combinations that are already cached",
    )
    args = parser.parse_args()

    domains = args.domains.split(",") if args.domains else list(DOMAINS)
    unknown = [d for d in domains if d not in DOMAINS]
    if unknown:
        parser.error(f"unknown domain(s): {', '.join(unknown)}. Known: {', '.join(DOMAINS)}")

    requests = list(combinations(domains))
    print(f"Warming {len(requests)} filter combinations across {len(domains)} domain(s).\n")

    warmed = skipped = failed = 0
    for i, request in enumerate(requests, 1):
        label = (
            f"{request.domain} stars={request.stars or 'any'} "
            f"contributors={request.contributors or 'any'}"
        )

        if not args.force and cache.get(
            _filters_cache_key(request), ttl_seconds=DISCOVER_TTL_SECONDS
        ):
            print(f"[{i}/{len(requests)}] {label} — already cached, skipping")
            skipped += 1
            continue

        print(f"[{i}/{len(requests)}] {label}")
        try:
            payload, candidates = discover_repos(request, force=args.force)
            # Warm the whole pool, not just the first page — otherwise the first
            # student to rotate past page one still waits on a summarize call.
            fill_pool_summaries(request, candidates)
            pool = payload.get("pool", [])
            note = f" (relaxed: {', '.join(payload['relaxations'])})" if payload.get("relaxations") else ""
            print(f"    -> {len(pool)} repos{note}")
            warmed += 1
        except Exception as e:
            print(f"    ! failed: {e}")
            failed += 1

        if i < len(requests):
            time.sleep(SECONDS_BETWEEN_RUNS)

    print(f"\nDone. warmed={warmed} skipped={skipped} failed={failed}")


if __name__ == "__main__":
    main()

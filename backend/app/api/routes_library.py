import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import APIRouter

from app.api.routes_repos import STORY_CAP
from app.config import GITHUB_TOKEN
from app.github_client import GitHubClient
from app.llm.repo_classifier import classify_repos_domains
from app.models.schemas import StorySummary
from app.storage import cache
from app.storage.cache import CACHE_DIR

router = APIRouter(tags=["library"])

# Repo→domain map, computed once per repo (cheap Haiku) and cached. This is the
# staging home for the domain field; it ports straight into a `repos.domain`
# column when the library moves to a database.
DOMAIN_CACHE_KEY = "library:domains:v1"
# Repo→GitHub description, fetched once per repo via a plain REST call (no LLM)
# and cached. Ports into a `repos.description` column later.
DESC_CACHE_KEY = "library:descriptions:v1"


def _to_summary(bundle: dict) -> StorySummary:
    return StorySummary(
        story_id=bundle["story_id"],
        title=bundle["metadata"]["title"],
        labels=bundle["metadata"]["labels"],
        qualities=bundle["metadata"].get("qualities", []),
    )


def _repo_from_cache_key(filename: str) -> str:
    # filename looks like "PaperMC__Paper:pass2.json" → "PaperMC/Paper"
    key = filename.replace(":pass2.json", "")
    return key.replace("__", "/")


@router.get("/library")
def get_library():
    results = []
    if not CACHE_DIR.exists():
        return results

    for path in sorted(CACHE_DIR.glob("*:pass2.json")):
        try:
            bundles = json.loads(path.read_text(encoding="utf-8"))
            repo = _repo_from_cache_key(path.name)
            # Same read-time cap as the stories API — pass2 caches now hold
            # every enriched elite, not just the top few.
            stories = [_to_summary(b) for b in bundles[:STORY_CAP]]
            # Hide repos whose mining yielded no stories — nothing to read.
            if stories:
                results.append({"repo": repo, "stories": stories})
        except Exception:
            continue

    _attach_domains(results)
    _attach_descriptions(results)
    return results


def _attach_descriptions(results: list[dict]) -> None:
    """Attach each repo's GitHub description (no LLM). Only repos we haven't
    fetched before hit the API; results are cached. Failed fetches stay
    uncached so they retry next time; a genuinely empty description caches as
    "" so it isn't re-fetched."""
    desc_map = cache.get(DESC_CACHE_KEY) or {}

    missing = [r["repo"] for r in results if r["repo"] not in desc_map]
    if missing:
        github = GitHubClient(GITHUB_TOKEN)

        def fetch(repo: str):
            obj = github.get_repo(repo)
            if obj.get("full_name"):  # got a valid response
                return repo, (obj.get("description") or "")
            return repo, None  # failed — don't cache, retry later

        with ThreadPoolExecutor(max_workers=8) as executor:
            for repo, desc in executor.map(fetch, missing):
                if desc is not None:
                    desc_map[repo] = desc
        cache.set(DESC_CACHE_KEY, desc_map)

    for r in results:
        r["description"] = desc_map.get(r["repo"]) or None


def _attach_domains(results: list[dict]) -> None:
    """Attach a `domain` id to each entry, classifying only repos we haven't
    seen before and caching the merged map."""
    domain_map = cache.get(DOMAIN_CACHE_KEY) or {}

    unclassified = [
        {"repo": r["repo"], "titles": [s.title for s in r["stories"]]}
        for r in results
        if r["repo"] not in domain_map
    ]
    if unclassified:
        try:
            new_map = classify_repos_domains(unclassified)
        except Exception:
            new_map = {}
        if new_map:
            domain_map = {**domain_map, **new_map}
            cache.set(DOMAIN_CACHE_KEY, domain_map)

    for r in results:
        r["domain"] = domain_map.get(r["repo"])

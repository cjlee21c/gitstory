from app.config import GITHUB_TOKEN
from app.github_client import GitHubClient
from app.pipeline.pass1_5_semantic_gate import pass_1_5_semantic_gate
from app.pipeline.pass1_screening import pass_1_mechanical_screening
from app.pipeline.pass2_enrichment import pass_2_deep_enrichment
from app.storage import cache

# Safety ceiling only — the per-response story cap now lives in the stories
# API (routes_repos.STORY_CAP), applied after quality filtering at read time.
# Pass 2 is LLM-free, so enriching all elites keeps the cache reusable across
# any quality selection without re-running the pipeline. Pass 1's GATE_LIMIT
# already caps the shortlist well below this.
ENRICH_CEILING = 20

# Bumped whenever screening logic changes shape, so tuning thresholds doesn't
# leave every previously-run repo pinned to results from the old rules. Without
# this, loosening a threshold is invisible until someone passes force=true —
# repos screened under the old 8-comment / 5-file cuts stayed at 0 stories
# forever. Mirrors the `discover:v3:` convention in discovery/orchestrator.py.
PIPELINE_VERSION = "v2"


def pass2_cache_key(repo: str) -> str:
    """The read side (stories API) has to look under the same versioned key the
    pipeline writes, so both go through here."""
    return f"{repo}:{PIPELINE_VERSION}:pass2"


def run_pipeline(repo: str, force: bool = False):
    github = GitHubClient(GITHUB_TOKEN)

    pass1_key = f"{repo}:{PIPELINE_VERSION}:pass1"
    pass1_5_key = f"{repo}:{PIPELINE_VERSION}:pass1_5"
    pass2_key = pass2_cache_key(repo)

    if not force:
        bundles = cache.get(pass2_key)
        if bundles is not None:
            print(f"Cache hit for {repo} (pass2). Skipping pipeline.")
            return bundles

    candidates_p1 = None if force else cache.get(pass1_key)
    if candidates_p1 is None:
        candidates_p1 = pass_1_mechanical_screening(repo, github)
        cache.set(pass1_key, candidates_p1)

    elite_p1_5 = None if force else cache.get(pass1_5_key)
    if elite_p1_5 is None:
        elite_p1_5 = pass_1_5_semantic_gate(candidates_p1)
        cache.set(pass1_5_key, elite_p1_5)

    bundles = pass_2_deep_enrichment(repo, elite_p1_5[:ENRICH_CEILING], github)
    cache.set(pass2_key, bundles)
    return bundles

from app.config import GITHUB_TOKEN
from app.github_client import GitHubClient
from app.pipeline.pass1_5_semantic_gate import pass_1_5_semantic_gate
from app.pipeline.pass1_screening import pass_1_mechanical_screening
from app.pipeline.pass2_enrichment import pass_2_deep_enrichment
from app.storage import cache

STORY_CAP = 4


def run_pipeline(repo: str, force: bool = False):
    github = GitHubClient(GITHUB_TOKEN)

    pass1_key = f"{repo}:pass1"
    pass1_5_key = f"{repo}:pass1_5"
    pass2_key = f"{repo}:pass2"

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

    bundles = pass_2_deep_enrichment(repo, elite_p1_5[:STORY_CAP], github)
    cache.set(pass2_key, bundles)
    return bundles

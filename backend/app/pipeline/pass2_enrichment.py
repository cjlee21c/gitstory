import time
from concurrent.futures import ThreadPoolExecutor

from app.github_client import GitHubClient

MAX_WORKERS = 16  # one commits call per candidate, all independent — overlap them harder


def _enrich_candidate(repo: str, github: GitHubClient, candidate: dict):
    """Builds one master bundle for a single elite candidate. The only network
    call here (pulls/{pr}/commits) is independent across candidates, so callers
    can run many of these concurrently."""
    issue = candidate["issue"]
    pr_num = candidate["pr_num"]
    issue_num = issue["number"]

    discussion_timeline = [
        {
            "author": comment["user"]["login"],
            "role": comment.get("author_association", "NONE"),
            "body": comment["body"],
            "timestamp": comment["created_at"],
            # Where it was said: an inline diff comment reads differently from a
            # conversation reply, and the workspace generator cites both.
            "source": comment.get("source", "issue"),
        }
        for comment in candidate["comments"]
    ]

    commits_data = github.get(repo, f"pulls/{pr_num}/commits")
    commit_history = [
        {
            "sha": commit["sha"][:7],
            "message": commit["commit"]["message"],
            "author": commit["commit"]["author"]["name"],
            "timestamp": commit["commit"]["author"]["date"],
        }
        for commit in commits_data
    ]

    bundle = {
        "story_id": f"{repo}#{issue_num}",
        "metadata": {
            "title": issue["title"],
            "labels": [l["name"] for l in issue.get("labels", [])],
            "qualities": candidate.get("qualities", []),
        },
        "pr_metadata": candidate["pr_meta"],
        "issue_payload": {"body": issue.get("body", "")},
        "discussion_timeline": discussion_timeline,
        "commit_history": commit_history,
    }

    print(
        f"  #{issue_num}: {issue['title'][:50]} | "
        f"{len(discussion_timeline)} comments | {len(commit_history)} commits"
    )
    return bundle


def pass_2_deep_enrichment(repo: str, elite_candidates, github: GitHubClient):
    print("\nInitiating Pass 2: Deep Data Enrichment...")
    start = time.time()

    # Each candidate's commit fetch + bundle build is independent, so run them
    # concurrently instead of sequentially. executor.map preserves input order.
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        master_bundles = list(
            executor.map(lambda c: _enrich_candidate(repo, github, c), elite_candidates)
        )

    elapsed = round(time.time() - start, 1)
    print(f"\nPipeline Complete. Built {len(master_bundles)} master bundles. ({elapsed}s)")
    return master_bundles

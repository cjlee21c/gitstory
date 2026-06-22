import time

from app.github_client import GitHubClient


def pass_2_deep_enrichment(repo: str, elite_candidates, github: GitHubClient):
    print("\nInitiating Pass 2: Deep Data Enrichment...")
    start = time.time()
    master_bundles = []

    for candidate in elite_candidates:
        issue = candidate["issue"]
        pr_num = candidate["pr_num"]
        issue_num = issue["number"]

        discussion_timeline = [
            {
                "author": comment["user"]["login"],
                "role": comment.get("author_association", "NONE"),
                "body": comment["body"],
                "timestamp": comment["created_at"],
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
            },
            "pr_metadata": candidate["pr_meta"],
            "issue_payload": {"body": issue.get("body", "")},
            "discussion_timeline": discussion_timeline,
            "commit_history": commit_history,
        }

        master_bundles.append(bundle)
        print(
            f"  #{issue_num}: {issue['title'][:50]} | "
            f"{len(discussion_timeline)} comments | {len(commit_history)} commits"
        )
        time.sleep(1)

    elapsed = round(time.time() - start, 1)
    print(f"\nPipeline Complete. Built {len(master_bundles)} master bundles. ({elapsed}s)")
    return master_bundles

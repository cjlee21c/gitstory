import time

from app.github_client import GitHubClient

MIN_COMMENTS = 8
MAX_CHANGED_FILES = 5
MIN_AUTHORS = 3


def pass_1_mechanical_screening(repo: str, github: GitHubClient):
    print(f"Initiating Pass 1: Mechanical Screening for {repo}...")
    start = time.time()

    issues = github.get(repo, "issues", params={"state": "closed", "sort": "comments", "per_page": 100})
    qualified_candidates = []

    for issue in issues:
        issue_num = issue["number"]

        if issue.get("comments", 0) < MIN_COMMENTS:
            continue

        pr_data = issue.get("pull_request")
        if not pr_data:
            print(f"  [Skip #{issue_num}] No linked PR")
            continue

        pr_num = int(pr_data["url"].split("/")[-1])
        pr_details = github.get(repo, f"pulls/{pr_num}")

        if not pr_details.get("merged"):
            print(f"  [Skip #{issue_num}] PR not merged")
            continue

        if pr_details.get("changed_files", 0) > MAX_CHANGED_FILES:
            print(f"  [Skip #{issue_num}] Too many changed files ({pr_details.get('changed_files')})")
            continue

        comments = github.get(repo, f"issues/{issue_num}/comments", params={"per_page": 100})
        authors = {c["user"]["login"] for c in comments if c.get("user")}
        if issue.get("user"):
            authors.add(issue["user"]["login"])

        if len(authors) < MIN_AUTHORS:
            print(f"  [Skip #{issue_num}] Not enough discussion participants")
            continue

        merged_at = pr_details.get("merged_at", "")
        reviewers = list(
            {r["user"]["login"] for r in github.get(repo, f"pulls/{pr_num}/reviews") if r.get("user")}
        )

        print(f"  [Pass #{issue_num}] {issue['title'][:50]}")
        qualified_candidates.append(
            {
                "issue": issue,
                "pr_num": pr_num,
                "comments": comments,
                "pr_meta": {
                    "merged_at": merged_at,
                    "reviewers": reviewers,
                    "changed_files": pr_details.get("changed_files", 0),
                },
            }
        )
        time.sleep(0.5)

    elapsed = round(time.time() - start, 1)
    print(f"\nPass 1 Complete. {len(qualified_candidates)} candidates survived. ({elapsed}s)")
    return qualified_candidates

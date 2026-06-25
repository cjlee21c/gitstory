import time
from concurrent.futures import ThreadPoolExecutor

from app.github_client import GitHubClient

MIN_COMMENTS = 8
MAX_CHANGED_FILES = 5
MIN_AUTHORS = 3
MAX_WORKERS = 8


def _screen_issue(repo: str, github: GitHubClient, issue: dict):
    """Runs the 3 GitHub API calls needed to fully evaluate one issue. Independent
    across issues, so callers can run many of these concurrently."""
    issue_num = issue["number"]
    pr_num = int(issue["pull_request"]["url"].split("/")[-1])
    pr_details = github.get(repo, f"pulls/{pr_num}")

    if not pr_details.get("merged"):
        print(f"  [Skip #{issue_num}] PR not merged")
        return None

    if pr_details.get("changed_files", 0) > MAX_CHANGED_FILES:
        print(f"  [Skip #{issue_num}] Too many changed files ({pr_details.get('changed_files')})")
        return None

    comments = github.get(repo, f"issues/{issue_num}/comments", params={"per_page": 100})
    authors = {c["user"]["login"] for c in comments if c.get("user")}
    if issue.get("user"):
        authors.add(issue["user"]["login"])

    if len(authors) < MIN_AUTHORS:
        print(f"  [Skip #{issue_num}] Not enough discussion participants")
        return None

    reviewers = list(
        {r["user"]["login"] for r in github.get(repo, f"pulls/{pr_num}/reviews") if r.get("user")}
    )

    print(f"  [Pass #{issue_num}] {issue['title'][:50]}")
    return {
        "issue": issue,
        "pr_num": pr_num,
        "comments": comments,
        "pr_meta": {
            "merged_at": pr_details.get("merged_at", ""),
            "reviewers": reviewers,
            "changed_files": pr_details.get("changed_files", 0),
        },
    }


def pass_1_mechanical_screening(repo: str, github: GitHubClient):
    print(f"Initiating Pass 1: Mechanical Screening for {repo}...")
    start = time.time()

    issues = github.get(repo, "issues", params={"state": "closed", "sort": "comments", "per_page": 100})

    # Cheap filter first (no API calls) so the thread pool below only spends
    # network round trips on issues that actually have a shot at qualifying.
    to_check = []
    for issue in issues:
        if issue.get("comments", 0) < MIN_COMMENTS:
            continue
        if not issue.get("pull_request"):
            print(f"  [Skip #{issue['number']}] No linked PR")
            continue
        to_check.append(issue)

    # Each issue's 3 GitHub calls are independent of every other issue's, so
    # run them concurrently instead of waiting on each one sequentially.
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = executor.map(lambda issue: _screen_issue(repo, github, issue), to_check)
        qualified_candidates = [r for r in results if r is not None]

    elapsed = round(time.time() - start, 1)
    print(f"\nPass 1 Complete. {len(qualified_candidates)} candidates survived. ({elapsed}s)")
    return qualified_candidates

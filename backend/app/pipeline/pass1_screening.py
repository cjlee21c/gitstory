import time

from app.github_client import GitHubClient

# Mechanical screening thresholds (layer 2). Loosened so smaller / less busy
# repos still surface stories — the Pass 1.5 semantic gate remains the quality
# backstop that drops issues without real technical friction.
MIN_COMMENTS = 5       # was 8
MAX_CHANGED_FILES = 10  # was 5
MIN_AUTHORS = 2        # was 3

# One GraphQL query replaces the old "1 list call + 3 REST calls per candidate"
# storm. GitHub's GraphQL `search` takes the same query syntax as REST search,
# so `is:pr is:merged sort:comments-desc` gives us the most-discussed *merged*
# PRs (no wasted round trips on un-merged / PR-less issues), and the nested
# selection pulls changed-file count, the comment thread, and reviewers in the
# same request.
#
# The fetch depths are deliberately shallow: GraphQL resolves every nested
# connection eagerly, so `comments(first: 100)` on 50 PRs made the server do far
# more work than the REST short-circuit and ran *slower* (~5s vs ~1.7s measured).
# 30 PRs × 40 comments is ample — the gate reads 5 comments, the workspace
# samples 15 — and keeps the query resolving in ~2s.
SEARCH_LIMIT = 30
_PR_SEARCH_QUERY = """
query($q: String!, $first: Int!) {
  search(query: $q, type: ISSUE, first: $first) {
    nodes {
      ... on PullRequest {
        number
        title
        body
        changedFiles
        mergedAt
        author { login }
        labels(first: 20) { nodes { name } }
        comments(first: 40) {
          totalCount
          nodes { author { login } authorAssociation body createdAt }
        }
        reviews(first: 20) { nodes { author { login } } }
      }
    }
  }
}
"""


def _to_candidate(pr: dict) -> dict:
    """Reshapes a GraphQL PullRequest node into the REST-compatible candidate
    dict the downstream passes (1.5 gate, 2 enrichment) already expect. GraphQL
    author fields are nullable (deleted accounts), so guard every `.login`."""
    comments = [
        {
            "user": {"login": (c["author"] or {}).get("login", "ghost")},
            "author_association": c["authorAssociation"],
            "body": c["body"] or "",
            "created_at": c["createdAt"],
        }
        for c in pr["comments"]["nodes"]
    ]
    reviewers = list(
        {(r["author"] or {}).get("login") for r in pr["reviews"]["nodes"] if r.get("author")}
    )
    pr_author = (pr["author"] or {}).get("login", "ghost")
    issue = {
        "number": pr["number"],
        "title": pr["title"],
        "body": pr["body"] or "",
        "labels": [{"name": l["name"]} for l in pr["labels"]["nodes"]],
        "user": {"login": pr_author},
    }
    return {
        # A PR's number is its issue number in GitHub, so pr_num == issue number.
        "issue": issue,
        "pr_num": pr["number"],
        "comments": comments,
        "pr_meta": {
            "merged_at": pr["mergedAt"] or "",
            "reviewers": reviewers,
            "changed_files": pr["changedFiles"],
        },
    }


def pass_1_mechanical_screening(repo: str, github: GitHubClient):
    print(f"Initiating Pass 1: Mechanical Screening for {repo}...")
    start = time.time()

    query = f"repo:{repo} is:pr is:merged sort:comments-desc"
    data = github.graphql(_PR_SEARCH_QUERY, {"q": query, "first": SEARCH_LIMIT})
    nodes = ((data.get("data") or {}).get("search") or {}).get("nodes") or []

    qualified_candidates = []
    for pr in nodes:
        if not pr:  # non-PullRequest nodes come back empty for the inline fragment
            continue
        num = pr["number"]
        if pr["comments"]["totalCount"] < MIN_COMMENTS:
            continue
        if pr["changedFiles"] > MAX_CHANGED_FILES:
            print(f"  [Skip #{num}] Too many changed files ({pr['changedFiles']})")
            continue

        candidate = _to_candidate(pr)
        authors = {c["user"]["login"] for c in candidate["comments"]}
        authors.add(candidate["issue"]["user"]["login"])
        if len(authors) < MIN_AUTHORS:
            print(f"  [Skip #{num}] Not enough discussion participants")
            continue

        print(f"  [Pass #{num}] {pr['title'][:50]}")
        qualified_candidates.append(candidate)

    elapsed = round(time.time() - start, 1)
    print(f"\nPass 1 Complete. {len(qualified_candidates)} candidates survived. ({elapsed}s)")
    return qualified_candidates

import time

from app.github_client import GitHubClient
from app.pipeline.ranking import body_signals, stage1_score

# Mechanical screening is now rank-and-cut, not accept/reject. The only hard
# floors left are the ones that mean "there is no discussion here at all" —
# everything else (size, comment volume) is a ranking signal in ranking.py.
#
# The old thresholds rejected on `comments.totalCount`, which counts *issue*
# comments only. GitHub's `sort:comments-desc` ranks by issue + review comments,
# so review-centric repos (Google/Microsoft house style: all discussion inline
# on the diff) had every one of their top PRs discarded — 30 hits, 0 survivors.
MIN_DISCUSSION = 5   # total comments, review threads included
MIN_AUTHORS = 2

# How many ranked candidates get the expensive treatment. Measured score
# distributions fall off a cliff past ~12 across repo shapes, and 12 candidates
# at the gate's ~65% pass rate comfortably fills STORY_CAP=4.
GATE_LIMIT = 12

# Skip the review-body round trip when the issue thread alone already gives the
# gate and the workspace enough to read.
ISSUE_COMMENTS_SUFFICIENT = 8

SEARCH_LIMIT = 30

# `totalCommentsCount` is a precomputed scalar (issue + review comments), so it
# costs no extra resolution time — measured 3.2s -> 3.1s on saleor/saleor. That
# is what makes ranking-before-fetching possible: we can order all 30 hits by
# true discussion volume without paying for a single comment body.
#
# The fetch depths stay shallow on purpose. GraphQL resolves nested connections
# eagerly, so pulling review bodies for all 30 hits here costs +4.2s (3.2s ->
# 7.4s). Pass 1b fetches them for the top GATE_LIMIT only, at +2.3s.
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
        totalCommentsCount
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

# Pass 1b: review bodies + inline thread comments for the ranked shortlist,
# batched into one aliased query (12 PRs = 4 GraphQL rate-limit points).
_REVIEW_FIELDS = """
    reviews(first: 30) {
      nodes {
        author { login }
        authorAssociation
        body
        submittedAt
        comments(first: 20) {
          nodes { author { login } authorAssociation body createdAt path }
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
            "source": "issue",
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


def _search_signals(pr: dict, candidate: dict) -> dict:
    """Stage-1 signals, all read off the search response."""
    participants = {(pr["author"] or {}).get("login")}
    participants |= {c["user"]["login"] for c in candidate["comments"]}
    participants |= set(candidate["pr_meta"]["reviewers"])
    participants.discard(None)
    return {
        "discussion": pr["totalCommentsCount"],
        "participants": len(participants),
        "changed_files": pr["changedFiles"],
    }


def _review_query(candidates: list[dict]) -> str:
    aliases = "\n".join(
        f'p{c["pr_num"]}: pullRequest(number: {c["pr_num"]}) {{ number {_REVIEW_FIELDS} }}'
        for c in candidates
    )
    return f"query($owner: String!, $name: String!) {{ repository(owner: $owner, name: $name) {{\n{aliases}\n}} }}"


def _merge_review_comments(candidate: dict, pr_node: dict) -> int:
    """Folds review bodies and inline diff comments into the candidate's comment
    timeline, so the gate and the workspace generator see the discussion that
    actually happened. Returns how many were added.

    Inline comments carry their file path — that context is what makes a review
    thread readable out of the diff's context."""
    added = []
    for review in (pr_node.get("reviews") or {}).get("nodes") or []:
        author = (review.get("author") or {}).get("login", "ghost")
        body = (review.get("body") or "").strip()
        if body:
            added.append(
                {
                    "user": {"login": author},
                    "author_association": review.get("authorAssociation", "NONE"),
                    "body": body,
                    "created_at": review.get("submittedAt") or "",
                    "source": "review",
                }
            )
        for c in (review.get("comments") or {}).get("nodes") or []:
            c_body = (c.get("body") or "").strip()
            if not c_body:
                continue
            path = c.get("path")
            added.append(
                {
                    "user": {"login": (c.get("author") or {}).get("login", "ghost")},
                    "author_association": c.get("authorAssociation", "NONE"),
                    "body": f"[{path}] {c_body}" if path else c_body,
                    "created_at": c.get("createdAt") or "",
                    "source": "review_inline",
                }
            )

    candidate["comments"].extend(added)
    # Chronological order matters: the gate reads the head of this list, and
    # `alternations` is meaningless if the timeline is grouped by source.
    candidate["comments"].sort(key=lambda c: c.get("created_at") or "")
    return len(added)


def _fetch_review_threads(repo: str, github: GitHubClient, candidates: list[dict]) -> None:
    """Pass 1b. One batched query for the whole shortlist; fails soft, since a
    candidate without review bodies is still usable (just thinner)."""
    needs_fetch = [
        c
        for c in candidates
        if sum(1 for x in c["comments"] if x["source"] == "issue") < ISSUE_COMMENTS_SUFFICIENT
    ]
    if not needs_fetch:
        print("  [Pass 1b] Issue threads already substantial — skipping review fetch.")
        return

    owner, _, name = repo.partition("/")
    data = github.graphql(_review_query(needs_fetch), {"owner": owner, "name": name})
    repo_node = ((data.get("data") or {}).get("repository")) or {}
    if not repo_node:
        print(f"  [Pass 1b] Review fetch failed for {repo} — continuing with issue comments only.")
        return

    total = 0
    for candidate in needs_fetch:
        pr_node = repo_node.get(f"p{candidate['pr_num']}")
        if pr_node:
            total += _merge_review_comments(candidate, pr_node)
    print(f"  [Pass 1b] Pulled {total} review comments across {len(needs_fetch)} PRs.")


def pass_1_mechanical_screening(repo: str, github: GitHubClient):
    print(f"Initiating Pass 1: Ranked Screening for {repo}...")
    start = time.time()

    query = f"repo:{repo} is:pr is:merged sort:comments-desc"
    data = github.graphql(_PR_SEARCH_QUERY, {"q": query, "first": SEARCH_LIMIT})
    nodes = ((data.get("data") or {}).get("search") or {}).get("nodes") or []

    scored = []
    for pr in nodes:
        if not pr:  # non-PullRequest nodes come back empty for the inline fragment
            continue
        num = pr["number"]
        candidate = _to_candidate(pr)
        signals = _search_signals(pr, candidate)

        if signals["discussion"] < MIN_DISCUSSION:
            continue
        if signals["participants"] < MIN_AUTHORS:
            print(f"  [Skip #{num}] Not enough discussion participants")
            continue

        candidate["signals"] = signals
        scored.append((stage1_score(signals), candidate))

    scored.sort(key=lambda x: -x[0])
    shortlist = [c for _, c in scored[:GATE_LIMIT]]

    for score, candidate in scored[:GATE_LIMIT]:
        s = candidate["signals"]
        print(
            f"  [Rank {score:5.1f}] #{candidate['pr_num']:<7} "
            f"{s['discussion']} comments / {s['participants']} people / "
            f"{s['changed_files']} files | {candidate['issue']['title'][:44]}"
        )

    if shortlist:
        _fetch_review_threads(repo, github, shortlist)
        for candidate in shortlist:
            candidate["signals"].update(body_signals(candidate["comments"]))

    elapsed = round(time.time() - start, 1)
    print(
        f"\nPass 1 Complete. {len(scored)} candidates ranked, "
        f"top {len(shortlist)} shortlisted. ({elapsed}s)"
    )
    return shortlist

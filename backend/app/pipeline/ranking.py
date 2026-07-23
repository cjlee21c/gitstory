"""Candidate ranking — the two-stage scoring that replaces Pass 1's hard cuts.

Stage 1 scores all 30 search hits using only fields the single search query
already returns (GitHub's `totalCommentsCount` scalar costs no extra latency),
so the expensive review-body fetch runs on the top slice instead of everything.
Stage 2 re-scores that slice once bodies are in hand, ordering what the story
cap ultimately picks from.

The old design hard-rejected on comment count and changed-file count. Both are
ranking signals here instead: a hard cut on `changedFiles` fought the
`sort:comments-desc` ordering (the most-discussed PRs are the big ones), and a
hard cut on issue-comment count discarded review-centric repos entirely.
"""

import math

MAINTAINER_ROLES = {"MEMBER", "OWNER", "COLLABORATOR"}

# A comment long enough to carry an argument rather than "LGTM" / "+1".
SUBSTANTIVE_CHARS = 240

# Changed files are free up to this point, then cost a log-scaled penalty. A
# 132-file PR still places mid-pack if its discussion is rich enough.
FREE_CHANGED_FILES = 10
SIZE_PENALTY_WEIGHT = 2.0

# Diminishing returns: the 11th participant says little the 6th didn't.
MAX_PARTICIPANTS = 6
MAX_SUBSTANTIVE = 8
MAX_ALTERNATIONS = 10


def _size_penalty(changed_files: int) -> float:
    if changed_files <= FREE_CHANGED_FILES:
        return 0.0
    return SIZE_PENALTY_WEIGHT * math.log2(changed_files / FREE_CHANGED_FILES)


def stage1_score(signals: dict) -> float:
    """Ranks raw search hits. Only uses signals present in the search response,
    so it never triggers an extra round trip."""
    score = 2.0 * math.log1p(signals["discussion"])
    score += 2.5 * min(signals["participants"], MAX_PARTICIPANTS)
    score -= _size_penalty(signals["changed_files"])
    return score


def stage2_score(signals: dict) -> float:
    """Re-ranks candidates whose comment bodies have been fetched. Adds the
    signals that separate a real argument from a long thread of approvals."""
    score = stage1_score(signals)
    score += 1.2 * min(signals["substantive"], MAX_SUBSTANTIVE)
    score += 0.8 * min(signals["alternations"], MAX_ALTERNATIONS)
    score += 2.0 if signals["maintainer_engaged"] else 0.0
    return score


def body_signals(comments: list[dict]) -> dict:
    """Substance signals over a merged comment timeline. `alternations` counts
    speaker changes — a 40-comment thread by one person is a monologue, not a
    debate."""
    substantive = sum(1 for c in comments if len(c.get("body") or "") > SUBSTANTIVE_CHARS)

    authors = [(c.get("user") or {}).get("login") for c in comments]
    alternations = sum(
        1 for a, b in zip(authors, authors[1:]) if a and b and a != b
    )
    maintainer_engaged = any(
        c.get("author_association") in MAINTAINER_ROLES for c in comments
    )
    return {
        "substantive": substantive,
        "alternations": alternations,
        "maintainer_engaged": maintainer_engaged,
    }

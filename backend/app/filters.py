"""Single source of truth for the two-stage search filter options.

Stage 1 (repository filters) map to GitHub search qualifiers applied in
discovery; Stage 2 (quality attributes) drive story labeling in pass 1.5
and read-time filtering in the stories API. The frontend mirrors these ids
in frontend/src/filters.ts — a mismatched id fails request validation.
"""

DOMAINS = {
    "gaming": {
        "label": "Gaming",
        "keywords": ["game engine", "game framework", "chess engine"],
    },
    "finance": {
        "label": "Finance",
        "keywords": ["trading", "quantitative finance", "payments"],
    },
    "healthcare": {
        "label": "Healthcare",
        "keywords": ["healthcare", "medical imaging", "health records"],
    },
    "education": {
        "label": "Education",
        "keywords": ["learning platform", "education", "flashcards"],
    },
    "developer_tools": {
        "label": "Developer Tools",
        "keywords": ["code editor", "build tool", "debugger"],
    },
    "social": {
        "label": "Social / Communication",
        "keywords": ["chat", "messaging", "social network"],
    },
    "media": {
        "label": "Media / Entertainment",
        "keywords": ["media server", "video player", "music player"],
    },
    "science": {
        "label": "Science / Research",
        "keywords": ["scientific computing", "data analysis", "bioinformatics"],
    },
}

# Disk size in KB (GitHub's `size:` qualifier unit). Half-open ranges: a
# bucket is (lo, hi) meaning lo <= size < hi; hi=None means unbounded.
SIZE_BUCKETS = {
    "small": (0, 5_000),        # < 5 MB
    "medium": (5_000, 50_000),  # 5–50 MB
    "large": (50_000, None),    # > 50 MB
}

STAR_BUCKETS = {
    "lt100": (None, 100),
    "100-1k": (100, 1_000),
    "1k-10k": (1_000, 10_000),
    "gt10k": (10_000, None),
}

CONTRIBUTOR_BUCKETS = {
    "lt10": (None, 10),
    "10-50": (10, 50),
    "50-200": (50, 200),
    "gt200": (200, None),
}

# Definitions phrased in issue-discussion terms; they feed both the pass 1.5
# gate prompt and the structured-output schema enum so the two can't drift.
QUALITY_DEFINITIONS = {
    "security": (
        "vulnerabilities, authentication/authorization, input validation, "
        "secrets handling, or safe processing of untrusted data"
    ),
    "performance": (
        "speed, latency, memory usage, scalability, caching, or algorithmic "
        "efficiency"
    ),
    "usability": (
        "user experience, API ergonomics, error messages, accessibility, or "
        "developer experience"
    ),
    "maintainability": (
        "code structure, refactoring, technical debt, testing, modularity, "
        "or long-term evolvability"
    ),
}

QUALITY_ATTRIBUTES = list(QUALITY_DEFINITIONS)


def size_qualifier(sizes: list[str]) -> str | None:
    """One merged `size:` range spanning the selected buckets. Non-contiguous
    selections (small + large) are handled by the exact in_size_buckets()
    post-check; the qualifier only narrows the GitHub search."""
    if not sizes:
        return None
    bounds = [SIZE_BUCKETS[s] for s in sizes]
    lo = min(b[0] for b in bounds)
    highs = [b[1] for b in bounds]
    if any(h is None for h in highs):
        return None if lo == 0 else f"size:>={lo}"
    return f"size:{lo}..{max(highs)}"


def star_qualifier(bucket: str | None) -> str | None:
    if bucket is None:
        return None
    lo, hi = STAR_BUCKETS[bucket]
    if lo is None:
        return f"stars:<{hi}"
    if hi is None:
        return f"stars:>={lo}"
    return f"stars:{lo}..{hi}"


def _in_bucket(value: int, bounds: tuple[int | None, int | None]) -> bool:
    lo, hi = bounds
    return (lo is None or value >= lo) and (hi is None or value < hi)


def in_size_buckets(size_kb: int, sizes: list[str]) -> bool:
    if not sizes:
        return True
    return any(_in_bucket(size_kb, SIZE_BUCKETS[s]) for s in sizes)


def in_contributor_bucket(count: int, bucket: str | None) -> bool:
    if bucket is None:
        return True
    return _in_bucket(count, CONTRIBUTOR_BUCKETS[bucket])

"""Single source of truth for the two-stage search filter options.

Stage 1 (repository filters) map to GitHub search qualifiers applied in
discovery; Stage 2 (quality attributes) drive story labeling in pass 1.5
and read-time filtering in the stories API. The frontend mirrors these ids
in frontend/src/filters.ts — a mismatched id fails request validation.

Each domain carries three search surfaces, because any one of them alone
yields far too few candidates once star/contributor filters are stacked on
top (e.g. `healthcare stars:>=10000` matches 2 repos on all of GitHub):

  keywords — phrase queries. Multi-word entries are AND-ed by GitHub, so
             these are precise but narrow.
  topics   — GitHub topic slugs, queried one per search since multiple
             `topic:` terms in one query are AND-ed. The most reliable
             domain signal, but only covers repos whose owners tagged them.
  terms    — single words OR-ed into one broad query. The widest net:
             `healthcare OR medical OR clinical` matches ~45x more repos
             than the phrase query alone.

topics/terms are backend-only — the frontend mirror needs the ids and
labels, not the search surfaces.
"""

DOMAINS = {
    "gaming": {
        "label": "Gaming",
        "keywords": ["game engine", "game framework", "chess engine", "physics engine",
                     "game server", "rendering engine"],
        "topics": ["game-engine", "gamedev", "game-development", "game"],
        "terms": ["game", "gamedev", "engine", "rendering"],
    },
    "finance": {
        "label": "Finance",
        "keywords": ["trading", "quantitative finance", "payments", "algorithmic trading",
                     "accounting", "banking"],
        "topics": ["finance", "trading", "fintech", "algorithmic-trading"],
        "terms": ["trading", "finance", "payments", "banking"],
    },
    "healthcare": {
        "label": "Healthcare",
        "keywords": ["healthcare", "medical imaging", "health records",
                     "electronic health record", "telemedicine", "hospital management"],
        "topics": ["healthcare", "medical", "fhir", "ehr"],
        "terms": ["healthcare", "medical", "clinical", "patient"],
    },
    "education": {
        "label": "Education",
        # "learning" is deliberately absent from terms and topics: it matches
        # "machine learning" far more often than anything about teaching, and
        # pulled tensorflow/keras/scikit-learn into this domain. The surfaces
        # here aim at education *software* (an LMS, a flashcard app) rather than
        # learning materials, which are mostly awesome-lists with no
        # engineering discussion to mine.
        "keywords": ["learning management system", "flashcards", "online courses",
                     "student information system", "quiz platform", "learning platform"],
        "topics": ["lms", "learning-management-system", "education", "elearning"],
        "terms": ["education", "teaching", "courseware", "classroom"],
    },
    "developer_tools": {
        "label": "Developer Tools",
        "keywords": ["code editor", "build tool", "debugger", "package manager",
                     "static analysis", "language server"],
        "topics": ["developer-tools", "cli", "build-tool", "code-editor"],
        "terms": ["editor", "compiler", "debugger", "linter"],
    },
    "social": {
        "label": "Social / Communication",
        "keywords": ["chat", "messaging", "social network", "forum software",
                     "video conferencing", "federated social"],
        "topics": ["chat", "messaging", "social-network", "communication"],
        "terms": ["chat", "messaging", "social", "forum"],
    },
    "media": {
        "label": "Media / Entertainment",
        "keywords": ["media server", "video player", "music player", "video editing",
                     "audio processing", "streaming server"],
        "topics": ["media-server", "video", "music", "streaming"],
        "terms": ["media", "video", "audio", "streaming"],
    },
    "science": {
        "label": "Science / Research",
        "keywords": ["scientific computing", "data analysis", "bioinformatics",
                     "numerical simulation", "computational biology", "physics simulation"],
        "topics": ["scientific-computing", "data-science", "bioinformatics", "simulation"],
        "terms": ["scientific", "simulation", "bioinformatics", "numerical"],
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

# Narrowest to widest, so discovery can widen a bucket by one notch when the
# student's pick matches almost nothing on GitHub.
STAR_ORDER = ["lt100", "100-1k", "1k-10k", "gt10k"]

CONTRIBUTOR_BUCKETS = {
    "lt10": (None, 10),
    "10-50": (10, 50),
    "50-200": (50, 200),
    "gt200": (200, None),
}

# The eight quality attributes taught in the course, phrased in
# issue-discussion terms. Each definition is a compressed tactic cluster drawn
# from that attribute's tactics slide, because naming concrete tactics ("retry",
# "graceful degradation") gives the gate far more to match against than an
# abstract gloss would.
#
# This dict is the single source: pass 1.5 renders it into the gate prompt AND
# into the structured-output enum, and the stories API seeds its counts from
# QUALITY_ATTRIBUTES. Editing here changes all three together.
#
# ORDER MATTERS for the UI: frontend/src/filters.ts mirrors these ids, and a
# mismatched id fails request validation.
#
# Each definition follows its slide's own tactic tree: the top-level categories
# in order, with that category's concrete tactics named. The tactic names are
# what earn their keep — "graceful degradation" or "record/playback" appear
# almost verbatim in real PR discussions, where an abstract gloss like "handles
# failure well" matches nothing.
QUALITY_DEFINITIONS = {
    "availability": (
        "detecting faults (monitor, ping/echo, heartbeat, timestamp, condition "
        "monitoring, sanity checking, voting, exception detection, self-test), "
        "recovering from faults (redundant spare, rollback, exception handling, "
        "software upgrade, retry, ignore faulty behavior, graceful degradation, "
        "reconfiguration, shadow, state resynchronization, escalating restart, "
        "nonstop forwarding), or preventing faults (removal from service, "
        "transactions, predictive model, exception prevention, increase "
        "competence set)"
    ),
    "security": (
        "detecting attacks (detect intrusion, detect service denial, verify "
        "message integrity, detect message delivery anomalies), resisting them "
        "(identify/authenticate/authorize actors, limit access, limit exposure, "
        "encrypt data, separate entities, validate input, change credential "
        "settings), reacting to them (revoke access, restrict login, inform "
        "actors), or recovering from them (audit, nonrepudiation)"
    ),
    "modifiability": (
        "increasing cohesion (split module, redistribute responsibilities), "
        "reducing coupling (encapsulate, use an intermediary, abstract common "
        "services, restrict dependencies), or deferring binding (component "
        "replacement, compile-time parameterization, aspects, "
        "configuration-time binding, resource files, discovery, interpret "
        "parameters, shared repositories, polymorphism)"
    ),
    "performance": (
        "controlling resource demand (manage work requests, limit event "
        "response, prioritize events, reduce computational overhead, bound "
        "execution times, increase efficiency) or managing resources (increase "
        "resources, introduce concurrency, maintain multiple copies of "
        "computations or data, bound queue sizes, schedule resources) — where "
        "the goal is latency, throughput, or scalability"
    ),
    "testability": (
        "controlling and observing system state (specialized interfaces, "
        "record/playback, localize state storage, abstract data sources, "
        "sandbox, executable assertions) or limiting complexity (limit "
        "structural complexity, limit nondeterminism) — including flaky tests "
        "and code that is hard to write a test for"
    ),
    "usability": (
        "supporting user initiative (cancel, undo, pause/resume, aggregate) or "
        "supporting system initiative (maintain task model, maintain user "
        "model, maintain system model) — including API ergonomics, error "
        "messages, and accessibility"
    ),
    "deployability": (
        "managing the deployment pipeline (scale rollouts, script deployment "
        "commands, rollback) or managing the deployed system (manage service "
        "interactions, package dependencies, toggle features)"
    ),
    "energy_efficiency": (
        "monitoring resources (metering, static or dynamic classification), "
        "allocating resources (reduce usage, discovery, schedule resources), or "
        "reducing resource demand (manage event arrival, limit event response, "
        "prioritize events, reduce computational overhead, bound execution "
        "times, increase resource usage efficiency) — only when the discussion "
        "is explicitly about energy, power draw, battery life, or carbon cost, "
        "not merely about speed"
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


def widen_star_qualifier(bucket: str | None) -> str | None:
    """The bucket merged with the one below it, as a GitHub qualifier.

    Used as the *search* qualifier so a single query covers both the strict
    and the relaxed range; discovery then narrows back down in Python. Returns
    None when there is nothing below to merge (already the widest, or no
    bucket picked), which callers read as "no star qualifier at all".
    """
    if bucket is None:
        return None
    index = STAR_ORDER.index(bucket)
    if index == 0:
        return None
    lo = STAR_BUCKETS[STAR_ORDER[index - 1]][0]
    hi = STAR_BUCKETS[bucket][1]
    if lo is None:
        return f"stars:<{hi}"
    if hi is None:
        return f"stars:>={lo}"
    return f"stars:{lo}..{hi}"


def widened_star_bucket_label(bucket: str) -> str | None:
    """Plain-language label for the widened range, for the student-facing
    notice ("we widened the star filter to 1k+")."""
    index = STAR_ORDER.index(bucket)
    if index == 0:
        return None
    lo, hi = STAR_BUCKETS[STAR_ORDER[index - 1]][0], STAR_BUCKETS[bucket][1]
    if lo is None:
        return f"under {hi:,}"
    if hi is None:
        return f"{lo:,}+"
    return f"{lo:,}–{hi:,}"


def _in_bucket(value: int, bounds: tuple[int | None, int | None]) -> bool:
    lo, hi = bounds
    return (lo is None or value >= lo) and (hi is None or value < hi)


def in_size_buckets(size_kb: int, sizes: list[str]) -> bool:
    if not sizes:
        return True
    return any(_in_bucket(size_kb, SIZE_BUCKETS[s]) for s in sizes)


def in_star_bucket(count: int, bucket: str | None) -> bool:
    if bucket is None:
        return True
    return _in_bucket(count, STAR_BUCKETS[bucket])


def in_contributor_bucket(count: int, bucket: str | None) -> bool:
    if bucket is None:
        return True
    return _in_bucket(count, CONTRIBUTOR_BUCKETS[bucket])

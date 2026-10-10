"""Replaces the real people in a story with per-story pseudonyms.

The discussion data is public GitHub activity, so this is de-identification
rather than secrecy: the point is that nobody reading a GitStories workspace —
or the paper built from it — can tell which real person argued what. Those
people never agreed to appear in teaching material.

Two call sites, deliberately both:

  pseudonymize_bundle()  before the bundle is sent to the LLM, so the model
                         never sees a real identity and cannot write one down.
  scrub_workspace()      over generated beats before they are cached, as a net
                         for anything the model echoed back anyway.

Aliases are numbered per story, never globally. A global map would let anyone
line two stories up side by side and re-identify a person from the overlap.

scripts/check_privacy.py asserts the result over the whole cache and fails the
build on a leak; run it after touching anything here or in the prompts.
"""

import re

# A reviewer listed in pr_metadata carries no author_association, so it gets its
# own pseudo-association here. Bots get theirs too: CI and review bots are not
# people and need no protecting, but calling one "Outside Commenter A" would
# read to a student as a human saying the build failed.
_REVIEWER_ROLE = "_reviewer"
_BOT_ROLE = "_bot"

# GitHub's author_association values, mapped to the role a student should see.
# Keeping the maintainer/contributor/outsider split is deliberate: a repo
# owner's objection carries different weight from a first-time commenter's, and
# reading that difference is part of what the story teaches. The grouping
# matches roleTone() in frontend/src/components/workspace/ViewpointBeat.tsx.
ROLE_LABELS = {
    "OWNER": "Maintainer",
    "MEMBER": "Maintainer",
    "COLLABORATOR": "Maintainer",
    "CONTRIBUTOR": "Contributor",
    "NONE": "Outside Commenter",
    _REVIEWER_ROLE: "Reviewer",
    _BOT_ROLE: "Automation",
}
FALLBACK_LABEL = "Participant"

# For a person we can name but cannot place in the discussion — a commit author
# who never commented, so there is no alias of theirs to use.
REDACTED_NAME = "a contributor"

# Path and URL shapes that embed a username. Comment bodies paste shell output
# and links ("/home/moul/go/src/...", "github.com/jcfr/CTK/blob/..."), which
# identifies the account even when the bare login is too word-like to replace.
_PATH_PREFIXES = ("/home/", "/Users/", "github.com/", "githubusercontent.com/")

# Commit trailers and review text carry addresses ("Co-authored-by: X <x@y.io>").
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")

# Any remaining @handle is a username by definition, even one belonging to
# someone who never posted in this story and so has no alias. The lookbehind
# keeps it off the local part of an address, where the @ follows a word char.
_LOOSE_MENTION_RE = re.compile(r"(?<![\w.])@([A-Za-z0-9][A-Za-z0-9-]{0,38})\b")


def _alias_suffix(index: int) -> str:
    """0 -> A, 25 -> Z, 26 -> AA. Spreadsheet-column lettering."""
    letters = ""
    index += 1
    while index:
        index, rem = divmod(index - 1, 26)
        letters = chr(ord("A") + rem) + letters
    return letters


def _is_distinctive(name: str) -> bool:
    """Whether a bare occurrence of this name in prose is safely a person.

    Some real logins in this corpus are ordinary English words — `cart`, `fire`,
    `viet` — and blindly replacing those would rewrite sentences about shopping
    carts and firing events. Names that are long, or that mix in a digit, hyphen
    or capital, can't collide with prose. The rest are still replaced wherever
    an `@` or a path prefix marks them as a username.
    """
    return len(name) >= 5 or any(c.isdigit() or c == "-" or c.isupper() for c in name)


def _is_bot(login: str) -> bool:
    """GitHub suffixes app accounts with "[bot]". Bots whose login hides it
    (a plain account used for CI) just get a person alias, which over-applies
    the pseudonym harmlessly."""
    return login.lower().endswith("[bot]")


def _commit_names(bundle: dict) -> set[str]:
    """Author names off commit metadata. These are real legal names ("Alice
    Cecile") as often as they are handles, and they belong to people who may
    never have posted a comment — so they need their own handling."""
    return {c["author"] for c in bundle.get("commit_history") or [] if c.get("author")}


def build_alias_map(bundle: dict) -> dict[str, str]:
    """login -> "Maintainer A". Numbered in order of first appearance in the
    discussion, so the aliases read in the order a student meets them."""
    roles: dict[str, str] = {}
    for entry in bundle.get("discussion_timeline") or []:
        login = entry.get("author")
        if login and login not in roles:
            roles[login] = _BOT_ROLE if _is_bot(login) else (entry.get("role") or "NONE")
    for login in bundle.get("pr_metadata", {}).get("reviewers") or []:
        if login and login not in roles:
            roles[login] = _BOT_ROLE if _is_bot(login) else _REVIEWER_ROLE

    counters: dict[str, int] = {}
    aliases: dict[str, str] = {}
    for login, role in roles.items():
        label = ROLE_LABELS.get(role, FALLBACK_LABEL)
        seen = counters.get(label, 0)
        counters[label] = seen + 1
        aliases[login] = f"{label} {_alias_suffix(seen)}"
    return aliases


def build_name_map(bundle: dict, aliases: dict[str, str]) -> dict[str, str]:
    """Commit-metadata names -> their replacement. A name that *is* one of the
    discussion logins reuses that person's alias, so the text stays coherent;
    anyone else becomes a neutral phrase, because there is no position of theirs
    for a student to attribute anything to."""
    by_lower = {login.lower(): alias for login, alias in aliases.items()}
    return {
        name: by_lower.get(name.lower(), REDACTED_NAME) for name in _commit_names(bundle) if name
    }


def scrub_text(text: str, aliases: dict[str, str]) -> str:
    """Replace every recognizable reference to a known login with its alias."""
    if not text or not aliases:
        return text
    # Longest login first, so "arthuro" can't claim the prefix of "arthuro555".
    for login in sorted(aliases, key=len, reverse=True):
        alias = aliases[login]
        escaped = re.escape(login)
        # An @ makes it unambiguously a mention, whatever the login looks like.
        text = re.sub(rf"@{escaped}\b", lambda _m, a=alias: a, text, flags=re.I)
        for prefix in _PATH_PREFIXES:
            text = re.sub(
                rf"({re.escape(prefix)}){escaped}\b",
                lambda m, a=alias: m.group(1) + a,
                text,
                flags=re.I,
            )
        if _is_distinctive(login):
            text = re.sub(rf"\b{escaped}\b", lambda _m, a=alias: a, text, flags=re.I)
    return text


def redact_names(text: str, names: dict[str, str]) -> str:
    """Replace commit-metadata names. Multi-token names ("Alice Cecile") are
    distinctive enough to match on sight; a single token has to pass the same
    word-collision guard as a login."""
    if not text or not names:
        return text
    for name in sorted(names, key=len, reverse=True):
        if " " in name:
            if len(name) < 4:
                continue
        elif not _is_distinctive(name):
            continue
        text = re.sub(
            rf"\b{re.escape(name)}\b", lambda _m, r=names[name]: r, text, flags=re.I
        )
    return text


def redact_contacts(text: str) -> str:
    """Strip addresses, then any @handle still standing — including handles of
    people who never posted here, who therefore have no alias to receive."""
    if not text:
        return text
    text = _EMAIL_RE.sub(REDACTED_NAME, text)
    return _LOOSE_MENTION_RE.sub(REDACTED_NAME, text)


def _cleaner(bundle: dict):
    """The full text pass, in the order that matters: known logins first so they
    keep their alias, then commit names, then whatever contact details are left
    over for the blunt sweep."""
    aliases = build_alias_map(bundle)
    names = build_name_map(bundle, aliases)

    def clean(text: str) -> str:
        return redact_contacts(redact_names(scrub_text(text, aliases), names))

    return aliases, clean


def pseudonymize_bundle(bundle: dict) -> dict:
    """A copy of the bundle with no real identity left in it, for the LLM.

    Commit author names are dropped outright rather than aliased: the decision
    beat cross-checks commit_history for *what* landed and when, and never needs
    to know who pushed it. Commit *messages* are cleaned rather than dropped —
    they carry the engineering content, and also "Co-authored-by:" trailers.
    """
    aliases, clean = _cleaner(bundle)

    metadata = bundle.get("metadata") or {}
    pr_metadata = bundle.get("pr_metadata") or {}
    return {
        **bundle,
        "metadata": {**metadata, "title": clean(metadata.get("title", ""))},
        "pr_metadata": {
            **pr_metadata,
            "reviewers": [
                aliases.get(r, FALLBACK_LABEL) for r in pr_metadata.get("reviewers") or []
            ],
        },
        "issue_payload": {
            **(bundle.get("issue_payload") or {}),
            "body": clean((bundle.get("issue_payload") or {}).get("body", "")),
        },
        "discussion_timeline": [
            {
                **entry,
                "author": aliases.get(entry.get("author"), FALLBACK_LABEL),
                "body": clean(entry.get("body", "")),
            }
            for entry in bundle.get("discussion_timeline") or []
        ],
        "commit_history": [
            {
                **{k: v for k, v in commit.items() if k != "author"},
                "message": clean(commit.get("message", "")),
            }
            for commit in bundle.get("commit_history") or []
        ],
    }


# Beat fields that hold prose a name could hide in.
_TEXT_FIELDS = ("title", "body", "question")

# "author" is handled separately. It holds nothing but an identity, so an exact
# login there is replaced by lookup rather than by the prose rules — those skip
# word-like logins such as `moul` on purpose, which is right inside a sentence
# and wrong for a field whose entire value is the person.
_IDENTITY_FIELDS = ("author",)


def scrub_workspace(payload: dict, bundle: dict) -> dict:
    """Last pass over generated beats, using `bundle` as the authority on which
    identities belong to this story. Applied before the workspace is cached, so
    a cache hit serves clean content without re-scrubbing."""
    aliases, clean = _cleaner(bundle)
    by_login = {login.lower(): alias for login, alias in aliases.items()}

    beats = []
    for beat in payload.get("beats") or []:
        scrubbed = dict(beat)
        for field in _IDENTITY_FIELDS:
            value = scrubbed.get(field)
            if isinstance(value, str):
                scrubbed[field] = by_login.get(value.strip().lower()) or clean(value)
        for field in _TEXT_FIELDS:
            if isinstance(scrubbed.get(field), str):
                scrubbed[field] = clean(scrubbed[field])
        if isinstance(scrubbed.get("lessons"), list):
            scrubbed["lessons"] = [
                clean(item) if isinstance(item, str) else item for item in scrubbed["lessons"]
            ]
        beats.append(scrubbed)
    return {**payload, "beats": beats}

"""Assert that no real identity survives anywhere a student or the LLM can see.

Run from the backend directory, before deploying:
    ./venv/bin/python scripts/check_privacy.py --dir seed_cache
    ./venv/bin/python scripts/check_privacy.py --dir /data/.cache   # deploy

Exits non-zero on any leak, so it can gate a release.

This stands in for a test suite the project does not have, and needs no test
dependency — the risk it guards is quiet. A prompt edit, a new beat field, or a
pipeline change can reintroduce a real login without anything failing, and the
result would be a published paper and a classroom tool that name people who
never agreed to appear in either.

Three checks:
  unit     the scrubber's behaviour on crafted input, including the logins that
           are ordinary English words (`cart`, `fire`) and must survive in prose
  corpus   every cached workspace, against its own bundle's real identities
  llm      what _build_raw_data actually sends to Anthropic, per bundle
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import privacy  # noqa: E402  (needs the path above)
from app.llm.workspace_generator import _build_raw_data  # noqa: E402

ALIAS_PREFIXES = tuple(privacy.ROLE_LABELS.values()) + (privacy.FALLBACK_LABEL,)

# Identities short enough to collide with ordinary prose are checked only in the
# fields that hold nothing but a name; scrub_text deliberately leaves them alone
# inside sentences. Mirrors privacy._is_distinctive.
MIN_PROSE_LEN = 5


def identities(bundle: dict) -> set[str]:
    out = {e["author"] for e in bundle.get("discussion_timeline") or [] if e.get("author")}
    out |= {r for r in bundle.get("pr_metadata", {}).get("reviewers") or [] if r}
    out |= {c["author"] for c in bundle.get("commit_history") or [] if c.get("author")}
    return out


def beat_prose(beat: dict) -> str:
    parts = [str(beat.get(f, "")) for f in ("title", "body", "question")]
    parts += [str(x) for x in beat.get("lessons") or []]
    return " ".join(parts)


def check_unit() -> list[str]:
    bundle = {
        "story_id": "acme/shop#1",
        "metadata": {"title": "Fix by arthuro555"},
        "pr_metadata": {"reviewers": ["4ian"], "merged_at": "x", "changed_files": 1},
        "issue_payload": {"body": "See /home/moul/go and github.com/jcfr/CTK. Thanks @cart!"},
        "discussion_timeline": [
            {"author": "arthuro555", "role": "CONTRIBUTOR", "body": "mine", "timestamp": "t"},
            {
                "author": "4ian",
                "role": "OWNER",
                "body": "arthuro555 is right but the shopping cart is slow. Fire the event.",
                "timestamp": "t",
            },
            {"author": "cart", "role": "NONE", "body": "Alice Cecile saw it too", "timestamp": "t"},
            {"author": "moul", "role": "CONTRIBUTOR", "body": "ack", "timestamp": "t"},
            {"author": "jcfr", "role": "MEMBER", "body": "ack", "timestamp": "t"},
            {"author": "ci[bot]", "role": "NONE", "body": "build failed", "timestamp": "t"},
        ],
        "commit_history": [
            {"sha": "abc1234", "message": "fix", "author": "Alice Cecile", "timestamp": "t"}
        ],
    }
    out = privacy.pseudonymize_bundle(bundle)
    timeline = out["discussion_timeline"]
    body_4ian = timeline[1]["body"]
    aliases = privacy.build_alias_map(bundle)

    cases = [
        ("author fields aliased", all(a.startswith(ALIAS_PREFIXES) for a in (e["author"] for e in timeline))),
        ("bot gets Automation alias", aliases["ci[bot]"].startswith("Automation")),
        ("@mention replaced", "@cart" not in out["issue_payload"]["body"]),
        ("home path username replaced", "/home/moul" not in out["issue_payload"]["body"]),
        ("url username replaced", "github.com/jcfr" not in out["issue_payload"]["body"]),
        ("login in prose replaced", "arthuro555" not in body_4ian),
        ("title login replaced", "arthuro555" not in out["metadata"]["title"]),
        ("reviewers aliased", all(r.startswith(ALIAS_PREFIXES) for r in out["pr_metadata"]["reviewers"])),
        ("word-login 'cart' kept in prose", "shopping cart" in body_4ian),
        ("word-login 'fire' kept in prose", "Fire the event" in body_4ian),
        ("real name redacted", "Alice Cecile" not in timeline[2]["body"]),
        ("commit author dropped", "author" not in out["commit_history"][0]),
    ]
    # A word-like author field is still a pure identity and must be aliased.
    workspace = {"beats": [{"type": "viewpoint", "author": "moul", "title": "", "body": ""}]}
    scrubbed = privacy.scrub_workspace(workspace, bundle)
    cases.append(
        ("word-like author field aliased", scrubbed["beats"][0]["author"].startswith(ALIAS_PREFIXES))
    )
    return [name for name, ok in cases if not ok]


def check_corpus(cache_dir: Path) -> list[str]:
    failures = []
    for path in sorted(cache_dir.glob("*:workspace*.json")):
        name = path.name
        story_id = name.split(":workspace")[0].replace("__", "/", 1)
        repo_key = name.split(":workspace")[0].split("#")[0]
        bundle = None
        for pass2 in sorted(cache_dir.glob(f"{repo_key}:*pass2.json")):
            try:
                data = json.loads(pass2.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(data, list):
                bundle = next(
                    (b for b in data if isinstance(b, dict) and b.get("story_id") == story_id),
                    bundle,
                )
        workspace = json.loads(path.read_text(encoding="utf-8"))

        for beat in workspace.get("beats") or []:
            author = beat.get("author")
            if isinstance(author, str) and not author.startswith(ALIAS_PREFIXES):
                failures.append(f"{name}: author {author!r} is not an alias")

        if bundle is None:
            failures.append(f"{name}: no bundle cached, cannot verify — delete it")
            continue
        for real in identities(bundle):
            if len(real) < MIN_PROSE_LEN:
                continue
            for beat in workspace.get("beats") or []:
                if re.search(rf"\b{re.escape(real)}\b", beat_prose(beat), re.I):
                    failures.append(f"{name}: {real!r} in {beat.get('type')} prose")
    return failures


def check_llm_input(cache_dir: Path, limit: int) -> list[str]:
    failures = []
    checked = 0
    for pass2 in sorted(cache_dir.glob("*pass2.json")):
        try:
            data = json.loads(pass2.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, list):
            continue
        for bundle in data:
            if not isinstance(bundle, dict) or checked >= limit:
                continue
            checked += 1
            raw = _build_raw_data(bundle)
            for real in identities(bundle):
                if len(real) < MIN_PROSE_LEN:
                    continue
                if re.search(rf"\b{re.escape(real)}\b", raw, re.I):
                    failures.append(f"{bundle['story_id']}: {real!r} reaches the LLM")
    print(f"  (checked {checked} bundles)")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", default="seed_cache", help="cache directory to audit")
    parser.add_argument("--llm-sample", type=int, default=250, help="bundles to check for step 3")
    args = parser.parse_args()

    cache_dir = Path(args.dir).resolve()
    if not cache_dir.is_dir():
        print(f"not a directory: {cache_dir}")
        return 1

    total = 0
    for label, failures in (
        ("unit", check_unit()),
        ("corpus", check_corpus(cache_dir)),
        ("llm", check_llm_input(cache_dir, args.llm_sample)),
    ):
        status = "ok" if not failures else f"{len(failures)} FAILED"
        print(f"{label:8} {status}")
        for line in failures[:20]:
            print(f"    - {line}")
        if len(failures) > 20:
            print(f"    … and {len(failures) - 20} more")
        total += len(failures)

    print()
    print("PASS — no real identity reaches a student or the LLM" if not total else f"FAIL — {total} leak(s)")
    return 0 if not total else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Re-label cached stories against the current quality-attribute vocabulary.

Run from the backend directory:
    ./venv/bin/python scripts/relabel_qualities.py --dir seed_cache --dry-run
    ./venv/bin/python scripts/relabel_qualities.py --dir seed_cache
    ./venv/bin/python scripts/relabel_qualities.py --dir /data/.cache   # deploy

Why this exists: the gate's label vocabulary grew from four attributes to the
eight taught in the course, so every story cached under the old vocabulary
carries labels that no longer exist (`maintainability`) and is missing the ones
that now matter (`testability`, `deployability`, ...). Bumping PIPELINE_VERSION
alone would fix that only by making the next student on each repo sit through a
full re-mine — GitHub search, review-thread fetch, gate, enrichment — and the
committed seed library holds no pass1 caches to replay, so those round trips
would all be real.

They aren't needed. A pass2 bundle already carries everything the gate reads:
the title, the issue body, and the full discussion timeline. So this reads each
old-version bundle, hands it back to the same `_gate_candidate` the pipeline
uses, and writes a new-version bundle with fresh labels. No GitHub calls, and
one Haiku call per story (~$0.014 per repo).

Stories the gate now rejects are kept, not dropped: `is_story` is a screening
decision that was already made when the repo was mined, and re-litigating it
here would silently shrink a library the class is already using.
"""

import argparse
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Make `import app` work when run directly as scripts/relabel_qualities.py.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.filters import QUALITY_ATTRIBUTES  # noqa: E402
from app.pipeline.orchestrator import PIPELINE_VERSION  # noqa: E402
from app.pipeline.pass1_5_semantic_gate import MAX_WORKERS, _gate_candidate  # noqa: E402

# Versions this script knows how to read. Kept explicit so a future bump has to
# consciously decide whether its cached shape is still convertible.
CONVERTIBLE_FROM = ["v2", ""]


def _bundle_to_candidate(bundle: dict) -> dict:
    """Reshape a pass2 bundle back into the candidate dict the gate expects.

    The gate reads `issue.title`, `issue.body`, and `comments[].user.login` /
    `.author_association` / `.body` — all of which pass2 preserved under
    different names."""
    return {
        "issue": {
            "number": bundle["story_id"].rpartition("#")[2],
            "title": bundle["metadata"]["title"],
            "body": bundle.get("issue_payload", {}).get("body", ""),
        },
        "comments": [
            {
                "user": {"login": entry["author"]},
                "author_association": entry.get("role", "NONE"),
                "body": entry.get("body", ""),
            }
            for entry in bundle.get("discussion_timeline", [])
        ],
    }


def _relabel_bundle(bundle: dict) -> tuple[dict, tuple[int, int], bool]:
    """One gate call. Returns (bundle, usage, ok).

    The gate's return value is ignored: a `is_story: false` verdict means "this
    wasn't worth mining", which was already decided when the repo was mined and
    is not this script's business to revisit. The labels are read off the
    candidate dict, which the gate populates either way.

    Only a genuine API failure leaves no labels — and there the old ones are
    cleared rather than kept. Stale labels look harmless but are worse than
    none: a story left holding a retired label matches no current filter and no
    fail-open branch, so it silently disappears from the catalog entirely."""
    candidate = _bundle_to_candidate(bundle)
    _, usage = _gate_candidate(candidate)
    ok = "qualities" in candidate
    bundle["metadata"]["qualities"] = candidate.get("qualities", [])
    return bundle, usage, ok


_VERSIONED = re.compile(r":v\d+$")


def _source_paths(cache_dir: Path) -> list[tuple[Path, Path]]:
    """(old, new) path pairs for every convertible pass2 cache in the dir.

    Keyed by repo so each repo is converted once: the unversioned pattern
    `*:pass2.json` also matches `owner__repo:v2:pass2.json`, and taking that
    match at face value yields a `owner__repo:v2:v3:pass2.json` double-version
    — including re-converting this run's own output."""
    pairs: dict[str, tuple[Path, Path]] = {}
    for old_version in CONVERTIBLE_FROM:
        suffix = f":{old_version}:pass2.json" if old_version else ":pass2.json"
        for path in sorted(cache_dir.glob(f"*{suffix}")):
            repo_key = path.name[: -len(suffix)]
            if _VERSIONED.search(repo_key):
                continue  # a versioned cache caught by the unversioned pattern
            new_path = cache_dir / f"{repo_key}:{PIPELINE_VERSION}:pass2.json"
            if new_path.exists() or repo_key in pairs:
                continue  # already migrated, or a newer version already queued
            pairs[repo_key] = (path, new_path)
    return list(pairs.values())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", default="seed_cache", help="cache directory to migrate")
    parser.add_argument("--dry-run", action="store_true", help="report only, no LLM calls")
    parser.add_argument("--limit", type=int, help="migrate at most N repos (for a trial run)")
    args = parser.parse_args()

    cache_dir = Path(args.dir)
    if not cache_dir.is_dir():
        sys.exit(f"No such directory: {cache_dir}")

    pairs = _source_paths(cache_dir)
    if args.limit:
        pairs = pairs[: args.limit]
    if not pairs:
        print(f"Nothing to migrate in {cache_dir} — every cache is already {PIPELINE_VERSION}.")
        return

    stories = sum(len(json.loads(old.read_text(encoding="utf-8"))) for old, _ in pairs)
    print(f"{len(pairs)} repos / {stories} stories -> {PIPELINE_VERSION}")
    print(f"Vocabulary: {', '.join(QUALITY_ATTRIBUTES)}\n")
    if args.dry_run:
        for old, new in pairs:
            print(f"  {old.name}  ->  {new.name}")
        print(f"\nDry run — no LLM calls made. ~{stories} gate calls would run.")
        return

    start = time.time()
    before: dict[str, int] = {}
    after: dict[str, int] = {q: 0 for q in QUALITY_ATTRIBUTES}
    total_in = total_out = failed = 0

    for old, new in pairs:
        bundles = json.loads(old.read_text(encoding="utf-8"))
        for b in bundles:
            for q in b["metadata"].get("qualities", []):
                before[q] = before.get(q, 0) + 1

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            results = list(executor.map(_relabel_bundle, bundles))

        relabeled = [b for b, _, _ in results]
        total_in += sum(u[0] for _, u, _ in results)
        total_out += sum(u[1] for _, u, _ in results)
        failed += sum(1 for _, _, ok in results if not ok)
        for b in relabeled:
            for q in b["metadata"].get("qualities", []):
                after[q] = after.get(q, 0) + 1

        new.write_text(
            json.dumps(relabeled, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"  {new.name}  ({len(relabeled)} stories)")

    elapsed = round(time.time() - start, 1)
    print(f"\nDone in {elapsed}s — {total_in:,} in / {total_out:,} out tokens")
    if failed:
        print(
            f"WARNING: {failed} stories got no labels (gate API failure) and now "
            f"pass every filter. Re-run to retry them."
        )
    print("\nLabel distribution:")
    width = max(len(q) for q in set(before) | set(after))
    for q in sorted(set(before) | set(after), key=lambda q: -after.get(q, 0)):
        print(f"  {q:<{width}}  {before.get(q, 0):>4} -> {after.get(q, 0):>4}")


if __name__ == "__main__":
    main()

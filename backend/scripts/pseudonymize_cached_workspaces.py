"""Pseudonymize workspaces generated before app/privacy.py existed.

Run from the backend directory:
    ./venv/bin/python scripts/pseudonymize_cached_workspaces.py --dir seed_cache --dry-run
    ./venv/bin/python scripts/pseudonymize_cached_workspaces.py --dir seed_cache
    ./venv/bin/python scripts/pseudonymize_cached_workspaces.py --dir /data/.cache   # deploy

Why this exists: workspaces cached before the privacy pass carry real GitHub
logins in `author`, in beat titles ("Position A — arthuro555") and inside the
prose itself. Regenerating them would mean paying Sonnet again for 40 stories
to rewrite text that is already correct — the only thing wrong with it is the
names. So this rewrites the names in place instead, at no token cost, using the
same scrubber the live path uses.

The alias map comes from the story's pass2 bundle, which is the authority on who
took part. A workspace whose bundle is no longer cached cannot be scrubbed — but
it also can't be reached, since the library and story list are both built from
pass2 bundles, so it is reported and left for deletion rather than shipped with
real names still in it.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import privacy  # noqa: E402  (needs the path above)


def story_id_from_name(name: str) -> str:
    """'4ian__GDevelop#2006:workspace:p1.json' -> '4ian/GDevelop#2006'.

    Only the first '__' is a separator: GitHub owner names cannot contain an
    underscore, but repository names can (`freqtrade__freqtrade-strategies`).
    """
    return name.split(":workspace")[0].replace("__", "/", 1)


def bundles_for(cache_dir: Path, name: str) -> list[dict]:
    """Every pass2 bundle for this workspace's repo, under any pipeline version.
    A workspace cache key carries no version, so its bundle may sit under v2, v3
    or the original unversioned key."""
    repo_key = name.split(":workspace")[0].split("#")[0]
    found: list[dict] = []
    for path in sorted(cache_dir.glob(f"{repo_key}:*pass2.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, list):
            found.extend(b for b in data if isinstance(b, dict))
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", required=True, help="cache directory to rewrite")
    parser.add_argument("--dry-run", action="store_true", help="report without writing")
    args = parser.parse_args()

    cache_dir = Path(args.dir).resolve()
    if not cache_dir.is_dir():
        print(f"not a directory: {cache_dir}")
        return 1

    files = sorted(cache_dir.glob("*:workspace*.json"))
    mode = "DRY RUN" if args.dry_run else "WRITE"
    print(f"{mode} over {len(files)} workspace file(s) in {cache_dir}\n")

    changed = clean = orphaned = 0
    orphans: list[str] = []
    for path in files:
        story_id = story_id_from_name(path.name)
        bundle = next(
            (b for b in bundles_for(cache_dir, path.name) if b.get("story_id") == story_id),
            None,
        )
        if bundle is None:
            orphaned += 1
            orphans.append(path.name)
            continue

        before = json.loads(path.read_text(encoding="utf-8"))
        after = privacy.scrub_workspace(before, bundle)
        if after == before:
            clean += 1
            continue

        changed += 1
        for old, new in zip(before.get("beats") or [], after.get("beats") or []):
            for field in ("author", "title", "body", "question"):
                o, n = old.get(field), new.get(field)
                if isinstance(o, str) and o != n:
                    print(f"  {path.name} [{old.get('type')}.{field}]")
                    print(f"    - {o[:100]}")
                    print(f"    + {n[:100]}")
        if not args.dry_run:
            path.write_text(
                json.dumps(after, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )

    print(f"\nchanged {changed} | already clean {clean} | no bundle {orphaned}")
    for name in orphans:
        print(f"  unreachable, delete it: {name}")
    if args.dry_run and changed:
        print("re-run without --dry-run to apply")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

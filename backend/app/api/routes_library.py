import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.api.routes_repos import STORY_CAP
from app.config import GITHUB_TOKEN
from app.db import get_session
from app.github_client import GitHubClient
from app.llm.repo_classifier import classify_repos_domains
from app.models.db_models import Repo
from app.models.schemas import StorySummary
from app.storage.cache import CACHE_DIR

router = APIRouter(tags=["library"])


def _to_summary(bundle: dict) -> StorySummary:
    return StorySummary(
        story_id=bundle["story_id"],
        title=bundle["metadata"]["title"],
        labels=bundle["metadata"]["labels"],
        qualities=bundle["metadata"].get("qualities", []),
    )


def _repo_from_cache_key(filename: str) -> str:
    # filename looks like "PaperMC__Paper:pass2.json" → "PaperMC/Paper"
    key = filename.replace(":pass2.json", "")
    return key.replace("__", "/")


@router.get("/library")
def get_library(session: Session = Depends(get_session)):
    results = []
    if not CACHE_DIR.exists():
        return results

    for path in sorted(CACHE_DIR.glob("*:pass2.json")):
        try:
            bundles = json.loads(path.read_text(encoding="utf-8"))
            repo = _repo_from_cache_key(path.name)
            # Same read-time cap as the stories API — pass2 caches now hold
            # every enriched elite, not just the top few.
            stories = [_to_summary(b) for b in bundles[:STORY_CAP]]
            # Hide repos whose mining yielded no stories — nothing to read.
            if stories:
                results.append({"repo": repo, "stories": stories})
        except Exception:
            continue

    _attach_repo_meta(session, results)
    return results


def _attach_repo_meta(session: Session, results: list[dict]) -> None:
    """Attach domain + description from the `repos` table. Repos not yet in the
    table are classified (Haiku) and described (GitHub REST, no LLM) once, then
    persisted — so this only pays for genuinely new repos."""
    repo_names = [r["repo"] for r in results]
    rows = {
        row.repo: row
        for row in session.exec(select(Repo).where(Repo.repo.in_(repo_names))).all()
    }

    missing = [r for r in results if r["repo"] not in rows]
    if missing:
        domain_map = classify_repos_domains(
            [{"repo": r["repo"], "titles": [s.title for s in r["stories"]]} for r in missing]
        )
        github = GitHubClient(GITHUB_TOKEN)

        def fetch_desc(repo: str) -> str | None:
            obj = github.get_repo(repo)
            return (obj.get("description") or "") if obj.get("full_name") else None

        with ThreadPoolExecutor(max_workers=8) as executor:
            desc_list = list(executor.map(fetch_desc, [r["repo"] for r in missing]))

        for entry, description in zip(missing, desc_list):
            repo = entry["repo"]
            row = Repo(
                repo=repo,
                domain=domain_map.get(repo),
                description=description,
            )
            session.add(row)
            rows[repo] = row
        session.commit()

    for r in results:
        row = rows.get(r["repo"])
        r["domain"] = row.domain if row else None
        r["description"] = (row.description or None) if row else None

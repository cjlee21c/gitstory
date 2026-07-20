"""One-shot, idempotent migration of the prototype flat files into SQLite.

Run from the backend directory:
    ./venv/bin/python scripts/migrate.py

Imports:
  - answers/*.json              -> users (get-or-create by student_id) + answers
  - .cache/library:domains:v1   -> repos.domain
  - .cache/library:descriptions:v1 -> repos.description

Re-running skips rows that already exist, so it's safe to run repeatedly.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Make `import app` work when run directly as scripts/migrate.py.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, select  # noqa: E402

from app.db import create_db_and_tables, engine  # noqa: E402
from app.models.db_models import Answer, Repo, User  # noqa: E402
from app.storage import cache  # noqa: E402

ANSWERS_DIR = Path(__file__).resolve().parent.parent / "answers"


def _parse_dt(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return datetime.now(timezone.utc)


def _get_or_create_user(session: Session, student_id: str) -> User:
    user = session.exec(select(User).where(User.student_id == student_id)).first()
    if user is None:
        user = User(student_id=student_id, display_name=student_id)
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


def migrate_answers(session: Session) -> tuple[int, int]:
    new_answers = 0
    new_users = 0
    if not ANSWERS_DIR.exists():
        return 0, 0

    before_users = session.exec(select(User)).all()
    before_count = len(before_users)

    for path in sorted(ANSWERS_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            print(f"  ! skipped unreadable {path.name}")
            continue

        student_id = (data.get("student_id") or "").strip()
        story_id = (data.get("story_id") or "").strip()
        if not student_id or not story_id:
            continue

        user = _get_or_create_user(session, student_id)

        # Idempotent: skip if this (user, story) answer already migrated.
        exists = session.exec(
            select(Answer).where(Answer.user_id == user.id, Answer.story_id == story_id)
        ).first()
        if exists:
            continue

        session.add(
            Answer(
                user_id=user.id,
                story_id=story_id,
                kind="reflection",
                selected_option=data.get("selected_option"),
                response_text=data.get("reflection"),
                submitted_at=_parse_dt(data.get("submitted_at")),
            )
        )
        new_answers += 1

    session.commit()
    after_count = len(session.exec(select(User)).all())
    new_users = after_count - before_count
    return new_users, new_answers


def migrate_repos(session: Session) -> int:
    domains = cache.get("library:domains:v1") or {}
    descriptions = cache.get("library:descriptions:v1") or {}
    repos = set(domains) | set(descriptions)

    new_repos = 0
    for repo in sorted(repos):
        existing = session.get(Repo, repo)
        if existing:
            # Backfill any missing fields without clobbering existing values.
            changed = False
            if existing.domain is None and domains.get(repo):
                existing.domain = domains[repo]
                changed = True
            if existing.description is None and descriptions.get(repo):
                existing.description = descriptions[repo]
                changed = True
            if changed:
                session.add(existing)
            continue
        session.add(
            Repo(repo=repo, domain=domains.get(repo), description=descriptions.get(repo))
        )
        new_repos += 1

    session.commit()
    return new_repos


def main() -> None:
    create_db_and_tables()
    with Session(engine) as session:
        new_users, new_answers = migrate_answers(session)
        new_repos = migrate_repos(session)

        total_users = len(session.exec(select(User)).all())
        total_answers = len(session.exec(select(Answer)).all())
        total_repos = len(session.exec(select(Repo)).all())

    print("Migration complete.")
    print(f"  users:   +{new_users} new  (total {total_users})")
    print(f"  answers: +{new_answers} new  (total {total_answers})")
    print(f"  repos:   +{new_repos} new  (total {total_repos})")


if __name__ == "__main__":
    main()

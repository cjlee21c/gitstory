import os
from collections.abc import Iterator
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

# Single-file SQLite DB. Defaults to the backend root (gitignored via
# backend/*.db); in deploy, DB_PATH points at a mounted disk (e.g.
# /data/gitstory.db) so it survives redeploys.
DB_PATH = Path(os.environ.get("DB_PATH", Path(__file__).resolve().parent.parent / "gitstory.db"))

# check_same_thread=False: FastAPI serves sync endpoints from a thread pool, so a
# session may be used on a different thread than the one that opened it.
engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
)


def create_db_and_tables() -> None:
    # Import models so their tables are registered on SQLModel.metadata.
    from app.models import db_models  # noqa: F401

    # Ensure the parent dir exists (e.g. a freshly mounted /data disk).
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session

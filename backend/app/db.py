from collections.abc import Iterator
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

# Single-file SQLite DB at the backend root (gitignored via backend/*.db).
DB_PATH = Path(__file__).resolve().parent.parent / "gitstory.db"

# check_same_thread=False: FastAPI serves sync endpoints from a thread pool, so a
# session may be used on a different thread than the one that opened it.
engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
)


def create_db_and_tables() -> None:
    # Import models so their tables are registered on SQLModel.metadata.
    from app.models import db_models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session

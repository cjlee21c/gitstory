from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    student_id: str = Field(index=True, unique=True)  # roster key
    display_name: str | None = None
    role: str = Field(default="student")
    created_at: datetime = Field(default_factory=_utcnow)

    # Auth columns — provider-agnostic, unused this round. Any login method
    # (Google OAuth, password, …) drops in later without a migration.
    email: str | None = Field(default=None, index=True)
    auth_provider: str | None = None  # "google" | "password" | ...
    provider_subject: str | None = None  # e.g. Google `sub`
    password_hash: str | None = None


class Repo(SQLModel, table=True):
    __tablename__ = "repos"

    repo: str = Field(primary_key=True)  # "owner/name"
    domain: str | None = None
    description: str | None = None
    language: str | None = None
    stars: int | None = None
    mined_at: datetime = Field(default_factory=_utcnow)


class Answer(SQLModel, table=True):
    __tablename__ = "answers"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    story_id: str = Field(index=True)  # soft ref, e.g. "4ian/GDevelop#2006"
    beat_id: str | None = None
    kind: str = Field(default="reflection")  # future: "mcq" | "short"
    selected_option: str | None = None
    response_text: str | None = None
    # Filled only for graded quizzes later; reflections leave these null.
    is_correct: bool | None = None
    score: float | None = None
    submitted_at: datetime = Field(default_factory=_utcnow)

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, field_validator

from app.filters import CONTRIBUTOR_BUCKETS, DOMAINS, SIZE_BUCKETS, STAR_BUCKETS

# Literal types generated from filters.py so an unknown filter id from the
# frontend fails validation with a 422 instead of silently passing through.
DomainId = Literal[tuple(DOMAINS)]  # type: ignore[valid-type]
SizeId = Literal[tuple(SIZE_BUCKETS)]  # type: ignore[valid-type]
StarId = Literal[tuple(STAR_BUCKETS)]  # type: ignore[valid-type]
ContribId = Literal[tuple(CONTRIBUTOR_BUCKETS)]  # type: ignore[valid-type]


class StoryMetadata(BaseModel):
    title: str
    labels: list[str]
    qualities: list[str] = []


class PRMetadata(BaseModel):
    merged_at: str
    reviewers: list[str]
    changed_files: int


class IssuePayload(BaseModel):
    body: str


class DiscussionEntry(BaseModel):
    author: str
    role: str
    body: str
    timestamp: str
    # "issue" | "review" | "review_inline". Defaulted so bundles cached before
    # review threads were merged in still validate.
    source: str = "issue"


class CommitEntry(BaseModel):
    sha: str
    message: str
    author: str
    timestamp: str


class StoryBundle(BaseModel):
    story_id: str
    metadata: StoryMetadata
    pr_metadata: PRMetadata
    issue_payload: IssuePayload
    discussion_timeline: list[DiscussionEntry]
    commit_history: list[CommitEntry]


class StorySummary(BaseModel):
    story_id: str
    title: str
    labels: list[str]
    qualities: list[str] = []


class StoryListResponse(BaseModel):
    stories: list[StorySummary]
    # Per-quality label counts over the repo's full (unfiltered, uncapped) story
    # set, so the UI can show which quality filters actually have content and
    # grey out dead ones. Computed from cached labels — no extra LLM/API cost.
    quality_counts: dict[str, int]
    # Set when the requested focus matched nothing and `stories` is the
    # unfiltered fallback instead. Mirrors DiscoverResponse.notice.
    notice: str | None = None


class PipelineRunResponse(BaseModel):
    repo: str
    story_count: int
    cached: bool
    stories: list[StorySummary]


class ContextBeat(BaseModel):
    beat_id: str
    type: Literal["context"]
    order: int
    title: str
    body: str
    source_refs: list[str] = []


class DilemmaBeat(BaseModel):
    beat_id: str
    type: Literal["dilemma"]
    order: int
    title: str
    body: str
    source_refs: list[str] = []


class ViewpointBeat(BaseModel):
    beat_id: str
    type: Literal["viewpoint"]
    order: int
    title: str
    body: str
    author: str
    author_role: str
    source_refs: list[str] = []

class CheckpointBeat(BaseModel):
    beat_id: str
    type: Literal["checkpoint"]
    order: int
    question: str
    format: Literal["reflection"] = "reflection"
    must_precede_decision: bool = True


class DecisionBeat(BaseModel):
    beat_id: str
    type: Literal["decision"]
    order: int
    title: str
    body: str
    source_refs: list[str] = []


class LessonsBeat(BaseModel):
    beat_id: str
    type: Literal["lessons"]
    order: int
    title: str
    lessons: list[str]


Beat = Annotated[
    Union[ContextBeat, DilemmaBeat, ViewpointBeat, CheckpointBeat, DecisionBeat, LessonsBeat],
    Field(discriminator="type"),
]


class WorkspaceContent(BaseModel):
    story_id: str
    beats: list[Beat]


# A curated domain id OR a free-text custom domain the student typed. Custom
# values are ephemeral search seeds only — repos get re-bucketed into the
# curated 8 by classify_repos_domains() before they ever reach the library.
CUSTOM_DOMAIN_MAX_LEN = 40


class DiscoverRequest(BaseModel):
    domain: str
    sizes: list[SizeId] = []
    stars: StarId | None = None
    contributors: ContribId | None = None
    keyword: str | None = None
    # Only used to rotate which slice of the result pool this student sees, so
    # coming back to the same filters doesn't show the same repos again. Not
    # part of the discovery cache key — students share the underlying pool.
    student_id: str | None = None

    @field_validator("domain")
    @classmethod
    def _validate_domain(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("domain must not be empty")
        if v in DOMAINS:
            return v
        if len(v) > CUSTOM_DOMAIN_MAX_LEN:
            raise ValueError(f"custom domain must be {CUSTOM_DOMAIN_MAX_LEN} characters or fewer")
        return v


class RepoRecommendation(BaseModel):
    repo: str
    summary: str
    stars: int | None = None
    language: str | None = None


class DiscoverResponse(BaseModel):
    repos: list[RepoRecommendation]
    # Set when the filters matched too little on GitHub and discovery widened
    # them; explains to the student what changed and why.
    notice: str | None = None
    relaxed: list[str] = []
